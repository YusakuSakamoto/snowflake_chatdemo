# S3ストレージ設計：Obsidian Vault（DB設計ドキュメント）

## 概要
本ドキュメントは、Obsidian VaultのDB設計ドキュメントをS3に保存し、Snowflake経由でCortex Agentが参照できるようにするための S3 バケット設計を定義する。

Cortex Agent（`APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT`）は、DB設計の文脈を理解するために、Vaultに格納されたテーブル設計書、カラム定義、スキーマ設計などを参照する。

## 設計目標
1. 検索性：Cortex Agentが必要なドキュメントを迅速に検索できる
2. 鮮度：Vault更新後、数分以内にSnowflakeから最新版を参照可能
3. セキュリティ：設計ドキュメントへのアクセスを適切に制限
4. バージョン管理：ドキュメント変更履歴を追跡可能
5. コスト最適化：静的ドキュメントのストレージコストを最小化

## ユースケース

### 1. Cortex Agentによるテーブル設計参照
ユーザーが「ANKEN_MEISAIテーブルの設計意図は？」と質問した場合：
```
User Query
  ↓
Cortex Agent (SNOWFLAKE_DEMO_AGENT)
  ↓
Snowflake: SELECT FROM DB_DESIGN.DOCS_OBSIDIAN
           WHERE file_path LIKE '%design.ANKEN_MEISAI.md%'
  ↓
S3: s3://135365622922-snowflake-chatdemo-vault-prod/design/APP_PRODUCTION/design.ANKEN_MEISAI.md
  ↓
Agent: 設計意図を抽出して回答生成
```

### 2. DB設計レビューの自動化
新しいテーブル設計を追加した際、Cortex Agentが自動レビュー：
```
New Design File
  ↓
S3 Upload (via sync script)
  ↓
Snowflake External Table: AUTO_REFRESH
  ↓
Cortex Agent: 設計レビュータスク実行
  ↓
レビュー結果を DB_DESIGN.PROFILE_RESULTS に記録
```

## S3バケット構造

### バケット名
```
s3://135365622922-snowflake-chatdemo-vault-prod/
```

- AWS Account ID: `135365622922`
- 環境: `prod`

### ディレクトリ階層
Obsidian Vaultのディレクトリ構造をそのまま維持：

```
snowflake-chatdemo-vault-prod/
├── master/                             # マスタ定義
│   ├── schemas/
│   │   ├── APP_PRODUCTION.md
│   │   ├── APP_DEVELOPMENT.md
│   │   ├── NAME_RESOLUTION.md
│   │   └── LOG.md
│   ├── tables/
│   │   ├── APP_PRODUCTION.ANKEN_MEISAI.md
│   │   ├── APP_PRODUCTION.DEPARTMENT_MASTER.md
│   │   └── ...
│   ├── externaltables/
│   │   ├── LOG.CORTEX_CONVERSATIONS.md
│   │   ├── LOG.AZFUNCTIONS_LOGS.md
│   │   └── ...
│   ├── columns/
│   │   ├── APP_PRODUCTION.ANKEN_MEISAI.ANKEN_ID.md
│   │   └── ...
│   ├── views/
│   │   ├── APP_PRODUCTION.V_ENTITY_ALIAS_ALL.md
│   │   └── ...
│   └── other/
│       ├── APP_PRODUCTION.RESOLVE_ENTITY_ALIAS.md (Procedure)
│       └── ...
├── design/                             # 設計ドキュメント
│   ├── design.APP_PRODUCTION.md        # スキーマ設計
│   ├── design.NAME_RESOLUTION.md
│   ├── design.LOG.md
│   ├── APP_PRODUCTION/
│   │   ├── design.ANKEN_MEISAI.md
│   │   ├── design.DEPARTMENT_MASTER.md
│   │   └── ...
│   ├── NAME_RESOLUTION/
│   │   ├── design.DIM_ENTITY_ALIAS.md
│   │   └── ...
│   └── LOG/
│       ├── design.CORTEX_CONVERSATIONS.md
│       └── ...
├── views/                              # Dataview クエリ（参考）
│   ├── ddl_all.md
│   ├── tables.md
│   └── ...
├── generated/                          # 生成されたDDL
│   └── ddl/
│       ├── snowflake_ddl_20260101_120000.sql
│       └── snowflake_external_ddl_20260102_042001.sql
├── profile_results/                    # プロファイル結果（Git管理外）
│   └── year=YYYY/
│       └── month=MM/
│           └── day=DD/
│               ├── {run_id}_results.json  # PROFILE_RESULTS
│               └── {run_id}_run.json      # PROFILE_RUNS
└── _metadata/                          # メタデータ（同期情報）
    └── sync_history.json
```

### パーティション戦略

#### 設計ドキュメント
パーティション不要：
- ドキュメントは静的で、時系列ではない
- ファイルパスによる階層構造で十分に効率的
- Snowflake External Tableは `metadata$filename` で個別ファイルを特定

#### プロファイル結果
日付パーティション（year/month/day）：
- 時系列データとして管理（プロファイル実行日ベース）
- 古いデータのクエリ性能を最適化
- ライフサイクルポリシーで古いパーティションを自動削除可能
- パーティションプルーニングによるクエリコスト削減

## ファイル同期戦略

### 同期方法

#### オプション1：手動同期（初期）
```bash
# Obsidian Vault → S3 への同期（設計ドキュメントのみ）
aws s3 sync \
  /mnt/c/Users/Owner/Documents/snowflake-db/ \
  s3://snowflake-chatdemo-vault-prod/ \
  --exclude ".obsidian/*" \
  --exclude ".trash/*" \
  --exclude "profile_results/*" \
  --delete
```

注記：`profile_results/` はSnowflakeから直接書き込まれるため、ローカル同期から除外。

#### オプション2：GitHub Actions経由（推奨）
```yaml
# .github/workflows/sync-vault-to-s3.yml
name: Sync Vault to S3

on:
  push:
    branches: [main]
    paths:
      - 'docs/snowflake/chatdemo/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Sync to S3
        run: |
          aws s3 sync docs/snowflake/chatdemo/ \
            s3://snowflake-chatdemo-vault-prod/ \
            --exclude ".obsidian/*" \
            --exclude "profile_results/*" \
            --delete
      
      - name: Trigger Snowflake External Table Refresh
        run: |
          # SnowflakeのREST APIまたはSnowpipe経由でREFRESH
          curl -X POST "${{ secrets.SNOWFLAKE_REFRESH_WEBHOOK }}"
```

#### オプション3：リアルタイム同期（将来）
Obsidian Pluginで変更検知 → 自動S3 Upload

### 同期頻度
- 手動同期：設計ドキュメント更新時（git push後）
- GitHub Actions：mainブランチへのpush時に自動
- 目標：5分以内にSnowflakeから参照可能

## Snowflake External Stage / Table

### External Stage定義

#### ドキュメント用Stage
```sql
CREATE OR REPLACE STAGE DB_DESIGN.VAULT_STAGE
  URL = 's3://snowflake-chatdemo-vault-prod/'
  STORAGE_INTEGRATION = S3_INTEGRATION_READONLY
  FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 0);
```

注記：Markdownファイルはテキストとして読み込むため、FILE_FORMATはCSVでも可（1カラムとして扱う）。

#### プロファイル結果用Stage
```sql
CREATE OR REPLACE STAGE DB_DESIGN.OBSIDIAN_VAULT_STAGE
  URL = 's3://snowflake-chatdemo-vault-prod/'
  STORAGE_INTEGRATION = S3_INTEGRATION_READWRITE
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = FALSE)
  COMMENT = 'Obsidian Vault用S3ステージ（Markdown/JSON出力先、プロファイル結果含む）';
```

注記：プロファイル結果はSnowflakeから書き込むため、READWRITEアクセスが必要。

### External Table定義

#### 設計ドキュメント（DB_DESIGN.DOCS_OBSIDIAN）
既存の `DB_DESIGN.DOCS_OBSIDIAN` テーブルを External Table として再定義：

```sql
CREATE OR REPLACE EXTERNAL TABLE DB_DESIGN.DOCS_OBSIDIAN (
  file_path VARCHAR AS (metadata$filename::VARCHAR),
  file_content VARCHAR AS ($1::VARCHAR),
  file_size NUMBER AS (metadata$file_size::NUMBER),
  last_modified TIMESTAMP_NTZ AS (metadata$file_last_modified::TIMESTAMP_NTZ)
)
LOCATION = @DB_DESIGN.VAULT_STAGE
FILE_FORMAT = (TYPE = 'CSV' FIELD_DELIMITER = 'NONE' RECORD_DELIMITER = 'NONE')
AUTO_REFRESH = TRUE
COMMENT = 'Obsidian Vault DB設計ドキュメント（S3外部テーブル）';
```

重要：`FILE_DELIMITER = 'NONE'` でファイル全体を1レコードとして読み込む。

#### プロファイル結果（DB_DESIGN.PROFILE_RESULTS_EXTERNAL）
```sql
CREATE OR REPLACE EXTERNAL TABLE DB_DESIGN.PROFILE_RESULTS_EXTERNAL (
  target_db VARCHAR AS ($1:target_db::VARCHAR),
  target_schema VARCHAR AS ($1:target_schema::VARCHAR),
  target_table VARCHAR AS ($1:target_table::VARCHAR),
  target_column VARCHAR AS ($1:target_column::VARCHAR),
  run_id VARCHAR AS ($1:run_id::VARCHAR),
  as_of_at TIMESTAMP_NTZ AS ($1:as_of_at::TIMESTAMP_NTZ),
  metrics VARIANT AS ($1:metrics::VARIANT),
  year NUMBER AS (metadata$external_table_partition:year::NUMBER),
  month NUMBER AS (metadata$external_table_partition:month::NUMBER),
  day NUMBER AS (metadata$external_table_partition:day::NUMBER)
)
LOCATION = @DB_DESIGN.OBSIDIAN_VAULT_STAGE/profile_results/
FILE_FORMAT = (TYPE = 'JSON')
PARTITION BY (year, month, day)
AUTO_REFRESH = FALSE
COMMENT = 'プロファイル結果（カラム単位メトリクス）の外部テーブル';
```

#### プロファイル実行履歴（DB_DESIGN.PROFILE_RUNS_EXTERNAL）
```sql
CREATE OR REPLACE EXTERNAL TABLE DB_DESIGN.PROFILE_RUNS_EXTERNAL (
  run_id VARCHAR AS ($1:run_id::VARCHAR),
  target_db VARCHAR AS ($1:target_db::VARCHAR),
  target_schema VARCHAR AS ($1:target_schema::VARCHAR),
  target_table VARCHAR AS ($1:target_table::VARCHAR),
  started_at TIMESTAMP_NTZ AS ($1:started_at::TIMESTAMP_NTZ),
  finished_at TIMESTAMP_NTZ AS ($1:finished_at::TIMESTAMP_NTZ),
  status VARCHAR AS ($1:status::VARCHAR),
  sample_pct FLOAT AS ($1:sample_pct::FLOAT),
  warehouse_name VARCHAR AS ($1:warehouse_name::VARCHAR),
  role_name VARCHAR AS ($1:role_name::VARCHAR),
  git_commit VARCHAR AS ($1:git_commit::VARCHAR),
  note VARCHAR AS ($1:note::VARCHAR),
  year NUMBER AS (metadata$external_table_partition:year::NUMBER),
  month NUMBER AS (metadata$external_table_partition:month::NUMBER),
  day NUMBER AS (metadata$external_table_partition:day::NUMBER)
)
LOCATION = @DB_DESIGN.OBSIDIAN_VAULT_STAGE/profile_results/
FILE_FORMAT = (TYPE = 'JSON')
PARTITION BY (year, month, day)
AUTO_REFRESH = FALSE
COMMENT = 'プロファイル実行履歴の外部テーブル';
```

### Snowpipe による自動更新（任意）

S3イベント通知 → Snowpipe → External Table REFRESH の自動化：

```sql
CREATE OR REPLACE PIPE DB_DESIGN.VAULT_PIPE
  AUTO_INGEST = TRUE
AS
  -- Snowpipeは通常のテーブル用だが、External TableのREFRESHトリガーとして利用
  ALTER EXTERNAL TABLE DB_DESIGN.DOCS_OBSIDIAN REFRESH;
```

S3イベント通知設定：
```json
{
  "LambdaFunctionConfigurations": [
    {
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:TriggerSnowflakeRefresh",
      "Events": ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "prefix", "Value": "design/"},
            {"Name": "suffix", "Value": ".md"}
          ]
        }
      }
    }
  ]
}
```

## Cortex Agent統合

### Cortex Agentの設定

#### Semantic Modelへの追加
```sql
-- DB_DESIGN.DOCS_OBSIDIAN を Cortex Agent のコンテキストに追加
ALTER CORTEX AGENT APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT
  SET SEMANTIC_MODEL = (
    -- 既存のテーブル
    'GBPS253YS_DB.APP_PRODUCTION.ANKEN_MEISAI',
    'GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER',
    -- DB設計ドキュメント（追加）
    'GBPS253YS_DB.DB_DESIGN.DOCS_OBSIDIAN'
  );
```

#### RAG（Retrieval-Augmented Generation）の実装
```sql
-- ユーザーの質問に関連する設計ドキュメントを検索
CREATE OR REPLACE FUNCTION DB_DESIGN.SEARCH_DESIGN_DOCS(
  query_text VARCHAR
)
RETURNS TABLE (file_path VARCHAR, relevance_score FLOAT, excerpt VARCHAR)
AS
$$
  SELECT 
    file_path,
    -- Snowflake Cortex Search または単純なLIKE検索
    CASE 
      WHEN file_content ILIKE '%' || query_text || '%' THEN 1.0
      ELSE 0.0
    END AS relevance_score,
    SUBSTR(file_content, POSITION(query_text IN file_content) - 100, 300) AS excerpt
  FROM DB_DESIGN.DOCS_OBSIDIAN
  WHERE file_content ILIKE '%' || query_text || '%'
  ORDER BY relevance_score DESC
  LIMIT 5
$$;

-- Cortex Agentから呼び出し
SELECT * FROM TABLE(DB_DESIGN.SEARCH_DESIGN_DOCS('ANKEN_MEISAI'));
```

### 使用例

#### 例1：テーブル設計意図の質問
```
User: "ANKEN_MEISAIテーブルの設計意図を教えて"

Cortex Agent:
  1. DB_DESIGN.SEARCH_DESIGN_DOCS('ANKEN_MEISAI') で設計ドキュメントを検索
  2. design.ANKEN_MEISAI.md の内容を取得
  3. "概要"と"設計方針"セクションを抽出
  4. 自然言語で回答生成

Response: 
"ANKEN_MEISAIテーブルは、取込先（案件明細）のランディングテーブルです。
外部システムから受け取ったデータをそのまま格納し、制約を設けずに取込安定性を優先する設計です。"
```

#### 例2：カラムの意味を質問
```
User: "ANKEN_MEISAIのSHOHIN_CODE_RAWって何？"

Cortex Agent:
  1. カラム定義を検索: 
     SELECT file_content FROM DB_DESIGN.DOCS_OBSIDIAN 
     WHERE file_path LIKE '%ANKEN_MEISAI.SHOHIN_CODE_RAW.md'
  2. commentフィールドを抽出
  3. 回答生成

Response:
"SHOHIN_CODE_RAWは、外部システムから受け取った商品コードの生の値です。
正規化・変換前の元データを保持するためのカラムです。"
```

## セキュリティ設計

### 暗号化

#### サーバーサイド暗号化（SSE）
- 方式：SSE-S3（AES-256）
- 理由：設計ドキュメントには機密情報（テーブル構造、業務ロジック）が含まれる

```json
{
  "Rules": [
    {
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      },
      "BucketKeyEnabled": true
    }
  ]
}
```

### アクセス制御

#### IAMポリシー（Snowflake用・読み取り専用）
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::snowflake-chatdemo-vault-prod",
        "arn:aws:s3:::snowflake-chatdemo-vault-prod/*"
      ]
    }
  ]
}
```

#### IAMポリシー（同期スクリプト用・書き込み可）
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::snowflake-chatdemo-vault-prod",
        "arn:aws:s3:::snowflake-chatdemo-vault-prod/*"
      ]
    }
  ]
}
```

#### バケットポリシー
パブリックアクセスをブロック：
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyPublicReadAccess",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::snowflake-chatdemo-vault-prod/*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalAccount": "123456789012"
        }
      }
    }
  ]
}
```

### Snowflake側のアクセス制御
```sql
-- DB設計ドキュメントへのアクセスは、開発者とCortex Agentのみ
GRANT SELECT ON DB_DESIGN.DOCS_OBSIDIAN TO ROLE DEVELOPER;
GRANT SELECT ON DB_DESIGN.DOCS_OBSIDIAN TO ROLE AGENT_ROLE;

-- 一般ユーザーには非公開
REVOKE SELECT ON DB_DESIGN.DOCS_OBSIDIAN FROM ROLE PUBLIC;
```

## バージョン管理

### S3バージョニング
有効化：設計ドキュメントの変更履歴を追跡

```json
{
  "Status": "Enabled"
}
```

#### バージョニングの利点
- 誤って削除・上書きした場合の復旧
- 設計変更の履歴を追跡（いつ、どのファイルが変更されたか）
- Cortex Agentが過去の設計バージョンを参照可能

#### ライフサイクルポリシー（非最新バージョン）
```json
{
  "Rules": [
    {
      "Id": "DeleteOldVersions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
```

### Git連携
- 正の根拠（Source of Truth）：GitHubリポジトリ（`docs/snowflake/chatdemo/`）
- S3：Snowflakeからの参照用コピー
- 同期フロー：Git push → GitHub Actions → S3 sync → Snowflake REFRESH

## コスト見積もり

### 前提条件
- Vault全体のサイズ：約50MB（Markdownファイル）
- 月次更新頻度：50回（設計変更）
- バージョン保持：最新 + 過去90日分

### ストレージコスト

| 項目 | サイズ | ストレージクラス | 単価 | 月額コスト |
|------|-------|---------------|------|----------|
| 最新版 | 50MB | S3 Standard | $0.023/GB | $0.0012 |
| 過去バージョン | 150MB（3ヶ月分） | S3 Standard | $0.023/GB | $0.0035 |

月次合計：約$0.005（1円未満）

### API リクエストコスト
- LIST操作：10回/日（Snowflake REFRESH） × 30日 = 300回 → $0.0015
- GET操作：1,000回/日（Cortex Agent照会） × 30日 = 30,000回 → $0.012
- PUT操作：50回/月（更新） → $0.00025

API合計：約$0.014/月

### データ転送コスト
- S3 → Snowflake：同一リージョン（us-east-1）なら無料
- GitHub Actions → S3：無料（AWS内）

### 総コスト見積もり
- ストレージ：$0.005/月
- API：$0.014/月
- 合計：約$0.02/月（2円程度）

## 運用設計

### 同期フロー（詳細）

#### ステップ1：ローカル編集（Obsidian）
```
C:\Users\Owner\Documents\snowflake-db\ (Windows側)
  ↓ 手動編集
design/APP_PRODUCTION/design.NEW_TABLE.md
```

#### ステップ2：WSL側へ同期
```bash
# 手動コピー（現在の運用）
cp /mnt/c/Users/Owner/Documents/snowflake-db/design/APP_PRODUCTION/design.NEW_TABLE.md \
   /home/yolo/pg/snowflake_chatdemo/docs/snowflake/chatdemo/design/APP_PRODUCTION/
```

#### ステップ3：Git commit & push
```bash
cd /home/yolo/pg/snowflake_chatdemo
git add docs/snowflake/chatdemo/design/APP_PRODUCTION/design.NEW_TABLE.md
git commit -m "Add design for NEW_TABLE"
git push origin main
```

#### ステップ4：GitHub Actions → S3 sync
```yaml
# 自動実行（push時）
- name: Sync to S3
  run: |
    aws s3 sync docs/snowflake/chatdemo/ \
      s3://snowflake-chatdemo-vault-prod/ \
      --exclude ".obsidian/*"
```

#### ステップ5：Snowflake External Table REFRESH
```sql
-- 手動実行（初期）
ALTER EXTERNAL TABLE DB_DESIGN.DOCS_OBSIDIAN REFRESH;

-- または、AUTO_REFRESH=TRUE で自動（数分後）
```

#### ステップ6：Cortex Agent参照可能
```sql
-- Cortex Agentが新しい設計ドキュメントを参照可能
SELECT file_content 
FROM DB_DESIGN.DOCS_OBSIDIAN 
WHERE file_path LIKE '%design.NEW_TABLE.md';
```

### モニタリング

#### CloudWatch メトリクス
- BucketSize：Vaultサイズの推移（異常な増加を検知）
- NumberOfObjects：ファイル数の推移
- GetRequests：Cortex Agentのアクセス頻度

#### Snowflake側モニタリング
```sql
-- External Tableの最終REFRESH時刻を確認
SELECT SYSTEM$EXTERNAL_TABLE_METADATA('DB_DESIGN.DOCS_OBSIDIAN');

-- Cortex Agentのドキュメント参照頻度
SELECT 
  DATE_TRUNC('day', timestamp) AS day,
  COUNT(*) AS access_count
FROM LOG.CORTEX_CONVERSATIONS
WHERE message_content:text ILIKE '%DOCS_OBSIDIAN%'
GROUP BY 1
ORDER BY 1 DESC;
```

### トラブルシューティング

#### 問題1：S3同期が失敗
```bash
# 手動で再同期
aws s3 sync docs/snowflake/chatdemo/ \
  s3://snowflake-chatdemo-vault-prod/ \
  --dryrun  # まずdryrunで確認

# 実行
aws s3 sync docs/snowflake/chatdemo/ \
  s3://snowflake-chatdemo-vault-prod/ \
  --delete
```

#### 問題2：Snowflake External TableがREFRESHされない
```sql
-- 手動REFRESH
ALTER EXTERNAL TABLE DB_DESIGN.DOCS_OBSIDIAN REFRESH;

-- AUTO_REFRESHの状態確認
SHOW EXTERNAL TABLES IN SCHEMA DB_DESIGN;
```

#### 問題3：Cortex Agentがドキュメントを見つけられない
```sql
-- ファイルパスの確認
SELECT file_path 
FROM DB_DESIGN.DOCS_OBSIDIAN 
WHERE file_path LIKE '%ANKEN_MEISAI%';

-- 全文検索の動作確認
SELECT * 
FROM TABLE(DB_DESIGN.SEARCH_DESIGN_DOCS('ANKEN_MEISAI'));
```

## 拡張計画

### 1. Cortex Search統合
Snowflake Cortex Searchを使用した高度な検索：
```sql
-- ベクトル検索でセマンティックに類似したドキュメントを検索
CREATE CORTEX SEARCH SERVICE DB_DESIGN.VAULT_SEARCH
  ON file_content
  USING DB_DESIGN.DOCS_OBSIDIAN;

-- 使用例
SELECT * 
FROM TABLE(DB_DESIGN.VAULT_SEARCH!SEARCH('案件明細の設計方針'));
```

### 2. 差分検知と通知
設計ドキュメントが更新された際にSlack通知：
```sql
CREATE OR REPLACE TASK notify_design_changes
  WAREHOUSE = MONITORING_WH
  SCHEDULE = '10 MINUTE'
AS
BEGIN
  -- 最終REFRESH後に追加・変更されたファイルを検出
  INSERT INTO DB_DESIGN.CHANGE_LOG
  SELECT file_path, last_modified, 'updated'
  FROM DB_DESIGN.DOCS_OBSIDIAN
  WHERE last_modified > (SELECT MAX(check_time) FROM DB_DESIGN.CHANGE_LOG);
  
  -- Slack通知
  CALL notify_slack('New design documents updated: ' || 
    (SELECT LISTAGG(file_path, ', ') FROM DB_DESIGN.CHANGE_LOG WHERE created_at >= CURRENT_TIMESTAMP() - INTERVAL '10 minute'));
END;
```

### 3. 自動設計レビュー
新しい設計ドキュメントがS3にアップロードされたら、Cortex Agentが自動レビュー：
```sql
CREATE OR REPLACE TASK auto_design_review
  WAREHOUSE = AGENT_WH
  SCHEDULE = '30 MINUTE'
AS
BEGIN
  -- 未レビューの設計ドキュメントを抽出
  FOR record IN (
    SELECT file_path, file_content
    FROM DB_DESIGN.DOCS_OBSIDIAN
    WHERE file_path LIKE 'design/%'
      AND file_path NOT IN (SELECT file_path FROM DB_DESIGN.REVIEW_RESULTS)
  ) DO
    -- Cortex Agentでレビュー実行
    CALL APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT(
      'この設計ドキュメントをレビューしてください: ' || record.file_content
    );
    
    -- レビュー結果を記録
    INSERT INTO DB_DESIGN.REVIEW_RESULTS (file_path, review_result, reviewed_at)
    VALUES (record.file_path, LAST_QUERY_ID(), CURRENT_TIMESTAMP());
  END FOR;
END;
```

### 4. マルチ言語対応
設計ドキュメントを英語・中国語にも翻訳：
```
design/
  ├── ja/  # 日本語（デフォルト）
  │   └── APP_PRODUCTION/
  │       └── design.ANKEN_MEISAI.md
  ├── en/  # 英語
  │   └── APP_PRODUCTION/
  │       └── design.ANKEN_MEISAI.md
  └── zh/  # 中国語
      └── APP_PRODUCTION/
          └── design.ANKEN_MEISAI.md
```

Cortex Agentが言語を自動判定して適切なドキュメントを参照。

## 設計レビュー時のチェックポイント
- [ ] S3バケットが作成され、暗号化が有効化されているか
- [ ] IAMポリシーが最小権限の原則に従っているか（読み取り専用 for Snowflake）
- [ ] バージョニングが有効化されているか（設計変更履歴の追跡）
- [ ] GitHub Actions同期フローが正常動作するか
- [ ] Snowflake External Tableが正しく定義され、AUTO_REFRESH が動作するか
- [ ] Cortex AgentがDOCS_OBSIDIANテーブルにアクセス可能か
- [ ] 検索機能（SEARCH_DESIGN_DOCS）が正常動作するか
- [ ] コスト見積もりが妥当か（月$0.02程度）

## 参考リンク
- Snowflake External Tables: https://docs.snowflake.com/en/sql-reference/sql/create-external-table
- Snowflake Cortex Search: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search
- AWS S3 Versioning: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
- GitHub Actions - AWS S3 Sync: https://github.com/jakejarvis/s3-sync-action
