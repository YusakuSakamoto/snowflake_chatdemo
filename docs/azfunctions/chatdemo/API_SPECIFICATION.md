# Azure Functions API仕様書

## エンドポイント一覧

### 1. チャット機能

#### POST /api/chat
Snowflake Cortex Agentとのチャット

リクエスト:
```json
{
  "message": "質問内容",
  "user_id": "user123"
}
```

レスポンス:
```json
{
  "status": "success",
  "message": "メッセージが保存されました",
  "recent_messages": [
    {
      "user_id": "user123",
      "message": "質問内容",
      "ai_response": "応答内容",
      "timestamp": "2026-01-02T12:34:56"
    }
  ]
}
```

---

### 2. ストリーミングチャット

#### POST /api/chat/stream
SSE（Server-Sent Events）形式でストリーミング応答

リクエスト:
```json
{
  "message": "質問内容",
  "user_id": "user123",
  "agent_name": "CUSTOMER_CHAT_AGENT"  // optional
}
```

レスポンス（SSE）:
```
event: text_delta
data: {"text": "応答の"}

event: text_delta
data: {"text": "一部"}

event: done
data: {"status": "completed"}
```

SSEイベント種類:
- `text_delta`: テキストの差分
- `text_final`: 最終テキスト
- `tool_detail`: ツール実行結果
- `tool_step`: ツール実行ステップ
- `done`: 完了
- `error`: エラー

---

### 3. DB設計レビュー（NEW）

#### POST /api/review/schema
Snowflake AgentによるDB設計レビューを実行し、Markdown形式で結果を返す

リクエスト:
```json
{
  "target_schema": "DB_DESIGN",
  "max_tables": 100  // optional
}
```

レスポンス:
```json
{
  "success": true,
  "message": "レビュー完了",
  "markdown": "---\ntype: agent_review\n...",
  "metadata": {
    "target_schema": "DB_DESIGN",
    "review_date": "2026-01-02",
    "max_tables": 100
  }
}
```

エラーレスポンス:
```json
{
  "success": false,
  "error": "エラーメッセージ"
}
```

実行時間: 最大15分（Agent実行時間により変動）

使用例:
```bash
# curl
curl -X POST http://localhost:7071/api/review/schema \
  -H "Content-Type: application/json" \
  -d '{"target_schema": "DB_DESIGN"}'

# Python
import requests
response = requests.post(
    "http://localhost:7071/api/review/schema",
    json={"target_schema": "DB_DESIGN", "max_tables": 50}
)
markdown = response.json()["markdown"]
```

---

## モジュール構成

### 1. function_app.py
Azure Functionsのエントリーポイント

主要関数:
- `chat_endpoint`: チャット処理
- `chat_stream_endpoint`: ストリーミングチャット（SSE）
- `review_schema_endpoint`: DB設計レビュー（NEW）

### 2. snowflake_cortex.py
Snowflake Cortex Agent呼び出しクライアント

主要クラス:
- `SnowflakeCortexClient`: Cortex Agent API wrapper

### 3. snowflake_db.py
Snowflake接続管理

主要クラス:
- `SnowflakeConnection`: コンテキストマネージャー形式の接続管理

### 4. db_review_agent.py（NEW）
DB設計レビューエージェント専用モジュール

主要クラス:
- `DBReviewAgent`: OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT のラッパー

主要メソッド:
- `review_schema()`: スキーマレビューを実行
- `save_review_to_vault()`: レビュー結果をSnowflake Stageに保存

---

## 環境変数

### 必須設定（local.settings.json）

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SNOWFLAKE_ACCOUNT": "your-account.snowflakecomputing.com",
    "SNOWFLAKE_USER": "your-user",
    "SNOWFLAKE_PASSWORD": "your-password",
    "SNOWFLAKE_WAREHOUSE": "GBPS253YS_WH",
    "SNOWFLAKE_DATABASE": "GBPS253YS_DB",
    "SNOWFLAKE_SCHEMA": "DB_DESIGN",
    "USE_MOCK": "False"
  }
}
```

---

## テスト

### DB設計レビューテスト

```bash
# 直接呼び出しテスト
cd tests/azfunctions/chatdemo
python test_review_agent.py --schema DB_DESIGN

# ローカルAzure Functions経由テスト
python test_review_agent.py --local --schema DB_DESIGN

# カスタムURL指定
python test_review_agent.py --url https://your-function.azurewebsites.net --schema APP_PRODUCTION
```

テスト出力:
- コンソール: 実行ログとMarkdownプレビュー
- ファイル: `tests/output/review_{SCHEMA}_{DATE}.md`

---

## デプロイ

### Azure Functionsへのデプロイ

```bash
# Azure CLIでログイン
az login

# 関数アプリにデプロイ
cd app/azfunctions/chatdemo
func azure functionapp publish your-function-app-name --python
```

### 環境変数設定（Azure Portal）

1. Azure Portal → Function App → 設定 → 環境変数
2. 必須環境変数を追加（local.settings.json と同じ内容）
3. 保存して再起動

---

## トラブルシューティング

### Agent実行タイムアウト
- `orchestration.budget.seconds` がデフォルト900秒（15分）
- 大規模スキーマの場合は `max_tables` で制限

### Markdown抽出失敗
- Agent出力形式が `~~~md\n...\n~~~` であることを確認
- ログでAgent生出力を確認: `logging.warning("Markdownの抽出に失敗")`

### Snowflake接続エラー
- 環境変数が正しく設定されているか確認
- Warehouse/Database/Schemaの存在を確認
- ネットワーク接続（Snowflakeへの到達性）を確認

---

## 参考資料

- [Snowflake Cortex Agent](https://docs.snowflake.com/en/user-guide/cortex-agent)
- [Azure Functions Python Developer Guide](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
