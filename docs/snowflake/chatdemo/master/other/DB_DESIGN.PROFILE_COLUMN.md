---
type: other
schema_id: SCH_20251226180633
physical: PROFILE_COLUMN
object_type: procedure
comment:
---

# SQL

```sql
CREATE OR REPLACE PROCEDURE DB_DESIGN.PROFILE_COLUMN(
    P_TARGET_DB     STRING,
    P_TARGET_SCHEMA STRING,
    P_TARGET_TABLE  STRING,
    P_TARGET_COLUMN STRING,
    P_SAMPLE_PCT    FLOAT DEFAULT NULL
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  V_QDB   STRING;
  V_QSC   STRING;
  V_QTB   STRING;
  V_FULL  STRING;
  V_QCOL  STRING;

  V_SQL     STRING;
  V_METRICS VARIANT;
BEGIN
  /* フル修飾テーブル */
  V_QDB  := '"' || REPLACE(P_TARGET_DB, '"', '""') || '"';
  V_QSC  := '"' || REPLACE(P_TARGET_SCHEMA, '"', '""') || '"';
  V_QTB  := '"' || REPLACE(P_TARGET_TABLE, '"', '""') || '"';
  V_FULL := V_QDB || '.' || V_QSC || '.' || V_QTB;

  V_QCOL := '"' || REPLACE(P_TARGET_COLUMN, '"', '""') || '"';

  /* 動的SQL生成 */
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

  /* 実行 */
  EXECUTE IMMEDIATE :V_SQL;

  /* 結果をVARIANTで取得 */
  SELECT METRICS
    INTO :V_METRICS
    FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

  RETURN V_METRICS;
END;
$$;
```

