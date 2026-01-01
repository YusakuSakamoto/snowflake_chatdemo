# [[design.PROFILE_COLUMN]]

## 概要

`[[DB_DESIGN.PROFILE_COLUMN]]` は、指定された単一カラムの品質プロファイルメトリクスを算出し、VARIANT形式で返却するプロシージャです。

- スキーマ: [[design.DB_DESIGN]] (SCH_20251226180633)
- オブジェクトタイプ: PROCEDURE
- 言語: SQL
- 実行モード: EXECUTE AS OWNER
- 戻り値: VARIANT (メトリクスJSON)

---

## 業務上の意味

### 目的
個別カラムのデータ品質メトリクス（行数、NULL率、ユニーク値数、最小/最大値、最小/最大長、頻出値TOP20など）を算出し、VARIANT型のJSON形式で返却します。このプロシージャは`PROFILE_TABLE`から呼び出され、カラムごとの詳細な統計情報を提供することで、データ品質分析の基礎データを構築します。

### 利用シーン
- PROFILE_TABLEからの自動呼び出し: テーブルプロファイル実行時のカラムメトリクス算出
- カラム品質調査: 特定のカラムに対する詳細なプロファイル分析
- サンプリング検証: 大規模テーブルに対するBERNOULLIサンプリングでのメトリクス算出
- 型非依存プロファイル: TO_VARCHAR変換により、数値/文字列/日付型を統一的に処理

---

## 設計上の位置づけ

### データフロー
```
PROFILE_ALL_TABLES (オーケストレーション層)
  ↓
PROFILE_TABLE (個別テーブル処理)
  ↓
PROFILE_COLUMN (カラムメトリクス算出) ← 本プロシージャ
  ↓ (VARIANT戻り値)
PROFILE_RESULTS (カラム別メトリクス記録)
```

### 他コンポーネントとの連携
- 上流: [[DB_DESIGN.PROFILE_TABLE]] (テーブルプロファイル実行・ループ呼び出し)
- 出力先: [[DB_DESIGN.PROFILE_RESULTS]] (METRICSカラムにVARIANT形式で保存)
- 連携先: [[DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL]] (メトリクス集計・出力)

---

## 設計方針

### 1. 型非依存の統一メトリクス
方針: TO_VARCHAR変換により、すべてのデータ型を統一的に処理  
理由:
- 数値型、文字列型、日付型など、型に関わらず同一のメトリクスを算出
- MIN/MAXは文字列ソート順で取得し、視覚的な確認を容易化
- LENGTH計算により、データ長の統計も取得可能

実装:
```sql
MIN(TO_VARCHAR(COLUMN)) AS min_varchar,
MAX(TO_VARCHAR(COLUMN)) AS max_varchar,
MIN(LENGTH(TO_VARCHAR(COLUMN))) AS min_len,
MAX(LENGTH(TO_VARCHAR(COLUMN))) AS max_len
```

### 2. サンプリングサポート
方針: P_SAMPLE_PCTパラメータでBERNOULLIサンプリングを実現  
理由:
- 大規模テーブル（数億行）でのプロファイル実行時間とコストを削減
- NULL率や頻出値の統計は、適切なサンプリング率（1%～10%）で精度を維持

実装:
```sql
CASE
  WHEN P_SAMPLE_PCT IS NULL THEN ''
  ELSE ' TABLESAMPLE BERNOULLI(' || P_SAMPLE_PCT || ')'
END
```

### 3. VARIANT形式での返却
方針: OBJECT_CONSTRUCTでJSON形式のメトリクスを返却  
理由:
- スキーマレス: メトリクス項目の追加・変更に柔軟に対応
- 構造化データ: 階層的なデータ（top_valuesなど）を自然に表現
- Snowflake標準: VARIANT型はSnowflakeの準構造化データ型として最適

実装:
```sql
OBJECT_CONSTRUCT(
  'row_count', row_count,
  'null_count', null_count,
  'null_rate', IFF(row_count=0, NULL, null_count::FLOAT/row_count),
  'distinct_count', distinct_count,
  'distinct_rate_non_null', IFF((row_count-null_count)=0, NULL, distinct_count::FLOAT/(row_count-null_count)),
  'min_varchar', min_varchar,
  'max_varchar', max_varchar,
  'min_len', min_len,
  'max_len', max_len,
  'top_values', (SELECT ARRAY_AGG(OBJECT_CONSTRUCT('value', v, 'count', c)) FROM TOP_VALUES)
)
```

### 4. 頻出値TOP20の取得
方針: GROUP BY + ORDER BY + LIMIT 20で頻出値を抽出  
理由:
- データ品質調査で重要な、値の分布状況を把握
- マスタデータの整合性確認（異常な値の検出）
- NULL値は除外し、非NULLの頻出値のみを記録

実装:
```sql
TOP_VALUES AS (
  SELECT
    TO_VARCHAR(COLUMN) AS v,
    COUNT(*) AS c
  FROM SRC
  WHERE COLUMN IS NOT NULL
  GROUP BY 1
  ORDER BY c DESC
  LIMIT 20
)
```

---

## パラメータ設計

| パラメータ名 | 型 | 必須 | デフォルト値 | 説明 |
|---|---|---|---|---|
| P_TARGET_DB | STRING | ✅ | - | プロファイル対象のデータベース名 |
| P_TARGET_SCHEMA | STRING | ✅ | - | プロファイル対象のスキーマ名 |
| P_TARGET_TABLE | STRING | ✅ | - | プロファイル対象のテーブル名 |
| P_TARGET_COLUMN | STRING | ✅ | - | プロファイル対象のカラム名 |
| P_SAMPLE_PCT | FLOAT | - | NULL | サンプリング割合（0.0～100.0）。NULLの場合は全件スキャン |

### パラメータ設計の背景
- P_TARGET_DB / P_TARGET_SCHEMA / P_TARGET_TABLE: 動的なフル修飾名構築に使用
- P_TARGET_COLUMN: ダブルクォートのエスケープ処理を経て、動的SQLに埋め込み
- P_SAMPLE_PCT: PROFILE_TABLEから受け渡され、カラムごとに同一のサンプリング率を適用

---

## 戻り値設計

### 戻り値: VARIANT (メトリクスJSON)
成功時にはカラムのメトリクスをVARIANT型のJSON形式で返却します。この戻り値は呼び出し元のPROFILE_TABLEでPROFILE_RESULTSテーブルに保存されます。

### メトリクス構造
```json
{
  "row_count": 10000,
  "null_count": 150,
  "null_rate": 0.015,
  "distinct_count": 8500,
  "distinct_rate_non_null": 0.863,
  "min_varchar": "2020-01-01",
  "max_varchar": "2025-12-31",
  "min_len": 10,
  "max_len": 10,
  "top_values": [
    {"value": "Active", "count": 3200},
    {"value": "Inactive", "count": 2800},
    {"value": "Pending", "count": 1500},
    ...
  ]
}
```

### メトリクス項目の説明
- `row_count`: カラムの行数（サンプリング適用後）
- `null_count`: NULL値の件数
- `null_rate`: NULL率（null_count / row_count）
- `distinct_count`: ユニークな値の数
- `distinct_rate_non_null`: 非NULL値におけるユニーク率（distinct_count / (row_count - null_count)）
- `min_varchar`: 最小値（文字列変換後）
- `max_varchar`: 最大値（文字列変換後）
- `min_len`: 最小文字列長
- `max_len`: 最大文字列長
- `top_values`: 頻出値TOP20（配列形式、NULL除外）

---

## 内部処理フロー

### ステップ1: フル修飾名生成
```sql
V_QDB  := '"' || REPLACE(P_TARGET_DB, '"', '""') || '"';
V_QSC  := '"' || REPLACE(P_TARGET_SCHEMA, '"', '""') || '"';
V_QTB  := '"' || REPLACE(P_TARGET_TABLE, '"', '""') || '"';
V_FULL := V_QDB || '.' || V_QSC || '.' || V_QTB;
```
- REPLACE(..., '"', '""'): ダブルクォートのエスケープ処理
- フル修飾名: `"DB"."SCHEMA"."TABLE"` の形式で構築

### ステップ2: カラム名のエスケープ
```sql
V_QCOL := '"' || REPLACE(P_TARGET_COLUMN, '"', '""') || '"';
```
- カラム名にダブルクォートが含まれる場合のエスケープ処理
- 動的SQLインジェクション対策

### ステップ3: 動的SQL構築
```sql
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
```

重要な実装ポイント:
- CTE構造: SRC（ソースデータ）→ AGG（集計メトリクス）→ TOP_VALUES（頻出値）
- IFF関数: ゼロ除算回避（row_count=0の場合、null_rateはNULL）
- ARRAY_AGG: 頻出値を配列形式でネスト
- シングルクォートのエスケープ: 動的SQL内で`''`として表現

### ステップ4: 動的SQL実行
```sql
EXECUTE IMMEDIATE :V_SQL;
```
- プレースホルダ変数（:V_SQL）を使用して動的SQLを実行

### ステップ5: 結果取得
```sql
SELECT METRICS
  INTO :V_METRICS
  FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```
- RESULT_SCAN: 直前のクエリ結果を取得
- LAST_QUERY_ID(): 直前に実行されたクエリのIDを取得
- INTO: 結果をVARIANT型変数に格納

### ステップ6: VARIANT返却
```sql
RETURN V_METRICS;
```
- 呼び出し元（[[design.PROFILE_TABLE]]）にVARIANT形式のメトリクスを返却

---

## 運用

### 直接実行例1: 通常実行（全件スキャン）
```sql
DECLARE V_RESULT VARIANT;
BEGIN
  CALL DB_DESIGN.PROFILE_COLUMN(
    'GBPS253YS_DB',
    'PUBLIC',
    'CUSTOMERS',
    'CUSTOMER_NAME',
    NULL  -- 全件スキャン
  ) INTO :V_RESULT;
  
  -- メトリクス確認
  SELECT :V_RESULT AS metrics;
END;
```

### 直接実行例2: サンプリング実行（1%）
```sql
DECLARE V_RESULT VARIANT;
BEGIN
  CALL DB_DESIGN.PROFILE_COLUMN(
    'ANALYTICS_DB',
    'STAGING',
    'LARGE_FACT_TABLE',
    'TRANSACTION_DATE',
    1.0  -- 1%サンプリング
  ) INTO :V_RESULT;
  
  -- NULL率確認
  SELECT :V_RESULT:null_rate::FLOAT AS null_rate;
END;
```

### PROFILE_TABLEからの呼び出し（実際の利用形態）
```sql
-- PROFILE_TABLEのカラムループ内で実行
FOR REC IN V_COL_RS DO
  V_COL_NAME := REC.COLUMN_NAME;
  
  -- PROFILE_COLUMN呼び出し
  CALL DB_DESIGN.PROFILE_COLUMN(
    P_TARGET_DB,
    P_TARGET_SCHEMA,
    P_TARGET_TABLE,
    :V_COL_NAME,
    P_SAMPLE_PCT
  ) INTO :V_METRICS;
  
  -- PROFILE_RESULTSに保存
  INSERT INTO DB_DESIGN.PROFILE_RESULTS
    (RUN_ID, TARGET_DB, TARGET_SCHEMA, TARGET_TABLE,
     TARGET_COLUMN, AS_OF_AT, METRICS)
  VALUES
    (:V_RUN_ID, :P_TARGET_DB, :P_TARGET_SCHEMA, :P_TARGET_TABLE,
     :V_COL_NAME, CURRENT_TIMESTAMP(), :V_METRICS);
END FOR;
```

### メトリクスの解析例
```sql
-- PROFILE_RESULTSからメトリクス抽出
DECLARE V_RESULT VARIANT;
BEGIN
  SELECT METRICS INTO :V_RESULT
  FROM DB_DESIGN.PROFILE_RESULTS
  WHERE RUN_ID = 'RUN-01HX...'
    AND TARGET_COLUMN = 'ORDER_DATE'
  LIMIT 1;
  
  -- メトリクスパース
  SELECT
    :V_RESULT:row_count::INT AS row_count,
    :V_RESULT:null_rate::FLOAT AS null_rate,
    :V_RESULT:distinct_count::INT AS distinct_count,
    :V_RESULT:min_varchar::STRING AS min_value,
    :V_RESULT:max_varchar::STRING AS max_value;
  
  -- 頻出値抽出
  SELECT
    f.value:value::STRING AS top_value,
    f.value:count::INT AS occurrence_count
  FROM TABLE(FLATTEN(INPUT => :V_RESULT:top_values)) f
  ORDER BY occurrence_count DESC;
END;
```

### パフォーマンス考慮事項
- 大規模テーブル: サンプリング率1.0～10.0を推奨（全件スキャンはコスト高）
- カラムごとの実行: PROFILE_TABLEからのループ呼び出しで、カラム数に比例した実行時間
- TOP_VALUES算出: LIMIT 20により、頻出値の計算コストを抑制
- 適切なウェアハウスサイズ: カラム数とテーブルサイズに応じて、ウェアハウスサイズを調整

---

## 関連ドキュメント

- [[design.PROFILE_TABLE]]: カラムプロファイルを呼び出す上位プロシージャ
- [[design.PROFILE_RESULTS]]: メトリクスを保存するテーブル（METRICSカラムにVARIANT保存）
- [[design.PROFILE_RUNS]]: プロファイル実行履歴テーブル
- [[design.PROFILE_ALL_TABLES]]: スキーマ全体のプロファイル実行（最上位オーケストレーション）
- [[design.EXPORT_PROFILE_EVIDENCE_MD_VFINAL]]: プロファイル結果のMarkdown出力
