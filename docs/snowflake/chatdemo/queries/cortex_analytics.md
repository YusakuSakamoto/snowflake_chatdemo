# Cortex対話分析クエリ集

このドキュメントには、[[tables/cortex_conversation_logs]]を分析するための便利なクエリをまとめています。

---

## 📊 基本統計

### 1. 日次対話数
```sql
SELECT 
    DATE(timestamp) as date,
    COUNT(DISTINCT session_id) as unique_sessions,
    COUNT(*) as total_conversations,
    AVG(execution_time_ms) as avg_response_time_ms
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1 DESC;
```

### 2. ユーザー別活動
```sql
SELECT 
    user_id,
    COUNT(DISTINCT session_id) as session_count,
    COUNT(*) as conversation_count,
    SUM(tokens_used) as total_tokens,
    ROUND(SUM(tokens_used) * 0.0001, 2) as estimated_cost_usd  -- 仮単価
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY total_tokens DESC
LIMIT 20;
```

---

## 🔍 SQL分析

### 3. 頻出SQLパターン
```sql
SELECT 
    REGEXP_SUBSTR(sql_executed, '^(SELECT|INSERT|UPDATE|DELETE).*?FROM\\s+(\\w+)', 1, 1, 'ie') as sql_pattern,
    COUNT(*) as execution_count,
    AVG(execution_time_ms) as avg_time_ms,
    MAX(execution_time_ms) as max_time_ms
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
  AND sql_executed IS NOT NULL
GROUP BY 1
ORDER BY execution_count DESC
LIMIT 50;
```

### 4. 遅いクエリTOP10
```sql
SELECT 
    timestamp,
    user_id,
    session_id,
    user_message,
    sql_executed,
    execution_time_ms,
    tokens_used
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
  AND execution_time_ms > 5000  -- 5秒以上
ORDER BY execution_time_ms DESC
LIMIT 10;
```

---

## 🛠️ ツール使用分析

### 5. ツール使用頻度
```sql
SELECT 
    tool.value::STRING as tool_name,
    COUNT(*) as usage_count,
    AVG(execution_time_ms) as avg_execution_time_ms
FROM cortex_conversation_logs,
LATERAL FLATTEN(input => tools_used) tool
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY usage_count DESC;
```

### 6. ツール組み合わせパターン
```sql
SELECT 
    ARRAY_TO_STRING(tools_used, ' -> ') as tool_sequence,
    COUNT(*) as occurrence_count,
    AVG(execution_time_ms) as avg_time_ms
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
  AND ARRAY_SIZE(tools_used) > 1
GROUP BY 1
ORDER BY occurrence_count DESC
LIMIT 20;
```

---

## ⚠️ エラー分析

### 7. エラー率
```sql
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_requests,
    SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as error_count,
    ROUND(100.0 * error_count / total_requests, 2) as error_rate_pct
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1 DESC;
```

### 8. エラータイプ別集計
```sql
SELECT 
    REGEXP_SUBSTR(error_message, '^[^:]+') as error_type,
    COUNT(*) as error_count,
    MIN(timestamp) as first_occurrence,
    MAX(timestamp) as last_occurrence
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
  AND error_message IS NOT NULL
GROUP BY 1
ORDER BY error_count DESC;
```

---

## 💰 コスト分析

### 9. トークン使用量トレンド
```sql
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as conversation_count,
    SUM(tokens_used) as total_tokens,
    ROUND(AVG(tokens_used), 0) as avg_tokens,
    ROUND(SUM(tokens_used) * 0.0001, 2) as estimated_cost_usd
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1 AND day = 2
GROUP BY 1
ORDER BY 1;
```

### 10. コストが高い会話TOP20
```sql
SELECT 
    session_id,
    user_id,
    timestamp,
    user_message,
    tokens_used,
    ROUND(tokens_used * 0.0001, 4) as estimated_cost_usd
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
ORDER BY tokens_used DESC
LIMIT 20;
```

---

## 📈 ユーザー行動分析

### 11. セッション長の分布
```sql
SELECT 
    session_id,
    user_id,
    COUNT(*) as messages_in_session,
    DATEDIFF('minute', MIN(timestamp), MAX(timestamp)) as session_duration_minutes,
    SUM(tokens_used) as total_tokens_in_session
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY 1, 2
HAVING messages_in_session > 1
ORDER BY session_duration_minutes DESC
LIMIT 50;
```

### 12. 質問トピック分析（簡易版）
```sql
SELECT 
    CASE 
        WHEN LOWER(user_message) LIKE '%売上%' OR LOWER(user_message) LIKE '%sales%' THEN '売上分析'
        WHEN LOWER(user_message) LIKE '%在庫%' OR LOWER(user_message) LIKE '%inventory%' THEN '在庫管理'
        WHEN LOWER(user_message) LIKE '%顧客%' OR LOWER(user_message) LIKE '%customer%' THEN '顧客分析'
        WHEN LOWER(user_message) LIKE '%テーブル%' OR LOWER(user_message) LIKE '%table%' THEN 'スキーマ参照'
        ELSE 'その他'
    END as topic,
    COUNT(*) as question_count,
    AVG(execution_time_ms) as avg_response_time_ms
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY question_count DESC;
```

---

## 🔄 パフォーマンスモニタリング

### 13. レスポンスタイム分布
```sql
SELECT 
    CASE 
        WHEN execution_time_ms < 1000 THEN '< 1秒'
        WHEN execution_time_ms < 3000 THEN '1-3秒'
        WHEN execution_time_ms < 5000 THEN '3-5秒'
        WHEN execution_time_ms < 10000 THEN '5-10秒'
        ELSE '> 10秒'
    END as response_time_bucket,
    COUNT(*) as conversation_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY 
    CASE response_time_bucket
        WHEN '< 1秒' THEN 1
        WHEN '1-3秒' THEN 2
        WHEN '3-5秒' THEN 3
        WHEN '5-10秒' THEN 4
        ELSE 5
    END;
```

### 14. 時間帯別負荷
```sql
SELECT 
    HOUR(timestamp) as hour_of_day,
    COUNT(*) as request_count,
    AVG(execution_time_ms) as avg_response_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_response_time_ms
FROM cortex_conversation_logs
WHERE year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1;
```

---

## 🔗 関連ドキュメント

- [[tables/cortex_conversation_logs]] - テーブル定義
- [[schemas/logging]] - ログスキーマ全体
- [[reviews/log_architecture]] - アーキテクチャ設計
