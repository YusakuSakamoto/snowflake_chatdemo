---
type: column
column_id: EXT_20251226181951
table_id: TBL_20260102230002
physical: STATUS
domain: VARCHAR
pk: false
ref_table_id:
ref_column:
ref_cardinality:
is_nullable: false
default: null
comment: 'プロファイル実行の状態。許可値は以下の通り：RUNNING : 実行中SUCCEEDED : 正常終了FAILED : 異常終了状態遷移は原則として
  RUNNING → SUCCEEDED | FAILED のみとする。 (外部テーブル版: EXT_PROFILE_RUNS)'
---

# STATUS
