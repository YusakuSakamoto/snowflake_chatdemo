import os
import snowflake.connector
from dotenv import load_dotenv
from snowflake_auth import SnowflakeAuthClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

load_dotenv()


class SnowflakeConnection:
    """
    Snowflakeデータベース接続を管理するコンテキストマネージャー
    """
    
    def __init__(self):
        self.connection = None
        self.auth_client = SnowflakeAuthClient()
        
    def _load_private_key(self):
        """秘密鍵をロードしてRSAPrivateKeyオブジェクトを返す"""
        if not self.auth_client.private_key_path or not os.path.exists(self.auth_client.private_key_path):
            return None
        
        with open(self.auth_client.private_key_path, "rb") as key_file:
            private_key_data = key_file.read()
        
        passphrase = self.auth_client.private_key_passphrase.encode() if self.auth_client.private_key_passphrase else None
        
        private_key = serialization.load_pem_private_key(
            private_key_data,
            password=passphrase,
            backend=default_backend()
        )
        
        return private_key
        
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
            # 秘密鍵認証（RSAPrivateKeyオブジェクトを直接渡す）
            private_key = self._load_private_key()
            if private_key:
                self.connection = snowflake.connector.connect(
                    account=self.auth_client.account,
                    user=self.auth_client.user,
                    private_key=private_key,
                    warehouse=self.auth_client.warehouse,
                    database=self.auth_client.database,
                    schema=self.auth_client.schema,
                    role=self.auth_client.role
                )
            else:
                raise ValueError("Failed to load private key")
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
