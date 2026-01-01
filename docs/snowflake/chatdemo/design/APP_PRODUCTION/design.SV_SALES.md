# Semantic View設計：[[design.SV_SALES]]

## 概要
[[APP_PRODUCTION.SV_SALES]] は、らくらく案件データ（正規化VIEW群）を元にした売上・請求分析向けのセマンティックモデルである。  
Snowflake Cortex Analyst による自然言語クエリを実現するための意味定義・同義語・リレーションシップを提供する。

## 設計上の位置づけ
セマンティックビュー（Semantic View）は、Snowflake の Cortex Analyst が自然言語クエリを SQL に変換するための**メタデータ層**である。

- 物理的なテーブル・VIEWは変更しない
- YAML形式で意味定義（dimensions, measures, relationships）を記述
- 同義語（synonyms）により表記ゆれを吸収
- リレーションシップにより正しいJOINを自動生成

## 対象テーブル・VIEW

### 1. DEPARTMENTS（部署マスタ）
- **物理実体**: [[APP_PRODUCTION.DEPARTMENT_MASTER]]
- **粒度**: 年度×部署ID
- **役割**: 組織階層・部署名・略称の提供
- **主要ディメンション**:
  - DEPARTMENT_CODE / SECTION_CODE / GROUP_CODE（階層キー）
  - COMBINED_NAME / COMBINED_SHORT_NAME（表示用名称）
  - HEADQUARTERS_CODE（本部単位集計用）

### 2. CUSTOMERS（取引先マスタ）
- **物理実体**: [[APP_PRODUCTION.V_CUSTOMER_MASTER]]
- **粒度**: 取引先ID
- **役割**: 取引先名称の提供
- **主要ディメンション**:
  - CUSTOMER_ID（取引先キー）
  - CUSTOMER_NAME（取引先名）

### 3. PROJECTS（案件マスタ）
- **物理実体**: [[APP_PRODUCTION.V_PROJECT_MASTER]]
- **粒度**: 案件番号×枝番×年度
- **役割**: 案件単位の属性提供
- **主要ディメンション**:
  - PROJECT_NUMBER / BRANCH_NUMBER / FISCAL_YEAR（案件キー）
  - PROJECT_NAME / SUBJECT（案件名称）
  - CUSTOMER_ID / DEPARTMENT_ID（関連マスタへのFK）

### 4. ORDERS（オーダマスタ）
- **物理実体**: [[APP_PRODUCTION.V_ORDER_MASTER]]
- **粒度**: オーダ番号
- **役割**: 受注情報の提供
- **主要ディメンション**:
  - ORDER_NUMBER（オーダキー）
  - ORDER_DATE（受注日）

### 5. INVOICES（請求マスタ）
- **物理実体**: [[APP_PRODUCTION.V_INVOICE]]
- **粒度**: 請求番号×計上月
- **役割**: 売上・請求金額の提供
- **主要ディメンション**:
  - INVOICE_NUMBER / ACCOUNTING_MONTH（請求キー）
- **主要メジャー**:
  - INVOICE_AMOUNT（請求金額・税抜）
  - TAX_AMOUNT（消費税額）
  - INVOICE_AMOUNT_WITH_TAX（請求金額・税込）

### 6. PROJECT_FACTS（プロジェクトファクト）
- **物理実体**: [[APP_PRODUCTION.V_PROJECT_FACT]]
- **粒度**: 明細粒度（最も細かい粒度）
- **役割**: 詳細分析・明細レベルの検索
- **主要ディメンション**:
  - すべてのキー情報を保持
- **主要メジャー**:
  - ROW_COUNT（明細レコード数）

## リレーションシップ設計

### 基本方針
- **スタースキーマ的構造**: INVOICES を中心としたファクトテーブル
- **スノーフレーク拡張**: PROJECTSを経由してCUSTOMERS/DEPARTMENTSへ
- **明細粒度保持**: PROJECT_FACTSで最も細かい粒度を保持

### リレーションシップ一覧

#### 案件マスタ → マスタ系
- `PROJECT_TO_CUSTOMER`: PROJECTS → CUSTOMERS（取引先名の取得）
- `PROJECT_TO_DEPARTMENT`: PROJECTS → DEPARTMENTS（部署名の取得）

#### 受注・請求 → 案件
- `ORDER_TO_PROJECT`: ORDERS → PROJECTS（オーダから案件属性取得）
- `INVOICE_TO_PROJECT`: INVOICES → PROJECTS（請求から案件属性取得）
- `INVOICE_TO_ORDER`: INVOICES → ORDERS（請求からオーダ日取得）

#### ファクト → すべて
- `FACT_TO_PROJECT`: PROJECT_FACTS → PROJECTS（明細から案件属性）
- `FACT_TO_CUSTOMER`: PROJECT_FACTS → CUSTOMERS（明細から取引先名）
- `FACT_TO_DEPARTMENT`: PROJECT_FACTS → DEPARTMENTS（明細から部署名）

## 同義語（Synonyms）設計

### 部署関連
- 「部」「部CD」「部コード」「department_code」→ DEPARTMENT_CODE
- 「課」「課CD」「課コード」「section_code」→ SECTION_CODE
- 「グループ」「グループCD」→ GROUP_CODE
- 「本部」「本部コード」→ HEADQUARTERS_CODE

### 取引先関連
- 「顧客」「取引先」「顧客名」「取引先名」→ CUSTOMER_NAME
- 「顧客ID」「取引先ID」「取引先コード」→ CUSTOMER_ID

### 案件関連
- 「案件」「案件No」「案件番号」→ PROJECT_NUMBER
- 「枝番」→ BRANCH_NUMBER
- 「年度」→ FISCAL_YEAR

### 金額関連
- 「売上」「請求」「金額」「請求金額」「売上金額」→ INVOICE_AMOUNT
- 「税込」「税込金額」→ INVOICE_AMOUNT_WITH_TAX
- 「消費税」「税額」→ TAX_AMOUNT

### 日付関連
- 「計上月」「売上月」→ ACCOUNTING_MONTH
- 「受注日」「オーダ日」→ ORDER_DATE

## 利用シーン

### 1. 部署別売上集計
**自然言語クエリ例:**
- 「営業部の2024年度の売上合計を教えて」
- 「本部別の売上ランキングを表示」
- 「第一営業課の今月の請求金額は？」

**想定SQL変換:**
```sql
SELECT 
    d.COMBINED_NAME,
    SUM(i.INVOICE_AMOUNT) AS total_sales
FROM INVOICES i
LEFT JOIN PROJECTS p ON i.PROJECT_NUMBER = p.PROJECT_NUMBER
LEFT JOIN DEPARTMENTS d ON p.DEPARTMENT_ID = d.DEPARTMENT_ID
WHERE d.COMBINED_NAME LIKE '%営業%'
  AND p.FISCAL_YEAR = '2024'
GROUP BY d.COMBINED_NAME
```

### 2. 取引先別分析
**自然言語クエリ例:**
- 「〇〇株式会社の売上推移を教えて」
- 「取引先ごとの請求件数トップ10」

**想定SQL変換:**
```sql
SELECT 
    c.CUSTOMER_NAME,
    i.ACCOUNTING_MONTH,
    SUM(i.INVOICE_AMOUNT) AS monthly_sales
FROM INVOICES i
LEFT JOIN PROJECTS p ON i.PROJECT_NUMBER = p.PROJECT_NUMBER
LEFT JOIN CUSTOMERS c ON p.CUSTOMER_ID = c.CUSTOMER_ID
WHERE c.CUSTOMER_NAME = '〇〇株式会社'
GROUP BY c.CUSTOMER_NAME, i.ACCOUNTING_MONTH
ORDER BY i.ACCOUNTING_MONTH
```

### 3. 期間別集計
**自然言語クエリ例:**
- 「2024年度の月次売上推移」
- 「今期と前期の売上比較」

### 4. 明細レベル検索
**自然言語クエリ例:**
- 「案件番号12345の明細データを表示」
- 「営業部で取引先Aの案件一覧」

## メンテナンス方針

### YAMLファイルの管理
- **Git管理**: master/semanticviews/ 配下で管理
- **S3ステージ同期**: デプロイ時にS3にアップロード
- **バージョニング**: semantic_view_id で履歴管理

### 同義語の追加ルール
- 業務で実際に使われる用語を優先
- 略語・正式名称の両方を登録
- 表記ゆれ（全角半角、大文字小文字）を吸収

### リレーションシップの追加ルール
- JOIN条件が複数の場合はすべて明示
- 外部キー制約がなくても論理的な関連があれば定義
- パフォーマンスを考慮してleft joinを基本とする

## 運用上の注意

### データ品質への依存
- セマンティックビューは物理データの品質に依存する
- NULL値・欠損値が多いとJOINが成立しない
- 正規化VIEWの品質保証が前提

### Cortex Analystの制約
- 複雑すぎるクエリは変換失敗する可能性
- 集計関数の組み合わせに制約あり
- 最大テーブル数・リレーションシップ数に制限

### パフォーマンス考慮
- ファクトテーブルが大きい場合は集計VIEWの追加を検討
- 頻繁に使われるクエリはマテリアライズドビュー化
- 同義語が多すぎるとAmbiguityが発生

## 参考リンク
- [[APP_PRODUCTION.SV_SALES]] - YAMLマスターファイル
- [[APP_PRODUCTION.V_INVOICE]] - 請求マスタVIEW（金額ソース）
- [[APP_PRODUCTION.V_PROJECT_MASTER]] - 案件マスタVIEW
- [[APP_PRODUCTION.V_CUSTOMER_MASTER]] - 取引先マスタVIEW
- [[APP_PRODUCTION.DEPARTMENT_MASTER]] - 部署マスタテーブル
- [[design.APP_PRODUCTION]] - スキーマ設計方針
