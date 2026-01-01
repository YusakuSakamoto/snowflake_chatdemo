---
type: other
schema_id: SCH_20251226180633
physical: PROFILE_ALL_TABLES
object_type: procedure
comment:
---

# SQL
```sql
CREATE OR REPLACE PROCEDURE DB_DESIGN.PROFILE_ALL_TABLES(
    P_TARGET_DB     STRING,
    P_TARGET_SCHEMA STRING,
    P_SAMPLE_PCT    FLOAT DEFAULT NULL,
    P_NOTE          STRING DEFAULT NULL
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  V_RESULTS   ARRAY;
  V_TBL_RS    RESULTSET;
  V_TBL_NAME  STRING;
  V_RUN_ID    STRING;

  V_SQL_LIST  STRING;
  V_SQL_CALL  STRING;

  V_QDB       STRING;
  V_QSC       STRING;
BEGIN
  V_RESULTS := ARRAY_CONSTRUCT();

  /* DB / SCHEMA を安全にクォート */
  V_QDB := '"' || REPLACE(P_TARGET_DB,'"','""') || '"';
  V_QSC := '''' || REPLACE(P_TARGET_SCHEMA,'''','''''') || '''';

  /* BASE TABLE 一覧を動的SQLで取得 */
  V_SQL_LIST := '
SELECT TABLE_NAME
FROM ' || V_QDB || '.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = ' || V_QSC || '
  AND TABLE_TYPE = ''BASE TABLE''
ORDER BY TABLE_NAME
';

  V_TBL_RS := (EXECUTE IMMEDIATE :V_SQL_LIST);

  /* テーブルごとに PROFILE_TABLE を CALL */
  FOR REC IN V_TBL_RS DO
    V_TBL_NAME := REC.TABLE_NAME;

    BEGIN
      V_SQL_CALL := '
CALL GBPS253YS_DB.DB_DESIGN.PROFILE_TABLE(
  ''' || REPLACE(P_TARGET_DB,'''','''''') || ''',
  ''' || REPLACE(P_TARGET_SCHEMA,'''','''''') || ''',
  ''' || REPLACE(V_TBL_NAME,'''','''''') || ''',
  ' || NVL(TO_VARCHAR(P_SAMPLE_PCT), 'NULL') || ',
  NULL,
  NULL,
  ''' || REPLACE(COALESCE(P_NOTE,'manual weekly all-tables run'),'''','''''') || '''
)
';

      EXECUTE IMMEDIATE :V_SQL_CALL;

      /* ★列名依存をやめて、1列目($1)でRUN_IDを取得 */
      SELECT $1::STRING
        INTO :V_RUN_ID
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

      V_RESULTS := ARRAY_APPEND(
        V_RESULTS,
        OBJECT_CONSTRUCT(
          'table', V_TBL_NAME,
          'run_id', V_RUN_ID,
          'status', 'SUCCEEDED'
        )
      );

    EXCEPTION
      WHEN OTHER THEN
        V_RESULTS := ARRAY_APPEND(
          V_RESULTS,
          OBJECT_CONSTRUCT(
            'table', V_TBL_NAME,
            'status', 'FAILED',
            'error', SQLERRM
          )
        );
    END;
  END FOR;

  RETURN OBJECT_CONSTRUCT(
    'target_db', P_TARGET_DB,
    'target_schema', P_TARGET_SCHEMA,
    'tables_processed', ARRAY_SIZE(V_RESULTS),
    'results', V_RESULTS
  );
END;
$$;
```

