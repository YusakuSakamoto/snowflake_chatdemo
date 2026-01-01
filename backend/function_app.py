import azure.functions as func
import logging
import os
import json
import time
import requests
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


# ----------------------------
# ストリーミング対応の新しいエンドポイント
# ----------------------------
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")
CORS_HEADERS = {
    "Access-Control-Allow-Origin": CORS_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
}


def _json(payload: dict, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
        headers=CORS_HEADERS,
    )


def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise ValueError(f"Missing env var: {name}")
    return v


def _fix_mojibake(s: str) -> str:
    if not isinstance(s, str) or not s:
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except Exception:
        return s


def _find_flush_pos(buf: str) -> int:
    """改行 / ## / 句点でフラッシュ位置を見つける"""
    if not buf:
        return 0

    nl = buf.rfind("\n")
    if nl >= 0:
        return nl + 1

    idx = buf.find("## ")
    if idx > 0:
        return idx

    last = -1
    for c in ["。", "!", "!", "?", "?"]:
        last = max(last, buf.rfind(c))
    if last >= 0:
        return last + 1

    return 0


def _first_content_json(obj: dict):
    """Snowflake tool_result は obj['content'][0]['json'] に情報が入ることが多い"""
    try:
        content = obj.get("content")
        if isinstance(content, list) and len(content) > 0:
            c0 = content[0]
            if isinstance(c0, dict):
                j = c0.get("json")
                if isinstance(j, dict):
                    return j
    except Exception:
        pass
    return None


def _try_parse_json_string(v):
    if isinstance(v, str):
        s = v.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except Exception:
                return v
    return v


def _extract_tool_detail(obj: dict):
    """ツール実行結果から詳細を抽出"""
    if not isinstance(obj, dict):
        return {"tool_name": "tool", "status": "unknown", "input": None, "output": None, "sql": None, "raw": obj}

    tool_name = obj.get("name") or obj.get("tool_name") or "tool"
    status = obj.get("status") or "unknown"
    elapsed_ms = obj.get("elapsed_ms") or obj.get("elapsedMs")

    cj = _first_content_json(obj)

    tool_input = None
    tool_output = None
    sql = None

    if isinstance(cj, dict):
        if "result" in cj:
            parsed = _try_parse_json_string(cj.get("result"))
            tool_output = parsed if isinstance(parsed, (dict, list)) else {"result": parsed}

            if isinstance(parsed, dict):
                tool_input = {"term": parsed.get("term")} if parsed.get("term") else None

        if "sql" in cj and isinstance(cj.get("sql"), str):
            sql = cj.get("sql")

        if "result_set" in cj and cj.get("result_set") is not None:
            tool_output = cj.get("result_set")

        if tool_name == "text_to_sql" and tool_input is None:
            t = cj.get("text")
            if isinstance(t, str) and t:
                tool_input = {"note": t}

    return {
        "tool_name": str(tool_name),
        "status": status,
        "elapsed_ms": elapsed_ms,
        "input": tool_input,
        "output": tool_output,
        "sql": sql,
        "raw": obj,
    }


@app.route(route="chat-stream", methods=["POST", "OPTIONS"])
def chat_stream(req: func.HttpRequest) -> func.HttpResponse:
    """
    ストリーミング対応のCortex Agent APIエンドポイント
    """
    logging.info('Chat stream endpoint triggered')
    
    if req.method == "OPTIONS":
        return func.HttpResponse("", status_code=204, headers=CORS_HEADERS)

    started = time.time()

    try:
        # --- input ---
        try:
            body = req.get_json()
        except Exception:
            raw = req.get_body().decode("utf-8", errors="replace")
            body = json.loads(raw) if raw else {}

        text = body.get("text") or body.get("input") or body.get("message")
        if not text:
            return _json({"ok": False, "error": "text is required"}, 400)

        # --- env ---
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

        payload = {
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "tool_choice": {"type": "auto"},
        }

        # --- call Cortex Agent ---
        r = requests.post(url, headers=headers, json=payload, stream=True, timeout=900)
        if r.status_code >= 400:
            return _json(
                {
                    "ok": False,
                    "error": "snowflake_error",
                    "snowflake_status": r.status_code,
                    "body": r.text,
                },
                502,
            )

        progress = ["開始：Agentに問い合わせました"]
        tool_logs_short = []
        tool_details = []

        delta_all = []

        buf = ""
        current_event = None
        events_count = 0

        final_answer = None
        got_final = False

        def add_progress(msg: str):
            if msg:
                progress.append(msg)

        def flush(force=False):
            nonlocal buf
            if not buf:
                return

            if force:
                rest = buf.strip()
                if rest:
                    for i in range(0, len(rest), 400):
                        add_progress(rest[i : i + 400])
                buf = ""
                return

            pos = _find_flush_pos(buf)
            if pos > 0:
                chunk = buf[:pos].strip()
                buf = buf[pos:]
                if chunk:
                    for line in chunk.splitlines():
                        line = line.strip()
                        if line:
                            add_progress(line)

        for raw in r.iter_lines(decode_unicode=False):
            if raw is None:
                continue
            try:
                line = raw.decode("utf-8")
            except Exception:
                line = raw.decode("utf-8", errors="replace")

            line = line.rstrip("\r")

            if line == "":
                current_event = None
                continue

            if line.startswith("event:"):
                current_event = line[len("event:") :].strip()
                continue

            if not line.startswith("data:"):
                continue

            data_str = line[len("data:") :].strip()
            if data_str == "[DONE]":
                break

            try:
                obj = json.loads(data_str)
            except Exception:
                continue

            events_count += 1

            # --- delta ---
            if current_event == "response.text.delta":
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t:
                    delta_all.append(t)
                    buf += t
                    flush(False)
                continue

            # --- final answer ---
            if current_event == "response.text":
                if got_final:
                    continue
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t:
                    final_answer = t
                    got_final = True
                    flush(True)
                    add_progress("完了：最終回答を受け取りました")
                continue

            # --- tool result ---
            if current_event == "response.tool_result":
                detail = _extract_tool_detail(obj)
                tool_logs_short.append(f'{detail["tool_name"]} ({detail["status"]})')
                tool_details.append(detail)
                continue

        # response.text が来ない場合は delta を最終回答にする
        if not final_answer:
            final_answer = "".join(delta_all).strip()
            if final_answer:
                add_progress("完了：最終回答を受け取りました")

        elapsed = round(time.time() - started, 3)

        return _json(
            {
                "ok": True,
                "elapsed_sec": elapsed,
                "answer": _fix_mojibake(final_answer or ""),
                "progress": progress,
                "tool_logs": tool_logs_short,
                "tool_details": tool_details,
                "events_count": events_count,
            }
        )

    except Exception as e:
        logging.error(f"ストリーミングエラー: {str(e)}")
        return _json({"ok": False, "error": "internal_error", "message": str(e)}, 500)
