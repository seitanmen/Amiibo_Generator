#!/usr/bin/env python3
"""
Enhanced Amiibo Bin Generator
AmiiboAPIデータとタイプ別テンプレートシステムを使用して、より正確な.binファイルを生成する
"""

import os
import json
import sys
import argparse
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# pyamiiboライブラリのインポート
try:
    from amiibo import AmiiboDump, AmiiboMasterKey
except ImportError:
    print("Error: pyamiibo library not found. Install with: pip install pyamiibo")
    sys.exit(1)

class EnhancedAmiiboGenerator:
    def __init__(self, key_file="key_retail.bin"):
        self.key_file = key_file
        self.keys = None
        self.template_cache = {}
        
    def load_keys(self) -> bool:
        """暗号化キーをロードする"""
        if not os.path.exists(self.key_file):
            print(f"Error: Key file '{self.key_file}' not found")
            return False
        
        try:
            with open(self.key_file, 'rb') as f:
                key_data = f.read()
            
            if len(key_data) == 160:
                self.keys = AmiiboMasterKey.from_combined_bin(key_data)
                print(f"Successfully loaded encryption keys from {self.key_file}")
                return True
            else:
                print(f"Error: Invalid key file size. Expected 160 bytes, got {len(key_data)}")
                return False
                
        except Exception as e:
            print(f"Error loading keys: {e}")
            return False
    
    def load_amiibo_data(self, data_file: str) -> Optional[Dict]:
        """Amiibo APIデータをロードする"""
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'amiibo' not in data:
                print("Error: Invalid API data format - missing 'amiibo' key")
                return None
            
            print(f"Loaded {len(data['amiibo'])} Amiibo entries from {data_file}")
            return data
            
        except Exception as e:
            print(f"Error loading API data: {e}")
            return None
    
    def sanitize_filename(self, name: str) -> str:
        """ファイル名として使用できない文字を置換する"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        name = name.rstrip('. ')
        if not name:
            name = "Unknown"
        return name
    
    def get_template_for_amiibo(self, amiibo_info: Dict) -> Optional[str]:
        """Amiiboタイプに応じたテンプレートファイルを取得する"""
        amiibo_type = amiibo_info.get('type', 'Figure')
        series = amiibo_info.get('amiiboSeries', '')
        
        # テンプレートマッピング
        template_mapping = {
            'Card': {
                'primary': '8-Bit Mario Classic Color.bin',  # デフォルト
                'alternatives': {
                    'Animal Crossing': 'Animal_Crossing_Card.bin',
                    'Mario Sports Superstars': 'Mario_Sports_Card.bin'
                }
            },
            'Figure': {
                'primary': '8-Bit Mario Classic Color.bin',  # デフォルト
                'alternatives': {
                    'Super Smash Bros.': 'Smash_Figure.bin',
                    'Legend Of Zelda': 'Zelda_Figure.bin',
                    'Splatoon': 'Splatoon_Figure.bin'
                }
            },
            'Band': {
                'primary': '8-Bit Mario Classic Color.bin',  # デフォルト
                'alternatives': {
                    'Super Nintendo World': 'SNW_Band.bin'
                }
            },
            'Yarn': {
                'primary': '8-Bit Mario Classic Color.bin',  # デフォルト
                'alternatives': {
                    "Yoshi's Woolly World": 'Yoshi_Yarn.bin'
                }
            },
            'Block': {
                'primary': '8-Bit Mario Classic Color.bin',  # デフォルト
                'alternatives': {
                    'My Mario Wooden Blocks': 'Mario_Block.bin'
                }
            }
        }
        
        # 適切なテンプレートを選択
        if amiibo_type in template_mapping:
            type_config = template_mapping[amiibo_type]
            
            # シリーズ固有のテンプレートを優先
            if series in type_config['alternatives']:
                template_file = type_config['alternatives'][series]
                if os.path.exists(template_file):
                    return template_file
            
            # プライマリテンプレートを使用
            if os.path.exists(type_config['primary']):
                return type_config['primary']
        
        # フォールバック
        return "8-Bit Mario Classic Color.bin"
    
    def create_amiibo_identification_block(self, amiibo_info: Dict) -> Optional[bytes]:
        """Amiibo Identification Blockを生成する"""
        head = amiibo_info.get('head', '')
        tail = amiibo_info.get('tail', '')
        amiibo_type = amiibo_info.get('type', 'Figure')
        series = amiibo_info.get('amiiboSeries', '')
        name = amiibo_info.get('name', 'Unknown')
        
        # 8バイトのIdentification Blockを生成
        id_block = bytearray(8)
        
        # デバッグ情報
        if len(head) != 8 or len(tail) != 8:
            print(f"Debug: Invalid head/tail length for {name}: head={head}({len(head)}), tail={tail}({len(tail)})")
            return None
        
        try:
            # Game & Character ID（headの最初の6桁 + tailの最初の2桁）
            game_char_hex = head[:6] + tail[:2]
            game_char_id = int(game_char_hex, 16)
            id_block[0:2] = game_char_id.to_bytes(2, 'big')
            
            # Character variant（headの6-8桁目）
            id_block[2] = int(head[6:8], 16)
            
            # Amiibo Figure Type（typeからマッピング）
            type_mapping = {
                'Card': 0x00,
                'Figure': 0x01,
                'Band': 0x02,
                'Yarn': 0x03,
                'Block': 0x04
            }
            id_block[3] = type_mapping.get(amiibo_type, 0x01)
            
            # Amiibo Model Number（head/tailから計算）
            model_hex = head[2:4] + tail[2:4]
            model_number = int(model_hex, 16) & 0xFFFF
            id_block[4:6] = model_number.to_bytes(2, 'big')
            
            # Amiibo Series（シリーズからマッピング）
            series_mapping = {
                'Animal Crossing': 0x00,
                'Super Smash Bros.': 0x01,
                'Mario Sports Superstars': 0x02,
                'Legend Of Zelda': 0x03,
                'Splatoon': 0x04,
                'Street Fighter 6': 0x05,
                'Super Mario Bros.': 0x06,
                'Monster Hunter': 0x07,
                'Monster Hunter Rise': 0x08,
                'Yoshi\'s Woolly World': 0x09,
                'My Mario Wooden Blocks': 0x0A,
                'Super Nintendo World': 0x0B,
                'Fire Emblem': 0x0C,
                'Pokemon': 0x0D,
                'Kirby': 0x0E,
                'Metroid': 0x0F,
                'Others': 0x10
            }
            id_block[6] = series_mapping.get(series, 0x00)
            
            # Format Version（常に0x02）
            id_block[7] = 0x02
            
            return bytes(id_block)
            
        except Exception as e:
            print(f"Debug: Error creating ID block for {name}: {e}")
            print(f"Debug: head={head}, tail={tail}, type={amiibo_type}, series={series}")
            return None
    
    def create_enhanced_amiibo_data(self, amiibo_info: Dict) -> Optional[bytes]:
        """改良版Amiiboデータ構造を作成する"""
        head = amiibo_info.get('head', '')
        tail = amiibo_info.get('tail', '')
        
        if not head or not tail:
            print(f"Warning: Missing head/tail for {amiibo_info.get('name', 'Unknown')}")
            return None
        
        # 適切なテンプレートを取得
        template_file = self.get_template_for_amiibo(amiibo_info)
        if not template_file or not os.path.exists(template_file):
            print(f"Error: Template file not found for {amiibo_info.get('name', 'Unknown')}")
            return None
        
        # テンプレートをロード
        try:
            with open(template_file, 'rb') as f:
                template_data = f.read()
            
            # テンプレートを復号化
            template_dump = AmiiboDump(self.keys, template_data)
            template_dump.unlock()
            
            # 新しいAmiiboDumpを作成
            new_dump = AmiiboDump(self.keys, template_dump.data, is_locked=False)
            
            # UIDを設定（最初のバイトを保持）
            existing_first_byte = template_dump._uid_raw[0:1].hex()
            new_uid_suffix = (head + tail)[2:]  # 最初の2文字をスキップ
            new_uid_7bytes = existing_first_byte + new_uid_suffix[:12]
            new_dump.uid_hex = new_uid_7bytes
            
            # Amiibo Identification Blockを更新（0x54オフセット）
            identification_block = self.create_amiibo_identification_block(amiibo_info)
            if identification_block:
                new_dump.data[0x54:0x5C] = identification_block
            
            # タイプ固有の追加設定
            self.apply_type_specific_settings(new_dump, amiibo_info)
            
            # 暗号化してロック
            new_dump.lock()
            
            return bytes(new_dump.data)
            
        except Exception as e:
            print(f"Error creating enhanced amiibo data: {e}")
            return None
    
    def apply_type_specific_settings(self, dump: AmiiboDump, amiibo_info: Dict):
        """タイプ固有の設定を適用する"""
        amiibo_type = amiibo_info.get('type', 'Figure')
        series = amiibo_info.get('amiiboSeries', '')
        
        # カード固有の設定
        if amiibo_type == 'Card':
            # Animal Crossingカードの初期化データ
            if series == 'Animal Crossing':
                # AppData領域を初期化
                dump.data[0x208:0x210] = b'\x00' * 8  # Country Code
                dump.data[0x20C:0x20E] = b'\x00\x00'  # Write counter
                
        # フィギュア固有の設定
        elif amiibo_type == 'Figure':
            # Smash Bros.フィギュアの初期化データ
            if series == 'Super Smash Bros.':
                # Smash Bros. AppIDを設定
                dump.data[0x180:0x184] = b'\x00\x10\x11\x0E'  # Smash AppID
    
    def create_series_directory(self, output_dir: str, series: str) -> str:
        """シリーズ用のディレクトリを作成する"""
        safe_series = self.sanitize_filename(series)
        series_dir = os.path.join(output_dir, safe_series)
        os.makedirs(series_dir, exist_ok=True)
        return series_dir
    
    def generate_bin_file(self, amiibo_info: Dict) -> Optional[bytes]:
        """個別のAmiibo .binファイルを生成する"""
        try:
            return self.create_enhanced_amiibo_data(amiibo_info)
        except Exception as e:
            print(f"Error generating bin for {amiibo_info.get('name', 'Unknown')}: {e}")
            return None
    
    def generate_all_bins(self, data_file: str = "amiibo_api_data.json", 
                         output_dir: str = "enhanced_amiibo_bins",
                         organize_by_series: bool = True) -> bool:
        """すべてのAmiibo .binファイルを生成する"""
        # キーをロード
        if not self.load_keys():
            return False
        
        # APIデータをロード
        data = self.load_amiibo_data(data_file)
        if data is None:
            return False
        
        # 出力ディレクトリを作成
        os.makedirs(output_dir, exist_ok=True)
        
        amiibos = data['amiibo']
        success_count = 0
        error_count = 0
        series_counts = {}
        type_counts = defaultdict(int)
        
        print(f"Generating {len(amiibos)} enhanced Amiibo bin files...")
        
        # 進捗バーの設定
        if tqdm:
            progress_iter = tqdm(amiibos, desc="Processing Amiibos")
        else:
            progress_iter = amiibos
        
        for i, amiibo in enumerate(progress_iter, 1):
            name = amiibo.get('name', 'Unknown')
            series = amiibo.get('amiiboSeries', 'Unknown Series')
            amiibo_type = amiibo.get('type', 'Figure')
            
            # 進捗表示（tqdm未使用時のみ）
            if not tqdm:
                print(f"[{i}/{len(amiibos)}] Processing: {name} ({series}) - {amiibo_type}")
            
            # .binデータ生成
            bin_data = self.generate_bin_file(amiibo)
            if bin_data is None:
                error_count += 1
                continue
            
            # 出力先ディレクトリを決定
            if organize_by_series:
                target_dir = self.create_series_directory(output_dir, series)
                if series not in series_counts:
                    series_counts[series] = 0
                series_counts[series] += 1
            else:
                target_dir = output_dir
            
            # ファイル名をサニタイズし、IDを追加
            safe_name = self.sanitize_filename(name)
            amiibo_id = amiibo.get('head', '') + amiibo.get('tail', '')
            filename = f"{safe_name}_{amiibo_id}.bin"
            filepath = os.path.join(target_dir, filename)
            
            # 重複チェック
            if os.path.exists(filepath):
                print(f"  -> File already exists, skipping: {filename}")
                continue
            
            # ファイルを保存
            try:
                with open(filepath, 'wb') as f:
                    f.write(bin_data)
                success_count += 1
                type_counts[amiibo_type] += 1
            except Exception as e:
                print(f"Error saving file {filepath}: {e}")
                error_count += 1
        
        # 結果報告
        print(f"\nGeneration complete!")
        print(f"Successfully generated: {success_count}")
        print(f"Errors: {error_count}")
        
        if organize_by_series and series_counts:
            print(f"\nGenerated by series:")
            for series, count in sorted(series_counts.items()):
                print(f"  {series}: {count}")
        
        print(f"\nGenerated by type:")
        for amiibo_type, count in sorted(type_counts.items()):
            print(f"  {amiibo_type}: {count}")
        
        return error_count == 0

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='Generate enhanced Amiibo .bin files from API data')
    parser.add_argument('--data-file', default='amiibo_api_data.json',
                       help='Path to Amiibo API JSON data file')
    parser.add_argument('--output-dir', default='enhanced_amiibo_bins',
                       help='Output directory for generated .bin files')
    parser.add_argument('--key-file', default='key_retail.bin',
                       help='Path to encryption key file')
    parser.add_argument('--no-series', action='store_true',
                       help='Don\'t organize files by series (put all in root directory)')
    parser.add_argument('--verify', action='store_true',
                       help='Verify generated files after creation')
    
    args = parser.parse_args()
    
    # ジェネレーターを作成
    generator = EnhancedAmiiboGenerator(args.key_file)
    
    # ファイルを生成
    organize_by_series = not args.no_series
    success = generator.generate_all_bins(args.data_file, args.output_dir, organize_by_series)
    
    if success:
        print("\n✅ All files generated successfully!")
        
        # 検証オプションが指定されている場合は検証を実行
        if args.verify:
            print("\nNote: Verification will be implemented in the next phase.")
    else:
        print("\n❌ Some files failed to generate. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()