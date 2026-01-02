# 外部テーブル設計：[[design.CORTEX_CONVERSATIONS]]

## 概要
[[LOG.CORTEX_CONVERSATIONS]] は、Snowflake Cortex Agent との会話履歴を長期保管・分析するための外部テーブルである。

本テーブルは、S3に保存されたJSON Lines形式のログファイルを、Snowflakeから直接クエリ可能にする。  
[[APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT]] を含む、全Cortex Agentの会話ログを統合的に管理する。

## 業務上の意味
- このテーブルが表す概念  
  1レコードは「1つのメッセージ」を表す。  
  ユーザーからの質問（`message_role='user'`）とAgentからの回答（`message_role='assistant'`）が交互に記録される。

- 主な利用シーン  
  - 会話品質の分析（回答精度、レスポンス時間）
  - エラーパターンの特定と改善
  - ユーザー行動の理解（よく聞かれる質問、利用時間帯）
  - 機械学習モデルの Fine-tuning 用データセット作成

## 設計上の位置づけ
[[LOG.CORTEX_CONVERSATIONS]] は、以下の観測性（Observability）スタックの一部として機能する：

- アプリケーションログ（Azure Functions / SWA）
- Cortex Agent会話ログ ← 本テーブル
- Snowflake メトリクス（クエリ実行統計）

これらを横断的に分析することで、システム全体の健全性を把握できる。

## 設計方針

### 外部テーブルを採用する理由

本テーブルでは、EXTERNAL TABLE（外部テーブル）を採用する。

#### メリット：
1. コスト最適化  
   - 会話ログは膨大になる可能性があるが、S3ストレージは Snowflake 内部ストレージより大幅に安価
   - クエリ時のみ課金されるため、長期保管コストを抑制

2. 柔軟な保持期間管理  
   - S3のライフサイクルポリシーで古いログを自動アーカイブ（Glacier等）
   - Snowflake側のテーブル定義を変更せずにストレージ階層を変更可能

3. スキーマ進化の容易性  
   - 会話ログのフォーマットが変わっても、新しいパーティションから新スキーマを適用
   - 過去ログの再ロード不要

#### デメリットと対処：
- クエリ速度：内部テーブルより遅い → 頻繁にクエリする集計結果はマテリアライズドビューで高速化
- クラスタリング不可：外部テーブルはクラスタリングキーが使えない → パーティションによる時系列最適化で代替

### パーティション設計の詳細

S3パス構造：
```
s3://135365622922-snowflake-chatdemo-vault-prod/cortex_conversations/
  YEAR=2026/
    MONTH=01/
      DAY=02/
        HOUR=14/
          {uuid}.json
```

パーティションカラム（year, month, day, hour）は `metadata$filename` から抽出される。

#### パーティションプルーニングの例：
```sql
-- 直近24時間のログのみスキャン（効率的）
SELECT * FROM LOG.CORTEX_CONVERSATIONS
WHERE year = 2026 AND month = 1 AND day = 2;

-- パーティション指定なし（全ファイルスキャン：非効率）
SELECT * FROM LOG.CORTEX_CONVERSATIONS
WHERE timestamp > CURRENT_TIMESTAMP() - INTERVAL '1 day';
```

重要：時系列クエリでは必ず year, month, day を WHERE句に含めること。

### JSON Lines フォーマットの選択理由

各ログファイルは 1行=1メッセージ の JSON Lines (NDJSON) 形式で保存される。

#### 利点：
- 追記専用（Append-Only）に最適：会話ログは追記のみなので、行単位追記が効率的
- スキーマレス：VARIANT型で柔軟にメタデータを格納可能
- Snowflake の JSON サポート：半構造化データに対する豊富な関数群（FLATTEN, `GET` など）

## カラム設計の判断

### 主キーの概念
外部テーブルには主キー制約を設定できないが、論理的には以下が一意性を持つ：
- conversation_id + timestamp + message_role

実際には、同じ会話内で複数メッセージが同時刻に記録されることはまずない。

### 各カラムの設計意図

#### conversation_id (VARCHAR)
- 意味：1つの会話スレッドを一意識別するID
- 生成方法：フロントエンドで UUID 生成し、すべてのメッセージに付与
- 利用例：特定の会話の全履歴を取得

```sql
SELECT * FROM LOG.CORTEX_CONVERSATIONS
WHERE conversation_id = 'abc-123-def-456'
ORDER BY timestamp;
```

#### session_id (VARCHAR)
- 意味：ユーザーセッションを識別するID
- conversation_id との違い：1セッション内で複数の会話が行われる可能性
- 利用例：ユーザーの行動パターン分析（セッション時間、会話数）

#### user_id (VARCHAR, nullable)
- 意味：ユーザーを識別するID（匿名ユーザーの場合は NULL）
- プライバシー配慮：実名ではなく、ハッシュ化されたIDまたは仮名IDを使用
- GDPR対応：ユーザーから削除要求があった場合、user_id で絞り込んでログ削除

#### agent_name (VARCHAR)
- 意味：どのCortex Agentが回答したか
- 値例：[[design.SNOWFLAKE_DEMO_AGENT]], `CUSTOMER_SUPPORT_AGENT` など
- 利用例：Agent別の回答品質比較

#### message_role (VARCHAR)
- 意味：発話者の識別
- 値：`user` または `assistant`
- 利用例：ユーザーの質問だけを抽出、Agentの回答だけを抽出

```sql
-- ユーザーの質問TOP10
SELECT message_content:text::VARCHAR AS question,
       COUNT(*) AS frequency
FROM LOG.CORTEX_CONVERSATIONS
WHERE message_role = 'user'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

#### message_content (VARIANT)
- 意味：メッセージ本体と関連メタデータを含むJSON
- 構造例：
```json
{
  "text": "What is the total sales for department A?",
  "tokens": 12,
  "model": "mistral-large",
  "latency_ms": 1200,
  "error": null
}
```
- 利用例：エラーメッセージの分析

```sql
-- エラーが発生したメッセージを抽出
SELECT conversation_id, 
       message_content:text::VARCHAR AS message,
       message_content:error::VARCHAR AS error
FROM LOG.CORTEX_CONVERSATIONS
WHERE message_content:error IS NOT NULL;
```

#### timestamp (TIMESTAMP_NTZ)
- 意味：メッセージが生成された日時（タイムゾーンなし）
- なぜNTZ？：ログは UTC で統一し、表示時にアプリケーション側で変換
- 利用例：時系列分析、レスポンスタイム計算

#### metadata (VARIANT)
- 意味：実行時コンテキスト（使用モデル、トークン数、課金情報など）
- 柔軟性：将来的に追加したい情報を自由に格納できる
- 利用例：コスト分析、パフォーマンス分析

```sql
-- Agent別の平均レスポンスタイム
SELECT agent_name,
       AVG(metadata:latency_ms::NUMBER) AS avg_latency_ms
FROM LOG.CORTEX_CONVERSATIONS
WHERE message_role = 'assistant'
  AND year = 2026 AND month = 1
GROUP BY 1;
```

#### パーティションカラム（year, month, day, hour）
- 意味：S3パスから抽出されるパーティション情報
- データ型：NUMBER（0埋めなしの整数）
- 利用：必ず WHERE句で指定してパーティションプルーニングを有効化

## クエリパターン例

### パターン1：特定ユーザーの会話履歴
```sql
SELECT conversation_id,
       message_role,
       message_content:text::VARCHAR AS message,
       timestamp
FROM LOG.CORTEX_CONVERSATIONS
WHERE user_id = 'USER_123'
  AND year = 2026 AND month = 1
ORDER BY timestamp;
```

### パターン2：エラー率の日次推移
```sql
SELECT DATE_TRUNC('day', timestamp) AS day,
       COUNT(*) AS total_messages,
       COUNT_IF(message_content:error IS NOT NULL) AS errors,
       ROUND(errors / total_messages * 100, 2) AS error_rate_pct
FROM LOG.CORTEX_CONVERSATIONS
WHERE year = 2026 AND month = 1
  AND message_role = 'assistant'
GROUP BY 1
ORDER BY 1;
```

### パターン3：よく聞かれる質問TOP20
```sql
SELECT message_content:text::VARCHAR AS question,
       COUNT(*) AS frequency
FROM LOG.CORTEX_CONVERSATIONS
WHERE message_role = 'user'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20;
```

### パターン4：会話の長さ分布
```sql
SELECT conversation_id,
       COUNT(*) AS message_count,
       MIN(timestamp) AS start_time,
       MAX(timestamp) AS end_time,
       TIMESTAMPDIFF(SECOND, start_time, end_time) AS duration_sec
FROM LOG.CORTEX_CONVERSATIONS
WHERE year = 2026 AND month = 1 AND day = 2
GROUP BY 1
ORDER BY message_count DESC;
```

## 運用上の注意

### AUTO_REFRESH の動作
- ``AUTO_REFRESH`=TRUE` により、S3に新ファイルが追加されると自動的にメタデータ更新
- 通常は数分以内に反映されるが、リアルタイム性が必要な場合は手動 REFRESH も可能

```sql
ALTER EXTERNAL TABLE LOG.CORTEX_CONVERSATIONS REFRESH;
```

### ログの書き込みフロー
1. フロントエンド（Next.js）が会話メッセージを収集
2. Azure Functions がメッセージを受け取り、JSON Lines形式に変換
3. AWS SDK で S3 の適切なパーティションパスへ PUT
4. Snowflake が AUTO_REFRESH で自動検知

### データ保持ポリシー
- 直近30日：高頻度クエリ用に内部テーブルへコピー（任意）
- 31-90日：S3 Standard（外部テーブルで直接クエリ）
- 91-365日：S3 Intelligent-Tiering
- 1年超：S3 Glacier（長期アーカイブ、クエリ不可）

## セキュリティ・プライバシー

### 個人情報の取り扱い
- user_id は仮名化ID（SHA256ハッシュなど）を使用
- 実名、メールアドレス、電話番号などのPIIは格納しない
- message_content 内にPIIが含まれないよう、フロントエンド側でマスキング

### GDPR削除要求への対応
ユーザーから削除要求があった場合：
1. S3から該当 user_id のログファイルを特定
2. ファイルを削除または該当行をマスキング
3. 外部テーブルを REFRESH

### アクセス制御
```sql
-- ログ閲覧権限（開発者・データアナリスト向け）
GRANT SELECT ON LOG.CORTEX_CONVERSATIONS TO ROLE LOG_VIEWER;

-- 個人情報を含むカラムへのアクセス制限
CREATE MASKING POLICY mask_user_id AS (val VARCHAR) RETURNS VARCHAR ->
  CASE 
    WHEN CURRENT_ROLE() IN ('LOG_ADMIN', 'PRIVACY_OFFICER') THEN val
    ELSE '*MASKED*'
  END;

ALTER TABLE LOG.CORTEX_CONVERSATIONS MODIFY COLUMN user_id 
  SET MASKING POLICY mask_user_id;
```

## 今後の拡張計画

### マテリアライズドビューによる高速化
頻繁にクエリされる集計はMVで事前計算：
```sql
CREATE MATERIALIZED VIEW LOG.MV_DAILY_AGENT_SUMMARY AS
SELECT DATE_TRUNC('day', timestamp) AS log_date,
       agent_name,
       COUNT(*) AS total_messages,
       COUNT_IF(message_role = 'user') AS user_messages,
       COUNT_IF(message_role = 'assistant') AS assistant_messages,
       COUNT_IF(message_content:error IS NOT NULL) AS errors,
       AVG(message_content:tokens::NUMBER) AS avg_tokens
FROM LOG.CORTEX_CONVERSATIONS
WHERE year >= 2026
GROUP BY 1, 2;
```

### アラート設定
エラー率が閾値を超えた場合に通知：
```sql
CREATE ALERT high_error_rate
  WAREHOUSE = MONITORING_WH
  SCHEDULE = '5 MINUTE'
  IF EXISTS (
    SELECT 1 FROM LOG.MV_DAILY_AGENT_SUMMARY
    WHERE log_date = CURRENT_DATE()
      AND errors / NULLIF(assistant_messages, 0) > 0.05
  )
  THEN CALL notify_slack('High error rate in Cortex Agent!');
```

### 全文検索インデックス
特定のキーワードでメッセージを検索する場合、Snowflake Search Optimization Service を検討：
```sql
ALTER TABLE LOG.CORTEX_CONVERSATIONS 
  ADD SEARCH OPTIMIZATION ON (message_content);
```

## 設計レビュー時のチェックポイント
- [ ] パーティション指定のないクエリが発行されていないか
- [ ] エラー率が許容範囲内か（目標: <1%）
- [ ] 平均レスポンスタイムが目標内か（目標: <3秒）
- [ ] S3ストレージコストが予算内か
- [ ] PIIが適切にマスキングされているか
