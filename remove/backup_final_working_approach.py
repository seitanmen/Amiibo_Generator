#!/usr/bin/env python3
"""
Final working Amiibo generation using correct pyamiibo approach
"""

import os
from amiibo import AmiiboDump, AmiiboMasterKey

def final_working_approach():
    """正しいpyamiiboアプローチを使用したAmiibo生成"""
    
    print("=== Final Working Amiibo Generation ===")
    
    # キーのロード
    key_file = "key_retail.bin"
    with open(key_file, 'rb') as f:
        key_data = f.read()
    
    keys = AmiiboMasterKey.from_combined_bin(key_data)
    print("Keys loaded")
    
    try:
        # 既存ファイルを復号化してテンプレートとして使用
        existing_file = "8-Bit Mario Classic Color.bin"
        with open(existing_file, 'rb') as f:
            existing_data = f.read()
        
        # 既存ファイルからDumpを作成（ロック状態）
        existing_dump = AmiiboDump(keys, existing_data, is_locked=True)
        print("Existing dump created")
        
        # 復号化
        existing_dump.unlock()
        print("Existing dump unlocked")
        print(f"Template UID: {existing_dump.uid_hex}")
        print(f"Template UID raw: {existing_dump._uid_raw.hex()}")
        
        # 新しいDumpを作成（復号化されたテンプレートデータから、ロックされていない状態で）
        new_dump = AmiiboDump(keys, existing_dump.data, is_locked=False)
        print("New dump created from template (unlocked)")
        
        # 新しいUIDを設定（SandyのID）
        # 既存のAmiiboの最初のバイトを維持し、残りを変更
        existing_first_byte = existing_dump._uid_raw[0:1].hex()
        new_uid_suffix = "38000103000502"  # 0438000103000502から最初のバイトを除いた残り
        new_uid_7bytes = existing_first_byte + new_uid_suffix[:12]  # 最初のバイト + 新しいUIDの残り6バイト
        new_dump.uid_hex = new_uid_7bytes
        print(f"New UID set: {new_dump.uid_hex}")
        
        # ロック
        new_dump.lock()
        print("New dump locked")
        
        # 保存
        output_file = "working_sandy.bin"
        with open(output_file, 'wb') as f:
            f.write(new_dump.data)
        
        print(f"Saved to {output_file} ({len(new_dump.data)} bytes)")
        
        # 検証
        with open(output_file, 'rb') as f:
            verify_data = f.read()
        
        verify_dump = AmiiboDump(keys, verify_data, is_locked=True)
        print(f"Verification - is locked: {verify_dump.is_locked}")
        
        if verify_dump.is_locked:
            verify_dump.unlock()
            print("Verification dump unlocked")
        
        print(f"Verification UID: {verify_dump.uid_hex}")
        print("Success! Amiibo generated correctly.")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = final_working_approach()
    exit(0 if success else 1)