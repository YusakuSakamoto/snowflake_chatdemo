# 外部テーブル設計：[[design.CORTEX_CONVERSATIONS]]

## 概要

[[LOG.CORTEX_CONVERSATIONS]] は、Snowflake Cortex Agent との会話履歴を長期保管・分析するための外部テーブルである。

本テーブルは、S3 に保存された JSON Lines（NDJSON）形式のログファイルを、Snowflake から EXTERNAL TABLE として直接クエリ可能にする。
[[APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT]] を含む、全 Cortex Agent の会話ログを統合的に管理する。

---

## 業務上の意味

### このテーブルが表す概念

* 1レコード = **1つのメッセージ**
* ユーザーからの質問（`message_role = 'user'`）と
  Agent からの回答（`message_role = 'assistant'`）が時系列で記録される

### 主な利用シーン

* 会話品質の分析（回答精度、レスポンス時間）
* エラーパターンの特定と改善
* ユーザー行動の理解（よく聞かれる質問、利用時間帯）
* 機械学習モデルの Fine-tuning 用データセット作成

---

## 設計上の位置づけ

[[LOG.CORTEX_CONVERSATIONS]] は、以下の Observability スタックの一部として機能する。

* アプリケーションログ（Azure Functions / SWA）
* Cortex Agent 会話ログ ← 本テーブル
* Snowflake メトリクス（クエリ実行統計）

これらを横断的に分析することで、アプリケーション・AI・データ基盤を含むシステム全体の健全性を把握できる。

---

## 設計方針

### 外部テーブル（EXTERNAL TABLE）を採用する理由

本テーブルでは EXTERNAL TABLE を採用する。

#### メリット

1. **コスト最適化**

   * 会話ログは膨大になる可能性があるが、S3 ストレージは Snowflake 内部ストレージより安価
   * クエリ実行時のみコンピュート課金されるため、長期保管コストを抑制できる

2. **柔軟な保持期間管理**

   * S3 ライフサイクルポリシーにより、古いログを自動アーカイブ（Glacier 等）
   * Snowflake 側のテーブル定義を変更せずにストレージ階層を変更可能

3. **スキーマ進化への耐性**

   * 会話ログのフォーマット変更時も、新しいパーティションから段階的に適用可能
   * 過去ログの再ロードを前提としない

#### 留意点と対処

* **クエリ速度**

  * 内部テーブルより遅いため、頻繁に利用する集計はマテリアライズドビューで高速化
* **物理最適化の制約**

  * 内部テーブルのようなクラスタリング最適化は前提としない
  * 時系列パーティション設計によるスキャン量削減を主手段とする

---

## EXTERNAL TABLE 前提の制約と品質担保

Snowflake の EXTERNAL TABLE では以下を前提とする。

* PRIMARY KEY / UNIQUE / FOREIGN KEY

  * 定義可能だが **強制（enforced）されない**
* CHECK 制約

  * サポートされない

そのため、本テーブルの品質担保は以下で行う。

* 設計ドキュメントでの明示（本書）
* 検証クエリによる定期チェック
* 取り込み元（アプリケーション）での制御
* 必要に応じた内部テーブル・MV 化

---

## パーティション設計

### S3 パス構造

```
s3://135365622922-snowflake-chatdemo-vault-prod/cortex_conversations/
  YEAR=2026/
    MONTH=01/
      DAY=02/
        HOUR=14/
          {uuid}.json
```

* パーティションカラム（YEAR, MONTH, DAY, HOUR）は `metadata$filename` から抽出される
* 原則として **時系列単位でのファイル配置**を行う

### パーティションプルーニング例

```sql
-- 効率的（パーティション指定あり）
SELECT *
FROM LOG.CORTEX_CONVERSATIONS
WHERE year = 2026 AND month = 1 AND day = 2;

-- 非効率（全ファイルスキャン）
SELECT *
FROM LOG.CORTEX_CONVERSATIONS
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL '1 day';
```

**重要**：
時系列クエリでは必ず YEAR / MONTH / DAY（必要に応じて HOUR）を WHERE 句に含める。

---

## ログファイル粒度（重要）

* JSON Lines 形式：**1行 = 1メッセージ**
* 原則として **1ファイルは同一 conversation_id に属する複数メッセージ**（例：user / assistant のペア）を含む
* ファイル単位での一貫性（conversation_id 混在なし）を前提とする

※ 将来的に「1メッセージ = 1ファイル」へ変更する可能性はあるが、本設計ではファイル単位削除・再生成を許容する。

---

## カラム設計の判断

### 論理的一意性

EXTERNAL TABLE では主キー制約を強制できないため、論理的一意性として以下を前提とする。

* 推奨識別子：

  * `conversation_id`
  * `message_role`
  * `timestamp`
* 完全な一意性は保証されないため、重複検知は検証クエリで行う

---

### 各カラムの設計意図

#### conversation_id (VARCHAR)

* 意味：1つの会話スレッドを一意識別する ID
* 生成方法：フロントエンドで UUID を生成し、すべてのメッセージに付与
* 利用例：

```sql
SELECT *
FROM LOG.CORTEX_CONVERSATIONS
WHERE conversation_id = 'abc-123-def-456'
ORDER BY timestamp;
```

---

#### session_id (VARCHAR)

* 意味：ユーザーセッション識別子
* 1セッション内で複数の会話が行われる可能性を許容
* セッション単位の行動分析に利用

---

#### user_id (VARCHAR, nullable)

* 意味：ユーザー識別子（匿名ユーザーは NULL）
* 実名は使用せず、ハッシュ化または仮名 ID を使用
* GDPR 削除要求時の論理キー

---

#### agent_name (VARCHAR)

* 意味：応答した Cortex Agent 名
* 値例：[[design.SNOWFLAKE_DEMO_AGENT]], `CUSTOMER_SUPPORT_AGENT`
* Agent 別の品質比較に利用

---

#### message_role (VARCHAR)

* 意味：発話者の種別
* 値：`user` / `assistant`

---

#### message_content (VARIANT)

* 意味：**メッセージ本文**
* 原則構造：

```json
{
  "text": "What is the total sales for department A?"
}
```

* 会話内容そのものを保持し、分析・検索の主対象とする

---

#### metadata (VARIANT)

* 意味：**観測・運用・実行時メタ情報**
* 想定内容：

```json
{
  "tokens": 12,
  "model": "mistral-large",
  "latency_ms": 1200,
  "error": null,
  "trace_id": "xxxx"
}
```

* 利用例：

```sql
SELECT agent_name,
       AVG(metadata:latency_ms::NUMBER) AS avg_latency_ms
FROM LOG.CORTEX_CONVERSATIONS
WHERE message_role = 'assistant'
  AND year = 2026 AND month = 1
GROUP BY 1;
```

---

#### timestamp (TIMESTAMP_NTZ)

* 意味：メッセージ生成日時（UTC）
* 表示時にアプリケーション側でタイムゾーン変換を行う

---

#### パーティションカラム（YEAR, MONTH, DAY, HOUR）

* S3 パス由来の時系列情報
* パーティションプルーニング専用
* NULL 混入は性能劣化につながるため、定期検証を行う

---

## 運用上の注意

### AUTO_REFRESH

* `AUTO_REFRESH = TRUE` により新規ファイルを自動検知
* 反映遅延・欠損が疑われる場合は手動 REFRESH を実施

```sql
ALTER EXTERNAL TABLE LOG.CORTEX_CONVERSATIONS REFRESH;
```

---

### データ保持ポリシー

* 直近30日：内部テーブル or MV へコピー（任意）
* 31–90日：S3 Standard
* 91–365日：S3 Intelligent-Tiering
* 1年超：S3 Glacier（クエリ不可、監査用途）

---

## セキュリティ・プライバシー

### 個人情報の取り扱い

* user_id は仮名化 ID
* PII は message_content / metadata に含めない
* フロントエンド側でマスキングを実施

### GDPR 削除要求対応

1. 対象 user_id を含むファイルを特定
2. ファイル削除または再生成
3. EXTERNAL TABLE を REFRESH

---

## 今後の拡張計画

### マテリアライズドビュー

```sql
CREATE MATERIALIZED VIEW LOG.MV_DAILY_AGENT_SUMMARY AS
SELECT DATE_TRUNC('day', timestamp) AS log_date,
       agent_name,
       COUNT(*) AS total_messages,
       COUNT_IF(message_role = 'user') AS user_messages,
       COUNT_IF(message_role = 'assistant') AS assistant_messages,
       COUNT_IF(metadata:error IS NOT NULL) AS errors,
       AVG(metadata:tokens::NUMBER) AS avg_tokens
FROM LOG.CORTEX_CONVERSATIONS
WHERE year >= 2026
GROUP BY 1, 2;
```

---

## 設計レビュー時のチェックポイント

* [ ] パーティション指定のないクエリが発行されていないか
* [ ] metadata と message_content の責務が守られているか
* [ ] 重複レコードが発生していないか
* [ ] エラー率 < 1%、平均レスポンス < 3秒を維持しているか
* [ ] PII が適切に排除・マスキングされているか
