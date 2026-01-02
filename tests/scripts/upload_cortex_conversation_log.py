#!/usr/bin/env python3
"""
CORTEX_CONVERSATIONS外部テーブル設計に準拠した会話ログJSON Linesファイル生成・S3アップロードスクリプト
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "app/azfunctions/chatdemo"))
from s3_upload import upload_file_to_s3

# --- 設定 ---
BUCKET = "135365622922-snowflake-chatdemo-vault-prod"
S3_BASE = "cortex_conversations"

# --- サンプルデータ（実運用ではAPIから受信） ---
conversation_id = str(uuid.uuid4())
session_id = str(uuid.uuid4())
user_id = "user123"
agent_name = "SNOWFLAKE_DEMO_AGENT"
message_role = "user"
message_content = {
    "text": "こんにちは",
    "tokens": 3,
    "model": "mistral-large",
    "latency_ms": 1200,
    "error": None
}
timestamp = datetime.now(timezone.utc).replace(microsecond=0)
metadata = {
    "latency_ms": 1200,
    "request_id": str(uuid.uuid4())
}

# --- パーティション抽出 ---
year = timestamp.year
month = timestamp.month
day = timestamp.day
hour = timestamp.hour
# --- JSON Linesファイル生成 ---
log_obj = {
    "conversation_id": conversation_id,
    "session_id": session_id,
    "user_id": user_id,
    "agent_name": agent_name,
    "message_role": message_role,
    "message_content": message_content,
    "timestamp": timestamp.isoformat(),
    "metadata": metadata,
    "year": year,
    "month": month,
    "day": day,
    "hour": hour
}

log_dir = Path("tmp/cortex_conversations")
log_dir.mkdir(parents=True, exist_ok=True)
file_name = f"{conversation_id}_{timestamp.strftime('%Y%m%dT%H%M%S')}.jsonl"
file_path = log_dir / file_name
with open(file_path, "w", encoding="utf-8") as f:
    f.write(json.dumps(log_obj, ensure_ascii=False) + "\n")

# --- S3パス構築 ---
s3_key = f"{S3_BASE}/year={year}/month={month:02d}/day={day:02d}/hour={hour:02d}/{file_name}"

# --- S3アップロード ---
if upload_file_to_s3(str(file_path), BUCKET, s3_key, content_type="application/json"):
    print(f"アップロード完了: s3://{BUCKET}/{s3_key}")
else:
    print("アップロード失敗")
