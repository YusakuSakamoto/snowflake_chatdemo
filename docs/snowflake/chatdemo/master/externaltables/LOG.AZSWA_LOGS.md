---
type: externaltable
table_id: TBL_20260102000103
schema_id: SCH_20260102000001
physical: AZSWA_LOGS
stage_name: LOGS_STAGE
stage_location: azswa/
file_format: JSON
auto_refresh: true
partition_by: [year, month, day, hour]
comment: Azure Static Web Apps アクセスログ（外部テーブル）
---

# AZSWA_LOGS
