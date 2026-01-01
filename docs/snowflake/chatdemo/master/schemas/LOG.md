---
type: schema
schema_id: SCH_20260102000001
physical: LOG
comment: アプリケーションログ集約（S3外部ステージ）
---

# LOG

## 概要
全アプリケーションのログをS3経由で集約するスキーマ。外部テーブルによるパーティション管理でコスト最適化を実現。

## 格納データ
- Cortex Agent会話ログ
- Azure Functionsログ
- Azure Static Web Appsログ
- Snowflakeメトリクスログ

## 技術詳細
- ストレージ: S3外部ステージ
- パーティション: year/month/day/hour
- フォーマット: JSON Lines (NDJSON)
