# Snowflake Chat Demo

チャットアプリケーション with Snowflake DB

## 📁 プロジェクト構造（汎用化版）

```
snowflake_chatdemo/
├── app/                                    # アプリケーションコード
│   ├── azfunctions/chatdemo/              # Azure Functions (Python 3.11)
│   │   ├── function_app.py
│   │   ├── host.json
│   │   ├── requirements.txt
│   │   └── *.py                           # 各種モジュール
│   └── azswa/chatdemo/                    # Azure SWA (Next.js)
│       ├── pages/
│       ├── styles/
│       ├── package.json
│       └── next.config.js
├── docs/                                   # ドキュメント（Obsidian Vault）
│   ├── azfunctions/chatdemo/              # Azure Functions設計書
│   ├── azswa/chatdemo/                    # SWA設計書
│   └── snowflake/chatdemo/                # Snowflake設計書
│       ├── .obsidian/                     # Obsidian設定
│       ├── tables/                        # テーブル定義
│       ├── schemas/                       # スキーマ設計
│       ├── queries/                       # クエリ集
│       ├── reviews/                       # 設計レビュー
│       ├── migrations/                    # マイグレーション
│       └── README.md
├── tests/                                  # テストコード
│   ├── azfunctions/chatdemo/              # バックエンドテスト
│   ├── azswa/chatdemo/                    # フロントエンドテスト
│   └── snowflake/chatdemo/                # Snowflakeテスト
├── scripts/                                # ユーティリティスクリプト
├── .venv/                                  # Python仮想環境
└── README.md                               # このファイル
```

## 🚀 セットアップ

### 1. Python仮想環境

```bash
# プロジェクトルートで実行
python -m venv .venv
source .venv/bin/activate  # WSL/Linux
```

### 2. バックエンド（Azure Functions）

```bash
cd app/azfunctions/chatdemo
pip install -r requirements.txt
```

### 3. フロントエンド（Next.js）

```bash
cd app/azswa/chatdemo
npm install
```

## ⚙️ 環境変数

### バックエンド（app/azfunctions/chatdemo/local.settings.json）
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "USE_MOCK": "false",
    "SNOWFLAKE_ACCOUNT": "your-account",
    "SNOWFLAKE_USER": "your-user",
    "SNOWFLAKE_PASSWORD": "your-password",
    "SNOWFLAKE_WAREHOUSE": "your-warehouse",
    "SNOWFLAKE_DATABASE": "your-database",
    "SNOWFLAKE_SCHEMA": "your-schema",
    "SNOWFLAKE_ROLE": "ACCOUNTADMIN"
  },
  "Host": {
    "CORS": "*",
    "CORSCredentials": false
  }
}
```

**モードの切り替え:**
- `USE_MOCK=true`: モックデータを使用（開発用）
- `USE_MOCK=false`: Snowflake Cortex Agentに接続

### フロントエンド（app/azswa/chatdemo/.env.local）
```
NEXT_PUBLIC_API_URL=http://localhost:7071/api
```

## 🏃 開発サーバー起動

### バックエンド

```bash
cd app/azfunctions/chatdemo
func start --port 7071
```

### フロントエンド

```bash
cd app/azswa/chatdemo
npm run dev
```

アクセス: http://localhost:3000

## 📚 ドキュメント

### Obsidian Vaultで開く

1. Obsidianアプリを起動
2. "Open folder as vault"を選択
3. `docs/snowflake/chatdemo/`を選択

### 主要ドキュメント

- [Snowflake設計書](docs/snowflake/chatdemo/README.md)
- [ログアーキテクチャ](docs/snowflake/chatdemo/reviews/log_architecture.md)
- [Cortex対話ログテーブル](docs/snowflake/chatdemo/tables/cortex_conversation_logs.md)
- [開発ノート](docs/snowflake/chatdemo/development-notes.md)

## 🧪 テスト

### バックエンドテスト

```bash
pytest tests/azfunctions/chatdemo/ -v
```

### フロントエンドテスト

```bash
cd app/azswa/chatdemo
npm test
```

### Snowflakeテスト

```bash
pytest tests/snowflake/chatdemo/ -v
```

## 📊 ログアーキテクチャ

全てのログをSnowflakeに集約し、S3外部ステージとして保存：

```
アプリ → S3バケット → Snowflake外部ステージ → 外部テーブル
         (パーティション)     (year/month/day)
```

### ログの種類

1. **Cortex対話ログ** - AI Agentとの会話履歴、SQL実行履歴
2. **Azure Functionsログ** - バックエンド実行ログ、エラーログ
3. **SWAログ** - フロントエンドアクセスログ
4. **Snowflakeメトリクス** - クエリパフォーマンス、コスト分析

詳細: [docs/snowflake/chatdemo/reviews/log_architecture.md](docs/snowflake/chatdemo/reviews/log_architecture.md)

## 🛠️ 技術スタック

| レイヤー | 技術 |
|---------|------|
| **フロントエンド** | Next.js, TypeScript, React |
| **バックエンド** | Azure Functions (Python 3.11) |
| **データベース** | Snowflake |
| **AI** | Snowflake Cortex Agent |
| **ホスティング** | Azure Static Web Apps |
| **ログストレージ** | AWS S3 (外部ステージ) |
| **設計書** | Obsidian Vault |

## 🔄 開発フロー

1. **設計** → Obsidianで設計書作成
2. **実装** → VSCode + GitHub Copilot
3. **テスト** → pytest / Jest
4. **デプロイ** → GitHub Actions
5. **監視** → Snowflakeログ分析

## 🚀 デプロイ

GitHub Actions により自動デプロイが設定されています。

- **バックエンド**: Azure Functions にデプロイ
- **フロントエンド**: Azure Static Web Apps にデプロイ

## 📝 開発環境

- **OS**: Ubuntu (on WSL)
- **バージョン管理**: GitHub
- **設計書**: Obsidian → AWS S3同期 → GitHub COMMIT
- **エディタ**: VSCode + GitHub Copilot (Code Agent)
- **DB**: Snowflake (AWS account)
