# Azure Functions Tests

Azure Functionsのテストコードを配置します。

## 📁 構造

```
tests/azfunctions/chatdemo/
├── test_snowflake_auth.py      # 認証テスト
├── test_snowflake_cortex.py    # Cortex呼び出しテスト
├── test_stream_endpoint.py     # ストリーミングエンドポイントテスト
└── fixtures/                   # テストデータ
```

## 🧪 テスト実行

```bash
cd /home/yolo/pg/snowflake_chatdemo
pytest tests/azfunctions/chatdemo/ -v
```

## 📋 テストカバレッジ

- [ ] Snowflake認証
- [ ] Cortex Agent呼び出し
- [ ] エラーハンドリング
- [ ] ストリーミングレスポンス
