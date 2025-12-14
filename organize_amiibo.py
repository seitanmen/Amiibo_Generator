import os
import shutil
import json
import urllib.request
import urllib.error
import argparse
import time

# AmiiboAPI URL
API_URL = "https://www.amiiboapi.com/api/amiibo/"

# Dependency check
try:
    from amiibo import AmiiboDump
    from amiibo.keys import AmiiboMasterKey
    PYAMIIBO_AVAILABLE = True
except ImportError:
    PYAMIIBO_AVAILABLE = False
    AmiiboDump = None
    AmiiboMasterKey = None

def get_amiibo_info(head_hex, tail_hex):
    """
    Query the AmiiboAPI for the given head and tail.
    """
    url = f"{API_URL}?id={head_hex}{tail_hex}"
    
    # Simple retry logic
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data.get('amiibo', None)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Amiibo not found in API
                return None
            print(f"HTTP Error {e.code} for {head_hex}{tail_hex}. Retrying...")
        except Exception as e:
            print(f"Error fetching data: {e}. Retrying...")
        
        time.sleep(1) # Be nice to the API
    return None

def sanitize_filename(name):
    """
    Remove illegal characters from filenames.
    """
    return "".join([c for c in name if c.isalnum() or c in (' ', '-', '_', '.')]).strip()

def process_files(input_dir, output_dir, copy_mode=False, keys=None, check_mode=False):
    if not os.path.exists(output_dir) and not check_mode:
        os.makedirs(output_dir)
    elif check_mode and not os.path.exists(output_dir):
        # In check mode, we still need output_dir for the report
        os.makedirs(output_dir)

    processed_count = 0
    skipped_count = 0

    print(f"Scanning '{input_dir}' for .bin files...")
    
    if check_mode:
        print("--- CHECK MODE ---")
        print("Files will NOT be moved, copied, or modified.")
        print("Scanned Amiibos will be compared against the full database.")
    
    if keys:
        print("Decryption keys loaded. Files will be processed for identification.")
    elif PYAMIIBO_AVAILABLE:
        print("Warning: 'key_retail.bin' not found or keys not loaded. Encrypting decrypted files will be SKIPPED.")
    else:
        print("Note: 'pyamiibo' not installed. Advanced processing unavailable.")

    processed_ids = set()

    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if not file.lower().endswith('.bin'):
                continue
            
            file_path = os.path.join(root, file)
            head_hex = None
            tail_hex = None
            is_decrypted_originally = False
            dump = None

            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                # Check for small files
                if len(data) < 540:
                     pass

                if keys and PYAMIIBO_AVAILABLE and AmiiboDump:
                    try:
                        dump = AmiiboDump(keys, data)
                        if dump.is_locked:
                            dump.unlock() # Decrypt to read ID
                            is_decrypted_originally = False
                        else:
                            is_decrypted_originally = True
                        
                        # Amiibo ID is at 0x54 (84) in decrypted data
                        amiibo_id_bytes = dump.data[84:92]
                        head_hex = amiibo_id_bytes[:4].hex()
                        tail_hex = amiibo_id_bytes[4:].hex()
                    except Exception as e:
                        if not check_mode: # Less verbose in check mode? or same.
                             print(f"Decryption/Parsing failed for {file}: {e}. Trying raw read...")
                        if len(data) >= 92:
                            head_hex = data[84:88].hex()
                            tail_hex = data[88:92].hex()
                else:
                    # Raw read (No keys)
                    if len(data) >= 92:
                        head_hex = data[84:88].hex()
                        tail_hex = data[88:92].hex()
                
                if not head_hex or not tail_hex:
                    if not check_mode:
                        print(f"Skipping {file}: Could not extract ID.")
                    skipped_count += 1
                    continue

                # Check for duplicates in current batch
                unique_id = f"{head_hex}{tail_hex}"
                if unique_id in processed_ids:
                    # In check mode, we just ignore duplicates silently or log lightly
                    if not check_mode:
                        print(f"[Duplicate] Skipping {file} (ID: {unique_id}) - Already processed.")
                    skipped_count += 1
                    continue
                
                # If check_mode, we mainly care about the ID, but getting name is nice for log
                if check_mode:
                     print(f"[Found] {file} (ID: {unique_id})")
                     processed_ids.add(unique_id)
                     processed_count += 1
                     continue

                # --- Normal Organization Mode Below ---

                # Query API
                amiibo_info = get_amiibo_info(head_hex, tail_hex)
                
                if amiibo_info:
                    if isinstance(amiibo_info, list):
                        amiibo_info = amiibo_info[0]

                    series = sanitize_filename(amiibo_info.get('amiiboSeries', 'Unknown Series'))
                    name = sanitize_filename(amiibo_info.get('name', 'Unknown Amiibo'))
                    
                    dest_dir = os.path.join(output_dir, series)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    
                    # Logic: If it was decrypted, we encrypt it and add suffix.
                    # If it was encrypted, we save it as is (keep original name format).
                    
                    filename_suffix = ""
                    should_write_dump = False
                    
                    if is_decrypted_originally and keys and PYAMIIBO_AVAILABLE and dump:
                        # Re-encrypt for saving
                        dump.lock()
                        filename_suffix = "_(Encrypted)"
                        should_write_dump = True
                    
                    new_filename = f"{name}{filename_suffix}.bin"
                    dest_path = os.path.join(dest_dir, new_filename)
                    
                    # Handle duplicates
                    counter = 1
                    base_name = f"{name}{filename_suffix}"
                    while os.path.exists(dest_path):
                        new_filename = f"{base_name}_{counter}.bin"
                        dest_path = os.path.join(dest_dir, new_filename)
                        counter += 1
                    
                    # Perform Save
                    if should_write_dump and dump:
                        with open(dest_path, 'wb') as out_f:
                            out_f.write(dump.data)
                        if not copy_mode:
                            os.remove(file_path) # Delete original if moving
                        action = "Converted & Saved"
                    else:
                        if copy_mode:
                            shutil.copy2(file_path, dest_path)
                            action = "Copied"
                        else:
                            shutil.move(file_path, dest_path)
                            action = "Moved"
                        
                    print(f"[{action}] {file} -> {series}/{new_filename}")
                    processed_count += 1
                    processed_ids.add(unique_id)
                else:
                    print(f"[Unknown] Could not identify {file} (ID: {head_hex}{tail_hex})")
                    unique_id = f"{head_hex}{tail_hex}"
                    unknown_dir = os.path.join(output_dir, "Unknown")
                    if not os.path.exists(unknown_dir):
                        os.makedirs(unknown_dir)
                    
                    # If we have a decrypted unknown file, do we encrypt it? 
                    # User request: "decrypted files... converted to encrypted".
                    # Let's apply it to unknowns too for consistency if we have keys.
                    
                    final_filename = file
                    should_write_unknown = False
                    
                    if is_decrypted_originally and keys and PYAMIIBO_AVAILABLE and dump:
                        dump.lock()
                        root_name, ext = os.path.splitext(file)
                        final_filename = f"{root_name}_(Encrypted){ext}"
                        should_write_unknown = True
                        
                    dest_path = os.path.join(unknown_dir, final_filename)
                    
                    if should_write_unknown and dump:
                        with open(dest_path, 'wb') as out_f:
                            out_f.write(dump.data)
                        if not copy_mode:
                            os.remove(file_path)
                    else: 
                        if copy_mode:
                            shutil.copy2(file_path, dest_path)
                        else:
                            shutil.move(file_path, dest_path)
                            
                    skipped_count += 1
                    processed_ids.add(unique_id)

            except Exception as e:
                print(f"Error processing {file}: {e}")
                skipped_count += 1

    print(f"\nProcessing Complete.")
    if check_mode:
        print(f"Found {processed_count} unique Amiibos.")
    else:
        print(f"Successfully organized: {processed_count}")
        print(f"Skipped/Unknown: {skipped_count}")

    # Generate Missing Report
    check_for_missing_amiibos(processed_ids, output_dir)

def check_for_missing_amiibos(found_ids, output_dir):
    print("\nfetching full Amiibo list from API to check for missing files...")
    try:
        req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                all_data = json.loads(response.read().decode())
                all_amiibos = all_data.get('amiibo', [])
                
                missing = []
                # Filter out card types if user only cares about figures? 
                # For now, keep all as user dataset might include cards.
                
                for amiibo in all_amiibos:
                    # IDs in API are separate head/tail, we combine them
                    head = amiibo.get('head', '')
                    tail = amiibo.get('tail', '')
                    full_id = f"{head}{tail}"
                    
                    if full_id not in found_ids:
                        missing.append(amiibo)
                
                # Sort by series then name
                missing.sort(key=lambda x: (x.get('amiiboSeries', ''), x.get('name', '')))
                
                report_path = os.path.join(output_dir, "missing_amiibo_report.txt")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(f"Missing Amiibo Report - Generated on {time.ctime()}\n")
                    f.write(f"Scanned {len(found_ids)} unique Amiibos.\n")
                    f.write(f"Total Missing: {len(missing)}\n")
                    f.write("="*60 + "\n\n")
                    
                    current_series = None
                    for m in missing:
                        series = m.get('amiiboSeries', 'Unknown')
                        name = m.get('name', 'Unknown')
                        adb_id = f"{m.get('head')}{m.get('tail')}"
                        am_type = m.get('type', 'Unknown')
                        
                        if series != current_series:
                            f.write(f"\n## {series}\n")
                            current_series = series
                        
                        f.write(f"- [{am_type}] {name} (ID: {adb_id})\n")
                
                print(f"Missing Amiibo report generated at: {report_path}")
                print(f"Total missing entries: {len(missing)}")
            else:
                print("Failed to fetch full Amiibo list for report.")
    except Exception as e:
        print(f"Error generating missing report: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize Amiibo BIN files using AmiiboAPI.")
    parser.add_argument("input_dir", help="Directory containing Amiibo BIN files to organize")
    parser.add_argument("output_dir", help="Directory to place organized files (or report in check mode)")
    parser.add_argument("--copy", action="store_true", help="Copy files instead of moving them")
    parser.add_argument("--key-file", default="key_retail.bin", help="Path to key_retail.bin (default: key_retail.bin in current dir)")
    parser.add_argument("--check", action="store_true", help="Check mode: Scan files and generate report WITHOUT moving/modifying files.")

    args = parser.parse_args()
    
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        exit(1)

    keys = None
    if PYAMIIBO_AVAILABLE and AmiiboMasterKey:
        key_path = args.key_file
        if os.path.exists(key_path):
            try:
                with open(key_path, 'rb') as f:
                    key_data = f.read()
                keys = AmiiboMasterKey.from_combined_bin(key_data)
                print("Decryption keys loaded successfully.")
            except Exception as e:
                print(f"Warning: Failed to load keys: {e}. Proceeding with raw read.")
                keys = None
        else:
             # Only warn if they specifically pointed to a missing file, or if default missing but library present
             if key_path != "key_retail.bin":
                 print(f"Warning: Key file '{key_path}' not found.")
    
    try:
        process_files(args.input_dir, args.output_dir, args.copy, keys, args.check)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
