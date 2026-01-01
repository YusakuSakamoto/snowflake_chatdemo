import azure.functions as func
import logging
import os
import json
from snowflake_db import SnowflakeConnection

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="chat", methods=["POST"])
def chat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    チャットメッセージを処理し、Snowflakeに保存するエンドポイント
    """
    logging.info('Chat endpoint triggered')

    try:
        # リクエストボディを取得
        req_body = req.get_json()
        message = req_body.get('message')
        user_id = req_body.get('user_id', 'anonymous')

        if not message:
            return func.HttpResponse(
                json.dumps({"error": "メッセージが必要です"}),
                mimetype="application/json",
                status_code=400
            )

        # Snowflakeに接続してメッセージを保存
        with SnowflakeConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_messages (user_id, message, timestamp)
                VALUES (%s, %s, CURRENT_TIMESTAMP())
                """,
                (user_id, message)
            )
            
            # 最近のメッセージを取得
            cursor.execute(
                """
                SELECT user_id, message, timestamp
                FROM chat_messages
                ORDER BY timestamp DESC
                LIMIT 10
                """
            )
            recent_messages = cursor.fetchall()

        response_data = {
            "status": "success",
            "message": "メッセージが保存されました",
            "recent_messages": [
                {
                    "user_id": row[0],
                    "message": row[1],
                    "timestamp": str(row[2])
                }
                for row in recent_messages
            ]
        }

        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"エラー: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


@app.route(route="messages", methods=["GET"])
def get_messages(req: func.HttpRequest) -> func.HttpResponse:
    """
    Snowflakeからチャットメッセージを取得するエンドポイント
    """
    logging.info('Get messages endpoint triggered')

    try:
        limit = req.params.get('limit', '50')
        
        with SnowflakeConnection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT user_id, message, timestamp
                FROM chat_messages
                ORDER BY timestamp DESC
                LIMIT {int(limit)}
                """
            )
            messages = cursor.fetchall()

        response_data = {
            "messages": [
                {
                    "user_id": row[0],
                    "message": row[1],
                    "timestamp": str(row[2])
                }
                for row in messages
            ]
        }

        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"エラー: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
