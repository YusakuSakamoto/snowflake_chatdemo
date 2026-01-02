---
type: other
schema_id: SCH_20260102000001
physical: LOGS_STAGE
object_type: stage
comment: LOGスキーマ外部テーブル用のS3ステージ（logs-prod バケット）
---

# SQL
```sql
CREATE OR REPLACE STAGE LOG.LOGS_STAGE
  URL = 's3://135365622922-snowflake-chatdemo-logs-prod/'
  STORAGE_INTEGRATION = S3_OBSIDIAN_INT;
```
