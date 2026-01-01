# Obsidian DB設計ノート README

この Vault は **Obsidian を DB 設計の正本（Single Source of Truth）として扱う**ための設計ノートです。  
Markdown + YAML + Dataview を用いて、**設計の再現性・レビュー性・自動化耐性**を重視した構成を採用しています。
- schema / table / column を **1定義1ファイル**で正規化
- 設計意図と定義を明確に分離
- Snowflake DDL 生成・Cortex Search / Agent 連携を前提とした設計

---
## 目的

- DB 設計情報を **Obsidian Vault に一元集約**する
- schema / table / column を **不変 ID で管理**する
- 設計判断・レビュー履歴を **構造化された Markdown として保存**する
- Dataview により
    - 定義一覧
    - 横断レビュー
    - DDL 生成用ビュー  
        を自動生成する

※ 実 DB への反映、マイグレーション管理、データ操作は対象外  
（本 Vault は **設計・合意・レビュー・改善サイクル専用**）

---

## 前提環境

- Obsidian 最新版
- 有効化しているプラグイン
  - Dataview（必須・JavaScript クエリ有効）
  - **Bases**（コアプラグイン）
  - （任意）Templater / QuickAdd / Advanced Tables

※ **Bases は使用しません**
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
|master|**定義の正本**（DDL 生成・自動処理対象）|
|design|設計意図・判断理由・前提条件|
|reviews|人・Agent によるレビュー結果・履歴|
|views|一覧表示・横断チェック・DDL 生成（参照専用）|

- **定義は必ず `master/` を編集する**
- `design/`・`reviews/`・`views/` には定義を書かない 
- Agent / Analyst / 計測処理が `master/` を直接変更することは禁止

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
**1 table = 1 ファイル**

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

**1 column = 1 ファイル**

`master/columns/<SCHEMA>.<TABLE>.<COLUMN>.md`
```yaml
---
type: column
column_id: COL_RUN_ID
table_id: TBL_PROFILE_RUNS
logical: 実行ID
physical: RUN_ID
domain: string
pk: true
is_nullable: false
default:
comment: プロファイル実行を一意に識別するID
---
```

---

## 設計書（design）の使い方

### スキーマ設計書（必須）

`design/design.<SCHEMA>.md`
- スキーマ全体の設計思想
- 命名規約
- 制約ポリシー（DDLで縛らない理由等）
- 例外・アンチパターン

※ **レビュー時・Agent実行時に必ず参照される前提**

---

### テーブル設計書（必須）

`design/<SCHEMA>/design.<TABLE>.md`
- テーブル単位の設計判断
- nullable / default / domain の理由
- PK / FK の選択理由
- 運用・拡張時の前提

※ 存在しない場合は「設計意図未記録」としてレビューで明示される

---
## reviews の使い方（レビュー履歴）

### 設計レビュー（人・Agent）

`reviews/<YYYY-MM-DD>/<SCHEMA>.<TABLE>.md`
- Cortex Agent による設計レビュー結果
- 人手レビューの記録
- 改善提案・差分案（master は直接編集しない）

### プロファイル・計測レビュー

`reviews/profiles/YYYYMMDD_HH24MISSFF3/<SCHEMA>/<TABLE>.md`
- プロファイル結果（raw / summary）
- 設計との乖離指摘
- 次アクション提案

※ 実データの計測結果も **Vault 上の md が正本**

---

## views の使い方（一覧・管理）

### table 一覧

**DB全体のテーブル俯瞰・レビュー用**

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

**全カラム横断チェック用**

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

## 補足ルール（厳守）

- schema / table / column は **必ず不変 ID で関連付ける**    
- ファイル名が変わっても ID は変えない
- Agent は Vault（md）しか参照しない
- Evidence は必ず **実在する md パス**を使用する
- Git 管理・再現性を最優先する


