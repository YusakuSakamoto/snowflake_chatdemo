---
type: semantic_view
semantic_view_id: SV_20260102000001
schema_id: SCH_20251225131727
physical: SV_SALES
comment: 売上・請求分析向けセマンティックモデル（らくらく案件データ正規化VIEW群）
---

# SV_SALES

## 概要

らくらく案件データ（正規化VIEW群）を元にした売上・請求分析向けのセマンティックモデル。
Cortex Analyst による自然言語クエリを実現するための意味定義を提供。

## 設計意図
- [[design.SV_SALES]] を参照

## YAML定義

```yaml
name: SV_SALES
description: らくらく案件データ（正規化VIEW群）を元にした売上・請求分析向けセマンティックモデル

tables:
  - name: DEPARTMENTS
    description: 部署マスタ（年度別）
    base_table:
      database: GBPS253YS_DB
      schema: APP_PRODUCTION
      table: DEPARTMENT_MASTER
    primary_key:
      columns: [FISCAL_YEAR, DEPARTMENT_ID]
    dimensions:
      - name: DEPARTMENT_CODE
        expr: DEPARTMENT_CODE
        data_type: TEXT
        description: 部CD（部の配下をまとめるキー）。1桁の文字列。
        synonyms: ["部CD", "部コード", "部", "department_code"]
      - name: SECTION_CODE
        expr: SECTION_CODE
        data_type: TEXT
        description: 課CD。1桁の文字列。
        synonyms: ["課CD", "課コード", "課", "section_code"]
      - name: GROUP_CODE
        expr: GROUP_CODE
        data_type: TEXT
        description: グループCD。1桁の文字列。
        synonyms: ["グループCD", "グループコード", "グループ", "group_code"]
      - name: FISCAL_YEAR
        expr: FISCAL_YEAR
        data_type: TEXT
        description: 年度
      - name: DEPARTMENT_ID
        expr: DEPARTMENT_ID
        data_type: TEXT
        description: 部署ID
      - name: DIVISION_CODE
        expr: DIVISION_CODE
        data_type: TEXT
        description: 部コード（3桁）
        synonyms: ["DIVISION", "division_code", "部(3桁)"]
      - name: DEPARTMENT_SECTION_CODE
        expr: DEPARTMENT_SECTION_CODE
        data_type: TEXT
        description: 課コード（4桁：DIVISION_CODE + SECTION_CODE）
        synonyms: ["SECTION(4桁)", "department_section_code", "課(4桁)"]
      - name: HEADQUARTERS_CODE
        expr: HEADQUARTERS_CODE
        data_type: TEXT
        description: 本部コード（本部単位の範囲展開・集計キー）
        synonyms: ["本部", "本部コード", "headquarters_code"]
      - name: GENERAL_DEPARTMENT_CODE
        expr: GENERAL_DEPARTMENT_CODE
        data_type: TEXT
        description: 汎用部署コード（マスタ側の提供値。用途は要確認）
        synonyms: ["general_department_code"]
      - name: DEPARTMENT_CATEGORY
        expr: DEPARTMENT_CATEGORY
        data_type: TEXT
        description: 部署区分（本部 / 部 / 課 / グループ）
        synonyms: ["カテゴリ", "区分", "department_category"]
      - name: COMBINED_NAME
        expr: COMBINED_NAME
        data_type: TEXT
        description: 部署のフル名称（階層結合名）
        synonyms: ["部署名", "正式名称", "name_full", "combined_name"]
      - name: COMBINED_SHORT_NAME
        expr: COMBINED_SHORT_NAME
        data_type: TEXT
        description: 部署の略称（階層結合の短縮名）
        synonyms: ["略称", "name_short", "short_name", "combined_short_name"]

  - name: CUSTOMERS
    description: 取引先マスタ（正規化VIEW）
    base_table:
      database: GBPS253YS_DB
      schema: APP_PRODUCTION
      table: V_CUSTOMER_MASTER
    primary_key:
      columns: [CUSTOMER_ID]
    dimensions:
      - name: CUSTOMER_ID
        expr: CUSTOMER_ID
        data_type: TEXT
        description: 取引先ID
        synonyms: ["顧客ID", "取引先コード"]
      - name: CUSTOMER_NAME
        expr: CUSTOMER_NAME
        data_type: TEXT
        description: 取引先名
        synonyms: ["顧客名", "取引先名"]
      - name: ACTIVE_FLAG
        expr: ACTIVE_FLAG
        data_type: TEXT
        description: 有効無効フラグ

  - name: PROJECTS
    description: 案件マスタ（案件番号＋枝番＋年度）
    base_table:
      database: GBPS253YS_DB
      schema: APP_PRODUCTION
      table: V_PROJECT_MASTER
    primary_key:
      columns: [PROJECT_NUMBER, BRANCH_NUMBER, FISCAL_YEAR]
    dimensions:
      - name: PROJECT_NUMBER
        expr: PROJECT_NUMBER
        data_type: TEXT
        description: 案件番号
        synonyms: ["案件No", "案件番号", "project_number"]
      - name: BRANCH_NUMBER
        expr: BRANCH_NUMBER
        data_type: TEXT
        description: 枝番
        synonyms: ["枝番", "branch_number"]
      - name: FISCAL_YEAR
        expr: FISCAL_YEAR
        data_type: TEXT
        description: 年度
        synonyms: ["年度", "fiscal_year"]
      - name: PROJECT_NAME
        expr: PROJECT_NAME
        data_type: TEXT
        description: 案件名
        synonyms: ["案件名", "project_name"]
      - name: SUBJECT
        expr: SUBJECT
        data_type: TEXT
        description: 件名
        synonyms: ["件名", "subject"]
      - name: SALES_CATEGORY
        expr: SALES_CATEGORY
        data_type: TEXT
        description: 売上区分
        synonyms: ["売上区分", "sales_category"]
      - name: RANK
        expr: RANK
        data_type: TEXT
        description: ランク
      - name: CUSTOMER_ID
        expr: CUSTOMER_ID
        data_type: TEXT
        description: 取引先ID
        synonyms: ["顧客ID", "取引先ID", "customer_id"]
      - name: DEPARTMENT_ID
        expr: DEPARTMENT_ID
        data_type: TEXT
        description: 部署ID
        synonyms: ["部署ID", "department_id"]
      - name: WORK_START_DATE
        expr: WORK_START_DATE
        data_type: DATE
        description: 作業開始日
        synonyms: ["作業開始日", "work_start_date"]
      - name: WORK_END_DATE
        expr: WORK_END_DATE
        data_type: DATE
        description: 作業終了日
        synonyms: ["作業終了日", "work_end_date"]

  - name: ORDERS
    description: オーダマスタ（オーダ番号単位）
    base_table:
      database: GBPS253YS_DB
      schema: APP_PRODUCTION
      table: V_ORDER_MASTER
    primary_key:
      columns: [ORDER_NUMBER]
    dimensions:
      - name: ORDER_NUMBER
        expr: ORDER_NUMBER
        data_type: TEXT
        description: オーダ番号
        synonyms: ["オーダNo", "オーダ番号", "order_number"]
      - name: PROJECT_NUMBER
        expr: PROJECT_NUMBER
        data_type: TEXT
        description: 案件番号
      - name: BRANCH_NUMBER
        expr: BRANCH_NUMBER
        data_type: TEXT
        description: 枝番
      - name: FISCAL_YEAR
        expr: FISCAL_YEAR
        data_type: TEXT
        description: 年度
      - name: ORDER_DATE
        expr: ORDER_DATE
        data_type: DATE
        description: オーダ日
        synonyms: ["オーダ日", "受注日", "order_date"]
      - name: SALES_CATEGORY
        expr: SALES_CATEGORY
        data_type: TEXT
        description: 売上区分

  - name: INVOICES
    description: 請求マスタ（請求番号×計上月単位、金額集計済）
    base_table:
      database: GBPS253YS_DB
      schema: APP_PRODUCTION
      table: V_INVOICE
    primary_key:
      columns: [INVOICE_KEY, ACCOUNTING_MONTH]
    dimensions:
      - name: INVOICE_KEY
        expr: INVOICE_KEY
        data_type: TEXT
        description: 請求キー（請求番号 or 仮キー：NO_INVOICE_xxx）
        synonyms: ["請求キー", "invoice_key"]
      - name: INVOICE_NUMBER
        expr: INVOICE_NUMBER
        data_type: TEXT
        description: 請求番号（NULLの場合あり）
        synonyms: ["請求No", "請求番号", "invoice_number"]
      - name: ORDER_NUMBER
        expr: ORDER_NUMBER
        data_type: TEXT
        description: オーダ番号
        synonyms: ["オーダNo", "オーダ番号", "order_number"]
      - name: ACCOUNTING_MONTH
        expr: ACCOUNTING_MONTH
        data_type: TEXT
        description: 計上月（YYYY/MM形式の文字列、例：2024/04、2025/12）
        synonyms: ["計上月", "売上月", "accounting_month"]
        sample_values: ["2024/04", "2024/05", "2024/06", "2025/01"]
      - name: SALES_DELIVERY_FLAG
        expr: SALES_DELIVERY_FLAG
        data_type: TEXT
        description: 売上渡しフラグ
        synonyms: ["売上渡し", "sales_delivery_flag"]
    measures:
      - name: INVOICE_AMOUNT
        expr: AMOUNT
        data_type: NUMBER
        description: 請求金額
        synonyms: ["請求金額", "売上金額", "金額", "invoice_amount", "amount"]
        default_aggregation: sum

  - name: PROJECT_FACTS
    description: プロジェクトファクト（生データ粒度、明細粒度）
    base_table:
      database: GBPS253YS_DB
      schema: APP_PRODUCTION
      table: V_PROJECT_FACT
    dimensions:
      - name: PROJECT_NUMBER
        expr: PROJECT_NUMBER
        data_type: TEXT
        description: 案件番号
      - name: BRANCH_NUMBER
        expr: BRANCH_NUMBER
        data_type: TEXT
        description: 枝番
      - name: FISCAL_YEAR
        expr: FISCAL_YEAR
        data_type: TEXT
        description: 年度
      - name: ORDER_NUMBER
        expr: ORDER_NUMBER
        data_type: TEXT
        description: オーダ番号
      - name: INVOICE_NUMBER
        expr: INVOICE_NUMBER
        data_type: TEXT
        description: 請求番号
      - name: ACCOUNTING_MONTH
        expr: ACCOUNTING_MONTH
        data_type: TEXT
        description: 計上月
      - name: CUSTOMER_ID
        expr: CUSTOMER_ID
        data_type: TEXT
        description: 取引先ID
      - name: DEPARTMENT_ID
        expr: DEPARTMENT_ID
        data_type: TEXT
        description: 部署ID
    measures:
      - name: ROW_COUNT
        expr: COUNT(*)
        data_type: NUMBER
        description: 明細レコード数
        default_aggregation: sum

relationships:
  - name: PROJECT_TO_CUSTOMER
    leftTable: PROJECTS
    rightTable: CUSTOMERS
    joinType: left_outer
    relationshipColumns:
      - leftColumn: CUSTOMER_ID
        rightColumn: CUSTOMER_ID

  - name: PROJECT_TO_DEPARTMENT
    leftTable: PROJECTS
    rightTable: DEPARTMENTS
    joinType: left_outer
    relationshipColumns:
      - leftColumn: DEPARTMENT_ID
        rightColumn: DEPARTMENT_ID
      - leftColumn: FISCAL_YEAR
        rightColumn: FISCAL_YEAR

  - name: ORDER_TO_PROJECT
    leftTable: ORDERS
    rightTable: PROJECTS
    joinType: left_outer
    relationshipColumns:
      - leftColumn: PROJECT_NUMBER
        rightColumn: PROJECT_NUMBER
      - leftColumn: BRANCH_NUMBER
        rightColumn: BRANCH_NUMBER
      - leftColumn: FISCAL_YEAR
        rightColumn: FISCAL_YEAR

  - name: INVOICE_TO_ORDER
    leftTable: INVOICES
    rightTable: ORDERS
    joinType: left_outer
    relationshipColumns:
      - leftColumn: ORDER_NUMBER
        rightColumn: ORDER_NUMBER

  - name: FACT_TO_PROJECT
    leftTable: PROJECT_FACTS
    rightTable: PROJECTS
    joinType: left_outer
    relationshipColumns:
      - leftColumn: PROJECT_NUMBER
        rightColumn: PROJECT_NUMBER
      - leftColumn: BRANCH_NUMBER
        rightColumn: BRANCH_NUMBER
      - leftColumn: FISCAL_YEAR
        rightColumn: FISCAL_YEAR

  - name: FACT_TO_CUSTOMER
    leftTable: PROJECT_FACTS
    rightTable: CUSTOMERS
    joinType: left_outer
    relationshipColumns:
      - leftColumn: CUSTOMER_ID
        rightColumn: CUSTOMER_ID

  - name: FACT_TO_DEPARTMENT
    leftTable: PROJECT_FACTS
    rightTable: DEPARTMENTS
    joinType: left_outer
    relationshipColumns:
      - leftColumn: DEPARTMENT_ID
        rightColumn: DEPARTMENT_ID
      - leftColumn: FISCAL_YEAR
        rightColumn: FISCAL_YEAR
```

## 利用方法

### YAMLファイルとして保存
```bash
# S3ステージ経由でアップロード（SV_SALES.yamlとして出力）
PUT file://SV_SALES.yaml @APP_PRODUCTION.RAW_DATA;
```

### Cortex Analyst呼び出し
```sql
SELECT SNOWFLAKE.CORTEX.ANALYST_TEXT_TO_SQL(
    '@APP_PRODUCTION.RAW_DATA/SV_SALES.yaml',
    '営業部の2024年度の売上合計を教えて'
);
```

## 参考リンク
- [[design.SV_SALES]] - 設計意図
- [[APP_PRODUCTION.V_CUSTOMER_MASTER]] - 取引先マスタVIEW
- [[APP_PRODUCTION.V_PROJECT_MASTER]] - 案件マスタVIEW
- [[APP_PRODUCTION.V_ORDER_MASTER]] - オーダマスタVIEW
- [[APP_PRODUCTION.V_INVOICE]] - 請求マスタVIEW
- [[APP_PRODUCTION.V_PROJECT_FACT]] - プロジェクトファクトVIEW
- [[APP_PRODUCTION.DEPARTMENT_MASTER]] - 部署マスタテーブル
