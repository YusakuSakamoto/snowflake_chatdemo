---
type: view
view_id: VW_20251229021950
schema_id: SCH_20251225131727
physical: V_ENTITY_ALIAS_ALL
comment: 名称解決用エイリアス辞書（MANUAL + AUTO 統合）。alias_normalized×entity_type ごとに優先度/信頼度で1件に正規化する。
---

# V_ENTITY_ALIAS_ALL

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name      | comment                                           |
| ---------------- | ------------------------------------------------- |
| ALIAS_RAW        | 別名（正規化前の生文字列）                                     |
| ALIAS_NORMALIZED | 正規化後の別名（NORMALIZE_JA / NORMALIZE_JA_DEPT 適用後）     |
| ENTITY_TYPE      | エンティティ種別（department / customer / project / order） |
| ENTITY_ID        | エンティティID（共通利用のため varchar）                         |
| ENTITY_NAME      | 正式名称（表示用）                                         |
| CONFIDENCE       | 別名の信頼度（0.0〜1.0）                                   |
| PRIORITY         | 優先度（小さいほど優先）                                      |
| IS_ACTIVE        | 有効フラグ                                              |

## SQL
```sql
SELECT
  alias_raw,
  alias_normalized,
  entity_type,
  entity_id,
  entity_name,
  confidence,
  priority,
  is_active
FROM (
  SELECT
    alias_raw,
    alias_normalized,
    entity_type,
    entity_id,
    entity_name,
    confidence,
    priority,
    is_active
  FROM GBPS253YS_DB.NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL
  WHERE is_active = TRUE

  UNION ALL

  SELECT
    alias_raw,
    alias_normalized,
    entity_type,
    entity_id,
    entity_name,
    confidence,
    priority,
    is_active
  FROM GBPS253YS_DB.APP_PRODUCTION.V_ENTITY_ALIAS_AUTO
  WHERE is_active = TRUE
)
QUALIFY
  ROW_NUMBER() OVER (
    PARTITION BY alias_normalized, entity_type
    ORDER BY priority ASC, confidence DESC
  ) = 1
```
