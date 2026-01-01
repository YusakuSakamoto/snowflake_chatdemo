# Conversation History (会話履歴)

> [!info] 概要
> Snowflake Cortex Agentとユーザーの対話履歴を記録するテーブル

## 📊 基本情報

| 項目 | 内容 |
|------|------|
| **スキーマ** | [[schemas/logging]] |
| **作成日** | 2026-01-02 |
| **更新頻度** | 高頻度（リアルタイム） |
| **データ量** | 〜1000万行/月 |
| **保持期間** | 1年間 |
| **ストレージ** | S3外部ステージ |

**タグ**: #ログ #Cortex #対話履歴 #分析

---

## 🏗️ テーブル定義

### 外部ステージ
```sql
CREATE STAGE s3_cortex_logs_stage
  URL = 's3://bucket/cortex_logs/'
  CREDENTIALS = (AWS_KEY_ID = '...' AWS_SECRET_KEY = '...');
```

### 外部テーブル
```sql
CREATE EXTERNAL TABLE cortex_conversation_logs (
    session_id VARCHAR AS (value:session_id::VARCHAR),
    user_id VARCHAR AS (value:user_id::VARCHAR),
    timestamp TIMESTAMP_NTZ AS (value:timestamp::TIMESTAMP_NTZ),
    user_message VARCHAR AS (value:user_message::VARCHAR),
    agent_response VARCHAR AS (value:agent_response::VARCHAR),
    sql_executed VARCHAR AS (value:sql_executed::VARCHAR),
    tools_used ARRAY AS (value:tools_used::ARRAY),
    execution_time_ms NUMBER AS (value:execution_time_ms::NUMBER),
    tokens_used NUMBER AS (value:tokens_used::NUMBER),
    error_message VARCHAR AS (value:error_message::VARCHAR),
    metadata VARIANT AS (value:metadata::VARIANT),
    
    -- パーティションカラム
    year INT AS (SPLIT_PART(metadata$filename, '/', -4)),
    month INT AS (SPLIT_PART(metadata$filename, '/', -3)),
    day INT AS (SPLIT_PART(metadata$filename, '/', -2))
)
PARTITION BY (year, month, day)
LOCATION = @s3_cortex_logs_stage
FILE_FORMAT = (TYPE = JSON)
AUTO_REFRESH = TRUE;
```

## 📋 カラム一覧

| カラム名 | データ型 | 説明 |
|----------|----------|------|
| `session_id` | VARCHAR | セッション識別子（UUID） |
| `user_id` | VARCHAR | ユーザー識別子 |
| `timestamp` | TIMESTAMP_NTZ | 対話発生時刻 |
| `user_message` | VARCHAR | ユーザーの質問・入力 |
| `agent_response` | VARCHAR | Agentの回答 |
| `sql_executed` | VARCHAR | 実行されたSQLクエリ |
| `tools_used` | ARRAY | 使用されたツール一覧 |
| `execution_time_ms` | NUMBER | 処理時間（ミリ秒） |
| `tokens_used` | NUMBER | 使用トークン数 |
| `error_message` | VARCHAR | エラーメッセージ（あれば） |
| `metadata` | VARIANT | その他のメタデータ（JSON） |
| `year` | INT | パーティション: 年 |
| `month` | INT | パーティション: 月 |
| `day` | INT | パーティション: 日 |

## 🗂️ S3ディレクトリ構造

```
s3://bucket/cortex_logs/
└── year=2026/
    └── month=01/
        └── day=02/
            ├── session_abc123_001.json
            ├── session_abc123_002.json
            └── session_def456_001.json
```

### ファイルフォーマット（JSON Lines）
```json
{"session_id":"abc123","user_id":"user001","timestamp":"2026-01-02T10:30:00","user_message":"Show me sales data","agent_response":"Here's the sales data...","sql_executed":"SELECT * FROM sales WHERE...","tools_used":["query_database","format_results"],"execution_time_ms":1234,"tokens_used":500,"error_message":null,"metadata":{"ip":"192.168.1.1","user_agent":"Chrome"}}
```

## 🚀 パフォーマンス設計

### パーティショニング効果
```sql
-- パーティション指定で高速検索
SELECT * FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1 AND day = 2
  AND session_id = 'abc123';
```

### 定期リフレッシュ
```sql
ALTER EXTERNAL TABLE cortex_conversation_logs REFRESH;
```

## 📈 使用パターン

### 1. セッション別対話履歴
```sql
SELECT 
    timestamp,
    user_message,
    agent_response,
    execution_time_ms
FROM cortex_conversation_logs
WHERE session_id = 'abc123'
ORDER BY timestamp;
```

### 2. SQL実行頻度分析
```sql
SELECT 
    sql_executed,
    COUNT(*) as execution_count,
    AVG(execution_time_ms) as avg_time_ms
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
  AND sql_executed IS NOT NULL
GROUP BY sql_executed
ORDER BY execution_count DESC;
```

### 3. ツール使用統計
```sql
SELECT 
    FLATTEN(tools_used) as tool,
    COUNT(*) as usage_count
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY tool
ORDER BY usage_count DESC;
```

### 4. エラー分析
```sql
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as error_count,
    error_message
FROM cortex_conversation_logs
WHERE error_message IS NOT NULL
  AND year = 2026 AND month = 1
GROUP BY 1, 3
ORDER BY 1 DESC;
```

### 5. コスト分析（トークン使用量）
```sql
SELECT 
    DATE_TRUNC('day', timestamp) as date,
    COUNT(*) as conversation_count,
    SUM(tokens_used) as total_tokens,
    AVG(tokens_used) as avg_tokens_per_conversation
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1 DESC;
```

## 🔗 関連テーブル

- [[tables/azure_functions_logs]] - バックエンドログと突合
- [[tables/snowflake_metrics]] - クエリパフォーマンスと相関分析

## ⚠️ 注意事項

- [ ] 個人情報を含む可能性があるため、アクセス制限を設定
- [ ] S3バケットは暗号化必須
- [ ] 古いログは定期的にアーカイブ（1年保持後に削除）
- [ ] パーティション指定なしの全件検索は避ける

## 🔄 変更履歴

| 日付 | 変更内容 | 担当者 |
|------|----------|--------|
| 2026-01-02 | 初版作成 - 外部テーブル設計 | - |

## 🔍 関連ドキュメント

- [[schemas/logging]] - ログスキーマ全体設計
- [[reviews/log_architecture]] - ログアーキテクチャレビュー
- [[queries/cortex_analytics]] - Cortex対話分析クエリ集
