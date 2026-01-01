
# テーブル設計：[[design.DOCS_OBSIDIAN]]

## 概要
[[DB_DESIGN.DOCS_OBSIDIAN]] は、Obsidian Vault 上の Markdown ファイルを 1ファイル = 1レコードとして取り込み、設計レビュー・検索・Agent 処理の一次ソースとして提供する内部テーブルである。  
[[DB_DESIGN.DOCS_OBSIDIAN.PATH]]（Vault 内の相対パス）と [[DB_DESIGN.DOCS_OBSIDIAN.CONTENT]]（本文）を中心に保持し、Vault を正本とする設計思想のもとで、設計定義（master）・設計意図（design）・レビュー結果（reviews）を Snowflake 上で横断的に扱える状態を作る。

## 関連コンポーネントとの関係

### [[design.V_DOCS_OBSIDIAN]] との関係
[[DB_DESIGN.V_DOCS_OBSIDIAN]] は [[design.DOCS_OBSIDIAN]] を基底とする参照専用ビューであり、検索・閲覧・Agent 利用に適した形で情報を提供する層である。

- 保管・提供の流れ  
  [[DB_DESIGN.DOCS_OBSIDIAN]] → [[DB_DESIGN.V_DOCS_OBSIDIAN]] → DB_DESIGN.OBSIDIAN_VAULT_SEARCH

- 役割分担  
  - [[DB_DESIGN.DOCS_OBSIDIAN]]  
    Vault から取り込んだ Markdown を 1ファイル単位で保持する保管層。
  - [[DB_DESIGN.V_DOCS_OBSIDIAN]]  
    下流（検索サービス・Agent）向けに整形された提供層。

[[design.V_DOCS_OBSIDIAN]] は [[design.DOCS_OBSIDIAN]] の内容を変更せず、参照用途のための投影・整形のみを行う。  
Evidence の根拠単位は常に [[DB_DESIGN.DOCS_OBSIDIAN.PATH]] によって示される実在する .md ファイルであり、ビュー側でその意味を変えない。

### [[design.V_DOCS_OBSIDIAN]] から `OBSIDIAN_VAULT_SEARCH` への連携
DB_DESIGN.OBSIDIAN_VAULT_SEARCH は、[[DB_DESIGN.V_DOCS_OBSIDIAN]] を検索インデックスの入力として利用する Cortex Search サービスである。

- [[DB_DESIGN.V_DOCS_OBSIDIAN]] で提供されたテキストおよびメタ情報をインデックス化する
- Agent は検索結果を探索の補助として利用するが、存在有無や正否判断は Vault 上の実在する [[DB_DESIGN.DOCS_OBSIDIAN.PATH]] を根拠とする

検索結果のスコアやヒット有無のみを根拠に、設計定義やカラムの存在有無を判断しない。

### [[design.INGEST_VAULT_MD]] プロシージャーとの関係
[[DB_DESIGN.INGEST_VAULT_MD]] は、[[DB_DESIGN.OBSIDIAN_VAULT_STAGE]] に同期された Vault の Markdown を読み取り、[[design.DOCS_OBSIDIAN]] に 1ファイル = 1レコードで UPSERT する唯一の書き込み経路である。

- [[DB_DESIGN.DOCS_OBSIDIAN]] への INSERT / UPDATE / DELETE は [[DB_DESIGN.INGEST_VAULT_MD]] のみが行う
- アプリケーション、分析クエリ、運用作業からの直接更新は行わない
- 再実行時も結果が破綻しないよう、冪等な取り込みを前提とする

[[DB_DESIGN.DOCS_OBSIDIAN.FILE_LAST_MODIFIED]] は Vault 側の更新時刻、  
[[DB_DESIGN.DOCS_OBSIDIAN.INGESTED_AT]] は Snowflake への取り込み時刻を示し、両者を区別して扱う。

## 業務上の意味
- このテーブルが表す概念  
  Vault 内 Markdown 資産の台帳。1行が 1つの .md ファイルを表す。
- 主な利用シーン  
  - 設計資産の検索・参照（[[DB_DESIGN.V_DOCS_OBSIDIAN]] / DB_DESIGN.OBSIDIAN_VAULT_SEARCH 経由）  
  - 設計レビューの自動化・高度化（Vault 正本を Snowflake 上で扱うための基盤）  
  - 取り込み運用・監査（取り込み鮮度・遅延の把握）

## 設計方針

### 主キーと識別
- [[DB_DESIGN.DOCS_OBSIDIAN.DOC_ID]] は [[design.DOCS_OBSIDIAN]] における論理的な主キーであり、1ファイルを一意に識別する。
- 実際の一意性担保は [[DB_DESIGN.INGEST_VAULT_MD]] の処理ロジックに依存する。
- PRIMARY KEY 制約は、設計意図を明示するための情報的な制約として付与している。

### カラムの意味づけ
- [[DB_DESIGN.DOCS_OBSIDIAN.DOC_ID]]  
  Vault 内の Markdown ファイルを一意に識別する内部 ID。
- [[DB_DESIGN.DOCS_OBSIDIAN.PATH]]  
  Vault ルートからの相対パス。Evidence として参照される最小単位。
- [[DB_DESIGN.DOCS_OBSIDIAN.FOLDER]]  
  [[DB_DESIGN.DOCS_OBSIDIAN.PATH]] から抽出される論理スコープ（master / design / reviews / views / templates）。
- [[DB_DESIGN.DOCS_OBSIDIAN.CONTENT]]  
  Markdown ファイル全文（frontmatter を含む）。Agent が参照する唯一の本文情報。
- [[DB_DESIGN.DOCS_OBSIDIAN.FILE_LAST_MODIFIED]]  
  Vault 側での最終更新時刻。
- [[DB_DESIGN.DOCS_OBSIDIAN.INGESTED_AT]]  
  Snowflake に取り込まれた時刻。
- [[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_ID]]  
  設計オブジェクトを指す論理 ID（schema_id / table_id / column_id / view_id 等）。
- [[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_TYPE]]  
  [[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_ID]] が示す設計粒度（schema / table / column / view など）。

[[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_ID]] / [[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_TYPE]] は  
[[DB_DESIGN.DOCS_OBSIDIAN.PATH]] と併用して関連付けや探索の補助に使うものであり、ID 名のみの参照に依存しない。

## 注意点
- NOT NULL 列  
  [[DB_DESIGN.DOCS_OBSIDIAN.DOC_ID]],  
  [[DB_DESIGN.DOCS_OBSIDIAN.PATH]],  
  [[DB_DESIGN.DOCS_OBSIDIAN.FOLDER]],  
  [[DB_DESIGN.DOCS_OBSIDIAN.CONTENT]],  
  [[DB_DESIGN.DOCS_OBSIDIAN.INGESTED_AT]]
- NULL 許容列  
  [[DB_DESIGN.DOCS_OBSIDIAN.FILE_LAST_MODIFIED]],  
  [[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_ID]],  
  [[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_TYPE]]

## 将来拡張の余地
- 取り込み管理の高度化  
  CONTENT_HASH, INGEST_RUN_ID, ERROR_STATUS, ERROR_MESSAGE など
- 設計資産の関連付け精度向上  
  [[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_ID]] / [[DB_DESIGN.DOCS_OBSIDIAN.OBJECT_TYPE]] と  
  [[DB_DESIGN.DOCS_OBSIDIAN.PATH]] の対応ルール明確化
- 大量化時の運用改善  
  [[DB_DESIGN.DOCS_OBSIDIAN.FOLDER]] や  
  [[DB_DESIGN.DOCS_OBSIDIAN.PATH]] プレフィックスを意識した検索・クラスタリングの検討

## 関連

table_id:: TBL_20251227124901

- 関連ビュー：[[DB_DESIGN.V_DOCS_OBSIDIAN]]
- 関連検索サービス：DB_DESIGN.OBSIDIAN_VAULT_SEARCH
- 関連プロシージャ：[[DB_DESIGN.INGEST_VAULT_MD]]
- 関連 External Stage：[[DB_DESIGN.OBSIDIAN_VAULT_STAGE]]

```dataview
TABLE physical, domain, comment
FROM "master/columns"
WHERE table_id = this.table_id
SORT schema_id, physical
```


