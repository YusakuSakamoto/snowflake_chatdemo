---
type: externaltable
table_id: TBL_20260102000102
schema_id: SCH_20260102000001
physical: AZFUNCTIONS_LOGS
stage_name: LOGS_STAGE
stage_location: azfunctions/
file_format: JSON
auto_refresh: true
partition_by: [year, month, day, hour]
comment: Azure Functionsログ（外部テーブル）
---

