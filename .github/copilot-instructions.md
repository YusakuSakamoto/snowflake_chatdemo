# GitHub Copilot Instructions

このファイルは、GitHub Copilotがコンテキストとして参照する重要なドキュメントと規則を定義します。

---

## 必読ドキュメント

Copilotは以下のドキュメントを必ず参照してください：

### 1. Snowflake 命名規則
ファイル: `docs/snowflake/chatdemo/NAMING_CONVENTIONS_GUIDE.md`

重要ポイント:
- ビュー（View）: `V_` プレフィックス必須（例: `V_CUSTOMER_MASTER`, `V_DOCS_OBSIDIAN`）
- マテリアライズドビュー: `MV_` プレフィックス必須（例: `MV_DAILY_SALES_SUMMARY`）
- テーブル: `UPPERCASE_UNDERSCORE` 形式（例: `DOCS_OBSIDIAN`, `PROFILE_RESULTS`）
- プロシージャ: `UPPERCASE_UNDERSCORE` 形式（例: `PROFILE_TABLE`, `INGEST_VAULT_MD`）

### 2. Snowflake メンテナンスガイド
ファイル: `docs/snowflake/chatdemo/MAINTENANCE_GUIDE.md`

重要ポイント:
- Obsidianリンク規則
  - 設計ドキュメント参照: `[[design.OBJECT]]`
  - エンティティ参照: `[[SCHEMA.OBJECT]]`
  - カラム参照: `[[SCHEMA.TABLE.COLUMN]]`
- バッククォート（`）の使用禁止（カラム名・パラメータ名）
- パス付きリンク禁止
- マスターファイル構造とデザインファイル構造

### 3. Azure Functions 命名規則
ファイル: `docs/azfunctions/chatdemo/NAMING_CONVENTIONS_GUIDE.md`

重要ポイント:
- モジュール: `lowercase_with_underscores.py`
- クラス: `PascalCase`
- 関数: `lowercase_with_underscores`
- 定数: `UPPERCASE_WITH_UNDERSCORES`
- エンドポイント: `{action}_{resource}_endpoint`

### 4. Azure Functions メンテナンスガイド
ファイル: `docs/azfunctions/chatdemo/MAINTENANCE_GUIDE.md`

重要ポイント:
- PEP 8準拠のPythonコーディング規則
- 型ヒント必須
- Docstring必須（関数・クラス・モジュール）
- 構造化ログ推奨

### 5. Azure SWA 命名規則
ファイル: `docs/azswa/chatdemo/NAMING_CONVENTIONS_GUIDE.md`

重要ポイント:
- コンポーネント: `PascalCase`
- 関数: `camelCase`
- 定数: `UPPERCASE_WITH_UNDERSCORES`
- 型・インターフェース: `PascalCase`（`I` プレフィックス不要）
- CSSモジュール: `camelCase`

### 6. Azure SWA メンテナンスガイド
ファイル: `docs/azswa/chatdemo/MAINTENANCE_GUIDE.md`

重要ポイント:
- TypeScript型定義必須
- React関数コンポーネント推奨
- Hooks使用ルール
- CSSモジュール使用

### 7. Git運用規則
ファイル: `docs/git/chatdemo/GIT_WORKFLOW.md`

重要ポイント:
- コミットメッセージは必ず日本語で記載
- プレフィックス使用: `feat:`, `fix:`, `docs:`, `refactor:`, `style:`, `test:`, `chore:`
- コミット前にWindows Vaultへの同期を確認

---

## Obsidianリンク形式（厳守）

### ❌ 禁止事項
```markdown
# バッククォートの使用禁止
❌ `TARGET_SCHEMA` / `TARGET_TABLE`
❌ DB_DESIGN.PROFILE_RUNS.`RUN_ID`
❌ | `P_TARGET_DB` | STRING |

# パス付きリンク禁止
❌ [[master/tables/DB_DESIGN.DOCS_OBSIDIAN]]
❌ [[design/DB_DESIGN/design.PROFILE_TABLE]]

# 重複プレフィックス禁止
❌ design.[[design.OBJECT]]
```

### ✅ 正しい形式
```markdown
# 通常のテキスト（リンク不要の場合）
✅ TARGET_SCHEMA / TARGET_TABLE
✅ | P_TARGET_DB | STRING |

# Obsidianリンク
✅ [[design.DOCS_OBSIDIAN]]
✅ [[DB_DESIGN.DOCS_OBSIDIAN]]
✅ [[DB_DESIGN.PROFILE_RUNS.RUN_ID]]
```

---

## ファイル構造

### マスターファイル
```
docs/snowflake/chatdemo/master/
├── schemas/          # スキーマ定義
├── tables/           # テーブル定義
├── views/            # ビュー定義（V_ プレフィックス必須）
├── externaltables/   # 外部テーブル定義
├── columns/          # カラム定義（152ファイル）
└── other/            # プロシージャ・関数・ツール
```

### デザインファイル
```
docs/snowflake/chatdemo/design/
├── design.SCHEMA.md           # スキーマ設計方針
├── APP_PRODUCTION/            # 各スキーマの設計
├── DB_DESIGN/
├── LOG/
└── NAME_RESOLUTION/
```

---

## コード生成時の注意事項

### Markdownファイル生成時
1. すべてのスキーマオブジェクト参照には `[[]]` リンクを使用
2. バッククォートは技術用語やコード例のみに使用
3. カラム名・パラメータ名にはバッククォートを使用しない

### Python スクリプト生成時
1. UTF-8エンコーディングを使用
2. `tests/scripts/` ディレクトリに配置
3. 処理結果を明確にログ出力
4. dry-runモードの実装を推奨

### Git コミット時
1. コミットメッセージは必ず日本語
2. 適切なプレフィックスを使用
3. Windows Vault同期を確認

---

## プロジェクト思想

### 最重要原則
- Obsidian Vault上のMarkdown（.md）が唯一の設計正本
- Snowflake上のDDL/VIEW/TABLE/PROCEDURE/AGENTはすべて「結果物」
- Agentは実DBや実データを直接解釈しない
- 判断・存在確認・不足指摘は、必ずVault上の実在する.mdを根拠とする

### 設計ドキュメントの役割
- design/: 設計思想・意図を記載
- master/: 実際のオブジェクト定義を記載
- Agent/LLMは両方を参照して判断する

---

## 自動化スクリプト

メンテナンス用スクリプトは `tests/scripts/` に配置されています。
既存のスクリプトを参考に、同様の構造で新規スクリプトを作成してください。

テンプレート構造:
```python
#!/usr/bin/env python3
"""スクリプトの説明"""
from pathlib import Path

def process_file(content: str) -> tuple[str, int]:
    changes = 0
    # 処理内容
    return content, changes

def main():
    design_dir = Path("docs/snowflake/chatdemo/design")
    total_changes = 0
    files_changed = 0
    
    for md_file in design_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = process_file(content)
        
        if changes > 0:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
```

---

## 参考ドキュメント一覧

すべてのドキュメントは `docs/` ディレクトリ配下に整理されています：

- `docs/snowflake/chatdemo/README.md` - プロジェクト概要
- `docs/git/chatdemo/GIT_WORKFLOW.md` - Git運用規則
- `tests/scripts/README.md` - スクリプト一覧

これらのドキュメントを参照しながら、一貫性のあるコードとドキュメントを生成してください。
