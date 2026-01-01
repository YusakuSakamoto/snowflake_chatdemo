---
type: view
view_id: VW_20251225163920
schema_id: SCH_20251225131727
physical: V_PROJECT_MASTER
comment: 案件マスタVIEW（案件番号＋枝番＋年度単位）
---

# V_PROJECT_MASTER

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name     | comment |
| --------------- | ------- |
| PROJECT_NUMBER  | 案件番号    |
| BRANCH_NUMBER   | 枝番      |
| FISCAL_YEAR     | 年度      |
| PROJECT_NAME    | 案件名     |
| SUBJECT         | 件名      |
| SALES_CATEGORY  | 売上区分    |
| RANK            | ランク     |
| CUSTOMER_ID     | 取引先ID   |
| DEPARTMENT_ID   | 部署ID    |
| WORK_START_DATE | 作業開始日   |
| WORK_END_DATE   | 作業終了日   |

## SQL
```sql
SELECT
    project_number,
    branch_number,
    fiscal_year,
    ANY_VALUE(project_name) AS project_name,
    ANY_VALUE(subject) AS subject,
    ANY_VALUE(sales_category) AS sales_category,
    ANY_VALUE(rank) AS rank,
    ANY_VALUE(customer_id) AS customer_id,
    ANY_VALUE(department_id) AS department_id,
    TRY_TO_DATE(ANY_VALUE(work_start_date)) AS work_start_date,
    TRY_TO_DATE(ANY_VALUE(work_end_date)) AS work_end_date
FROM ANKEN_MEISAI
WHERE project_number IS NOT NULL
GROUP BY
    project_number,
    branch_number,
    fiscal_year
```
