CREATE OR REPLACE SCHEMA APP_DEVELOPMENT;
COMMENT ON SCHEMA APP_DEVELOPMENT IS 'アプリケーション開発';

CREATE OR REPLACE SCHEMA APP_PRODUCTION;
COMMENT ON SCHEMA APP_PRODUCTION IS 'アプリケーション本番';

CREATE OR REPLACE SCHEMA DB_DESIGN;
COMMENT ON SCHEMA DB_DESIGN IS 'DB設計用スキーマ';

CREATE OR REPLACE SCHEMA IMPORT;
COMMENT ON SCHEMA IMPORT IS 'データ取込・検査';

CREATE OR REPLACE SCHEMA NAME_RESOLUTION;
COMMENT ON SCHEMA NAME_RESOLUTION IS '名称解決（手動辞書）';

CREATE OR REPLACE TABLE DB_DESIGN.DOCS_OBSIDIAN (
  DOC_ID VARCHAR NOT NULL,
  CONTENT VARCHAR NOT NULL,
  FILE_LAST_MODIFIED TIMESTAMP_LTZ,
  FOLDER VARCHAR NOT NULL,
  INGESTED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP() NOT NULL,
  OBJECT_ID VARCHAR,
  OBJECT_TYPE VARCHAR,
  PATH VARCHAR NOT NULL,
  PRIMARY KEY (DOC_ID)
);
COMMENT ON TABLE DB_DESIGN.DOCS_OBSIDIAN IS 'Obsidian Vault 上の Markdown ファイルを 1 ファイル = 1 レコードで格納する論理テーブル。設計レビュー・検索・Agent 処理の一次ソース。';
COMMENT ON COLUMN DB_DESIGN.DOCS_OBSIDIAN.DOC_ID IS 'Vault 内の Markdown ファイルを一意に識別する ID。INGEST 処理で生成され、論理的な主キーとして使用される。';
COMMENT ON COLUMN DB_DESIGN.DOCS_OBSIDIAN.CONTENT IS 'Markdown ファイルの全文（frontmatter を含む）を文字列として格納した内容。Cortex Search / Agent の唯一の参照対象。';
COMMENT ON COLUMN DB_DESIGN.DOCS_OBSIDIAN.FILE_LAST_MODIFIED IS 'Vault 上の元ファイルが最後に更新された時刻。S3 上のメタデータに基づく。';
COMMENT ON COLUMN DB_DESIGN.DOCS_OBSIDIAN.FOLDER IS 'PATH から抽出した最上位フォルダ名（例: master, design, reviews, views, templates）。分類・検索・スコープ判定用。';
COMMENT ON COLUMN DB_DESIGN.DOCS_OBSIDIAN.INGESTED_AT IS '当該レコードが Snowflake に取り込まれた時刻。INGEST 実行時に自動設定される。';
COMMENT ON COLUMN DB_DESIGN.DOCS_OBSIDIAN.OBJECT_ID IS '設計オブジェクトに紐づく論理 ID（schema_id / table_id / column_id / view_id 等）。frontmatter 由来。';
COMMENT ON COLUMN DB_DESIGN.DOCS_OBSIDIAN.OBJECT_TYPE IS 'OBJECT_ID が指すオブジェクト種別（schema / table / column / view など）。frontmatter 由来。';
COMMENT ON COLUMN DB_DESIGN.DOCS_OBSIDIAN.PATH IS 'Vault ルートからの相対パス。master/columns/... など Obsidian 上の実パスを保持する。';

CREATE OR REPLACE TABLE DB_DESIGN.PROFILE_RESULTS (
  RUN_ID VARCHAR NOT NULL,
  TARGET_COLUMN VARCHAR NOT NULL,
  AS_OF_AT TIMESTAMP_LTZ NOT NULL,
  METRICS VARIANT NOT NULL,
  TARGET_DB VARCHAR NOT NULL,
  TARGET_SCHEMA VARCHAR NOT NULL,
  TARGET_TABLE VARCHAR NOT NULL,
  PRIMARY KEY (RUN_ID, TARGET_COLUMN)
);
COMMENT ON TABLE DB_DESIGN.PROFILE_RESULTS IS 'プロファイル処理により算出されたカラム単位の計測結果を保持するテーブル。1行が1回の実行（run）における1カラム分の結果を表し、品質確認・比較・監査・設計レビューの根拠として利用される。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RESULTS.RUN_ID IS 'プロファイル実行（run）を識別するID。PROFILE_RUNS.RUN_ID と対応し、どの実行に紐づく結果かを示す。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RESULTS.TARGET_COLUMN IS '計測対象となったカラム名。RUN_ID と組み合わせて、1回の実行における結果行を一意に識別する。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RESULTS.AS_OF_AT IS '計測対象データの論理時点。実行時刻そのものではなく、「どの時点のデータを計測したか」を表す。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RESULTS.METRICS IS 'カラム単位のプロファイル計測結果を格納するVARIANT。NULL率、件数、distinct数、最小値・最大値などを柔軟に保持する。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RESULTS.TARGET_DB IS '計測対象となったデータベース名。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RESULTS.TARGET_SCHEMA IS '計測対象となったスキーマ名。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RESULTS.TARGET_TABLE IS '計測対象となったテーブル名。';

CREATE OR REPLACE TABLE DB_DESIGN.PROFILE_RUNS (
  RUN_ID VARCHAR NOT NULL,
  FINISHED_AT TIMESTAMP_LTZ,
  GIT_COMMIT VARCHAR,
  NOTE VARCHAR,
  ROLE_NAME VARCHAR,
  SAMPLE_PCT FLOAT,
  STARTED_AT TIMESTAMP_LTZ NOT NULL,
  STATUS VARCHAR NOT NULL,
  TARGET_DB VARCHAR NOT NULL,
  TARGET_SCHEMA VARCHAR NOT NULL,
  TARGET_TABLE VARCHAR NOT NULL,
  WAREHOUSE_NAME VARCHAR,
  PRIMARY KEY (RUN_ID)
);
COMMENT ON TABLE DB_DESIGN.PROFILE_RUNS IS '実行管理テーブル';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.RUN_ID IS 'プロファイル実行（run）を一意に識別するID。1回の PROFILE_TABLE 実行につき1つ発行される。原則としてUUID等によりアプリケーション側で一意生成され、同一RUN_IDでの再実行時は結果を上書きする。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.FINISHED_AT IS 'プロファイル実行終了時刻。実行中（STATUS=''RUNNING''）はNULL、完了時（SUCCEEDED / FAILED）に設定される。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.GIT_COMMIT IS 'プロファイル実行に使用されたコードのGitコミットID。手動実行やローカル実行など、コミット情報を取得できない場合はNULLとなる。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.NOTE IS '実行に関する補足情報やユーザメモ。異常終了時にはエラーコードおよびエラーメッセージが追記されることがある。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.ROLE_NAME IS 'プロファイル実行時のセッションロール名。実行ユーザやジョブの権限確認・監査目的で記録する。ロールが明示されていない場合はNULLとなる。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.SAMPLE_PCT IS 'プロファイル実行時に使用したサンプリング率（BERNOULLI）。NULLの場合は全件を対象にプロファイルを実行する。値は 0〜100 の割合を想定する。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.STARTED_AT IS 'プロファイル実行開始時刻。STATUS=''RUNNING'' となった時点で設定される。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.STATUS IS 'プロファイル実行の状態。許可値は以下の通り：RUNNING : 実行中SUCCEEDED : 正常終了FAILED : 異常終了状態遷移は原則として RUNNING → SUCCEEDED | FAILED のみとする。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.TARGET_DB IS 'プロファイル対象テーブルが属するデータベース名。実行対象を一意に特定するために必須。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.TARGET_SCHEMA IS 'プロファイル対象テーブルが属するスキーマ名。TARGET_DB・TARGET_TABLE と組み合わせて実行対象を特定する。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.TARGET_TABLE IS 'プロファイル対象のテーブル名。同一テーブルに対して複数回のプロファイル実行履歴を保持する。';
COMMENT ON COLUMN DB_DESIGN.PROFILE_RUNS.WAREHOUSE_NAME IS 'プロファイル実行時に使用されたSnowflakeウェアハウス名。実行時に明示されていない、または自動選択された場合はNULLとなる。';

CREATE OR REPLACE TABLE APP_PRODUCTION.DEPARTMENT_MASTER (
  ACCOUNTING_DEPARTMENT_CODE VARCHAR,
  COMBINED_NAME VARCHAR,
  COMBINED_SHORT_NAME VARCHAR,
  DEPARTMENT_CATEGORY VARCHAR,
  DEPARTMENT_CODE VARCHAR,
  DEPARTMENT_ID VARCHAR,
  DEPARTMENT_SECTION_CODE VARCHAR,
  DIVISION_CODE VARCHAR,
  FISCAL_YEAR VARCHAR,
  FULL_NAME VARCHAR,
  GENERAL_DEPARTMENT_CODE VARCHAR,
  GROUP_CODE VARCHAR,
  HEADQUARTERS_CODE VARCHAR,
  ID VARCHAR,
  SECTION_CODE VARCHAR,
  SHORT_NAME VARCHAR
);
COMMENT ON TABLE APP_PRODUCTION.DEPARTMENT_MASTER IS '部署マスタ（年度別）CSV取込用テーブル';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.ACCOUNTING_DEPARTMENT_CODE IS '経理部門CD';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.COMBINED_NAME IS '組合せ名称';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.COMBINED_SHORT_NAME IS '組合せ略称';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.DEPARTMENT_CATEGORY IS '部署区分';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.DEPARTMENT_CODE IS '部CD';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.DEPARTMENT_ID IS '部署ID';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.DEPARTMENT_SECTION_CODE IS '部課CD';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.DIVISION_CODE IS '部門CD';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.FISCAL_YEAR IS '年度';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.FULL_NAME IS '正式名称';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.GENERAL_DEPARTMENT_CODE IS '統括部CD';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.GROUP_CODE IS 'グループCD';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.HEADQUARTERS_CODE IS '本部CD';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.ID IS 'レコードID';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.SECTION_CODE IS '課CD';
COMMENT ON COLUMN APP_PRODUCTION.DEPARTMENT_MASTER.SHORT_NAME IS '略称';

CREATE OR REPLACE TABLE APP_PRODUCTION.ANKEN_MEISAI (
  ACCOUNTING_MONTH VARCHAR,
  ACTIVE_FLAG VARCHAR,
  AMOUNT NUMBER(15,2) DEFAULT 0,
  BRANCH_NUMBER VARCHAR,
  CUSTOMER_ID VARCHAR,
  CUSTOMER_NAME VARCHAR,
  CUSTOMER_ORDER_NUMBER VARCHAR,
  CUSTOMER_QUOTE_REQUEST_NUMBER VARCHAR,
  DEPARTMENT_ID VARCHAR,
  DEPARTMENT_NAME VARCHAR,
  DEPARTMENT_SECTION_SHORT_NAME VARCHAR,
  DEPARTMENT_SHORT_NAME VARCHAR,
  DIVISION_CODE VARCHAR,
  FISCAL_YEAR VARCHAR,
  GROUP_SHORT_NAME VARCHAR,
  ID VARCHAR,
  INVOICE_NUMBER VARCHAR,
  ORDER_NAME VARCHAR,
  ORDER_NUMBER VARCHAR,
  PROJECT_NAME VARCHAR,
  PROJECT_NUMBER VARCHAR,
  RANK VARCHAR,
  SALES_CATEGORY VARCHAR,
  SALES_DELIVERY_FLAG VARCHAR,
  SECTION_NAME VARCHAR,
  SUBJECT VARCHAR,
  WORK_END_DATE VARCHAR,
  WORK_START_DATE VARCHAR
);
COMMENT ON TABLE APP_PRODUCTION.ANKEN_MEISAI IS '案件明細CSV取込用テーブル';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.ACCOUNTING_MONTH IS '計上月度';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.ACTIVE_FLAG IS '有効無効フラグ';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.AMOUNT IS '金額';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.BRANCH_NUMBER IS '枝番';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.CUSTOMER_ID IS '取引先ID';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.CUSTOMER_NAME IS '取引先名';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.CUSTOMER_ORDER_NUMBER IS '顧客注文番号';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.CUSTOMER_QUOTE_REQUEST_NUMBER IS '顧客見積依頼番号';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.DEPARTMENT_ID IS '部署ID';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.DEPARTMENT_NAME IS '部署名';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.DEPARTMENT_SECTION_SHORT_NAME IS '部課名（略称）';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.DEPARTMENT_SHORT_NAME IS '部名（略称）';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.DIVISION_CODE IS '部門CD';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.FISCAL_YEAR IS '年度';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.GROUP_SHORT_NAME IS 'グループ名（略称）';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.ID IS 'レコードID';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.INVOICE_NUMBER IS '請求番号';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.ORDER_NAME IS 'オーダ名';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.ORDER_NUMBER IS 'オーダ番号';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.PROJECT_NAME IS '案件名';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.PROJECT_NUMBER IS '案件番号';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.RANK IS 'ランク';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.SALES_CATEGORY IS '売上区分';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.SALES_DELIVERY_FLAG IS '売上渡しフラグ';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.SECTION_NAME IS '課名（正式）';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.SUBJECT IS '件名';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.WORK_END_DATE IS '作業終了日';
COMMENT ON COLUMN APP_PRODUCTION.ANKEN_MEISAI.WORK_START_DATE IS '作業開始日';

CREATE OR REPLACE TABLE APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL (
  ALIAS_NORMALIZED VARCHAR NOT NULL,
  ALIAS_RAW VARCHAR NOT NULL,
  CONFIDENCE NUMBER(3,2) DEFAULT 0.7 NOT NULL,
  CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() NOT NULL,
  CREATED_BY VARCHAR,
  ENTITY_ID VARCHAR NOT NULL,
  ENTITY_NAME VARCHAR NOT NULL,
  ENTITY_TYPE VARCHAR NOT NULL,
  IS_ACTIVE BOOLEAN DEFAULT true NOT NULL,
  NOTE VARCHAR NOT NULL,
  PRIORITY NUMBER(5,0) DEFAULT 100 NOT NULL,
  UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() NOT NULL
);
COMMENT ON TABLE APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL IS '人手で管理するエンティティ別名テーブル（AUTO生成で拾えない略称・社内用語・例外対応用）';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.ALIAS_NORMALIZED IS 'NORMALIZE_JA / NORMALIZE_JA_DEPT 適用後の文字列';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.ALIAS_RAW IS '人が入力・承認した別名（例: DI, デジイノ, 本社DI）';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.CONFIDENCE IS 'この別名の信頼度（0.0〜1.0、人手追加は0.6〜0.8推奨）';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.CREATED_BY IS '追加したユーザー/システム名';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.ENTITY_ID IS '対応するマスタのID（共通利用のためvarchar）';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.ENTITY_NAME IS '正式名称（UI表示・確認用）';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.ENTITY_TYPE IS 'department / customer / project / order';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.IS_ACTIVE IS 'falseで無効化（削除せず履歴保持）';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.NOTE IS '補足（由来、使いどころ、注意点など）';
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL.PRIORITY IS '小さいほど優先（MANUALはAUTOより必ず小さく）';

CREATE OR REPLACE TABLE APP_PRODUCTION.DIM_ENTITY_ALIAS (
  alias_normalized VARCHAR NOT NULL,
  entity_type VARCHAR NOT NULL,
  alias_raw VARCHAR,
  confidence NUMBER(3,2) NOT NULL,
  entity_id VARCHAR NOT NULL,
  entity_name VARCHAR,
  is_active BOOLEAN NOT NULL,
  priority NUMBER(5,0) DEFAULT 1000 NOT NULL,
  refresh_run_id VARCHAR NOT NULL,
  refreshed_at timestamp_ntz NOT NULL,
  PRIMARY KEY (alias_normalized, entity_type)
);
COMMENT ON COLUMN APP_PRODUCTION.DIM_ENTITY_ALIAS.refresh_run_id IS 'refresh実行単位の識別子（timestampやUUID）';

-- ==============================
-- VIEWS
-- ==============================
CREATE OR REPLACE VIEW DB_DESIGN.DOCS_OBSIDIAN_V (
  DOC_ID COMMENT 'Obsidianノートの一意ID（1ファイル=1レコード）',
  PATH COMMENT 'Vault内のMarkdownファイルパス（.md付き）',
  FOLDER COMMENT 'Vault内のフォルダパス（PATHの上位）',
  CONTENT COMMENT 'Markdown本文（全文）',
  UPDATED_AT COMMENT 'Snowflakeに取り込まれた時刻（最新判定用）',
  SCOPE COMMENT 'Vault上の大分類（master / design / views / templates / other）',
  FILE_TYPE COMMENT 'ノート種別（master_columns / profile_evidence / agent_review 等）',
  RUN_DATE COMMENT 'EvidenceやReviewの対象日（YYYY-MM-DD）。パスまたはfrontmatterから抽出',
  TARGET_SCHEMA COMMENT '対象スキーマ名（PATH規約から抽出）',
  TARGET_TABLE COMMENT '対象テーブル名（PATH規約から抽出）',
  TARGET_COLUMN COMMENT '対象カラム名（master/columns のみ）'
) COMMENT = 'Obsidian VaultのMarkdownを解析し、Cortex Search/Agent用の検索メタ情報を付与したVIEW'
AS
WITH base AS (
  SELECT
    DOC_ID,
    PATH,
    FOLDER,
    CONTENT,
    INGESTED_AT AS UPDATED_AT
  FROM DB_DESIGN.DOCS_OBSIDIAN
),
parsed AS (
  SELECT
    DOC_ID,
    PATH,
    FOLDER,
    CONTENT,
    UPDATED_AT,

    /* 大分類 */
    CASE
      WHEN PATH LIKE 'master/%'     THEN 'master'
      WHEN PATH LIKE 'design/%'     THEN 'design'
      WHEN PATH LIKE 'views/%'      THEN 'views'
      WHEN PATH LIKE 'templates/%'  THEN 'templates'
      ELSE 'other'
    END AS SCOPE,

    /* 詳細種別（検索・Agent制御用） */
    CASE
      WHEN PATH LIKE 'master/columns/%' THEN 'master_columns'
      WHEN PATH LIKE 'master/tables/%'  THEN 'master_tables'
      WHEN PATH LIKE 'master/schemas/%' THEN 'master_schemas'
      WHEN PATH LIKE 'master/views/%'   THEN 'master_views'
      WHEN PATH LIKE 'master/other/%'   THEN 'master_other'
      WHEN PATH LIKE 'design/reviews/profiles/%' THEN 'profile_evidence'
      WHEN PATH LIKE 'design/reviews/agent/%'    THEN 'agent_review'
      ELSE 'misc'
    END AS FILE_TYPE,

    /* RUN_DATE：パス優先 → frontmatter fallback */
    COALESCE(
      /* profiles */
      IFF(PATH LIKE 'design/reviews/profiles/%',
          REGEXP_SUBSTR(
            PATH,
            'design/reviews/profiles/([0-9]{4}-[0-9]{2}-[0-9]{2})/',
            1, 1, 'e', 1
          ),
          NULL
      ),

      /* agent */
      IFF(PATH LIKE 'design/reviews/agent/%',
          REGEXP_SUBSTR(
            PATH,
            'design/reviews/agent/([0-9]{4}-[0-9]{2}-[0-9]{2})/',
            1, 1, 'e', 1
          ),
          NULL
      ),

      /* frontmatter: review_date */
      REGEXP_SUBSTR(
        CONTENT,
        '^review_date:\\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\\s*$',
        1, 1, 'me', 1
      ),

      /* frontmatter: generated_on */
      REGEXP_SUBSTR(
        CONTENT,
        '^generated_on:\\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\\s*$',
        1, 1, 'me', 1
      )
    ) AS RUN_DATE,

    /* TARGET_SCHEMA */
    IFF(PATH LIKE 'master/columns/%',
        REGEXP_SUBSTR(
          PATH,
          'master/columns/([^.]+)\\.',
          1, 1, 'e', 1
        ),
        COALESCE(
          IFF(PATH LIKE 'design/reviews/profiles/%',
              REGEXP_SUBSTR(
                PATH,
                'design/reviews/profiles/[0-9-]+/([^/]+)/',
                1, 1, 'e', 1
              ),
              NULL
          ),
          IFF(PATH LIKE 'design/reviews/agent/%',
              REGEXP_SUBSTR(
                PATH,
                'design/reviews/agent/[0-9-]+/([^/]+)/',
                1, 1, 'e', 1
              ),
              NULL
          )
        )
    ) AS TARGET_SCHEMA,

    /* TARGET_TABLE */
    IFF(PATH LIKE 'master/columns/%',
        REGEXP_SUBSTR(
          PATH,
          'master/columns/[^.]+\\.([^.]+)\\.',
          1, 1, 'e', 1
        ),
        COALESCE(
          IFF(PATH LIKE 'design/reviews/profiles/%',
              REGEXP_SUBSTR(
                PATH,
                'design/reviews/profiles/[0-9-]+/[^/]+/([^/]+)\\.md$',
                1, 1, 'e', 1
              ),
              NULL
          ),
          IFF(PATH LIKE 'design/reviews/agent/%',
              REGEXP_SUBSTR(
                PATH,
                'design/reviews/agent/[0-9-]+/[^/]+/([^/]+)\\.review\\.md$',
                1, 1, 'e', 1
              ),
              NULL
          )
        )
    ) AS TARGET_TABLE,

    /* TARGET_COLUMN（master/columns のみ） */
    IFF(PATH LIKE 'master/columns/%',
        REGEXP_SUBSTR(
          PATH,
          'master/columns/[^.]+\\.[^.]+\\.([^.]+)\\.md$',
          1, 1, 'e', 1
        ),
        NULL
    ) AS TARGET_COLUMN

  FROM base
)
SELECT
  DOC_ID,
  PATH,
  FOLDER,
  CONTENT,
  UPDATED_AT,
  SCOPE,
  FILE_TYPE,
  RUN_DATE,
  TARGET_SCHEMA,
  TARGET_TABLE,
  TARGET_COLUMN
FROM parsed;

CREATE OR REPLACE VIEW DB_DESIGN.V_PROFILE_RESULTS_LATEST (
  RUN_ID COMMENT 'プロファイル実行ID',
  TARGET_DB COMMENT '対象DB',
  TARGET_SCHEMA COMMENT '対象スキーマ',
  TARGET_TABLE COMMENT '対象テーブル',
  TARGET_COLUMN COMMENT '対象カラム',
  AS_OF_AT COMMENT 'メトリクス算出時点',
  METRICS COMMENT 'プロファイル結果メトリクス（VARIANT想定）'
) COMMENT = '最新（SUCCEEDED）のプロファイル実行に紐づく結果一覧'
AS
WITH LATEST AS (
  SELECT
    TARGET_DB, TARGET_SCHEMA, TARGET_TABLE,
    MAX(STARTED_AT) AS MAX_STARTED_AT
  FROM GBPS253YS_DB.DB_DESIGN.PROFILE_RUNS
  WHERE STATUS = 'SUCCEEDED'
  GROUP BY 1,2,3
),
LATEST_RUN AS (
  SELECT r.*
  FROM GBPS253YS_DB.DB_DESIGN.PROFILE_RUNS r
  JOIN LATEST l
    ON r.TARGET_DB = l.TARGET_DB
   AND r.TARGET_SCHEMA = l.TARGET_SCHEMA
   AND r.TARGET_TABLE  = l.TARGET_TABLE
   AND r.STARTED_AT    = l.MAX_STARTED_AT
)
SELECT
  pr.RUN_ID,
  pr.TARGET_DB,
  pr.TARGET_SCHEMA,
  pr.TARGET_TABLE,
  pr.TARGET_COLUMN,
  pr.AS_OF_AT,
  pr.METRICS
FROM GBPS253YS_DB.DB_DESIGN.PROFILE_RESULTS pr
JOIN LATEST_RUN lr
  ON pr.RUN_ID = lr.RUN_ID;;

CREATE OR REPLACE VIEW APP_PRODUCTION.V_CUSTOMER_MASTER (
  CUSTOMER_ID COMMENT '取引先ID',
  CUSTOMER_NAME COMMENT '取引先名',
  ACTIVE_FLAG COMMENT '有効無効フラグ'
) COMMENT = '取引先マスタVIEW（案件明細から生成）'
AS
SELECT
  customer_id,
  ANY_VALUE(customer_name) AS customer_name,
  MAX(active_flag) AS active_flag
FROM ANKEN_MEISAI
WHERE customer_id IS NOT NULL
GROUP BY customer_id;

CREATE OR REPLACE VIEW APP_PRODUCTION.V_INVOICE (
  INVOICE_KEY COMMENT '請求キー（請求番号 or 仮キー）',
  INVOICE_NUMBER COMMENT '請求番号',
  ORDER_NUMBER COMMENT 'オーダ番号',
  ACCOUNTING_MONTH COMMENT '計上月度',
  AMOUNT COMMENT '請求金額',
  SALES_DELIVERY_FLAG COMMENT '売上渡しフラグ'
) COMMENT = '請求VIEW（請求番号×計上月単位、売上金額集計済）'
AS
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
    accounting_month;

CREATE OR REPLACE VIEW APP_PRODUCTION.V_ORDER_MASTER (
  ORDER_NUMBER COMMENT 'オーダ番号',
  ORDER_NAME COMMENT 'オーダ名',
  PROJECT_NUMBER COMMENT '案件番号',
  BRANCH_NUMBER COMMENT '枝番',
  FISCAL_YEAR COMMENT '年度',
  CUSTOMER_ORDER_NUMBER COMMENT '顧客注文番号'
) COMMENT = 'オーダマスタVIEW（オーダ番号単位）'
AS
SELECT
    order_number,
    ANY_VALUE(order_name) AS order_name,
    ANY_VALUE(project_number) AS project_number,
    ANY_VALUE(branch_number) AS branch_number,
    ANY_VALUE(fiscal_year) AS fiscal_year,
    ANY_VALUE(customer_order_number) AS customer_order_number
FROM ANKEN_MEISAI
WHERE order_number IS NOT NULL
GROUP BY order_number;

CREATE OR REPLACE VIEW APP_PRODUCTION.V_PROJECT_FACT (
  ID COMMENT 'レコードID',
  PROJECT_NUMBER COMMENT '案件番号',
  BRANCH_NUMBER COMMENT '枝番',
  FISCAL_YEAR COMMENT '年度',
  ORDER_NUMBER COMMENT 'オーダ番号',
  INVOICE_NUMBER COMMENT '請求番号',
  CUSTOMER_QUOTE_REQUEST_NUMBER COMMENT '顧客見積依頼番号',
  ACTIVE_FLAG COMMENT '有効無効フラグ'
) COMMENT = '案件ファクトVIEW（生データ粒度を保持）'
AS
SELECT
    id,
    project_number,
    branch_number,
    fiscal_year,
    order_number,
    invoice_number,
    customer_quote_request_number,
    active_flag
FROM ANKEN_MEISAI;

CREATE OR REPLACE VIEW APP_PRODUCTION.V_PROJECT_MASTER (
  PROJECT_NUMBER COMMENT '案件番号',
  BRANCH_NUMBER COMMENT '枝番',
  FISCAL_YEAR COMMENT '年度',
  PROJECT_NAME COMMENT '案件名',
  SUBJECT COMMENT '件名',
  SALES_CATEGORY COMMENT '売上区分',
  RANK COMMENT 'ランク',
  CUSTOMER_ID COMMENT '取引先ID',
  DEPARTMENT_ID COMMENT '部署ID',
  WORK_START_DATE COMMENT '作業開始日',
  WORK_END_DATE COMMENT '作業終了日'
) COMMENT = '案件マスタVIEW（案件番号＋枝番＋年度単位）'
AS
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
    fiscal_year;

CREATE OR REPLACE VIEW APP_PRODUCTION.V_ENTITY_ALIAS_AUTO (
  ALIAS_RAW COMMENT '別名（正規化前の生文字列）',
  ALIAS_NORMALIZED COMMENT '正規化後の別名（NORMALIZE_JA / NORMALIZE_JA_DEPT 適用後）',
  ENTITY_TYPE COMMENT 'エンティティ種別（department / customer / project / order）',
  ENTITY_ID COMMENT 'エンティティID（共通利用のため varchar）',
  ENTITY_NAME COMMENT '正式名称（表示用）',
  CONFIDENCE COMMENT '別名の信頼度（0.0〜1.0）',
  PRIORITY COMMENT '優先度（小さいほど優先）',
  IS_ACTIVE COMMENT '優先度（小さいほど優先）'
) COMMENT = '自動生成エイリアス辞書（部署/顧客/案件/オーダー）。手動辞書と統合して名称解決に利用する。'
AS
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
FROM GBPS253YS_DB.APP_PRODUCTION.V_ORDER_MASTER;

CREATE OR REPLACE VIEW APP_PRODUCTION.V_ENTITY_ALIAS_ALL (
  ALIAS_RAW COMMENT '別名（正規化前の生文字列）',
  ALIAS_NORMALIZED COMMENT '正規化後の別名（NORMALIZE_JA / NORMALIZE_JA_DEPT 適用後）',
  ENTITY_TYPE COMMENT 'エンティティ種別（department / customer / project / order）',
  ENTITY_ID COMMENT 'エンティティID（共通利用のため varchar）',
  ENTITY_NAME COMMENT '正式名称（表示用）',
  CONFIDENCE COMMENT '別名の信頼度（0.0〜1.0）',
  PRIORITY COMMENT '優先度（小さいほど優先）',
  IS_ACTIVE COMMENT '優先度（小さいほど優先）'
) COMMENT = '名称解決用エイリアス辞書（MANUAL + AUTO 統合）。alias_normalized×entity_type ごとに優先度/信頼度で1件に正規化する。'
AS
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
  FROM GBPS253YS_DB.APP_PRODUCTION.DIM_ENTITY_ALIAS_MANUAL
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
  ) = 1;

-- ==============================
-- OTHER OBJECTS
-- ==============================
-- PROCEDURE: DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL
CREATE OR REPLACE PROCEDURE DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL(
    P_SOURCE_DB         VARCHAR,
    P_SOURCE_SCHEMA     VARCHAR,
    P_SOURCE_VIEW       VARCHAR,
    P_TARGET_DB         VARCHAR,
    P_RUN_DATE          VARCHAR,   -- YYYY-MM-DD
    P_VAULT_PREFIX      VARCHAR,   -- reviews/profiles
    P_TARGET_SCHEMA     VARCHAR    -- NULL = all
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
  -- view
  v_view_fqn           STRING;

  -- sql
  v_sql                STRING;

  -- paths
  v_path_md            STRING;
  v_path_raw_prefix    STRING;
  v_path_err           STRING;

  -- counters
  v_total              NUMBER;
  v_i                  NUMBER;
  v_ok                 NUMBER DEFAULT 0;
  v_failed             NUMBER DEFAULT 0;

  -- current table
  v_schema             STRING;
  v_table              STRING;
  v_schema_esc         STRING;
  v_table_esc          STRING;

  -- literals
  v_target_db_esc      STRING;
  v_schema_lit         STRING;

  -- raw file info
  v_raw_rel_prefix     STRING;
  v_raw_rel_file       STRING;

  -- return json
  v_target_db_json     STRING;
  v_run_date_json      STRING;
  v_vault_prefix_json  STRING;
BEGIN
  ------------------------------------------------------------------
  -- init
  ------------------------------------------------------------------
  v_view_fqn := P_SOURCE_DB || '.' || P_SOURCE_SCHEMA || '.' || P_SOURCE_VIEW;

  v_target_db_esc := REPLACE(P_TARGET_DB, '''', '''''');

  v_schema_lit :=
    CASE
      WHEN P_TARGET_SCHEMA IS NULL THEN 'NULL'
      ELSE '''' || REPLACE(P_TARGET_SCHEMA, '''', '''''') || ''''
    END;

  v_target_db_json    := REPLACE(P_TARGET_DB, '"', '\\"');
  v_run_date_json     := REPLACE(P_RUN_DATE,  '"', '\\"');
  v_vault_prefix_json := REPLACE(P_VAULT_PREFIX, '"', '\\"');

  ------------------------------------------------------------------
  -- target tables
  ------------------------------------------------------------------
  EXECUTE IMMEDIATE '
    CREATE OR REPLACE TEMP TABLE TMP_TARGETS (
      TARGET_SCHEMA STRING,
      TARGET_TABLE  STRING
    )';

  v_sql :=
    'INSERT INTO TMP_TARGETS
     SELECT DISTINCT TARGET_SCHEMA, TARGET_TABLE
     FROM ' || v_view_fqn || '
     WHERE TARGET_DB = ''' || v_target_db_esc || '''
       AND (' || v_schema_lit || ' IS NULL OR TARGET_SCHEMA = ' || v_schema_lit || ')';

  EXECUTE IMMEDIATE v_sql;

  SELECT COUNT(*) INTO v_total FROM TMP_TARGETS;

  ------------------------------------------------------------------
  -- loop
  ------------------------------------------------------------------
  v_i := 1;

  WHILE (v_i <= v_total) DO
    -- pick 1 table
    v_sql :=
      'CREATE OR REPLACE TEMP TABLE TMP_ONE AS
       SELECT TARGET_SCHEMA, TARGET_TABLE
       FROM (
         SELECT TARGET_SCHEMA, TARGET_TABLE,
                ROW_NUMBER() OVER (ORDER BY TARGET_SCHEMA, TARGET_TABLE) AS RN
         FROM TMP_TARGETS
       )
       WHERE RN = ' || TO_VARCHAR(v_i);

    EXECUTE IMMEDIATE v_sql;

    SELECT TARGET_SCHEMA, TARGET_TABLE
      INTO v_schema, v_table
    FROM TMP_ONE;

    v_schema_esc := REPLACE(v_schema, '''', '''''');
    v_table_esc  := REPLACE(v_table,  '''', '''''');

    -- paths
    v_path_md :=
      '@OBSIDIAN_VAULT_STAGE/' || P_VAULT_PREFIX || '/' || P_RUN_DATE || '/'
      || v_schema || '/' || v_table || '.md';

    v_path_raw_prefix :=
      '@OBSIDIAN_VAULT_STAGE/' || P_VAULT_PREFIX || '/' || P_RUN_DATE || '/'
      || v_schema || '/' || v_table || '.raw.json';

    v_path_err :=
      '@OBSIDIAN_VAULT_STAGE/' || P_VAULT_PREFIX || '/' || P_RUN_DATE || '/'
      || v_schema || '/' || v_table || '.error.md';

    v_raw_rel_prefix :=
      P_VAULT_PREFIX || '/' || P_RUN_DATE || '/' || v_schema || '/' || v_table || '.raw.json';

    v_raw_rel_file := v_raw_rel_prefix || '_0_0_0';

    ----------------------------------------------------------------
    -- per table (continue on error)
    ----------------------------------------------------------------
    BEGIN
      --------------------------------------------------------------
      -- summary md
      --------------------------------------------------------------
      EXECUTE IMMEDIATE 'CREATE OR REPLACE TEMP TABLE TMP_MD (LINE STRING)';

      v_sql :=
'INSERT INTO TMP_MD (LINE)
SELECT LINE
FROM (
  WITH base AS (
    SELECT *
    FROM ' || v_view_fqn || '
    WHERE TARGET_DB     = ''' || v_target_db_esc || '''
      AND TARGET_SCHEMA = ''' || v_schema_esc || '''
      AND TARGET_TABLE  = ''' || v_table_esc || '''
  ),
  t AS (
    SELECT
      ANY_VALUE(TARGET_DB) AS TARGET_DB,
      ANY_VALUE(TARGET_SCHEMA) AS TARGET_SCHEMA,
      ANY_VALUE(TARGET_TABLE) AS TARGET_TABLE,
      MAX(AS_OF_AT) AS AS_OF_AT,
      MAX(RUN_ID) AS RUN_ID,
      MAX(TRY_TO_NUMBER(TO_VARCHAR(METRICS:"row_count"))) AS ROW_COUNT
    FROM base
  ),
  c AS (
    SELECT
      TARGET_COLUMN AS COL,
      TRY_TO_DOUBLE(TO_VARCHAR(METRICS:"null_rate")) AS NULL_RATE,
      TRY_TO_NUMBER(TO_VARCHAR(METRICS:"distinct_count")) AS DISTINCT_CNT
    FROM base
  )
  SELECT LINE
  FROM (
    SELECT 10, ''---'' FROM t
    UNION ALL SELECT 20, ''type: profile_evidence'' FROM t
    UNION ALL SELECT 30, ''target_db: '' || TARGET_DB FROM t
    UNION ALL SELECT 40, ''target_schema: '' || TARGET_SCHEMA FROM t
    UNION ALL SELECT 50, ''target_table: '' || TARGET_TABLE FROM t
    UNION ALL SELECT 60, ''as_of_at: '' || TO_VARCHAR(AS_OF_AT, ''YYYY-MM-DD"T"HH24:MI:SS'') FROM t
    UNION ALL SELECT 70, ''run_id: '' || COALESCE(RUN_ID, ''null'') FROM t
    UNION ALL SELECT 80, ''row_count: '' || COALESCE(TO_VARCHAR(ROW_COUNT), ''null'') FROM t
    UNION ALL SELECT 90, ''generated_on: ' || REPLACE(P_RUN_DATE, '''', '''''') || ''' FROM t
    UNION ALL SELECT 100, ''---'' FROM t
    UNION ALL SELECT 110, '' '' FROM t

    UNION ALL SELECT 120, ''# Profile Evidence: '' || TARGET_SCHEMA || ''.'' || TARGET_TABLE FROM t
    UNION ALL SELECT 130, '' '' FROM t

    UNION ALL SELECT 200, ''## Raw metrics'' FROM t
    UNION ALL SELECT 210, ''- Prefix: `' || REPLACE(v_raw_rel_prefix, '''', '''''') || '`'' FROM t
    UNION ALL SELECT 220, ''- File: `' || REPLACE(v_raw_rel_file, '''', '''''') || '`'' FROM t
    UNION ALL SELECT 230, '' '' FROM t

    UNION ALL SELECT 300, ''## Columns (summary)'' FROM t
    UNION ALL SELECT 310, ''| column | null_rate | distinct_count |'' FROM t
    UNION ALL SELECT 320, ''|---|---:|---:|'' FROM t

    UNION ALL
    SELECT
      400 + ROW_NUMBER() OVER (ORDER BY COL),
      ''| `'' || COL || ''` | '' ||
      COALESCE(TO_VARCHAR(ROUND(NULL_RATE * 100, 2)) || ''%'', ''null'') || '' | '' ||
      COALESCE(TO_VARCHAR(DISTINCT_CNT), ''null'') || '' |''
    FROM c
  ) x(LINE_NO, LINE)
  ORDER BY 1
)';

      EXECUTE IMMEDIATE v_sql;

      EXECUTE IMMEDIATE
'COPY INTO ' || v_path_md || '
 FROM TMP_MD
 FILE_FORMAT = (
   TYPE = CSV
   FIELD_DELIMITER = ''\u0001''
   RECORD_DELIMITER = ''\n''
   COMPRESSION = NONE
 )
 HEADER = FALSE
 SINGLE = TRUE
 OVERWRITE = TRUE
 INCLUDE_QUERY_ID = FALSE';

      --------------------------------------------------------------
      -- raw json
      --------------------------------------------------------------
      EXECUTE IMMEDIATE 'CREATE OR REPLACE TEMP TABLE TMP_RAW (LINE STRING)';

      v_sql :=
'INSERT INTO TMP_RAW (LINE)
SELECT TO_JSON(
  OBJECT_CONSTRUCT(
    ''target_db'', ''' || v_target_db_esc || ''',
    ''target_schema'', ''' || v_schema_esc || ''',
    ''target_table'', ''' || v_table_esc || ''',
    ''run_date'', ''' || REPLACE(P_RUN_DATE, '''', '''''') || ''',
    ''metrics'', ARRAY_AGG(
      OBJECT_CONSTRUCT(
        ''column'', TARGET_COLUMN,
        ''as_of_at'', AS_OF_AT,
        ''run_id'', RUN_ID,
        ''metrics'', METRICS
      )
    )
  )
)
FROM ' || v_view_fqn || '
WHERE TARGET_DB     = ''' || v_target_db_esc || '''
  AND TARGET_SCHEMA = ''' || v_schema_esc || '''
  AND TARGET_TABLE  = ''' || v_table_esc || '''';

      EXECUTE IMMEDIATE v_sql;

      EXECUTE IMMEDIATE
'COPY INTO ' || v_path_raw_prefix || '
 FROM TMP_RAW
 FILE_FORMAT = (
   TYPE = CSV
   FIELD_DELIMITER = ''\u0001''
   RECORD_DELIMITER = ''\n''
   COMPRESSION = NONE
 )
 HEADER = FALSE
 SINGLE = TRUE
 OVERWRITE = TRUE
 INCLUDE_QUERY_ID = FALSE';

      v_ok := v_ok + 1;

    EXCEPTION
      WHEN OTHER THEN
        v_failed := v_failed + 1;
    END;

    v_i := v_i + 1;
  END WHILE;

  RETURN PARSE_JSON(
    '{' ||
      '"status":"OK",' ||
      '"exported_ok":' || v_ok || ',' ||
      '"exported_failed":' || v_failed || ',' ||
      '"raw_file_suffix":"_0_0_0",' ||
      '"target_db":"' || v_target_db_json || '",' ||
      '"run_date":"'  || v_run_date_json  || '",' ||
      '"vault_prefix":"' || v_vault_prefix_json || '"' ||
    '}'
  );
END;
$$;

-- PROCEDURE: DB_DESIGN.GET_DOCS_BY_PATHS_AGENT
CREATE OR REPLACE PROCEDURE DB_DESIGN.GET_DOCS_BY_PATHS_AGENT(
  PATHS_JSON STRING,
  MAX_CHARS  STRING
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  v_paths     VARIANT;
  v_max_chars NUMBER;
  v_docs      VARIANT;
  v_missing   VARIANT;
BEGIN
  v_max_chars := TRY_TO_NUMBER(MAX_CHARS);

  IF (PATHS_JSON IS NULL OR PATHS_JSON = '') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT('error', 'PATHS_JSON is required (JSON array string)'));
  END IF;

  v_paths := PARSE_JSON(PATHS_JSON);
  IF (TYPEOF(v_paths) <> 'ARRAY') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT(
      'error',
      'PATHS_JSON must be a JSON array string, e.g. ["design/design.DB_DESIGN.md"]'
    ));
  END IF;

  -- (A) docs（存在するもの）
  WITH req AS (
    SELECT VALUE::STRING AS REQ_PATH
    FROM TABLE(FLATTEN(INPUT => :v_paths))
  ),
  hit AS (
    SELECT
      r.REQ_PATH,
      d.DOC_ID, d.PATH, d.FOLDER, d.SCOPE, d.FILE_TYPE, d.RUN_DATE,
      d.TARGET_SCHEMA, d.TARGET_TABLE, d.TARGET_COLUMN,
      d.UPDATED_AT,
      IFF(:v_max_chars IS NULL, d.CONTENT, LEFT(d.CONTENT, :v_max_chars)) AS CONTENT_TRIM
    FROM req r
    LEFT JOIN DB_DESIGN.DOCS_OBSIDIAN_V d
      ON d.PATH = r.REQ_PATH
  )
  SELECT COALESCE(
           ARRAY_AGG(
             OBJECT_CONSTRUCT(
               'path', PATH,
               'doc_id', DOC_ID,
               'folder', FOLDER,
               'scope', SCOPE,
               'file_type', FILE_TYPE,
               'run_date', RUN_DATE,
               'target_schema', TARGET_SCHEMA,
               'target_table', TARGET_TABLE,
               'target_column', TARGET_COLUMN,
               'updated_at', UPDATED_AT,
               'content', CONTENT_TRIM
             )
           ) WITHIN GROUP (ORDER BY REQ_PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_docs
  FROM hit
  WHERE DOC_ID IS NOT NULL;

  -- (B) missing（見つからないもの）
  WITH req AS (
    SELECT VALUE::STRING AS REQ_PATH
    FROM TABLE(FLATTEN(INPUT => :v_paths))
  ),
  hit AS (
    SELECT
      r.REQ_PATH,
      d.DOC_ID
    FROM req r
    LEFT JOIN DB_DESIGN.DOCS_OBSIDIAN_V d
      ON d.PATH = r.REQ_PATH
  )
  SELECT COALESCE(
           ARRAY_AGG(REQ_PATH) WITHIN GROUP (ORDER BY REQ_PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_missing
  FROM hit
  WHERE DOC_ID IS NULL;

  RETURN TO_VARIANT(OBJECT_CONSTRUCT(
    'count', ARRAY_SIZE(v_docs),
    'docs', v_docs,
    'missing_count', ARRAY_SIZE(v_missing),
    'missing_paths', v_missing
  ));
END;
$$;

-- PROCEDURE: DB_DESIGN.INGEST_VAULT_MD
CREATE OR REPLACE PROCEDURE DB_DESIGN.INGEST_VAULT_MD("STAGE_NAME" VARCHAR, "PATTERN" VARCHAR)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS OWNER
AS '
import hashlib
from snowflake.snowpark.files import SnowflakeFile

BUCKET = "135365622922-snowflake-dbdesign"

def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def _to_relpath(name: str) -> str:
    """
    LIST結果のnameが
      - s3://<bucket>/path...
      - path...
    のどちらでも、ステージ相対パスを返す。
    """
    n = str(name).lstrip("/")
    prefix = f"s3://{BUCKET}/"
    if n.startswith(prefix):
        return n[len(prefix):]
    # 念のため一般形（s3://bucket/...）も扱う
    if n.startswith("s3://"):
        parts = n.split("/", 3)
        # [''s3:'', '''', ''<bucket>'', ''<rest>'']
        return parts[3] if len(parts) >= 4 else ""
    return n

def run(session, stage_name, pattern):
    rows = session.sql(f"LIST {stage_name} PATTERN=''{pattern}''").collect()

    processed = 0
    errors = 0
    samples = []

    for r in rows:
        try:
            d = r.as_dict()
            full_name = d["name"]
            last_modified = d.get("last_modified", None)

            relpath = _to_relpath(full_name)
            if not relpath:
                raise Exception(f"Could not derive relpath from name={full_name}")

            # scoped url: 第2引数はステージ相対パス
            safe_rel = relpath.replace("''", "''''")
            scoped_url = session.sql(
                f"SELECT BUILD_SCOPED_FILE_URL({stage_name}, ''{safe_rel}'') AS U"
            ).collect()[0]["U"]

            with SnowflakeFile.open(scoped_url, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")

            folder = relpath.split("/", 1)[0] if "/" in relpath else relpath
            doc_id = _md5(relpath)

            session.sql(
                """
MERGE INTO DB_DESIGN.DOCS_OBSIDIAN t
USING (
  SELECT
    ? AS DOC_ID,
    ? AS PATH,
    ? AS FOLDER,
    ? AS CONTENT,
    TRY_TO_TIMESTAMP_TZ(?)::TIMESTAMP_LTZ AS FILE_LAST_MODIFIED
) s
ON t.DOC_ID = s.DOC_ID
WHEN MATCHED AND (
     t.FILE_LAST_MODIFIED IS NULL
  OR s.FILE_LAST_MODIFIED IS NULL
  OR s.FILE_LAST_MODIFIED > t.FILE_LAST_MODIFIED
)
THEN UPDATE SET
  PATH = s.PATH,
  FOLDER = s.FOLDER,
  CONTENT = s.CONTENT,
  FILE_LAST_MODIFIED = s.FILE_LAST_MODIFIED,
  INGESTED_AT = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (DOC_ID, PATH, FOLDER, CONTENT, FILE_LAST_MODIFIED)
  VALUES (s.DOC_ID, s.PATH, s.FOLDER, s.CONTENT, s.FILE_LAST_MODIFIED)
                """,
                params=[doc_id, relpath, folder, content, last_modified]
            ).collect()

            processed += 1

        except Exception as e:
            errors += 1
            if len(samples) < 5:
                samples.append({"error": str(e), "name": d.get("name")})

    return {"files_listed": len(rows), "processed": processed, "errors": errors, "samples": samples}
';

-- PROCEDURE: DB_DESIGN.LIST_SCHEMA_RELATED_DOC_PATHS_AGENT
CREATE OR REPLACE PROCEDURE DB_DESIGN.LIST_SCHEMA_RELATED_DOC_PATHS_AGENT(
  TARGET_SCHEMA STRING,
  MAX_TABLES    STRING
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  v_schema         STRING;
  v_max_tables     NUMBER;
  v_base_paths     VARIANT;
  v_table_paths    VARIANT;
  v_all_paths      VARIANT;
  v_paths_dedup    VARIANT;
BEGIN
  v_schema := TARGET_SCHEMA;
  v_max_tables := COALESCE(TRY_TO_NUMBER(MAX_TABLES), 2000);

  IF (v_schema IS NULL OR v_schema = '') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT('error', 'TARGET_SCHEMA is required'));
  END IF;

  -- 上位設計（DB_DESIGNは常に入れる。重複しても後でdistinct）
  v_base_paths := ARRAY_CONSTRUCT(
    'design/design.DB_DESIGN.md',
    'design/design.' || v_schema || '.md'
  );

  -- master/tables を列挙（TARGET_SCHEMA で絞る）
  SELECT COALESCE(
           ARRAY_AGG(PATH) WITHIN GROUP (ORDER BY PATH),
           ARRAY_CONSTRUCT()
         )
    INTO :v_table_paths
  FROM (
    SELECT d.PATH
    FROM DB_DESIGN.DOCS_OBSIDIAN_V d
    WHERE d.PATH LIKE 'master/tables/%'
      AND d.TARGET_SCHEMA = :v_schema
    QUALIFY ROW_NUMBER() OVER (ORDER BY d.PATH) <= :v_max_tables
  );

  v_all_paths := ARRAY_CAT(v_base_paths, v_table_paths);

  -- distinct & sort
  WITH p AS (
    SELECT VALUE::STRING AS path
    FROM TABLE(FLATTEN(INPUT => :v_all_paths))
    WHERE VALUE IS NOT NULL
  )
  SELECT COALESCE(
           ARRAY_AGG(path) WITHIN GROUP (ORDER BY path),
           ARRAY_CONSTRUCT()
         )
    INTO :v_paths_dedup
  FROM (SELECT DISTINCT path FROM p);

  RETURN TO_VARIANT(OBJECT_CONSTRUCT(
    'target_schema', v_schema,
    'count', ARRAY_SIZE(v_paths_dedup),
    'paths', v_paths_dedup,
    'paths_json', TO_JSON(v_paths_dedup)
  ));
END;
$$;

-- PROCEDURE: DB_DESIGN.LIST_TABLE_RELATED_DOC_PATHS_AGENT
CREATE OR REPLACE PROCEDURE DB_DESIGN.LIST_TABLE_RELATED_DOC_PATHS_AGENT(
  TARGET_SCHEMA    STRING,
  TARGET_TABLE     STRING,
  INCLUDE_COLUMNS  STRING, -- "true"/"false"
  MAX_COLUMNS      STRING
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  v_schema      STRING;
  v_table       STRING;
  v_inc_cols    BOOLEAN;
  v_max_cols    NUMBER;

  v_base_paths  VARIANT;
  v_col_paths   VARIANT;
  v_all_paths   VARIANT;
  v_paths_dedup VARIANT;
BEGIN
  v_schema := TARGET_SCHEMA;
  v_table  := TARGET_TABLE;
  v_inc_cols := IFF(UPPER(COALESCE(INCLUDE_COLUMNS,'FALSE')) IN ('TRUE','1','YES','Y'), TRUE, FALSE);
  v_max_cols := COALESCE(TRY_TO_NUMBER(MAX_COLUMNS), 5000);

  IF (v_schema IS NULL OR v_schema = '') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT('error', 'TARGET_SCHEMA is required'));
  END IF;
  IF (v_table IS NULL OR v_table = '') THEN
    RETURN TO_VARIANT(OBJECT_CONSTRUCT('error', 'TARGET_TABLE is required'));
  END IF;

  v_base_paths := ARRAY_CONSTRUCT(
    'design/design.DB_DESIGN.md',
    'design/design.' || v_schema || '.md',
    'master/tables/' || v_schema || '.' || v_table || '.md',
    'design/' || v_schema || '/design.' || v_table || '.md'
  );

  IF (v_inc_cols) THEN
    SELECT COALESCE(
             ARRAY_AGG(PATH) WITHIN GROUP (ORDER BY PATH),
             ARRAY_CONSTRUCT()
           )
      INTO :v_col_paths
    FROM (
      SELECT d.PATH
      FROM DB_DESIGN.DOCS_OBSIDIAN_V d
      WHERE d.PATH LIKE 'master/columns/%'
        AND d.TARGET_SCHEMA = :v_schema
        AND d.TARGET_TABLE  = :v_table
      QUALIFY ROW_NUMBER() OVER (ORDER BY d.PATH) <= :v_max_cols
    );
  ELSE
    v_col_paths := ARRAY_CONSTRUCT();
  END IF;

  v_all_paths := ARRAY_CAT(v_base_paths, v_col_paths);

  WITH p AS (
    SELECT VALUE::STRING AS path
    FROM TABLE(FLATTEN(INPUT => :v_all_paths))
    WHERE VALUE IS NOT NULL
  )
  SELECT COALESCE(
           ARRAY_AGG(path) WITHIN GROUP (ORDER BY path),
           ARRAY_CONSTRUCT()
         )
    INTO :v_paths_dedup
  FROM (SELECT DISTINCT path FROM p);

  RETURN TO_VARIANT(OBJECT_CONSTRUCT(
    'target_schema', v_schema,
    'target_table', v_table,
    'include_columns', v_inc_cols,
    'count', ARRAY_SIZE(v_paths_dedup),
    'paths', v_paths_dedup,
    'paths_json', TO_JSON(v_paths_dedup)
  ));
END;
$$;

-- AGENT: DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT
CREATE OR REPLACE AGENT DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT
  COMMENT = 'Obsidian Vault（master/design/reviews）を根拠に、SP（PATH列挙→本文取得）だけで静的レビューする（Search不要・NULL引数禁止）'
  PROFILE = '{"display_name":"OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT"}'
FROM SPECIFICATION
$$
models:
  orchestration: auto

orchestration:
  budget:
    seconds: 900
    tokens: 409600

instructions:
  orchestration: >
    あなたはデータベース設計レビュー専用のアシスタントです。
    設計の正本は Obsidian Vault（Markdown）であり、ストアドプロシージャ（generic tool）のみを使って静的レビューを行います。
    DBの実データ/DDLへの直接参照は禁止です。Search（Cortex Search）は使いません。

    【最重要】思考ステップ（Planning等）は出力しない。最終出力は response 指定のMarkdownのみ。

    【NULL禁止（最重要）】
    - generic tool 呼び出しで JSON の null は使用禁止（<nil> で失敗する）。
    - 省略可能パラメータは「キーごと送らない」こと（nullを送らない）。
    - すべての引数は文字列で渡す（"true"/"false"、"5000" など）。

    【スキーマレビュー手順（必須）】
    1) list_schema_related_doc_paths を必ず実行し、paths_json を得る。
       - 入力は target_schema（必須）と max_tables（任意）のみ。
    2) get_docs_by_paths に paths_json を渡して、本文を取得して読む。
    3) 指摘のため columns が必要なテーブルだけ、list_table_related_doc_paths を実行する。
       - target_schema / target_table / include_columns は必須（include_columns は "true" または "false"）。
       - 返った paths_json を get_docs_by_paths に渡して columns を列挙回収する。
    4) Evidence は各指摘につきちょうど2件。
       - PATH は Vault 上に実在する .md ファイルパスのみ（必ず .md で終わる）。
       - PATH不明の指摘は成立させない。
       - Evidence が2件揃わない指摘は High にしない。
    5) High は最大3件、Findings 合計10件以内。

    【レビュー観点】
    - 命名・概念の一貫性 / domain・型の統一
    - nullable / default の妥当性
    - PK / FK 設計（不変性・一意性）
    - 状態管理・時刻整合性 / 履歴・監査・運用拡張性

  response: |
    日本語で回答してください。
    出力は reviews/ に保存可能なMarkdownとし、最終回答は必ず単一のチルダフェンスで囲ってください。
    - 先頭行は「~~~md」
    - 末尾行は「~~~」
    - ブロック外の文字は禁止
    - 重要：出力本文中にバッククォート3連のコードフェンス文字列を含めない（混入するなら該当部分を省略してよい）

    形式は以下に厳密に従うこと：

    ~~~md
    ---
    type: agent_review
    review_date: <YYYY-MM-DD>
    target: <SCHEMA>
    ---

    # <SCHEMA> 設計レビュー

    ## 0. メタ情報
    - 対象: <SCHEMA>
    - レビュー日: <YYYY-MM-DD>
    - 対象ノート候補（PATH一覧）:
      - <PATH>
      - ...

    ## 1. サマリ（3行）
    - ...
    - ...
    - ...

    ## 2. Findings（重要度別）
    ### High
    #### High-1: <タイトル>
    - 指摘:
    - 影響:
    - 提案:
    - Evidence:
      - PATH: ...
        抜粋: "..."
      - PATH: ...
        抜粋: "..."
    - Vault差分案（AIは編集しない）:
      - 変更対象PATH: ...
        変更内容: ...

    ### Med
    #### Med-1: <タイトル>
    - 指摘:
    - 影響:
    - 提案:
    - Evidence:
      - PATH: ...
        抜粋: "..."
      - PATH: ...
        抜粋: "..."
    - Vault差分案（AIは編集しない）:
      - 変更対象PATH: ...
        変更内容: ...

    ### Low
    #### Low-1: <タイトル>
    - 指摘:
    - 影響:
    - 提案:
    - Evidence:
      - PATH: ...
        抜粋: "..."
      - PATH: ...
        抜粋: "..."
    - Vault差分案（AIは編集しない）:
      - 変更対象PATH: ...
        変更内容: ...

    ## 3. 【仮説】の検証（該当がある場合のみ）
    - 仮説:
    - 確認に必要な情報:
    - Analystでの検証質問（自然言語で）:

    ## 4. 追加で集めたい情報（不足がある場合のみ）
    - 追加調査:
    - 追加ツール実行案:

    ## 5. 改善提案（次アクション）
    - 実施内容:
      期待効果:
      優先度: High / Med / Low
      変更対象PATH（案）:
    ~~~

tools:
  - tool_spec:
      type: "generic"
      name: "list_schema_related_doc_paths"
      description: "スキーマ単位の関連md PATH群を列挙して返す（NULLが発生しない入口）。"
      input_schema:
        type: "object"
        properties:
          target_schema:
            type: "string"
          max_tables:
            type: "string"
            description: "省略可（例: \"2000\"）"
        required: ["target_schema", "max_tables"]

  - tool_spec:
      type: "generic"
      name: "list_table_related_doc_paths"
      description: "テーブル単位の関連md PATH群を列挙（必要なら columns も含める）。"
      input_schema:
        type: "object"
        properties:
          target_schema:
            type: "string"
          target_table:
            type: "string"
          include_columns:
            type: "string"
            description: "\"true\"/\"false\"（必須）"
          max_columns:
            type: "string"
            description: "省略可（例: \"5000\"）"
        required: ["target_schema","target_table","include_columns"]

  - tool_spec:
      type: "generic"
      name: "get_docs_by_paths"
      description: "paths_json（JSON配列文字列）で指定したmdの本文等を返す。"
      input_schema:
        type: "object"
        properties:
          paths_json:
            type: "string"
          max_chars:
            type: "string"
            description: "省略可（例: \"8000\"）"
        required: ["paths_json"]

tool_resources:
  list_schema_related_doc_paths:
    type: "procedure"
    execution_environment:
      type: "warehouse"
      warehouse: "GBPS253YS_WH"
      query_timeout: 300
    identifier: "GBPS253YS_DB.DB_DESIGN.LIST_SCHEMA_RELATED_DOC_PATHS_AGENT"

  list_table_related_doc_paths:
    type: "procedure"
    execution_environment:
      type: "warehouse"
      warehouse: "GBPS253YS_WH"
      query_timeout: 300
    identifier: "GBPS253YS_DB.DB_DESIGN.LIST_TABLE_RELATED_DOC_PATHS_AGENT"

  get_docs_by_paths:
    type: "procedure"
    execution_environment:
      type: "warehouse"
      warehouse: "GBPS253YS_WH"
      query_timeout: 300
    identifier: "GBPS253YS_DB.DB_DESIGN.GET_DOCS_BY_PATHS_AGENT"
$$;

-- PROCEDURE: DB_DESIGN.OBSIDIAN_VAULT_STAGE
CREATE OR REPLACE STAGE DB_DESIGN.OBSIDIAN_VAULT_STAGE
  URL = 's3://135365622922-snowflake-dbdesign/'
  STORAGE_INTEGRATION = S3_OBSIDIAN_INT;

-- PROCEDURE: DB_DESIGN.PROFILE_ALL_TABLES
CREATE OR REPLACE PROCEDURE DB_DESIGN.PROFILE_ALL_TABLES(
    P_TARGET_DB     STRING,
    P_TARGET_SCHEMA STRING,
    P_SAMPLE_PCT    FLOAT DEFAULT NULL,
    P_NOTE          STRING DEFAULT NULL
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  V_RESULTS   ARRAY;
  V_TBL_RS    RESULTSET;
  V_TBL_NAME  STRING;
  V_RUN_ID    STRING;

  V_SQL_LIST  STRING;
  V_SQL_CALL  STRING;

  V_QDB       STRING;
  V_QSC       STRING;
BEGIN
  V_RESULTS := ARRAY_CONSTRUCT();

  /* DB / SCHEMA を安全にクォート */
  V_QDB := '"' || REPLACE(P_TARGET_DB,'"','""') || '"';
  V_QSC := '''' || REPLACE(P_TARGET_SCHEMA,'''','''''') || '''';

  /* BASE TABLE 一覧を動的SQLで取得 */
  V_SQL_LIST := '
SELECT TABLE_NAME
FROM ' || V_QDB || '.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = ' || V_QSC || '
  AND TABLE_TYPE = ''BASE TABLE''
ORDER BY TABLE_NAME
';

  V_TBL_RS := (EXECUTE IMMEDIATE :V_SQL_LIST);

  /* テーブルごとに PROFILE_TABLE を CALL */
  FOR REC IN V_TBL_RS DO
    V_TBL_NAME := REC.TABLE_NAME;

    BEGIN
      V_SQL_CALL := '
CALL GBPS253YS_DB.DB_DESIGN.PROFILE_TABLE(
  ''' || REPLACE(P_TARGET_DB,'''','''''') || ''',
  ''' || REPLACE(P_TARGET_SCHEMA,'''','''''') || ''',
  ''' || REPLACE(V_TBL_NAME,'''','''''') || ''',
  ' || NVL(TO_VARCHAR(P_SAMPLE_PCT), 'NULL') || ',
  NULL,
  NULL,
  ''' || REPLACE(COALESCE(P_NOTE,'manual weekly all-tables run'),'''','''''') || '''
)
';

      EXECUTE IMMEDIATE :V_SQL_CALL;

      /* ★列名依存をやめて、1列目($1)でRUN_IDを取得 */
      SELECT $1::STRING
        INTO :V_RUN_ID
        FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

      V_RESULTS := ARRAY_APPEND(
        V_RESULTS,
        OBJECT_CONSTRUCT(
          'table', V_TBL_NAME,
          'run_id', V_RUN_ID,
          'status', 'SUCCEEDED'
        )
      );

    EXCEPTION
      WHEN OTHER THEN
        V_RESULTS := ARRAY_APPEND(
          V_RESULTS,
          OBJECT_CONSTRUCT(
            'table', V_TBL_NAME,
            'status', 'FAILED',
            'error', SQLERRM
          )
        );
    END;
  END FOR;

  RETURN OBJECT_CONSTRUCT(
    'target_db', P_TARGET_DB,
    'target_schema', P_TARGET_SCHEMA,
    'tables_processed', ARRAY_SIZE(V_RESULTS),
    'results', V_RESULTS
  );
END;
$$;

-- PROCEDURE: DB_DESIGN.PROFILE_COLUMN
CREATE OR REPLACE PROCEDURE DB_DESIGN.PROFILE_COLUMN(
    P_TARGET_DB     STRING,
    P_TARGET_SCHEMA STRING,
    P_TARGET_TABLE  STRING,
    P_TARGET_COLUMN STRING,
    P_SAMPLE_PCT    FLOAT DEFAULT NULL
)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  V_QDB   STRING;
  V_QSC   STRING;
  V_QTB   STRING;
  V_FULL  STRING;
  V_QCOL  STRING;

  V_SQL     STRING;
  V_METRICS VARIANT;
BEGIN
  /* フル修飾テーブル */
  V_QDB  := '"' || REPLACE(P_TARGET_DB, '"', '""') || '"';
  V_QSC  := '"' || REPLACE(P_TARGET_SCHEMA, '"', '""') || '"';
  V_QTB  := '"' || REPLACE(P_TARGET_TABLE, '"', '""') || '"';
  V_FULL := V_QDB || '.' || V_QSC || '.' || V_QTB;

  V_QCOL := '"' || REPLACE(P_TARGET_COLUMN, '"', '""') || '"';

  /* 動的SQL生成 */
  V_SQL := '
WITH SRC AS (
  SELECT * FROM ' || V_FULL ||
  CASE
    WHEN P_SAMPLE_PCT IS NULL THEN ''
    ELSE ' TABLESAMPLE BERNOULLI(' || P_SAMPLE_PCT || ')'
  END || '
),
AGG AS (
  SELECT
    COUNT(*) AS row_count,
    SUM(IFF(' || V_QCOL || ' IS NULL, 1, 0)) AS null_count,
    COUNT(DISTINCT ' || V_QCOL || ') AS distinct_count,
    MIN(TO_VARCHAR(' || V_QCOL || ')) AS min_varchar,
    MAX(TO_VARCHAR(' || V_QCOL || ')) AS max_varchar,
    MIN(LENGTH(TO_VARCHAR(' || V_QCOL || '))) AS min_len,
    MAX(LENGTH(TO_VARCHAR(' || V_QCOL || '))) AS max_len
  FROM SRC
),
TOP_VALUES AS (
  SELECT
    TO_VARCHAR(' || V_QCOL || ') AS v,
    COUNT(*) AS c
  FROM SRC
  WHERE ' || V_QCOL || ' IS NOT NULL
  GROUP BY 1
  ORDER BY c DESC
  LIMIT 20
)
SELECT OBJECT_CONSTRUCT(
  ''row_count'', row_count,
  ''null_count'', null_count,
  ''null_rate'', IFF(row_count=0, NULL, null_count::FLOAT/row_count),
  ''distinct_count'', distinct_count,
  ''distinct_rate_non_null'', IFF((row_count-null_count)=0, NULL, distinct_count::FLOAT/(row_count-null_count)),
  ''min_varchar'', min_varchar,
  ''max_varchar'', max_varchar,
  ''min_len'', min_len,
  ''max_len'', max_len,
  ''top_values'', (SELECT ARRAY_AGG(OBJECT_CONSTRUCT(''value'', v, ''count'', c)) FROM TOP_VALUES)
) AS METRICS
FROM AGG
';

  /* 実行 */
  EXECUTE IMMEDIATE :V_SQL;

  /* 結果をVARIANTで取得 */
  SELECT METRICS
    INTO :V_METRICS
    FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

  RETURN V_METRICS;
END;
$$;

-- PROCEDURE: DB_DESIGN.PROFILE_TABLE
CREATE OR REPLACE PROCEDURE DB_DESIGN.PROFILE_TABLE(
    P_TARGET_DB     STRING,
    P_TARGET_SCHEMA STRING,
    P_TARGET_TABLE  STRING,
    P_SAMPLE_PCT    FLOAT DEFAULT NULL,
    P_RUN_ID        STRING DEFAULT NULL,
    P_GIT_COMMIT    STRING DEFAULT NULL,
    P_NOTE          STRING DEFAULT NULL
)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
  V_RUN_ID    STRING;
  V_STARTED   TIMESTAMP_LTZ;

  V_QDB   STRING;
  V_QSC   STRING;
  V_QTB   STRING;
  V_FULL  STRING;

  V_COL_RS   RESULTSET;
  V_COL_NAME STRING;

  V_QCOL    STRING;
  V_SQL     STRING;
  V_METRICS VARIANT;
  V_SQLC    STRING;
BEGIN
  /* ========== RUN 初期化 ========== */
  V_STARTED := CURRENT_TIMESTAMP();
  V_RUN_ID  := COALESCE(P_RUN_ID, 'RUN-' || UUID_STRING());

  /* ========== RUN 登録（冪等） ========== */
  MERGE INTO DB_DESIGN.PROFILE_RUNS T
  USING (
    SELECT
      :V_RUN_ID        AS RUN_ID,
      :P_TARGET_DB     AS TARGET_DB,
      :P_TARGET_SCHEMA AS TARGET_SCHEMA,
      :P_TARGET_TABLE  AS TARGET_TABLE,
      :P_SAMPLE_PCT    AS SAMPLE_PCT,
      :V_STARTED       AS STARTED_AT,
      'RUNNING'        AS STATUS,
      CURRENT_WAREHOUSE() AS WAREHOUSE_NAME,
      CURRENT_ROLE()      AS ROLE_NAME,
      :P_GIT_COMMIT    AS GIT_COMMIT,
      :P_NOTE          AS NOTE
  ) S
  ON T.RUN_ID = S.RUN_ID
  WHEN MATCHED THEN
    UPDATE SET
      STARTED_AT     = S.STARTED_AT,
      FINISHED_AT    = NULL,
      STATUS         = 'RUNNING',
      SAMPLE_PCT     = S.SAMPLE_PCT,
      WAREHOUSE_NAME = S.WAREHOUSE_NAME,
      ROLE_NAME      = S.ROLE_NAME,
      GIT_COMMIT     = S.GIT_COMMIT,
      NOTE           = S.NOTE
  WHEN NOT MATCHED THEN
    INSERT (
      RUN_ID, TARGET_DB, TARGET_SCHEMA, TARGET_TABLE,
      SAMPLE_PCT, STARTED_AT, STATUS,
      WAREHOUSE_NAME, ROLE_NAME, GIT_COMMIT, NOTE
    )
    VALUES (
      S.RUN_ID, S.TARGET_DB, S.TARGET_SCHEMA, S.TARGET_TABLE,
      S.SAMPLE_PCT, S.STARTED_AT, S.STATUS,
      S.WAREHOUSE_NAME, S.ROLE_NAME, S.GIT_COMMIT, S.NOTE
    );

  /* ========== 再実行対策：既存結果削除 ========== */
  DELETE FROM DB_DESIGN.PROFILE_RESULTS
   WHERE RUN_ID = :V_RUN_ID;

  /* ========== 対象テーブル（フル修飾） ========== */
  V_QDB  := '"' || REPLACE(P_TARGET_DB, '"', '""') || '"';
  V_QSC  := '"' || REPLACE(P_TARGET_SCHEMA, '"', '""') || '"';
  V_QTB  := '"' || REPLACE(P_TARGET_TABLE, '"', '""') || '"';
  V_FULL := V_QDB || '.' || V_QSC || '.' || V_QTB;

  /* ========== 列一覧取得 ========== */
  V_SQLC := '
    SELECT COLUMN_NAME
    FROM ' || V_QDB || '.INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ?
      AND TABLE_NAME   = ?
    ORDER BY ORDINAL_POSITION
  ';
  V_COL_RS := (EXECUTE IMMEDIATE :V_SQLC USING (P_TARGET_SCHEMA, P_TARGET_TABLE));

  /* ========== 列ごとのメトリクス算出 ========== */
  FOR REC IN V_COL_RS DO
    V_COL_NAME := REC.COLUMN_NAME;
    V_QCOL := '"' || REPLACE(V_COL_NAME, '"', '""') || '"';

    V_SQL := '
WITH SRC AS (
  SELECT * FROM ' || V_FULL ||
  CASE
    WHEN P_SAMPLE_PCT IS NULL THEN ''
    ELSE ' TABLESAMPLE BERNOULLI(' || P_SAMPLE_PCT || ')'
  END || '
),
AGG AS (
  SELECT
    COUNT(*) AS row_count,
    SUM(IFF(' || V_QCOL || ' IS NULL, 1, 0)) AS null_count,
    COUNT(DISTINCT ' || V_QCOL || ') AS distinct_count,
    MIN(TO_VARCHAR(' || V_QCOL || ')) AS min_varchar,
    MAX(TO_VARCHAR(' || V_QCOL || ')) AS max_varchar,
    MIN(LENGTH(TO_VARCHAR(' || V_QCOL || '))) AS min_len,
    MAX(LENGTH(TO_VARCHAR(' || V_QCOL || '))) AS max_len
  FROM SRC
),
TOP_VALUES AS (
  SELECT
    TO_VARCHAR(' || V_QCOL || ') AS v,
    COUNT(*) AS c
  FROM SRC
  WHERE ' || V_QCOL || ' IS NOT NULL
  GROUP BY 1
  ORDER BY c DESC
  LIMIT 20
)
SELECT OBJECT_CONSTRUCT(
  ''row_count'', row_count,
  ''null_count'', null_count,
  ''null_rate'', IFF(row_count=0, NULL, null_count::FLOAT/row_count),
  ''distinct_count'', distinct_count,
  ''distinct_rate_non_null'', IFF((row_count-null_count)=0, NULL, distinct_count::FLOAT/(row_count-null_count)),
  ''min_varchar'', min_varchar,
  ''max_varchar'', max_varchar,
  ''min_len'', min_len,
  ''max_len'', max_len,
  ''top_values'', (SELECT ARRAY_AGG(OBJECT_CONSTRUCT(''value'', v, ''count'', c)) FROM TOP_VALUES)
) AS METRICS
FROM AGG
';

    EXECUTE IMMEDIATE :V_SQL;

    SELECT METRICS
      INTO :V_METRICS
      FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

    INSERT INTO DB_DESIGN.PROFILE_RESULTS
      (RUN_ID, TARGET_DB, TARGET_SCHEMA, TARGET_TABLE,
       TARGET_COLUMN, AS_OF_AT, METRICS)
    SELECT
      :V_RUN_ID, :P_TARGET_DB, :P_TARGET_SCHEMA, :P_TARGET_TABLE,
      :V_COL_NAME, CURRENT_TIMESTAMP(), :V_METRICS;
  END FOR;

  /* ========== RUN 正常終了 ========== */
  UPDATE DB_DESIGN.PROFILE_RUNS
     SET FINISHED_AT = CURRENT_TIMESTAMP(),
         STATUS      = 'SUCCEEDED'
   WHERE RUN_ID = :V_RUN_ID;

  RETURN V_RUN_ID;

EXCEPTION
  WHEN OTHER THEN
    UPDATE DB_DESIGN.PROFILE_RUNS
       SET FINISHED_AT = CURRENT_TIMESTAMP(),
           STATUS      = 'FAILED',
           NOTE =
             COALESCE(:P_NOTE, '') ||
             IFF(:P_NOTE IS NULL, '', ' | ') ||
             'ERROR(' || :SQLCODE || '): ' || :SQLERRM
     WHERE RUN_ID = :V_RUN_ID;
    RAISE;
END;
$$;

-- PROCEDURE: APP_PRODUCTION.EXPAND_DEPARTMENT_SCOPE_TOOL
create or replace procedure APP_PRODUCTION.EXPAND_DEPARTMENT_SCOPE_TOOL(
  payload_json string
)
returns variant
language javascript
execute as owner
as
$$
function q1(sqlText, binds) {
  return snowflake.createStatement({ sqlText: sqlText, binds: binds || [] }).execute();
}
function toInt(v, defVal, minVal, maxVal) {
  const n = parseInt(v, 10);
  const x = Number.isFinite(n) ? n : defVal;
  return Math.max(minVal, Math.min(maxVal, x));
}
function upper(v) { return (v===null||v===undefined) ? "" : String(v).toUpperCase(); }

try {
  // --- parse payload_json ---
  const arg = arguments[0];
  const jsonText = (arg === null || arg === undefined || String(arg).length === 0) ? "{}" : String(arg);

  const prs = q1("select parse_json(?)", [jsonText]);
  prs.next();
  const p = prs.getColumnValue(1) || {};

  let fy = (p.fiscal_year === null || p.fiscal_year === undefined) ? "" : String(p.fiscal_year);
  let deptId = (p.department_id === null || p.department_id === undefined) ? "" : String(p.department_id); // ここは部署IDのつもり
  const includeSelf = (upper(p.include_self) === "Y") ? "Y" : "N";
  const maxNodes = toInt(p.max_nodes, 500, 1, 5000);

  if (!fy) {
    const rsFy = q1("select max(FISCAL_YEAR) from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER", []);
    fy = rsFy.next() ? String(rsFy.getColumnValue(1)) : "";
    if (!fy) return { ok:false, next:"error", message:"cannot determine fiscal_year", payload:p };
  }
  if (!deptId) return { ok:false, next:"error", message:"department_id is required (logical dept id)", payload:p };

  // --- 1) まず department_id として探す ---
  let rsRoot = q1(`
    select
      DEPARTMENT_ID,
      DEPARTMENT_CATEGORY,
      DEPARTMENT_CODE,
      HEADQUARTERS_CODE,
      GENERAL_DEPARTMENT_CODE,
      COMBINED_NAME,
      COMBINED_SHORT_NAME
    from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
    where FISCAL_YEAR = ?
      and DEPARTMENT_ID = ?
    limit 1
  `, [fy, deptId]);

  // --- 2) 見つからなければ「deptIdは id だった」可能性があるので救済 ---
  if (!rsRoot.next()) {
    const rsMap = q1(`
      select DEPARTMENT_ID
      from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
      where FISCAL_YEAR = ?
        and ID = ?
      limit 1
    `, [fy, deptId]);

    if (rsMap.next()) {
      deptId = String(rsMap.getColumnValue(1));
      rsRoot = q1(`
        select
          DEPARTMENT_ID,
          DEPARTMENT_CATEGORY,
          DEPARTMENT_CODE,
          HEADQUARTERS_CODE,
          GENERAL_DEPARTMENT_CODE,
          COMBINED_NAME,
          COMBINED_SHORT_NAME
        from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
        where FISCAL_YEAR = ?
          and DEPARTMENT_ID = ?
        limit 1
      `, [fy, deptId]);

      if (!rsRoot.next()) {
        return { ok:false, next:"error", message:"mapped from ID but root row still not found", fiscal_year:fy, input_id:p.department_id, mapped_department_id:deptId };
      }
    } else {
      return { ok:false, next:"error", message:"department_id not found (and also not found as ID)", fiscal_year:fy, input_value:p.department_id };
    }
  }

  // rsRoot is currently on a valid row
  const root_department_id = String(rsRoot.getColumnValue(1));
  const category = String(rsRoot.getColumnValue(2));
  const deptCode = rsRoot.getColumnValue(3) === null ? null : String(rsRoot.getColumnValue(3));
  const hqCode   = rsRoot.getColumnValue(4) === null ? null : String(rsRoot.getColumnValue(4));
  const genCode  = rsRoot.getColumnValue(5) === null ? null : String(rsRoot.getColumnValue(5));
  const nameFull = rsRoot.getColumnValue(6);
  const nameShort= rsRoot.getColumnValue(7);

  // --- decide scope key + allowed categories ---
  let whereKey = "";
  let bindsKey = [];
  let allowCats = null;

  if (category === "グループ") {
    whereKey = "FISCAL_YEAR = ? and DEPARTMENT_ID = ?";
    bindsKey = [fy, root_department_id];
  } else if (category === "課") {
    if (!deptCode) return { ok:false, next:"error", message:"department_code is null for 課", fiscal_year:fy, department_id:root_department_id };
    whereKey = "FISCAL_YEAR = ? and DEPARTMENT_CODE = ?";
    bindsKey = [fy, deptCode];
    allowCats = (includeSelf === "Y") ? ["課","グループ"] : ["グループ"];
  } else if (category === "部") {
    if (!deptCode) return { ok:false, next:"error", message:"department_code is null for 部", fiscal_year:fy, department_id:root_department_id };
    whereKey = "FISCAL_YEAR = ? and DEPARTMENT_CODE = ?";
    bindsKey = [fy, deptCode];
    allowCats = (includeSelf === "Y") ? ["部","課","グループ"] : ["課","グループ"];
  } else if (category === "本部") {
    if (!hqCode) return { ok:false, next:"error", message:"headquarters_code is null for 本部", fiscal_year:fy, department_id:root_department_id };
    whereKey = "FISCAL_YEAR = ? and HEADQUARTERS_CODE = ?";
    bindsKey = [fy, hqCode];
    allowCats = (includeSelf === "Y") ? ["本部","部","課","グループ"] : ["部","課","グループ"];
  } else {
    return { ok:false, next:"error", message:"unsupported department_category", department_category:category, fiscal_year:fy, department_id:root_department_id };
  }

  let extra = "";
  if (allowCats && allowCats.length > 0) {
    const quoted = allowCats.map(x => "'" + x.replace(/'/g,"''") + "'").join(",");
    extra = ` and DEPARTMENT_CATEGORY in (${quoted}) `;
  }

  const rs = q1(`
    select
      DEPARTMENT_ID,
      DEPARTMENT_CATEGORY,
      DEPARTMENT_CODE,
      SECTION_CODE,
      GROUP_CODE,
      COMBINED_NAME,
      COMBINED_SHORT_NAME
    from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
    where ${whereKey}
      ${extra}
    order by
      case DEPARTMENT_CATEGORY when '本部' then 1 when '部' then 2 when '課' then 3 when 'グループ' then 4 else 9 end,
      DEPARTMENT_ID
    limit ${maxNodes}
  `, bindsKey);

  const ids = [];
  const members = [];
  while (rs.next()) {
    const did = String(rs.getColumnValue(1));
    ids.push(did);
    members.push({
      department_id: did,
      department_category: String(rs.getColumnValue(2)),
      department_code: rs.getColumnValue(3) === null ? null : String(rs.getColumnValue(3)),
      section_code: rs.getColumnValue(4) === null ? null : String(rs.getColumnValue(4)),
      group_code: rs.getColumnValue(5) === null ? null : String(rs.getColumnValue(5)),
      name_full: rs.getColumnValue(6),
      name_short: rs.getColumnValue(7)
    });
  }

  return {
    ok: true,
    next: "aggregate",
    fiscal_year: fy,
    resolved: {
      department_id: root_department_id,
      department_category: category,
      department_code: deptCode,
      headquarters_code: hqCode,
      general_department_code: genCode,
      name_full: nameFull,
      name_short: nameShort
    },
    scope: {
      include_self: includeSelf,
      department_ids: ids,
      count: ids.length,
      members: members
    }
  };

} catch (err) {
  return { ok:false, next:"error", message:String(err), stack: err && err.stack ? String(err.stack) : null };
}
$$;

-- FUNCTION: APP_PRODUCTION.NORMALIZE_JA
create or replace function APP_PRODUCTION.NORMALIZE_JA(s string)
returns string
language javascript
as
$$
  // Snowflake JavaScript UDF は arguments[0] を使う
  var s0 = arguments[0];
  if (s0 === null) return null;
  let t = String(s0);
  t = t.normalize("NFKC");
  t = t.trim();
  t = t.toLowerCase();
  t = t.replace(
    /(株式会社|有限会社|合同会社|（株）|\(株\)|㈱|（有）|\(有\)|㈲|（同）|\(同\)|inc\.?|llc|ltd\.?|co\.?|company|limited)/gi,
    ""
  );
  t = t.replace(/[\s\u3000]+/g, "");
  t = t.replace(
    /[()\[\]{}<>「」『』【】（）・,，．.／\/\\\-＿_―ー…:：;；!！?？'"“”‘’&＋+*＝=]/g,
    ""
  );
  t = t.replace(/[\u3041-\u3096]/g, function (ch) {
    return String.fromCharCode(ch.charCodeAt(0) + 0x60);
  });
  t = t.replace(/第(\d+)期/g, "$1期");
  t = t.replace(/ー{2,}/g, "ー");
  t = t.trim();
  return t;
$$;

-- FUNCTION: APP_PRODUCTION.NORMALIZE_JA_DEPT
create or replace function APP_PRODUCTION.NORMALIZE_JA_DEPT(s string)
returns string
language javascript
as
$$
  var s0 = arguments[0];
  if (s0 === null) return null;
  let t = String(s0);
  t = t.normalize("NFKC");
  t = t.trim().toLowerCase();
  t = t.replace(/(株式会社|有限会社|合同会社|（株）|\(株\)|㈱|（有）|\(有\)|㈲|（同）|\(同\))/g, "");
  t = t.replace(/[\s\u3000]+/g, "");
  t = t.replace(/[()\[\]{}<>「」『』【】（）・,，．.／\/\\\-＿_―ー…:：;；!！?？'"“”‘’&＋+*＝=]/g, "");
  t = t.replace(/[\u3041-\u3096]/g, function (ch) {
    return String.fromCharCode(ch.charCodeAt(0) + 0x60);
  });
  t = t.replace(/(?<!本)(部|課|室|グループ|G|ユニット|チーム)$/g, "");
  return t;
$$;

-- STAGE: APP_PRODUCTION.RAW_DATA
CREATE OR REPLACE STAGE APP_PRODUCTION.RAW_DATA
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
  DIRECTORY = (ENABLE = TRUE);

-- PROCEDURE: APP_PRODUCTION.RESOLVE_ENTITY_ALIAS
create or replace procedure APP_PRODUCTION.RESOLVE_ENTITY_ALIAS(
    term string,
    max_candidates string,                 -- ★ NUMBER(38,0) 回避のため string で受ける
    entity_type_hint string default null   -- 'department' / 'customer' / 'project' / 'order' / null
)
returns variant
language javascript
execute as owner
as
$$
/* =========================
 * Utility
 * ========================= */
function q1(sqlText, binds) {
  const st = snowflake.createStatement({
    sqlText: sqlText,
    binds: binds || []
  });
  return st.execute();
}

function firstValue(rs) {
  if (rs.next()) return rs.getColumnValue(1);
  return null;
}

// JS SPでは列名でのgetColumnValueが効かないことがあるため、列番号で取得する
function rowsToArray(rs) {
  const out = [];
  while (rs.next()) {
    out.push({
      alias_raw:        rs.getColumnValue(1),
      alias_normalized: rs.getColumnValue(2),
      entity_type:      rs.getColumnValue(3),
      entity_id:        rs.getColumnValue(4),
      entity_name:      rs.getColumnValue(5),
      confidence:       Number(rs.getColumnValue(6)),
      priority:         Number(rs.getColumnValue(7))
    });
  }
  return out;
}

function toInt(v, defVal, minVal, maxVal) {
  const n = parseInt(v, 10);
  const x = Number.isFinite(n) ? n : defVal;
  return Math.max(minVal, Math.min(maxVal, x));
}

try {
  /* =========================
   * Params (Snowflake JS SP: use arguments[])
   * ========================= */
  const termArg           = arguments[0];
  const maxCandidatesArg  = arguments[1];
  const entityTypeHintArg = arguments[2];

  const t = (termArg === null || termArg === undefined) ? "" : String(termArg);

  const max = toInt(maxCandidatesArg, 8, 1, 50);
  const limitClause = " limit " + max;

  const hasHint =
    entityTypeHintArg !== null &&
    entityTypeHintArg !== undefined &&
    String(entityTypeHintArg).length > 0;

  const typeClause = hasHint ? " and entity_type = ? " : "";

  /* =========================
   * Normalize
   * ※UDFは完全修飾推奨。必要に応じてスキーマ名を修正してください。
   * ========================= */
  const normJa = firstValue(
    q1("select GBPS253YS_DB.APP_PRODUCTION.NORMALIZE_JA(?)", [t])
  );

  const normDept = firstValue(
    q1("select GBPS253YS_DB.APP_PRODUCTION.NORMALIZE_JA_DEPT(?)", [t])
  );

  /* =========================
   * Candidate Resolver
   * ========================= */
  function fetchCandidates(sqlBase, binds) {
    const rs = q1(sqlBase, binds);
    const candidates = rowsToArray(rs);

    // 1件のみ → 確定
    if (candidates.length === 1) {
      return { decided: true, resolved: candidates[0], candidates: candidates };
    }

    // 上位が十分強い場合 → 自動確定（任意チューニング）
    if (candidates.length >= 2) {
      const top = candidates[0];
      const second = candidates[1];
      if (
        top.confidence >= 0.95 &&
        (top.confidence - second.confidence) >= 0.10
      ) {
        return { decided: true, resolved: top, candidates: candidates };
      }
    }

    return { decided: false, resolved: null, candidates: candidates };
  }

  /* =========================
   * Step ① raw 完全一致（alias_raw）
   * ========================= */
  {
    const sql = `
      select
        alias_raw,
        alias_normalized,
        entity_type,
        entity_id,
        entity_name,
        confidence,
        priority
      from DIM_ENTITY_ALIAS
      where is_active = true
        and alias_raw = ?
        ${typeClause}
      order by
        priority asc,
        confidence desc,
        length(alias_normalized) asc
      ${limitClause}
    `;

    const binds = hasHint ? [t, entityTypeHintArg] : [t];
    const r = fetchCandidates(sql, binds);

    if (r.decided) {
      return {
        ok: true,
        step: 1,
        next: "aggregate",
        term: t,
        normalized: normJa,
        resolved: r.resolved
      };
    }
  }

  /* =========================
   * Step ② 正規化 完全一致（alias_normalized）
   * departmentは normJa / normDept の両方で試す
   * ========================= */
  {
    const sql = `
      select
        alias_raw,
        alias_normalized,
        entity_type,
        entity_id,
        entity_name,
        confidence,
        priority
      from DIM_ENTITY_ALIAS
      where is_active = true
        and (
              alias_normalized = ?
           or (entity_type = 'department' and alias_normalized = ?)
        )
        ${typeClause}
      order by
        priority asc,
        confidence desc,
        length(alias_normalized) asc
      ${limitClause}
    `;

    const binds = hasHint
      ? [normJa, normDept, entityTypeHintArg]
      : [normJa, normDept];

    const r = fetchCandidates(sql, binds);

    if (r.decided) {
      return {
        ok: true,
        step: 2,
        next: "aggregate",
        term: t,
        normalized: normJa,
        resolved: r.resolved
      };
    }
  }

  /* =========================
   * Step ③ 正規化 部分一致（候補提示）
   * ========================= */
  {
    const sql = `
      select
        alias_raw,
        alias_normalized,
        entity_type,
        entity_id,
        entity_name,
        confidence,
        priority
      from DIM_ENTITY_ALIAS
      where is_active = true
        and (
             alias_normalized like '%' || ? || '%'
          or (entity_type = 'department' and alias_normalized like '%' || ? || '%')
        )
        ${typeClause}
      order by
        priority asc,
        confidence desc,
        length(alias_normalized) asc
      ${limitClause}
    `;

    const binds = hasHint
      ? [normJa, normDept, entityTypeHintArg]
      : [normJa, normDept];

    const r = fetchCandidates(sql, binds);

    return {
      ok: true,
      step: 3,
      next: "disambiguate",
      term: t,
      normalized: normJa,
      candidates: r.candidates
    };
  }

} catch (err) {
  // Agent経由でも原因が追えるように返す
  return {
    ok: false,
    next: "error",
    message: String(err),
    stack: err && err.stack ? String(err.stack) : null
  };
}
$$;

-- PROCEDURE: APP_PRODUCTION.RESOLVE_ENTITY_ALIAS_TOOL
create or replace procedure GBPS253YS_DB.APP_PRODUCTION.RESOLVE_ENTITY_ALIAS_TOOL(payload_json string)
returns variant
language javascript
execute as owner
as
$$
try {
  const s = (payload_json === null || payload_json === undefined) ? "{}" : String(payload_json);
  const rs = snowflake.createStatement({ sqlText: "select parse_json(?)", binds: [s] }).execute();
  rs.next();
  const p = rs.getColumnValue(1) || {};

  const term = (p.term ?? "").toString();
  const maxCandidates = (p.max_candidates ?? "8").toString();
  const hint = (p.entity_type_hint === undefined || p.entity_type_hint === null || String(p.entity_type_hint).length === 0)
    ? null
    : String(p.entity_type_hint);

  const st = snowflake.createStatement({
    sqlText: `call GBPS253YS_DB.APP_PRODUCTION.RESOLVE_ENTITY_ALIAS(?, ?, ?)`,
    binds: [term, maxCandidates, hint]
  });
  const r2 = st.execute();
  r2.next();
  return r2.getColumnValue(1);

} catch (err) {
  return { ok:false, next:"error", message:String(err), stack: err && err.stack ? String(err.stack) : null };
}
$$;

-- AGENT: APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT
CREATE OR REPLACE AGENT APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT
  COMMENT = 'snowflakeデモ用のエージェントです。名称解決→部署スコープ展開→集計まで決定論で実行します。'
  PROFILE = '{"display_name":"SNOWFLAKE_DEMO_AGENT"}'
  FROM SPECIFICATION
$$
models:
  orchestration: auto

instructions:
  orchestration: >
    あなたはデータ分析アシスタントです。
    部署・顧客・案件・オーダーの名称の特定を、LLMの推測や文字列探索（LIKE/ILIKE）で行ってはいけません。
    必ずツールで決定論的に解決してください。

    重要:
    - 部（部署区分=部）を指定された場合、売上は下位の課/グループに紐づくため、
      そのまま department_id で絞ると0件になることがあります。
      必ず expand_department_scope を呼び、配下の department_id 群（スコープ）を確定してから集計してください。

    手順:
    1) ユーザー質問から固有名詞候補（部署/顧客/案件/オーダーになりうる語）を抽出し、各語について resolve_entity_alias を呼びます。
       - resolve_entity_alias には payload_json（JSON文字列）を渡す
       - payload_json には term と max_candidates="8" を必ず入れる
       - entity_type_hint は原則省略（確信があるときのみ 'department'/'customer'/'project'/'order'）
       - 例: {"term":"デジタルイノベーション部","max_candidates":"8","entity_type_hint":"department"}

    2) resolve_entity_alias の結果 next が "disambiguate" の場合:
       - candidates を日本語で箇条書き表示し、ユーザーに選択を求める
       - この場合は text_to_sql に進まない

    3) resolve_entity_alias の結果 next が "aggregate" の場合:
       - resolved を採用して集計条件に使う
       - resolved.entity_type が "department" のときは、必ず expand_department_scope を呼び、
         配下の department_id 群（scope.department_ids）を確定する
         例: {"fiscal_year":"2025","department_id":"00092","include_self":"N","max_nodes":"500"}

       - fiscal_year はユーザー質問に年度指定があればそれを使う。指定がない場合は、最新年度（データに存在する最大の年度）を使う。

    4) expand_department_scope の戻り next が "disambiguate" の場合:
       - members / candidates を箇条書きで提示し、ユーザーに選択を求める
       - この場合は text_to_sql に進まない

    5) expand_department_scope の戻り next が "aggregate" の場合:
       - scope.department_ids を集計条件として必ず利用する
       - 文字列（部署名）でのフィルタは禁止
       - その上で text_to_sql を使って売上合計などの分析SQLを作る

    6) ツール実行で next が "error" の場合:
       - エラーメッセージを短く示し、どの情報が不足か（年度/正式名称など）をユーザーに確認する
       - 推測で補完しない

  response: >
    日本語で簡潔に答える。曖昧な場合は候補提示して選択を求める。名称はツール結果に従い、文字列探索で特定しない。

tools:
  # ① 名称解決（決定論）
  - tool_spec:
      type: "generic"
      name: "resolve_entity_alias"
      description: >
        名称辞書に基づき、部門/顧客/案件/オーダーの名称を決定論的に解決する。
        引数は payload_json（JSON文字列）1つ。
        例: {"term":"デジタルイノベーション部","max_candidates":"8","entity_type_hint":"department"}
      input_schema:
        type: "object"
        properties:
          payload_json:
            type: "string"
            description: "JSON文字列。termとmax_candidatesは必須。entity_type_hintは任意。"
        required: ["payload_json"]

  # ② 部署スコープ展開（部→課/グループのdepartment_id群）
  - tool_spec:
      type: "generic"
      name: "expand_department_scope"
      description: >
        部署IDから、同一年度・同一部CD配下の部署（課/グループ）のdepartment_id群を決定論的に取得する。
        引数は payload_json（JSON文字列）1つ。
        例: {"fiscal_year":"2025","department_id":"00092","include_self":"N","max_nodes":"500"}
      input_schema:
        type: "object"
        properties:
          payload_json:
            type: "string"
            description: "JSON文字列。fiscal_yearとdepartment_idは必須。include_selfは通常'N'。"
        required: ["payload_json"]

  # ③ Text-to-SQL（名称解決・スコープ確定後のみ）
  - tool_spec:
      type: "cortex_analyst_text_to_sql"
      name: "text_to_sql"
      description: "自然言語の質問をSQLに変換する"

tool_resources:
  resolve_entity_alias:
    type: "procedure"
    execution_environment:
      type: "warehouse"
      warehouse: "GBPS253YS_WH"
      query_timeout: 60
    identifier: "GBPS253YS_DB.APP_PRODUCTION.RESOLVE_ENTITY_ALIAS_TOOL"

  expand_department_scope:
    type: "procedure"
    execution_environment:
      type: "warehouse"
      warehouse: "GBPS253YS_WH"
      query_timeout: 60
    identifier: "GBPS253YS_DB.APP_PRODUCTION.EXPAND_DEPARTMENT_SCOPE_TOOL"

  text_to_sql:
    semantic_model_file: "@GBPS253YS_DB.APP_PRODUCTION.RAW_DATA/test.yaml"
    execution_environment:
      type: "warehouse"
      warehouse: "GBPS253YS_WH"
      query_timeout: 60
$$;
