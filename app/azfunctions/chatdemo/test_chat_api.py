"""
/chatエンドポイントに「こんにちは」をPOSTし、Cortex Agent応答と保存動作をテスト
"""
import requests
import json

def main():
    url = "http://localhost:7071/api/chat"
    payload = {
        "user_id": "test_user",
        "message": "こんにちは"
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, data=json.dumps(payload), headers=headers)
    print("Status:", resp.status_code)
    print("Response:", resp.text)

if __name__ == "__main__":
    main()
