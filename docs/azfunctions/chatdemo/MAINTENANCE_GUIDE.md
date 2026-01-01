# Azure Functions メンテナンスガイド

## 概要
本ドキュメントは、Azure Functions（Python）プロジェクトのメンテナンス規則と手順を定義します。

---

## 命名規則

詳細は [naming_conventions.md](naming_conventions.md) を参照してください。

### 主要ルール
- **モジュール**: `lowercase_with_underscores.py`
- **クラス**: `PascalCase`
- **関数**: `lowercase_with_underscores`
- **定数**: `UPPERCASE_WITH_UNDERSCORES`
- **エンドポイント**: `{action}_{resource}_endpoint`

---

## 開発環境セットアップ

### 1. Python仮想環境
```bash
# プロジェクトルートで実行
cd /home/yolo/pg/snowflake_chatdemo
python -m venv .venv
source .venv/bin/activate  # WSL/Linux
```

### 2. 依存関係インストール
```bash
cd app/azfunctions/chatdemo
pip install -r requirements.txt
```

### 3. 環境変数設定
```bash
# local.settings.json.exampleをコピー
cp local.settings.json.example local.settings.json

# 必要な環境変数を設定
# SNOWFLAKE_ACCOUNT, SNOWFLAKE_BEARER_TOKEN など
```

### 4. ローカル実行
```bash
# Azure Functions Core Tools使用
func start

# または開発用モック使用
USE_MOCK=True func start
```

---

## プロジェクト構造

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
└── stream_endpoint.py          # ストリーミング処理
```

---

## コーディング規則

### 1. Pythonスタイルガイド（PEP 8準拠）

#### インデント
- スペース4つ（タブ禁止）
- 継続行は適切にインデント

```python
# 良い例
def long_function_name(
    var_one: str,
    var_two: int,
    var_three: Dict[str, Any]
) -> Optional[str]:
    pass

# 悪い例
def long_function_name(var_one: str, var_two: int,
var_three: Dict[str, Any]) -> Optional[str]:
    pass
```

#### 行の長さ
- 最大79文字（コード）
- 最大72文字（Docstring、コメント）
- 長い行は適切に分割

```python
# 良い例
result = some_function(
    argument_one,
    argument_two,
    argument_three
)

# 悪い例
result = some_function(argument_one, argument_two, argument_three, argument_four, argument_five)
```

#### インポート
- 標準ライブラリ → サードパーティ → ローカルモジュール
- アルファベット順にソート
- 1行1インポート

```python
# 良い例
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

import requests
from azure.functions import HttpRequest, HttpResponse

from snowflake_cortex import SnowflakeCortexClient
from snowflake_auth import authenticate

# 悪い例
import json, os, logging
from snowflake_cortex import *
```

### 2. 型ヒント必須

```python
# 良い例
def process_message(
    message: str,
    user_id: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """メッセージを処理して結果を返す"""
    pass

# 悪い例
def process_message(message, user_id, options=None):
    pass
```

### 3. Docstring必須（関数・クラス・モジュール）

```python
def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Snowflake REST API経由でクエリを実行する
    
    Args:
        query: 実行するSQLクエリ文字列
        params: クエリパラメータ（オプション）
    
    Returns:
        クエリ実行結果を含むディクショナリ
        {
            "data": [...],
            "row_count": 123,
            "status": "success"
        }
    
    Raises:
        SnowflakeConnectionError: Snowflake接続エラー時
        InvalidQueryError: クエリ構文エラー時
    
    Example:
        >>> result = execute_query("SELECT * FROM table LIMIT 10")
        >>> print(result['row_count'])
        10
    """
    pass
```

### 4. エラーハンドリング

#### try-exceptの適切な使用
```python
# 良い例
try:
    result = cortex_client.execute_query(query)
except SnowflakeConnectionError as e:
    logging.error(f'Connection error: {str(e)}')
    return error_response(503, "Snowflakeに接続できません")
except InvalidQueryError as e:
    logging.error(f'Query error: {str(e)}')
    return error_response(400, "クエリが不正です")
except Exception as e:
    logging.error(f'Unexpected error: {str(e)}')
    return error_response(500, "予期しないエラーが発生しました")

# 悪い例
try:
    result = cortex_client.execute_query(query)
except:
    return error_response(500, "エラー")
```

#### カスタム例外の定義
```python
class SnowflakeError(Exception):
    """Snowflake関連エラーの基底クラス"""
    pass

class SnowflakeConnectionError(SnowflakeError):
    """Snowflake接続エラー"""
    pass

class SnowflakeQueryError(SnowflakeError):
    """Snowflakeクエリ実行エラー"""
    pass
```

### 5. ログ出力

#### ログレベルの使い分け
```python
# DEBUG: 詳細なデバッグ情報
logging.debug(f'Query parameters: {params}')

# INFO: 正常な処理フロー
logging.info('Chat endpoint triggered')
logging.info(f'Message saved for user {user_id}')

# WARNING: 警告（処理は継続）
logging.warning(f'Retry attempt {retry_count}/{max_retries}')
logging.warning('Token expiring soon, refreshing')

# ERROR: エラー（処理失敗）
logging.error(f'Query execution failed: {str(e)}')
logging.error(f'Authentication failed for user {user_id}')

# CRITICAL: 致命的エラー（サービス停止レベル）
logging.critical('Database connection pool exhausted')
```

#### 構造化ログ（推奨）
```python
import json

logging.info(json.dumps({
    'event': 'message_processed',
    'user_id': user_id,
    'message_length': len(message),
    'processing_time_ms': elapsed_time,
    'timestamp': datetime.utcnow().isoformat()
}))
```

---

## テスト規則

### 1. テストファイル構造
```
tests/azfunctions/chatdemo/
├── __init__.py
├── test_function_app.py
├── test_snowflake_cortex.py
├── test_snowflake_auth.py
└── fixtures/
    ├── __init__.py
    └── sample_data.py
```

### 2. テスト命名
```python
def test_chat_endpoint_success():
    """正常系：チャットメッセージ送信成功"""
    pass

def test_chat_endpoint_missing_message():
    """異常系：メッセージパラメータ未指定"""
    pass

def test_execute_query_timeout():
    """異常系：クエリ実行タイムアウト"""
    pass
```

### 3. テスト実行
```bash
# すべてのテスト実行
pytest tests/azfunctions/chatdemo/

# 特定のテストファイル
pytest tests/azfunctions/chatdemo/test_function_app.py

# カバレッジ付き
pytest --cov=app/azfunctions/chatdemo tests/azfunctions/chatdemo/
```

---

## デプロイ手順

### 1. デプロイ前チェックリスト
- [ ] すべてのテストが通過
- [ ] 環境変数が正しく設定されている
- [ ] requirements.txtが最新
- [ ] ログレベルが本番用（INFO以上）
- [ ] モックモード無効化（USE_MOCK=False）
- [ ] 機密情報がコードにハードコードされていない

### 2. Azure Functionsへのデプロイ
```bash
# Azure CLIでログイン
az login

# Function Appにデプロイ
func azure functionapp publish <function-app-name>

# 環境変数設定（Azure Portal または CLI）
az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group <resource-group> \
  --settings \
    SNOWFLAKE_ACCOUNT="xyz12345" \
    SNOWFLAKE_BEARER_TOKEN="@Microsoft.KeyVault(SecretUri=...)"
```

### 3. デプロイ後の確認
```bash
# ヘルスチェック
curl https://<function-app-name>.azurewebsites.net/api/health

# ログ確認
func azure functionapp logstream <function-app-name>
```

---

## トラブルシューティング

### 1. Snowflake接続エラー
```python
# エラー: "Failed to connect to Snowflake"
# 確認事項：
# - SNOWFLAKE_ACCOUNT が正しいか
# - SNOWFLAKE_BEARER_TOKEN (PAT) が有効か
# - ネットワークポリシーでIPが許可されているか
# - WAREHOUSEが起動しているか

# デバッグ方法：
logging.debug(f'Account: {self.account}')
logging.debug(f'Host: {self.host}')
logging.debug(f'Warehouse: {self.warehouse}')
```

### 2. CORS エラー
```python
# フロントエンドからのリクエストがブロックされる場合

# local.settings.json に追加
{
  "Host": {
    "CORS": "*",
    "CORSCredentials": false
  }
}

# レスポンスヘッダーに追加
headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization"
}
```

### 3. タイムアウトエラー
```python
# Function実行タイムアウト（デフォルト5分）

# host.json で延長
{
  "version": "2.0",
  "functionTimeout": "00:10:00"  # 10分
}

# Snowflakeクエリタイムアウト
execute_query(query, timeout=30)  # 30秒
```

---

## パフォーマンス最適化

### 1. 接続プール
```python
class SnowflakeCortexClient:
    def __init__(self):
        # セッションを再利用
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.bearer_token}'
        })
```

### 2. 非同期処理（必要に応じて）
```python
import asyncio
import aiohttp

async def fetch_multiple_queries(queries: List[str]) -> List[Dict]:
    """複数クエリを並列実行"""
    async with aiohttp.ClientSession() as session:
        tasks = [execute_async(session, q) for q in queries]
        results = await asyncio.gather(*tasks)
    return results
```

### 3. キャッシュ戦略
```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=128)
def get_cached_config(key: str) -> Any:
    """設定情報をキャッシュ"""
    return fetch_config(key)
```

---

## セキュリティベストプラクティス

### 1. 機密情報管理
```python
# ❌ 悪い例
SNOWFLAKE_BEARER_TOKEN = "secret_token_12345"

# ✅ 良い例
SNOWFLAKE_BEARER_TOKEN = os.getenv('SNOWFLAKE_BEARER_TOKEN')

# Azure Key Vault使用（推奨）
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://<vault-name>.vault.azure.net/", credential=credential)
token = client.get_secret("snowflake-bearer-token").value
```

### 2. 入力バリデーション
```python
def validate_message(message: str) -> bool:
    """メッセージのバリデーション"""
    if not message or not message.strip():
        raise InvalidRequestError("メッセージが空です")
    
    if len(message) > 5000:
        raise InvalidRequestError("メッセージが長すぎます（最大5000文字）")
    
    # SQLインジェクション対策（Snowflakeパラメータバインド使用）
    return True
```

### 3. レート制限
```python
from functools import wraps
from time import time

def rate_limit(max_calls: int, time_window: int):
    """レート制限デコレーター"""
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time()
            calls[:] = [c for c in calls if c > now - time_window]
            
            if len(calls) >= max_calls:
                raise TooManyRequestsError("レート制限を超えました")
            
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=10, time_window=60)
def chat_endpoint(req):
    pass
```

---

## 監視・アラート

### 1. Application Insights統合
```python
from applicationinsights import TelemetryClient

tc = TelemetryClient(os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY'))

# カスタムメトリクス
tc.track_metric('message_processing_time', elapsed_time)
tc.track_metric('query_execution_time', query_time)

# カスタムイベント
tc.track_event('message_processed', {
    'user_id': user_id,
    'message_length': len(message)
})

# 例外トラッキング
try:
    result = process()
except Exception as e:
    tc.track_exception()
    raise
```

### 2. ヘルスチェックエンドポイント
```python
@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """ヘルスチェックエンドポイント"""
    try:
        # Snowflake接続確認
        cortex_client = SnowflakeCortexClient()
        cortex_client.authenticate()
        
        return func.HttpResponse(
            json.dumps({
                "status": "healthy",
                "service": "azure-functions-chatdemo",
                "timestamp": datetime.utcnow().isoformat(),
                "dependencies": {
                    "snowflake": "ok"
                }
            }),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f'Health check failed: {str(e)}')
        return func.HttpResponse(
            json.dumps({
                "status": "unhealthy",
                "error": str(e)
            }),
            mimetype="application/json",
            status_code=503
        )
```

---

## Git運用規則

本プロジェクトは統一されたGit運用規則に従います。

詳細は [docs/git/chatdemo/GIT_WORKFLOW.md](../../git/chatdemo/GIT_WORKFLOW.md) を参照してください。

### コミットメッセージ例
```bash
# 良い例
git commit -m "feat: ストリーミングチャットエンドポイント追加"
git commit -m "fix: Snowflake認証エラー時のリトライ処理修正"
git commit -m "refactor: ログ出力を構造化ログに変更"
git commit -m "test: Cortex APIクライアントのユニットテスト追加"

# 悪い例
git commit -m "update"
git commit -m "bug fix"
git commit -m "Add new feature"  # 英語（日本語推奨）
```

---

## 参考ドキュメント

- [Azure Functions Python開発ガイド](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Snowflake REST API Documentation](https://docs.snowflake.com/en/developer-guide/sql-api/index.html)
- [命名規則](naming_conventions.md)
- [Git運用規則](../../git/chatdemo/GIT_WORKFLOW.md)
