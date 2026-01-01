# design.[[design.PROFILE_TABLE]]

## 概要

`DB_DESIGN.PROFILE_TABLE` は、指定された単一テーブルの全カラムに対して、品質プロファイルメトリクスを算出・記録するプロシージャです。

- スキーマ: [[design.DB_DESIGN]] (SCH_20251226180633)
- オブジェクトタイプ: PROCEDURE
- 言語: SQL
- 実行モード: EXECUTE AS OWNER
- 戻り値: STRING (`RUN_ID`)

---

## 業務上の意味

### 目的
個別テーブルの品質プロファイル（行数、NULL率、ユニーク値数、最小/最大値、頻出値など）を自動収集し、データ品質レビューの基礎データを蓄積します。プロファイル結果はPROFILE_RUNSおよびPROFILE_RESULTSテーブルに記録され、後続の品質分析や異常検知に活用されます。

### 利用シーン
- 個別テーブルの詳細プロファイル: 特定のテーブルに絞った品質調査
- PROFILE_ALL_TABLESからの呼び出し: スキーマ全体の一括プロファイル実行時の実行単位
- 再実行による差分検証: 同一RUN_IDで再実行し、品質変化を追跡
- マイグレーション検証: 移行前後での各カラムの統計値比較

---

## 設計上の位置づけ

### データフロー
```
PROFILE_ALL_TABLES (オーケストレーション層)
  ↓
PROFILE_TABLE (個別テーブル処理) ← 本プロシージャ
  ↓
INFORMATION_SCHEMA.COLUMNS (カラム一覧取得)
  ↓
PROFILE_COLUMN (カラムメトリクス算出) ← ループ実行
  ↓
PROFILE_RESULTS (カラム別メトリクス記録)
PROFILE_RUNS (実行履歴記録)
  ↓
EXPORT_PROFILE_EVIDENCE_MD_VFINAL (Markdown出力)
  ↓
S3 (snowflake-chatdemo-vault-prod/reviews/profiles/)
```

### 他コンポーネントとの連携
- 上流: DB_DESIGN.[[design.PROFILE_ALL_TABLES]] (全テーブルプロファイル)
- 並列処理: INFORMATION_SCHEMA.COLUMNS (カラムメタデータ取得)
- 下流: DB_DESIGN.[[design.PROFILE_RESULTS]] (カラムメトリクス蓄積)
- 下流: DB_DESIGN.[[design.PROFILE_RUNS]] (実行履歴記録)
- 出力: DB_DESIGN.[[design.EXPORT_PROFILE_EVIDENCE_MD_VFINAL]] (S3エクスポート)

---

## 設計方針

### 1. 冪等性設計
方針: 同一RUN_IDでの再実行を安全にサポート  
理由:
- ネットワーク障害やタイムアウトによる再実行シナリオに対応
- 差分検証のために意図的に同じRUN_IDで再プロファイルを実施

実装:
```sql
MERGE INTO DB_DESIGN.PROFILE_RUNS ...
  ON T.RUN_ID = S.RUN_ID
  WHEN MATCHED THEN UPDATE SET ...
  WHEN NOT MATCHED THEN INSERT ...;

DELETE FROM DB_DESIGN.PROFILE_RESULTS
 WHERE RUN_ID = :V_RUN_ID;
```
- MERGE: 既存のRUN_IDがあれば更新、なければ新規挿入
- DELETE: 再実行時に既存の結果を削除し、重複を防止

### 2. トランザクション境界
方針: 1テーブル全体を1トランザクションとして扱う  
理由:
- カラムごとのループ実行中にエラーが発生した場合、部分的な結果を残さない
- 全カラムの整合性を保証（途中終了したRUN_IDは`STATUS = 'FAILED'`で明示）

実装:
```sql
BEGIN
  -- RUN登録、カラムループ、結果記録
  UPDATE DB_DESIGN.PROFILE_RUNS SET STATUS = 'SUCCEEDED' ...;
EXCEPTION
  WHEN OTHER THEN
    UPDATE DB_DESIGN.PROFILE_RUNS SET STATUS = 'FAILED' ...;
    RAISE;
END;
```

### 3. サンプリング戦略
方針: P_SAMPLE_PCTパラメータでBERNOULLIサンプリングをサポート  
理由:
- 大規模テーブル（数億行）のプロファイルでコストとクエリ時間を削減
- NULL値や頻出値の統計は、適切なサンプリングで精度を維持可能

実装:
```sql
CASE
  WHEN P_SAMPLE_PCT IS NULL THEN ''
  ELSE ' TABLESAMPLE BERNOULLI(' || P_SAMPLE_PCT || ')'
END
```
- BERNOULLIサンプリング: Snowflakeの標準機能を活用し、ランダムサンプリングを実現
- NULL時は全件スキャン: 正確性が必要な場合に対応

### 4. カラムメトリクス統一化
方針: すべてのカラムに対して同一の統計指標を算出  
理由:
- 異なる型（数値/文字列/日付）に対しても、統一的にプロファイル可能
- TO_VARCHAR変換により、MIN/MAXを文字列ソート順で算出

実装:
```sql
SELECT OBJECT_CONSTRUCT(
  'row_count', COUNT(*),
  'null_count', SUM(IFF(COL IS NULL, 1, 0)),
  'distinct_count', COUNT(DISTINCT COL),
  'min_varchar', MIN(TO_VARCHAR(COL)),
  'max_varchar', MAX(TO_VARCHAR(COL)),
  'min_len', MIN(LENGTH(TO_VARCHAR(COL))),
  'max_len', MAX(LENGTH(TO_VARCHAR(COL))),
  'top_values', ARRAY_AGG(...)
)
```
- TO_VARCHAR変換: 日付型や数値型も文字列として統一処理
- OBJECT_CONSTRUCT: JSONとしてメトリクスを保存（スキーマ変更に柔軟）

---

## パラメータ設計

| パラメータ名 | 型 | 必須 | デフォルト値 | 説明 |
|---|---|---|---|---|
| `P_TARGET_DB` | STRING | ✅ | - | プロファイル対象のデータベース名 |
| `P_TARGET_SCHEMA` | STRING | ✅ | - | プロファイル対象のスキーマ名 |
| `P_TARGET_TABLE` | STRING | ✅ | - | プロファイル対象のテーブル名 |
| `P_SAMPLE_PCT` | FLOAT | - | NULL | サンプリング割合（0.0～100.0）。NULLの場合は全件スキャン |
| `P_RUN_ID` | STRING | - | NULL | 実行ID。NULLの場合は自動生成（`RUN-` + UUID） |
| `P_GIT_COMMIT` | STRING | - | NULL | Git コミットハッシュ（バージョン管理用） |
| `P_NOTE` | STRING | - | NULL | 実行メモ（運用管理用） |

### パラメータ設計の背景
- P_SAMPLE_PCT: BERNOULLIサンプリング（行単位）を使用。例: 1.0 = 1%サンプリング、100.0 = 全件
- P_RUN_ID: 外部から指定可能にすることで、複数テーブルの一括実行時に共通IDで管理可能
- P_GIT_COMMIT: DDL変更やプロシージャ更新のトレーサビリティを確保
- P_NOTE: 定期実行 vs アドホック実行の区別、担当者記録など

---

## 戻り値設計

### 戻り値: `RUN_ID`（STRING）
成功時には実行ID（例: `RUN-01HX...`）を返却します。このIDを使用して、PROFILE_RUNSおよびPROFILE_RESULTSから詳細なプロファイル結果を取得できます。

### 利用例
```sql
DECLARE
  V_RUN_ID STRING;
BEGIN
  CALL DB_DESIGN.PROFILE_TABLE(
    'GBPS253YS_DB', 'PUBLIC', 'CUSTOMERS', NULL
  ) INTO :V_RUN_ID;
  
  -- 結果確認
  SELECT * FROM DB_DESIGN.PROFILE_RESULTS
   WHERE RUN_ID = :V_RUN_ID
   ORDER BY TARGET_COLUMN;
END;
```

---

## 内部処理フロー

### ステップ1: RUN初期化
```sql
V_STARTED := CURRENT_TIMESTAMP();
V_RUN_ID  := COALESCE(P_RUN_ID, 'RUN-' || UUID_STRING());
```
- UUID_STRING(): Snowflakeの標準関数で一意なIDを生成
- COALESCE: 外部指定がなければ自動生成

### ステップ2: RUN登録（冪等）
```sql
MERGE INTO DB_DESIGN.PROFILE_RUNS T
USING (SELECT :V_RUN_ID AS RUN_ID, ...) S
ON T.RUN_ID = S.RUN_ID
WHEN MATCHED THEN UPDATE SET STATUS = 'RUNNING', ...
WHEN NOT MATCHED THEN INSERT (...);
```
- MERGE: 再実行時に既存のRUN_IDを更新し、STATUS='RUNNING'にリセット
- WAREHOUSE_NAME, ROLE_NAME: 実行環境のメタデータを記録

### ステップ3: 既存結果削除（再実行対策）
```sql
DELETE FROM DB_DESIGN.PROFILE_RESULTS
 WHERE RUN_ID = :V_RUN_ID;
```
- 再実行時の重複データを防止
- トランザクション内で削除するため、エラー時はロールバック

### ステップ4: 対象テーブルのフル修飾名生成
```sql
V_QDB  := '"' || REPLACE(P_TARGET_DB, '"', '""') || '"';
V_QSC  := '"' || REPLACE(P_TARGET_SCHEMA, '"', '""') || '"';
V_QTB  := '"' || REPLACE(P_TARGET_TABLE, '"', '""') || '"';
V_FULL := V_QDB || '.' || V_QSC || '.' || V_QTB;
```
- REPLACE(..., '"', '""'): ダブルクォートのエスケープ処理
- フル修飾名: `"DB"."SCHEMA"."TABLE"` の形式で構築

### ステップ5: カラム一覧取得
```sql
V_SQLC := '
  SELECT COLUMN_NAME
  FROM ' || V_QDB || '.INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = ?
    AND TABLE_NAME   = ?
  ORDER BY ORDINAL_POSITION
';
V_COL_RS := (EXECUTE IMMEDIATE :V_SQLC USING (P_TARGET_SCHEMA, P_TARGET_TABLE));
```
- INFORMATION_SCHEMA.COLUMNS: Snowflake標準ビューでカラムメタデータ取得
- ORDINAL_POSITION: テーブル定義順でカラムを処理
- USING句: SQLインジェクション対策（パラメータバインディング）

### ステップ6: カラムごとのメトリクス算出（ループ）
```sql
FOR REC IN V_COL_RS DO
  V_COL_NAME := REC.COLUMN_NAME;
  V_QCOL := '"' || REPLACE(V_COL_NAME, '"', '""') || '"';

  V_SQL := '
WITH SRC AS (
  SELECT * FROM ' || V_FULL ||
  CASE
    WHEN P_SAMPLE_PCT IS NULL THEN ''
    ELSE ' TABLESAMPLE BERNOULLI(' || P_SAMPLE_PCT || ')'
  END || '
),
AGG AS (
  SELECT
    COUNT(*) AS row_count,
    SUM(IFF(' || V_QCOL || ' IS NULL, 1, 0)) AS null_count,
    COUNT(DISTINCT ' || V_QCOL || ') AS distinct_count,
    MIN(TO_VARCHAR(' || V_QCOL || ')) AS min_varchar,
    MAX(TO_VARCHAR(' || V_QCOL || ')) AS max_varchar,
    MIN(LENGTH(TO_VARCHAR(' || V_QCOL || '))) AS min_len,
    MAX(LENGTH(TO_VARCHAR(' || V_QCOL || '))) AS max_len
  FROM SRC
),
TOP_VALUES AS (
  SELECT
    TO_VARCHAR(' || V_QCOL || ') AS v,
    COUNT(*) AS c
  FROM SRC
  WHERE ' || V_QCOL || ' IS NOT NULL
  GROUP BY 1
  ORDER BY c DESC
  LIMIT 20
)
SELECT OBJECT_CONSTRUCT(
  ''row_count'', row_count,
  ''null_count'', null_count,
  ''null_rate'', IFF(row_count=0, NULL, null_count::FLOAT/row_count),
  ''distinct_count'', distinct_count,
  ''distinct_rate_non_null'', IFF((row_count-null_count)=0, NULL, distinct_count::FLOAT/(row_count-null_count)),
  ''min_varchar'', min_varchar,
  ''max_varchar'', max_varchar,
  ''min_len'', min_len,
  ''max_len'', max_len,
  ''top_values'', (SELECT ARRAY_AGG(OBJECT_CONSTRUCT(''value'', v, ''count'', c)) FROM TOP_VALUES)
) AS METRICS
FROM AGG
';

  EXECUTE IMMEDIATE :V_SQL;

  SELECT METRICS
    INTO :V_METRICS
    FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

  INSERT INTO DB_DESIGN.PROFILE_RESULTS
    (RUN_ID, TARGET_DB, TARGET_SCHEMA, TARGET_TABLE,
     TARGET_COLUMN, AS_OF_AT, METRICS)
  SELECT
    :V_RUN_ID, :P_TARGET_DB, :P_TARGET_SCHEMA, :P_TARGET_TABLE,
    :V_COL_NAME, CURRENT_TIMESTAMP(), :V_METRICS;
END FOR;
```

重要な実装ポイント:
- RESULT_SCAN(LAST_QUERY_ID()): 動的SQLの結果を取得
- OBJECT_CONSTRUCT: メトリクスをJSON形式で構造化
- TOP_VALUES: 頻出値TOP20をARRAY_AGGで配列化
- TO_VARCHAR: 型に依存せず統一的に処理

### ステップ7: RUN正常終了
```sql
UPDATE DB_DESIGN.PROFILE_RUNS
   SET FINISHED_AT = CURRENT_TIMESTAMP(),
       STATUS      = 'SUCCEEDED'
 WHERE RUN_ID = :V_RUN_ID;

RETURN V_RUN_ID;
```

### ステップ8: 例外ハンドリング
```sql
EXCEPTION
  WHEN OTHER THEN
    UPDATE DB_DESIGN.PROFILE_RUNS
       SET FINISHED_AT = CURRENT_TIMESTAMP(),
           STATUS      = 'FAILED',
           NOTE =
             COALESCE(:P_NOTE, '') ||
             IFF(:P_NOTE IS NULL, '', ' | ') ||
             'ERROR(' || :SQLCODE || '): ' || :SQLERRM
     WHERE RUN_ID = :V_RUN_ID;
    RAISE;
END;
```
- SQLERRM / SQLCODE: エラーメッセージとコードを記録
- RAISE: 呼び出し元にエラーを伝播

---

## 運用

### 実行例1: 通常実行（全件スキャン）
```sql
CALL DB_DESIGN.PROFILE_TABLE(
  'GBPS253YS_DB',
  'PUBLIC',
  'CUSTOMERS',
  NULL  -- 全件スキャン
);
```

### 実行例2: サンプリング実行（1%）
```sql
CALL DB_DESIGN.PROFILE_TABLE(
  'ANALYTICS_DB',
  'STAGING',
  'LARGE_FACT_TABLE',
  1.0,  -- 1%サンプリング
  NULL,
  '20250102abc',  -- Git commit hash
  'exploratory profile for new table'
);
```

### 実行例3: 再実行（同一RUN_ID）
```sql
-- 初回実行
DECLARE V_RUN_ID STRING DEFAULT 'RUN-MANUAL-001';
BEGIN
  CALL DB_DESIGN.PROFILE_TABLE(
    'GBPS253YS_DB', 'PUBLIC', 'ORDERS',
    NULL, :V_RUN_ID, NULL, 'first run'
  );
END;

-- 再実行（エラー時など）
DECLARE V_RUN_ID STRING DEFAULT 'RUN-MANUAL-001';
BEGIN
  CALL DB_DESIGN.PROFILE_TABLE(
    'GBPS253YS_DB', 'PUBLIC', 'ORDERS',
    NULL, :V_RUN_ID, NULL, 'retry after fixing permissions'
  );
END;
```

### 結果の確認
```sql
-- 実行履歴
SELECT *
FROM DB_DESIGN.PROFILE_RUNS
WHERE TARGET_DB = 'GBPS253YS_DB'
  AND TARGET_SCHEMA = 'PUBLIC'
  AND TARGET_TABLE = 'CUSTOMERS'
ORDER BY STARTED_AT DESC;

-- カラム別メトリクス
SELECT
  TARGET_COLUMN,
  METRICS:row_count::INT AS row_count,
  METRICS:null_rate::FLOAT AS null_rate,
  METRICS:distinct_count::INT AS distinct_count,
  METRICS:min_varchar::STRING AS min_value,
  METRICS:max_varchar::STRING AS max_value
FROM DB_DESIGN.PROFILE_RESULTS
WHERE RUN_ID = 'RUN-01HX...'
ORDER BY TARGET_COLUMN;

-- 頻出値の確認
SELECT
  TARGET_COLUMN,
  f.value:value::STRING AS top_value,
  f.value:count::INT AS occurrence_count
FROM DB_DESIGN.PROFILE_RESULTS,
     LATERAL FLATTEN(INPUT => METRICS:top_values) f
WHERE RUN_ID = 'RUN-01HX...'
  AND TARGET_COLUMN = 'CUSTOMER_STATUS'
ORDER BY occurrence_count DESC;
```

### パフォーマンス考慮事項
- 大規模テーブル: P_SAMPLE_PCTを使用してコスト削減（推奨: 1.0～10.0）
- カラム数が多い場合: カラムごとにフルスキャンが発生するため、適切なウェアハウスサイズを選択
- 頻繁な実行: タスクスケジューリングで定期実行する場合、適切な間隔（週次/月次）を設定

---

## 関連ドキュメント

- [[design.PROFILE_ALL_TABLES]]: スキーマ全体の一括プロファイル（上位オーケストレーション）
- [[design.PROFILE_RUNS]]: プロファイル実行履歴テーブル
- [[design.PROFILE_RESULTS]]: カラム別メトリクス蓄積テーブル
- [[design.EXPORT_PROFILE_EVIDENCE_MD_VFINAL]]: プロファイル結果のMarkdown出力
- [[design.INGEST_VAULT_MD]]: S3からのMarkdown取り込み
- [[design.DOCS_OBSIDIAN]]: Cortex Agent用のドキュメント管理
