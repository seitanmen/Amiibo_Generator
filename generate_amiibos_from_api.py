"""
Amiibo Bin Generator
Amiibo APIデータから暗号化された.binファイルを生成する
"""

import os
import json
import sys
import argparse
from typing import Dict, List, Optional, Tuple
from pathlib import Path

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

class AmiiboGenerator:
    def __init__(self, key_file="key_retail.bin"):
        self.key_file = key_file
        self.keys = None
        
    def load_keys(self) -> bool:
        """
        暗号化キーをロードする
        """
        if not os.path.exists(self.key_file):
            print(f"Error: Key file '{self.key_file}' not found")
            return False
        
        try:
            with open(self.key_file, 'rb') as f:
                key_data = f.read()
            
            # key_retail.binはcombined形式（160バイト）
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
        """
        Amiibo APIデータをロードする
        """
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
        """
        ファイル名として使用できない文字を置換する
        """
        # ファイル名として使用できない文字を置換
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # 末尾のドットとスペースを削除
        name = name.rstrip('. ')
        
        # 空の場合はデフォルト名
        if not name:
            name = "Unknown"
        
        return name
    
    def build_identification_block(self, head: str, tail: str, amiibo_type: str, series: str) -> bytes:
        """
        Amiibo Identification BlockをAPIデータから構築
        
        重要な発見：Identification Block (0x54-0x5C) は単純に Head + Tail で構成される！
        """
        try:
            # Head (4 bytes) + Tail (4 bytes) = Identification Block (8 bytes)
            head_bytes = bytes.fromhex(head)
            tail_bytes = bytes.fromhex(tail)
            
            # 確実に8バイトになるようにパディング
            if len(head_bytes) < 4:
                head_bytes = head_bytes.ljust(4, b'\x00')
            if len(tail_bytes) < 4:
                tail_bytes = tail_bytes.ljust(4, b'\x00')
            
            return head_bytes[:4] + tail_bytes[:4]
            
        except Exception as e:
            print(f"Warning: Could not build ID block: {e}")
            # デフォルト値を返す
            return b'\x00\x00\x00\x00\x01\x00\x00\x02'
    
    def apply_type_specific_init(self, dump, amiibo_type: str, series: str):
        """
        タイプ固有の初期化データを適用
        """
        # Cardタイプの初期化
        if amiibo_type == 'Card' and series == 'Animal Crossing':
            # Country Code（0x208-0x210）
            dump.data[0x208:0x210] = b'\x00' * 8
            # Write Counter（0x20C-0x20E）
            dump.data[0x20C:0x20E] = b'\x00\x00'
        
        # Figureタイプの初期化
        elif amiibo_type == 'Figure':
            # Smash Bros. AppID（0x180-0x184）
            if series == 'Super Smash Bros.':
                dump.data[0x180:0x184] = b'\x00\x10\x11\x0E'
    
    def create_amiibo_data_structure(self, head: str, tail: str, amiibo_type: str = 'Figure', series: str = 'Unknown Series') -> Optional[bytes]:
        """
        Amiiboデータ構造を作成する（テンプレートベース）
        """
        amiibo_id = head + tail
        
        # テンプレートファイルが存在する場合は使用
        # 注：どのAmiiboをベースとしても機能します（IDブロックとUIDは上書きされるため）
        template_file = "base_amiibo.bin"
        if os.path.exists(template_file):
            with open(template_file, 'rb') as f:
                template_data = f.read()
            
            # テンプレートを復号化
            template_dump = AmiiboDump(self.keys, template_data)
            template_dump.unlock()
            
            # 新しいAmiiboDumpを作成（テンプレートデータをベースに）
            new_dump = AmiiboDump(self.keys, template_dump.data, is_locked=False)
            
            # UIDを設定（NTAG215標準形式：04 + 6バイトの一意ID）
            # headとtailから一意のUIDを生成
            combined_id = head + tail
            # ハッシュ的に一意な6バイトを生成
            import hashlib
            hash_obj = hashlib.md5(combined_id.encode())
            unique_6bytes = hash_obj.digest()[:6]
            # NTAG215標準の接頭辞04 + 6バイト
            new_uid = '04' + unique_6bytes.hex()
            new_dump.uid_hex = new_uid
            
            # Amiibo Identification Blockを更新（0x54-0x5C）
            id_block = self.build_identification_block(head, tail, amiibo_type, series)
            new_dump.data[0x54:0x5C] = id_block
            
            # タイプ固有の初期化データを適用
            self.apply_type_specific_init(new_dump, amiibo_type, series)
            
            # 暗号化してロック
            new_dump.lock()
            
            return bytes(new_dump.data)
        
        print(f"Error: Template file '{template_file}' not found")
        return None
    
    def create_series_directory(self, output_dir: str, series: str) -> str:
        """
        シリーズ用のディレクトリを作成する
        """
        # シリーズ名をサニタイズ
        safe_series = self.sanitize_filename(series)
        series_dir = os.path.join(output_dir, safe_series)
        
        # ディレクトリを作成
        os.makedirs(series_dir, exist_ok=True)
        
        return series_dir
    
    def generate_bin_file(self, amiibo_info: Dict) -> Optional[bytes]:
        """
        個別のAmiibo .binファイルを生成する
        """
        try:
            head = amiibo_info.get('head', '')
            tail = amiibo_info.get('tail', '')
            amiibo_type = amiibo_info.get('type', 'Figure')
            series = amiibo_info.get('amiiboSeries', '')
            
            if not head or not tail:
                print(f"Warning: Missing head/tail for {amiibo_info.get('name', 'Unknown')}")
                return None
            
            # Amiiboデータ構造を作成
            amiibo_data = self.create_amiibo_data_structure(head, tail, amiibo_type, series)
            if amiibo_data is None:
                return None
            
            return amiibo_data
            
        except Exception as e:
            print(f"Error generating bin for {amiibo_info.get('name', 'Unknown')}: {e}")
            return None
    
    def generate_all_bins(self, data_file: str = "amiibo_api_data.json", 
                         output_dir: str = "generated_amiibo_bins",
                         organize_by_series: bool = True) -> bool:
        """
        すべてのAmiibo .binファイルを生成する
        """
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
        
        print(f"Generating {len(amiibos)} Amiibo bin files...")
        
        # 進捗バーの設定
        if tqdm:
            progress_iter = tqdm(amiibos, desc="Processing Amiibos")
        else:
            progress_iter = amiibos
        
        for i, amiibo in enumerate(progress_iter, 1):
            name = amiibo.get('name', 'Unknown')
            series = amiibo.get('amiiboSeries', 'Unknown Series')
            
            # 進捗表示（tqdm未使用時のみ）
            if not tqdm:
                print(f"[{i}/{len(amiibos)}] Processing: {name} ({series})")
            
            # .binデータ生成
            bin_data = self.generate_bin_file(amiibo)
            if bin_data is None:
                error_count += 1
                continue
            
            # 出力先ディレクトリを決定
            if organize_by_series:
                target_dir = self.create_series_directory(output_dir, series)
                # シリーズごとのカウント
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
            
            # 重複チェック - 存在する場合は上書きしないでスキップ
            if os.path.exists(filepath):
                print(f"  -> File already exists, skipping: {filename}")
                continue
            
            # ファイルを保存
            try:
                with open(filepath, 'wb') as f:
                    f.write(bin_data)
                success_count += 1
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
        
        return error_count == 0
    
    def verify_generated_files(self, output_dir: str = "generated_amiibo_bins", 
                              sample_size: int = 5) -> bool:
        """
        生成されたファイルを検証する
        """
        print(f"\n=== Verifying Generated Files ===")
        
        # 出力ディレクトリの.binファイルを検索
        bin_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.bin'):
                    bin_files.append(os.path.join(root, file))
        
        if not bin_files:
            print("No .bin files found to verify")
            return False
        
        # サンプルファイルを検証
        import random
        sample_files = random.sample(bin_files, min(sample_size, len(bin_files)))
        
        success_count = 0
        error_count = 0
        
        for i, file_path in enumerate(sample_files, 1):
            print(f"[{i}/{len(sample_files)}] Verifying: {os.path.relpath(file_path, output_dir)}")
            
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # ファイルサイズ検証
                if len(file_data) != 540:
                    print(f"  -> Error: Invalid file size {len(file_data)} (expected 540)")
                    error_count += 1
                    continue
                
                # pyamiiboで検証
                dump = AmiiboDump(self.keys, file_data)
                print(f"  -> Locked: {dump.is_locked}")
                
                if dump.is_locked:
                    dump.unlock()
                    print(f"  -> UID: {dump.uid_hex}")
                else:
                    print(f"  -> Already unlocked, UID: {dump.uid_hex}")
                
                success_count += 1
                print(f"  -> Verification successful")
                
            except Exception as e:
                print(f"  -> Error: {e}")
                error_count += 1
        
        print(f"\nVerification complete!")
        print(f"Successfully verified: {success_count}")
        print(f"Errors: {error_count}")
        
        return error_count == 0

def main():
    """
    メイン実行関数
    """
    parser = argparse.ArgumentParser(description='Generate Amiibo .bin files from API data')
    parser.add_argument('--data-file', default='amiibo_api_data.json',
                       help='Path to Amiibo API JSON data file')
    parser.add_argument('--output-dir', default='generated_amiibo_bins',
                       help='Output directory for generated .bin files')
    parser.add_argument('--key-file', default='key_retail.bin',
                       help='Path to encryption key file')
    parser.add_argument('--no-series', action='store_true',
                       help='Don\'t organize files by series (put all in root directory)')
    parser.add_argument('--verify', action='store_true',
                       help='Verify generated files after creation')
    
    args = parser.parse_args()
    
    # ジェネレーターを作成
    generator = AmiiboGenerator(args.key_file)
    
    # ファイルを生成
    organize_by_series = not args.no_series
    success = generator.generate_all_bins(args.data_file, args.output_dir, organize_by_series)
    
    if success:
        print("\n✅ All files generated successfully!")
        
        # 検証オプションが指定されている場合は検証を実行
        if args.verify:
            generator.verify_generated_files(args.output_dir)
    else:
        print("\n❌ Some files failed to generate. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()