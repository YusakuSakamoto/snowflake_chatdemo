"""
Snowflake接続ユーティリティ - 秘密鍵認証対応

秘密鍵認証とBearer Token認証の両方に対応したSnowflake接続クライアント
"""


import os

class SnowflakeAuthClient:
    def __init__(self):
        self.account_url = os.getenv("SNOWFLAKE_ACCOUNT_URL")
        self.bearer_token = os.getenv("SNOWFLAKE_BEARER_TOKEN")

    def get_auth_headers(self):
        if self.bearer_token:
            return {"Authorization": f"Bearer {self.bearer_token}"}
        raise ValueError("SNOWFLAKE_BEARER_TOKEN is not set")

    def get_bearer_token(self):
        if self.bearer_token:
            return self.bearer_token
        raise ValueError("SNOWFLAKE_BEARER_TOKEN is not set")
    def get_jwt_token(self) -> Optional[str]:
        """秘密鍵からJWTトークンを生成"""
        if not self.private_key_path or not os.path.exists(self.private_key_path):
            return None
        
        try:
            # 秘密鍵を読み込み
            with open(self.private_key_path, "rb") as key_file:
                private_key_data = key_file.read()
            
            passphrase = self.private_key_passphrase.encode() if self.private_key_passphrase else None
            
            private_key = serialization.load_pem_private_key(
                private_key_data,
                password=passphrase,
                backend=default_backend()
            )
            
            # 公開鍵のフィンガープリントを取得
            public_key_bytes = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            import hashlib
            public_key_fp = 'SHA256:' + hashlib.sha256(public_key_bytes).hexdigest()
            
            # JWTペイロードを作成
            account_identifier = f"{self.account}".upper()
            qualified_username = f"{self.user}".upper()
            
            now = int(time.time())
            lifetime = 3600  # 1時間
            
            payload = {
                "iss": f"{account_identifier}.{qualified_username}.{public_key_fp}",
                "sub": qualified_username,
                "iat": now,
                "exp": now + lifetime
            }
            
            # JWTトークンを生成
            token = jwt.encode(
                payload,
                private_key,
                algorithm="RS256"
            )
            
            return token
            
        except Exception as e:
            print(f"JWT token generation failed: {e}")
            return None
    
    def get_auth_header(self) -> Dict[str, str]:
        """認証ヘッダーを取得"""
        if self.auth_method == "private_key":
            jwt_token = self.get_jwt_token()
            if jwt_token:
                return {"Authorization": f"Bearer {jwt_token}"}
        
        # デフォルトはBearer Token
        if self.bearer_token:
            return {"Authorization": f"Bearer {self.bearer_token}"}
        
        raise ValueError("No authentication method available")
    
    def execute_query(self, sql: str) -> Optional[Dict[str, Any]]:
        """SQLクエリを実行"""
        url = f"{self.account_url}/api/v2/statements"
        
        headers = {
            **self.get_auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "statement": sql,
            "timeout": 60,
            "database": self.database,
            "schema": self.schema,
            "warehouse": self.warehouse,
            "role": self.role
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Query execution failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return None
    
    def test_connection(self) -> bool:
        """接続テスト"""
        result = self.execute_query("SELECT CURRENT_VERSION(), CURRENT_USER(), CURRENT_ACCOUNT()")
        
        if result and 'data' in result:
            print("✅ Connection successful!")
            print(f"   Data: {result['data']}")
            return True
        else:
            print("❌ Connection failed!")
            return False


def main():
    """テスト実行"""
    print("Snowflake認証テスト")
    print("=" * 50)
    
    client = SnowflakeAuthClient()
    
    print(f"Account: {client.account}")
    print(f"User: {client.user}")
    print(f"Auth Method: {client.auth_method}")
    print(f"Database: {client.database}")
    print(f"Schema: {client.schema}")
    print()
    
    # 接続テスト
    client.test_connection()


if __name__ == "__main__":
    main()
