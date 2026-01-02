import os
import requests
import json
from typing import Dict, Any, Optional
from snowflake_auth import SnowflakeAuthClient

class SnowflakeCortexClient:
    """
    Snowflake Cortex Agent REST APIクライアント
    """
    
    def __init__(self):
        self.auth_client = SnowflakeAuthClient()
        self.account = self.auth_client.account
        self.host = self.auth_client.host
        self.user = self.auth_client.user
        self.warehouse = self.auth_client.warehouse
        self.database = self.auth_client.database
        self.schema = self.auth_client.schema
        self.role = self.auth_client.role
        self.agent_name = os.getenv('SNOWFLAKE_AGENT_NAME', 'SNOWFLAKE_DEMO_AGENT')
        
        # Snowflake REST APIエンドポイント
        self.base_url = f"https://{self.host}/api/v2"
        self.session = requests.Session()
        
    def authenticate(self) -> bool:
        """
        Snowflake REST APIで認証を行う（PAT/JWT対応）
        """
        try:
            # 認証ヘッダーを取得
            auth_header = self.auth_client.get_auth_header()
            
            if not auth_header:
                print("認証情報が設定されていません")
                return False
            
            # 接続テスト
            test_query = "SELECT CURRENT_VERSION()"
            result = self.execute_query(test_query)
            
            if result:
                print("Snowflake認証成功")
                return True
            return False
        except Exception as e:
            print(f"認証エラー: {str(e)}")
            return False
    
    def execute_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Snowflake REST API経由でクエリを実行（PAT/JWT認証）
        """
        url = f"{self.base_url}/statements"
        
        # 認証ヘッダーを取得
        auth_header = self.auth_client.get_auth_header()
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            **auth_header
        }
        
        payload = {
            "statement": query,
            "timeout": 60,
            "database": self.database,
            "schema": self.schema,
            "warehouse": self.warehouse,
            "role": self.role
        }
        
        try:
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"クエリ実行エラー: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"リクエストエラー: {str(e)}")
            return None
    
    def call_cortex_agent(self, prompt: str, agent_name: Optional[str] = None, context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Snowflake Cortex AgentをREST API経由で呼び出す
        
        Note: AgentはREST API経由でのみ呼び出し可能
        エンドポイント: /api/v2/databases/{db}/schemas/{schema}/agents/{agent}:run
        """
        # Agent名が指定されていない場合は環境変数から取得
        if not agent_name:
            agent_name = self.agent_name
        
        # Agent名をスキーマとオブジェクト名に分割
        # 例: "DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT" -> ("DB_DESIGN", "OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT")
        if "." in agent_name:
            agent_schema, agent_object = agent_name.split(".", 1)
        else:
            agent_schema = self.schema
            agent_object = agent_name
        
        # コンテキストがある場合はプロンプトに追加
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"
        
        # Cortex Agent REST API エンドポイント
        url = f"{self.base_url}/databases/{self.database}/schemas/{agent_schema}/agents/{agent_object}:run"
        
        # 認証ヘッダーを取得
        auth_header = self.auth_client.get_auth_header()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            **auth_header
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": full_prompt}]
                }
            ],
            "tool_choice": {"type": "auto"}
        }
        
        try:
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=900
            )
            
            print(f"Agent API status code: {response.status_code}")
            
            if response.status_code >= 400:
                error_msg = f"Snowflake Agent Error: {response.status_code} - {response.text}"
                print(error_msg)
                return {
                    "ok": False,
                    "error": "snowflake_error",
                    "status_code": response.status_code,
                    "body": response.text
                }
            
            # ストリーミングレスポンスを収集
            full_response = ""
            line_count = 0
            for line in response.iter_lines():
                if line:
                    line_count += 1
                    decoded_line = line.decode('utf-8')
                    print(f"[Line {line_count}] {decoded_line[:200]}")  # 最初の200文字のみログ
                    
                    # SSE形式: "data: {...}"
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]  # "data: " を除去
                        if data_str.strip():
                            try:
                                data = json.loads(data_str)
                                # Snowflake Agent形式: {"content_index": N, "text": "..."}
                                if isinstance(data, dict):
                                    if "text" in data:
                                        full_response += data["text"]
                                    # 旧形式も念のため対応: {"delta": {"content": "..."}}
                                    elif "delta" in data:
                                        delta = data["delta"]
                                        if isinstance(delta, dict) and "content" in delta:
                                            full_response += delta["content"]
                            except json.JSONDecodeError as je:
                                print(f"JSON decode error: {je}")
                                pass
            
            print(f"Total lines received: {line_count}")
            print(f"Full response length: {len(full_response)}")
            print(f"Response preview: {full_response[:500]}")
            
            return {
                "ok": True,
                "response": full_response,
                "status_code": response.status_code
            }
            
        except Exception as e:
            error_msg = f"Agent呼び出しエラー: {str(e)}"
            print(error_msg)
            return {
                "ok": False,
                "error": str(e)
            }
    
    def save_message(self, user_id: str, message: str, ai_response: Optional[str] = None) -> bool:
        """
        チャットメッセージをSnowflakeに保存
        """
        # テーブルが存在しない場合は作成
        create_table_query = """
        CREATE TABLE IF NOT EXISTS CHAT_MESSAGES (
            ID NUMBER AUTOINCREMENT,
            USER_ID VARCHAR(255),
            MESSAGE TEXT,
            AI_RESPONSE TEXT,
            TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            PRIMARY KEY (ID)
        )
        """
        
        self.execute_query(create_table_query)
        
        # メッセージを挿入
        insert_query = f"""
        INSERT INTO CHAT_MESSAGES (USER_ID, MESSAGE, AI_RESPONSE)
        VALUES ('{user_id}', '{message}', '{ai_response if ai_response else 'NULL'}')
        """
        
        result = self.execute_query(insert_query)
        return result is not None
    
    def get_messages(self, limit: int = 50) -> Optional[list]:
        """
        最近のチャットメッセージを取得
        """
        query = f"""
        SELECT USER_ID, MESSAGE, AI_RESPONSE, TIMESTAMP
        FROM CHAT_MESSAGES
        ORDER BY TIMESTAMP DESC
        LIMIT {limit}
        """
        
        result = self.execute_query(query)
        
        if result and 'data' in result:
            return result['data']
        return []
