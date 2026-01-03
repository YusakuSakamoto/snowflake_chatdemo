# 外部テーブル設計：[[design.AZSWA_LOGS]]

## 概要

[[LOG.AZSWA_LOGS]] は、Azure Static Web Apps（Next.js フロントエンド）のアクセスログを長期保管・分析するための外部テーブルである。

本テーブルは、S3 に保存された JSON 形式（原則 JSON Lines を推奨）のログファイルを、Snowflake から EXTERNAL TABLE として直接参照可能にする。
UX 改善（導線・離脱・速度）、障害検知（4xx/5xx の急増）、セキュリティ監視（異常アクセス傾向）を主用途とする。

## 業務上の意味

* このテーブルが表す概念
  **1レコード = 1 HTTP リクエスト**。
  ブラウザからフロントエンドへ到達したアクセスの「結果（status_code）」「業務上の状態（status）」「体感性能（response_time_ms）」を、時系列で追跡する。

* 主な利用シーン

  * 404/5xx の監視と原因調査（発生ページ・流入元・時間帯）
  * パフォーマンス分析（P50/P95/P99、デバイス別、ページ別）
  * ユーザー行動分析（セッション遷移、リファラ別、時間帯別）
  * 異常アクセス検知（短時間多アクセス、特定パス集中、UA偏り）

## 設計上の位置づけ

[[LOG.AZSWA_LOGS]] は、観測性（Observability）スタックのフロントエンド側を担当する。

* フロントエンド（Azure SWA / Next.js）アクセスログ ← 本テーブル
* バックエンド（Azure Functions）アプリログ：[[LOG.AZFUNCTIONS_LOGS]]
* AI 会話ログ：[[LOG.CORTEX_CONVERSATIONS]]
* Snowflake メトリクス（クエリ実行統計）

これらを横断的に分析することで、**ユーザー操作 → API 呼び出し → Agent 応答**までの流れを追跡しやすくなる。

---

## 設計方針

### 外部テーブルを採用する理由

本テーブルでは EXTERNAL TABLE（外部テーブル）を採用する。

#### メリット

1. コスト最適化

   * アクセスログは増え続ける前提だが、S3 ストレージは安価で長期保管に向く
2. 柔軟な保持期間管理

   * S3 ライフサイクルで自動アーカイブでき、Snowflake 側の定義変更が不要
3. スキーマ進化の容易性

   * metadata（VARIANT）を併用し、将来的な属性追加に耐える

#### デメリットと対処

* クエリ速度：内部テーブルより遅い
  → 頻繁に見る集計は内部テーブル化または MV で高速化
* 制約が強制されない（品質担保の弱さ）
  → 検証クエリ・監視・書き込み側制御で運用担保する
* クラスタリング不可
  → 時系列パーティションで代替し、スキャン範囲を絞る

---

## パーティション設計

### S3 パス構造

例：

```
s3://.../logs/azswa/
  YEAR=2026/
    MONTH=01/
      DAY=02/
        HOUR=14/
          {uuid}.json
```

### パーティションカラム（YEAR, MONTH, DAY, HOUR）

* 役割：`metadata$filename` から抽出し、パーティションプルーニングを効かせる
* 型：NUMBER（整数運用）

#### パーティションプルーニングの例

（重要：時系列クエリは YEAR/MONTH/DAY を基本として絞り込む）

```sql
-- 良い例：日単位でスキャン範囲を限定
SELECT *
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1 AND day = 2;

-- 悪い例：全スキャンになりがち（外部テーブルでは高コスト）
SELECT *
FROM LOG.AZSWA_LOGS
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL '1 day';
```

---

## 制約・品質担保（EXTERNAL TABLE 前提）

### 制約に関する基本方針

* PRIMARY KEY / UNIQUE / FOREIGN KEY

  * 宣言できても強制されないため、DDL による品質担保には使わない
* CHECK 制約

  * DDL に載せない（前提方針に従う）

よって品質担保は以下の組み合わせで行う。

* 書き込み側での必須項目保証（log_id、timestamp、status_code など）
* 定期的な検証クエリ（重複・NULL・値域）
* 異常時の S3 データ是正（除外・マスキング・再生成）
* 高頻度利用の集計は内部テーブル化

---

## 主キー・識別子設計

### log_id（主キー相当）

* 意味：HTTP リクエストを一意識別する ID
* 生成方法：リクエスト処理時に UUID を生成
* 設計判断：
  外部テーブルで一意性を強制できないため、「一意であるべき」ことを設計として明示し、**重複検知を運用で担保**する。

#### 重複検知の運用例（推奨）

* 日次で「重複が 0」を確認し、異常があれば書き込み経路を点検する。

```sql
SELECT log_id, COUNT(*) AS c
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1 AND day = 2
GROUP BY 1
HAVING COUNT(*) > 1;
```

### request_id（相関 ID）

* 意味：Azure SWA が付与する識別子（またはリクエスト相関用 ID）
* 用途：[[LOG.AZFUNCTIONS_LOGS]] 等との論理 JOIN に利用
* 設計判断：FK 制約は持たず、**JOIN 成功率や欠損率を監視**する

---

## STATUS / STATUS_CODE 設計

* 意味：アプリケーション／業務ロジックの状態
* 想定値：RUNNING / SUCCEEDED / FAILED など
* 主用途：

  * 業務フローの異常検知（HTTP は 200 だが処理は FAILED など）
  * UX/導線の成否指標

### 設計上の注意

* HTTP の可視化・アラートは STATUS_CODE を主に使う
* 業務状態の可視化は STATUS を主に使う
* どちらかが恒常的に不要になった場合は削除を検討（ただし “混ぜない” を優先）

---

## カラム設計の判断

### timestamp（TIMESTAMP_NTZ）

* 意味：リクエスト受信日時（UTC）
* なぜ NTZ：ログ時刻は UTC 統一し、表示や集計のタイムゾーン変換は利用側で行う
* 代表用途：時系列集計、ピーク検知、障害発生点の特定

### response_time_ms（NUMBER, nullable）

* 意味：レスポンス時間（ms）
* NULL 許容理由：

  * 測定不能（クライアント中断、ログ収集欠損）
  * エラーで計測完了前に終了
* 代表用途：P95/P99、パス別、UA 別の体感性能

### session_id（VARCHAR, nullable）

* 意味：ユーザーセッション識別子
* 取得元：Cookie / LocalStorage など
* NULL 許容理由：匿名・初回アクセス・同意未取得などを想定

### user_agent（VARCHAR, nullable）

* 意味：ブラウザ／OS／デバイス情報
* 代表用途：デバイス別の性能差、特定 UA での不具合検知

### client_ip（VARCHAR, nullable）

* 意味：クライアント IP
* 方針：個人特定を避けるためマスク（例：末尾オクテットの匿名化）
* 代表用途：異常アクセス傾向（ただし個人追跡が目的にならないようにする）

### metadata（VARIANT）

* 意味：拡張コンテキスト（referrer、A/B テスト、実験フラグ等）
* 設計判断：

  * 変化しやすい属性を吸収する
  * 主要分析軸は固定カラムに寄せ、metadata を“何でも箱”にしない

---

## クエリパターン例

### パターン1：エラー率の時系列推移（HTTP観点）

```sql
SELECT DATE_TRUNC('hour', timestamp) AS hour,
       COUNT(*) AS total,
       COUNT_IF(status_code >= 400) AS errors,
       ROUND(errors / total * 100, 2) AS error_rate_pct
FROM LOG.AZSWA_LOGS
WHERE year = 2026 AND month = 1 AND day = 2
GROUP BY 1
ORDER BY 1;
```

### パターン2：P95/P99 レイテンシ（パス別）

```sql
SELECT metadata:path::VARCHAR AS path,
       APPROX_PERCENTILE(response_time_ms, 0.95) AS p95_ms,
       APPROX_PERCENTILE(response_time_ms, 0.99) AS p99_ms
FROM LOG.AZSWA_LOGS
WHERE response_time_ms IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY p99_ms DESC;
```

### パターン3：業務状態 FAILED の検出（アプリ観点）

```sql
SELECT timestamp, status_code, status, metadata
FROM LOG.AZSWA_LOGS
WHERE status = 'FAILED'
  AND year = 2026 AND month = 1
ORDER BY timestamp DESC;
```

### パターン4：request_id でバックエンドログと相関（論理 JOIN）

```sql
SELECT a.timestamp,
       a.status_code,
       a.request_id,
       b.function_name,
       b.level,
       b.message
FROM LOG.AZSWA_LOGS a
LEFT JOIN LOG.AZFUNCTIONS_LOGS b
  ON a.request_id = b.invocation_id
WHERE a.year = 2026 AND a.month = 1 AND a.day = 2;
```

---

## 運用上の注意

### AUTO_REFRESH の前提

* 新規ファイル追加が自動反映される前提（遅延は発生し得る）
* 運用監視では「新規ファイルが増えているのに反映されない」状態を検知する

### ログの書き込みフロー（代表例）

1. SWA/フロントエンドがアクセスログを生成（または基盤ログを取得）
2. 収集・転送（例：ログ基盤 → S3）
3. S3 のパーティションパスへ保存
4. Snowflake が AUTO_REFRESH で検知

### 監視項目（要点）

* AUTO_REFRESH 失敗回数
* 新規ファイル増加量（時間あたり）
* スキャン量・クレジット消費の急増
* 404 / 5xx の急増、特定パス集中

---

## セキュリティ・プライバシー

### 機密情報の取り扱い（最低限の契約）

* Authorization / Cookie / API キー等の秘匿情報を **ログ本文に出さない**
* metadata に入れる場合も、復元可能な秘密値は格納しない（マスク or 除外）
* client_ip は匿名化（保存目的が「個人追跡」にならないようにする）

### アクセス制御（例）

```sql
GRANT SELECT ON LOG.AZSWA_LOGS TO ROLE LOG_VIEWER;
```

---

## 今後の拡張計画

### マテリアライズドビューによる高速化（例）

```sql
CREATE MATERIALIZED VIEW LOG.MV_HOURLY_SWA_METRICS AS
SELECT DATE_TRUNC('hour', timestamp) AS hour,
       COUNT(*) AS total_requests,
       COUNT_IF(status_code >= 400) AS errors,
       APPROX_PERCENTILE(response_time_ms, 0.99) AS p99_ms
FROM LOG.AZSWA_LOGS
WHERE year >= 2026
GROUP BY 1;
```

### アラート（例）

```sql
CREATE ALERT high_swa_error_rate
  WAREHOUSE = MONITORING_WH
  SCHEDULE = '10 MINUTE'
  IF EXISTS (
    SELECT 1
    FROM LOG.MV_HOURLY_SWA_METRICS
    WHERE hour >= DATEADD('hour', -1, CURRENT_TIMESTAMP())
      AND errors / NULLIF(total_requests, 0) > 0.05
  )
  THEN CALL notify_slack('High error rate in Azure SWA!');
```

---

## 設計レビュー時のチェックポイント

* [ ] YEAR/MONTH/DAY を指定しないクエリが常態化していないか（コスト劣化）
* [ ] 404 / 5xx が急増していないか（入口：status_code）
* [ ] status='FAILED' が増えていないか（業務観点）
* [ ] response_time_ms の P99 が目標を超えていないか
* [ ] log_id 重複が発生していないか
* [ ] 秘匿情報がログに出ていないか（metadata 含む）

---

## 変更履歴

- 2026-01-04
  - カラムコメントを具体化（論理一意性、JSON例、NULL条件、パーティションカラムの注意点等を明記）
  - EXTERNAL TABLEの品質担保方針を明確化
  - 設計とDDL（master正本）の責務分離を整理
- 2026-01-03
  - STATUS / STATUS_CODE の役割分担を明文化（High-1 対応）
  - 外部テーブル制約・品質担保方針を明確化
  - 設計と DDL（master 正本）の責務分離を整理
