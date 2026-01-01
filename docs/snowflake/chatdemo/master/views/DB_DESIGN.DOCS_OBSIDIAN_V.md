---
type: view
view_id: VW_20251227014013
schema_id: SCH_20251226180633
physical: DOCS_OBSIDIAN_V
comment: Obsidian VaultのMarkdownを解析し、Cortex Search/Agent用の検索メタ情報を付与したVIEW
---

# DOCS_OBSIDIAN_V

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name   | comment                                                   |
| ------------- | --------------------------------------------------------- |
| DOC_ID        | Obsidianノートの一意ID（1ファイル=1レコード）                             |
| PATH          | Vault内のMarkdownファイルパス（.md付き）                              |
| FOLDER        | Vault内のフォルダパス（PATHの上位）                                    |
| CONTENT       | Markdown本文（全文）                                            |
| UPDATED_AT    | Snowflakeに取り込まれた時刻（最新判定用）                                 |
| SCOPE         | Vault上の大分類（master / design / views / templates / other）   |
| FILE_TYPE     | ノート種別（master_columns / profile_evidence / agent_review 等） |
| RUN_DATE      | EvidenceやReviewの対象日（YYYY-MM-DD）。パスまたはfrontmatterから抽出      |
| TARGET_SCHEMA | 対象スキーマ名（PATH規約から抽出）                                       |
| TARGET_TABLE  | 対象テーブル名（PATH規約から抽出）                                       |
| TARGET_COLUMN | 対象カラム名（master/columns のみ）                                 |

## SQL
```sql
WITH base AS (
  SELECT
    DOC_ID,
    PATH,
    FOLDER,
    CONTENT,
    INGESTED_AT AS UPDATED_AT
  FROM DB_DESIGN.DOCS_OBSIDIAN
),
parsed AS (
  SELECT
    DOC_ID,
    PATH,
    FOLDER,
    CONTENT,
    UPDATED_AT,

    /* 大分類 */
    CASE
      WHEN PATH LIKE 'master/%'     THEN 'master'
      WHEN PATH LIKE 'design/%'     THEN 'design'
      WHEN PATH LIKE 'views/%'      THEN 'views'
      WHEN PATH LIKE 'templates/%'  THEN 'templates'
      ELSE 'other'
    END AS SCOPE,

    /* 詳細種別（検索・Agent制御用） */
    CASE
      WHEN PATH LIKE 'master/columns/%' THEN 'master_columns'
      WHEN PATH LIKE 'master/tables/%'  THEN 'master_tables'
      WHEN PATH LIKE 'master/schemas/%' THEN 'master_schemas'
      WHEN PATH LIKE 'master/views/%'   THEN 'master_views'
      WHEN PATH LIKE 'master/other/%'   THEN 'master_other'
      WHEN PATH LIKE 'design/reviews/profiles/%' THEN 'profile_evidence'
      WHEN PATH LIKE 'design/reviews/agent/%'    THEN 'agent_review'
      ELSE 'misc'
    END AS FILE_TYPE,

    /* RUN_DATE：パス優先 → frontmatter fallback */
    COALESCE(
      /* profiles */
      IFF(PATH LIKE 'design/reviews/profiles/%',
          REGEXP_SUBSTR(
            PATH,
            'design/reviews/profiles/([0-9]{4}-[0-9]{2}-[0-9]{2})/',
            1, 1, 'e', 1
          ),
          NULL
      ),

      /* agent */
      IFF(PATH LIKE 'design/reviews/agent/%',
          REGEXP_SUBSTR(
            PATH,
            'design/reviews/agent/([0-9]{4}-[0-9]{2}-[0-9]{2})/',
            1, 1, 'e', 1
          ),
          NULL
      ),

      /* frontmatter: review_date */
      REGEXP_SUBSTR(
        CONTENT,
        '^review_date:\\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\\s*$',
        1, 1, 'me', 1
      ),

      /* frontmatter: generated_on */
      REGEXP_SUBSTR(
        CONTENT,
        '^generated_on:\\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\\s*$',
        1, 1, 'me', 1
      )
    ) AS RUN_DATE,

    /* TARGET_SCHEMA */
    IFF(PATH LIKE 'master/columns/%',
        REGEXP_SUBSTR(
          PATH,
          'master/columns/([^.]+)\\.',
          1, 1, 'e', 1
        ),
        COALESCE(
          IFF(PATH LIKE 'design/reviews/profiles/%',
              REGEXP_SUBSTR(
                PATH,
                'design/reviews/profiles/[0-9-]+/([^/]+)/',
                1, 1, 'e', 1
              ),
              NULL
          ),
          IFF(PATH LIKE 'design/reviews/agent/%',
              REGEXP_SUBSTR(
                PATH,
                'design/reviews/agent/[0-9-]+/([^/]+)/',
                1, 1, 'e', 1
              ),
              NULL
          )
        )
    ) AS TARGET_SCHEMA,

    /* TARGET_TABLE */
    IFF(PATH LIKE 'master/columns/%',
        REGEXP_SUBSTR(
          PATH,
          'master/columns/[^.]+\\.([^.]+)\\.',
          1, 1, 'e', 1
        ),
        COALESCE(
          IFF(PATH LIKE 'design/reviews/profiles/%',
              REGEXP_SUBSTR(
                PATH,
                'design/reviews/profiles/[0-9-]+/[^/]+/([^/]+)\\.md$',
                1, 1, 'e', 1
              ),
              NULL
          ),
          IFF(PATH LIKE 'design/reviews/agent/%',
              REGEXP_SUBSTR(
                PATH,
                'design/reviews/agent/[0-9-]+/[^/]+/([^/]+)\\.review\\.md$',
                1, 1, 'e', 1
              ),
              NULL
          )
        )
    ) AS TARGET_TABLE,

    /* TARGET_COLUMN（master/columns のみ） */
    IFF(PATH LIKE 'master/columns/%',
        REGEXP_SUBSTR(
          PATH,
          'master/columns/[^.]+\\.[^.]+\\.([^.]+)\\.md$',
          1, 1, 'e', 1
        ),
        NULL
    ) AS TARGET_COLUMN

  FROM base
)
SELECT
  DOC_ID,
  PATH,
  FOLDER,
  CONTENT,
  UPDATED_AT,
  SCOPE,
  FILE_TYPE,
  RUN_DATE,
  TARGET_SCHEMA,
  TARGET_TABLE,
  TARGET_COLUMN
FROM parsed
```
