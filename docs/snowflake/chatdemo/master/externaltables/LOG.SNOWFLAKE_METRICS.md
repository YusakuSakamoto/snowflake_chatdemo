---
type: externaltable
table_id: TBL_20260102000104
schema_id: SCH_20260102000001
physical: SNOWFLAKE_METRICS
stage_name: LOGS_STAGE
stage_location: snowflake_metrics/
file_format: JSON
auto_refresh: true
partition_by: [year, month, day, hour]
comment: Snowflakeメトリクスログ（外部テーブル）
---

