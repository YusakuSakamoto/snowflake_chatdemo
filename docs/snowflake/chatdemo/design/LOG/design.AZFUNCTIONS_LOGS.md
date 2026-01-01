# 外部テーブル設計：[[AZFUNCTIONS_LOGS]]

## 概要
[[LOG.AZFUNCTIONS_LOGS]] は、Azure Functions（バックエンドAPI）のアプリケーションログを集約・分析するための外部テーブルである。

本テーブルは、Python製のAzure Functions が出力するログを、S3経由でSnowflakeから直接クエリ可能にする。  
関数の実行時間、エラー率、呼び出し頻度などを長期的に追跡できる。

## 業務上の意味
- このテーブルが表す概念  
  1レコードは「1つのログエントリ」を表す。  
  INFO / WARNING / ERROR レベルのログが時系列で記録される。

- 主な利用シーン  
  - 関数のパフォーマンス分析（P50/P99レイテンシ）
  - エラーパターンの特定とデバッグ
  - API呼び出し頻度の監視
  - コスト分析（実行時間×呼び出し回数）

## 設計上の位置づけ
[[LOG.AZFUNCTIONS_LOGS]] は、以下のアプリケーションスタックの一部として機能する：

- フロントエンド（Azure SWA / Next.js）
- バックエンドAPI（Azure Functions） ← 本テーブル
- データベース（Snowflake）
- AI Agent（Cortex Agent）

これらのログを横断的に分析することで、リクエストの全体フローを追跡できる。

## 設計方針

### 外部テーブルを採用する理由
[[LOG]].AZFUNCTIONS_LOGSでも、EXTERNAL TABLE（外部テーブル） を採用する理由は [[LOG.CORTEX_CONVERSATIONS]] と同様：
- コスト最適化（S3ストレージの安価性）
- 柔軟な保持期間管理（古いログの自動アーカイブ）
- スキーマ進化の容易性

### パーティション設計
S3パス構造：
```
s3://snowflake-chatdemo-vault-prod/logs/azfunctions/
  year=2026/
    month=01/
      day=02/
        hour=14/
          {uuid}.json
```

時系列クエリでは必ず `year`, `month`, `day` を指定してパーティションプルーニングを有効化すること。

## カラム設計の判断

### 各カラムの設計意図

#### `log_id` (VARCHAR)
- 意味：1つのログエントリを一意識別するID
- 生成方法：ログ出力時に UUID 生成
- 利用例：特定のエラーログを追跡

#### `function_name` (VARCHAR)
- 意味：どのAzure Functionが実行されたか
- 値例：`HttpTrigger1`, `stream_endpoint`, `snowflake_cortex`
- 利用例：関数ごとのエラー率・実行時間分析

```sql
-- 関数ごとのP99レイテンシ
SELECT function_name,
       APPROX_PERCENTILE(duration_ms, 0.99) AS p99_latency_ms
FROM LOG.AZFUNCTIONS_LOGS
WHERE year = 2026 AND month = 1
  AND duration_ms IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC;
```

#### `invocation_id` (VARCHAR)
- 意味：Azure Functions の実行単位ID（Azureが自動付与）
- 利用例：分散トレーシング（1リクエストに対する複数ログの関連付け）

#### `level` (VARCHAR)
- 意味：ログレベル
- 値：`INFO` / `WARNING` / `ERROR`
- 利用例：エラーログのみを抽出

```sql
-- エラー頻度の高い関数TOP5
SELECT function_name, COUNT(*) AS error_count
FROM LOG.AZFUNCTIONS_LOGS
WHERE level = 'ERROR'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 5;
```

#### `message` (VARCHAR)
- 意味：ログメッセージ本文
- 利用例：特定のエラーメッセージを検索

```sql
-- "Timeout" を含むエラーログ
SELECT function_name, timestamp, message
FROM LOG.AZFUNCTIONS_LOGS
WHERE level = 'ERROR'
  AND message ILIKE '%timeout%'
  AND year = 2026 AND month = 1;
```

#### `timestamp` (TIMESTAMP_NTZ)
- 意味：ログが出力された日時（UTC）
- 利用例：時系列分析、エラー発生時刻の特定

#### `duration_ms` (NUMBER, nullable)
- 意味：関数の実行時間（ミリ秒）
- NULL の場合：エラーで途中終了、またはログ開始時点のエントリ
- 利用例：パフォーマンス分析、SLA監視

```sql
-- 実行時間が3秒を超えた関数呼び出し
SELECT function_name, timestamp, duration_ms
FROM LOG.AZFUNCTIONS_LOGS
WHERE duration_ms > 3000
  AND year = 2026 AND month = 1
ORDER BY duration_ms DESC;
```

#### `status_code` (NUMBER, nullable)
- 意味：HTTPステータスコード（200, 400, 500など）
- NULL の場合：HTTP関連ではないログエントリ
- 利用例：エラーレスポンスの統計

```sql
-- ステータスコード別の集計
SELECT status_code,
       COUNT(*) AS count
FROM LOG.AZFUNCTIONS_LOGS
WHERE status_code IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC;
```

#### `exception` (VARIANT)
- 意味：例外が発生した場合のスタックトレースとエラー詳細
- 構造例：
```json
{
  "type": "SnowflakeConnectionError",
  "message": "Failed to connect to Snowflake",
  "stacktrace": "...",
  "context": {
    "user_id": "USER_123",
    "request_id": "REQ_456"
  }
}
```
- 利用例：例外タイプ別の集計

```sql
-- 例外タイプ別の発生頻度
SELECT exception:type::VARCHAR AS exception_type,
       COUNT(*) AS count
FROM LOG.AZFUNCTIONS_LOGS
WHERE exception IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC;
```

#### `metadata` (VARIANT)
- 意味：追加のコンテキスト情報（リクエストヘッダ、環境変数など）
- 利用例：特定の環境やユーザーに関連するログを抽出

#### パーティションカラム（`year`, `month`, `day`, `hour`）
- [[LOG.CORTEX_CONVERSATIONS]] と同様

## クエリパターン例

### パターン1：エラー率の時系列推移
```sql
SELECT DATE_TRUNC('hour', timestamp) AS hour,
       COUNT(*) AS total,
       COUNT_IF(level = 'ERROR') AS errors,
       ROUND(errors / total * 100, 2) AS error_rate_pct
FROM LOG.AZFUNCTIONS_LOGS
WHERE year = 2026 AND month = 1 AND day = 2
GROUP BY 1
ORDER BY 1;
```

### パターン2：関数別の平均・P95・P99レイテンシ
```sql
SELECT function_name,
       AVG(duration_ms) AS avg_ms,
       APPROX_PERCENTILE(duration_ms, 0.95) AS p95_ms,
       APPROX_PERCENTILE(duration_ms, 0.99) AS p99_ms
FROM LOG.AZFUNCTIONS_LOGS
WHERE duration_ms IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY p99_ms DESC;
```

### パターン3：特定の例外が発生したリクエスト
```sql
SELECT invocation_id,
       function_name,
       timestamp,
       exception:message::VARCHAR AS error_message,
       exception:stacktrace::VARCHAR AS stacktrace
FROM LOG.AZFUNCTIONS_LOGS
WHERE exception:type::VARCHAR = 'SnowflakeConnectionError'
  AND year = 2026 AND month = 1;
```

### パターン4：SLA違反（レスポンスタイム > 3秒）の件数
```sql
SELECT function_name,
       COUNT(*) AS sla_violations
FROM LOG.AZFUNCTIONS_LOGS
WHERE duration_ms > 3000
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC;
```

## 運用上の注意

### ログの書き込みフロー
1. Azure Functions が実行され、Pythonの`logging`モジュールでログ出力
2. Application Insights → Azure Stream Analytics → S3 へ転送
3. または、直接 AWS SDK で S3 へ PUT
4. Snowflake が AUTO_REFRESH で自動検知

### データ保持ポリシー
- 直近7日：頻繁にクエリされるため、内部テーブルへコピー（任意）
- 8-90日：S3 Standard（外部テーブルで直接クエリ）
- 91-365日：S3 Intelligent-Tiering
- 1年超：S3 Glacier（アーカイブ）

## セキュリティ・プライバシー

### 機密情報のマスキング
- ログに認証トークンやAPIキーが含まれないよう、アプリケーション側でフィルタリング
- `metadata` 内にPII（個人情報）が含まれる場合はマスキングポリシーを適用

### アクセス制御
```sql
GRANT SELECT ON LOG.AZFUNCTIONS_LOGS TO ROLE LOG_VIEWER;
```

## 今後の拡張計画

### マテリアライズドビューによる高速化
```sql
CREATE MATERIALIZED VIEW LOG.MV_HOURLY_FUNCTION_METRICS AS
SELECT DATE_TRUNC('hour', timestamp) AS hour,
       function_name,
       COUNT(*) AS total_invocations,
       COUNT_IF(level = 'ERROR') AS errors,
       AVG(duration_ms) AS avg_duration_ms,
       APPROX_PERCENTILE(duration_ms, 0.99) AS p99_duration_ms
FROM LOG.AZFUNCTIONS_LOGS
WHERE year >= 2026
GROUP BY 1, 2;
```

### アラート設定
```sql
CREATE ALERT high_function_error_rate
  WAREHOUSE = MONITORING_WH
  SCHEDULE = '10 MINUTE'
  IF EXISTS (
    SELECT 1 FROM LOG.MV_HOURLY_FUNCTION_METRICS
    WHERE hour >= DATEADD('hour', -1, CURRENT_TIMESTAMP())
      AND errors / NULLIF(total_invocations, 0) > 0.05
  )
  THEN CALL notify_slack('High error rate in Azure Functions!');
```

## 設計レビュー時のチェックポイント
- [ ] エラー率が許容範囲内か（目標: <1%）
- [ ] P99レイテンシが目標内か（目標: <3秒）
- [ ] SLA違反（>3秒）の件数が許容範囲内か
- [ ] 機密情報がログに出力されていないか
