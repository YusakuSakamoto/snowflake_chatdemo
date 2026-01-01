---
type: other
schema_id: SCH_20251226180633
physical: OBSIDIAN_VAULT_STAGE
object_type: procedure
comment:
---

# SQL
```sql
CREATE OR REPLACE STAGE DB_DESIGN.OBSIDIAN_VAULT_STAGE
  URL = 's3://135365622922-snowflake-dbdesign/'
  STORAGE_INTEGRATION = S3_OBSIDIAN_INT;
```
