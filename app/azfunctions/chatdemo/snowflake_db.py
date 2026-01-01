import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


class SnowflakeConnection:
    """
    Snowflakeデータベース接続を管理するコンテキストマネージャー
    """
    
    def __init__(self):
        self.connection = None
        self.account = os.getenv('SNOWFLAKE_ACCOUNT')
        self.user = os.getenv('SNOWFLAKE_USER')
        self.password = os.getenv('SNOWFLAKE_PASSWORD')
        self.warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
        self.database = os.getenv('SNOWFLAKE_DATABASE')
        self.schema = os.getenv('SNOWFLAKE_SCHEMA')
        
    def __enter__(self):
        """
        コンテキストマネージャーの開始時にSnowflake接続を確立
        """
        self.connection = snowflake.connector.connect(
            account=self.account,
            user=self.user,
            password=self.password,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema
        )
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
