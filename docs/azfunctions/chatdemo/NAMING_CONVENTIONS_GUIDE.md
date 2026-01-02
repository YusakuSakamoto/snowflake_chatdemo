# Azure Functions 命名規則

## 概要
本ドキュメントは、Azure Functions（Python）プロジェクトにおける命名規則を定義します。一貫性のある命名により、コードの可読性と保守性が向上します。

---

## Python命名規則

### モジュール・ファイル（Module / File）
- 形式: `lowercase_with_underscores.py`
- 例:
  - `function_app.py` - メインのFunction Appエントリポイント
  - `snowflake_cortex.py` - Snowflake Cortex API クライアント
  - `snowflake_auth.py` - Snowflake認証ロジック
  - `snowflake_db.py` - Snowflakeデータベース操作
  - `stream_endpoint.py` - ストリーミングエンドポイント

### クラス（Class）
- 形式: `PascalCase`
- 例:
  - `SnowflakeCortexClient` - Cortex APIクライアント
  - `SnowflakeAuthHandler` - 認証ハンドラー
  - `MessageProcessor` - メッセージ処理クラス
  - `ResponseFormatter` - レスポンス整形クラス

### 関数・メソッド（Function / Method）
- 形式: `lowercase_with_underscores`
- 動詞始まり推奨
- 例:
  - `chat_endpoint()` - チャットエンドポイント
  - `stream_chat()` - ストリーミングチャット
  - `execute_query()` - クエリ実行
  - `save_message()` - メッセージ保存
  - `get_messages()` - メッセージ取得
  - `call_cortex_agent()` - Cortex Agent呼び出し
  - `authenticate()` - 認証処理

### 変数（Variable）
- 形式: `lowercase_with_underscores`
- 定数: `UPPERCASE_WITH_UNDERSCORES`
- 例:
  ```python
  # 通常の変数
  user_id = "anonymous"
  message_content = "Hello"
  cortex_result = None
  
  # 定数
  USE_MOCK = False
  MAX_RETRY_COUNT = 3
  DEFAULT_TIMEOUT = 30
  API_VERSION = "v2"
  ```

### プライベートメンバー
- 形式: `_leading_underscore`
- 例:
  ```python
  class SnowflakeCortexClient:
      def __init__(self):
          self._session = requests.Session()
          self._base_url = "https://..."
      
      def _build_headers(self):
          """内部使用のヘルパーメソッド"""
          pass
  ```

---

## Azure Functions固有の命名規則

### HTTPトリガー関数（Endpoint）
- 形式: `{purpose}_endpoint` または `{action}_{resource}`
- デコレーター: `@app.route(route="{route_name}")`
- 例:
  ```python
  @app.route(route="chat", methods=["POST", "OPTIONS"])
  def chat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
      """チャットメッセージ処理エンドポイント"""
      pass
  
  @app.route(route="stream", methods=["POST"])
  def stream_chat(req: func.HttpRequest) -> func.HttpResponse:
      """ストリーミングチャットエンドポイント"""
      pass
  
  @app.route(route="messages", methods=["GET"])
  def get_messages_endpoint(req: func.HttpRequest) -> func.HttpResponse:
      """メッセージ一覧取得エンドポイント"""
      pass
  ```

### ルート名（Route Name）
- 形式: `lowercase-with-hyphens` または `lowercase`
- RESTful推奨:
  - `chat` - チャット送信
  - `stream` - ストリーミング
  - `messages` - メッセージ一覧
  - `messages/{id}` - 特定メッセージ取得
  - `health` - ヘルスチェック

### タイマートリガー関数
- 形式: `{action}_{schedule}`
- 例:
  ```python
  @app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer")
  def cleanup_old_messages(timer: func.TimerRequest):
      """5分ごとに古いメッセージをクリーンアップ"""
      pass
  ```

---

## 環境変数（Environment Variables）

### 命名規則
- 形式: `UPPERCASE_WITH_UNDERSCORES`
- プレフィックス: サービス名を明示
- 例:
  ```python
  # Snowflake設定
  SNOWFLAKE_ACCOUNT = "xyz12345"
  SNOWFLAKE_HOST = "xyz12345.snowflakecomputing.com"
  SNOWFLAKE_USER = "api_user"
  SNOWFLAKE_BEARER_TOKEN = "secret_token"
  SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
  SNOWFLAKE_DATABASE = "CHATDEMO_DB"
  SNOWFLAKE_SCHEMA = "APP_PRODUCTION"
  SNOWFLAKE_ROLE = "API_ROLE"
  SNOWFLAKE_AGENT_NAME = "SNOWFLAKE_DEMO_AGENT"
  
  # Azure設定
  AZURE_STORAGE_CONNECTION_STRING = "..."
  AZURE_APP_INSIGHTS_KEY = "..."
  
  # アプリケーション設定
  USE_MOCK = "False"
  LOG_LEVEL = "INFO"
  MAX_MESSAGE_LENGTH = "5000"
  ```

### local.settings.json構造
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SNOWFLAKE_ACCOUNT": "xyz12345",
    "SNOWFLAKE_USER": "api_user",
    "SNOWFLAKE_BEARER_TOKEN": "your_token_here",
    "USE_MOCK": "False"
  }
}
```

---

## ログ出力規則

### ログレベル
- `logging.debug()`: 詳細なデバッグ情報
- `logging.info()`: 一般的な情報（関数開始/終了、正常処理）
- `logging.warning()`: 警告（リトライ、代替処理）
- `logging.error()`: エラー（例外、失敗）
- `logging.critical()`: 致命的エラー（サービス停止レベル）

### ログメッセージ形式
```python
# 良い例
logging.info('Chat endpoint triggered')
logging.info(f'User {user_id} sent message')
logging.error(f'Snowflake query failed: {str(e)}')
logging.warning(f'Retry attempt {retry_count}/{max_retries}')

# 悪い例
logging.info('処理開始')  # 何の処理か不明
logging.error('エラー')  # 詳細不足
```

---

## エラーハンドリング規則

### 例外クラス
- 形式: `{Purpose}Error` または `{Service}{Purpose}Error`
- 例:
  ```python
  class SnowflakeConnectionError(Exception):
      """Snowflake接続エラー"""
      pass
  
  class CortexAgentError(Exception):
      """Cortex Agent実行エラー"""
      pass
  
  class InvalidRequestError(Exception):
      """不正なリクエストエラー"""
      pass
  ```

### try-exceptパターン
```python
try:
    # メイン処理
    result = execute_operation()
except SpecificError as e:
    logging.error(f'Specific error occurred: {str(e)}')
    return error_response(400, "詳細なエラーメッセージ")
except Exception as e:
    logging.error(f'Unexpected error: {str(e)}')
    return error_response(500, "予期しないエラーが発生しました")
```

---

## レスポンス形式

### 成功レスポンス
```python
{
    "status": "success",
    "message": "操作が完了しました",
    "data": {
        "id": "123",
        "result": "..."
    },
    "timestamp": "2026-01-02T12:00:00Z"
}
```

### エラーレスポンス
```python
{
    "status": "error",
    "error_code": "INVALID_REQUEST",
    "message": "メッセージが必要です",
    "details": {
        "field": "message",
        "issue": "empty_value"
    },
    "timestamp": "2026-01-02T12:00:00Z"
}
```

---

## テスト命名規則

### テストファイル
- 形式: `test_{module_name}.py`
- 例:
  - `test_snowflake_cortex.py`
  - `test_function_app.py`
  - `test_auth.py`

### テスト関数
- 形式: `test_{function_name}_{scenario}`
- 例:
  ```python
  def test_chat_endpoint_success():
      """正常系：チャットメッセージ送信成功"""
      pass
  
  def test_chat_endpoint_missing_message():
      """異常系：メッセージ未指定"""
      pass
  
  def test_execute_query_connection_error():
      """異常系：接続エラー時のリトライ"""
      pass
  ```

---

## ディレクトリ構造規則

```
app/azfunctions/chatdemo/
├── function_app.py              # メインエントリポイント
├── host.json                    # Functions Host設定
├── requirements.txt             # Python依存関係
├── local.settings.json          # ローカル設定（Git管理外）
├── local.settings.json.example  # 設定テンプレート
├── snowflake_cortex.py         # Cortex APIクライアント
├── snowflake_auth.py           # 認証ロジック
├── snowflake_db.py             # DB操作
├── stream_endpoint.py          # ストリーミング処理
├── utils/                      # ユーティリティ
│   ├── __init__.py
│   ├── validators.py           # バリデーション
│   └── formatters.py           # フォーマット処理
├── models/                     # データモデル
│   ├── __init__.py
│   └── message.py              # メッセージモデル
└── tests/                      # テストコード
    ├── __init__.py
    ├── test_function_app.py
    └── test_snowflake_cortex.py
```

---

## 禁止事項

### ❌ 避けるべき命名
```python
# 悪い例
def f():                    # 意味不明な短縮形
def getData():              # camelCase（Pythonでは非推奨）
class snowflake_client:     # クラスはPascalCase
USER_ID = "test"            # 定数でない変数を大文字
```

### ❌ 避けるべきパターン
- グローバル変数の乱用
- 過度に長い関数名（`get_user_messages_from_snowflake_database_with_filters_and_sorting`）
- 略語の過剰使用（`msg`, `usr`, `db`は文脈次第）
- マジックナンバー（定数化すべき数値のハードコード）

---

## ベストプラクティス

### ✅ 推奨パターン
```python
# 定数の定義
DEFAULT_TIMEOUT = 30
MAX_RETRY_COUNT = 3
SUPPORTED_METHODS = ["GET", "POST", "OPTIONS"]

# 型ヒント使用
def process_message(message: str, user_id: str) -> Dict[str, Any]:
    """メッセージ処理"""
    pass

# Docstring記載
def execute_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Snowflake REST API経由でクエリを実行
    
    Args:
        query: 実行するSQLクエリ
    
    Returns:
        クエリ結果のディクショナリ、エラー時はNone
    
    Raises:
        SnowflakeConnectionError: 接続エラー時
    """
    pass
```

---

## 参考資料

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Azure Functions Python開発ガイド](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- [Snowflake REST API設計](docs/snowflake/chatdemo/naming_conventions.md)
