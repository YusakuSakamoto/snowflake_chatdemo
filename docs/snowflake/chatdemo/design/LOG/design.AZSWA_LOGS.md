# 外部テーブル設計：[[AZSWA_LOGS]]

## 概要
[[LOG.AZSWA_LOGS]] は、Azure Static Web Apps（フロントエンド）のアクセスログを集約・分析するための外部テーブルである。

本テーブルは、Next.js製のフロントエンドが処理したHTTPリクエストのログを、S3経由でSnowflakeから直接クエリ可能にする。  
ユーザー行動、ページ閲覧数、エラー率などを長期的に追跡できる。

## 業務上の意味
- このテーブルが表す概念  
  1レコードは「1つのHTTPリクエスト」を表す。  
  ユーザーがどのページにアクセスし、どの程度の時間で応答したかが記録される。

- 主な利用シーン  
  - ユーザー行動分析（人気ページ、離脱率）
  - パフォーマンス監視（ページロード時間）
  - エラー監視（404, 500エラーの頻度）
  - セキュリティ分析（不審なアクセスパターン）

## 設計上の位置づけ
[[LOG.AZSWA_LOGS]] は、以下のフロー全体の最上流に位置する：

1. ユーザー → Azure SWA / Next.js ← 本テーブル
2. Azure SWA → Azure Functions（API呼び出し）
3. Azure Functions → Snowflake（データアクセス）
4. Snowflake → Cortex Agent（AI推論）

フロントエンドのログを分析することで、ユーザー体験の改善につながる。

## 設計方針

### 外部テーブルを採用する理由
[[LOG.CORTEX_CONVERSATIONS]] および [[LOG.AZFUNCTIONS_LOGS]] と同様の理由。

### パーティション設計
S3パス構造：
```
s3://snowflake-chatdemo-vault-prod/logs/azswa/
  year=2026/
    month=01/
      day=02/
        hour=14/
          {uuid}.json
```

## カラム設計の判断

### 各カラムの設計意図

#### `log_id` (VARCHAR)
- 意味：1つのHTTPリクエストを一意識別するID
- 生成方法：リクエスト処理時に UUID 生成

#### `request_id` (VARCHAR)
- 意味：Azure SWA が自動付与するリクエストID
- 利用例：フロントエンド（SWA）とバックエンド（Functions）のログを紐付け

```sql
-- フロントエンドとバックエンドのログを結合
SELECT s.timestamp AS frontend_time,
       s.url,
       s.status_code AS frontend_status,
       f.function_name,
       f.duration_ms AS backend_duration
FROM LOG.AZSWA_LOGS s
JOIN LOG.AZFUNCTIONS_LOGS f 
  ON s.request_id = f.metadata:request_id::VARCHAR
WHERE s.year = 2026 AND s.month = 1 AND s.day = 2;
```

#### `session_id` (VARCHAR, nullable)
- 意味：ユーザーセッションID（Cookieやローカルストレージから取得）
- 利用例：セッション単位の行動分析（訪問ページ数、滞在時間）

```sql
-- セッションごとのページビュー数
SELECT session_id,
       COUNT(*) AS page_views,
       MIN(timestamp) AS session_start,
       MAX(timestamp) AS session_end,
       TIMESTAMPDIFF(MINUTE, session_start, session_end) AS duration_min
FROM LOG.AZSWA_LOGS
WHERE session_id IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY page_views DESC;
```

#### `user_agent` (VARCHAR, nullable)
- 意味：ユーザーのブラウザ・デバイス情報
- 利用例：デバイス別の利用統計、ブラウザ互換性分析

```sql
-- ブラウザ別のアクセス数
SELECT 
  CASE
    WHEN user_agent ILIKE '%Chrome%' THEN 'Chrome'
    WHEN user_agent ILIKE '%Safari%' THEN 'Safari'
    WHEN user_agent ILIKE '%Firefox%' THEN 'Firefox'
    ELSE 'Other'
  END AS browser,
  COUNT(*) AS access_count
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1
GROUP BY 1;
```

#### `url` (VARCHAR)
- 意味：リクエストされたURL（パスとクエリパラメータ）
- 利用例：人気ページTOP10、離脱率の高いページ

```sql
-- 人気ページTOP10
SELECT url,
       COUNT(*) AS views
FROM LOG.AZSWA_LOGS
WHERE status_code = 200
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

#### `method` (VARCHAR)
- 意味：HTTPメソッド（GET, POST, PUT, DELETE）
- 利用例：APIエンドポイントごとのリクエスト分布

#### `status_code` (NUMBER)
- 意味：HTTPステータスコード（200, 404, 500など）
- 利用例：エラー率の監視

```sql
-- ステータスコード別の集計
SELECT status_code,
       COUNT(*) AS count,
       ROUND(count / SUM(count) OVER () * 100, 2) AS pct
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC;
```

#### `timestamp` (TIMESTAMP_NTZ)
- 意味：リクエストを受信した日時（UTC）
- 利用例：時間帯別のアクセス傾向分析

```sql
-- 時間帯別のアクセス数（JST変換）
SELECT HOUR(CONVERT_TIMEZONE('UTC', 'Asia/Tokyo', timestamp)) AS hour_jst,
       COUNT(*) AS access_count
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1;
```

#### `response_time_ms` (NUMBER, nullable)
- 意味：レスポンスタイム（ミリ秒）
- NULL の場合：測定できなかった、またはエラーで途中終了
- 利用例：ページ読み込み速度の分析

```sql
-- P95レスポンスタイム
SELECT url,
       APPROX_PERCENTILE(response_time_ms, 0.95) AS p95_ms
FROM LOG.AZSWA_LOGS
WHERE response_time_ms IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

#### `client_ip` (VARCHAR, nullable)
- 意味：クライアントのIPアドレス
- プライバシー配慮：最後のオクテットをマスク（例：`192.168.1.xxx`）
- 利用例：地域別アクセス分析、異常アクセスの検知

#### `metadata` (VARIANT)
- 意味：追加のコンテキスト情報（リファラー、A/Bテストフラグなど）
- 利用例：流入元分析、A/Bテストの効果測定

#### パーティションカラム（`year`, `month`, `day`, `hour`）
- [[LOG.CORTEX_CONVERSATIONS]] と同様

## クエリパターン例

### パターン1：エラー率の日次推移
```sql
SELECT DATE_TRUNC('day', timestamp) AS day,
       COUNT(*) AS total_requests,
       COUNT_IF(status_code >= 400) AS errors,
       ROUND(errors / total_requests * 100, 2) AS error_rate_pct
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1;
```

### パターン2：404エラー（存在しないページ）の多いURL
```sql
SELECT url,
       COUNT(*) AS not_found_count
FROM LOG.AZSWA_LOGS
WHERE status_code = 404
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20;
```

### パターン3：ユーザーの訪問経路（セッション単位）
```sql
SELECT session_id,
       LISTAGG(url, ' → ') WITHIN GROUP (ORDER BY timestamp) AS user_journey
FROM LOG.AZSWA_LOGS
WHERE session_id IS NOT NULL
  AND year = 2026 AND month = 1 AND day = 2
GROUP BY 1
LIMIT 10;
```

### パターン4：レスポンスタイムが遅いページ（P99 > 3秒）
```sql
SELECT url,
       APPROX_PERCENTILE(response_time_ms, 0.99) AS p99_ms
FROM LOG.AZSWA_LOGS
WHERE response_time_ms IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1
HAVING p99_ms > 3000
ORDER BY 2 DESC;
```

## 運用上の注意

### ログの書き込みフロー
1. Azure SWA / Next.js がリクエストを処理
2. ミドルウェアまたはカスタムロガーでログ生成
3. Azure Monitor → Stream Analytics → S3
4. Snowflake が AUTO_REFRESH で自動検知

### データ保持ポリシー
- 直近30日：アクセス分析用に内部テーブルへコピー（任意）
- 31-90日：S3 Standard（外部テーブルで直接クエリ）
- 91-365日：S3 Intelligent-Tiering
- 1年超：S3 Glacier（アーカイブ）

## セキュリティ・プライバシー

### IPアドレスのマスキング
- プライバシー保護のため、IPアドレスの最後のオクテットをマスク
- GDPR対応として、個人特定可能な情報を削除

### アクセス制御
```sql
GRANT SELECT ON LOG.AZSWA_LOGS TO ROLE LOG_VIEWER;
```

## 今後の拡張計画

### マテリアライズドビューによる高速化
```sql
CREATE MATERIALIZED VIEW LOG.MV_DAILY_PAGE_METRICS AS
SELECT DATE_TRUNC('day', timestamp) AS day,
       url,
       COUNT(*) AS views,
       COUNT_IF(status_code = 200) AS successful_views,
       COUNT_IF(status_code >= 400) AS errors,
       AVG(response_time_ms) AS avg_response_ms,
       APPROX_PERCENTILE(response_time_ms, 0.95) AS p95_response_ms
FROM LOG.AZSWA_LOGS
WHERE year >= 2026
GROUP BY 1, 2;
```

### アラート設定
```sql
CREATE ALERT high_404_error_rate
  WAREHOUSE = MONITORING_WH
  SCHEDULE = '15 MINUTE'
  IF EXISTS (
    SELECT 1 FROM LOG.AZSWA_LOGS
    WHERE timestamp >= DATEADD('minute', -15, CURRENT_TIMESTAMP())
      AND status_code = 404
    HAVING COUNT(*) > 100
  )
  THEN CALL notify_slack('High 404 error rate detected!');
```

## 設計レビュー時のチェックポイント
- [ ] エラー率（4xx, 5xx）が許容範囲内か（目標: <2%）
- [ ] P95レスポンスタイムが目標内か（目標: <2秒）
- [ ] 404エラーの多いURLに対応済みか
- [ ] IPアドレスが適切にマスキングされているか
