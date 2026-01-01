import azure.functions as func
import logging
import os
import json
from datetime import datetime

# モックデータ（開発用）
mock_messages = []

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="chat", methods=["POST", "OPTIONS"])
def chat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    チャットメッセージを処理し、Snowflakeに保存するエンドポイント
    """
    logging.info('Chat endpoint triggered')
    
    # OPTIONSリクエスト（CORS preflight）への対応
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )

    try:
        # リクエストボディを取得
        req_body = req.get_json()
        message = req_body.get('message')
        user_id = req_body.get('user_id', 'anonymous')

        if not message:
            return func.HttpResponse(
                json.dumps({"error": "メッセージが必要です"}),
                mimetype="application/json",
                status_code=400,
                headers={
                    "Access-Control-Allow-Origin": "*"
                }
            )

        # モックデータに保存（開発用）
        mock_messages.append({
            'user_id': user_id,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # 最近のメッセージを取得（最大10件）
        recent_messages = mock_messages[-10:][::-1]

        response_data = {
            "status": "success",
            "message": "メッセージが保存されました",
            "recent_messages": recent_messages
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
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*"
            }
        )


@app.route(route="messages", methods=["GET", "OPTIONS"])
def get_messages(req: func.HttpRequest) -> func.HttpResponse:
    """
    Snowflakeからチャットメッセージを取得するエンドポイント
    """
    logging.info('Get messages endpoint triggered')
    
    # OPTIONSリクエスト（CORS preflight）への対応
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )

    try:
        limit = int(req.params.get('limit', '50'))
        
        # モックデータから取得
        messages = mock_messages[-limit:][::-1]

        response_data = {
            "messages": messages
        }

        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )

    except Exception as e:
        logging.error(f"エラー: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*"
            }
        )
