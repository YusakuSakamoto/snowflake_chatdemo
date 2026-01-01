import os
import snowflake.connector
from dotenv import load_dotenv
from snowflake_auth import SnowflakeAuthClient

load_dotenv()


class SnowflakeConnection:
    """
    Snowflakeデータベース接続を管理するコンテキストマネージャー
    """
    
    def __init__(self):
        self.connection = None
        self.auth_client = SnowflakeAuthClient()
        
    def __enter__(self):
        """
        コンテキストマネージャーの開始時にSnowflake接続を確立
        """
        # Bearer Token認証を優先
        if self.auth_client.bearer_token:
            # Personal Access Token (PAT) の場合
            self.connection = snowflake.connector.connect(
                account=self.auth_client.account,
                user=self.auth_client.user,
                authenticator='oauth',
                token=self.auth_client.bearer_token,
                warehouse=self.auth_client.warehouse,
                database=self.auth_client.database,
                schema=self.auth_client.schema
            )
        elif self.auth_client.auth_method == "private_key":
            # JWT Token認証
            jwt_token = self.auth_client.get_jwt_token()
            if jwt_token:
                self.connection = snowflake.connector.connect(
                    account=self.auth_client.account,
                    user=self.auth_client.user,
                    authenticator='oauth',
                    token=jwt_token,
                    warehouse=self.auth_client.warehouse,
                    database=self.auth_client.database,
                    schema=self.auth_client.schema
                )
            else:
                raise ValueError("Failed to generate JWT token from private key")
        else:
            raise ValueError("SNOWFLAKE_BEARER_TOKEN or SNOWFLAKE_PRIVATE_KEY_PATH must be set")
        
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        コンテキストマネージャーの終了時に接続をクローズ
        """
        if self.connection:
            self.connection.close()
        return False


def create_chat_table():
    """
    チャットメッセージテーブルを作成（初回セットアップ用）
    """
    with SnowflakeConnection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                user_id VARCHAR(255),
                message TEXT,
                timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
            """
        )
        cursor.close()
