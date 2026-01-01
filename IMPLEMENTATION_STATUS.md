```
Azure Functions - DB設計レビューエージェント 実装完了

## ✅ 実装内容

### 1. 新規モジュール
- **db_review_agent.py**: DB設計レビューAgent呼び出しラッパー
  - `DBReviewAgent.review_schema()`: スキーマレビュー実行
  - Markdown抽出機能
  
### 2. 新規エンドポイント
- **POST /api/review/schema**: DB設計レビュー実行
  - Request: `{"target_schema": "DB_DESIGN", "max_tables": 5}`
  - Response: Markdown形式のレビュー結果

### 3. 認証強化
- **snowflake_db.py**: Bearer Token + JWT認証対応
  - Personal Access Token (PAT) 認証
  - 秘密鍵によるJWT認証
  - snowflake_authとの統合

### 4. テストスクリプト
- **test_review_agent.py**: 直接呼び出し & HTTPエンドポイントテスト
  - `--local`: ローカルAzure Functions経由
  - `--schema`: 対象スキーマ指定
  - `--max-tables`: 最大テーブル数制限

### 5. ドキュメント
- **API_SPECIFICATION.md**: API仕様書（全エンドポイント）
- **README.md**: 更新（DB設計レビュー機能追加）

## ⚠️ 現在の状態

**Azure Functions起動完了**  
エンドポイント: http://localhost:7071/api/review/schema

**認証エラー発生中**  
Bearer Token (Personal Access Token)が期限切れのため、Snowflake接続に失敗しています。

## 🔧 次のステップ（認証修正）

### オプション1: 新しいBearer Tokenを発行
```sql
-- Snowflake WebUIで実行
USE ROLE ACCOUNTADMIN;
SELECT SYSTEM$GENERATE_USER_TOKEN('GBPS253YS_API_USER');
```

local.settings.jsonの`SNOWFLAKE_BEARER_TOKEN`を更新

### オプション2: パスワード認証に切り替え
```json
{
  "SNOWFLAKE_USER": "your-user",
  "SNOWFLAKE_PASSWORD": "your-password",
  "SNOWFLAKE_AUTH_METHOD": "password"
}
```

snowflake_db.pyにパスワード認証パスを追加

### オプション3: 秘密鍵認証に切り替え
```json
{
  "SNOWFLAKE_AUTH_METHOD": "private_key",
  "SNOWFLAKE_PRIVATE_KEY_PATH": "/path/to/rsa_key.p8",
  "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE": "your-passphrase"
}
```

## 📦 コミット内容

```bash
git add app/azfunctions/chatdemo/db_review_agent.py
git add app/azfunctions/chatdemo/function_app.py
git add app/azfunctions/chatdemo/snowflake_db.py
git add tests/azfunctions/chatdemo/test_review_agent.py
git add docs/azfunctions/chatdemo/API_SPECIFICATION.md
git commit -m "fix: Snowflake認証強化とログ追加（Bearer Token + JWT対応）"
```

## 🎯 使用方法（認証修正後）

```bash
# Azure Functions起動
cd app/azfunctions/chatdemo
func start --port 7071

# 別ターミナルでテスト実行
cd tests/azfunctions/chatdemo
python test_review_agent.py --local --schema DB_DESIGN --max-tables 5
```

レビュー結果は `tests/output/review_DB_DESIGN_*.md` に保存されます。
```
