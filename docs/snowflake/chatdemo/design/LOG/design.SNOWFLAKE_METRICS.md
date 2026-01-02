# 外部テーブル設計：[[design.SNOWFLAKE_METRICS]]

## 概要
[[LOG.SNOWFLAKE_METRICS]] は、Snowflake自体のクエリ実行メトリクスとリソース使用状況を蓄積・分析するための外部テーブルである。

本テーブルは、Snowflakeの `INFORMATION_SCHEMA` や `ACCOUNT_USAGE` から定期的にエクスポートされたメトリクスデータを、S3経由で長期保管する。  
コスト分析、パフォーマンス最適化、容量計画の根拠データとして活用される。

## 業務上の意味
- このテーブルが表す概念  
  1レコードは「1つのメトリクス測定値」を表す。  
  クエリ実行時間、スキャンデータ量、ウェアハウスのクレジット消費量などが記録される。

- 主な利用シーン  
  - コスト分析（どのクエリが高コストか）
  - パフォーマンス最適化（遅いクエリの特定）
  - ウェアハウスサイジング（適切なサイズの判断）
  - 容量計画（ストレージ使用量の予測）

## 設計上の位置づけ
[[LOG.SNOWFLAKE_METRICS]] は、以下のシステム全体の「観測性の基盤」として機能する：

- アプリケーションログ（SWA, Azure Functions）
- Cortex Agent 会話ログ
- Snowflake メトリクス ← 本テーブル（データベース層の健全性）

これらを統合的に分析することで、システム全体のボトルネックを特定できる。

## 設計方針

### 外部テーブルを採用する理由
メトリクスデータは膨大になる可能性があるため、EXTERNAL TABLE を採用：
- 長期保管でもコストを抑制（S3 Glacier へのアーカイブ）
- 必要な期間だけクエリすることでコンピュートコストを最小化

### パーティション設計
S3パス構造：
```
s3://snowflake-chatdemo-vault-prod/logs/snowflake_metrics/
  YEAR=2026/
    MONTH=01/
      DAY=02/
        HOUR=14/
          {uuid}.json
```

## カラム設計の判断

### 各カラムの設計意図

#### metric_id (VARCHAR)
- 意味：1つのメトリクス測定値を一意識別するID
- 生成方法：メトリクス収集時に UUID 生成

#### metric_name (VARCHAR)
- 意味：メトリクスの種別
- 値例：
  - `query_execution_time` : クエリ実行時間（秒）
  - `bytes_scanned` : スキャンされたデータ量（バイト）
  - `credits_used` : ウェアハウスのクレジット消費量
  - `rows_produced` : クエリが返した行数
  - `compilation_time` : クエリコンパイル時間
  - `storage_bytes` : ストレージ使用量

#### metric_value (NUMBER)
- 意味：メトリクスの測定値（数値）
- 利用例：時系列での推移グラフ、統計計算

```sql
-- クエリ実行時間の日次平均
SELECT DATE_TRUNC('day', timestamp) AS day,
       AVG(metric_value) AS avg_execution_sec
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'query_execution_time'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1;
```

#### warehouse_name (VARCHAR, nullable)
- 意味：どのウェアハウスでクエリが実行されたか
- NULL の場合：ウェアハウスに依存しないメトリクス（例：ストレージ使用量）
- 利用例：ウェアハウスごとのコスト・パフォーマンス分析

```sql
-- ウェアハウスごとのクレジット消費量
SELECT warehouse_name,
       SUM(metric_value) AS total_credits
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'credits_used'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC;
```

#### query_id (VARCHAR, nullable)
- 意味：Snowflakeのクエリ実行ID
- 利用例：特定のクエリの詳細分析、`QUERY_HISTORY` との紐付け

```sql
-- 実行時間が長いクエリTOP10
SELECT query_id,
       MAX(metric_value) AS execution_time_sec
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'query_execution_time'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

#### user_name (VARCHAR, nullable)
- 意味：クエリを実行したユーザー名
- 利用例：ユーザーごとのクエリ実行頻度、コスト配分

```sql
-- ユーザーごとのクエリ実行回数
SELECT user_name,
       COUNT(DISTINCT query_id) AS query_count
FROM LOG.SNOWFLAKE_METRICS
WHERE query_id IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC;
```

#### timestamp (TIMESTAMP_NTZ)
- 意味：メトリクスが測定された日時（UTC）
- 利用例：時系列分析、ピーク時間帯の特定

#### metadata (VARIANT)
- 意味：追加のコンテキスト情報
- 構造例：
```json
{
  "database_name": "GBPS253YS_DB",
  "schema_name": "APP_PRODUCTION",
  "table_name": "ANKEN_MEISAI",
  "query_type": "SELECT",
  "execution_status": "SUCCESS"
}
```
- 利用例：データベース別・テーブル別のアクセス統計

```sql
-- テーブル別のスキャンデータ量
SELECT metadata:table_name::VARCHAR AS table_name,
       SUM(metric_value) / 1024 / 1024 / 1024 AS total_gb_scanned
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'bytes_scanned'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC;
```

#### パーティションカラム（YEAR, MONTH, DAY, HOUR）
- [[LOG.CORTEX_CONVERSATIONS]] と同様

## データソースと収集方法

### 1. INFORMATION_SCHEMA.QUERY_HISTORY
リアルタイムに近いクエリ実行情報を取得：
```sql
-- 定期タスク（1時間ごと）でメトリクスを抽出
CREATE TASK collect_query_metrics
  WAREHOUSE = ETL_WH
  SCHEDULE = '60 MINUTE'
AS
INSERT INTO @LOG_STAGE/snowflake_metrics/YEAR={{YEAR}}/MONTH={{MONTH}}/DAY={{DAY}}/HOUR={{HOUR}}/metrics.json
SELECT 
  UUID_STRING() AS metric_id,
  'query_execution_time' AS metric_name,
  TOTAL_ELAPSED_TIME / 1000 AS metric_value,
  WAREHOUSE_NAME,
  QUERY_ID,
  USER_NAME,
  START_TIME AS timestamp,
  OBJECT_CONSTRUCT(
    'database_name', DATABASE_NAME,
    'schema_name', SCHEMA_NAME,
    'query_type', QUERY_TYPE
  ) AS metadata
FROM INFORMATION_SCHEMA.QUERY_HISTORY
WHERE START_TIME >= DATEADD('hour', -1, CURRENT_TIMESTAMP());
```

### 2. ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
ウェアハウスのクレジット消費量を取得：
```sql
-- 日次でクレジット消費量を集計
SELECT 
  UUID_STRING() AS metric_id,
  'credits_used' AS metric_name,
  CREDITS_USED AS metric_value,
  WAREHOUSE_NAME,
  NULL AS query_id,
  NULL AS user_name,
  START_TIME AS timestamp,
  NULL AS metadata
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= CURRENT_DATE() - 1;
```

### 3. ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
ストレージ使用量を取得：
```sql
-- 日次でストレージ使用量を記録
SELECT 
  UUID_STRING() AS metric_id,
  'storage_bytes' AS metric_name,
  AVERAGE_DATABASE_BYTES AS metric_value,
  NULL AS warehouse_name,
  NULL AS query_id,
  NULL AS user_name,
  USAGE_DATE AS timestamp,
  OBJECT_CONSTRUCT('database_name', DATABASE_NAME) AS metadata
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
WHERE USAGE_DATE >= CURRENT_DATE() - 1;
```

## クエリパターン例

### パターン1：ウェアハウスごとの月次コスト
```sql
SELECT warehouse_name,
       SUM(metric_value) * 3.00 AS estimated_cost_usd  -- 1クレジット=$3と仮定
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'credits_used'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC;
```

### パターン2：遅いクエリの特定（実行時間 > 60秒）
```sql
SELECT query_id,
       user_name,
       warehouse_name,
       metric_value AS execution_time_sec,
       timestamp
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'query_execution_time'
  AND metric_value > 60
  AND year = 2026 AND month = 1
ORDER BY metric_value DESC;
```

### パターン3：データスキャン量の多いテーブルTOP10
```sql
SELECT metadata:table_name::VARCHAR AS table_name,
       SUM(metric_value) / 1024 / 1024 / 1024 AS total_gb_scanned
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'bytes_scanned'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

### パターン4：ストレージ使用量の推移
```sql
SELECT DATE_TRUNC('day', timestamp) AS day,
       SUM(metric_value) / 1024 / 1024 / 1024 / 1024 AS total_tb
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'storage_bytes'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1;
```

## 運用上の注意

### メトリクス収集の頻度
- クエリ実行メトリクス：1時間ごと（リアルタイム性が必要）
- クレジット消費量：1日ごと（日次集計で十分）
- ストレージ使用量：1日ごと（変動が少ない）

### データ保持ポリシー
- 直近30日：頻繁にクエリされるため、内部テーブルへコピー（任意）
- 31-90日：S3 Standard（外部テーブルで直接クエリ）
- 91-365日：S3 Intelligent-Tiering
- 1年超：S3 Glacier（長期保管、監査用）

## 今後の拡張計画

### マテリアライズドビューによる高速化
```sql
CREATE MATERIALIZED VIEW LOG.MV_DAILY_COST_SUMMARY AS
SELECT DATE_TRUNC('day', timestamp) AS day,
       warehouse_name,
       SUM(CASE WHEN metric_name = 'credits_used' THEN metric_value ELSE 0 END) AS total_credits,
       SUM(CASE WHEN metric_name = 'credits_used' THEN metric_value ELSE 0 END) * 3.00 AS estimated_cost_usd
FROM LOG.SNOWFLAKE_METRICS
WHERE year >= 2026
GROUP BY 1, 2;
```

### アラート設定
```sql
CREATE ALERT high_warehouse_cost
  WAREHOUSE = MONITORING_WH
  SCHEDULE = '1 DAY'
  IF EXISTS (
    SELECT 1 FROM LOG.MV_DAILY_COST_SUMMARY
    WHERE day = CURRENT_DATE() - 1
      AND estimated_cost_usd > 100.00
  )
  THEN CALL notify_slack('Daily warehouse cost exceeded $100!');
```

### コスト予測モデル
過去のメトリクスを元に、将来のコストを予測：
```sql
-- 過去30日の平均クレジット消費量から、月次コストを予測
SELECT AVG(daily_credits) * 30 * 3.00 AS predicted_monthly_cost_usd
FROM (
  SELECT DATE_TRUNC('day', timestamp) AS day,
         SUM(metric_value) AS daily_credits
  FROM LOG.SNOWFLAKE_METRICS
  WHERE metric_name = 'credits_used'
    AND timestamp >= CURRENT_DATE() - 30
  GROUP BY 1
);
```

## 設計レビュー時のチェックポイント
- [ ] 月次コストが予算内か
- [ ] 遅いクエリ（>60秒）が特定・改善されているか
- [ ] ウェアハウスサイズが適切か（CPU使用率が80%前後が理想）
- [ ] ストレージ使用量の増加率が想定内か
