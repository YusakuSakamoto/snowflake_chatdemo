import os
import requests
import json
from typing import Dict, Any, Optional

class SnowflakeCortexClient:
    """
    Snowflake Cortex Agent REST APIクライアント
    """
    
    def __init__(self):
        self.account = os.getenv('SNOWFLAKE_ACCOUNT')
        self.host = os.getenv('SNOWFLAKE_HOST', f"{self.account}.snowflakecomputing.com")
        self.user = os.getenv('SNOWFLAKE_USER')
        self.pat = os.getenv('SNOWFLAKE_PAT')  # Personal Access Token
        self.warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
        self.database = os.getenv('SNOWFLAKE_DATABASE')
        self.schema = os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')
        self.role = os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')
        
        # Snowflake REST APIエンドポイント
        self.base_url = f"https://{self.host}/api/v2"
        self.session = requests.Session()
        
    def authenticate(self) -> bool:
        """
        Snowflake REST APIで認証を行う（PAT使用）
        """
        try:
            # PATが設定されているか確認
            if not self.pat:
                print("Personal Access Token (PAT)が設定されていません")
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
        Snowflake REST API経由でクエリを実行（PAT認証）
        """
        url = f"{self.base_url}/statements"
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.pat}',
            'X-Snowflake-Authorization-Token-Type': 'KEYPAIR_JWT'
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
