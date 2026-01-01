---
type: other
schema_id: SCH_20251226180633
physical: EXPORT_PROFILE_EVIDENCE_MD_VFINAL
object_type: procedure
comment:
---

# SQL

```sql
CREATE OR REPLACE PROCEDURE DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL(
    P_SOURCE_DB         VARCHAR,
    P_SOURCE_SCHEMA     VARCHAR,
    P_SOURCE_VIEW       VARCHAR,
    P_TARGET_DB         VARCHAR,
    P_RUN_DATE          VARCHAR,   -- YYYY-MM-DD
    P_VAULT_PREFIX      VARCHAR,   -- reviews/profiles
    P_TARGET_SCHEMA     VARCHAR    -- NULL = all
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
  -- view
  v_view_fqn           STRING;

  -- sql
  v_sql                STRING;

  -- paths
  v_path_md            STRING;
  v_path_raw_prefix    STRING;
  v_path_err           STRING;

  -- counters
  v_total              NUMBER;
  v_i                  NUMBER;
  v_ok                 NUMBER DEFAULT 0;
  v_failed             NUMBER DEFAULT 0;

  -- current table
  v_schema             STRING;
  v_table              STRING;
  v_schema_esc         STRING;
  v_table_esc          STRING;

  -- literals
  v_target_db_esc      STRING;
  v_schema_lit         STRING;

  -- raw file info
  v_raw_rel_prefix     STRING;
  v_raw_rel_file       STRING;

  -- return json
  v_target_db_json     STRING;
  v_run_date_json      STRING;
  v_vault_prefix_json  STRING;
BEGIN
  ------------------------------------------------------------------
  -- init
  ------------------------------------------------------------------
  v_view_fqn := P_SOURCE_DB || '.' || P_SOURCE_SCHEMA || '.' || P_SOURCE_VIEW;

  v_target_db_esc := REPLACE(P_TARGET_DB, '''', '''''');

  v_schema_lit :=
    CASE
      WHEN P_TARGET_SCHEMA IS NULL THEN 'NULL'
      ELSE '''' || REPLACE(P_TARGET_SCHEMA, '''', '''''') || ''''
    END;

  v_target_db_json    := REPLACE(P_TARGET_DB, '"', '\\"');
  v_run_date_json     := REPLACE(P_RUN_DATE,  '"', '\\"');
  v_vault_prefix_json := REPLACE(P_VAULT_PREFIX, '"', '\\"');

  ------------------------------------------------------------------
  -- target tables
  ------------------------------------------------------------------
  EXECUTE IMMEDIATE '
    CREATE OR REPLACE TEMP TABLE TMP_TARGETS (
      TARGET_SCHEMA STRING,
      TARGET_TABLE  STRING
    )';

  v_sql :=
    'INSERT INTO TMP_TARGETS
     SELECT DISTINCT TARGET_SCHEMA, TARGET_TABLE
     FROM ' || v_view_fqn || '
     WHERE TARGET_DB = ''' || v_target_db_esc || '''
       AND (' || v_schema_lit || ' IS NULL OR TARGET_SCHEMA = ' || v_schema_lit || ')';

  EXECUTE IMMEDIATE v_sql;

  SELECT COUNT(*) INTO v_total FROM TMP_TARGETS;

  ------------------------------------------------------------------
  -- loop
  ------------------------------------------------------------------
  v_i := 1;

  WHILE (v_i <= v_total) DO
    -- pick 1 table
    v_sql :=
      'CREATE OR REPLACE TEMP TABLE TMP_ONE AS
       SELECT TARGET_SCHEMA, TARGET_TABLE
       FROM (
         SELECT TARGET_SCHEMA, TARGET_TABLE,
                ROW_NUMBER() OVER (ORDER BY TARGET_SCHEMA, TARGET_TABLE) AS RN
         FROM TMP_TARGETS
       )
       WHERE RN = ' || TO_VARCHAR(v_i);

    EXECUTE IMMEDIATE v_sql;

    SELECT TARGET_SCHEMA, TARGET_TABLE
      INTO v_schema, v_table
    FROM TMP_ONE;

    v_schema_esc := REPLACE(v_schema, '''', '''''');
    v_table_esc  := REPLACE(v_table,  '''', '''''');

    -- paths
    v_path_md :=
      '@DB_DESIGN.OBSIDIAN_VAULT_STAGE/' || P_VAULT_PREFIX || '/' || P_RUN_DATE || '/'
      || v_schema || '/' || v_table || '.md';

    v_path_raw_prefix :=
      '@DB_DESIGN.OBSIDIAN_VAULT_STAGE/' || P_VAULT_PREFIX || '/' || P_RUN_DATE || '/'
      || v_schema || '/' || v_table || '.raw.json';

    v_path_err :=
      '@DB_DESIGN.OBSIDIAN_VAULT_STAGE/' || P_VAULT_PREFIX || '/' || P_RUN_DATE || '/'
      || v_schema || '/' || v_table || '.error.md';

    v_raw_rel_prefix :=
      P_VAULT_PREFIX || '/' || P_RUN_DATE || '/' || v_schema || '/' || v_table || '.raw.json';

    v_raw_rel_file := v_raw_rel_prefix || '_0_0_0';

    ----------------------------------------------------------------
    -- per table (continue on error)
    ----------------------------------------------------------------
    BEGIN
      --------------------------------------------------------------
      -- summary md
      --------------------------------------------------------------
      EXECUTE IMMEDIATE 'CREATE OR REPLACE TEMP TABLE TMP_MD (LINE STRING)';

      v_sql :=
'INSERT INTO TMP_MD (LINE)
SELECT LINE
FROM (
  WITH base AS (
    SELECT *
    FROM ' || v_view_fqn || '
    WHERE TARGET_DB     = ''' || v_target_db_esc || '''
      AND TARGET_SCHEMA = ''' || v_schema_esc || '''
      AND TARGET_TABLE  = ''' || v_table_esc || '''
  ),
  t AS (
    SELECT
      ANY_VALUE(TARGET_DB) AS TARGET_DB,
      ANY_VALUE(TARGET_SCHEMA) AS TARGET_SCHEMA,
      ANY_VALUE(TARGET_TABLE) AS TARGET_TABLE,
      MAX(AS_OF_AT) AS AS_OF_AT,
      MAX(RUN_ID) AS RUN_ID,
      MAX(TRY_TO_NUMBER(TO_VARCHAR(METRICS:"row_count"))) AS ROW_COUNT
    FROM base
  ),
  c AS (
    SELECT
      TARGET_COLUMN AS COL,
      TRY_TO_DOUBLE(TO_VARCHAR(METRICS:"null_rate")) AS NULL_RATE,
      TRY_TO_NUMBER(TO_VARCHAR(METRICS:"distinct_count")) AS DISTINCT_CNT
    FROM base
  )
  SELECT LINE
  FROM (
    SELECT 10, ''---'' FROM t
    UNION ALL SELECT 20, ''type: profile_evidence'' FROM t
    UNION ALL SELECT 30, ''target_db: '' || TARGET_DB FROM t
    UNION ALL SELECT 40, ''target_schema: '' || TARGET_SCHEMA FROM t
    UNION ALL SELECT 50, ''target_table: '' || TARGET_TABLE FROM t
    UNION ALL SELECT 60, ''as_of_at: '' || TO_VARCHAR(AS_OF_AT, ''YYYY-MM-DD"T"HH24:MI:SS'') FROM t
    UNION ALL SELECT 70, ''run_id: '' || COALESCE(RUN_ID, ''null'') FROM t
    UNION ALL SELECT 80, ''row_count: '' || COALESCE(TO_VARCHAR(ROW_COUNT), ''null'') FROM t
    UNION ALL SELECT 90, ''generated_on: ' || REPLACE(P_RUN_DATE, '''', '''''') || ''' FROM t
    UNION ALL SELECT 100, ''---'' FROM t
    UNION ALL SELECT 110, '' '' FROM t

    UNION ALL SELECT 120, ''# Profile Evidence: '' || TARGET_SCHEMA || ''.'' || TARGET_TABLE FROM t
    UNION ALL SELECT 130, '' '' FROM t

    UNION ALL SELECT 200, ''## Raw metrics'' FROM t
    UNION ALL SELECT 210, ''- Prefix: `' || REPLACE(v_raw_rel_prefix, '''', '''''') || '`'' FROM t
    UNION ALL SELECT 220, ''- File: `' || REPLACE(v_raw_rel_file, '''', '''''') || '`'' FROM t
    UNION ALL SELECT 230, '' '' FROM t

    UNION ALL SELECT 300, ''## Columns (summary)'' FROM t
    UNION ALL SELECT 310, ''| column | null_rate | distinct_count |'' FROM t
    UNION ALL SELECT 320, ''|---|---:|---:|'' FROM t

    UNION ALL
    SELECT
      400 + ROW_NUMBER() OVER (ORDER BY COL),
      ''| `'' || COL || ''` | '' ||
      COALESCE(TO_VARCHAR(ROUND(NULL_RATE * 100, 2)) || ''%'', ''null'') || '' | '' ||
      COALESCE(TO_VARCHAR(DISTINCT_CNT), ''null'') || '' |''
    FROM c
  ) x(LINE_NO, LINE)
  ORDER BY 1
)';

      EXECUTE IMMEDIATE v_sql;

      EXECUTE IMMEDIATE
'COPY INTO ' || v_path_md || '
 FROM TMP_MD
 FILE_FORMAT = (
   TYPE = CSV
   FIELD_DELIMITER = ''\u0001''
   RECORD_DELIMITER = ''\n''
   COMPRESSION = NONE
 )
 HEADER = FALSE
 SINGLE = TRUE
 OVERWRITE = TRUE
 INCLUDE_QUERY_ID = FALSE';

      --------------------------------------------------------------
      -- raw json
      --------------------------------------------------------------
      EXECUTE IMMEDIATE 'CREATE OR REPLACE TEMP TABLE TMP_RAW (LINE STRING)';

      v_sql :=
'INSERT INTO TMP_RAW (LINE)
SELECT TO_JSON(
  OBJECT_CONSTRUCT(
    ''target_db'', ''' || v_target_db_esc || ''',
    ''target_schema'', ''' || v_schema_esc || ''',
    ''target_table'', ''' || v_table_esc || ''',
    ''run_date'', ''' || REPLACE(P_RUN_DATE, '''', '''''') || ''',
    ''metrics'', ARRAY_AGG(
      OBJECT_CONSTRUCT(
        ''column'', TARGET_COLUMN,
        ''as_of_at'', AS_OF_AT,
        ''run_id'', RUN_ID,
        ''metrics'', METRICS
      )
    )
  )
)
FROM ' || v_view_fqn || '
WHERE TARGET_DB     = ''' || v_target_db_esc || '''
  AND TARGET_SCHEMA = ''' || v_schema_esc || '''
  AND TARGET_TABLE  = ''' || v_table_esc || '''';

      EXECUTE IMMEDIATE v_sql;

      EXECUTE IMMEDIATE
'COPY INTO ' || v_path_raw_prefix || '
 FROM TMP_RAW
 FILE_FORMAT = (
   TYPE = CSV
   FIELD_DELIMITER = ''\u0001''
   RECORD_DELIMITER = ''\n''
   COMPRESSION = NONE
 )
 HEADER = FALSE
 SINGLE = TRUE
 OVERWRITE = TRUE
 INCLUDE_QUERY_ID = FALSE';

      v_ok := v_ok + 1;

    EXCEPTION
      WHEN OTHER THEN
        v_failed := v_failed + 1;
    END;

    v_i := v_i + 1;
  END WHILE;

  RETURN PARSE_JSON(
    '{' ||
      '"status":"OK",' ||
      '"exported_ok":' || v_ok || ',' ||
      '"exported_failed":' || v_failed || ',' ||
      '"raw_file_suffix":"_0_0_0",' ||
      '"target_db":"' || v_target_db_json || '",' ||
      '"run_date":"'  || v_run_date_json  || '",' ||
      '"vault_prefix":"' || v_vault_prefix_json || '"' ||
    '}'
  );
END;
$$;
```
