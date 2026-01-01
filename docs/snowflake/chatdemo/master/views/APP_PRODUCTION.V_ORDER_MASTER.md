---
type: view
view_id: VW_20251225163627
schema_id: SCH_20251225131727
physical: V_ORDER_MASTER
comment: オーダマスタVIEW（オーダ番号単位）
---

# V_ORDER_MASTER

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name           | comment |
| --------------------- | ------- |
| ORDER_NUMBER          | オーダ番号   |
| ORDER_NAME            | オーダ名    |
| PROJECT_NUMBER        | 案件番号    |
| BRANCH_NUMBER         | 枝番      |
| FISCAL_YEAR           | 年度      |
| CUSTOMER_ORDER_NUMBER | 顧客注文番号  |

## SQL
```sql
SELECT
    order_number,
    ANY_VALUE(order_name) AS order_name,
    ANY_VALUE(project_number) AS project_number,
    ANY_VALUE(branch_number) AS branch_number,
    ANY_VALUE(fiscal_year) AS fiscal_year,
    ANY_VALUE(customer_order_number) AS customer_order_number
FROM ANKEN_MEISAI
WHERE order_number IS NOT NULL
GROUP BY order_number
```
