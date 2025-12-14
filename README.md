# Amiibo Converter - 使い方ガイド

## 📋 概要

このプロジェクトは、AmiiboAPIから取得したデータを使用して、暗号化されたAmiibo `.bin`ファイルを生成するツールです。NTAG215形式（540バイト）のAmiiboファイルを、テンプレートファイルをベースにして生成します。

## 🚀 必要なファイル

### 実行に必要なファイル
- `key_retail.bin` - Amiiboの暗号化キー（160バイト）
- `base_amiibo.bin` - ベース用Amiiboファイル（540バイト）
- `amiibo_api_data.json` - AmiiboAPIから取得したデータ（932件のAmiibo情報）

**📝 ベースAmiiboについて**:

- `base_amiibo.bin` はAmiibo生成のテンプレートとして使用されます
- **どのAmiiboをベースとしても機能します**（IDブロックとUIDはAPIデータをもとに上書きされるため）
- 540バイトのNTAG215形式のAmiiboファイル（任意のデータ）
- ご自身でダンプした`8-Bit Mario Classic Color.bin（どのAmiiboダンプでも可）`などを`base_amiibo.bin` にリネームしてください

### ツール
- `generate_amiibos_from_api.py` - メインジェネレーター
- `fetch_amiibo_data.py` - APIデータ取得ツール
- `organize_amiibo.py` - ファイル整理ツール
- `verify_all_files.py` - 生成ファイル検証ツール

## 🚀 セットアップ

### 1. 依存関係のインストール

```bash
# 必要なPythonライブラリをインストール
pip install pyamiibo tqdm
```

### 2. ファイルの確認

以下のファイルを用意して下さい：

```bash
key_retail.bin
```
```bash
base_amiibo.bin
```

## 🎯 使い方

### 基本的な使い方

#### 1. APIデータの取得（初回のみ）

```bash
python3 fetch_amiibo_data.py
```

これにより、`https://www.amiiboapi.com/api/amiibo/` から最新のAmiiboデータを取得し、`amiibo_api_data.json` を作成します。

#### 2. Amiiboファイルの一括生成

```bash
# 基本生成（シリーズ別に整理）
python3 generate_amiibos_from_api.py

# カスタマイズオプション
python3 generate_amiibos_from_api.py \
    --output-dir my_amiibo_collection \
    --no-series \
    --verify
```

#### 3. 生成ファイルの検証

```bash
# すべてのファイルを検証
python3 verify_all_files.py --output-dir generated_amiibo_bins

# サンプル数を指定して検証
python3 verify_all_files.py --output-dir generated_amiibo_bins --sample 10
```

### 4. ファイルの整理

```bash
# 生成されたファイルを整理
python3 organize_amiibo.py --source-dir generated_amiibo_bins --target-dir organized_amiibo
```

## 📝 コマンドラインオプション

### generate_amiibos_from_api.py

```bash
python3 generate_amiibos_from_api.py [オプション]

オプション:
  --data-file FILE     APIデータファイルのパス（デフォルト: amiibo_api_data.json）
  --output-dir DIR     出力ディレクトリ（デフォルト: generated_amiibo_bins）
  --key-file FILE       暗号化キーファイルのパス（デフォルト: key_retail.bin）
  --no-series           シリーズ別整理を無効化（すべてルートディレクトリに保存）
  --verify              生成後にファイル検証を実行
  --help                ヘルプを表示
```

### fetch_amiibo_data.py

```bash
python3 fetch_amiibo_data.py [オプション]

オプション:
  --output-file FILE    出力ファイル名（デフォルト: amiibo_api_data.json）
  --url URL            APIのURL（デフォルト: https://www.amiiboapi.com/api/amiibo/）
  --help                ヘルプを表示
```

### verify_all_files.py

```bash
python3 verify_all_files.py [オプション]

オプション:
  --output-dir DIR      検証対象ディレクトリ（デフォルト: generated_amiibo_bins）
  --key-file FILE        暗号化キーファイル（デフォルト: key_retail.bin）
  --sample NUMBER        検証するサンプル数（デフォルト: 5）
  --help                ヘルプを表示
```

### organize_amiibo.py

```bash
python3 organize_amiibo.py [オプション]

オプション:
  --source-dir DIR      元ディレクトリ（デフォルト: generated_amiibo_bins）
  --target-dir DIR      整理先ディレクトリ（デフォルト: organized_amiibo）
  --help                ヘルプを表示
```

## 📁 生成されるファイル構造

### 基本的な出力構造

```
generated_amiibo_bins/
├── Animal Crossing/
│   ├── Isabelle_0181000100440502.bin
│   ├── Tom Nook_01960000024e0502.bin
│   └── ...
├── Super Smash Bros./
│   ├── Mario_0005000000140002.bin
│   ├── Link_01000000034b0902.bin
│   └── ...
├── Mario Sports Superstars/
│   ├── Baby Mario - Baseball_09cc020102a60e02.bin
│   └── ...
├── Street Fighter 6/
│   ├── Ryu_34c0000104a81d02.bin
│   └── ...
└── [他のシリーズ...]
```

### ファイル名の形式

生成されるファイル名は以下の形式です：
```
[Amiibo名]_[AmiiboID].bin
```

例：`Isabelle_0181000100440502.bin`

## 🔧 技術仕様

### 対応しているAmiiboタイプ

- **Card** - Amiiboカード（674種類）
- **Figure** - Amiiboフィギュア（240種類）
- **Band** - Amiiboバンド（9種類）
- **Yarn** - Amiiboヤーン（5種類）
- **Block** - Amiiboブロック（4種類）

### 生成されるファイルの仕様

- **ファイルサイズ**: 540バイト（NTAG215標準）
- **暗号化方式**: pyamiiboライブラリを使用
- **UID形式**: 7バイトUID（最初のバイトは04固定）
- **データ構造**: 3dbrewを参照
- **フォーマット**: v2　（v3には現在対応していません。）

## 📊 サポートされているAmiibo

### 主要なシリーズ

- **Animal Crossing** - 525種類
- **Super Smash Bros.** - 96種類
- **Mario Sports Superstars** - 90種類
- **Street Fighter 6** - 63種類
- **Legend Of Zelda** - 26種類

### 合計

**932種類**のAmiiboファイルを生成可能

## ⚠️ 注意事項

### 重要な注意点

1. **キーファイル**: `key_retail.bin`は任天堂の知的財産です。適法的に取得してください。
2. **テンプレートファイル**: `8-Bit Mario Classic Color.bin`は、正規のAmiiboファイルを使用してください。
3. **個人的利用**: 生成したファイルは個人的利用の範囲内でご使用ください。
4. **法的遵守**: 各国の著作権法を遵守してご使用ください。

### 技術的な制限

- 現在の実装では、すべてのAmiiboが同じテンプレート（base_amiibo.bin）をベースに生成されます
- Amiibo固有のゲームデータ（AppData）は初期化された状態です
- 一部のAmiiboでは、ゲーム固有の設定が必要な場合があります

## 🐛 トラブルシューティング

### よくある問題と解決策

#### 1. 「Key file not found」エラー

**原因**: `key_retail.bin` ファイルが存在しない

**解決策**:

```bash
# ファイルの存在を確認
ls -la key_retail.bin

# サイズを確認（160バイトであること）
wc -c key_retail.bin
```

#### 2. 「Template file not found」エラー

**原因**: `base_amiibo.bin` ファイルが存在しない

**解決策**: 

```bash
# ファイルの存在を確認
ls -la base_amiibo.bin

# サイズを確認（540バイトであること）
wc -c base_amiibo.bin
```


#### 3. 「pyamiibo library not found」エラー

**原因**: pyamiiboライブラリがインストールされていない

**解決策**: 

```bash
pip install pyamiibo
```

#### 4. 生成ファイルの検証エラー

**原因**: 生成されたファイルが破損しているか、暗号化に問題がある

**解決策**: 

```bash
# 検証ツールで詳細を確認
python3 verify_all_files.py --sample 5

# ファイルを再生成
python3 generate_amiibos_from_api.py --verify
```

#### 5. ファイル名の文字化け

**原因**: 特殊文字が含まれているAmiibo名

**解決策**: 

- プログラムが自動的にファイル名をサニタイズします
- 文字化けが発生する場合は、手動でファイル名を変更してください

## 📈 出力例

### 正常な実行例

```bash
$ python3 generate_amiibos_from_api.py
Successfully loaded encryption keys from key_retail.bin
Loaded 932 Amiibo entries from amiibo_api_data.json
Generating 932 Amiibo bin files...
Processing Amiibos: 100%|██████████| 932/932 [00:00<00:00, 7022.22it/s]

Generation complete!
Successfully generated: 932
Errors: 0
Success rate: 100.0%

Generated by series:
  8-bit Mario: 2
  Animal Crossing: 525
  Fire Emblem: 16
  Kirby: 6
  Legend Of Zelda: 26
  Mario Sports Superstars: 90
  Mega Man: 3
  Metroid: 4
  Monster Hunter: 8
  Monster Hunter Rise: 2
  My Mario Wooden Blocks: 4
  Pikmin: 1
  Pokemon: 1
  Power Pros: 1
  Splatoon: 26
  Street Fighter 6: 63
  Super Mario Bros: 15
  Super Nintendo World: 9
  Super Smash Bros.: 96
  Yoshi's Woolly World: 5

Generated by type:
  Band: 9
  Block: 4
  Card: 674
  Figure: 240
  Yarn: 5

✅ All files generated successfully!
```

### 検証結果の例

```bash
$ python3 verify_all_files.py --sample 3
=== Verifying Generated Files ===
[1/3] Verifying: Animal Crossing/Isabelle_0181000100440502.bin
  -> Locked: True
  -> UID: 0438000103000502
  -> ✅ Verification successful
[2/3] Verifying: Super Smash Bros./Mario_0005000000140002.bin
  -> Locked: True
  -> UID: 0005000000140002
  -> ✅ Verification successful
[3/3] Verifying: Street Fighter 6/Ryu_34c0000104a81d02.bin
  -> Locked: True
  -> UID: 34c0000104a81d02
  -> ✅ Verification successful

=== Verification Results ===
Total files: 3
Successfully verified: 3
Errors: 0
Success rate: 100.0%
```

## 🔧 開発者向け情報

### プロジェクト構造

```
amiibo_converter/
├── generate_amiibos_from_api.py    # メインジェネレーター
├── fetch_amiibo_data.py           # APIデータ取得
├── organize_amiibo.py              # ファイル整理
├── verify_all_files.py              # 検証ツール
├── key_retail.bin                  # 暗号化キー
├── 8-Bit Mario Classic Color.bin # テンプレート
├── amiibo_api_data.json           # APIデータ
├── backup/                         # バックアップ
└── remove/                         # 実験・テストファイル
```

### カスタマイズ方法

1. **新しいテンプレートの追加**: `generate_amiibos_from_api.py` の `get_template_for_amiibo()` メソッドを修正
2. **タイプ固有の初期化**: `apply_type_specific_settings()` メソッドを拡張
3. **出力形式の変更**: ファイル名やディレクトリ構造をカスタマイズ

## 📞 ライセンス

このプロジェクトは、以下のオープンソースライブラリおよび技術情報を参考にしています：

- [pyamiibo](https://github.com/tobywf/pyamiibo) - Amiibo操作ライブラリ
- [3dbrew](https://www.3dbrew.org/wiki/Amiibo) - Amiibo技術仕様
- [AmiiboAPI](https://www.amiiboapi.com/) - AmiiboデータAPI
- [amiitool](https://github.com/socram8888/amiitool) - Amiibo暗号化ツール

## 🤝 サポート

問題が発生した場合や、機能追加のご要望がありましたら、以下の情報を添えてご連絡ください：

1. 使用したコマンドとオプション
2. エラーメッセージの全文
3. 使用環境（OS、Pythonバージョンなど）
4. 再現手順

---

**Amiibo Converter** - Amiiboファイル生成ツール

*最終更新日: 2025年12月15日*