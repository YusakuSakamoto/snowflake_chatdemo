# プロシージャ設計：[[design.INGEST_VAULT_MD]]

## 概要
DB_DESIGN.[[design.INGEST_VAULT_MD]] は、S3ステージに同期されたObsidian VaultのMarkdownファイルを読み込み、DB_DESIGN.[[design.DOCS_OBSIDIAN]] テーブルに取り込むための専用プロシージャである。

本プロシージャは、GitHub → S3 → Snowflake の同期フローにおいて、Snowflake側のデータ取り込みを担当する唯一の書き込み経路である。

## 業務上の意味
- このプロシージャが表す概念  
  1つのMarkdownファイルを1レコードとして、[[design.DB_DESIGN]].DOCS_OBSIDIANテーブルにUPSERT（INSERT or UPDATE）する。

- 主な利用シーン  
  - Obsidian Vault更新後、GitHub Actions経由でS3に同期された後、手動またはタスクで実行
  - Cortex Agentが最新の設計ドキュメントを参照できるようにする
  - 注記：プロファイル結果は外部テーブル（DB_DESIGN.[[design.PROFILE_RESULTS_EXTERNAL]]）で直接参照するため、本プロシージャの対象外

## 設計上の位置づけ

### データフロー全体における役割
```
Obsidian Vault (Windows)
  ↓ 手動編集
WSL (Linux)
  ↓ git commit & push
GitHub Repository
  ↓ GitHub Actions
S3 (snowflake-chatdemo-vault-prod)
  ↓ INGEST_VAULT_MD ← 本プロシージャ
Snowflake: DB_DESIGN.DOCS_OBSIDIAN
  ↓ SELECT
Cortex Agent (SNOWFLAKE_DEMO_AGENT)
```

本プロシージャは、S3からSnowflakeへの橋渡しを担当する。

### DOCS_OBSIDIANテーブルとの関係
- DB_DESIGN.[[design.DOCS_OBSIDIAN]] への INSERT / UPDATE / DELETE は、本プロシージャのみが行う
- 直接のDML（手動INSERT/UPDATEなど）は禁止
- データ整合性と一元管理のため、取り込みロジックを本プロシージャに集約

### External Tableとの違い
External Tableとして DB_DESIGN.[[design.DOCS_OBSIDIAN]] を定義する案もあるが、本設計では内部テーブル + [[design.INGEST_VAULT_MD]] を採用：

#### 内部テーブル + プロシージャの利点
- クエリ高速化：Cortex Agentが頻繁にアクセスするため、内部テーブルの方が高速
- 全文検索の最適化：Search Optimization Serviceが利用可能
- 変換処理：ファイルパスの正規化、メタデータ抽出、ハッシュ計算を事前実行
- バージョン管理：UPDATED_ATでVault更新履歴を追跡

#### External Tableとの比較
| 項目 | Internal Table + [[design.INGEST_VAULT_MD]] | External Table |
|------|----------------------------------|----------------|
| クエリ速度 | ◎ 高速（内部ストレージ） | △ 低速（S3スキャン） |
| 全文検索 | ◎ Search Optimization | △ 制限あり |
| コスト | △ ストレージコスト高 | ◎ S3が安価 |
| リアルタイム性 | △ 手動/定期実行 | ◎ AUTO_REFRESH |
| データ変換 | ◎ 柔軟 | △ 制限あり |

本設計では、クエリ性能を優先し、内部テーブル方式を採用する。

## プロシージャの設計方針

### 入力パラメータ

#### 1. STAGE_NAME (VARCHAR)
- 意味：読み込み対象のSnowflake External Stage名
- 値例：`@DB_DESIGN.[[design.OBSIDIAN_VAULT_STAGE]]`
- 用途：S3バケット（`s3://snowflake-chatdemo-vault-prod/`）をマウントしたステージ

#### 2. PATTERN (VARCHAR)
- 意味：取り込み対象ファイルのパターン（glob）
- 値例：`'.*\\.md'`（全Markdownファイル）、`'design/.*\\.md'`（design/配下のみ）
- 用途：特定ディレクトリのみを取り込む場合に絞り込み

### 処理フロー

#### ステップ1：S3ステージのファイル一覧取得
```sql
LIST @DB_DESIGN.OBSIDIAN_VAULT_STAGE PATTERN='.*\.md'
```

LISTコマンドで、ステージ内の全Markdownファイルのパスとメタデータを取得。

#### ステップ2：各ファイルの読み込み
```python
# Pythonコード内（INGEST_VAULT_MDの実装）
from snowflake.snowpark.files import SnowflakeFile

for row in rows:  # LIST結果の各ファイル
    file_path = _to_relpath(row['name'])  # S3パスからステージ相対パスへ変換
    
    # ファイル内容を読み込み
    with SnowflakeFile.open(f"{stage_name}/{file_path}", 'r') as f:
        content = f.read()
```

#### ステップ3：ファイルパスの正規化
```python
def _to_relpath(name: str) -> str:
    """
    LIST結果のnameが
      - s3://<bucket>/path...
      - path...
    のどちらでも、ステージ相対パスを返す。
    """
    n = str(name).lstrip("/")
    prefix = f"s3://{BUCKET}/"
    if n.startswith(prefix):
        return n[len(prefix):]
    return n
```

`s3://snowflake-chatdemo-vault-prod/design/[[design.APP_PRODUCTION]]/design.[[design.ANKEN_MEISAI]].md`
  ↓
`design/[[design.APP_PRODUCTION]]/design.[[design.ANKEN_MEISAI]].md`

#### ステップ4：コンテンツハッシュ計算
```python
def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

content_hash = _md5(content)
```

ファイル内容のMD5ハッシュを計算し、変更検知に使用。

#### ステップ5：DOCS_OBSIDIANへUPSERT
```python
# MERGE文で既存レコードを更新、新規レコードを挿入
session.sql(f"""
    MERGE INTO DB_DESIGN.DOCS_OBSIDIAN AS target
    USING (
        SELECT 
            '{file_path}' AS file_path,
            '{content}' AS file_content,
            '{content_hash}' AS content_hash,
            CURRENT_TIMESTAMP() AS updated_at
    ) AS source
    ON target.file_path = source.file_path
    WHEN MATCHED AND target.content_hash != source.content_hash THEN
        UPDATE SET 
            file_content = source.file_content,
            content_hash = source.content_hash,
            updated_at = source.updated_at
    WHEN NOT MATCHED THEN
        INSERT (file_path, file_content, content_hash, created_at, updated_at)
        VALUES (source.file_path, source.file_content, source.content_hash, 
                source.updated_at, source.updated_at)
""").collect()
```

- MATCHED AND content_hash != content_hash：ファイルが変更された場合のみUPDATE
- NOT MATCHED：新規ファイルをINSERT
- 変更なし：何もしない（効率化）

#### ステップ6：処理結果の返却
```python
return {
    'processed': processed,  # 処理したファイル数
    'errors': errors,        # エラー数
    'samples': samples       # サンプルファイルパス（最初の5件）
}
```

### エラーハンドリング

#### ファイル読み込みエラー
- 発生条件：S3のファイルが破損、エンコーディングエラー
- 対処：エラーカウントを増やし、次のファイルへ続行（全体中断しない）

#### ステージアクセスエラー
- 発生条件：IAM権限不足、ステージ名が間違っている
- 対処：例外をスローし、プロシージャ全体を失敗させる

#### 文字エンコーディングエラー
- 発生条件：UTF-8以外のエンコーディングのファイル
- 対処：エラーログに記録し、スキップ

## 運用設計

### 実行タイミング

#### 1. 手動実行（初期・テスト時）
```sql
-- 全Markdownファイルを取り込み
CALL DB_DESIGN.INGEST_VAULT_MD(
    '@DB_DESIGN.OBSIDIAN_VAULT_STAGE',
    '.*\\.md'
);

-- design/配下のみ取り込み
CALL DB_DESIGN.INGEST_VAULT_MD(
    '@DB_DESIGN.OBSIDIAN_VAULT_STAGE',
    'design/.*\\.md'
);
```

#### 2. タスクによる定期実行
```sql
CREATE OR REPLACE TASK DB_DESIGN.SYNC_VAULT_DOCS
  WAREHOUSE = ETL_WH
  SCHEDULE = 'USING CRON 0 */6 * * * UTC'  -- 6時間ごと
AS
  CALL DB_DESIGN.INGEST_VAULT_MD(
    '@DB_DESIGN.OBSIDIAN_VAULT_STAGE',
    '.*\\.md'
  );
```

#### 3. GitHub Actions経由でトリガー（推奨）
```yaml
# .github/workflows/sync-vault-to-snowflake.yml
- name: Trigger Snowflake Ingest
  run: |
    # SnowflakeのREST APIでプロシージャ実行
    curl -X POST https://your-account.snowflakecomputing.com/api/v2/statements \
      -H "Authorization: Bearer ${{ secrets.SNOWFLAKE_TOKEN }}" \
      -H "Content-Type: application/json" \
      -d '{
        "statement": "CALL DB_DESIGN.INGEST_VAULT_MD(@DB_DESIGN.OBSIDIAN_VAULT_STAGE, '\''.*\\\\.md'\'')",
        "warehouse": "ETL_WH"
      }'
```

### モニタリング

#### 実行結果の確認
```sql
-- 最終更新時刻の確認
SELECT 
  MAX(updated_at) AS last_sync_time,
  COUNT(*) AS total_docs
FROM DB_DESIGN.DOCS_OBSIDIAN;

-- 最近更新されたファイル（上位10件）
SELECT 
  file_path,
  updated_at,
  LENGTH(file_content) AS content_size
FROM DB_DESIGN.DOCS_OBSIDIAN
ORDER BY updated_at DESC
LIMIT 10;
```

#### エラーログ
プロシージャの返り値でエラー数を確認：
```sql
-- 実行結果を変数に格納
SET result = (CALL DB_DESIGN.INGEST_VAULT_MD(@DB_DESIGN.OBSIDIAN_VAULT_STAGE, '.*\\.md'));

-- エラー数を確認
SELECT 
  $result:processed AS processed,
  $result:errors AS errors;

-- エラーがある場合はアラート
SELECT 
  CASE 
    WHEN $result:errors > 0 THEN 'WARNING: Errors detected in Vault ingestion'
    ELSE 'SUCCESS'
  END AS status;
```

### トラブルシューティング

#### 問題1：プロシージャが失敗する
```sql
-- ステージのアクセス確認
LIST @DB_DESIGN.OBSIDIAN_VAULT_STAGE;

-- IAM権限の確認
DESC STORAGE INTEGRATION S3_INTEGRATION_READONLY;
```

#### 問題2：一部のファイルが取り込まれない
```sql
-- PATTERNの確認
CALL DB_DESIGN.INGEST_VAULT_MD(
    '@DB_DESIGN.OBSIDIAN_VAULT_STAGE',
    'design/APP_PRODUCTION/.*\\.md'  -- 特定ディレクトリに絞り込み
);

-- ステージのファイル一覧と比較
LIST @DB_DESIGN.OBSIDIAN_VAULT_STAGE PATTERN='design/.*\.md';

SELECT file_path FROM DB_DESIGN.DOCS_OBSIDIAN WHERE file_path LIKE 'design/%';
```

#### 問題3：古いファイルが残っている（削除されたファイル）
S3から削除されたファイルは、自動的にDOCS_OBSIDIANから削除されない。手動で削除するか、定期クリーンアップタスクを設定：

```sql
-- S3にないファイルを削除（クリーンアップ）
DELETE FROM DB_DESIGN.DOCS_OBSIDIAN
WHERE file_path NOT IN (
  SELECT DISTINCT _to_relpath("name")
  FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))  -- 直前のLIST結果
);
```

または、プロシージャ内で削除ロジックを追加（将来拡張）。

## プロファイル結果の参照方法

### 外部テーブルで直接参照（推奨設計）
プロファイル結果は、外部テーブル（[[design.PROFILE_RESULTS_EXTERNAL]] / [[design.PROFILE_RUNS_EXTERNAL]]）で直接S3を参照する設計を採用：

```
PROFILE_ALL_TABLES (プロファイル実行)
  ↓ JSON直接書き込み
S3 (s3://snowflake-chatdemo-vault-prod/profile_results/year=YYYY/month=MM/day=DD/)
  ↓ 外部テーブル参照
DB_DESIGN.PROFILE_RESULTS_EXTERNAL (外部テーブル)
  ↓ クエリ
Cortex Agent / BI Tool
```

### 本プロシージャの対象外
- プロファイル結果（JSON形式）は `INGEST_VAULT_MD` の対象外
- 設計ドキュメント（Markdown形式）のみを `DOCS_OBSIDIAN` に取り込む
- 理由：
  - プロファイル結果は頻繁に更新されない（週次・月次）
  - リアルタイム性が不要
  - ストレージコスト削減（S3のみで管理）### ANKEN_ID
- データ型: VARCHAR(50)
- NULL数: 0 (0.0%)
- ユニーク数: 12,345 (100.0%)
- 最小値: A0001
- 最大値: A9999
- 理由：
  - プロファイル結果は頻繁に更新されない（週次・月次）
  - リアルタイム性が不要
  - ストレージコスト削減（S3のみで管理）

### プロファイル結果のクエリ例
```sql
-- 最新のプロファイル結果を参照
SELECT 
  target_schema,
  target_table,
  target_column,
  metrics:null_rate::FLOAT AS null_rate,
  metrics:distinct_count::NUMBER AS distinct_count
FROM DB_DESIGN.PROFILE_RESULTS_EXTERNAL
WHERE target_db = 'GBPS253YS_DB'
  AND target_schema = 'APP_PRODUCTION'
  AND year = 2026
  AND month = 1
ORDER BY target_table, target_column;
```

## 拡張計画

### 1. 削除ファイルの自動クリーンアップ
S3から削除されたファイルを自動的にDOCS_OBSIDIANからも削除：

```python
# プロシージャ内に追加
# ステップ7：削除ファイルの検出と削除
existing_files = {row['FILE_PATH'] for row in session.sql("SELECT file_path FROM DB_DESIGN.DOCS_OBSIDIAN").collect()}
current_files = {_to_relpath(row['name']) for row in rows}
deleted_files = existing_files - current_files

for file_path in deleted_files:
    session.sql(f"DELETE FROM DB_DESIGN.DOCS_OBSIDIAN WHERE file_path = '{file_path}'").collect()
```

### 2. 差分検知の高速化
content_hashを利用して、変更されたファイルのみ処理：

```python
# 既存ハッシュをメモリに読み込み
existing_hashes = {
    row['FILE_PATH']: row['CONTENT_HASH']
    for row in session.sql("SELECT file_path, content_hash FROM DB_DESIGN.DOCS_OBSIDIAN").collect()
}

# 変更されたファイルのみ処理
for row in rows:
    file_path = _to_relpath(row['name'])
    
    with SnowflakeFile.open(f"{stage_name}/{file_path}", 'r') as f:
        content = f.read()
    
    content_hash = _md5(content)
    
    if existing_hashes.get(file_path) == content_hash:
        # 変更なし、スキップ
        continue
    
    # 変更あり、UPSERT実行
    ...
```

### 3. バッチ処理の最適化
MERGEを個別実行ではなく、一括バッチで実行：

```python
# 一時テーブルにステージング
session.sql("""
    CREATE TEMP TABLE tmp_vault_updates (
        file_path VARCHAR,
        file_content VARCHAR,
        content_hash VARCHAR
    )
""").collect()

# 一括INSERT
for row in rows:
    ...
    session.sql(f"""
        INSERT INTO tmp_vault_updates VALUES ('{file_path}', '{content}', '{content_hash}')
    """).collect()

# 一括MERGE
session.sql("""
    MERGE INTO DB_DESIGN.DOCS_OBSIDIAN AS target
    USING tmp_vault_updates AS source
    ON target.file_path = source.file_path
    ...
""").collect()
```

### 4. 並列処理
大量のファイルを高速処理するため、Snowparkの並列処理機能を利用：

```python
from concurrent.futures import ThreadPoolExecutor

def process_file(row):
    # ファイル読み込み → ハッシュ計算 → UPSERT
    ...

with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(process_file, rows))
```

## 設計レビュー時のチェックポイント
- [ ] ステージ（[[design.OBSIDIAN_VAULT_STAGE]]）が正しく定義されているか
- [ ] IAMポリシーでS3読み取り権限が付与されているか
- [ ] プロシージャのPATTERNパラメータが適切か（全md vs 特定ディレクトリ）
- [ ] content_hashによる差分検知が機能しているか
- [ ] エラーハンドリングが適切か（一部エラーでも全体が止まらない）
- [ ] 実行頻度が適切か（手動 vs 定期タスク vs GitHub Actionsトリガー）
- [ ] 削除ファイルのクリーンアップロジックが必要か
- [ ] パフォーマンスが許容範囲内か（大量ファイルの場合）

## 参考リンク
- DB_DESIGN.[[design.DOCS_OBSIDIAN]] - 取り込み先テーブルの設計
- DB_DESIGN.[[design.OBSIDIAN_VAULT_STAGE]] - S3ステージの定義
- Snowflake SnowparkFile: https://docs.snowflake.com/en/developer-guide/snowpark/python/working-with-files
- S3 External Stage: https://docs.snowflake.com/en/user-guide/data-load-s3
