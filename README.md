# Snowflake Chat Demo

Obsidian × Snowflake を活用したチャットアプリケーション

コンセプト:  
DB設計・名称解決・売上データ基盤を、Obsidian Vault（Markdown）を設計正本として管理し、Snowflake Cortex Agentで対話的に分析できる基盤です。

## 🎯 プロジェクトの特徴

- 設計正本: Obsidian Vault（Markdown）が唯一の設計正本
- 自動DDL生成: ObsidianのDataviewから Snowflake DDLを自動生成
- Cortex Agent統合: 設計書を参照しながらAIエージェントが対話
- 名称解決: 業務用語・略称を手動辞書で管理し、決定論的に解決
- 再現性: 推測を排除し、説明可能・監査可能な構成

## 📁 プロジェクト構造

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
│   └── snowflake/chatdemo/                # Snowflake設計書（Obsidian Vault）
│       ├── .obsidian/                     # Obsidian設定・プラグイン
│       ├── master/                        # 定義の正本（DDL生成対象）
│       │   ├── schemas/                   # スキーマ定義
│       │   ├── tables/                    # テーブル定義
│       │   ├── columns/                   # カラム定義
│       │   └── views/                     # ビュー定義
│       ├── design/                        # 設計意図・判断理由
│       ├── reviews/                       # レビュー結果・プロファイル
│       ├── generated/                     # 自動生成DDL
│       ├── templates/                     # テンプレート
│       ├── views/                         # Dataviewビュー（自動生成）
│       ├── README.md                      # Vault全体説明
│       └── README_DB_DESIGN.md            # DB設計ガイド
├── tests/                                  # テストコード & スクリプト
│   ├── azfunctions/chatdemo/              # バックエンドテスト
│   ├── azswa/chatdemo/                    # フロントエンドテスト
│   ├── snowflake/chatdemo/                # Snowflakeテスト
│   └── scripts/                           # ユーティリティスクリプト
├── .venv/                                  # Python仮想環境
└── README.md                               # このファイル
```

## 🤖 GitHub Copilot設定

本プロジェクトには、GitHub Copilotが自動的に参照する設定ファイルが含まれています：

- `.github/copilot-instructions.md` - Copilotへの指示とプロジェクト規則
- `.vscode/settings.json` - VS Code設定（Copilot統合含む）

### 重要な規則
Copilotは以下のドキュメントを常に参照します：
- 命名規則: `docs/snowflake/chatdemo/NAMING_CONVENTIONS_GUIDE.md`
- メンテナンスガイド: `docs/snowflake/chatdemo/MAINTENANCE_GUIDE.md`
- Git運用規則: `docs/git/chatdemo/GIT_WORKFLOW.md`

---

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

モードの切り替え:
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

Windows側:
```
C:\Users\Owner\Documents\snowflake-db
```

WSL側（シンボリックリンク）:
```
docs/snowflake/chatdemo/
```

1. Obsidianアプリを起動
2. "Open folder as vault"を選択
3. Windows側のパス `C:\Users\Owner\Documents\snowflake-db` を開く

### 主要ドキュメント

- [Snowflake設計書](docs/snowflake/chatdemo/README.md) - 全体思想・スキーマ境界
- [DB設計ガイド](docs/snowflake/chatdemo/README_DB_DESIGN.md) - Obsidian Vault運用ガイド
- [スキーマ一覧](docs/snowflake/chatdemo/master/schemas/) - DB_DESIGN, APP_PRODUCTION等
- [テーブル定義](docs/snowflake/chatdemo/master/tables/) - master/配下に正本
- [設計意図](docs/snowflake/chatdemo/design/) - 人が読む設計判断
- [DDL生成結果](docs/snowflake/chatdemo/generated/ddl/) - 自動生成されたSQL

## 🏗️ Snowflake スキーマ構成

本プロジェクトでは、用途ごとに明確なスキーマ境界を設ける：

| スキーマ | 役割 |
|---------|------|
| DB_DESIGN | 設計・設計レビュー（Obsidian Vault連携） |
| IMPORT | データ取込・検査（Raw/Landing） |
| NAME_RESOLUTION | 名称解決の手動辞書 |
| APP_DEVELOPMENT | アプリケーション開発環境 |
| APP_PRODUCTION | アプリケーション本番環境 |

### 設計思想

- 設計正本: Obsidian Vault（Markdown）が唯一の正本
- DDL生成: Dataviewから自動生成（`generated/ddl/`）
- 名称解決: 推測を排除し、手動辞書（NAME_RESOLUTION）で決定論的に解決
- Agent制御: LLMに「考えさせない」、決定論を実行させる
- 再現性: 説明可能性・監査耐性を重視

### DEV → PROD反映ルール

- APP_DEVELOPMENTとAPP_PRODUCTIONは 同一仕様
- 差異は「配置先スキーマの差」のみ
- DEVで検証完了後、同一DDLをPRODに適用

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

## 📊 データフロー

```
楽々販売CSV → IMPORT（Raw） → APP_DEVELOPMENT（検証） → APP_PRODUCTION（本番）
                      ↓
           NAME_RESOLUTION（名称解決辞書）
                      ↓
              Cortex Agent（対話）
```

### ログアーキテクチャ（将来実装予定）

全てのログをSnowflakeに集約し、S3外部ステージとして保存：

```
アプリ → S3バケット → Snowflake外部ステージ → 外部テーブル
         (パーティション)     (year/month/day)
```

ログの種類:
1. Cortex対話ログ - AI Agentとの会話履歴、SQL実行履歴
2. Azure Functionsログ - バックエンド実行ログ
3. SWAログ - フロントエンドアクセスログ
4. Snowflakeメトリクス - クエリパフォーマンス、コスト分析

## 🛠️ 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Next.js, TypeScript, React |
| バックエンド | Azure Functions (Python 3.11) |
| データベース | Snowflake |
| AI | Snowflake Cortex Agent |
| 設計管理 | Obsidian Vault (Markdown + Dataview) |
| DDL自動生成 | DataviewJS → SQL |
| 名称解決 | 手動辞書（NAME_RESOLUTION） + UDF |
| ホスティング | Azure Static Web Apps |
| ログ基盤（予定） | AWS S3 (外部ステージ) |

## 🎨 設計の特徴

### 1. Obsidian Vaultを設計正本に
- schema/table/column を 1定義1ファイルで管理
- YAMLフロントマター + Markdownで構造化
- Dataviewで自動的にDDL生成・レビュー資料作成

### 2. 決定論的な名称解決
- 推測・LLM補完を排除
- 手動辞書（NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL）を正とする
- resolve_entity_alias ツールで確実に解決

### 3. Agent制御の明確化
- Agent は「考えない」、決定論を実行する
- 曖昧な場合は必ずユーザーに確認（disambiguate）
- 推測で補完しない

### 4. スキーマ境界の明確化
- IMPORT（取込）/ NAME_RESOLUTION（辞書）/ APP_*（アプリ）を分離
- 責務を明確にし、依存関係を制御

## 🔄 開発フロー

1. 設計 → Obsidianで設計書作成（master/配下）
2. DDL生成 → DataviewJSで自動生成（generated/ddl/）
3. 適用 → SnowflakeにDDLを実行
4. 実装 → VSCode + GitHub Copilot
5. テスト → pytest / Jest
6. レビュー → Obsidian上でレビュー記録
7. デプロイ → GitHub Actions

## 🚀 デプロイ

GitHub Actions により自動デプロイが設定されています。

- バックエンド: Azure Functions にデプロイ
- フロントエンド: Azure Static Web Apps にデプロイ

## 📝 開発環境

- OS: Ubuntu (on WSL)
- バージョン管理: GitHub
- 設計書: Obsidian → AWS S3同期 → GitHub COMMIT
- エディタ: VSCode + GitHub Copilot (Code Agent)
- DB: Snowflake (AWS account)
