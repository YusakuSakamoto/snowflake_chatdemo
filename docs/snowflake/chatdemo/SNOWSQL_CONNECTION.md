# SnowSQL接続方法

## 接続コマンド

### 秘密鍵認証（推奨）

```bash
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8
```

### 特定のロールで接続

```bash
# ACCOUNTADMINロールで接続
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r ACCOUNTADMIN

# GBPS253YS_API_ROLEロールで接続
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r GBPS253YS_API_ROLE
```

### クエリ実行（非対話モード）

```bash
# 単一クエリ実行
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "SELECT CURRENT_USER();"

# ファイルから実行
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -f script.sql

# 複数クエリ実行（セミコロン区切り）
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "USE DATABASE GBPS253YS_DB; SELECT CURRENT_DATABASE();"
```

---

## 接続設定

### 設定ファイルの場所

`~/.snowsql/config`

### myconn接続の設定内容

```ini
[connections.myconn]
accountname = PGPALAB-IY16795
username = YOLO
# private_key_path は明示的に指定（コマンドライン引数で上書き可能）
```

---

## よくある操作

### 1. Agent権限の付与

```bash
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r ACCOUNTADMIN -q "
GRANT USAGE ON AGENT GBPS253YS_DB.DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT 
TO ROLE GBPS253YS_API_ROLE;
"
```

### 2. データベースオブジェクトの確認

```bash
# スキーマ一覧
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "
USE DATABASE GBPS253YS_DB;
SHOW SCHEMAS;
"

# テーブル一覧
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "
SHOW TABLES IN SCHEMA GBPS253YS_DB.DB_DESIGN;
"

# Agent一覧
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "
SHOW AGENTS IN SCHEMA GBPS253YS_DB.DB_DESIGN;
"
```

### 3. Agent実行テスト

```bash
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r GBPS253YS_API_ROLE -q "
USE ROLE GBPS253YS_API_ROLE;
USE WAREHOUSE GBPS253YS_WH;
USE DATABASE GBPS253YS_DB;

SELECT SNOWFLAKE.CORTEX.COMPLETE_AGENT(
    'DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT',
    'DB_DESIGNスキーマの設計レビューを実行してください。対象テーブルは最大3件とします。'
) AS review_result;
"
```

---

## トラブルシューティング

### 秘密鍵のパスフレーズを求められる

秘密鍵にパスフレーズが設定されている場合、対話的に入力が求められます。
環境変数で設定することも可能：

```bash
export SNOWSQL_PRIVATE_KEY_PASSPHRASE="your-passphrase"
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8
```

### 接続タイムアウト

```bash
# タイムアウト時間を延長（秒）
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 \
  --option connect_timeout=300
```

### 詳細ログを出力

```bash
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 \
  -o log_level=DEBUG
```

---

## セキュリティ

### 秘密鍵のパーミッション

秘密鍵は適切な権限に設定してください：

```bash
chmod 600 /home/yolo/.ssh/snowflake/rsa_key.p8
```

### 秘密鍵の管理

- 秘密鍵はGitリポジトリにコミットしないこと
- `.gitignore`に`*.p8`を追加
- バックアップは暗号化して保管

---

## エイリアス設定（任意）

頻繁に使用する場合は、`.bashrc`または`.zshrc`にエイリアスを追加：

```bash
# ~/.bashrc または ~/.zshrc に追加
alias snowsql-myconn='snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8'
alias snowsql-admin='snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r ACCOUNTADMIN'
alias snowsql-api='snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -r GBPS253YS_API_ROLE'
```

反映：

```bash
source ~/.bashrc  # または source ~/.zshrc
```

使用例：

```bash
snowsql-admin -q "SHOW DATABASES;"
snowsql-api -q "SELECT CURRENT_ROLE();"
```

---

## 参考資料

- [SnowSQL公式ドキュメント](https://docs.snowflake.com/en/user-guide/snowsql)
- [秘密鍵認証](https://docs.snowflake.com/en/user-guide/key-pair-auth)
- [SnowSQL設定オプション](https://docs.snowflake.com/en/user-guide/snowsql-config)
