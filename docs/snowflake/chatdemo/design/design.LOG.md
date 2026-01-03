schema_id:: SCH_20260102000001

```dataview
TABLE comment, physical
FROM "master/externaltables"
WHERE schema_id = this.schema_id
SORT schema_id, physical
```

# [[design.LOG]] スキーマ 設計意図・全体設計

---

## 1. このスキーマの位置づけ

[[design.LOG]] スキーマは、全アプリケーション・サービスのログを統合集約するための専用スキーマである。

本スキーマの役割は次の3点に集約される：

> 1. Snowflake Cortex Agent会話ログの長期保管・分析基盤
> 2. Azure Functions / SWA のアプリケーションログの統合
> 3. Snowflake自体のメトリクス・監査ログの蓄積

つまり [[design.LOG]] は、

* システム全体の動作履歴を一元管理
* トラブルシューティングの証跡
* ユーザー行動分析の基礎データ
* コスト・パフォーマンス分析の根拠

を提供するための観測性（Observability）基盤スキーマである。

---

## 2. 設計思想の中核（最重要）

### 2.1 外部テーブル + S3 パーティション構成を採用する理由

本基盤では、すべてのログテーブルを外部テーブル（EXTERNAL TABLE）として実装する。

#### 理由

1. コスト最適化

   * S3ストレージコストは Snowflakeストレージより大幅に安価
   * 古いログは S3 ライフサイクルポリシーで低コストストレージへ移行可能
   * クエリ時のみコンピュート課金されるため、長期保管でも保管コストを抑制できる

2. 柔軟な保持期間管理

   * S3バケットポリシーでログ保持期間を柔軟に設定可能
   * 例：直近90日はStandard、91-365日はIA、1年超はGlacier

3. スキーマ進化の容易性

   * ログフォーマット変更時も、新しいパーティションから新スキーマを適用可能
   * 過去ログの再ロードを前提としない

4. パフォーマンス（主にスキャン削減）

   * YEAR / MONTH / DAY / HOUR のパーティションにより、時系列クエリで不要スキャンを削減
   * 必要な期間のパーティションのみスキャンされる（パーティションプルーニング）

#### デメリットと対処

* デメリット: 外部テーブルはクラスタリングキー等の物理最適化を前提にしにくい
* 対処: 頻繁にクエリするログは定期的に内部テーブルへ集約（またはマテリアライズドビュー化）

---

### 2.2 JSON Lines (NDJSON) フォーマットを採用する理由

各ログは 1行=1レコード の JSON Lines形式（NDJSON）でS3に保存する。

#### 理由

1. スキーマレス（進化に強い）

   * ログにフィールドを追加しても、原則として保存フォーマット側の柔軟性を維持できる
   * VARIANT型でメタデータを柔軟に格納可能

2. 追記専用（Append-Only）に最適

   * ログは基本的に追記のみ
   * JSONLは行単位で追記できるため、ストリーミング書き込みに適している

3. Snowflake の JSON サポート

   * 半構造化データ向け関数（FLATTEN / GET 等）により分析が容易

---

## 3. 各ログテーブルの設計判断

### 3.1 LOG.CORTEX_CONVERSATIONS

#### 目的

* Cortex Agent（[[APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT]]）の会話履歴を保管
* ユーザーとAIの対話品質を分析
* 問題のある応答やエラーの追跡
* 機械学習モデル改善の材料

#### 主要カラム設計判断（責務分離）

* conversation_id : 会話スレッドID（複数ターンをグループ化）
* session_id : セッション単位（複数会話をまたぐ可能性）
* message_role : `user` / `assistant`
* message_content : **メッセージ本文（主に text）**
* metadata : **運用・観測メタ情報（model / tokens / latency / error 等）**

#### クエリパターン想定

```sql
-- 特定ユーザーの会話履歴
SELECT *
FROM LOG.CORTEX_CONVERSATIONS
WHERE user_id = 'USER123'
  AND year = 2026 AND month = 1
ORDER BY timestamp;

-- エラー率の日次分析（metadata 側を参照）
SELECT DATE_TRUNC('day', timestamp) AS day, 
       COUNT(*) AS total,
       COUNT_IF(metadata:error IS NOT NULL) AS errors
FROM LOG.CORTEX_CONVERSATIONS
WHERE year = 2026 AND month = 1
GROUP BY 1;
```

---

### 3.2 LOG.AZFUNCTIONS_LOGS

#### 目的

* Azure Functions のアプリケーションログを集約
* 関数の実行時間・エラー率の監視
* リクエスト/レスポンスの追跡（トレーサビリティ）

#### 主要カラム設計判断

* function_name : どの関数が実行されたか
* invocation_id : Azure Functions の実行単位ID（分散トレーシング用）
* level : INFO / WARNING / ERROR でログレベルを分類
* duration_ms : 実行時間（パフォーマンス分析用）
* exception : VARIANT型で例外のスタックトレースを保持

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

### 3.3 LOG.AZSWA_LOGS

#### 目的

* Azure Static Web Apps（フロントエンド）のアクセスログを集約
* ユーザー行動分析（どのページが閲覧されているか）
* レスポンスタイム・エラー率の監視

#### 主要カラム設計判断

* request_id : HTTPリクエスト識別子
* session_id : ユーザーセッション（複数リクエストをグループ化）
* url / method : アクセス先とHTTPメソッド
* status_code : HTTPステータスコード（エラー検知用）
* client_ip / user_agent : ユーザー属性

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

### 3.4 LOG.SNOWFLAKE_METRICS

#### 目的

* Snowflake 自体のクエリ実行メトリクスを蓄積
* コスト分析（どのクエリが高コストか）
* パフォーマンス最適化の根拠データ

#### 主要カラム設計判断

* metric_name : メトリクス種別（例：`query_execution_time`, `bytes_scanned`, `credits_used`）
* metric_value : メトリクス値（数値）
* warehouse_name : どのウェアハウスで実行されたか
* query_id : Snowflakeのクエリ実行IDと紐付け

#### データソース想定

* INFORMATION_SCHEMA / ACCOUNT_USAGE から定期的に抽出・エクスポート

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
WHERE metric_name = 'query_execution_time'
  AND year = 2026 AND month = 1
ORDER BY 2 DESC
LIMIT 10;
```

---

## 4. 運用設計

### 4.1 ログの書き込み方法（想定）

各アプリケーションは以下のいずれかの方法でS3にログを書き込む。

1. Azure Functions / SWA

   * Application Insights →（中継基盤）→ S3 へ転送
   * または、アプリケーションから直接 AWS SDK で S3 PUT

2. Cortex Agent 会話ログ

   * 会話処理を担うアプリケーション層が、NDJSON に整形して S3 へ PUT

3. Snowflake メトリクス

   * 定期タスク（TASK 等）でメトリクスを抽出し、S3 へエクスポート

※ 具体的な実装方式は各テーブルの個別設計ドキュメントに委ねる（本書はスキーマ全体思想の説明が目的）。

---

### 4.2 パーティション設計詳細

S3パス構造（統一表記）：

```
s3://snowflake-chatdemo-vault-prod/logs/{log_type}/
  YEAR=YYYY/
    MONTH=MM/
      DAY=DD/
        HOUR=HH/
          {uuid}.json
```

例：

```
s3://snowflake-chatdemo-vault-prod/logs/cortex_conversations/
  YEAR=2026/MONTH=01/DAY=02/HOUR=14/abc123.json
```

* YEAR : 長期保管時の粗い絞り込み
* MONTH : 月単位のアーカイブ・削除が容易
* DAY : 日次分析の基本粒度
* HOUR : 直近の高頻度分析用

---

### 4.3 AUTO_REFRESH の設定

外部テーブルでは `AUTO_REFRESH = TRUE` を基本とする。

* S3 に新しいファイルが追加されると、外部テーブルのメタデータ更新が自動的に走る
* 反映遅延や欠損が疑われる場合は、運用手順として手動 REFRESH を用意する

---

## 5. 今後の拡張計画

### 5.1 マテリアライズドビュー化

頻繁にクエリされる集計結果はMVで高速化する。

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

* エラー率が閾値を超えた場合に通知
* Snowflake ALERT / 外部監視ツール連携を想定

### 5.3 長期保管ポリシー

* 直近30日: 内部テーブル / MV 等で高速クエリ（任意）
* 31-90日: S3 Standard（外部テーブル）
* 91-365日: S3 Intelligent-Tiering
* 1年超: S3 Glacier（アーカイブ）

---

## 6. セキュリティ・コンプライアンス

### 6.1 個人情報の取り扱い

* user_id, session_id は仮名化ID（ハッシュ値等）を使用
* 実名や連絡先等のPIIは格納しない
* GDPR削除要求に対応するため、user_id での削除手順を用意する（ファイル削除＋REFRESH等）

### 6.2 アクセス制御

```sql
-- ログ参照ロール（読み取り専用）
CREATE ROLE LOG_VIEWER;
GRANT USAGE ON SCHEMA LOG TO ROLE LOG_VIEWER;
GRANT SELECT ON ALL EXTERNAL TABLES IN SCHEMA LOG TO ROLE LOG_VIEWER;

-- ログ管理者ロール（運用管理）
CREATE ROLE LOG_ADMIN;
GRANT ALL ON SCHEMA LOG TO ROLE LOG_ADMIN;
```

---

## 7. 設計レビュー時のチェックポイント

* [ ] ログクエリの平均実行時間は許容範囲内か（例：<3秒）
* [ ] S3ストレージコストは予算内か
* [ ] パーティションプルーニングが有効に機能しているか
* [ ] エラーログの見逃しが発生していないか
* [ ] 古いログの削除ポリシーが守られているか
* [ ] `message_content` / `metadata` の責務が混線していないか（CORTEX_CONVERSATIONS）

---

## 8. 参考リンク

* Snowflake External Tables Documentation
* S3 Lifecycle Policies
* Observability Best Practices
