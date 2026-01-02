---
type: externaltable
table_id: TBL_20260102230002
schema_id: SCH_20251226180633
physical: EXT_PROFILE_RUNS
stage_name: OBSIDIAN_VAULT_STAGE
stage_location: profile_runs/
file_format: JSON
auto_refresh: false
partition_by:
  - YEAR
  - MONTH
  - DAY
comment: プロファイル実行管理テーブル（S3直接参照）。1行が1回のプロファイル実行を表し、実行履歴・トレーサビリティ確保に利用される。
---
