# メンテナンススクリプト

このディレクトリには、Snowflake設計ドキュメント（Obsidian Vault）のメンテナンス用スクリプトが含まれています。

---

## 📋 スクリプト一覧

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

### レビュー・メトリクス系（NEW）
- `analyze_reviews.py` - DB設計レビュー結果の統計分析

---

## 🚀 使用方法

### 基本的な実行方法
```bash
cd /home/yolo/pg/snowflake_chatdemo
python3 tests/scripts/<script_name>.py
```

### 実行例
```bash
# バッククォートを削除
python3 tests/scripts/fix_all_backticks_final.py

# ビュー名をリネーム
python3 tests/scripts/rename_view_simple.py

# レビュー結果の統計分析（NEW）
python3 tests/scripts/analyze_reviews.py
# 出力例:
# ============================================================
# DB Design Review Metrics
# ============================================================
# Total Reviews: 3
# Issues by Priority:
#   Critical: 1
#   High:     7
#   Med:      6
#   Low:      4
```

---

## 📊 スクリプト作成ガイドライン

新規スクリプトを作成する際は、以下のテンプレートを参考にしてください：

```python
#!/usr/bin/env python3
"""スクリプトの説明

使用方法:
    python3 tests/scripts/<スクリプト名>.py

処理内容:
    - 何をするスクリプトか
    - どのファイルを対象とするか
    - どのような変更を加えるか
"""
from pathlib import Path


def process_file(content: str) -> tuple[str, int]:
    """ファイルの処理ロジック
    
    Args:
        content: ファイルの内容
        
    Returns:
        (処理後の内容, 変更箇所数)
    """
    changes = 0
    # 処理内容
    return content, changes


def main():
    """メインエントリポイント"""
    target_dir = Path("docs/snowflake/chatdemo/design")
    
    total_changes = 0
    files_changed = 0
    
    for md_file in target_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = process_file(content)
        
        if changes > 0:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            relative_path = md_file.relative_to("docs/snowflake/chatdemo")
            print(f"✓ {relative_path}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")


if __name__ == "__main__":
    main()
```

---

## 🔧 注意事項

### 実行前の確認
1. 必ずリポジトリルートから実行すること
2. 変更前にGitコミットを作成すること
3. dry-runモードがあれば先にテスト実行すること

### エンコーディング
- すべてのファイルは **UTF-8** エンコーディングで処理
- 必ず `encoding="utf-8"` を明示的に指定

### Windows Vault同期
WSL → Windows への同期が必要な場合は手動で実行：
```bash
cp -r docs/snowflake/chatdemo/* /mnt/c/Users/yolo/Documents/Obsidian/chatdemo/docs/snowflake/chatdemo/
```

---

## 🔗 関連ドキュメント

- [メンテナンスガイド](../../docs/snowflake/chatdemo/MAINTENANCE_GUIDE.md)
- [命名規則](../../docs/snowflake/chatdemo/naming_conventions.md)
- [Git運用規則](../../docs/git/chatdemo/GIT_WORKFLOW.md)

---

## 関連ドキュメント

詳細は [MAINTENANCE_GUIDE.md](../../docs/snowflake/chatdemo/MAINTENANCE_GUIDE.md) を参照してください。

Snowflakeへの接続を確認し、基本的なクエリが実行できることをテストします。
