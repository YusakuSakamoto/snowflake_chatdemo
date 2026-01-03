import uuid

import azure.functions as func
import logging
import os
import json
import time
import requests
from datetime import datetime
from s3_upload import upload_file_to_s3

# モックデータ（開発用 - USE_MOCK=Trueの場合のみ使用）
mock_messages = []
USE_MOCK = os.getenv('USE_MOCK', 'False').lower() == 'true'

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="chat", methods=["POST", "OPTIONS"])
def chat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    チャットメッセージを処理し、Cortex Agent REST API経由でのみ応答するエンドポイント
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
            recent_messages = mock_messages[-10:][::-1]
            ai_response = f"これはモック応答です: {message}"
        else:
            # Cortex Agent REST API経由でのみ応答
            base_url = os.getenv("SNOWFLAKE_ACCOUNT_URL", "").rstrip("/")
            token = os.getenv("SNOWFLAKE_BEARER_TOKEN", "")
            database = os.getenv("SNOWFLAKE_DATABASE", "")
            schema = os.getenv("SNOWFLAKE_SCHEMA", "")
            agent = os.getenv("SNOWFLAKE_AGENT_NAME", "")

            url = f"{base_url}/api/v2/databases/{database}/schemas/{schema}/agents/{agent}:run"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            payload = {
                "messages": [{"role": "user", "content": [{"type": "text", "text": message}]}],
                "tool_choice": {"type": "auto"},
            }
            ai_response = "応答を取得できませんでした"
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=60)
                if r.status_code < 400:
                    data = r.json()
                    # Snowflake Cortex Agentの応答仕様に応じて取得
                    if "choices" in data and data["choices"]:
                        c = data["choices"][0].get("message", {}).get("content")
                        if isinstance(c, str):
                            ai_response = c
                        elif isinstance(c, list):
                            # {"type":"text","text":"..."} の配列を想定
                            ai_response = "".join(
                                [x.get("text", "") for x in c if isinstance(x, dict)]
                            ) or ai_response
                    elif "data" in data and data["data"]:
                        ai_response = data["data"][0][0]
            except Exception as e:
                logging.error(f"Cortex Agent REST API error: {e}")

            # S3アップロード（本番時のみ）
            try:
                s3_bucket = os.getenv("CHAT_S3_BUCKET")
                if s3_bucket:
                    from tempfile import NamedTemporaryFile
                    now = datetime.utcnow()
                    year = now.strftime('%Y')
                    month = now.strftime('%m')
                    day = now.strftime('%d')
                    hour = now.strftime('%H')
                    conversation_id = req_body.get('conversation_id') or str(uuid.uuid4())
                    agent_name = os.getenv("SNOWFLAKE_AGENT_NAME", "")
                    # NDJSON: user, assistant 2行
                    ndjson_lines = []
                    ndjson_lines.append(json.dumps({
                        "conversation_id": conversation_id,
                        "session_id": req_body.get('session_id'),
                        "user_id": user_id,
                        "agent_name": agent_name,
                        "message_role": "user",
                        "message_content": {"text": message},
                        "timestamp": now.isoformat(),
                        "metadata": None
                    }, ensure_ascii=False))
                    ndjson_lines.append(json.dumps({
                        "conversation_id": conversation_id,
                        "session_id": req_body.get('session_id'),
                        "user_id": user_id,
                        "agent_name": agent_name,
                        "message_role": "assistant",
                        "message_content": {"text": ai_response},
                        "timestamp": now.isoformat(),
                        "metadata": None
                    }, ensure_ascii=False))
                    s3_key = f"cortex_conversations/YEAR={year}/MONTH={month}/DAY={day}/HOUR={hour}/{uuid.uuid4()}.json"
                    with NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmpf:
                        tmpf.write("\n".join(ndjson_lines) + "\n")
                        tmpf.flush()
                        upload_file_to_s3(tmpf.name, s3_bucket, s3_key, content_type="application/json")
            except Exception as e:
                logging.error(f"S3 upload error: {e}")

            # 最近のメッセージは返さない（または空リスト）
            recent_messages = []

        response_data = {
            "status": "success",
            "message": "メッセージが保存されました",
            "recent_messages": recent_messages,
            "ai_response": ai_response
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
    チャットメッセージの取得（Snowflake DB直接アクセスは不可、モックのみ）
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
            # DBアクセス禁止のため空リスト返却
            messages = []

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


def _extract_tool_detail(obj: dict):
    """ツール実行結果から詳細を抽出"""
    if not isinstance(obj, dict):
        return {"tool_name": "tool", "status": "unknown", "input": None, "output": None, "raw": obj}

    tool_name = obj.get("name") or obj.get("tool_name") or "tool"
    status = obj.get("status") or "unknown"
    elapsed_ms = obj.get("elapsed_ms") or obj.get("elapsedMs")

    content_list = obj.get("content", [])
    if not isinstance(content_list, list):
        content_list = [content_list] if content_list else []

    tool_input = {}
    tool_output = {}

    for content_item in content_list:
        if not isinstance(content_item, dict):
            continue

        if "json" in content_item:
            cj = content_item.get("json", {})

            if "sql" in cj and isinstance(cj.get("sql"), str):
                tool_input["sql"] = cj.get("sql")

            if "text" in cj and isinstance(cj.get("text"), str):
                tool_input["note"] = cj.get("text")

            if "result" in cj:
                result_data = cj.get("result")
                if isinstance(result_data, str):
                    try:
                        tool_output["result"] = json.loads(result_data)
                    except Exception:
                        tool_output["result"] = result_data
                else:
                    tool_output["result"] = result_data

            if "result_set" in cj and cj.get("result_set") is not None:
                tool_output["data"] = cj.get("result_set")

            if "data" in cj and cj.get("data") is not None:
                tool_output["data"] = cj.get("data")

    return {
        "tool_name": str(tool_name),
        "status": status,
        "elapsed_ms": elapsed_ms,
        "input": tool_input if tool_input else None,
        "output": tool_output if tool_output else None,
        "raw": obj,
    }


def _strip_leading_blank_lines(s: str) -> str:
    """
    先頭の「空白のみの行」を削除（Markdownのインデント等は壊さないため行単位）
    """
    if not isinstance(s, str) or not s:
        return s
    lines = s.splitlines(True)  # 改行保持
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    return "".join(lines[i:])


@app.route(route="chat-stream", methods=["POST", "OPTIONS"])
def chat_stream(req: func.HttpRequest) -> func.HttpResponse:
    import uuid
    """
    ストリーミング対応のCortex Agent APIエンドポイント
    """
    logging.info('Chat stream endpoint triggered')

    if req.method == "OPTIONS":
        return func.HttpResponse("", status_code=204, headers=CORS_HEADERS)

    started = time.time()

    try:
        try:
            body = req.get_json()
        except Exception:
            raw = req.get_body().decode("utf-8", errors="replace")
            body = json.loads(raw) if raw else {}

        text = body.get("text") or body.get("input") or body.get("message")

        s3_bucket = os.getenv("CHAT_S3_BUCKET")
        conversation_id = body.get('conversation_id') or str(uuid.uuid4())
        session_id = body.get('session_id')
        user_id = body.get('user_id', 'anonymous')
        agent_name = os.getenv("SNOWFLAKE_AGENT_NAME", "")
        now = datetime.utcnow()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        hour = now.strftime('%H')

        if not text:
            return _json({"ok": False, "error": "text is required"}, 400)

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
                        add_progress(rest[i: i + 400])
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

            events_count += 1

            if current_event == "response.thinking.delta":
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t:
                    logging.info(f"[thinking.delta] {t[:500]}")
                continue

            if current_event == "response.thinking":
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t:
                    logging.info(f"[thinking] {t[:2000]}")
                continue

            if current_event == "response.text.delta":
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t:
                    delta_all.append(t)
                    buf += t
                    flush(False)
                continue

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

            if current_event == "response.tool_result":
                logging.info(f"🔧 Tool result event: {json.dumps(obj, ensure_ascii=False)[:500]}")
                detail = _extract_tool_detail(obj)
                logging.info(f"✅ Extracted detail: {json.dumps(detail, ensure_ascii=False)[:500]}")
                tool_logs_short.append(f'{detail["tool_name"]} ({detail["status"]})')
                tool_details.append(detail)
                add_progress(f"🔧 ツール: **{detail['tool_name']}** ({detail['status']})")
                continue

            if current_event in ["response.tool.call", "response.tool.start", "response.tool.end"]:
                tool_name = obj.get("name") or obj.get("tool_name") or "unknown"
                if current_event == "response.tool.call":
                    add_progress(f"📞 ツール呼び出し: **{tool_name}**")
                elif current_event == "response.tool.start":
                    add_progress(f"▶️ ツール実行開始: **{tool_name}**")
                elif current_event == "response.tool.end":
                    add_progress(f"✅ ツール実行完了: **{tool_name}**")
                continue

        if not final_answer:
            final_answer = "".join(delta_all).strip()
            if final_answer:
                add_progress("完了：最終回答を受け取りました")

        elapsed = round(time.time() - started, 3)

        try:
            if s3_bucket:
                import tempfile
                ndjson_lines = []
                ndjson_lines.append(json.dumps({
                    "conversation_id": conversation_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "message_role": "user",
                    "message_content": {"text": text},
                    "timestamp": now.isoformat(),
                    "metadata": None
                }, ensure_ascii=False))
                ndjson_lines.append(json.dumps({
                    "conversation_id": conversation_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "message_role": "assistant",
                    "message_content": {"text": final_answer},
                    "timestamp": now.isoformat(),
                    "metadata": None
                }, ensure_ascii=False))
                s3_key = f"cortex_conversations/YEAR={year}/MONTH={month}/DAY={day}/HOUR={hour}/{uuid.uuid4()}.json"
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmpf:
                    tmpf.write("\n".join(ndjson_lines) + "\n")
                    tmpf.flush()
                    upload_file_to_s3(tmpf.name, s3_bucket, s3_key, content_type="application/json")
        except Exception as e:
            logging.error(f"S3 upload error: {e}")

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

@app.route(route="review/schema", methods=["POST", "OPTIONS"])
def review_schema_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    import os
    import json
    import logging
    import requests
    from datetime import datetime
    from pathlib import Path
    import azure.functions as func

    # ----------------------------
    # 変数の初期化
    # ----------------------------
    success = False
    markdown = ""        # ログ用途：stream全文
    final_text = ""      # 最終出力：response.text（なければdelta結合）
    message = "レビュー完了"

    target_schema = None
    target_table = None     # 互換用
    target_object = None    # ★追加：オブジェクト単位レビュー用
    max_tables = None

    logging.info("DB Review endpoint triggered")

    # ----------------------------
    # OPTIONS（CORS）
    # ----------------------------
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    try:
        # ----------------------------
        # リクエストJSON取得
        # ----------------------------
        req_body = req.get_json()
        target_schema = req_body.get("target_schema")
        target_table = req_body.get("target_table")          # 既存互換
        target_object = req_body.get("target_object")        # ★新規
        max_tables = req_body.get("max_tables")

        # 互換：target_object 未指定なら target_table を採用（既存クライアント救済）
        if not target_object and target_table:
            target_object = target_table

        if not target_schema:
            return func.HttpResponse(
                json.dumps(
                    {"success": False, "error": "target_schema パラメータが必要です"},
                    ensure_ascii=False,
                ),
                mimetype="application/json",
                status_code=400,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        # ----------------------------
        # Snowflake Cortex Agent 設定
        # ----------------------------
        base_url = os.getenv("SNOWFLAKE_ACCOUNT_URL", "").rstrip("/")
        token = os.getenv("SNOWFLAKE_BEARER_TOKEN", "")
        database = os.getenv("SNOWFLAKE_DATABASE", "")
        schema = os.getenv("SNOWFLAKE_SCHEMA_REVIEW", os.getenv("SNOWFLAKE_SCHEMA", ""))
        agent = os.getenv(
            "SNOWFLAKE_AGENT_NAME_REVIEW",
            os.getenv("SNOWFLAKE_AGENT_NAME", ""),
        )

        url = f"{base_url}/api/v2/databases/{database}/schemas/{schema}/agents/{agent}:run"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        # ----------------------------
        # PARAMS_JSON（文字列前提 / null禁止）
        # ----------------------------
        params = {
            "TARGET_SCHEMA": str(target_schema),
            "MAX_TABLES": str(max_tables) if max_tables else "2000",
        }

        # ★重要：TARGET_OBJECT 指定時は tool 側が TARGET_TABLE を要求するため、同じ値を入れる
        # instructions: "TARGET_TABLE は TARGET_OBJECT と同義として扱い、TARGET_OBJECT の値をそのまま渡す"
        if target_object:
            params["TARGET_OBJECT"] = str(target_object)
            params["TARGET_TABLE"] = str(target_object)  # ★これが無いと Agent が tool を呼べない/迷う

        # ----------------------------
        # prompt（誤解させない・短め・PARAMS_JSON唯一入力を強調）
        # ----------------------------
        if target_object:
            prompt = (
                "以下の PARAMS_JSON を唯一の入力として、"
                "OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT の定義に厳密に従い、静的設計レビューを実行してください。\n\n"
                f"PARAMS_JSON:\n{json.dumps(params, ensure_ascii=False)}\n\n"
                "注意:\n"
                "- 今回は TARGET_OBJECT 指定のためオブジェクト単位レビュー（スキーマ全体レビューは禁止）\n"
                "- オブジェクト単位レビュー手順に従い、最初は list_table_related_doc_paths を INCLUDE_COLUMNS=\"false\" で実行\n"
                "- 推測禁止、Vault 根拠のみ使用\n"
            )
        else:
            prompt = (
                "以下の PARAMS_JSON を唯一の入力として、"
                "OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT の定義に厳密に従い、静的設計レビューを実行してください。\n\n"
                f"PARAMS_JSON:\n{json.dumps(params, ensure_ascii=False)}\n\n"
                "注意:\n"
                "- TARGET_OBJECT 未指定のためスキーマ単位レビュー\n"
                "- 推測禁止、Vault 根拠のみ使用\n"
            )

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            "tool_choice": {"type": "auto"},
        }

        # ----------------------------
        # Cortex Agent 呼び出し（SSE）
        # ----------------------------
        r = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)

        if r.status_code >= 400:
            return func.HttpResponse(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Cortex Agent API error: {r.status_code}",
                        "body": r.text,
                    },
                    ensure_ascii=False,
                ),
                mimetype="application/json",
                status_code=500,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        content_chunks = []
        delta_chunks = []
        current_event = None

        for raw in r.iter_lines(decode_unicode=False):
            if raw is None:
                continue

            try:
                line = raw.decode("utf-8")
            except Exception:
                line = raw.decode("utf-8", errors="ignore")

            # 既存仕様：streamの行ログは残す
            logging.info(f"[review_schema_endpoint][stream] {line[:500]}")
            content_chunks.append(line)

            line = line.rstrip("\r")

            if line == "":
                current_event = None
                continue

            if line.startswith("event:"):
                current_event = line[len("event:"):].strip()
                logging.info(f"[review_schema_endpoint][event] {current_event}")
                continue

            if not line.startswith("data:"):
                continue

            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                logging.info("[review_schema_endpoint][done] [DONE]")
                break

            # ここから data: JSON のログ（必要分だけ）
            # パースできない場合はそのままログ
            try:
                obj = json.loads(data_str)
            except Exception:
                logging.info(f"[review_schema_endpoint][data] {data_str[:500]}")
                continue

            # --- thinking delta ---
            if current_event == "response.thinking.delta":
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t:
                    logging.info(f"[review_schema_endpoint][thinking.delta] {t[:500]}")
                continue

            # --- thinking final ---
            if current_event == "response.thinking":
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t:
                    logging.info(f"[review_schema_endpoint][thinking] {t[:2000]}")
                continue

            # --- response.text.delta（ログ＋蓄積）---
            if current_event == "response.text.delta":
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t:
                    logging.info(f"[review_schema_endpoint][text.delta] {t[:500]}")
                    delta_chunks.append(t)
                continue

            # --- response.text（ログ＋最終採用）---
            if current_event == "response.text":
                t = obj.get("text") if isinstance(obj, dict) else None
                if isinstance(t, str) and t.strip():
                    logging.info(f"[review_schema_endpoint][text] {t[:500]}")
                    final_text = t
                continue

            # --- tool steps（tool_call / tool_start / tool_end 相当）---
            if current_event in ("response.tool.call", "response.tool.start", "response.tool.end"):
                tool_name = None
                if isinstance(obj, dict):
                    tool_name = obj.get("name") or obj.get("tool_name") or "unknown"
                logging.info(f"[review_schema_endpoint][tool_step] {current_event} tool={tool_name}")
                continue

            # --- tool result ---
            if current_event == "response.tool_result":
                # 全文は重いので先頭だけ（既存方針に合わせる）
                logging.info(
                    f"[review_schema_endpoint][tool_result] {json.dumps(obj, ensure_ascii=False)[:500]}"
                )
                continue

            # その他イベント（念のためログ）
            logging.info(
                f"[review_schema_endpoint][event_data] event={current_event} data={json.dumps(obj, ensure_ascii=False)[:300]}"
            )

        # response.text が来ない場合は delta を最終回答にする
        if not final_text.strip() and delta_chunks:
            final_text = "".join(delta_chunks).strip()

        markdown = "\n".join(content_chunks)
        success = bool(final_text.strip())

        if not success:
            message = "最終回答（response.text / response.text.delta）を取得できませんでした"

        # ----------------------------
        # ファイル保存（最終回答のみ）
        # 先頭空白行があれば削除
        # ----------------------------
        if success:
            # 既存 util を使う想定（この関数はファイル上のどこかに既にある前提）
            final_text = _strip_leading_blank_lines(final_text)

            output_dir = (
                Path(__file__).parent.parent.parent.parent
                / "docs" / "snowflake" / "chatdemo" / "reviews" / "schemas"
            )
            output_dir.mkdir(parents=True, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            schema_name = str(target_schema).replace("/", "_").replace(".", "_")

            obj_part = ""
            if target_object:
                obj_part = "_" + str(target_object).replace("/", "_").replace(".", "_")

            output_file = output_dir / f"{schema_name}{obj_part}_{ts}.md"
            output_file.write_text(final_text, encoding="utf-8")

            logging.info(f"Review saved to: {output_file}")

        response_data = {
            "success": success,
            "message": message,
            "final_text": final_text,
            "metadata": {
                "target_schema": target_schema,
                "target_object": target_object,
                "max_tables": max_tables,
                "review_date": datetime.now().strftime("%Y-%m-%d"),
            },
        }

        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            mimetype="application/json",
            status_code=200 if success else 500,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    except Exception as e:
        logging.error(f"DB review error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"success": False, "error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )
