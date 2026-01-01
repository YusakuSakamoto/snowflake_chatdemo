# Logging Schema (ログスキーマ)

> [!info] 概要
> アプリケーション全体のログを集約するスキーマ

## 📊 基本情報

| 項目 | 内容 |
|------|------|
| **スキーマ名** | `LOGGING` |
| **データベース** | `ANALYTICS_DB` |
| **作成日** | 2026-01-02 |
| **目的** | 全ログの一元管理とS3外部ステージ統合 |

**タグ**: #スキーマ #ログ #監視

---

## 🏗️ スキーマ作成

```sql
CREATE DATABASE IF NOT EXISTS ANALYTICS_DB;
CREATE SCHEMA IF NOT EXISTS ANALYTICS_DB.LOGGING;
```

## 📋 含まれるテーブル

### 1. アプリケーションログ
- [[tables/cortex_conversation_logs]] - Cortex Agent対話履歴
- [[tables/azure_functions_logs]] - Azure Functions実行ログ
- [[tables/swa_logs]] - Static Web Appsアクセスログ

### 2. データベースメトリクス
- [[tables/snowflake_query_metrics]] - クエリ実行メトリクス
- [[tables/snowflake_warehouse_metrics]] - ウェアハウス使用量
- [[tables/snowflake_storage_metrics]] - ストレージメトリクス

### 3. 設計変更履歴
- [[tables/schema_changes]] - DDL変更ログ

## 🗂️ S3バケット構造

```
s3://your-bucket/logs/
├── cortex_logs/
│   └── year=2026/month=01/day=02/
├── functions_logs/
│   └── year=2026/month=01/day=02/
├── swa_logs/
│   └── year=2026/month=01/day=02/
└── snowflake_metrics/
    ├── query_history/
    │   └── year=2026/month=01/day=02/hour=15/
    ├── warehouse_usage/
    │   └── year=2026/month=01/day=02/hour=15/
    └── storage/
        └── year=2026/month=01/day=02/
```

## 🚀 外部ステージ設定

```sql
-- Cortexログ用ステージ
CREATE STAGE LOGGING.s3_cortex_logs_stage
  URL = 's3://your-bucket/logs/cortex_logs/'
  CREDENTIALS = (AWS_KEY_ID = '...' AWS_SECRET_KEY = '...')
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = TRUE);

-- Azure Functionsログ用ステージ
CREATE STAGE LOGGING.s3_functions_logs_stage
  URL = 's3://your-bucket/logs/functions_logs/'
  CREDENTIALS = (AWS_KEY_ID = '...' AWS_SECRET_KEY = '...')
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = TRUE);

-- SWAログ用ステージ
CREATE STAGE LOGGING.s3_swa_logs_stage
  URL = 's3://your-bucket/logs/swa_logs/'
  CREDENTIALS = (AWS_KEY_ID = '...' AWS_SECRET_KEY = '...')
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = TRUE);

-- Snowflakeメトリクス用ステージ
CREATE STAGE LOGGING.s3_snowflake_metrics_stage
  URL = 's3://your-bucket/logs/snowflake_metrics/'
  CREDENTIALS = (AWS_KEY_ID = '...' AWS_SECRET_KEY = '...')
  DIRECTORY = (ENABLE = TRUE AUTO_REFRESH = TRUE);
```

## 📈 分析ビュー

### 統合ログビュー
```sql
CREATE VIEW LOGGING.unified_logs AS
SELECT 
    'CORTEX' as log_source,
    timestamp,
    session_id as trace_id,
    user_message as message,
    metadata
FROM LOGGING.cortex_conversation_logs
UNION ALL
SELECT 
    'FUNCTIONS' as log_source,
    timestamp,
    request_id as trace_id,
    message,
    metadata
FROM LOGGING.azure_functions_logs
UNION ALL
SELECT 
    'SWA' as log_source,
    timestamp,
    request_id as trace_id,
    url as message,
    metadata
FROM LOGGING.swa_logs;
```

## 🔐 アクセス権限

```sql
-- データエンジニア用ロール
GRANT USAGE ON SCHEMA LOGGING TO ROLE data_engineer;
GRANT SELECT ON ALL TABLES IN SCHEMA LOGGING TO ROLE data_engineer;
GRANT SELECT ON ALL EXTERNAL TABLES IN SCHEMA LOGGING TO ROLE data_engineer;

-- 分析者用ロール（読み取りのみ）
GRANT USAGE ON SCHEMA LOGGING TO ROLE analyst;
GRANT SELECT ON ALL VIEWS IN SCHEMA LOGGING TO ROLE analyst;
```

## ⚠️ 運用ルール

### データ保持期間
- **Cortex対話ログ**: 1年間
- **Azure Functions/SWAログ**: 3ヶ月
- **Snowflakeメトリクス**: 無期限（コスト分析用）

### バックアップ
- S3にすべてのデータが保存されているため、Snowflake側の削除は問題なし
- S3バケットはバージョニング有効化

### モニタリング
- 外部テーブルの自動リフレッシュ状態を監視
- パーティションの欠損チェック（日次）

## 🔄 変更履歴

| 日付 | 変更内容 | 担当者 |
|------|----------|--------|
| 2026-01-02 | 初版作成 - スキーマ設計 | - |

## 🔍 関連ドキュメント

- [[reviews/log_architecture]] - ログアーキテクチャ全体設計
- [[migrations/2026-01-02_create_logging_schema]]
