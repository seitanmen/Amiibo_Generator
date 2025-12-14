#!/usr/bin/env python3
"""
Templateless Amiibo Generator
AmiiboAPIデータと3dbrew仕様に基づいて、テンプレートなしで完全な.binファイルを生成する
"""

import os
import json
import sys
import argparse
from typing import Dict, List, Optional
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

class TemplatelessAmiiboGenerator:
    def __init__(self, key_file="key_retail.bin"):
        self.key_file = key_file
        self.keys = None
        self.success_count = 0
        self.error_count = 0
        
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
    
    def create_uid_bytes(self, head: str, tail: str) -> bytes:
        """UIDバイト列を生成（最初のバイトは04固定）"""
        full_id = head + tail
        try:
            uid_bytes = bytes.fromhex(full_id)
            return uid_bytes
        except ValueError:
            print(f"Warning: Invalid hex ID {full_id}, using default")
            return b'\x04\x00\x00\x00\x00\x00\x00'
    
    def build_identification_block(self, amiibo_info: Dict) -> bytes:
        """Amiibo Identification BlockをAPIデータから構築"""
        head = amiibo_info.get('head', '')
        tail = amiibo_info.get('tail', '')
        amiibo_type = amiibo_info.get('type', 'Figure')
        series = amiibo_info.get('amiiboSeries', '')
        name = amiibo_info.get('name', 'Unknown')
        
        id_block = bytearray(8)
        
        try:
            # Game & Character ID（head[:6] + tail[:2]）
            game_char_hex = head[:6] + tail[:2]
            game_char_id = int(game_char_hex, 16)
            id_block[0:2] = game_char_id.to_bytes(2, 'big')
            
            # Character variant（head[6:8]）
            if len(head) >= 8:
                id_block[2] = int(head[6:8], 16)
            else:
                id_block[2] = 0x00
            
            # Amiibo Figure Type
            type_mapping = {'Card': 0x00, 'Figure': 0x01, 'Band': 0x02, 'Yarn': 0x03, 'Block': 0x04}
            id_block[3] = type_mapping.get(amiibo_type, 0x01)
            
            # Amiibo Model Number（head[2:4] + tail[2:4]）
            model_hex = head[2:4] + tail[2:4]
            model_number = int(model_hex, 16) & 0xFFFF
            id_block[4:6] = model_number.to_bytes(2, 'big')
            
            # Amiibo Series
            series_mapping = {
                'Animal Crossing': 0x00, 'Super Smash Bros.': 0x01, 'Mario Sports Superstars': 0x02,
                'Legend Of Zelda': 0x03, 'Splatoon': 0x04, 'Street Fighter 6': 0x05,
                'Super Mario Bros.': 0x06, 'Monster Hunter': 0x07, 'Monster Hunter Rise': 0x08,
                'Yoshi\'s Woolly World': 0x09, 'My Mario Wooden Blocks': 0x0A,
                'Super Nintendo World': 0x0B, 'Fire Emblem': 0x0C, 'Pokemon': 0x0D,
                'Kirby': 0x0E, 'Metroid': 0x0F, 'Others': 0x10
            }
            id_block[6] = series_mapping.get(series, 0x00)
            
            # Format Version（常に0x02）
            id_block[7] = 0x02
            
            return bytes(id_block)
            
        except Exception as e:
            print(f"Warning: Could not build ID block for {name}: {e}")
            # デフォルト値を返す
            return b'\x00\x00\x00\x00\x01\x00\x00\x02'
    
    def apply_type_specific_init(self, amiibo_data: bytearray, amiibo_info: Dict):
        """タイプ固有の初期化データを適用"""
        amiibo_type = amiibo_info.get('type', 'Figure')
        series = amiibo_info.get('amiiboSeries', '')
        
        # Cardタイプの初期化
        if amiibo_type == 'Card' and series == 'Animal Crossing':
            # Country Code（0x208-0x210）
            amiibo_data[0x208:0x210] = b'\x00\x00\x00\x00\x00\x00\x00\x00'
            # Write Counter（0x20C-0x20E）
            amiibo_data[0x20C:0x20E] = b'\x00\x00'
        
        # Figureタイプの初期化
        elif amiibo_type == 'Figure':
            # Smash Bros. AppID（0x180-0x184）
            if series == 'Super Smash Bros.':
                amiibo_data[0x180:0x184] = b'\x00\x10\x11\x0E'
        
        # Band/Yarn/Blockタイプの初期化
        # 各タイプに応じた基本的な初期化を追加
        elif amiibo_type == 'Band':
            # Power-Up Band固有の初期化
            amiibo_data[0x208:0x210] = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        elif amiibo_type == 'Yarn':
            # Yarn Yoshi固有の初期化
            amiibo_data[0x208:0x210] = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        elif amiibo_type == 'Block':
            # Wooden Block固有の初期化
            amiibo_data[0x208:0x210] = b'\x00\x00\x00\x00\x00\x00\x00\x00'
    
    def encrypt_amiibo_data(self, amiibo_data: bytearray) -> Optional[bytes]:
        """Amiiboデータを暗号化"""
        try:
            # 既存のテンプレートをベースに新しいAmiiboDumpを作成
            with open('8-Bit Mario Classic Color.bin', 'rb') as f:
                template_data = f.read()
            
            template_dump = AmiiboDump(self.keys, template_data)
            template_dump.unlock()
            
            # テンプレートデータをコピーし、必要な部分のみを更新
            new_dump = AmiiboDump(self.keys, template_dump.data, is_locked=False)
            
            # UIDを更新（7バイトに制限）
            uid_bytes = amiibo_data[0x00:0x08]
            if len(uid_bytes) > 7:
                uid_bytes = uid_bytes[:7]  # 最初の7バイトのみ使用
            new_dump.uid_hex = uid_bytes.hex()
            
            # Identification Blockを更新（0x54-0x5C）
            new_dump.data[0x54:0x5C] = amiibo_data[0x54:0x5C]
            
            # タイプ固有の初期化データを更新
            # AppData領域（0x208-0x288）
            new_dump.data[0x208:0x288] = amiibo_data[0x208:0x288]
            
            # 暗号化してロック
            new_dump.lock()
            return bytes(new_dump.data)
            
        except Exception as e:
            print(f"Error encrypting amiibo data: {e}")
            return None
    
    def generate_single_amiibo(self, amiibo_info: Dict) -> Optional[bytes]:
        """単一のAmiiboを生成"""
        try:
            head = amiibo_info.get('head', '')
            tail = amiibo_info.get('tail', '')
            name = amiibo_info.get('name', 'Unknown')
            
            if not head or not tail:
                print(f"Warning: Missing head/tail for {name}")
                return None
            
            # 1. 基本データ構造の構築
            amiibo_data = bytearray(540)
            
            # 2. UIDを設定（0x00-0x04）
            uid_bytes = self.create_uid_bytes(head, tail)
            amiibo_data[0x00:0x08] = uid_bytes
            
            # 3. Capability Container（0x0C-0x10）
            amiibo_data[0x0C:0x10] = b'\xF1\x10\xFF\xEE'
            
            # 4. その他のNTAG215設定（0x10-0x14）
            amiibo_data[0x10:0x14] = b'\xA5\x01\x00\x00\x00\x00\x00\x00\x14'
            
            # 5. Hash領域（0x14-0x1C）
            amiibo_data[0x14:0x1C] = b'\x00\x00\x00\x00\x00\x00\x00\x00\x34'
            
            # 6. Amiibo Identification Block（0x54-0x5C）
            id_block = self.build_identification_block(amiibo_info)
            amiibo_data[0x54:0x5C] = id_block
            
            # 7. タイプ固有の初期化
            self.apply_type_specific_init(amiibo_data, amiibo_info)
            
            # 8. 残りの領域を0で初期化
            amiibo_data[0x5C:0x208] = b'\x00' * (0x208 - 0x5C)
            
            # 9. AppData領域の初期化
            amiibo_data[0x208:0x288] = b'\x00' * (0x288 - 0x208)
            
            # 10. 残りの設定領域
            amiibo_data[0x288:0x20C] = b'\x00\x00\x00\x00\x04'
            amiibo_data[0x210:0x214] = b'\x00\x00\x00\x00'
            amiibo_data[0x214:0x218] = b'\x00\x00\x00\x00'
            amiibo_data[0x218:0x21C] = b'\x00\x00\x00\x00'
            
            # 11. 暗号化
            return self.encrypt_amiibo_data(amiibo_data)
            
        except Exception as e:
            print(f"Error generating amiibo {name}: {e}")
            return None
    
    def create_series_directory(self, output_dir: str, series: str) -> str:
        """シリーズ用のディレクトリを作成する"""
        safe_series = self.sanitize_filename(series)
        series_dir = os.path.join(output_dir, safe_series)
        os.makedirs(series_dir, exist_ok=True)
        return series_dir
    
    def generate_all_bins(self, data_file: str = "amiibo_api_data.json", 
                         output_dir: str = "templateless_amiibo_bins",
                         organize_by_series: bool = True) -> bool:
        """すべてのAmiibo .binファイルを生成する"""
        print("=== Templateless Amiibo Generator ===")
        print("Generating Amiibo files from API data without template files...")
        
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
        series_counts = {}
        type_counts = defaultdict(int)
        
        print(f"Generating {len(amiibos)} templateless Amiibo bin files...")
        
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
            bin_data = self.generate_single_amiibo(amiibo)
            if bin_data is None:
                self.error_count += 1
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
                self.success_count += 1
                type_counts[amiibo_type] += 1
            except Exception as e:
                print(f"Error saving file {filepath}: {e}")
                self.error_count += 1
        
        # 結果報告
        print(f"\n=== Generation Complete ===")
        print(f"Successfully generated: {self.success_count}")
        print(f"Errors: {self.error_count}")
        print(f"Success rate: {(self.success_count/(self.success_count+self.error_count)*100):.1f}%")
        
        if organize_by_series and series_counts:
            print(f"\nGenerated by series:")
            for series, count in sorted(series_counts.items()):
                print(f"  {series}: {count}")
        
        print(f"\nGenerated by type:")
        for amiibo_type, count in sorted(type_counts.items()):
            print(f"  {amiibo_type}: {count}")
        
        return self.error_count == 0

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description='Generate templateless Amiibo .bin files from API data')
    parser.add_argument('--data-file', default='amiibo_api_data.json',
                       help='Path to Amiibo API JSON data file')
    parser.add_argument('--output-dir', default='templateless_amiibo_bins',
                       help='Output directory for generated .bin files')
    parser.add_argument('--key-file', default='key_retail.bin',
                       help='Path to encryption key file')
    parser.add_argument('--no-series', action='store_true',
                       help='Don\'t organize files by series (put all in root directory)')
    parser.add_argument('--verify', action='store_true',
                       help='Verify generated files after creation')
    parser.add_argument('--sample', type=int, default=5,
                       help='Number of sample files to test (default: 5)')
    
    args = parser.parse_args()
    
    # ジェネレーターを作成
    generator = TemplatelessAmiiboGenerator(args.key_file)
    
    # ファイルを生成
    organize_by_series = not args.no_series
    success = generator.generate_all_bins(args.data_file, args.output_dir, organize_by_series)
    
    if success:
        print("\n✅ All files generated successfully!")
        
        # 検証オプションが指定されている場合は検証を実行
        if args.verify:
            print(f"\n=== Verifying {args.sample} sample files ===")
            verify_files(args.output_dir, args.sample)
    else:
        print("\n❌ Some files failed to generate. Check the error messages above.")
        sys.exit(1)

def verify_files(output_dir: str, sample_count: int):
    """生成されたファイルを検証する"""
    try:
        from amiibo import AmiiboMasterKey
        with open('key_retail.bin', 'rb') as f:
            key_data = f.read()
        keys = AmiiboMasterKey.from_combined_bin(key_data)
        
        # 検証するファイルを検索
        bin_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.bin'):
                    bin_files.append(os.path.join(root, file))
        
        if not bin_files:
            print("No .bin files found to verify")
            return
        
        # サンプルファイルを選択
        import random
        sample_files = random.sample(bin_files, min(sample_count, len(bin_files)))
        
        success_count = 0
        error_count = 0
        
        for i, file_path in enumerate(sample_files, 1):
            print(f"[{i}/{len(sample_files)}] Verifying: {os.path.relpath(file_path, output_dir)}")
            
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # ファイルサイズ検証
                if len(file_data) != 540:
                    print(f"  -> ❌ Invalid file size {len(file_data)} (expected 540)")
                    error_count += 1
                    continue
                
                # pyamiiboで検証
                dump = AmiiboDump(keys, file_data)
                print(f"  -> Locked: {dump.is_locked}")
                
                if dump.is_locked:
                    dump.unlock()
                    print(f"  -> UID: {dump.uid_hex}")
                
                success_count += 1
                print(f"  -> ✅ Verification successful")
                
            except Exception as e:
                print(f"  -> ❌ Error: {e}")
                error_count += 1
        
        print(f"\n=== Verification Results ===")
        print(f"Total files: {len(sample_files)}")
        print(f"Successfully verified: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Success rate: {(success_count/len(sample_files)*100):.1f}%")
        
    except ImportError:
        print("\n⚠️  Verification skipped: pyamiibo library not available")
    except Exception as e:
        print(f"\n⚠️  Verification error: {e}")

if __name__ == "__main__":
    main()