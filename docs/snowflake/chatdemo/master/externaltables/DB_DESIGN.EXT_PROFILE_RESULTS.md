---
type: externaltable
table_id: TBL_20260102230001
schema_id: SCH_20251226180633
physical: EXT_PROFILE_RESULTS
stage_name: OBSIDIAN_VAULT_STAGE
stage_location: profile_results/
file_format: JSON
auto_refresh: false
partition_by:
  - YEAR
  - MONTH
  - DAY
comment: プロファイル処理により算出されたカラム単位の計測結果を保持する外部テーブル（S3直接参照）。1行が1回の実行（run）における1カラム分の結果を表し、品質確認・比較・監査・設計レビューの根拠として利用される。
---
