# 追加のストリーミングエンドポイント
# function_app.pyに追加する内容
def chat_stream_sse(req: func.HttpRequest) -> func.HttpResponse:
import os
import requests


    v = os.getenv(name)
    if not v:
        raise ValueError(f"Missing env var: {name}")
    return v

        headers = {
    """
    ストリーミング対応のCortex Agent APIエンドポイント
    Cortex Agent REST API経由のみ許可
    """
    base_url = _env("SNOWFLAKE_ACCOUNT_URL").rstrip("/")
    token = _env("SNOWFLAKE_BEARER_TOKEN")
    database = _env("SNOWFLAKE_DATABASE")
    schema = _env("SNOWFLAKE_SCHEMA")
    agent = _env("SNOWFLAKE_AGENT_NAME")

    url = f"{base_url}/api/v2/databases/{database}/schemas/{schema}/agents/{agent}:run"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    # 以降はCortex Agent REST APIストリーム呼び出しのみ
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        payload = {
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "tool_choice": {"type": "auto"},
        }

        # ストリーミングレスポンスを生成
        def generate():
            try:
                r = requests.post(url, headers=headers, json=payload, stream=True, timeout=900)
                if r.status_code >= 400:
                    yield f"event: error\ndata: {json.dumps({'error': 'snowflake_error', 'status': r.status_code})}\n\n"
                    return

                progress = []
                tool_details = []
                answer_chunks = []
                
                # 初期イベント送信
                yield f"event: start\ndata: {json.dumps({'status': 'connected'})}\n\n"

                current_event = None
                for raw in r.iter_lines(decode_unicode=False):
                    if raw is None:
                        continue
                    
                    try:
                        line = raw.decode("utf-8").rstrip("\r")
                    except Exception:
                        continue

                    if line == "":
                        current_event = None
                        continue

                    if line.startswith("event:"):
                        current_event = line[len("event:"):].strip()
                        continue

                    if not line.startswith("data:"):
                        continue

                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        obj = json.loads(data_str)
                    except Exception:
                        continue

                    # テキストデルタ
                    if current_event == "response.text.delta":
                        t = obj.get("text") if isinstance(obj, dict) else None
                        if isinstance(t, str) and t:
                            answer_chunks.append(t)
                            # クライアントに送信
                            yield f"event: text_delta\ndata: {json.dumps({'text': t})}\n\n"

                    # 最終テキスト
                    elif current_event == "response.text":
                        t = obj.get("text") if isinstance(obj, dict) else None
                        if isinstance(t, str) and t:
                            yield f"event: text_final\ndata: {json.dumps({'text': t})}\n\n"

                    # ツール結果
                    elif current_event == "response.tool_result":
                        detail = _extract_tool_detail(obj)
                        tool_details.append(detail)
                        # クライアントに送信
                        yield f"event: tool_detail\ndata: {json.dumps(detail, ensure_ascii=False)}\n\n"
                        
                    # ツールステップ
                    elif current_event in ["response.tool.call", "response.tool.start", "response.tool.end"]:
                        tool_name = obj.get("name") or obj.get("tool_name") or "unknown"
                        step_type = current_event.split(".")[-1]
                        yield f"event: tool_step\ndata: {json.dumps({'type': step_type, 'tool_name': tool_name})}\n\n"

                # 完了イベント
                yield f"event: done\ndata: {json.dumps({'status': 'completed', 'tool_count': len(tool_details)})}\n\n"

            except Exception as e:
                logging.exception("SSE generation failed")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        # SSEレスポンスを返す
        sse_headers = {
            **CORS_HEADERS,
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        
        return func.HttpResponse(
            body=generate(),
            status_code=200,
            headers=sse_headers,
            mimetype="text/event-stream"
        )

    except Exception as e:
        logging.exception("chat_stream_sse failed")
        return _json({"ok": False, "error": str(e)}, 500)
"""
