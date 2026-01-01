---
type: column
column_id: COL_EXT_20251226181139
table_id: TBL_20260102230002
physical: RUN_ID
domain: VARCHAR
pk: true
is_nullable: false
default: null
comment: プロファイル実行（run）を一意に識別するID。1回の PROFILE_TABLE 実行につき1つ発行される。原則としてUUID等によりアプリケーション側で一意生成され、同一RUN_IDでの再実行時は結果を上書きする。
  (外部テーブル版)
---

# RUN_ID
