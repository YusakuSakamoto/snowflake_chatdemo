---
type: other
schema_id: SCH_20251225131727
physical: RAW_DATA
object_type: stage
comment: RAWデータ格納用ステージ
---

# SQL
```sql
CREATE OR REPLACE STAGE APP_PRODUCTION.RAW_DATA
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
  DIRECTORY = (ENABLE = TRUE);
```

