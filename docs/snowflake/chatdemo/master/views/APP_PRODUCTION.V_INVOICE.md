---
type: view
view_id: VW_20251225163216
schema_id: SCH_20251225131727
physical: V_INVOICE
comment: 請求VIEW（請求番号×計上月単位、売上金額集計済）
---

# V_INVOICE

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name         | comment           |
| ------------------- | ----------------- |
| INVOICE_KEY         | 請求キー（請求番号 or 仮キー） |
| INVOICE_NUMBER      | 請求番号              |
| ORDER_NUMBER        | オーダ番号             |
| ACCOUNTING_MONTH    | 計上月度              |
| AMOUNT              | 請求金額              |
| SALES_DELIVERY_FLAG | 売上渡しフラグ           |

## SQL
```sql
SELECT
    /* 請求番号が無い場合は仮キーを生成 */
    COALESCE(
        invoice_number,
        CONCAT('NO_INVOICE_', order_number)
    ) AS invoice_key,

    invoice_number,
    ANY_VALUE(order_number) AS order_number,
    accounting_month,
    SUM(amount) AS amount,
    MAX(sales_delivery_flag) AS sales_delivery_flag
FROM ANKEN_MEISAI
/* ★ WHERE 句で invoice_number を除外しない */
GROUP BY
    COALESCE(invoice_number, CONCAT('NO_INVOICE_', order_number)),
    invoice_number,
    accounting_month
```
