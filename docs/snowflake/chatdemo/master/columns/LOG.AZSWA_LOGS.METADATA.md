---
type: column
column_id: COL_20260102000411
table_id: TBL_20260102000103
physical: METADATA
domain: VARIANT
pk: false
ref_table_id:
ref_column:
ref_cardinality:
is_nullable: true
default: 
comment: 追加コンテキスト情報（例：referrer, ab_test_flag, experiment_id, custom_tags）。
利用ガイドライン: 主要分析軸は固定カラムで持ち、METADATAは可変項目の吸収用。濫用を防ぐため、構造例・制限事項は設計ドキュメントに準拠。
構造例: {"referrer": "https://...", "ab_test_flag": "A", "experiment_id": "exp123", "custom_tags": ["tag1", "tag2"]}
---

# METADATA
