---
type: externaltable
table_id: TBL_20260102230002
schema_id: SCH_20251226180633
physical: PROFILE_RUNS_EXTERNAL
stage_name: OBSIDIAN_VAULT_STAGE
file_format: FF_JSON_LINES
auto_refresh: false
partition_by:
  - year
  - month
  - day
comment: プロファイル実行管理テーブル（S3直接参照）。1行が1回のプロファイル実行を表し、実行履歴・トレーサビリティ確保に利用される。
---
