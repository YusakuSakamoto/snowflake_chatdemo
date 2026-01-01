# design.[[EXPORT_PROFILE_EVIDENCE_MD_VFINAL]]

## 概要

`DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL` は、プロファイル結果（PROFILE_RESULTSテーブル）をMarkdown形式およびJSON形式でS3バケットにエクスポートするプロシージャです。Cortex Agentがデータ品質エビデンスとして参照できるよう、Obsidian Vault形式で構造化されたドキュメントを生成します。

- スキーマ: [[DB_DESIGN]] (SCH_20251226180633)
- オブジェクトタイプ: PROCEDURE
- 言語: SQL
- 実行モード: EXECUTE AS CALLER
- 戻り値: VARIANT (エクスポート結果のJSON)

---

## 業務上の意味

### 目的
プロファイル結果を人間が読める形式（Markdown）と機械処理可能な形式（JSON）の両方で出力し、以下のユースケースを実現します：

1. Cortex Agentの知識ベース更新: Obsidian Vaultに格納することで、DB設計レビューエージェントがデータ品質情報を参照可能
2. データ品質レポート: Markdownファイルをそのままドキュメンテーションツール（Obsidian, Notion等）で閲覧
3. アーカイブ: S3に長期保存することで、品質トレンドの履歴管理が可能

### 利用シーン
- 定期レポート作成: 週次プロファイル実行後、自動的にMarkdownレポートを生成
- データ品質監査: 過去のプロファイル結果をS3から取得し、品質劣化の原因分析
- Cortex Agentとの統合: INGEST_VAULT_MDでMarkdownを再取り込みし、エージェントの回答精度向上

---

## 設計上の位置づけ

### データフロー
```
PROFILE_ALL_TABLES (全テーブルプロファイル実行)
  ↓
PROFILE_RESULTS (カラム単位のメトリクス蓄積)
PROFILE_RUNS (実行履歴)
  ↓
EXPORT_PROFILE_EVIDENCE_MD_VFINAL ★このプロシージャ★
  ↓
S3 (snowflake-chatdemo-vault-prod/reviews/profiles/YYYY-MM-DD/schema/table.md)
  ↓
INGEST_VAULT_MD (S3からMarkdownを再取り込み)
  ↓
DOCS_OBSIDIAN (Cortex Agentが参照可能な内部テーブル)
  ↓
APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT (DB設計レビューエージェント)
```

### 他コンポーネントとの連携
- 上流: [[DB_DESIGN.PROFILE_ALL_TABLES]] → [[DB_DESIGN.PROFILE_RESULTS]] (プロファイル結果のソース)
- 下流: [[DB_DESIGN.INGEST_VAULT_MD]] (エクスポートしたMarkdownを再取り込み)
- 外部システム: S3バケット `snowflake-chatdemo-vault-prod`（[[S3_DESIGN_VAULT_DB_DOCS]]参照）
- 最終消費者: [[APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT]] (Cortex Agent)

---

## 設計方針

### 1. 二重フォーマット出力（Markdown + JSON）
方針: 同じデータを2つの形式で出力  
理由:
- Markdown: 人間が直接閲覧・編集可能。ObsidianやGitHubでレンダリング
- JSON: プログラムによる解析・集計が容易。将来のBI連携を見据える

実装:
- Markdown: `{schema}/{table}.md` - サマリーテーブル形式
- JSON: `{schema}/{table}.raw.json_0_0_0` - 全カラムの詳細メトリクス

### 2. Obsidian Vault互換の構造
方針: Obsidianのベストプラクティスに準拠したYAML frontmatter + Markdown本文  
理由:
- Cortex Agentは [[DOCS_OBSIDIAN]] テーブルをRAGソースとして利用
- frontmatterで構造化メタデータを埋め込むことで、セマンティック検索の精度向上

実装例:
```markdown
---
type: profile_evidence
target_db: GBPS253YS_DB
target_schema: PUBLIC
target_table: CUSTOMERS
as_of_at: 2026-01-02T15:30:00
run_id: 01HX...
row_count: 1500000
generated_on: 2026-01-02
---

# Profile Evidence: PUBLIC.CUSTOMERS

## Raw metrics
- Prefix: `reviews/profiles/2026-01-02/PUBLIC/CUSTOMERS.raw.json`
- File: `reviews/profiles/2026-01-02/PUBLIC/CUSTOMERS.raw.json_0_0_0`

## Columns (summary)
| column | null_rate | distinct_count |
|---|---:|---:|
| `CUSTOMER_ID` | 0.0% | 1500000 |
| `EMAIL` | 0.02% | 1499700 |
| `PHONE` | 5.3% | 1420000 |
```

### 3. S3パーティショニング戦略
方針: 日付ベースのディレクトリ構造 + スキーマ/テーブル階層  
理由:
- 日付パーティションで古いレポートの削除が容易
- スキーマ/テーブル階層でObsidianのフォルダ構造と一致

ディレクトリ構造:
```
s3://snowflake-chatdemo-vault-prod/
  reviews/
    profiles/
      2026-01-02/               ← P_RUN_DATE
        PUBLIC/                 ← TARGET_SCHEMA
          CUSTOMERS.md          ← サマリー
          CUSTOMERS.raw.json_0_0_0  ← 詳細JSON
        STAGING/
          ORDERS.md
          ORDERS.raw.json_0_0_0
```

### 4. エラーハンドリング（テーブル単位）
方針: 1テーブルの失敗が全体をブロックしない  
理由:
- 100テーブルを処理中、1テーブルだけメトリクスが取得できない場合でも、残り99テーブルは出力

実装:
```sql
BEGIN
  -- Markdown生成 + COPY INTO
  -- JSON生成 + COPY INTO
  v_ok := v_ok + 1;
EXCEPTION
  WHEN OTHER THEN
    v_failed := v_failed + 1;
END;
```

---

## パラメータ設計

| パラメータ名 | 型 | 必須 | デフォルト値 | 説明 |
|---|---|---|---|---|
| [[P_SOURCE_DB]] | VARCHAR | ✅ | - | プロファイル結果が格納されているDB（例: `GBPS253YS_DB`） |
| [[P_SOURCE_SCHEMA]] | VARCHAR | ✅ | - | プロファイル結果が格納されているスキーマ（例: [[DB_DESIGN]]） |
| [[P_SOURCE_VIEW]] | VARCHAR | ✅ | - | プロファイル結果のビュー名（例: [[V_PROFILE_RESULTS_LATEST]]） |
| [[P_TARGET_DB]] | VARCHAR | ✅ | - | プロファイル対象のDB（フィルタ条件） |
| [[P_RUN_DATE]] | VARCHAR | ✅ | - | 実行日（YYYY-MM-DD形式）。S3パスの日付部分に使用 |
| [[P_VAULT_PREFIX]] | VARCHAR | ✅ | - | S3の基底パス（例: `reviews/profiles`） |
| [[P_TARGET_SCHEMA]] | VARCHAR | - | NULL | プロファイル対象のスキーマ（NULLの場合は全スキーマ） |

### パラメータ設計の背景
- P_SOURCE_VIEW: 最新のプロファイル結果のみをエクスポートするため、ビュー経由で取得
- P_RUN_DATE: 実行日時を明示的に渡すことで、バッチジョブのタイムスタンプ管理が容易
- P_VAULT_PREFIX: `reviews/profiles` 固定ではなく可変にすることで、将来的に別用途（例: `adhoc/profiles`）にも対応
- P_TARGET_SCHEMA: NULL許容により、1回の実行で全スキーマを処理可能

---

## 戻り値設計

### 構造（JSON/VARIANT）
```json
{
  "status": "OK",
  "exported_ok": 23,
  "exported_failed": 1,
  "raw_file_suffix": "_0_0_0",
  "target_db": "GBPS253YS_DB",
  "run_date": "2026-01-02",
  "vault_prefix": "reviews/profiles"
}
```

### フィールド定義
- `status`: 常に `"OK"`（プロシージャ自体が正常完了）
- `exported_ok`: 正常にエクスポートされたテーブル数
- `exported_failed`: エクスポート失敗したテーブル数
- `raw_file_suffix`: JSON出力時のサフィックス（Snowflakeの内部仕様で`_0_0_0`が付与）
- `target_db` / `run_date` / `vault_prefix`: 入力パラメータのエコーバック

---

## 内部処理フロー

### ステップ1: 初期化とパラメータエスケープ
```sql
v_view_fqn := P_SOURCE_DB || '.' || P_SOURCE_SCHEMA || '.' || P_SOURCE_VIEW;
v_target_db_esc := REPLACE(P_TARGET_DB, '''', '''''');
v_schema_lit := CASE
  WHEN P_TARGET_SCHEMA IS NULL THEN 'NULL'
  ELSE '''' || REPLACE(P_TARGET_SCHEMA, '''', '''''') || ''''
END;
```
- FQN構築: ビューの完全修飾名を生成
- SQLインジェクション対策: シングルクォートをエスケープ

### ステップ2: 対象テーブル一覧の抽出
```sql
CREATE OR REPLACE TEMP TABLE TMP_TARGETS (
  TARGET_SCHEMA STRING,
  TARGET_TABLE  STRING
);

INSERT INTO TMP_TARGETS
SELECT DISTINCT TARGET_SCHEMA, TARGET_TABLE
FROM {v_view_fqn}
WHERE TARGET_DB = '{P_TARGET_DB}'
  AND (P_TARGET_SCHEMA IS NULL OR TARGET_SCHEMA = P_TARGET_SCHEMA);

SELECT COUNT(*) INTO v_total FROM TMP_TARGETS;
```
- 一時テーブル作成: ループ前に対象テーブルを確定
- フィルタリング: [[TARGET_DB]] と [[TARGET_SCHEMA]] で絞り込み

### ステップ3: テーブルごとのMarkdown/JSON生成（ループ処理）
```sql
v_i := 1;
WHILE (v_i <= v_total) DO
  -- 1. 現在のテーブルを選択
  CREATE OR REPLACE TEMP TABLE TMP_ONE AS
  SELECT TARGET_SCHEMA, TARGET_TABLE
  FROM (
    SELECT TARGET_SCHEMA, TARGET_TABLE,
           ROW_NUMBER() OVER (ORDER BY TARGET_SCHEMA, TARGET_TABLE) AS RN
    FROM TMP_TARGETS
  )
  WHERE RN = v_i;
  
  SELECT TARGET_SCHEMA, TARGET_TABLE
    INTO v_schema, v_table
  FROM TMP_ONE;
  
  -- 2. 出力パスを構築
  v_path_md :=
    '@DB_DESIGN.OBSIDIAN_VAULT_STAGE/' || P_VAULT_PREFIX || '/' || P_RUN_DATE || '/'
    || v_schema || '/' || v_table || '.md';
  
  v_path_raw_prefix :=
    '@DB_DESIGN.OBSIDIAN_VAULT_STAGE/' || P_VAULT_PREFIX || '/' || P_RUN_DATE || '/'
    || v_schema || '/' || v_table || '.raw.json';
  
  BEGIN
    -- 3. Markdown生成（TMP_MD）
    CREATE OR REPLACE TEMP TABLE TMP_MD (LINE STRING);
    INSERT INTO TMP_MD (LINE)
    SELECT LINE
    FROM (
      WITH base AS (
        SELECT * FROM {v_view_fqn}
        WHERE TARGET_DB = '{v_target_db}'
          AND TARGET_SCHEMA = '{v_schema}'
          AND TARGET_TABLE = '{v_table}'
      ),
      t AS (
        SELECT
          ANY_VALUE(TARGET_DB) AS TARGET_DB,
          ANY_VALUE(TARGET_SCHEMA) AS TARGET_SCHEMA,
          ANY_VALUE(TARGET_TABLE) AS TARGET_TABLE,
          MAX(AS_OF_AT) AS AS_OF_AT,
          MAX(RUN_ID) AS RUN_ID,
          MAX(TRY_TO_NUMBER(TO_VARCHAR(METRICS:"row_count"))) AS ROW_COUNT
        FROM base
      ),
      c AS (
        SELECT
          TARGET_COLUMN AS COL,
          TRY_TO_DOUBLE(TO_VARCHAR(METRICS:"null_rate")) AS NULL_RATE,
          TRY_TO_NUMBER(TO_VARCHAR(METRICS:"distinct_count")) AS DISTINCT_CNT
        FROM base
      )
      -- YAML frontmatter + Markdownボディ
      SELECT LINE FROM (
        SELECT 10, '---' FROM t
        UNION ALL SELECT 20, 'type: profile_evidence' FROM t
        UNION ALL SELECT 30, 'target_db: ' || TARGET_DB FROM t
        ...
        UNION ALL SELECT 300, '## Columns (summary)' FROM t
        UNION ALL SELECT 310, '| column | null_rate | distinct_count |' FROM t
        UNION ALL SELECT 320, '|---|---:|---:|' FROM t
        UNION ALL
        SELECT
          400 + ROW_NUMBER() OVER (ORDER BY COL),
          '| `' || COL || '` | ' ||
          COALESCE(TO_VARCHAR(ROUND(NULL_RATE * 100, 2)) || '%', 'null') || ' | ' ||
          COALESCE(TO_VARCHAR(DISTINCT_CNT), 'null') || ' |'
        FROM c
      ) x(LINE_NO, LINE)
      ORDER BY 1
    );
    
    -- 4. Markdownファイル出力（COPY INTO）
    COPY INTO {v_path_md}
    FROM TMP_MD
    FILE_FORMAT = (
      TYPE = CSV
      FIELD_DELIMITER = '\u0001'  -- 特殊文字で誤分割を防止
      RECORD_DELIMITER = '\n'
      COMPRESSION = NONE
    )
    HEADER = FALSE
    SINGLE = TRUE
    OVERWRITE = TRUE
    INCLUDE_QUERY_ID = FALSE;
    
    -- 5. JSON生成（TMP_RAW）
    CREATE OR REPLACE TEMP TABLE TMP_RAW (LINE STRING);
    INSERT INTO TMP_RAW (LINE)
    SELECT TO_JSON(
      OBJECT_CONSTRUCT(
        'target_db', '{v_target_db}',
        'target_schema', '{v_schema}',
        'target_table', '{v_table}',
        'run_date', '{P_RUN_DATE}',
        'metrics', ARRAY_AGG(
          OBJECT_CONSTRUCT(
            'column', TARGET_COLUMN,
            'as_of_at', AS_OF_AT,
            'run_id', RUN_ID,
            'metrics', METRICS
          )
        )
      )
    )
    FROM {v_view_fqn}
    WHERE TARGET_DB = '{v_target_db}'
      AND TARGET_SCHEMA = '{v_schema}'
      AND TARGET_TABLE = '{v_table}';
    
    -- 6. JSONファイル出力
    COPY INTO {v_path_raw_prefix}
    FROM TMP_RAW
    FILE_FORMAT = (
      TYPE = CSV
      FIELD_DELIMITER = '\u0001'
      RECORD_DELIMITER = '\n'
      COMPRESSION = NONE
    )
    HEADER = FALSE
    SINGLE = TRUE
    OVERWRITE = TRUE
    INCLUDE_QUERY_ID = FALSE;
    
    v_ok := v_ok + 1;
  EXCEPTION
    WHEN OTHER THEN
      v_failed := v_failed + 1;
  END;
  
  v_i := v_i + 1;
END WHILE;
```

### ステップ4: 結果返却
```sql
RETURN PARSE_JSON(
  '{' ||
    '"status":"OK",' ||
    '"exported_ok":' || v_ok || ',' ||
    '"exported_failed":' || v_failed || ',' ||
    '"raw_file_suffix":"_0_0_0",' ||
    '"target_db":"' || v_target_db_json || '",' ||
    '"run_date":"'  || v_run_date_json  || '",' ||
    '"vault_prefix":"' || v_vault_prefix_json || '"' ||
  '}'
);
```

---

## Markdown生成ロジックの詳細

### YAML Frontmatter
```markdown
---
type: profile_evidence
target_db: GBPS253YS_DB
target_schema: PUBLIC
target_table: CUSTOMERS
as_of_at: 2026-01-02T15:30:00
run_id: 01HX...
row_count: 1500000
generated_on: 2026-01-02
---
```
- type: Obsidianのタグとして機能。Cortex Agentが「これはプロファイルエビデンスである」と識別
- as_of_at: プロファイル実行時刻（ISO 8601形式）
- run_id: PROFILE_RUNSテーブルのプライマリキー。詳細トレーサビリティ確保

### Markdownボディ
```markdown
# Profile Evidence: PUBLIC.CUSTOMERS

## Raw metrics
- Prefix: `reviews/profiles/2026-01-02/PUBLIC/CUSTOMERS.raw.json`
- File: `reviews/profiles/2026-01-02/PUBLIC/CUSTOMERS.raw.json_0_0_0`

## Columns (summary)
| column | null_rate | distinct_count |
|---|---:|---:|
| `CUSTOMER_ID` | 0.0% | 1500000 |
| `EMAIL` | 0.02% | 1499700 |
| `PHONE` | 5.3% | 1420000 |
```
- Raw metrics: JSONファイルへのパス（Obsidian内リンクとして機能）
- Columns (summary): 人間が一目で品質を判断できるテーブル形式

---

## JSON生成ロジックの詳細

### 構造
```json
{
  "target_db": "GBPS253YS_DB",
  "target_schema": "PUBLIC",
  "target_table": "CUSTOMERS",
  "run_date": "2026-01-02",
  "metrics": [
    {
      "column": "CUSTOMER_ID",
      "as_of_at": "2026-01-02T15:30:00",
      "run_id": "01HX...",
      "metrics": {
        "row_count": 1500000,
        "null_count": 0,
        "null_rate": 0.0,
        "distinct_count": 1500000,
        "min": "CUST000001",
        "max": "CUST1500000",
        ...
      }
    },
    ...
  ]
}
```
- metrics配列: 全カラムの詳細メトリクスを含む
- VARIANT型保存: `METRICS` カラムはVARIANT型で、カラムごとに異なるメトリクスセットを格納可能

---

## 運用

### 実行例1: 本番DBの全スキーマをエクスポート
```sql
CALL DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL(
  'GBPS253YS_DB',                     -- P_SOURCE_DB
  'DB_DESIGN',                        -- P_SOURCE_SCHEMA
  'V_PROFILE_RESULTS_LATEST',         -- P_SOURCE_VIEW
  'GBPS253YS_DB',                     -- P_TARGET_DB
  '2026-01-02',                       -- P_RUN_DATE
  'reviews/profiles',                 -- P_VAULT_PREFIX
  NULL                                -- P_TARGET_SCHEMA (全スキーマ)
);
```

### 実行例2: 特定スキーマのみをエクスポート
```sql
CALL DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL(
  'GBPS253YS_DB',
  'DB_DESIGN',
  'V_PROFILE_RESULTS_LATEST',
  'GBPS253YS_DB',
  CURRENT_DATE()::STRING,             -- 動的に日付を取得
  'reviews/profiles',
  'PUBLIC'                            -- PUBLICスキーマのみ
);
```

### 実行例3: 結果の確認
```sql
-- S3ステージ内のファイル一覧
LIST @DB_DESIGN.OBSIDIAN_VAULT_STAGE/reviews/profiles/2026-01-02/;

-- 特定のMarkdownファイルを読み取り（検証用）
SELECT $1
FROM @DB_DESIGN.OBSIDIAN_VAULT_STAGE/reviews/profiles/2026-01-02/PUBLIC/CUSTOMERS.md
(FILE_FORMAT => 'DB_DESIGN.FF_MD_LINE');
```

### タスクスケジューリング（推奨パターン）
```sql
-- プロファイル実行 → エクスポートの連続タスク
CREATE OR REPLACE TASK DB_DESIGN.TASK_PROFILE_AND_EXPORT
  WAREHOUSE = 'COMPUTE_WH'
  SCHEDULE = 'USING CRON 0 4 * * 0 UTC'  -- 毎週日曜 04:00 UTC
AS
BEGIN
  -- Step 1: プロファイル実行
  CALL DB_DESIGN.PROFILE_ALL_TABLES(
    'GBPS253YS_DB',
    'PUBLIC',
    NULL,
    'weekly automated profile'
  );
  
  -- Step 2: エクスポート
  CALL DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL(
    'GBPS253YS_DB',
    'DB_DESIGN',
    'V_PROFILE_RESULTS_LATEST',
    'GBPS253YS_DB',
    CURRENT_DATE()::STRING,
    'reviews/profiles',
    NULL
  );
END;

ALTER TASK DB_DESIGN.TASK_PROFILE_AND_EXPORT RESUME;
```

---

## パフォーマンス考慮

### 実行時間の見積もり
- 1テーブルあたり: 5秒～30秒（Markdown生成 + COPY INTO）
- 100テーブルのスキーマ: 約10分～50分
- ボトルネック: `COPY INTO` のS3書き込み速度

### コスト最適化
- Warehouse選択: `EXECUTE AS CALLER` のため、呼び出し元のWHを使用。小規模WHで十分
- SINGLE = TRUE: 1テーブル1ファイルで分割を防ぎ、COPY INTO回数を最小化
- COMPRESSION = NONE: Markdown/JSONは可読性優先でgzip圧縮なし（S3のストレージコストは微小）

### 並列化の検討（将来拡張）
- 現行はループ処理だが、複数テーブルを並列処理することでスループット向上が可能
- Snowflakeの `EXECUTE IMMEDIATE` 内で `FOR LOOP` を並列化するには、外部オーケストレーター（Airflow等）の利用が必要

---

## エラーハンドリング

### 想定エラーケース
| エラー | 原因 | 対処方法 |
|---|---|---|
| `Stage does not exist` | [[OBSIDIAN_VAULT_STAGE]] が未作成 | ステージ作成コマンドを実行 |
| `Insufficient privileges` | ステージへのWRITE権限不足 | `GRANT WRITE ON STAGE TO ROLE` |
| `Invalid JSON` | METRICS列のVARIANT型が不正 | PROFILE_TABLEの実行ログを確認 |
| `Object does not exist` | v_view_fqnが存在しない | P_SOURCE_VIEW名を確認 |

### リトライ戦略
- 自動リトライ: テーブル単位でTRY-CATCH、失敗しても次のテーブルへ進む
- 手動リトライ: `exported_failed > 0` の場合、ログを確認して原因解決後に再実行

---

## セキュリティとアクセス制御

### 実行権限
- EXECUTE AS CALLER: 呼び出し元ユーザーの権限で実行
- 必要な権限:
  - `USAGE` on source database/schema
  - `SELECT` on source view
  - `USAGE` on [[DB_DESIGN]] schema
  - `WRITE` on [[DB_DESIGN.OBSIDIAN_VAULT_STAGE]]

### S3バケットのIAM権限
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::snowflake-chatdemo-vault-prod/reviews/profiles/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::snowflake-chatdemo-vault-prod",
      "Condition": {
        "StringLike": {
          "s3:prefix": "reviews/profiles/*"
        }
      }
    }
  ]
}
```

### External Stage設定例
```sql
CREATE OR REPLACE STAGE DB_DESIGN.OBSIDIAN_VAULT_STAGE
  URL = 's3://snowflake-chatdemo-vault-prod/'
  STORAGE_INTEGRATION = SNOWFLAKE_CHATDEMO_S3_INT
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = FALSE)
  COMMENT = 'Obsidian Vault用S3ステージ（Markdown/JSON出力先）';
```

---

## データ品質とバリデーション

### 入力バリデーション
- [[P_RUN_DATE]]: YYYY-MM-DD形式であることを前提。不正な形式の場合はS3パスが不正になるが、COPY INTOはエラーを返す
- [[P_VAULT_PREFIX]]: スラッシュ始まり/終わりを含まないこと（例: `reviews/profiles` OK, `/reviews/profiles/` NG）

### 出力の妥当性チェック
- ファイル存在確認: `LIST @STAGE/path/` で出力ファイルが生成されているか検証
- Markdown構文チェック: Obsidianで開いてレンダリングが正常か目視確認
- JSON構文チェック: `[[PARSE_JSON]]()` で読み取り可能か検証

---

## 拡張計画

### フェーズ2: HTML形式出力
- Markdown → HTML変換により、Webブラウザで直接閲覧可能なレポート生成
- CSS埋め込みで視覚的に洗練されたレポート

### フェーズ3: 差分レポート
- 前回実行時との比較（null_rate増加率、distinct_count減少率）をMarkdownに追記
- 「品質劣化アラート」セクションを自動生成

### フェーズ4: グラフ埋め込み
- Mermaid.js記法で分布グラフを生成（Obsidianで自動レンダリング）
- 例: ヒストグラム、ボックスプロット

### フェーズ5: 多言語対応
- 英語版Markdownの自動生成（frontmatterに `lang: en` を追加）

---

## 関連ドキュメント

### 上位設計
- [[design.DB_DESIGN]] - DB_DESIGNスキーマ全体の設計方針
- [[design.PROFILE_ALL_TABLES]] - プロファイル実行オーケストレーター
- [[design.INGEST_VAULT_MD]] - エクスポートしたMarkdownを再取り込み

### 詳細設計
- [[master/other/[[DB_DESIGN.PROFILE_TABLE]] - 個別テーブルのプロファイル実行
- [[master/tables/[[DB_DESIGN.PROFILE_RESULTS]] - カラム単位のメトリクス蓄積テーブル
- [[master/tables/[[DB_DESIGN.DOCS_OBSIDIAN]] - Obsidian Vaultのドキュメント管理テーブル

### 外部システム設計
- [[docs/awss3/chatdemo/S3_DESIGN_VAULT_DB_DOCS]] - S3バケット設計（Vault用）
- [[OBSIDIAN_VAULT_STRUCTURE]] - ObsidianのVault構造定義（未作成）

---

## 変更履歴

| 日付 | 変更者 | 変更内容 |
|---|---|---|
| 2026-01-02 | System | 初版作成（design.[[EXPORT_PROFILE_EVIDENCE_MD_VFINAL]]） |

---

## メタデータ

- 作成日: 2026-01-02
- 最終更新日: 2026-01-02
- ステータス: 運用中
- レビュー担当: DB設計チーム
- 次回レビュー予定: 2026-02-01
