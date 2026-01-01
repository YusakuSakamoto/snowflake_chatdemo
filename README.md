# Snowflake Chat Demo

チャットアプリケーション with Snowflake DB

## 開発環境

- **OS**: Ubuntu (on WSL)
- **バージョン管理**: GitHub
- **設計書**: Obsidian → AWS S3同期 → GitHub COMMIT
- **エディタ**: VSCode + GitHub Copilot (Code Agent)
- **DB**: Snowflake (AWS account)
- **バックエンド**: Azure Functions (Python 3.11)
- **フロントエンド**: Azure SWA (Next.js)

## プロジェクト構造

```
snowflake_chatdemo/
├── docs/              # Obsidian設計書（S3同期用）
├── backend/           # Azure Functions (Python 3.11)
├── frontend/          # Azure SWA (Next.js)
├── .github/           # GitHub Actions CI/CD
├── infrastructure/    # インフラ設定
└── README.md
```

## セットアップ

### バックエンド（Azure Functions）

```bash
cd backend
python -m venv venv
source venv/bin/activate  # WSL/Linux
pip install -r requirements.txt
```

### フロントエンド（Next.js）

```bash
cd frontend
npm install
npm run dev
```

## 環境変数

### バックエンド（backend/local.settings.json）
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SNOWFLAKE_ACCOUNT": "your-account",
    "SNOWFLAKE_USER": "your-user",
    "SNOWFLAKE_PASSWORD": "your-password",
    "SNOWFLAKE_WAREHOUSE": "your-warehouse",
    "SNOWFLAKE_DATABASE": "your-database",
    "SNOWFLAKE_SCHEMA": "your-schema"
  }
}
```

### フロントエンド（frontend/.env.local）
```
NEXT_PUBLIC_API_URL=http://localhost:7071/api
```

## デプロイ

GitHub Actions により自動デプロイが設定されています。

- **バックエンド**: Azure Functions にデプロイ
- **フロントエンド**: Azure Static Web Apps にデプロイ

## ドキュメント

設計書は `docs/` フォルダに Obsidian 形式で管理され、AWS S3 と同期されます。
