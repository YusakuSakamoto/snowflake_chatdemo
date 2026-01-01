---
type: view
view_id: VW_20251225163757
schema_id: SCH_20251225131727
physical: V_PROJECT_FACT
comment: 案件ファクトVIEW（生データ粒度を保持）
---

# V_PROJECT_FACT

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name                   | comment  |
| ----------------------------- | -------- |
| ID                            | レコードID   |
| PROJECT_NUMBER                | 案件番号     |
| BRANCH_NUMBER                 | 枝番       |
| FISCAL_YEAR                   | 年度       |
| ORDER_NUMBER                  | オーダ番号    |
| INVOICE_NUMBER                | 請求番号     |
| CUSTOMER_QUOTE_REQUEST_NUMBER | 顧客見積依頼番号 |
| ACTIVE_FLAG                   | 有効無効フラグ  |

## SQL
```sql
SELECT
    id,
    project_number,
    branch_number,
    fiscal_year,
    order_number,
    invoice_number,
    customer_quote_request_number,
    active_flag
FROM ANKEN_MEISAI
```
