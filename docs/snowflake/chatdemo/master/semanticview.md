
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
      - name: BRANCH_NUMBER
        expr: BRANCH_NUMBER
        data_type: TEXT
        description: 枝番
      - name: FISCAL_YEAR
        expr: FISCAL_YEAR
        data_type: TEXT
        description: 年度
      - name: PROJECT_NAME
        expr: PROJECT_NAME
        data_type: TEXT
        description: 案件名
        synonyms: ["案件"]
      - name: SUBJECT
        expr: SUBJECT
        data_type: TEXT
        description: 件名
      - name: SALES_CATEGORY
        expr: SALES_CATEGORY
        data_type: TEXT
        description: 売上区分
      - name: RANK
        expr: RANK
        data_type: TEXT
        description: 案件ランク
        synonyms: ["ランク", "確度", "ステータス", "確定ランク", "確定済"]
      - name: CUSTOMER_ID
        expr: CUSTOMER_ID
        data_type: TEXT
        description: 取引先ID
      - name: DEPARTMENT_ID
        expr: DEPARTMENT_ID
        data_type: TEXT
        description: 部署ID
      - name: WORK_START_DATE
        expr: WORK_START_DATE
        data_type: DATE
        description: 作業開始日
      - name: WORK_END_DATE
        expr: WORK_END_DATE
        data_type: DATE
        description: 作業終了日
      - name: IS_CONFIRMED
        expr: CASE WHEN RANK = '確定' THEN 'Y' ELSE 'N' END
        data_type: TEXT
        description: 確定ランク判定
        synonyms: ["確定", "確定済", "確定ランク"]

  - name: ORDERS
    description: オーダマスタ（オーダ番号）
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
        synonyms: ["受注番号", "オーダ"]
      - name: ORDER_NAME
        expr: ORDER_NAME
        data_type: TEXT
        description: オーダ名
      - name: CUSTOMER_ORDER_NUMBER
        expr: CUSTOMER_ORDER_NUMBER
        data_type: TEXT
        description: 顧客注文番号
        synonyms: ["PO番号"]
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

  - name: INVOICES
    description: 請求（請求番号×計上月、金額は集計済）
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
        description: 請求キー（請求番号 or 仮キー）
      - name: ACCOUNTING_DATE
        expr: TO_DATE(ACCOUNTING_MONTH || '/01', 'YYYY/MM/DD')
        data_type: DATE
        description: 計上月（ACCOUNTING_MONTH を月初日の DATE に変換）
        synonyms: ["計上日", "計上月", "売上月", "月", "month"]
      - name: ACCOUNTING_MONTH
        expr: ACCOUNTING_MONTH
        data_type: TEXT
        description: 計上月（YYYY/MM 形式・表示用）
        synonyms: ["計上月文字列"]
      - name: ORDER_NUMBER
        expr: ORDER_NUMBER
        data_type: TEXT
        description: オーダ番号
      - name: SALES_DELIVERY_FLAG
        expr: SALES_DELIVERY_FLAG
        data_type: TEXT
        description: 売上渡しフラグ
    facts:
      - name: AMOUNT
        expr: AMOUNT
        data_type: NUMBER
        description: 請求金額（集計済）
    metrics:
      - name: TOTAL_SALES
        expr: SUM(AMOUNT)
        description: 売上合計（請求金額合計）
        synonyms: ["売上", "請求合計"]
      - name: INVOICE_COUNT
        expr: COUNT(DISTINCT CONCAT(INVOICE_NUMBER, '-', ACCOUNTING_MONTH))
        description: 請求件数（請求×計上月）

relationships:
  - name: PROJECTS_TO_CUSTOMERS
    left_table: PROJECTS
    right_table: CUSTOMERS
    join_type: left_outer
    relationship_type: many_to_one
    relationship_columns:
      - left_column: CUSTOMER_ID
        right_column: CUSTOMER_ID

  - name: ORDERS_TO_PROJECTS
    left_table: ORDERS
    right_table: PROJECTS
    join_type: left_outer
    relationship_type: many_to_one
    relationship_columns:
      - left_column: PROJECT_NUMBER
        right_column: PROJECT_NUMBER
      - left_column: BRANCH_NUMBER
        right_column: BRANCH_NUMBER
      - left_column: FISCAL_YEAR
        right_column: FISCAL_YEAR

  - name: INVOICES_TO_ORDERS
    left_table: INVOICES
    right_table: ORDERS
    join_type: left_outer
    relationship_type: many_to_one
    relationship_columns:
      - left_column: ORDER_NUMBER
        right_column: ORDER_NUMBER
        
  - name: PROJECTS_TO_DEPARTMENTS
    left_table: PROJECTS
    right_table: DEPARTMENTS
    join_type: left_outer
    relationship_type: many_to_one
    relationship_columns:
      - left_column: FISCAL_YEAR
        right_column: FISCAL_YEAR
      - left_column: DEPARTMENT_ID
        right_column: DEPARTMENT_ID
```
