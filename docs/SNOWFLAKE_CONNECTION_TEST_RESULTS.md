# Snowflake接続テスト結果

**実施日時**: 2026年1月2日  
**接続方法**: SnowSQL + Private Key Authentication

## ✅ 接続成功

### セッション情報
- **Snowflakeバージョン**: 9.39.2
- **ユーザー**: YUSAKURO
- **アカウント**: IW55960 (PGPALAB-IY16795)
- **リージョン**: AWS_AP_NORTHEAST_1
- **ロール**: ACCOUNTADMIN

### 利用可能なデータベース
1. **GBPS253YS_DB** (メインデータベース)
2. SNOWFLAKE (システムデータベース)
3. USER$YUSAKURO (個人データベース)

### 利用可能なウェアハウス
1. **GBPS253YS_WH** - X-Small, Auto-suspend: 120秒
2. COMPUTE_WH - X-Small, Auto-suspend: 600秒
3. SYSTEM$STREAMLIT_NOTEBOOK_WH - X-Small

## データベース構造

### GBPS253YS_DB スキーマ一覧
1. **APP_PRODUCTION** - アプリケーション本番環境 ⭐
2. APP_DEVELOPMENT - アプリケーション開発環境
3. DB_DESIGN - DB設計用スキーマ
4. IMPORT - データ取込・検査
5. INFORMATION_SCHEMA - システムビュー
6. NAME_RESOLUTION - 名称解決（手動辞書）

### APP_PRODUCTION テーブル

#### 1. ANKEN_MEISAI（案件明細）
- レコード数: 1,232件
- サイズ: 74,240 bytes
- 用途: 案件明細CSV取込用テーブル

**カラム構成**:
- `ACCOUNTING_MONTH`: 会計月
- `ACTIVE_FLAG`: 有効フラグ
- `AMOUNT`: 金額
- `BRANCH_NUMBER`: 支店番号
- `CUSTOMER_ID`: 顧客ID
- `CUSTOMER_NAME`: 顧客名
- `CUSTOMER_ORDER_NUMBER`: 顧客注文番号
- `CUSTOMER_QUOTE_REQUEST_NUMBER`: 顧客見積依頼番号
- `DEPARTMENT_ID`: 部署ID
- `DEPARTMENT_NAME`: 部署名
- `DEPARTMENT_SECTION_SHORT_NAME`: 部署セクション略称
- `DEPARTMENT_SHORT_NAME`: 部署略称
- `DIVISION_CODE`: 事業部コード
- `FISCAL_YEAR`: 会計年度
- `GROUP_SHORT_NAME`: グループ略称
- `ID`: ID
- `INVOICE_NUMBER`: 請求書番号
- `ORDER_NAME`: 注文名
- `ORDER_NUMBER`: 注文番号
- `PROJECT_NAME`: プロジェクト名
- `PROJECT_NUMBER`: プロジェクト番号
- `RANK`: ランク
- `SALES_CATEGORY`: 売上カテゴリ
- `SALES_DELIVERY_FLAG`: 売上配送フラグ
- `SECTION_NAME`: セクション名
- `SUBJECT`: 件名
- `WORK_END_DATE`: 作業終了日
- `WORK_START_DATE`: 作業開始日

#### 2. DEPARTMENT_MASTER（部署マスタ）
- レコード数: 110件
- サイズ: 11,776 bytes
- 用途: 部署マスタ（年度別）CSV取込用テーブル

## Cortex Agent確認

### 検索結果
- Cortex Search Services: **未設定**
- Cortex Agentの設定が必要

### 次のステップ
1. Cortex Agentの作成
2. ツール（text_to_sql, resolve_entity_alias等）の設定
3. REST API経由での接続テスト

## ネットワーク設定

### 現在のIPアドレス
- **外部IP**: 119.47.235.175

### 接続コマンド
```bash
# SnowSQL接続
snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8

# ウェアハウスとスキーマを指定して接続
snowsql -c myconn \
  --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 \
  -w GBPS253YS_WH \
  -d GBPS253YS_DB \
  -s APP_PRODUCTION
```

## プロジェクト設定確認

### local.settings.json の設定値
```json
{
  "SNOWFLAKE_ACCOUNT": "PGPALAB-IY16795",
  "SNOWFLAKE_ACCOUNT_URL": "https://PGPALAB-IY16795.snowflakecomputing.com",
  "SNOWFLAKE_USER": "GBPS253YS_API_USER",
  "SNOWFLAKE_WAREHOUSE": "GBPS253YS_WH",
  "SNOWFLAKE_DATABASE": "GBPS253YS_DB",
  "SNOWFLAKE_SCHEMA": "APP_PRODUCTION",
  "SNOWFLAKE_AGENT_NAME": "SNOWFLAKE_DEMO_AGENT"
}
```

### 注意点
- 現在のSnowSQL接続ユーザー: **YUSAKURO**
- APIユーザー設定: **GBPS253YS_API_USER**
- 両ユーザーで同じ秘密鍵を使用可能か確認が必要

## REST API接続テスト予定

### エンドポイント
```
POST https://PGPALAB-IY16795.snowflakecomputing.com/api/v2/databases/GBPS253YS_DB/schemas/APP_PRODUCTION/agents/SNOWFLAKE_DEMO_AGENT:run
```

### 必要な作業
1. Cortex Agent `SNOWFLAKE_DEMO_AGENT` の作成
2. APIユーザー `GBPS253YS_API_USER` の権限確認
3. Bearer Token または Private Key での認証テスト
4. `/api/chat-stream` エンドポイントのテスト

## まとめ

✅ **接続成功**: SnowSQLでの接続確認完了  
✅ **データベース確認**: GBPS253YS_DB に案件明細データ（1,232件）が存在  
✅ **ウェアハウス確認**: GBPS253YS_WH が利用可能  
⏳ **Cortex Agent**: 設定が必要  
⏳ **REST API**: 接続テスト待ち
