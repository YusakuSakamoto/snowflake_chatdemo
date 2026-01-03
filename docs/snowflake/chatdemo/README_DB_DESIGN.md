# Obsidian DB設計ノート README

この Vault は Obsidian を DB 設計および分析基盤設計の正本（Single Source of Truth）として扱うための設計ノートです。  
Markdown + YAML + Dataview を用い、再現性・レビュー性・自動化耐性を重視した構成を採用します。

本 Vault は設計・合意・レビュー・改善サイクル専用であり、実 DB への反映、マイグレーション管理、データ操作は対象外です。

---

# Part A: Vaultの目的と運用（SSOT規約）

## 1. 目的と設計思想

### 1.1 目的
- DB 設計情報を Obsidian Vault に一元集約する
- schema / table / view / externaltable / column / monitoring を 1定義1ファイルで正規化する
- 不変 ID により参照関係を維持する
- 設計判断・レビュー履歴を構造化 Markdown として保存する
- Dataview により、定義一覧・横断レビュー・DDL 生成用ビューを自動生成する
- Snowflake DDL 生成と Cortex Agent / Analyst 連携を前提にする

### 1.2 設計思想（原則）
- 定義（master）と設計意図（design）を分離する
- 定義の変更は master のみで行い、設計判断は design に残す
- reviews は結果保存のみで、定義の正本ではない
- views フォルダは Obsidian の Dataview 表示専用（参照専用）とし、定義の正本ではない
- Git 管理・差分レビュー・再現性を優先する
- Agent / Analyst の振る舞い（ログ設計含む）も設計対象とみなす

---

## 2. 前提環境

- Obsidian 最新版
- 有効化しているプラグイン
  - Dataview（必須・JavaScript クエリ有効）
  - Templater（任意）
  - QuickAdd（任意）
  - Advanced Tables（任意）

※ Bases プラグインは使用しません（再現性・Git 管理・外部連携の都合上、Dataview を唯一の正とします）

---

## 3. フォルダ構成

```text
/
├─ master/                    # 定義の正本（DDL生成対象）
│ ├─ schemas/
│ ├─ tables/
│ ├─ externaltables/
│ ├─ views/
│ ├─ columns/
│ ├─ procedures/
│ ├─ functions/
│ ├─ alerts/
│ └─ other/                   # tool / agent / stage / fileformat 等（必要に応じて）
│
├─ design/                    # 設計意図・判断・前提条件
│ ├─ design.<SCHEMA>.md
│ └─ <SCHEMA>/
│    └─ design.<OBJECT>.md
│
├─ reviews/                   # レビュー結果・Agent出力・履歴
│ ├─ <YYYY-MM-DD>/
│ │  └─ <SCHEMA>.<OBJECT>.md
│ └─ profiles/
│    └─ <YYYY-MM-DD>/<SCHEMA>/<OBJECT>.md
│
├─ views/                     # Dataview / DataviewJS 専用ビュー（参照専用）
│ ├─ schemas.md
│ ├─ tables.md
│ ├─ externaltables.md
│ ├─ views.md
│ ├─ columns.md
│ └─ ddl_all.md
│
└─ templates/                 # テンプレート（任意）
```

---

## 4. フォルダごとの役割とルール

| フォルダ | 役割 |
|---|---|
| master | 定義の正本（DDL 生成・自動処理対象） |
| design | 設計意図・判断理由・前提条件 |
| reviews | 人・Agent によるレビュー結果・履歴 |
| views | 一覧表示・横断チェック・DDL 生成（参照専用） |

### 4.1 運用ルール
- 定義は必ず master を編集する
- design / reviews / views に定義を書かない
- Agent / Analyst / 自動処理が master を直接変更することは禁止
- Evidence は必ず実在する md パスを使用する
- ファイル名が変わっても ID は変えない（不変 ID 運用）
- object type ごとの置き場（重要）
  - schema: master/schemas/<SCHEMA>.md
  - table: master/tables/<SCHEMA>.<TABLE>.md
  - externaltable: master/externaltables/<SCHEMA>.<TABLE>.md
  - view: master/views/<SCHEMA>.<VIEW>.md
  - column: master/columns/<SCHEMA>.<TABLE>.<COLUMN>.md
  - procedure: master/procedures/<SCHEMA>.<PROC>.md
  - function: master/functions/<SCHEMA>.<FUNC>.md
  - alert: master/alerts/<SCHEMA>.<ALERT>.md
- 重要: view の定義は master/views に置く。master/tables と混同しない（レビュー・取得・DDL生成の安定稼働のため）

---

# Part B: 定義（master）と参照（views）

## 5. 定義ファイルの書き方（master）

### 5.1 schema 定義
master/schemas/<SCHEMA>.md

```yaml
---
type: schema
schema_id: SCH_PUBLIC
logical: 公開
physical: PUBLIC
comment: 公開用スキーマ
---
```

### 5.2 table 定義（1 table = 1ファイル）
master/tables/<SCHEMA>.<TABLE>.md

```yaml
---
type: table
table_id: TBL_PROFILE_RUNS
schema_id: SCH_DB_DESIGN
logical: プロファイル実行履歴
physical: PROFILE_RUNS
comment: プロファイル実行の履歴管理テーブル
---
```

### 5.3 externaltable 定義（1 externaltable = 1ファイル）
master/externaltables/<SCHEMA>.<TABLE>.md

```yaml
---
type: externaltable
externaltable_id: EXT_20260103000100
schema_id: SCH_LOG
physical: AZSWA_LOGS
comment: Azure Static Web Apps のアクセスログ（外部テーブル）
---
```

### 5.4 view 定義（1 view = 1ファイル）
master/views/<SCHEMA>.<VIEW>.md

```yaml
---
type: view
view_id: VW_20251226184000
schema_id: SCH_DB_DESIGN
physical: V_PROFILE_RESULTS_LATEST
comment: 最新（SUCCEEDED）のプロファイル実行に紐づく結果一覧
depends_on:
  - DB_DESIGN.PROFILE_RUNS
  - DB_DESIGN.PROFILE_RESULTS
---
```

本文の推奨構成（view の場合）:
- View Columns: ビューの列名と列コメント（型は不要）
- SQL: 定義 SQL
- 想定用途: 典型クエリ・利用シーン
- 注意: パーティション指定、コスト、権限、マスキング等

#### 5.4.1 view 定義のレビュー基準（必須）
view は「table と同じ感覚」でレビューすると事故ります。レビュー／自動処理が迷わないよう、以下を view の判定基準（根拠）として明文化します。

- View Columns を「列仕様の正」として扱う  
  - View Columns に列名があるのに SQL の SELECT に出てこない（または逆）は不整合とみなす  
  - SQL の SELECT は列名を明示することを推奨する（SELECT * はレビュー不能になりやすい）

- frontmatter の ID（view_id / schema_id など）は「定義識別子」であり、SQL が返す列ではない  
  - view_id / schema_id 等が SELECT 列に含まれないこと自体は問題にしない  
  - 不整合判定は「View Columns と SQL の整合」で行う

- depends_on は「運用上の安全策」として推奨する  
  - 依存先が増減したら depends_on を更新する  
  - depends_on はレビューの影響範囲把握に使う（DDL の依存解決ロジックとは別）

- view の運用意図は design に残す  
  - 例：直接テーブル参照を避ける／パーティション指定を誘導する／マスキング済み列のみ公開する 等  
  - view の SQL を賢くするより、変更時に壊れない導線（手順・チェックリスト）を優先する

### 5.5 column 定義（1 column = 1ファイル）
master/columns/<SCHEMA>.<TABLE>.<COLUMN>.md

```yaml
---
type: column
column_id: COL_RUN_ID
table_id: TBL_PROFILE_RUNS
logical: 実行ID
physical: RUN_ID
domain: id
is_nullable: false
pk: true
comment: プロファイル実行を一意に識別するID
---
```

---

## 6. Dataview ビュー（参照専用）

### 6.1 tables 一覧
views/tables.md

```dataview
TABLE
  schema_id,
  logical,
  physical,
  comment
FROM "master/tables"
SORT schema_id, physical
```

### 6.2 externaltables 一覧
views/externaltables.md

```dataview
TABLE
  schema_id,
  physical,
  comment
FROM "master/externaltables"
SORT schema_id, physical
```

### 6.3 views 一覧
views/views.md

```dataview
TABLE
  schema_id,
  physical,
  comment
FROM "master/views"
SORT schema_id, physical
```

### 6.4 columns 一覧（横断チェック用）
views/columns.md

```dataview
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

## 7. DDL 生成（views/ddl_all.md）

master 配下の定義から Snowflake DDL を生成します。

### 7.1 生成対象
- schema / table / view / procedure / function
- externaltable（パーティション対応）
- semantic view 用 YAML（必要に応じて）
- 運用定義（alert 等）

### 7.2 出力先
- generated/ddl/
- generated/externaltable/
- generated/yaml/

---

# Part C: 設計標準（Snowflake / Obsidian 規約）

## 8. Snowflake オブジェクト命名規則（要点）

詳細・例外・禁止事項は本 README の「11. メンテナンス・禁止事項」および「9. Obsidian リンク規則」を参照します。

### 8.1 主要ルール（抜粋）

| 区分 | 形式・プレフィックス | 例 |
|------|----------------------|----|
| スキーマ | 大文字英単語 | APP_PRODUCTION |
| テーブル | 大文字英単語_大文字英単語 | DOCS_OBSIDIAN |
| ビュー | V_ + 大文字英単語_大文字英単語 | V_CUSTOMER_MASTER |
| マテリアライズドビュー | MV_ + 大文字英単語_大文字英単語 | MV_DAILY_SALES_SUMMARY |
| 外部テーブル | 通常のテーブル名 または _EXTERNAL | PROFILE_RESULTS_EXTERNAL |
| カラム | 大文字英単語_大文字英単語 | CUSTOMER_ID |
| プロシージャ | 大文字英単語_大文字英単語（動詞始まり推奨） | PROFILE_TABLE |
| 関数 | 大文字英単語_大文字英単語（動詞始まり推奨） | NORMALIZE_JA |
| Cortex Tool/Agent | 動詞_名詞_TOOL または 動詞_名詞_AGENT | GET_DOCS_BY_PATHS_AGENT |
| ステージ | 大文字英単語_STAGE | OBSIDIAN_VAULT_STAGE |
| ファイルフォーマット | FF_ + 大文字英単語 | FF_JSON_LINES |
| パーティションカラム | 小文字英単語（Hive互換） | year, month, day, hour |

### 8.2 命名の原則
- 一貫性：同種オブジェクトに同一パターンを適用する
- 明確性：略語を避け、用途が名前から分かるようにする（ID 等の一般略語は可）
- 簡潔性：長すぎる名前は避ける（40文字以内推奨）
- 予約語回避：Snowflake予約語は避ける。必要ならダブルクォート
- 大文字・小文字：スキーマ/テーブル/カラムは大文字、パーティションカラムは小文字

---

## 9. Obsidian リンク規則（要点）

### 9.1 参照形式
- 設計思想・意図：[[design.OBJECT]]
- 実体参照：[[SCHEMA.OBJECT]]
- カラム参照：[[SCHEMA.TABLE.COLUMN]]

### 9.2 禁止事項（リンク）
- Obsidianリンクは必ず [[]] 形式を使用する
- パス付きリンクは禁止
  - NG: [[master/tables/DB_DESIGN.DOCS_OBSIDIAN]]
  - OK: [[DB_DESIGN.DOCS_OBSIDIAN]]
- 重複プレフィックスは禁止
  - NG: design.[[design.OBJECT]]
  - OK: [[design.OBJECT]]

---

## 10. Snowflake 設計レビュー用 仕様ルール（抜粋）

本章は設計レビューの判断根拠として扱います。

### 10.1 制約
- CHECK 制約は未サポート（DDLで使わない）
- PRIMARY KEY / UNIQUE / FOREIGN KEY は原則 enforce されない前提で設計する（メタデータ扱い）
- NOT NULL は設計ルールとして明確化し、生成元・取り込み・検証で担保する
- 値域・形式の担保は検証クエリ、ETL/ELT バリデーション、内部テーブル化で行う

### 10.2 外部テーブル
- 外部テーブルは外部ステージ上のファイル参照であり、内部テーブルの物理最適化前提で設計しない
- 最適化の主戦場はパス設計、PARTITION BY、WHERE句との一致（プルーニング）
- クラスタリング（CLUSTER BY / 自動再クラスタリング）を外部テーブル最適化策として扱わない
- 高頻度分析・重い集計がある場合は内部テーブル化（取り込み先）で最適化する

### 10.3 view の扱い（重要）
- view は table と別扱いで定義する（master/views に置く）
- view の取得・レビューは view 専用の PATH 列挙を行う（master/tables と混同しない）
- view の依存関係（参照元）は depends_on で明示することを推奨する
- 認可・マスキング・パーティション指定の誘導など、運用上の安全策は view で実現しやすい（設計意図を design に残す）

### 10.4 レビュー判定の補助ルール
- 本章に反する指摘は成立させない（例：CHECK を追加すべき、外部テーブルで制約強制すべき、など）
- 代替案は運用検証クエリ、取り込み時バリデーション、内部テーブル化を優先する

---

# Part D: メンテナンスと変更履歴

## 11. メンテナンス・禁止事項・手順（要点）

### 11.1 禁止事項（バッククォート）
- カラム名やパラメータ名をバッククォートで囲むことは禁止
  - NG: TARGET_SCHEMA をバッククォートで囲む表記
  - OK: TARGET_SCHEMA

例外（バッククォート使用可）：
- コード例の値（user / assistant）
- 技術用語（logging / AUTO_REFRESH）
- テーブル内のサンプルデータ（CUSTOMER_ID 等）
- SQL 関数名（FLATTEN / GET 等）

### 11.2 新規オブジェクト追加時（チェックリスト）
1. master に定義ファイル作成（schemas / tables / externaltables / views / procedures 等）
2. design に設計ファイル作成（design/<SCHEMA>/design.<OBJECT>.md）
3. 必要なら columns 定義を作成
4. 命名規則に準拠しているか確認
5. 参照が [[]] リンクになっているか確認
6. バッククォートが残っていないか確認

### 11.3 既存オブジェクト変更時
1. 変更理由を design に記載
2. master を更新
3. 関連する column 定義を更新
4. リンク切れがないか確認

### 11.4 view 追加・変更時の注意
- master/views に必ず置く（master/tables と混ぜない）
- view の列一覧（View Columns）と SQL を必ず同期させる
- 依存先が増えたら depends_on を更新する
- 直接テーブル参照を許可しない運用の場合、view 経由に寄せる意図を design に明記する

---

## 12. 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-01-02 | 初版作成：命名規則、リンク規則、メンテナンス手順を定義 |
| 2026-01-03 | view / externaltable の定義置き場とレビュー導線を追記（master/views, master/externaltables の明確化） |

---

# Appendix（付録）：実務ノウハウ（SSOT範囲外の参考）

## A1. Cortex Agent / Analyst ログ取得・モニタリング設計ガイド

本章は Cortex Analyst/Agent のログ取得・モニタリングに関する仕様（事実）と実務設計（推奨）をまとめます。

### A1.1 Cortex Analyst Monitoring の正体
Monitoring UI のログは LOG.CORTEX_CONVERSATIONS ではなく、テーブル関数から取得します。

```sql
SNOWFLAKE.LOCAL.CORTEX_ANALYST_REQUESTS(
  'FILE_ON_STAGE',
  '@<db>.<schema>.<stage>/<path>/<semantic_model>.yaml'
)
```

- 完了後のサマリログ（成功/失敗、質問、生成SQL、エラー等）
- 途中経過は含まれない

### A1.2 REQUEST_ID の意味
- REQUEST_ID は Cortex Analyst の1回の解析実行に付与される内部ID
- Monitoring UI の1行は1 REQUEST_ID
- 同じ質問でも再実行すれば別 REQUEST_ID

| ID | 意味 |
|----|------|
| conversation_id | 会話スレッド単位（Agent / API 側） |
| analyst request_id | Analyst 実行単位（Monitoring） |

- conversation_id : request_id = 1 : N
- REST API の request_id / trace_id とは別物

### A1.3 LOG.CORTEX_CONVERSATIONS が入口にならない理由
- LOG.CORTEX_CONVERSATIONS は Cortex Agent 系または別用途のログ
- Analyst Monitoring の公式取得先ではない
- Analyst 精度改善用途では誤った入口になりやすい

### A1.4 Cortex REST API のレスポンス仕様
非ストリーミング（stream=false）
- 最終結果のみ返却
- 途中経過は失われる
- 精度改善・デバッグには不十分

ストリーミング（stream=true）
- Server-Sent Events（SSE）
- Content-Type: text/event-stream
- イベントが順次流れる

主な event_type（例）：
- status：進行フェーズ
- message.content.delta：生成途中のテキスト断片
- tool_call / tool_result：Agent 内ツール実行
- warnings：精度劣化の前兆
- response_metadata：ここに analyst request_id が出ることがある
- done：終了

### A1.5 途中経過ログを全量取得する唯一の方法
- Snowflake 側で途中経過を自動保存する仕組みはない
- Monitoring は結果サマリ専用
- REST API を stream=true（SSE）で呼び、クライアント側ですべて保存する

### A1.6 Python（requests）での SSE 受信（要点）
```python
with requests.post(url, headers=headers, json=payload, stream=True) as r:
    for line in r.iter_lines(decode_unicode=True):
        if line.startswith("event:"):
            event_type = ...
        elif line.startswith("data:"):
            payload = ...
            # ここで必ずログ保存
```
- .json() は使わない（SSEは1つのJSONではない）

### A1.7 精度向上のためのログ設計（推奨）
- SSEイベント1件 = 1ログレコード（正規化しない、VARIANTで丸ごと保存）
- 推奨ログ項目：
  - conversation_id
  - analyst_request_id（response_metadata から）
  - event_type
  - payload（JSON丸ごと）
  - event_ts / ingested_at

### A1.8 S3 × Snowflake 連携の定番パターン
1. Agent REST API を SSEで呼ぶ
2. SSEイベントを NDJSON で S3 に保存
3. Snowflake External Stage を作成
4. Snowpipe / COPY INTO で VARIANT 取り込み
5. CORTEX_ANALYST_REQUESTS と JOIN

### A1.9 結論（運用構成）
- SSE全量ログ：途中経過、警告、ツール呼び出しを保存
- CORTEX_ANALYST_REQUESTS：成功率、生成SQL、エラー率の公式サマリ
- conversation_id × analyst_request_id で結合し、精度改善を計測可能にする

---

## A2. 2026年1月：チャット運用・開発の実践知見

- Azure Functions（Python）で SSE/ストリーミングAPIを安定運用するのは難しく、ワンショット JSON 応答 API に統一した方が安全なケースがある
- API 設計は POST で JSON を受け取り、JSON で一括返す方式に統一する
- エラー時も JSON で返し、CORS ヘッダを付与する
- S3 へのチャット履歴保存は NDJSON 形式（user / assistant の2行）を推奨する
- Python の try/except とインデント崩れに注意する（try は except または finally が必要）
- Git 管理下での復元は git restore が使えるが、インデント崩れは手動修正が必要な場合がある
- フロントエンドも fetch/await/response.json() で一括受信に統一する

---

## A3. Snowflake × Amazon S3 連携ノウハウ・設計原則まとめ

### A3.1 Snowflake から S3 に接続する基本原則
- Snowflake は IAM Role 経由で S3 にアクセスする（Access Key / Secret Key の直接指定は非推奨）
- Snowflake 側では Storage Integration を作成し、それを使って External Stage を定義する
- 実体としての接続制御・境界は AWS IAM にある

要点：
Snowflake は IAM Role を Assume して S3 に入る

### A3.2 接続手順の全体像
1. AWS 側で IAM Role を作成（S3 の GetObject / PutObject / ListBucket 等を許可）
2. Snowflake で Storage Integration を作成
3. DESC STORAGE INTEGRATION で取得した STORAGE_AWS_IAM_USER_ARN と STORAGE_AWS_EXTERNAL_ID を IAM Role の信頼ポリシーに設定
4. Snowflake で External Stage を作成
5. COPY INTO 等でデータ連携

### A3.3 Storage Integration の役割
- Storage Integration は S3 への権限の器
- Stage は Integration を参照するだけ
- Integration 自体がアクセス可能な S3 パスの上限を定義する

```sql
CREATE STORAGE INTEGRATION s3_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = S3
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::123456789012:role/snowflake-role'
  STORAGE_ALLOWED_LOCATIONS = (
    's3://bucket-a/data/',
    's3://bucket-b/logs/'
  );
```

### A3.4 複数 S3 バケットと Storage Integration の関係
結論：
複数バケットでも 1つの Storage Integration で問題ない。条件付きで。

1つでまとめられる条件：
- 同一 AWS アカウント
- 同一 IAM Role
- 権限レベル（Read / Write）が同じ
- セキュリティ境界を分ける必要がない

補足：
- STORAGE_ALLOWED_LOCATIONS には複数 S3 パスを指定可能
- Integration 1つに対して Stage は複数作成できる

### A3.5 Storage Integration を分けるべきケース
以下の場合は Integration を分割する。

- AWS アカウントが異なる
- IAM Role を分けたい
- Read 専用 / Write 可を分離したい
- 監査・セキュリティ要件で用途分離が必要
- 将来、片方だけ権限を落とす可能性がある

原則：
Integration は後から割るより最初から割るほうが運用が楽

### A3.6 よくある誤解・落とし穴
- バケットごとに必ず Integration が必要と思ってしまう
- Stage ごとに Integration が必要と思ってしまう
- Snowflake 側でパス制御しているつもりになる

境界線は IAM Role と S3 ポリシー。

### A3.7 実務的な設計ベストプラクティス

| レイヤ | 分割単位 |
|------|---------|
| Storage Integration | 権限・セキュリティ境界 |
| External Stage | 用途・テーブル・処理単位 |
| S3 Prefix | データ種別・ドメイン単位 |

### A3.8 要点の一文要約
- Snowflake × S3 連携は 認証と権限設計が大部分
- 同じ鍵（IAM Role）で開けるなら Integration は1つ
- 鍵を分けたいなら Integration を分ける

補足：
本ドキュメントは [[awss3.S3_DESIGN_VAULT_DB_DOCS]] および [[awss3.S3_DESIGN_LOG_EXTERNAL_TABLES]] の設計・運用知見をもとにまとめている。

---

## A4. SnowSQL接続方法

## 接続コマンド

### 秘密鍵認証（推奨）

```bash
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8
```

### 特定のロールで接続

```bash
# ACCOUNTADMINロールで接続
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r ACCOUNTADMIN

# GBPS253YS_API_ROLEロールで接続
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r GBPS253YS_API_ROLE
```

### クエリ実行（非対話モード）

```bash
# 単一クエリ実行
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "SELECT CURRENT_USER();"

# ファイルから実行
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -f script.sql

# 複数クエリ実行（セミコロン区切り）
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "USE DATABASE GBPS253YS_DB; SELECT CURRENT_DATABASE();"
```

---

## 接続設定

### 設定ファイルの場所

~/.snowsql/config

### myconn接続の設定内容

```ini
[connections.myconn]
accountname = PGPALAB-IY16795
username = YOLO
# private_key_path は明示的に指定（コマンドライン引数で上書き可能）
```

---

## よくある操作

### 1. Agent権限の付与

```bash
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r ACCOUNTADMIN -q "
GRANT USAGE ON AGENT GBPS253YS_DB.DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT 
TO ROLE GBPS253YS_API_ROLE;
"
```

### 2. データベースオブジェクトの確認

```bash
# スキーマ一覧
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "
USE DATABASE GBPS253YS_DB;
SHOW SCHEMAS;
"

# テーブル一覧
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "
SHOW TABLES IN SCHEMA GBPS253YS_DB.DB_DESIGN;
"

# Agent一覧
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "
SHOW AGENTS IN SCHEMA GBPS253YS_DB.DB_DESIGN;
"
```

### 3. Agent実行テスト

```bash
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r GBPS253YS_API_ROLE -q "
USE ROLE GBPS253YS_API_ROLE;
USE WAREHOUSE GBPS253YS_WH;
USE DATABASE GBPS253YS_DB;

SELECT SNOWFLAKE.CORTEX.COMPLETE_AGENT(
    'DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT',
    'DB_DESIGNスキーマの設計レビューを実行してください。対象テーブルは最大3件とします。'
) AS review_result;
"
```

---

## トラブルシューティング

### 秘密鍵のパスフレーズを求められる
秘密鍵にパスフレーズが設定されている場合、対話的に入力が求められます。  
環境変数で設定することも可能：

```bash
export SNOWSQL_PRIVATE_KEY_PASSPHRASE="your-passphrase"
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8
```

### 接続タイムアウト

```bash
# タイムアウト時間を延長（秒）
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 \
  --option connect_timeout=300
```

### 詳細ログを出力

```bash
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 \
  -o log_level=DEBUG
```

---

## セキュリティ

### 秘密鍵のパーミッション

```bash
chmod 600 /home/yolo/.ssh/snowflake/rsa_key.p8
```

### 秘密鍵の管理
- 秘密鍵はGitリポジトリにコミットしないこと
- .gitignoreに *.p8 を追加
- バックアップは暗号化して保管

---

## エイリアス設定（任意）

```bash
# ~/.bashrc または ~/.zshrc に追加
alias snowsql-myconn='snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8'
alias snowsql-admin='snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r ACCOUNTADMIN'
alias snowsql-api='snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r GBPS253YS_API_ROLE'
```

反映：

```bash
source ~/.bashrc  # または source ~/.zshrc
```

使用例：

```bash
snowsql-admin -q "SHOW DATABASES;"
snowsql-api -q "SELECT CURRENT_ROLE();"
```

---

## 参考資料
- SnowSQL公式ドキュメント https://docs.snowflake.com/en/user-guide/snowsql
- 秘密鍵認証 https://docs.snowflake.com/en/user-guide/key-pair-auth
- SnowSQL設定オプション https://docs.snowflake.com/en/user-guide/snowsql-config
