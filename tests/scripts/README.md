# メンテナンススクリプト

このディレクトリには、Snowflake設計ドキュメント（Obsidian Vault）のメンテナンス用スクリプトが含まれています。

---

## スクリプト一覧

### データベース接続テスト
```bash
bash tests/scripts/test_snowflake_connection.sh
```

### Obsidianリンク修正
- `add_obsidian_links.py` - 初期Obsidianリンク追加（148行、16ファイル）
- `fix_obsidian_links.py` - design.プレフィックス追加（531行、43ファイル）
- `fix_malformed_links.py` - 重複プレフィックス削除（18行、8ファイル）
- `fix_schema_table_links.py` - SCHEMA.TABLE形式に変換（220行、27ファイル）
- `fix_master_links.py` - [[SCHEMA.OBJECT]]形式に変換（145行、27ファイル）

### バッククォート削除
- `remove_param_backticks.py` - パラメータ名のバッククォート削除（26箇所、4ファイル）
- `fix_all_backticks.py` - バッククォート修正（第1版）
- `fix_all_backticks_v2.py` - バッククォート修正（第2版）
- `fix_all_backticks_final.py` - 最終バッククォート修正（61箇所、14ファイル）
- `fix_backticks_additional.py` - 追加バッククォート削除（55箇所、18ファイル）

### 命名規則修正
- `rename_docs_obsidian_v.py` - ビュー名変更（正規表現版）
- `rename_view_simple.py` - ビュー名変更（単純置換版、30箇所、9ファイル）

---

## 使用方法

### 基本的な実行方法
```bash
cd /path/to/snowflake_chatdemo
python3 tests/scripts/<script_name>.py
```

### 実行例
```bash
# バッククォートを削除
python3 tests/scripts/fix_all_backticks_final.py

# ビュー名をリネーム
python3 tests/scripts/rename_view_simple.py
```

---

## 関連ドキュメント

詳細は [MAINTENANCE_GUIDE.md](../../docs/snowflake/chatdemo/MAINTENANCE_GUIDE.md) を参照してください。

Snowflakeへの接続を確認し、基本的なクエリが実行できることをテストします。
