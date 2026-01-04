# 外部テーブル設計：[[design.AZFUNCTIONS_LOGS]]

## 概要

[[LOG.AZFUNCTIONS_LOGS]] は、Azure Functions（バックエンドAPI）のアプリケーションログを長期保管・分析するための外部テーブルである。

本テーブルは、Python製の Azure Functions が出力するログを S3 に保存し、Snowflake から直接クエリ可能にする。
関数の実行時間、エラー率、呼び出し頻度、HTTPステータスなどを時系列で追跡し、障害解析・性能改善・運用監視の根拠データとして利用する。

## 業務上の意味

* このテーブルが表す概念
  1レコードは「1つのログエントリ」を表す。
  INFO / WARNING / ERROR 等のログレベルを持ち、関数実行の状態（成功/失敗、遅延、例外）を時系列で記録する。

* 主な利用シーン

  * 関数のパフォーマンス分析（平均、P95/P99レイテンシ、SLA違反検知）
  * エラーパターンの特定とデバッグ（例外タイプ別の頻度、再現条件の切り分け）
  * API呼び出し頻度の監視（時間帯別、関数別の負荷傾向）
  * コスト分析（実行時間 × 呼び出し回数、エラー増加による再試行コスト）

## 設計上の位置づけ

[[LOG.AZFUNCTIONS_LOGS]] は、以下の観測性（Observability）スタックの一部として機能する：

* フロントエンド（Azure SWA / Next.js）
* バックエンドAPI（Azure Functions） ← 本テーブル
* AI Agent（Cortex Agent）
* データベース（Snowflake）

これらのログを横断的に分析することで、ユーザー操作からAPI実行、Agent応答までのリクエスト全体フローの追跡と、システム健全性の可視化が可能になる。


## 設計方針・運用要点（master本文記載禁止のため本ファイルに集約）

- S3長期保管・パーティション（year, month, day, hour）で効率的な時系列分析
- 主要カラム・S3パス・ファイル形式・AUTO_REFRESH等の詳細は本ファイルで管理
- カラム定義や論理一意性、NULL禁止等の運用ルールも本ファイルに明記

### 外部テーブルを採用する理由

本テーブルでは、EXTERNAL TABLE（外部テーブル）を採用する。

#### メリット：

1. コスト最適化

   * ログは増大しやすいが、S3ストレージは Snowflake 内部ストレージより安価
   * クエリ時のみスキャン課金となるため、長期保管コストを抑制

2. 柔軟な保持期間管理

   * S3ライフサイクルで古いログを自動アーカイブ（Glacier等）し、運用負荷を低減
   * Snowflake側の定義変更なしにストレージ階層を変更可能

3. スキーマ進化の容易性

   * ログ形式やメタデータ項目が増えても、VARIANT等で取り込み互換性を維持しやすい
   * 既存ログを再ロードせずに拡張が可能

#### デメリットと対処：

* クエリ速度：内部テーブルより遅い → 頻繁に参照する集計はマテリアライズドビューで高速化
* クラスタリング不可：外部テーブルはクラスタリングキーが使えない → パーティションによる時系列最適化で代替
* データ品質制約の強制不可：主キー等は強制できない → 書き込み側の整形・検証と、監視クエリで担保

### パーティション設計の詳細

S3パス構造：

```
s3://snowflake-chatdemo-vault-prod/logs/azfunctions/
  YEAR=2026/
    MONTH=01/
      DAY=02/
        HOUR=14/
          {uuid}.json
```

パーティションカラム（YEAR, MONTH, DAY, HOUR）は `metadata$filename` から抽出される。

#### パーティションプルーニングの例：

```sql
-- 対象日（パーティション指定あり）
SELECT * FROM LOG.AZFUNCTIONS_LOGS
WHERE year = 2026 AND month = 1 AND day = 2;

-- パーティション指定なし（全ファイルスキャン：非効率）
SELECT * FROM LOG.AZFUNCTIONS_LOGS
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL '1 day';
```

重要：時系列クエリでは必ず YEAR, MONTH, DAY（必要に応じてHOUR）を WHERE句に含めること。

## ログフォーマット設計（JSON Lines）

各ログファイルは 1行=1ログエントリ の JSON Lines (NDJSON) 形式で保存される。

#### 利点：

* 追記専用（Append-Only）に適する：ログは追記が中心で、行単位追記が効率的
* 半構造化データに強い：例外詳細や追加メタデータを柔軟に格納可能
* Snowflake の JSON 処理と親和：必要に応じてフィールド抽出・集計が容易

## カラム設計の判断

### 論理一意性（主キー概念）



外部テーブルには主キー制約を設定できないが、log_id（NOT NULL）による一意性を前提とする。
同一 invocation 内で複数ログが出るため、invocation_id 単体は一意にならない点に注意する。

#### 運用上の重複検知・監視手順
- 定期的にlog_idの重複検知クエリを実行し、重複が検出された場合はアラートを発報する
- 重複排除（dedupe）手順を下流処理に明記し、運用手順書に記載

```sql
-- log_id重複検知例
SELECT log_id, COUNT(*) AS cnt
FROM LOG.AZFUNCTIONS_LOGS
GROUP BY log_id
HAVING cnt > 1;
```

#### パーティション指定漏れの検知・防止
- クエリ監視機能やコスト異常検知を導入し、パーティション指定のない全スキャンを検知・アラート
- 運用手順書に「WHERE句で必ずYEAR, MONTH, DAY（必要に応じてHOUR）を指定する」ことを明記

#### VARIANT型カラムの最適化指針
- よくアクセスするVARIANT内フィールド（例: exception.type, metadata.user_id等）は、必要に応じてマテリアライズドビュー化や検索最適化を検討
- 頻出クエリパターンを分析し、パフォーマンス要件に応じて最適化方針を設計書に追記

### 各カラムの設計意図

#### log_id (VARCHAR)

* 意味：ログエントリの識別子（存在する場合）
* 生成方法：ログ出力時に UUID 生成
* 利用例：特定ログの追跡、重複排除のキー候補

#### function_name (VARCHAR)

* 意味：どの Azure Function が出力したログか
* 値例：`chat_endpoint`, `chat_stream`, `review_schema_endpoint`
* 利用例：関数ごとのエラー率・実行時間の分析

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

#### invocation_id (VARCHAR)

* 意味：Azure Functions の実行単位ID（Azure側が付与）
* 利用例：1リクエスト内のログを束ねる（デバッグ、因果追跡）

#### level (VARCHAR)

* 意味：ログレベル
* 値：`INFO` / `WARNING` / `ERROR`
* 利用例：障害分析（ERRORのみ抽出）、警告傾向の把握

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

#### message (VARCHAR)

* 意味：ログメッセージ本文
* 利用例：特定のキーワードや例外文言の検索

```sql
-- "Timeout" を含むエラーログ
SELECT function_name, timestamp, message
FROM LOG.AZFUNCTIONS_LOGS
WHERE level = 'ERROR'
  AND message ILIKE '%timeout%'
  AND year = 2026 AND month = 1;
```

#### timestamp (TIMESTAMP_NTZ)

* 意味：ログ出力日時（UTCで統一、表示側で変換）
* 利用例：時系列分析、障害発生時刻の特定、相関分析

#### duration_ms (NUMBER, nullable)

* 意味：関数の実行時間（ミリ秒）
* NULL の場合：開始ログなど計測対象外、または異常終了で計測未取得
* 利用例：SLA監視、遅延検知、P95/P99算出

```sql
-- 実行時間が3秒を超えた呼び出し
SELECT function_name, timestamp, duration_ms
FROM LOG.AZFUNCTIONS_LOGS
WHERE duration_ms > 3000
  AND year = 2026 AND month = 1
ORDER BY duration_ms DESC;
```

#### status_code (NUMBER, nullable)

* 意味：HTTPステータスコード（HTTP応答を伴うログの場合）
* NULL の場合：HTTP非関連のログ
* 利用例：APIエラー率、500系増加の検知

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

#### exception (VARIANT)

* 意味：例外発生時のスタックトレースやエラー詳細
* 構造例：

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

* 利用例：例外タイプ別集計、発生条件の特定

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

#### metadata (VARIANT)

* 意味：追加コンテキスト（リクエスト情報、環境識別子、関連ID等）
* 利用例：特定環境（prod/dev）やユーザーに紐づくログの抽出、相関分析

#### パーティションカラム（YEAR, MONTH, DAY, HOUR）

* 意味：S3パスから抽出されるパーティション情報
* データ型：NUMBER（0埋めなしの整数）
* 利用：WHERE句で指定し、パーティションプルーニングを有効化する

## クエリパターン例

### パターン1：エラー率の時系列推移

```sql
SELECT DATE_TRUNC('hour', timestamp) AS hour,
       COUNT(*) AS total,
       COUNT_IF(level = 'ERROR') AS errors,
       ROUND(errors / NULLIF(total, 0) * 100, 2) AS error_rate_pct
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

### パターン3：特定の例外が発生したリクエスト抽出

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

### AUTO_REFRESH の動作

* AUTO_REFRESH により、S3に新ファイルが追加されるとメタデータが更新される
* 反映遅延が問題になる場合は手動 REFRESH を実施する運用も検討する

```sql
ALTER EXTERNAL TABLE LOG.AZFUNCTIONS_LOGS REFRESH;
```

### ログの書き込みフロー

1. Azure Functions が実行され、Pythonの logging によりログを出力
2. ログを S3 へ転送（Application Insights 経由またはアプリが直接 PUT）
3. S3 のパーティションパスにファイルが配置される
4. Snowflake が AUTO_REFRESH で新規ファイルを検知し、外部テーブルに反映

注意：転送経路（Application Insights → 変換 → S3 / 直接PUT）が複数ある場合、ログ形式（JSON Lines）と必須項目の整合を運用ルールとして固定する。

### データ保持ポリシー

* 直近7日：高頻度クエリ用に内部テーブルへコピー（任意）
* 8-90日：S3 Standard（外部テーブルで直接クエリ）
* 91-365日：S3 Intelligent-Tiering
* 1年超：S3 Glacier（長期アーカイブ、クエリ不可）

## セキュリティ・プライバシー

### 機密情報の取り扱い

* ログに認証トークンやAPIキーが含まれないよう、アプリケーション側でフィルタリングする
* metadata にPIIが入り得る場合は、マスキング方針（アプリ側マスキング or Snowflake側ポリシー）を明確にする

### アクセス制御

```sql
GRANT SELECT ON LOG.AZFUNCTIONS_LOGS TO ROLE LOG_VIEWER;
```

## 今後の拡張計画

### マテリアライズドビューによる高速化

頻繁に参照する集計はMVで事前計算する：

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

### 全文検索の検討

ログ本文（message）や例外（exception）をキーワード検索したい場合、検索最適化の適用範囲を検討する：

```sql
ALTER TABLE LOG.AZFUNCTIONS_LOGS
  ADD SEARCH OPTIMIZATION ON (message);
```

## 設計レビュー時のチェックポイント

* [ ] パーティション指定のないクエリが発行されていないか
* [ ] エラー率が許容範囲内か（目標: <1%）
* [ ] P99レイテンシが目標内か（目標: <3秒）
* [ ] SLA違反（>3秒）の件数が許容範囲内か
* [ ] 機密情報がログに出力されていないか
* [ ] ログ形式（JSON Lines）と必須項目が転送経路間で整合しているか

---

## 変更履歴

- 2026-01-04
  - カラムコメントを具体化（論理一意性、JSON例、NULL条件、パーティションカラムの注意点等を明記）
  - EXTERNAL TABLEの品質担保方針を明確化
-  - master/externaltables配下の本文を削除し、設計要点・運用方針を本designファイルに集約
  - 設計とDDL（master正本）の責務分離を整理
