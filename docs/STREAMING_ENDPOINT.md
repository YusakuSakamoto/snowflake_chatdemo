# ストリーミング対応エンドポイント

## `/api/chat-stream`

Snowflake Cortex Agent の REST API をストリーミングで呼び出す新しいエンドポイントを追加しました。

### 機能

1. **Server-Sent Events (SSE) ストリーミング対応**
   - `response.text.delta` イベントでリアルタイムにテキストを受信
   - `response.tool_result` イベントでツール実行結果を取得

2. **プログレス追跡**
   - 改行、句点、セクション区切り（##）で自動フラッシュ
   - 処理状況を `progress` 配列で返却

3. **ツール実行詳細**
   - `resolve_entity_alias`: エンティティ名解決
   - `expand_department_scope`: 部門スコープ展開
   - `text_to_sql`: 自然言語からSQL生成
   - 各ツールの入力、出力、SQL、実行時間を記録

4. **文字化け対策**
   - `_fix_mojibake()` で latin-1/utf-8 変換

### リクエスト

```bash
POST /api/chat-stream
Content-Type: application/json

{
  "text": "売上トップ10を教えて",
  "message": "売上トップ10を教えて",  # textまたはmessage
  "input": "売上トップ10を教えて"      # inputも可
}
```

### レスポンス

```json
{
  "ok": true,
  "elapsed_sec": 3.452,
  "answer": "売上トップ10は以下の通りです...",
  "progress": [
    "開始：Agentに問い合わせました",
    "売上トップ10は以下の通りです",
    "1. 商品A: ¥1,000,000",
    "完了：最終回答を受け取りました"
  ],
  "tool_logs": [
    "text_to_sql (completed)",
    "resolve_entity_alias (completed)"
  ],
  "tool_details": [
    {
      "tool_name": "text_to_sql",
      "status": "completed",
      "elapsed_ms": 1234,
      "input": {"note": "売上トップ10を教えて"},
      "output": [...],
      "sql": "SELECT * FROM sales ORDER BY amount DESC LIMIT 10",
      "raw": {...}
    }
  ],
  "events_count": 45
}
```

### 環境変数

`local.settings.json` に以下が必要：

```json
{
  "Values": {
    "SNOWFLAKE_ACCOUNT_URL": "https://PGPALAB-IY16795.snowflakecomputing.com",
    "SNOWFLAKE_BEARER_TOKEN": "eyJraWQi...",
    "SNOWFLAKE_DATABASE": "GBPS253YS_DB",
    "SNOWFLAKE_SCHEMA": "APP_PRODUCTION",
    "SNOWFLAKE_AGENT_NAME": "SNOWFLAKE_DEMO_AGENT"
  }
}
```

### エラーハンドリング

1. **Snowflake エラー** (HTTP 400+)
   ```json
   {
     "ok": false,
     "error": "snowflake_error",
     "snowflake_status": 401,
     "body": "Invalid token"
   }
   ```

2. **内部エラー**
   ```json
   {
     "ok": false,
     "error": "internal_error",
     "message": "Connection timeout"
   }
   ```

### 既存エンドポイントとの比較

| 機能 | `/api/chat` | `/api/chat-stream` |
|------|-------------|-------------------|
| ストリーミング | ❌ | ✅ |
| プログレス追跡 | ❌ | ✅ |
| ツール詳細 | ❌ | ✅ |
| モックモード | ✅ | ❌ |
| メッセージ保存 | ✅ | ❌ |
| Cortex接続 | `snowflake_cortex.py` | 直接REST API |

### 使用例

```javascript
// フロントエンドからの呼び出し
const response = await axios.post('http://localhost:7071/api/chat-stream', {
  text: '今月の売上を教えて'
});

console.log('回答:', response.data.answer);
console.log('処理時間:', response.data.elapsed_sec, '秒');
console.log('使用ツール:', response.data.tool_logs);

// プログレス表示
response.data.progress.forEach(line => {
  console.log(line);
});
```

### テスト

```bash
# ローカルテスト
curl -X POST http://localhost:7071/api/chat-stream \
  -H "Content-Type: application/json" \
  -d '{"text":"売上トップ10を教えて"}'
```

### 注意事項

- タイムアウト: 900秒（15分）
- 文字エンコーディング: UTF-8
- CORS: `*` (開発環境)
- プログレスは400文字ごとに分割
