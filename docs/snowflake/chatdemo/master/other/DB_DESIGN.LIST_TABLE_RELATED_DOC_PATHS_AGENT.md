---
type: other
schema_id: SCH_20251226180633
physical: LIST_TABLE_RELATED_DOC_PATHS_AGENT
object_type: PROCEDURE
comment:
---

# SQL

````sql
CREATE OR REPLACE PROCEDURE DB_DESIGN.LIST_TABLE_RELATED_DOC_PATHS_AGENT(
  TARGET_SCHEMA    STRING,
  TARGET_TABLE     STRING,
  INCLUDE_COLUMNS  STRING, -- "true"/"false"
  MAX_COLUMNS      STRING
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  v_schema      STRING;
  v_table       STRING;
  v_inc_cols    BOOLEAN;
  v_max_cols    NUMBER;

  v_base_candidates VARIANT;  -- 候補（存在しないものも含む）
  v_base_paths      VARIANT;  -- 存在するものだけ
  v_col_paths       VARIANT;
  v_all_paths       VARIANT;
  v_paths_dedup     VARIANT;
BEGIN
  v_schema := TARGET_SCHEMA;
  v_table  := TARGET_TABLE;
  v_inc_cols := IFF(UPPER(COALESCE(INCLUDE_COLUMNS,'FALSE')) IN ('TRUE','1','YES','Y'), TRUE, FALSE);
  v_max_cols := COALESCE(TRY_TO_NUMBER(MAX_COLUMNS), 5000);

  IF (v_schema IS NULL OR v_schema = '') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT('error', 'TARGET_SCHEMA is required'));
  END IF;
  IF (v_table IS NULL OR v_table = '') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT('error', 'TARGET_TABLE is required'));
  END IF;

  -- (A) base候補：tables / externaltables / views / others を候補にする
  -- ここでの TARGET_TABLE は「物理名相当（TABLE/VIEW/OTHERの物理）」を想定
  v_base_candidates := ARRAY_CONSTRUCT(
    'README_DB_DESIGN.md',
    'design/design.DB_DESIGN.md',
    'design/design.' || v_schema || '.md',

    -- 内部/通常テーブル
    'master/tables/' || v_schema || '.' || v_table || '.md',

    -- 外部テーブル
    'master/externaltables/' || v_schema || '.' || v_table || '.md',

    -- ビュー定義
    'master/views/' || v_schema || '.' || v_table || '.md',

    -- その他オブジェクト（procedure/function/tool/semantic view 等）
    'master/other/' || v_schema || '.' || v_table || '.md',

    -- 設計意図（オブジェクト設計書）
    'design/' || v_schema || '/design.' || v_table || '.md'
  );

  -- (B) base候補のうち、V_DOCS_OBSIDIAN に実在するものだけ残す
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

  -- (C) columns（従来通り）
  IF (v_inc_cols) THEN
    SELECT COALESCE(
             ARRAY_AGG(PATH) WITHIN GROUP (ORDER BY PATH),
             ARRAY_CONSTRUCT()
           )
      INTO :v_col_paths
    FROM (
      SELECT d.PATH
      FROM DB_DESIGN.V_DOCS_OBSIDIAN d
      WHERE d.PATH LIKE 'master/columns/%'
        AND d.TARGET_SCHEMA = :v_schema
        AND d.TARGET_TABLE  = :v_table
      QUALIFY ROW_NUMBER() OVER (ORDER BY d.PATH) <= :v_max_cols
    );
  ELSE
    v_col_paths := ARRAY_CONSTRUCT();
  END IF;

  -- (D) 結合して重複排除
  v_all_paths := ARRAY_CAT(v_base_paths, v_col_paths);

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
    'target_table', v_table,
    'include_columns', v_inc_cols,
    'count', ARRAY_SIZE(v_paths_dedup),
    'paths', v_paths_dedup,
    'paths_json', TO_JSON(v_paths_dedup)
  ));
END;
$$;
````

