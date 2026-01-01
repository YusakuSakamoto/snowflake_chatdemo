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
    
    def call_cortex_agent(self, prompt: str, context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Snowflake Cortex Agentを呼び出す
        """
        # Cortex Complete関数を使用
        cortex_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            [
                {{'role': 'system', 'content': 'あなたは親切なAIアシスタントです。日本語で回答してください。'}},
                {{'role': 'user', 'content': '{prompt}'}}
            ]
        ) as response
        """
        
        if context:
            cortex_query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                [
                    {{'role': 'system', 'content': 'あなたは親切なAIアシスタントです。以下のコンテキストを参考に回答してください。\nコンテキスト: {context}'}},
                    {{'role': 'user', 'content': '{prompt}'}}
                ]
            ) as response
            """
        
        result = self.execute_query(cortex_query)
        return result
    
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
