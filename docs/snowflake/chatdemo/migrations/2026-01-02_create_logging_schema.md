# Migration: Create Logging Schema

**作成日**: 2026-01-02  
**実行者**: -  
**ステータス**: 📝 準備中

---

## 📋 概要

ログ集約システムの基盤となるSnowflakeスキーマとS3外部ステージを作成します。

### 作成対象
- `ANALYTICS_DB`データベース
- `LOGGING`スキーマ
- S3外部ステージ（4種類）
- 外部テーブル（初期版）

---

## 🔧 前提条件

### AWS側
- [ ] S3バケット作成済み: `s3://your-bucket/logs/`
- [ ] IAMユーザー作成済み（Snowflake用）
- [ ] 必要な権限: `s3:GetObject`, `s3:GetObjectVersion`, `s3:ListBucket`

### Snowflake側
- [ ] `ACCOUNTADMIN`ロールでの実行権限
- [ ] ウェアハウス: `COMPUTE_WH`が利用可能

---

## 📝 実行SQL

### Step 1: データベースとスキーマ作成
```sql
-- データベース作成
CREATE DATABASE IF NOT EXISTS ANALYTICS_DB
  COMMENT = 'アナリティクスとログ管理用データベース';

USE DATABASE ANALYTICS_DB;

-- ロギングスキーマ作成
CREATE SCHEMA IF NOT EXISTS LOGGING
  COMMENT = 'アプリケーション全体のログを集約';

USE SCHEMA LOGGING;
```

### Step 2: ファイルフォーマット作成
```sql
-- JSON Lines形式
CREATE OR REPLACE FILE FORMAT json_format
  TYPE = JSON
  COMPRESSION = AUTO
  STRIP_OUTER_ARRAY = FALSE;

-- Parquet形式（将来用）
CREATE OR REPLACE FILE FORMAT parquet_format
  TYPE = PARQUET
  COMPRESSION = AUTO;
```

### Step 3: S3外部ステージ作成
```sql
-- ⚠️ 認証情報を実際の値に置き換えること
SET aws_key_id = 'YOUR_AWS_ACCESS_KEY_ID';
SET aws_secret = 'YOUR_AWS_SECRET_ACCESS_KEY';

-- Cortexログ用ステージ
CREATE OR REPLACE STAGE s3_cortex_logs_stage
  URL = 's3://your-bucket/logs/cortex_logs/'
  CREDENTIALS = (
    AWS_KEY_ID = $aws_key_id
    AWS_SECRET_KEY = $aws_secret
  )
  FILE_FORMAT = json_format
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = TRUE)
  COMMENT = 'Snowflake Cortex Agent対話ログ';

-- Azure Functionsログ用ステージ
CREATE OR REPLACE STAGE s3_functions_logs_stage
  URL = 's3://your-bucket/logs/functions_logs/'
  CREDENTIALS = (
    AWS_KEY_ID = $aws_key_id
    AWS_SECRET_KEY = $aws_secret
  )
  FILE_FORMAT = json_format
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = TRUE)
  COMMENT = 'Azure Functions実行ログ';

-- SWAログ用ステージ
CREATE OR REPLACE STAGE s3_swa_logs_stage
  URL = 's3://your-bucket/logs/swa_logs/'
  CREDENTIALS = (
    AWS_KEY_ID = $aws_key_id
    AWS_SECRET_KEY = $aws_secret
  )
  FILE_FORMAT = json_format
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = TRUE)
  COMMENT = 'Static Web Appsアクセスログ';

-- Snowflakeメトリクス用ステージ
CREATE OR REPLACE STAGE s3_snowflake_metrics_stage
  URL = 's3://your-bucket/logs/snowflake_metrics/'
  CREDENTIALS = (
    AWS_KEY_ID = $aws_key_id
    AWS_SECRET_KEY = $aws_secret
  )
  FILE_FORMAT = json_format
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = TRUE)
  COMMENT = 'Snowflakeメトリクスデータ';
```

### Step 4: 外部テーブル作成（Cortexログ）
```sql
CREATE OR REPLACE EXTERNAL TABLE cortex_conversation_logs (
    session_id VARCHAR AS (value:session_id::VARCHAR),
    user_id VARCHAR AS (value:user_id::VARCHAR),
    timestamp TIMESTAMP_NTZ AS (value:timestamp::TIMESTAMP_NTZ),
    user_message VARCHAR AS (value:user_message::VARCHAR),
    agent_response VARCHAR AS (value:agent_response::VARCHAR),
    sql_executed VARCHAR AS (value:sql_executed::VARCHAR),
    tools_used ARRAY AS (value:tools_used::ARRAY),
    execution_time_ms NUMBER AS (value:execution_time_ms::NUMBER),
    tokens_used NUMBER AS (value:tokens_used::NUMBER),
    error_message VARCHAR AS (value:error_message::VARCHAR),
    metadata VARIANT AS (value:metadata::VARIANT),
    
    -- パーティションカラム
    year INT AS (SPLIT_PART(metadata$filename, '/', -4)),
    month INT AS (SPLIT_PART(metadata$filename, '/', -3)),
    day INT AS (SPLIT_PART(metadata$filename, '/', -2))
)
PARTITION BY (year, month, day)
LOCATION = @s3_cortex_logs_stage
FILE_FORMAT = json_format
AUTO_REFRESH = TRUE
COMMENT = 'Cortex Agent対話履歴（S3外部テーブル）';
```

### Step 5: 権限設定
```sql
-- データエンジニア用ロール
CREATE ROLE IF NOT EXISTS data_engineer;
GRANT USAGE ON DATABASE ANALYTICS_DB TO ROLE data_engineer;
GRANT USAGE ON SCHEMA LOGGING TO ROLE data_engineer;
GRANT SELECT ON ALL TABLES IN SCHEMA LOGGING TO ROLE data_engineer;
GRANT SELECT ON ALL EXTERNAL TABLES IN SCHEMA LOGGING TO ROLE data_engineer;

-- 分析者用ロール（読み取りのみ）
CREATE ROLE IF NOT EXISTS analyst;
GRANT USAGE ON DATABASE ANALYTICS_DB TO ROLE analyst;
GRANT USAGE ON SCHEMA LOGGING TO ROLE analyst;
GRANT SELECT ON ALL VIEWS IN SCHEMA LOGGING TO ROLE analyst;
```

---

## ✅ 動作確認

### 1. ステージ確認
```sql
SHOW STAGES IN SCHEMA LOGGING;

-- ステージ内のファイル確認
LIST @s3_cortex_logs_stage;
```

### 2. 外部テーブル確認
```sql
-- テーブル存在確認
SHOW EXTERNAL TABLES IN SCHEMA LOGGING;

-- メタデータリフレッシュ
ALTER EXTERNAL TABLE cortex_conversation_logs REFRESH;

-- データ確認（サンプル）
SELECT * FROM cortex_conversation_logs LIMIT 10;
```

### 3. パーティション確認
```sql
-- パーティション一覧
SELECT DISTINCT year, month, day
FROM cortex_conversation_logs
ORDER BY year DESC, month DESC, day DESC;
```

---

## 🔄 ロールバック手順

```sql
-- 外部テーブル削除
DROP EXTERNAL TABLE IF EXISTS cortex_conversation_logs;

-- ステージ削除
DROP STAGE IF EXISTS s3_cortex_logs_stage;
DROP STAGE IF EXISTS s3_functions_logs_stage;
DROP STAGE IF EXISTS s3_swa_logs_stage;
DROP STAGE IF EXISTS s3_snowflake_metrics_stage;

-- ファイルフォーマット削除
DROP FILE FORMAT IF EXISTS json_format;
DROP FILE FORMAT IF EXISTS parquet_format;

-- スキーマ削除（注意！）
-- DROP SCHEMA IF EXISTS LOGGING;
```

---

## ⚠️ 注意事項

1. **AWS認証情報**
   - 実際の値に置き換える
   - SecretsManagerの使用を推奨
   - IAMロールベース認証も検討

2. **S3バケット**
   - バケット名を実際の名前に変更
   - 暗号化設定の確認
   - バージョニング有効化推奨

3. **コスト**
   - S3リクエスト課金に注意
   - AUTO_REFRESHの頻度調整可能
   - 不要なパーティションは定期削除

4. **パフォーマンス**
   - 初回リフレッシュは時間がかかる可能性
   - ウェアハウスサイズの調整を検討

---

## 📊 想定されるリソース

| リソース | サイズ/数量 |
|---------|------------|
| S3ストレージ | 10GB/月（初期） |
| Snowflakeコンピュート | Small WH, 10min/日 |
| 外部テーブル数 | 4テーブル |
| パーティション数 | 〜90個/テーブル（3ヶ月分） |

---

## 🔗 関連ドキュメント

- [[schemas/logging]] - スキーマ設計
- [[tables/cortex_conversation_logs]] - Cortexログテーブル詳細
- [[reviews/log_architecture]] - アーキテクチャレビュー

## 📝 実行記録

| 実行日時 | 実行者 | 結果 | 備考 |
|---------|--------|------|------|
| - | - | - | - |
