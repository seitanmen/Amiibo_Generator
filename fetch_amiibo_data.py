#!/usr/bin/env python3
"""
Amiibo API Data Fetcher
AmiiboAPIから完全なデータセットを取得してローカルJSONファイルとして保存する
"""

import json
import urllib.request
import urllib.error
import time
from typing import Dict, List, Optional

API_URL = "https://www.amiiboapi.com/api/amiibo/"

def fetch_amiibo_data() -> Optional[Dict]:
    """
    AmiiboAPIから完全なデータセットを取得する
    """
    try:
        print("Fetching Amiibo database from API...")
        req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"Successfully fetched data with {len(data.get('amiibo', []))} Amiibos")
                return data
            else:
                print(f"HTTP Error: {response.status}")
                return None
                
    except urllib.error.URLError as e:
        print(f"Network Error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return None

def save_amiibo_data(data: Dict, filename: str = "amiibo_api_data.json") -> bool:
    """
    AmiiboデータをJSONファイルとして保存する
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

def validate_amiibo_data(data: Dict) -> bool:
    """
    取得したAmiiboデータの構造を検証する
    """
    if not isinstance(data, dict):
        print("Invalid data format: expected dictionary")
        return False
    
    if 'amiibo' not in data:
        print("Invalid data format: missing 'amiibo' key")
        return False
    
    amiibos = data['amiibo']
    if not isinstance(amiibos, list):
        print("Invalid data format: 'amiibo' should be a list")
        return False
    
    if len(amiibos) == 0:
        print("Warning: No Amiibo data found")
        return False
    
    # 最初のAmiiboエントリの構造を確認
    sample = amiibos[0]
    required_fields = ['name', 'head', 'tail', 'amiiboSeries', 'character', 'type']
    
    for field in required_fields:
        if field not in sample:
            print(f"Warning: Missing required field '{field}' in sample data")
    
    print(f"Data validation passed: {len(amiibos)} Amiibos found")
    return True

def main():
    """
    メイン実行関数
    """
    print("=== Amiibo API Data Fetcher ===")
    
    # データ取得
    data = fetch_amiibo_data()
    if data is None:
        print("Failed to fetch Amiibo data")
        return False
    
    # データ検証
    if not validate_amiibo_data(data):
        print("Data validation failed")
        return False
    
    # データ保存
    if save_amiibo_data(data):
        print("Successfully fetched and saved Amiibo data")
        return True
    else:
        print("Failed to save Amiibo data")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)