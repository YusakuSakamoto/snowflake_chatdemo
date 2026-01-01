---
type: view
view_id: VW_20251229015446
schema_id: SCH_20251225131727
physical: V_ENTITY_ALIAS_AUTO
comment: 自動生成エイリアス辞書（部署/顧客/案件/オーダー）。手動辞書と統合して名称解決に利用する。
---

# V_ENTITY_ALIAS_AUTO

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
| IS_ACTIVE        | 優先度（小さいほど優先）                                      |

## SQL
```sql
/* =========================
   部門：正式名称
   ========================= */
SELECT
  FULL_NAME                      AS alias_raw,
  NORMALIZE_JA_DEPT(FULL_NAME)   AS alias_normalized,
  'department'                   AS entity_type,
  ID::VARCHAR                    AS entity_id,
  FULL_NAME                      AS entity_name,
  1.00                           AS confidence,
  1000                           AS priority,
  TRUE                           AS is_active
FROM GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
WHERE FULL_NAME IS NOT NULL

UNION ALL

/* =========================
   部門：略称
   ========================= */
SELECT
  SHORT_NAME                     AS alias_raw,
  NORMALIZE_JA_DEPT(SHORT_NAME)  AS alias_normalized,
  'department'                   AS entity_type,
  ID::VARCHAR                    AS entity_id,
  FULL_NAME                      AS entity_name,
  0.85                           AS confidence,
  1000                           AS priority,
  TRUE                           AS is_active
FROM GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
WHERE SHORT_NAME IS NOT NULL

UNION ALL

/* =========================
   部門：複合正式名称（本部＋部門）
   ========================= */
SELECT
  COMBINED_NAME                      AS alias_raw,
  NORMALIZE_JA_DEPT(COMBINED_NAME)   AS alias_normalized,
  'department'                       AS entity_type,
  ID::VARCHAR                        AS entity_id,
  FULL_NAME                          AS entity_name,
  0.95                               AS confidence,
  1000                               AS priority,
  TRUE                               AS is_active
FROM GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
WHERE COMBINED_NAME IS NOT NULL

UNION ALL

/* =========================
   部門：複合略称
   ========================= */
SELECT
  COMBINED_SHORT_NAME                      AS alias_raw,
  NORMALIZE_JA_DEPT(COMBINED_SHORT_NAME)   AS alias_normalized,
  'department'                             AS entity_type,
  ID::VARCHAR                              AS entity_id,
  FULL_NAME                                AS entity_name,
  0.80                                     AS confidence,
  1000                                     AS priority,
  TRUE                                     AS is_active
FROM GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
WHERE COMBINED_SHORT_NAME IS NOT NULL

UNION ALL

/* =========================
   顧客（Customer）
   ========================= */
SELECT
  CUSTOMER_NAME                 AS alias_raw,
  NORMALIZE_JA(CUSTOMER_NAME)   AS alias_normalized,
  'customer'                    AS entity_type,
  CUSTOMER_ID::VARCHAR          AS entity_id,
  CUSTOMER_NAME                 AS entity_name,
  1.00                          AS confidence,
  1000                          AS priority,
  TRUE                          AS is_active
FROM GBPS253YS_DB.APP_PRODUCTION.V_CUSTOMER_MASTER

UNION ALL

/* =========================
   案件：案件名（project_name）
   ========================= */
SELECT
  PROJECT_NAME                 AS alias_raw,
  NORMALIZE_JA(PROJECT_NAME)   AS alias_normalized,
  'project'                    AS entity_type,
  PROJECT_NUMBER               AS entity_id,
  PROJECT_NAME                 AS entity_name,
  1.00                         AS confidence,
  1000                         AS priority,
  TRUE                         AS is_active
FROM GBPS253YS_DB.APP_PRODUCTION.V_PROJECT_MASTER
WHERE PROJECT_NAME IS NOT NULL

UNION ALL

/* =========================
   案件：件名（subject）
   ========================= */
SELECT
  SUBJECT                      AS alias_raw,
  NORMALIZE_JA(SUBJECT)        AS alias_normalized,
  'project'                    AS entity_type,
  PROJECT_NUMBER               AS entity_id,
  PROJECT_NAME                 AS entity_name,
  0.90                         AS confidence,
  1000                         AS priority,
  TRUE                         AS is_active
FROM GBPS253YS_DB.APP_PRODUCTION.V_PROJECT_MASTER
WHERE SUBJECT IS NOT NULL

UNION ALL

/* =========================
   オーダー（Order）
   ========================= */
SELECT
  ORDER_NAME                 AS alias_raw,
  NORMALIZE_JA(ORDER_NAME)   AS alias_normalized,
  'order'                    AS entity_type,
  ORDER_NUMBER::VARCHAR      AS entity_id,
  ORDER_NAME                 AS entity_name,
  1.00                       AS confidence,
  1000                       AS priority,
  TRUE                       AS is_active
FROM GBPS253YS_DB.APP_PRODUCTION.V_ORDER_MASTER
```
