import azure.functions as func
import logging
import os
import json
from datetime import datetime
from snowflake_cortex import SnowflakeCortexClient

# モックデータ（開発用 - USE_MOCK=Trueの場合のみ使用）
mock_messages = []
USE_MOCK = os.getenv('USE_MOCK', 'False').lower() == 'true'

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

        if USE_MOCK:
            # モックデータに保存（開発用）
            mock_messages.append({
                'user_id': user_id,
                'message': message,
                'ai_response': f"これはモック応答です: {message}",
                'timestamp': datetime.now().isoformat()
            })
            
            # 最近のメッセージを取得（最大10件）
            recent_messages = mock_messages[-10:][::-1]
        else:
            # Snowflake Cortex Agentを使用
            cortex_client = SnowflakeCortexClient()
            
            # Cortex Agentでメッセージを処理
            cortex_result = cortex_client.call_cortex_agent(message)
            
            ai_response = "応答を取得できませんでした"
            if cortex_result and 'data' in cortex_result:
                ai_response = cortex_result['data'][0][0] if cortex_result['data'] else ai_response
            
            # メッセージをSnowflakeに保存
            cortex_client.save_message(user_id, message, ai_response)
            
            # 最近のメッセージを取得
            messages_data = cortex_client.get_messages(10)
            recent_messages = [
                {
                    'user_id': row[0],
                    'message': row[1],
                    'ai_response': row[2],
                    'timestamp': str(row[3])
                }
                for row in messages_data
            ] if messages_data else []

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
        
        if USE_MOCK:
            # モックデータから取得
            messages = mock_messages[-limit:][::-1]
        else:
            # Snowflakeから取得
            cortex_client = SnowflakeCortexClient()
            messages_data = cortex_client.get_messages(limit)
            messages = [
                {
                    'user_id': row[0],
                    'message': row[1],
                    'ai_response': row[2],
                    'timestamp': str(row[3])
                }
                for row in messages_data
            ] if messages_data else []

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
