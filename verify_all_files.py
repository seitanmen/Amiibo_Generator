#!/usr/bin/env python3
"""
Verify All Generated Amiibo Files
生成されたすべてのAmiiboファイルを検証する
"""

import os
import sys
from typing import List

# pyamiiboライブラリのインポート
try:
    from amiibo import AmiiboDump, AmiiboMasterKey
except ImportError:
    print("Error: pyamiibo library not found. Install with: pip install pyamiibo")
    sys.exit(1)

def load_keys(key_file: str = "key_retail.bin"):
    """暗号化キーをロードする"""
    if not os.path.exists(key_file):
        print(f"Error: Key file '{key_file}' not found")
        return None
    
    try:
        with open(key_file, 'rb') as f:
            key_data = f.read()
        
        if len(key_data) == 160:
            return AmiiboMasterKey.from_combined_bin(key_data)
        else:
            print(f"Error: Invalid key file size. Expected 160 bytes, got {len(key_data)}")
            return None
    except Exception as e:
        print(f"Error loading keys: {e}")
        return None

def find_bin_files(output_dir: str) -> List[str]:
    """すべての.binファイルを検索する"""
    bin_files = []
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith('.bin'):
                bin_files.append(os.path.join(root, file))
    return bin_files

def verify_file(file_path: str, keys) -> tuple[bool, str]:
    """個別のファイルを検証する"""
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # ファイルサイズ検証
        if len(file_data) != 540:
            return False, f"Invalid file size {len(file_data)} (expected 540)"
        
        # pyamiiboで検証
        dump = AmiiboDump(keys, file_data)
        
        if dump.is_locked:
            dump.unlock()
            uid = dump.uid_hex
        else:
            uid = dump.uid_hex
        
        return True, f"UID: {uid}"
        
    except Exception as e:
        return False, str(e)

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify all generated Amiibo .bin files')
    parser.add_argument('--output-dir', default='generated_amiibo_bins',
                       help='Output directory containing .bin files')
    parser.add_argument('--key-file', default='key_retail.bin',
                       help='Path to encryption key file')
    
    args = parser.parse_args()
    
    # キーをロード
    print("Loading encryption keys...")
    keys = load_keys(args.key_file)
    if keys is None:
        sys.exit(1)
    
    # すべての.binファイルを検索
    print(f"Searching for .bin files in {args.output_dir}...")
    bin_files = find_bin_files(args.output_dir)
    
    if not bin_files:
        print("No .bin files found to verify")
        sys.exit(1)
    
    print(f"Found {len(bin_files)} .bin files")
    print("\n=== Verifying All Files ===\n")
    
    # 全ファイルを検証
    success_count = 0
    error_count = 0
    error_files = []
    
    for i, file_path in enumerate(bin_files, 1):
        relative_path = os.path.relpath(file_path, args.output_dir)
        print(f"[{i}/{len(bin_files)}] {relative_path}", end=" ... ")
        
        success, message = verify_file(file_path, keys)
        
        if success:
            print(f"✅ OK ({message})")
            success_count += 1
        else:
            print(f"❌ ERROR ({message})")
            error_count += 1
            error_files.append((relative_path, message))
    
    # 結果報告
    print(f"\n=== Verification Results ===")
    print(f"Total files: {len(bin_files)}")
    print(f"Successfully verified: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Success rate: {(success_count/len(bin_files)*100):.1f}%")
    
    if error_files:
        print(f"\n=== Error Details ===")
        for file_path, error in error_files:
            print(f"❌ {file_path}: {error}")
    
    # 終了コード
    if error_count > 0:
        print(f"\n⚠️  {error_count} files failed verification")
        sys.exit(1)
    else:
        print(f"\n✅ All files verified successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()