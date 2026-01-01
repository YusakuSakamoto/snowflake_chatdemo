---
type: view
view_id: VW_20251225161213
schema_id: SCH_20251225131727
physical: V_CUSTOMER_MASTER
comment: 取引先マスタVIEW（案件明細から生成）
---

# V_CUSTOMER_MASTER

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name   | comment |
| ------------- | ------- |
| CUSTOMER_ID   | 取引先ID   |
| CUSTOMER_NAME | 取引先名    |
| ACTIVE_FLAG   | 有効無効フラグ |

## SQL
```sql
SELECT
  customer_id,
  ANY_VALUE(customer_name) AS customer_name,
  MAX(active_flag) AS active_flag
FROM ANKEN_MEISAI
WHERE customer_id IS NOT NULL
GROUP BY customer_id
```
