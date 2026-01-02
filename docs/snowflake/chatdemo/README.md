
# Obsidian × Snowflake

このリポジトリ（Obsidian Vault）は、Snowflake上のDB設計・名称解決・アプリケーション基盤の「唯一の設計正本」です。

---

## 重要な設計思想・運用ルール

- 設計・運用の全判断は Obsidian Vault 上のMarkdown（.md）を唯一の根拠とする
- Snowflake上のDDL/VIEW/TABLE/PROCEDURE/AGENTはすべて「結果物」
- Agent/LLMは実DBや実データを直接解釈せず、Vault上の.mdのみを参照
- DEV/PRODやIMPORT/APP_PRODUCTION等のスキーマ設計・運用ルールは、必ず下記ガイドを参照

---

## 詳細ルール・運用ガイド

- 命名規則・リンク規則・設計思想の詳細は、以下のガイドに集約しています。
    - [MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md)
    - [NAMING_CONVENTIONS_GUIDE.md](NAMING_CONVENTIONS_GUIDE.md)
    - [README_DB_DESIGN.md](README_DB_DESIGN.md)
    - [docs/git/chatdemo/GIT_WORKFLOW.md](../../git/chatdemo/GIT_WORKFLOW.md)

---

## スキーマ・責務の全体像

| スキーマ            | 役割         |
| ------------------- | ------------ |
| DB_DESIGN           | 設計・設計レビュー  |
| IMPORT              | データ取込・検査   |
| NAME_RESOLUTION     | 名称解決（手動辞書） |
| APP_DEVELOPMENT     | アプリ開発・検証   |
| APP_PRODUCTION      | 本番アプリ・正本   |

---

## よくある質問・注意点

- APP_PRODUCTIONは業務ドメイン名であり、Snowflakeスキーマ名とは限りません
- DEV/PRODやIMPORT/APP_PRODUCTIONの切り替えは「設計の差」ではなく「配置先スキーマの差」のみで表現します
- 詳細な運用・禁止事項・例外・推奨事項は必ず[MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md)を参照してください

---

## 参考: 設計思想の要点

- 設計はVaultのMarkdownが正本
- データはIMPORT→APP_*に流れる
- 名称はNAME_RESOLUTIONで人が責任を持つ
- Agentは「考えない」決定論のみ実行

この構成により「説明可能性」「再現性」「監査耐性」「人による制御」を同時に満たします。

---

S3連携・Storage Integration/Stage設計の実務ノウハウは [S3_SNOWFLAKE_INTEGRATION_GUIDE.md](S3_SNOWFLAKE_INTEGRATION_GUIDE.md) を参照してください。
