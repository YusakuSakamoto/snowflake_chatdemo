---
type: other
schema_id: SCH_20251226180633
physical: PROFILE_TABLE
object_type: procedure
comment:
---

# SQL
```sql
CREATE OR REPLACE PROCEDURE DB_DESIGN.PROFILE_TABLE(
    P_TARGET_DB     STRING,
    P_TARGET_SCHEMA STRING,
    P_TARGET_TABLE  STRING,
    P_SAMPLE_PCT    FLOAT DEFAULT NULL,
    P_RUN_ID        STRING DEFAULT NULL,
    P_GIT_COMMIT    STRING DEFAULT NULL,
    P_NOTE          STRING DEFAULT NULL
)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  V_RUN_ID    STRING;
  V_STARTED   TIMESTAMP_LTZ;

  V_QDB   STRING;
  V_QSC   STRING;
  V_QTB   STRING;
  V_FULL  STRING;

  V_COL_RS   RESULTSET;
  V_COL_NAME STRING;

  V_QCOL    STRING;
  V_SQL     STRING;
  V_METRICS VARIANT;
  V_SQLC    STRING;
BEGIN
  /* ========== RUN 初期化 ========== */
  V_STARTED := CURRENT_TIMESTAMP();
  V_RUN_ID  := COALESCE(P_RUN_ID, 'RUN-' || UUID_STRING());

  /* ========== RUN 登録（冪等） ========== */
  MERGE INTO DB_DESIGN.PROFILE_RUNS T
  USING (
    SELECT
      :V_RUN_ID        AS RUN_ID,
      :P_TARGET_DB     AS TARGET_DB,
      :P_TARGET_SCHEMA AS TARGET_SCHEMA,
      :P_TARGET_TABLE  AS TARGET_TABLE,
      :P_SAMPLE_PCT    AS SAMPLE_PCT,
      :V_STARTED       AS STARTED_AT,
      'RUNNING'        AS STATUS,
      CURRENT_WAREHOUSE() AS WAREHOUSE_NAME,
      CURRENT_ROLE()      AS ROLE_NAME,
      :P_GIT_COMMIT    AS GIT_COMMIT,
      :P_NOTE          AS NOTE
  ) S
  ON T.RUN_ID = S.RUN_ID
  WHEN MATCHED THEN
    UPDATE SET
      STARTED_AT     = S.STARTED_AT,
      FINISHED_AT    = NULL,
      STATUS         = 'RUNNING',
      SAMPLE_PCT     = S.SAMPLE_PCT,
      WAREHOUSE_NAME = S.WAREHOUSE_NAME,
      ROLE_NAME      = S.ROLE_NAME,
      GIT_COMMIT     = S.GIT_COMMIT,
      NOTE           = S.NOTE
  WHEN NOT MATCHED THEN
    INSERT (
      RUN_ID, TARGET_DB, TARGET_SCHEMA, TARGET_TABLE,
      SAMPLE_PCT, STARTED_AT, STATUS,
      WAREHOUSE_NAME, ROLE_NAME, GIT_COMMIT, NOTE
    )
    VALUES (
      S.RUN_ID, S.TARGET_DB, S.TARGET_SCHEMA, S.TARGET_TABLE,
      S.SAMPLE_PCT, S.STARTED_AT, S.STATUS,
      S.WAREHOUSE_NAME, S.ROLE_NAME, S.GIT_COMMIT, S.NOTE
    );

  /* ========== 再実行対策：既存結果削除 ========== */
  DELETE FROM DB_DESIGN.PROFILE_RESULTS
   WHERE RUN_ID = :V_RUN_ID;

  /* ========== 対象テーブル（フル修飾） ========== */
  V_QDB  := '"' || REPLACE(P_TARGET_DB, '"', '""') || '"';
  V_QSC  := '"' || REPLACE(P_TARGET_SCHEMA, '"', '""') || '"';
  V_QTB  := '"' || REPLACE(P_TARGET_TABLE, '"', '""') || '"';
  V_FULL := V_QDB || '.' || V_QSC || '.' || V_QTB;

  /* ========== 列一覧取得 ========== */
  V_SQLC := '
    SELECT COLUMN_NAME
    FROM ' || V_QDB || '.INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ?
      AND TABLE_NAME   = ?
    ORDER BY ORDINAL_POSITION
  ';
  V_COL_RS := (EXECUTE IMMEDIATE :V_SQLC USING (P_TARGET_SCHEMA, P_TARGET_TABLE));

  /* ========== 列ごとのメトリクス算出 ========== */
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

  /* ========== RUN 正常終了 ========== */
  UPDATE DB_DESIGN.PROFILE_RUNS
     SET FINISHED_AT = CURRENT_TIMESTAMP(),
         STATUS      = 'SUCCEEDED'
   WHERE RUN_ID = :V_RUN_ID;

  RETURN V_RUN_ID;

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
$$;
```

