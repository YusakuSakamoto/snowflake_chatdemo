# Obsidian設計書

このフォルダはObsidianで管理される設計書を格納します。

## AWS S3同期設定

AWS S3と同期してバックアップと共有を実現します。

### S3バケット設定例

```bash
# AWS CLIでS3バケットを作成
aws s3 mb s3://snowflake-chatdemo-docs

# 同期コマンド（手動）
aws s3 sync ./docs s3://snowflake-chatdemo-docs --exclude ".obsidian/*"

# 定期同期設定（cron等）
# 0 */4 * * * aws s3 sync /path/to/docs s3://snowflake-chatdemo-docs
```

## ドキュメント構造

- `architecture/` - システムアーキテクチャ図
- `api/` - API仕様書
- `database/` - データベーススキーマ
- `deployment/` - デプロイメント手順
- `requirements/` - 要件定義
