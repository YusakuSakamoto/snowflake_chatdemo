def create_chat_table():

"""
このファイルではSnowflake DBへの直接接続・SQL実行は一切許可されていません。
Cortex Agent REST API経由のみ許可されています。
このモジュール経由でのDBアクセスは必ず例外となります。
"""


    raise RuntimeError("Snowflake DBへの直接アクセスは禁止されています。Cortex Agent REST API経由のみ許可されています。")
class SnowflakeConnection:
