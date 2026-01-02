# Obsidian DB設計ノート README

この Vault は Obsidian を DB 設計の正本（Single Source of Truth）として扱うための設計ノートです。  
Markdown + YAML + Dataview を用いて、設計の再現性・レビュー性・自動化耐性を重視した構成を採用しています。
- schema / table / column を 1定義1ファイルで正規化
- 設計意図と定義を明確に分離
- Snowflake DDL 生成・Cortex Search / Agent 連携を前提とした設計

---
## 目的

- DB 設計情報を Obsidian Vault に一元集約する
- schema / table / column を 不変 ID で管理する
- 設計判断・レビュー履歴を 構造化された Markdown として保存する
- Dataview により
    - 定義一覧
    - 横断レビュー
    - DDL 生成用ビュー  
        を自動生成する

※ 実 DB への反映、マイグレーション管理、データ操作は対象外  
（本 Vault は設計・合意・レビュー・改善サイクル専用）

---

## 前提環境

- Obsidian 最新版
- 有効化しているプラグイン
  - Dataview（必須・JavaScript クエリ有効）
  - Templater（任意）
  - QuickAdd（任意）
  - Advanced Tables（任意）

※ Bases プラグインは使用しません
（再現性・Git 管理・外部連携の都合上、Dataview のみを正とします）

---

## フォルダ構成

```text
/
├─ master/               # 定義の正本（DDL生成対象）
│ ├─ schemas/            # schema 定義
│ ├─ tables/             # table 定義
│ └─ columns/            # column 定義
│
├─ design/               # 人が読む設計意図・判断
│ ├─ design.<SCHEMA>.md
│ └─ <SCHEMA>/
│    └─ design.<TABLE>.md
│
├─ reviews/              # レビュー結果・Agent出力・計測レビュー
│ ├─ <YYYY-MM-DD>/
│ │  └─ <SCHEMA>.<TABLE>.md
│ └─ profiles/
│    └─ <YYYY-MM-DD>/<SCHEMA>/<TABLE>.md
│
├─ views/                # Dataview / DataviewJS 専用ビュー（編集禁止）
│ ├─ schemas.md
│ ├─ tables.md
│ ├─ columns.md
│ └─ ddl_all.md
│
└─ templates/            # テンプレート（任意）

```


---

## 基本ルール（重要）

### master / design / reviews / views の役割分離

|フォルダ|役割|
|---|---|
|master|定義の正本（DDL 生成・自動処理対象）|
|design|設計意図・判断理由・前提条件|
|reviews|人・Agent によるレビュー結果・履歴|
|views|一覧表示・横断チェック・DDL 生成（参照専用）|

- 定義は必ず master/ を編集する
- design/・reviews/・views/ には定義を書かない 
- Agent / Analyst / 計測処理が master/ を直接変更することは禁止

---

## 定義ファイルの書き方

### schema 定義（例）
`master/schemas/<SCHEMA>.md`
```yaml
---
type: schema
schema_id: SCH_PUBLIC      # 不変ID
logical: 公開
physical: PUBLIC
comment: 公開用スキーマ
---
```

### table 定義（例）
1 table = 1 ファイル

`master/tables/<SCHEMA>.<TABLE>.md`
```yaml
---
type: table
table_id: TBL_PROFILE_RUNS   # 不変ID
schema_id: SCH_DB_DESIGN
logical: プロファイル実行履歴
physical: PROFILE_RUNS
comment: プロファイル実行の履歴管理テーブル
---
```

---

### column 定義（例）

1 column = 1 ファイル

`master/columns/<SCHEMA>.<TABLE>.<COLUMN>.md`
```yaml
---
type: column
column_id: COL_RUN_ID
table_id: TBL_PROFILE_RUNS
logical: 実行ID

# Obsidian DB設計ノート README

このVaultはObsidianをDB設計の正本（Single Source of Truth）として扱うための設計ノートです。
詳細な運用ルール・命名規則・リンク規則は[MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md)および[NAMING_CONVENTIONS_GUIDE.md](NAMING_CONVENTIONS_GUIDE.md)を参照してください。

---

## 要点

- DB設計情報はObsidian Vaultに一元集約
- schema / table / columnは1定義1ファイルで管理
- 設計意図と定義を明確に分離
- Snowflake DDL生成・Cortex Search/Agent連携を前提とした設計
- 実DBへの反映・マイグレーション管理・データ操作は対象外（設計・合意・レビュー・改善サイクル専用）

---

## フォルダ構成（抜粋）

```text
/master/    # 定義の正本（DDL生成対象）
/design/    # 設計意図・判断
/reviews/   # レビュー結果・Agent出力
/views/     # Dataview専用ビュー
```

---

## プラグイン・前提環境

- Obsidian最新版
- Dataview（必須・JavaScriptクエリ有効）
- Templater/QuickAdd/Advanced Tables（任意）

---

> ※本READMEは重複・冗長な説明を避け、詳細は各ガイドに集約しています。

`views/tables.md`
```
TABLE
  schema_id,
  logical,
  physical,
  comment
FROM "master/tables"
SORT schema_id, physical
```

---

### column 一覧

全カラム横断チェック用

`views/columns.md`
```
TABLE
  table_id,
  logical,
  physical,
  domain,
  pk,
  row["is_nullable"] AS "NULL可"
FROM "master/columns"
SORT table_id, pk desc
```

---

### DDL 生成

master/ 配下の定義から Snowflake DDL を自動生成する

`views/ddl_all.md`

#### 生成内容
- 事前準備: DB・WH作成SQL
- 1. Snowflake DDL Generator: スキーマ・テーブル・ビュー・プロシージャ・セマンティックビュー（SQL コメント形式）
- 2. External Tables DDL Generator: 外部テーブル定義（パーティション対応）
- 3. YAML FILE Generator: セマンティックビュー用YAML個別ファイル生成

#### 出力先
- `generated/ddl/` - Snowflake DDL（スキーマ・テーブル・ビュー・プロシージャ等）
- `generated/externaltable/` - 外部テーブルDDL
- `generated/yaml/` - セマンティックビューYAMLファイル

---

## 補足ルール（厳守）

- schema / table / column は必ず不変 ID で関連付ける
- ファイル名が変わっても ID は変えない
- Agent は Vault（md）しか参照しない
- Evidence は必ず実在する md パスを使用する
- Git 管理・再現性を最優先する


