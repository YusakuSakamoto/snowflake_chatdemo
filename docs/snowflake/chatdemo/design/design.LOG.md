schema_id:: SCH_20260102000001

```dataview
TABLE comment, physical
FROM "master/externaltables"
WHERE schema_id = this.schema_id
SORT schema_id, physical
```

## [[LOG]] スキーマ 設計意図・全体設計

---

## 1. このスキーマの位置づけ

[[LOG]] スキーマは、全アプリケーション・サービスのログを統合集約するための専用スキーマである。

本スキーマの役割は次の3点に集約される：

> 1. Snowflake Cortex Agent会話ログの長期保管・分析基盤
> 2. Azure Functions / SWA のアプリケーションログの統合
> 3. Snowflake自体のメトリクス・監査ログの蓄積

つまり [[LOG]] は、

- システム全体の動作履歴を一元管理
- トラブルシューティングの証跡
- ユーザー行動分析の基礎データ
- コスト・パフォーマンス分析の根拠

を提供するための観測性（Observability）基盤スキーマである。

---

## 2. 設計思想の中核（最重要）

### 2.1 外部テーブル + S3 パーティション構成を採用する理由

本基盤では、すべてのログテーブルを外部テーブル（EXTERNAL TABLE）として実装する。

#### 理由：

1. コスト最適化
   - S3ストレージコストは Snowflakeストレージより大幅に安価
   - 古いログは自動的にS3のライフサイクルポリシーで低コストストレージへ移行可能
   - クエリ時のみ課金されるため、長期保管でもコスト増加が抑えられる

2. 柔軟な保持期間管理
   - S3バケットポリシーでログ保持期間を柔軟に設定可能
   - 例：直近90日はStandard、91-365日はIA、1年超はGlacier

3. スキーマ進化の容易性
   - ログフォーマット変更時も、新しいパーティションから新スキーマを適用可能
   - 過去ログを再ロードする必要がない

4. パフォーマンス
   - year/month/day/hour のパーティションにより、時系列クエリが高速化
   - 必要な期間のパーティションのみスキャンされる（パーティションプルーニング）

#### デメリットと対処：

- デメリット: 外部テーブルはクラスタリングキーや検索最適化サービスが使えない
- 対処: 頻繁にクエリするログは定期的に内部テーブルへ集約（マテリアライズドビュー化）

### 2.2 JSON Lines (NDJSON) フォーマットを採用する理由

各ログは 1行=1レコード の JSON Lines形式 でS3に保存する。

#### 理由：

1. スキーマレス
   - ログにフィールドを追加してもテーブル定義変更不要
   - VARIANT型でメタデータを柔軟に格納可能

2. 追記専用（Append-Only）に最適
   - ログは基本的に追記のみ
   - JSONLは行単位で追記できるため、ストリーミング書き込みに適している

3. Snowflake の JSON サポート
   - Snowflake は JSON の高速パースとクエリ最適化をサポート
   - 半構造化データに対する豊富な関数群（FLATTEN, GET, など）

---

## 3. 各ログテーブルの設計判断

### 3.1 [[LOG.CORTEX_CONVERSATIONS]]

#### 目的
- Cortex Agent（[[APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT]]）の会話履歴を保管
- ユーザーとAIの対話品質を分析
- 問題のあるクエリやエラーの追跡
- 機械学習モデルの改善材料

#### 主要カラム設計判断
- `conversation_id` : 1つの会話スレッドを一意識別（複数ターンをグループ化）
- `session_id` : ユーザーのセッション単位（複数会話をまたぐ可能性）
- `message_role` : `user` / `assistant` で発話者を区別
- `message_content` : VARIANT型でメッセージ本体+メタデータを格納
- `metadata` : 実行時コンテキスト（使用モデル、トークン数、レイテンシなど）

#### クエリパターン想定
```sql
-- 特定ユーザーの会話履歴
SELECT * FROM LOG.CORTEX_CONVERSATIONS
WHERE user_id = 'USER123'
  AND year = 2026 AND month = 1
ORDER BY timestamp;

-- エラー率の日次分析
SELECT DATE_TRUNC('day', timestamp) AS day, 
       COUNT(*) AS total,
       COUNT_IF(metadata:error IS NOT NULL) AS errors
FROM LOG.CORTEX_CONVERSATIONS
WHERE year = 2026 AND month = 1
GROUP BY 1;
```

---

### 3.2 [[LOG.AZFUNCTIONS_LOGS]]

#### 目的
- Azure Functions のアプリケーションログを集約
- 関数の実行時間・エラー率の監視
- リクエスト/レスポンスの追跡（トレーサビリティ）

#### 主要カラム設計判断
- `function_name` : どの関数が実行されたか
- `invocation_id` : Azure Functions の実行単位ID（分散トレーシング用）
- `level` : INFO / WARNING / ERROR でログレベルを分類
- `duration_ms` : 実行時間（パフォーマンス分析用）
- `exception` : VARIANT型で例外のスタックトレースを保持

#### クエリパターン想定
```sql
-- 関数ごとのP99レイテンシ
SELECT function_name,
       APPROX_PERCENTILE(duration_ms, 0.99) AS p99_ms
FROM LOG.AZFUNCTIONS_LOGS
WHERE year = 2026 AND month = 1
  AND duration_ms IS NOT NULL
GROUP BY 1;

-- エラー頻度の高い関数
SELECT function_name, COUNT(*) AS error_count
FROM LOG.AZFUNCTIONS_LOGS
WHERE level = 'ERROR'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

---

### 3.3 [[LOG.AZSWA_LOGS]]

#### 目的
- Azure Static Web Apps（フロントエンド）のアクセスログを集約
- ユーザー行動分析（どのページが閲覧されているか）
- レスポンスタイム・エラー率の監視

#### 主要カラム設計判断
- `request_id` : 1つのHTTPリクエストを一意識別
- `session_id` : ユーザーセッション（複数リクエストをグループ化）
- `url` / `method` : アクセス先とHTTPメソッド
- `status_code` : HTTPステータスコード（エラー検知用）
- `client_ip` / `user_agent` : ユーザー属性

#### クエリパターン想定
```sql
-- 人気ページTOP10
SELECT url, COUNT(*) AS views
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1
  AND status_code = 200
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;

-- エラー率の時系列推移
SELECT DATE_TRUNC('hour', timestamp) AS hour,
       COUNT(*) AS total_requests,
       COUNT_IF(status_code >= 400) AS errors
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1 AND day = 2
GROUP BY 1
ORDER BY 1;
```

---

### 3.4 [[LOG.SNOWFLAKE_METRICS]]

#### 目的
- Snowflake 自体のクエリ実行メトリクスを蓄積
- コスト分析（どのクエリが高コストか）
- パフォーマンス最適化の根拠データ

#### 主要カラム設計判断
- `metric_name` : メトリクス種別（例：`query_execution_time`, `bytes_scanned`）
- `metric_value` : メトリクス値（数値）
- `warehouse_name` : どのウェアハウスで実行されたか
- `query_id` : Snowflakeのクエリ実行IDと紐付け

#### データソース想定
- [[INFORMATION_SCHEMA.QUERY_HISTORY]] から定期的にエクスポート
- [[ACCOUNT_USAGE.QUERY_HISTORY]] から重要メトリクスを抽出

#### クエリパターン想定
```sql
-- ウェアハウスごとのコスト（クレジット消費）
SELECT warehouse_name,
       SUM(metric_value) AS total_credits
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'credits_used'
  AND year = 2026 AND month = 1
GROUP BY 1;

-- 実行時間が長いクエリTOP10
SELECT query_id, metric_value AS execution_time_sec
FROM LOG.SNOWFLAKE_METRICS
WHERE metric_name = 'execution_time'
  AND year = 2026 AND month = 1
ORDER BY 2 DESC
LIMIT 10;
```

---

## 4. 運用設計

### 4.1 ログの書き込み方法

各アプリケーションは以下の方法でS3にログを書き込む：

1. Azure Functions / SWA
   - Application Insights → Stream Analytics → S3
   - または直接 AWS SDK で S3 PUT

2. Cortex Agent会話ログ
   - Snowflakeストアドプロシージャで会話終了時にS3へ `COPY INTO @stage`

3. Snowflakeメトリクス
   - 定期タスク（TASK）で [[QUERY_HISTORY]] から抽出し S3 へエクスポート

### 4.2 パーティション設計詳細

S3パス構造：
```
s3://snowflake-chatdemo-vault-prod/logs/{log_type}/year=YYYY/month=MM/day=DD/hour=HH/{uuid}.json
```

例：
```
s3://snowflake-chatdemo-vault-prod/logs/cortex_conversations/year=2026/month=01/day=02/hour=14/abc123.json
```

- `year=YYYY` : 年でのパーティション（長期保管時の粗い絞り込み）
- `month=MM` : 月単位でのアーカイブ・削除が容易
- `day=DD` : 日単位の分析（最も頻繁に使われる粒度）
- `hour=HH` : リアルタイム分析用（直近数時間のログ）

### 4.3 AUTO_REFRESH の設定

すべての外部テーブルで `[[AUTO_REFRESH]]=TRUE` を設定：

- S3に新しいファイルが追加されると、Snowflakeが自動的にメタデータを更新
- クエリ時に最新データが即座に反映される
- 手動 `ALTER EXTERNAL TABLE ... REFRESH` が不要

---

## 5. 今後の拡張計画

### 5.1 マテリアライズドビュー化

頻繁にクエリされる集計結果はMVで高速化：

```sql
CREATE MATERIALIZED VIEW LOG.MV_DAILY_ERROR_SUMMARY AS
SELECT DATE_TRUNC('day', timestamp) AS log_date,
       'CORTEX' AS source,
       COUNT(*) AS total,
       COUNT_IF(metadata:error IS NOT NULL) AS errors
FROM LOG.CORTEX_CONVERSATIONS
GROUP BY 1
UNION ALL
SELECT DATE_TRUNC('day', timestamp),
       'AZFUNCTIONS',
       COUNT(*),
       COUNT_IF(level = 'ERROR')
FROM LOG.AZFUNCTIONS_LOGS
GROUP BY 1;
```

### 5.2 アラート機能

エラー率が閾値を超えた場合に通知：
- Snowflake ALERT 機能を使用
- Slackや外部監視ツールへ通知

### 5.3 長期保管ポリシー

- 直近30日: Snowflake で高速クエリ可能
- 31-90日: S3 Standard（外部テーブル）
- 91-365日: S3 Intelligent-Tiering
- 1年超: S3 Glacier（アーカイブ）

---

## 6. セキュリティ・コンプライアンス

### 6.1 個人情報の取り扱い

- `user_id`, `session_id` は仮名化ID（ハッシュ値）を使用
- 実名や連絡先などのPIIは格納しない
- GDPR削除要求に対応するため、user_id でのログ削除プロシージャを用意

### 6.2 アクセス制御

```sql
-- ログ参照ロール（読み取り専用）
CREATE ROLE LOG_VIEWER;
GRANT USAGE ON SCHEMA LOG TO ROLE LOG_VIEWER;
GRANT SELECT ON ALL EXTERNAL TABLES IN SCHEMA LOG TO ROLE LOG_VIEWER;

-- ログ管理者ロール（書き込み・削除可能）
CREATE ROLE LOG_ADMIN;
GRANT ALL ON SCHEMA LOG TO ROLE LOG_ADMIN;
```

---

## 7. 設計レビュー時のチェックポイント

このスキーマ設計が適切かを判断するため、以下を定期的にレビュー：

- [ ] ログクエリの平均実行時間は許容範囲内か（<3秒）
- [ ] S3ストレージコストは予算内か
- [ ] パーティションプルーニングが有効に機能しているか
- [ ] エラーログの見逃しが発生していないか
- [ ] 古いログの削除ポリシーが守られているか

---

## 8. 参考リンク

- [Snowflake External Tables Documentation](https://docs.snowflake.com/en/user-guide/tables-external-intro)
- [S3 Lifecycle Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [Observability Best Practices](https://sre.google/sre-book/monitoring-distributed-systems/)
