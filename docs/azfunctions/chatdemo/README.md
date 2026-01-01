# Azure Functions Documentation

このディレクトリにはAzure Functionsの設計書を配置します。

## 📚 ドキュメント一覧

- **[命名規則](NAMING_CONVENTIONS_GUIDE.md)** - Python/Azure Functions固有の命名規則
- **[メンテナンスガイド](MAINTENANCE_GUIDE.md)** - 開発・テスト・デプロイ手順
- **[API仕様書](API_SPECIFICATION.md)** - エンドポイント一覧と使用方法

## 🎯 主要機能

### 1. チャット機能
- Snowflake Cortex Agentとの対話
- ストリーミング応答（SSE）対応
- メッセージ履歴管理

### 2. DB設計レビュー（NEW）
- Snowflake AgentによるDB設計の自動レビュー
- Markdown形式でレビュー結果を出力
- 命名規則・データ型・PK/FK整合性チェック

## 📋 エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/chat` | チャットメッセージ処理 |
| POST | `/api/chat/stream` | ストリーミングチャット（SSE） |
| POST | `/api/review/schema` | DB設計レビュー実行 |

## 🔗 関連リンク

- 実際のコード: [app/azfunctions/chatdemo/](../../../app/azfunctions/chatdemo/)
- テストコード: [tests/azfunctions/chatdemo/](../../../tests/azfunctions/chatdemo/)
- Git運用規則: [docs/git/chatdemo/GIT_WORKFLOW.md](../../git/chatdemo/GIT_WORKFLOW.md)
