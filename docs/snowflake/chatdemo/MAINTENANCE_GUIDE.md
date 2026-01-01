# メンテナンスガイド

## 概要
本ドキュメントは、Snowflake設計ドキュメント（Obsidian Vault）のメンテナンス規則と手順を定義します。

---

## 命名規則

詳細は [naming_conventions.md](naming_conventions.md) を参照してください。

### 主要ルール
- **ビュー（View）**: `V_` プレフィックス必須
  - 例: `V_CUSTOMER_MASTER`, `V_DOCS_OBSIDIAN`
- **マテリアライズドビュー（Materialized View）**: `MV_` プレフィックス必須
  - 例: `MV_DAILY_SALES_SUMMARY`
- **テーブル（Table）**: `UPPERCASE_UNDERSCORE` 形式
  - 例: `DOCS_OBSIDIAN`, `PROFILE_RESULTS`

---

## Obsidianリンク規則

### 基本原則
すべてのスキーマオブジェクト参照には `[[]]` 形式のObsidianリンクを使用します。これにより、Obsidianのファイル名変更機能で自動的にリンクが更新されます。

### リンク形式の使い分け

#### 1. 設計ドキュメント参照
設計思想や意図を参照する場合：
```markdown
[[design.OBJECT_NAME]]
```

例：
- `[[design.DOCS_OBSIDIAN]]` - テーブルの設計思想
- `[[design.PROFILE_TABLE]]` - プロシージャの設計意図
- `[[design.APP_PRODUCTION]]` - スキーマの設計方針

#### 2. エンティティ（実体）参照
実際のデータベースオブジェクトを参照する場合：
```markdown
[[SCHEMA.OBJECT]]
```

例：
- `[[DB_DESIGN.DOCS_OBSIDIAN]]` - テーブル実体
- `[[DB_DESIGN.PROFILE_TABLE]]` - プロシージャ実体
- `[[APP_PRODUCTION.V_CUSTOMER_MASTER]]` - ビュー実体

#### 3. カラム参照
カラムを参照する場合：
```markdown
[[SCHEMA.TABLE.COLUMN]]
```

例：
- `[[DB_DESIGN.DOCS_OBSIDIAN.PATH]]` - PATHカラム
- `[[DB_DESIGN.PROFILE_RESULTS.RUN_ID]]` - RUN_IDカラム
- `[[APP_PRODUCTION.ANKEN_MEISAI.CUSTOMER_ID]]` - CUSTOMER_IDカラム

### 禁止事項

#### ❌ バッククォート（`）の使用禁止
カラム名やパラメータ名を `` ` `` で囲むことは禁止です。

**悪い例：**
```markdown
- `TARGET_SCHEMA` / `TARGET_TABLE` / `TARGET_COLUMN` により特定
- | `P_TARGET_DB` | STRING | ✅ | - |
- DB_DESIGN.PROFILE_RUNS.`RUN_ID` を起点として
```

**良い例：**
```markdown
- TARGET_SCHEMA / TARGET_TABLE / TARGET_COLUMN により特定
- | P_TARGET_DB | STRING | ✅ | - |
- [[DB_DESIGN.PROFILE_RUNS.RUN_ID]] を起点として
```

**例外（バッククォート使用OK）：**
- コード例の値：`user` / `assistant`
- 技術用語：`logging`, `AUTO_REFRESH`
- Markdownテーブル内のサンプルデータ：`CUSTOMER_ID`, `EMAIL`
- SQL関数名：`FLATTEN`, `GET`, `ANY_VALUE`

#### ❌ パス付きリンクの禁止
```markdown
❌ [[master/tables/DB_DESIGN.DOCS_OBSIDIAN]]
❌ [[design/DB_DESIGN/design.PROFILE_TABLE]]
✅ [[DB_DESIGN.DOCS_OBSIDIAN]]
✅ [[design.PROFILE_TABLE]]
```

#### ❌ 重複プレフィックスの禁止
```markdown
❌ design.[[design.OBJECT]]
❌ [[design.SCHEMA.TABLE]]
✅ [[design.OBJECT]]
```

---

## マスターファイル構造

### ディレクトリ構成
```
master/
├── schemas/          # スキーマ定義
├── tables/           # テーブル定義
├── views/            # ビュー定義
├── externaltables/   # 外部テーブル定義
├── columns/          # カラム定義（152ファイル）
└── other/            # プロシージャ・関数・ツール
```

### ファイル命名規則
- スキーマ: `SCHEMA_NAME.md`
- テーブル: `SCHEMA.TABLE.md`
- ビュー: `SCHEMA.VIEW.md`
- カラム: `SCHEMA.TABLE.COLUMN.md`
- プロシージャ: `SCHEMA.PROCEDURE.md`

---

## デザインファイル構造

### ディレクトリ構成
```
design/
├── design.SCHEMA.md           # スキーマ設計方針
├── APP_PRODUCTION/            # APP_PRODUCTIONスキーマ設計
│   └── design.OBJECT.md
├── DB_DESIGN/                 # DB_DESIGNスキーマ設計
│   └── design.OBJECT.md
├── LOG/                       # LOGスキーマ設計
│   └── design.OBJECT.md
└── NAME_RESOLUTION/           # NAME_RESOLUTIONスキーマ設計
    └── design.OBJECT.md
```

### ファイル命名規則
- スキーマ設計: `design.SCHEMA.md`
- オブジェクト設計: `design.OBJECT.md`

---

## メンテナンス手順

### 1. 新規オブジェクト追加時

#### 手順
1. masterファイルを作成（master/tables/, master/views/, etc.）
2. designファイルを作成（design/SCHEMA/design.OBJECT.md）
3. カラム定義ファイルを作成（必要に応じて）
4. naming_conventions.md に準拠しているか確認
5. リンクが正しく設定されているか確認

#### チェックリスト
- [ ] 命名規則に準拠している
- [ ] masterファイルが存在する
- [ ] designファイルが存在する
- [ ] カラム定義が作成されている（テーブル・ビューの場合）
- [ ] すべての参照が [[]] リンクになっている
- [ ] バッククォートが使用されていない

### 2. 既存オブジェクト変更時

#### 手順
1. 変更内容をdesignファイルに記載
2. masterファイルを更新
3. 関連するカラム定義を更新
4. リンク切れがないか確認

#### 注意点
- Obsidianのファイル名変更機能を使うと、リンクが自動更新される
- 手動でファイル名を変更した場合は、すべての参照を手動更新する必要がある

### 3. 命名規則違反の修正

#### 検出方法
```bash
# ビューで V_ プレフィックスがないものを検出
cd docs/snowflake/chatdemo/master/views
ls -1 | grep -v '^[A-Z_]*\.V_'
```

#### 修正手順
1. ファイル名をリネーム
2. 全ての参照を更新（スクリプト使用推奨）
3. Windows Vaultに同期
4. コミット・プッシュ

### 4. バッククォート削除

#### 検出方法
```bash
# バッククォートで囲まれた大文字の識別子を検出
grep -r '`[A-Z_]\+`' docs/snowflake/chatdemo/design/
```

#### 修正手順
1. tests/scripts/ 配下のスクリプトを参考に修正スクリプトを作成
2. 対象ファイルを一括変換
3. 手動で確認（例外ケースの確認）
4. Windows Vaultに同期
5. コミット・プッシュ

---

## 自動化スクリプト

### 配置場所
すべてのメンテナンススクリプトは `tests/scripts/` に配置します。

### 既存スクリプト一覧

#### リンク修正系
- `add_obsidian_links.py` - 初期Obsidianリンク追加
- `fix_obsidian_links.py` - Obsidianリンク修正（design.プレフィックス追加）
- `fix_malformed_links.py` - 不正リンク修正（重複プレフィックス削除）
- `fix_schema_table_links.py` - 実体参照修正（SCHEMA.TABLE形式に変換）
- `fix_master_links.py` - masterリンク修正（[[SCHEMA.OBJECT]]形式に変換）

#### バッククォート削除系
- `remove_param_backticks.py` - パラメータ名のバッククォート削除
- `fix_all_backticks.py` - 包括的バッククォート削除（第1版）
- `fix_all_backticks_v2.py` - 包括的バッククォート削除（第2版）
- `fix_all_backticks_final.py` - 最終バッククォート削除
- `fix_backticks_additional.py` - 追加バッククォート削除

#### 命名規則修正系
- `rename_docs_obsidian_v.py` - ビュー名変更（正規表現版）
- `rename_view_simple.py` - ビュー名変更（単純置換版）

### スクリプト作成ガイドライン

#### 基本構造
```python
#!/usr/bin/env python3
"""
スクリプトの説明
"""
from pathlib import Path

def process_file(content: str) -> tuple[str, int]:
    """ファイル内容を処理して変更箇所数を返す"""
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
        
        if changes > 0 and new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
```

#### 注意事項
- UTF-8エンコーディングを使用
- 変更前後の比較を必ず行う
- dry-runモードの実装を推奨
- 処理結果を明確にログ出力

---

## Windows Vault同期

### 同期先
```
/mnt/c/Users/Owner/Documents/snowflake-db/
```

### 同期コマンド
```bash
# 全ファイル同期（削除も含む）
rsync -av --delete docs/snowflake/chatdemo/ /mnt/c/Users/Owner/Documents/snowflake-db/

# 特定ファイル同期
cp "docs/snowflake/chatdemo/design/DB_DESIGN/design.OBJECT.md" \
   "/mnt/c/Users/Owner/Documents/snowflake-db/design/DB_DESIGN/"
```

### 同期タイミング
- 重要な変更後は必ず同期
- コミット前に同期推奨
- 大量のファイル変更時は rsync 使用

---

## Git運用規則

詳細は [GIT_WORKFLOW.md](../../git/chatdemo/GIT_WORKFLOW.md) を参照してください。

### 重要ポイント
- **コミットメッセージは日本語で記載**
- プレフィックス使用推奨（`feat:`, `fix:`, `docs:`, `refactor:` など）
- コミット前にWindows Vaultへの同期を確認

---

## トラブルシューティング

### リンク切れの検出
Obsidianの「リンク切れを表示」機能を使用するか、以下のスクリプトで検出：
```bash
# 存在しないファイルへのリンクを検出
grep -rho '\[\[[^]]*\]\]' docs/snowflake/chatdemo/design/ | \
  sort -u | \
  while read link; do
    file=$(echo "$link" | sed 's/\[\[\(.*\)\]\]/\1/')
    # ファイル存在チェックロジック
  done
```

### バッククォートの残存確認
```bash
# カラム名・パラメータ名のバッククォートを検出
grep -rn '`[A-Z_][A-Z_]*`' docs/snowflake/chatdemo/design/ | \
  grep -v 'AUTO_REFRESH\|logging\|user\|assistant'
```

### 命名規則違反の検出
```bash
# V_ プレフィックスがないビューを検出
cd docs/snowflake/chatdemo/master/views
ls -1 | grep -v '\.V_' | grep -v '^V_'

# MV_ プレフィックスがないマテリアライズドビューを検出
# （現在は該当なし）
```

---

## 参考資料

- [naming_conventions.md](naming_conventions.md) - 命名規則詳細
- [README.md](README.md) - プロジェクト概要
- [tests/scripts/README.md](../../tests/scripts/README.md) - スクリプト一覧

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-01-02 | 初版作成：命名規則、リンク規則、メンテナンス手順を定義 |
