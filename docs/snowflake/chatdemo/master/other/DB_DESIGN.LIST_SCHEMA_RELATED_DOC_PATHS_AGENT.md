---
type: other
schema_id: SCH_20251226180633
physical: LIST_SCHEMA_RELATED_DOC_PATHS_AGENT
object_type: PROCEDURE
comment:
---

# SQL

````sql
CREATE OR REPLACE PROCEDURE DB_DESIGN.LIST_SCHEMA_RELATED_DOC_PATHS_AGENT(
  TARGET_SCHEMA STRING,
  MAX_TABLES    STRING
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  v_schema         STRING;
  v_max_tables     NUMBER;

  v_base_candidates VARIANT;
  v_base_paths      VARIANT;

  v_design_paths    VARIANT;  -- ★追加：design/<SCHEMA>/design.*.md を拾う

  v_tables_paths    VARIANT;
  v_ext_paths       VARIANT;
  v_views_paths     VARIANT;
  v_other_paths     VARIANT;  -- ★修正：other（単数）に合わせる

  v_all_paths       VARIANT;
  v_paths_dedup     VARIANT;
BEGIN
  v_schema := TARGET_SCHEMA;
  v_max_tables := COALESCE(TRY_TO_NUMBER(MAX_TABLES), 2000);

  IF (v_schema IS NULL OR v_schema = '') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT('error', 'TARGET_SCHEMA is required'));
  END IF;

  -- (A) 上位設計（存在するものだけ残す）
  v_base_candidates := ARRAY_CONSTRUCT(
    'README_DB_DESIGN.md',
    'design/design.DB_DESIGN.md',
    'design/design.' || v_schema || '.md'
  );

  WITH cand AS (
    SELECT VALUE::STRING AS path
    FROM TABLE(FLATTEN(INPUT => :v_base_candidates))
    WHERE VALUE IS NOT NULL
  )
  SELECT COALESCE(
           ARRAY_AGG(c.path) WITHIN GROUP (ORDER BY c.path),
           ARRAY_CONSTRUCT()
         )
    INTO :v_base_paths
  FROM cand c
  JOIN DB_DESIGN.V_DOCS_OBSIDIAN d
    ON d.PATH = c.path;

  -- (A2) ★追加：design/<SCHEMA>/design.*.md を列挙（「リンク解決」はせず、実在PATHを構文で拾う）
  -- 例: design/DB_DESIGN/design.PROFILE_RUNS.md
  SELECT COALESCE(
           ARRAY_AGG(PATH) WITHIN GROUP (ORDER BY PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_design_paths
  FROM (
    SELECT d.PATH
    FROM DB_DESIGN.V_DOCS_OBSIDIAN d
    WHERE d.PATH LIKE ('design/' || :v_schema || '/design.%')
      AND d.PATH LIKE '%.md'
    QUALIFY ROW_NUMBER() OVER (ORDER BY d.PATH) <= :v_max_tables
  );

  -- (B) master/tables
  SELECT COALESCE(
           ARRAY_AGG(PATH) WITHIN GROUP (ORDER BY PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_tables_paths
  FROM (
    SELECT d.PATH
    FROM DB_DESIGN.V_DOCS_OBSIDIAN d
    WHERE d.PATH LIKE 'master/tables/%'
      AND d.TARGET_SCHEMA = :v_schema
    QUALIFY ROW_NUMBER() OVER (ORDER BY d.PATH) <= :v_max_tables
  );

  -- (C) master/externaltables
  SELECT COALESCE(
           ARRAY_AGG(PATH) WITHIN GROUP (ORDER BY PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_ext_paths
  FROM (
    SELECT d.PATH
    FROM DB_DESIGN.V_DOCS_OBSIDIAN d
    WHERE d.PATH LIKE 'master/externaltables/%'
      AND d.TARGET_SCHEMA = :v_schema
    QUALIFY ROW_NUMBER() OVER (ORDER BY d.PATH) <= :v_max_tables
  );

  -- (D) master/views
  SELECT COALESCE(
           ARRAY_AGG(PATH) WITHIN GROUP (ORDER BY PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_views_paths
  FROM (
    SELECT d.PATH
    FROM DB_DESIGN.V_DOCS_OBSIDIAN d
    WHERE d.PATH LIKE 'master/views/%'
      AND d.TARGET_SCHEMA = :v_schema
    QUALIFY ROW_NUMBER() OVER (ORDER BY d.PATH) <= :v_max_tables
  );

  -- (E) ★修正：master/other（単数）に合わせる（READMEと整合）
  SELECT COALESCE(
           ARRAY_AGG(PATH) WITHIN GROUP (ORDER BY PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_other_paths
  FROM (
    SELECT d.PATH
    FROM DB_DESIGN.V_DOCS_OBSIDIAN d
    WHERE d.PATH LIKE 'master/other/%'
      AND d.TARGET_SCHEMA = :v_schema
    QUALIFY ROW_NUMBER() OVER (ORDER BY d.PATH) <= :v_max_tables
  );

  -- (F) 結合して distinct & sort
  v_all_paths := ARRAY_CAT(
                  ARRAY_CAT(
                    ARRAY_CAT(
                      ARRAY_CAT(v_base_paths, v_design_paths),
                      ARRAY_CAT(v_tables_paths, v_ext_paths)
                    ),
                    v_views_paths
                  ),
                  v_other_paths
                );

  WITH p AS (
    SELECT VALUE::STRING AS path
    FROM TABLE(FLATTEN(INPUT => :v_all_paths))
    WHERE VALUE IS NOT NULL
  )
  SELECT COALESCE(
           ARRAY_AGG(path) WITHIN GROUP (ORDER BY path),
           ARRAY_CONSTRUCT()
         )
    INTO :v_paths_dedup
  FROM (SELECT DISTINCT path FROM p);

  RETURN TO_VARIANT(OBJECT_CONSTRUCT(
    'target_schema', v_schema,
    'count', ARRAY_SIZE(v_paths_dedup),
    'paths', v_paths_dedup,
    'paths_json', TO_JSON(v_paths_dedup)
  ));
END;
$$;
````

