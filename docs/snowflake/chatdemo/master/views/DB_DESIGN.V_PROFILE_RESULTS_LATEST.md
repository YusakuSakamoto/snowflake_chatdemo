---
type: view
view_id: VW_20251226184000
schema_id: SCH_20251226180633
physical: V_PROFILE_RESULTS_LATEST
comment: 最新（SUCCEEDED）のプロファイル実行に紐づく結果一覧
---

# V_PROFILE_RESULTS_LATEST

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name   | comment                  |
| ------------- | ------------------------ |
| RUN_ID        | プロファイル実行ID               |
| TARGET_DB     | 対象DB                     |
| TARGET_SCHEMA | 対象スキーマ                   |
| TARGET_TABLE  | 対象テーブル                   |
| TARGET_COLUMN | 対象カラム                    |
| AS_OF_AT      | メトリクス算出時点                |
| METRICS       | プロファイル結果メトリクス（VARIANT想定） |

## SQL
```sql
WITH LATEST AS (
  SELECT
    TARGET_DB, TARGET_SCHEMA, TARGET_TABLE,
    MAX(STARTED_AT) AS MAX_STARTED_AT
  FROM GBPS253YS_DB.DB_DESIGN.PROFILE_RUNS
  WHERE STATUS = 'SUCCEEDED'
  GROUP BY 1,2,3
),
LATEST_RUN AS (
  SELECT r.*
  FROM GBPS253YS_DB.DB_DESIGN.PROFILE_RUNS r
  JOIN LATEST l
    ON r.TARGET_DB = l.TARGET_DB
   AND r.TARGET_SCHEMA = l.TARGET_SCHEMA
   AND r.TARGET_TABLE  = l.TARGET_TABLE
   AND r.STARTED_AT    = l.MAX_STARTED_AT
)
SELECT
  pr.RUN_ID,
  pr.TARGET_DB,
  pr.TARGET_SCHEMA,
  pr.TARGET_TABLE,
  pr.TARGET_COLUMN,
  pr.AS_OF_AT,
  pr.METRICS
FROM GBPS253YS_DB.DB_DESIGN.PROFILE_RESULTS pr
JOIN LATEST_RUN lr
  ON pr.RUN_ID = lr.RUN_ID;
```
