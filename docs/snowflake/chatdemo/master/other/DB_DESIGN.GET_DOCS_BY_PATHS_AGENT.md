---
type: other
schema_id: SCH_20251226180633
physical: GET_DOCS_BY_PATHS_AGENT
object_type: PROCEDURE
comment:
---

# SQL

````sql
CREATE OR REPLACE PROCEDURE DB_DESIGN.GET_DOCS_BY_PATHS_AGENT(
  PATHS_JSON STRING,
  MAX_CHARS  STRING
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  v_paths     VARIANT;
  v_max_chars NUMBER;
  v_docs      VARIANT;
  v_missing   VARIANT;
BEGIN
  v_max_chars := TRY_TO_NUMBER(MAX_CHARS);

  IF (PATHS_JSON IS NULL OR PATHS_JSON = '') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT('error', 'PATHS_JSON is required (JSON array string)'));
  END IF;

  v_paths := PARSE_JSON(PATHS_JSON);
  IF (TYPEOF(v_paths) <> 'ARRAY') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT(
      'error',
      'PATHS_JSON must be a JSON array string, e.g. ["design/design.DB_DESIGN.md"]'
    ));
  END IF;

  -- (A) docs（存在するもの）
  WITH req AS (
    SELECT VALUE::STRING AS REQ_PATH
    FROM TABLE(FLATTEN(INPUT => :v_paths))
  ),
  hit AS (
    SELECT
      r.REQ_PATH,
      d.DOC_ID, d.PATH, d.FOLDER, d.SCOPE, d.FILE_TYPE, d.RUN_DATE,
      d.TARGET_SCHEMA, d.TARGET_TABLE, d.TARGET_COLUMN,
      d.UPDATED_AT,
      IFF(:v_max_chars IS NULL, d.CONTENT, LEFT(d.CONTENT, :v_max_chars)) AS CONTENT_TRIM
    FROM req r
    LEFT JOIN DB_DESIGN.DOCS_OBSIDIAN_V d
      ON d.PATH = r.REQ_PATH
  )
  SELECT COALESCE(
           ARRAY_AGG(
             OBJECT_CONSTRUCT(
               'path', PATH,
               'doc_id', DOC_ID,
               'folder', FOLDER,
               'scope', SCOPE,
               'file_type', FILE_TYPE,
               'run_date', RUN_DATE,
               'target_schema', TARGET_SCHEMA,
               'target_table', TARGET_TABLE,
               'target_column', TARGET_COLUMN,
               'updated_at', UPDATED_AT,
               'content', CONTENT_TRIM
             )
           ) WITHIN GROUP (ORDER BY REQ_PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_docs
  FROM hit
  WHERE DOC_ID IS NOT NULL;

  -- (B) missing（見つからないもの）
  WITH req AS (
    SELECT VALUE::STRING AS REQ_PATH
    FROM TABLE(FLATTEN(INPUT => :v_paths))
  ),
  hit AS (
    SELECT
      r.REQ_PATH,
      d.DOC_ID
    FROM req r
    LEFT JOIN DB_DESIGN.DOCS_OBSIDIAN_V d
      ON d.PATH = r.REQ_PATH
  )
  SELECT COALESCE(
           ARRAY_AGG(REQ_PATH) WITHIN GROUP (ORDER BY REQ_PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_missing
  FROM hit
  WHERE DOC_ID IS NULL;

  RETURN TO_VARIANT(OBJECT_CONSTRUCT(
    'count', ARRAY_SIZE(v_docs),
    'docs', v_docs,
    'missing_count', ARRAY_SIZE(v_missing),
    'missing_paths', v_missing
  ));
END;
$$;
````

