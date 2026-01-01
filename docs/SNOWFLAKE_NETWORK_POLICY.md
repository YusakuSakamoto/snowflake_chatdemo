# Snowflake ネットワークポリシー設定

## 現在のIPアドレス

**外部IP（インターネット）**: `119.47.235.175`  
**ローカルIP（WSL）**: `172.29.51.27`

## IPアドレス許可設定

### 1. Snowflake Web UIでの設定

1. Snowflake Web UI にログイン
   - URL: https://PGPALAB-IY16795.snowflakecomputing.com
   - ユーザー: `GBPS253YS_API_USER`

2. **Admin** → **Security** → **Network Policies** に移動

3. 既存のネットワークポリシーを編集、または新規作成

4. **Allowed IP Addresses** に以下を追加:
   ```
   119.47.235.175/32
   ```

### 2. SQLでの設定

#### 新しいネットワークポリシーを作成

```sql
-- ACCOUNTADMINロールで実行
USE ROLE ACCOUNTADMIN;

-- 現在のネットワークポリシーを確認
SHOW NETWORK POLICIES;

-- 新しいネットワークポリシーを作成
CREATE NETWORK POLICY allow_my_ip
  ALLOWED_IP_LIST = ('119.47.235.175/32')
  COMMENT = 'Allow access from development environment';

-- ユーザーにネットワークポリシーを適用
ALTER USER GBPS253YS_API_USER SET NETWORK_POLICY = allow_my_ip;

-- または、アカウント全体に適用
ALTER ACCOUNT SET NETWORK_POLICY = allow_my_ip;
```

#### 既存のネットワークポリシーに追加

```sql
USE ROLE ACCOUNTADMIN;

-- 既存のポリシー名を確認
SHOW NETWORK POLICIES;

-- 既存のポリシーにIPアドレスを追加
ALTER NETWORK POLICY <existing_policy_name>
  SET ALLOWED_IP_LIST = (
    '119.47.235.175/32',
    '他の既存IP/32'
  );
```

### 3. SnowSQLでの接続確認

```bash
# SnowSQLをインストール（まだの場合）
# https://docs.snowflake.com/en/user-guide/snowsql-install-config

# 方法1: 設定ファイルの接続名を使用（推奨）
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8

# 方法2: ブラウザ認証
snowsql -a PGPALAB-IY16795 \
  -u YUSAKURO \
  --authenticator externalbrowser

# 方法3: Personal Access Tokenで接続
snowsql -a PGPALAB-IY16795 \
  -u GBPS253YS_API_USER \
  --authenticator oauth \
  --token "<YOUR_SNOWFLAKE_BEARER_TOKEN>"

# 方法4: 秘密鍵認証（APIユーザー用）
snowsql -a PGPALAB-IY16795 \
  -u GBPS253YS_API_USER \
  --private-key-path /path/to/rsa_key.p8
```

#### SnowSQL設定ファイル (~/.snowsql/config)

```ini
[connections.myconn]
accountname = pgpalab-iy16795
username = YUSAKURO
# private_key_path = /home/yolo/.ssh/snowflake/rsa_key.p8

# 使用例
# snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8
```

### 4. ネットワークポリシーの確認

```sql
-- 現在のネットワークポリシーを確認
SHOW NETWORK POLICIES;

-- 特定のポリシーの詳細を確認
DESC NETWORK POLICY allow_my_ip;

-- ユーザーのネットワークポリシーを確認
SHOW PARAMETERS LIKE 'NETWORK_POLICY' FOR USER GBPS253YS_API_USER;

-- アカウントのネットワークポリシーを確認
SHOW PARAMETERS LIKE 'NETWORK_POLICY' FOR ACCOUNT;
```

### 5. 複数IPアドレスの許可（開発環境用）

```sql
-- 開発環境、自宅、オフィスなど複数のIPを許可
CREATE OR REPLACE NETWORK POLICY dev_access
  ALLOWED_IP_LIST = (
    '119.47.235.175/32',  -- 現在のIP
    '0.0.0.0/0'           -- すべてのIPを許可（開発時のみ推奨）
  )
  COMMENT = 'Development environment access';

-- 注意: '0.0.0.0/0' は本番環境では使用しないでください
```

### 6. トラブルシューティング

#### エラー: "IP address is not allowed to access Snowflake"

1. 現在のIPアドレスを確認:
   ```bash
   curl https://api.ipify.org
   ```

2. ネットワークポリシーに追加されているか確認

3. ポリシーが適用されているか確認:
   ```sql
   SHOW PARAMETERS LIKE 'NETWORK_POLICY' FOR USER GBPS253YS_API_USER;
   ```

#### IPアドレスが動的に変わる場合

```sql
-- IP範囲を許可（CIDR表記）
CREATE NETWORK POLICY flexible_access
  ALLOWED_IP_LIST = (
    '119.47.0.0/16'  -- より広い範囲を許可
  );
```

### 7. REST API / Azure Functions からのアクセス

Azure Functions から Snowflake に接続する場合:

1. **Azure Functions の送信IPアドレスを確認**
   - Azure Portal → Function App → Properties → Outbound IP addresses

2. **それらのIPをネットワークポリシーに追加**
   ```sql
   ALTER NETWORK POLICY allow_my_ip
     SET ALLOWED_IP_LIST = (
       '119.47.235.175/32',      -- 開発環境
       '13.78.xxx.xxx/32',       -- Azure Functions IP 1
       '13.78.yyy.yyy/32'        -- Azure Functions IP 2
       -- Azure Functions の全送信IPを追加
     );
   ```

### 8. セキュリティベストプラクティス

1. **最小権限の原則**: 必要なIPアドレスのみを許可
2. **定期的な見直し**: 使用していないIPは削除
3. **監査ログの確認**: 不審なアクセスをモニタリング
4. **開発と本番を分離**: 異なるネットワークポリシーを使用

```sql
-- 開発環境用
CREATE NETWORK POLICY dev_policy
  ALLOWED_IP_LIST = ('0.0.0.0/0');  -- 開発時のみ

-- 本番環境用
CREATE NETWORK POLICY prod_policy
  ALLOWED_IP_LIST = (
    '13.78.xxx.xxx/32',  -- 本番Azure Functions
    '52.xxx.xxx.xxx/32'  -- バックアップサーバー
  );
```

## 参考リンク

- [Snowflake Network Policies](https://docs.snowflake.com/en/user-guide/network-policies)
- [SnowSQL Installation](https://docs.snowflake.com/en/user-guide/snowsql-install-config)
- [Azure Functions Outbound IPs](https://learn.microsoft.com/en-us/azure/azure-functions/ip-addresses)

## 注意事項

- ネットワークポリシーの変更は即座に反映されます
- 誤って設定すると自分もアクセスできなくなる可能性があります
- ACCOUNTADMINロールが必要です
- Personal Access Token (PAT) を使用する場合も、ネットワークポリシーが適用されます
