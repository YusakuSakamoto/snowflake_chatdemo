# [[design.PROFILE_ALL_TABLES]]

## 概要

`[[DB_DESIGN.PROFILE_ALL_TABLES]]` は、指定されたデータベース・スキーマ内のすべてのテーブルに対して、プロファイル処理を一括実行するオーケストレーション用プロシージャです。

- スキーマ: [[design.DB_DESIGN]] (SCH_20251226180633)
- オブジェクトタイプ: PROCEDURE
- 言語: SQL
- 実行モード: EXECUTE AS OWNER
- 戻り値: VARIANT (処理結果のJSON)

---

## 業務上の意味

### 目的
大規模なスキーマに対して、全テーブルの品質プロファイルを効率的に収集するための自動化ツールです。手動で1テーブルずつプロファイルを実行するオペレーション負担を削減し、定期的なデータ品質レビューを実現します。

### 利用シーン
- 週次/月次の品質レビュー: 全テーブルのプロファイルを定期実行し、品質トレンドを追跡
- 新規スキーマのベースライン作成: 初回プロファイル実行で基準データを確立
- マイグレーション後の検証: 移行前後の品質比較のために全テーブルを一括プロファイル
- データ棚卸し: 使用状況やデータ品質の全体像把握

---

## 設計上の位置づけ

### データフロー
```
INFORMATION_SCHEMA.TABLES (BASE TABLE一覧取得)
  ↓
PROFILE_ALL_TABLES (オーケストレーション)
  ↓
PROFILE_TABLE (個別テーブルプロファイル) ← テーブル数だけループ実行
  ↓
PROFILE_RESULTS (各カラムのメトリクス蓄積)
PROFILE_RUNS (実行履歴記録)
  ↓
EXPORT_PROFILE_EVIDENCE_MD_VFINAL (Markdown形式でS3出力)
  ↓
S3 (snowflake-chatdemo-vault-prod/reviews/profiles/YYYY-MM-DD/)
  ↓
INGEST_VAULT_MD (Markdownを再取り込み)
  ↓
DOCS_OBSIDIAN (Cortex Agentが参照)
```

### 他コンポーネントとの連携
- 上流: INFORMATION_SCHEMA (Snowflake標準ビュー)
- 下流: [[DB_DESIGN.PROFILE_TABLE]] (個別テーブルプロファイル実行)
- 並列処理: [[DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL]] (結果をMarkdownでエクスポート)
- 集約層: [[DB_DESIGN.PROFILE_RESULTS]], [[DB_DESIGN.PROFILE_RUNS]]

---

## 設計方針

### 1. オーケストレーション設計
方針: 単純なループ処理で全テーブルを順次実行  
理由:
- Snowflakeのクエリキューイングにより、並列化は不要
- エラーハンドリングを個別テーブルレベルで実施
- 1テーブルの失敗が全体をブロックしない設計

実装:
```sql
FOR REC IN V_TBL_RS DO
  BEGIN
    CALL PROFILE_TABLE(...);
    -- 成功時の記録
  EXCEPTION
    WHEN OTHER THEN
      -- 失敗時の記録（処理継続）
  END;
END FOR;
```

### 2. エラーハンドリング
方針: Graceful Degradation（部分失敗を許容）  
理由:
- 1つのテーブルにアクセス権限がなくても、他のテーブルはプロファイル可能にする
- 大規模スキーマ（100テーブル以上）でも安定稼働を保証

実装:
- テーブルごとにTRY-CATCHで個別ハンドリング
- 失敗したテーブルは `status: 'FAILED'` として結果配列に記録
- 最終結果に `tables_processed`, `results` を含めることで、成功/失敗の内訳を可視化

### 3. 動的SQL設計
方針: 可変DB/スキーマに対応するため、動的SQLでテーブル一覧を取得  
理由:
- INFORMATION_SCHEMAは読み取り時にDBコンテキストが必要
- 他のデータベースに対してもプロファイル可能にする汎用性

実装:
```sql
V_SQL_LIST := '
SELECT TABLE_NAME
FROM ' || V_QDB || '.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = ' || V_QSC || '
  AND TABLE_TYPE = ''BASE TABLE''
ORDER BY TABLE_NAME
';
```

### 4. クォート・エスケープ処理
方針: SQLインジェクション対策として厳格にエスケープ  
理由:
- DB名/スキーマ名に特殊文字が含まれる可能性
- ダブルクォート（識別子）とシングルクォート（文字列リテラル）を使い分け

実装:
```sql
V_QDB := '"' || REPLACE(P_TARGET_DB,'"','""') || '"';
V_QSC := '''' || REPLACE(P_TARGET_SCHEMA,'''','''''') || '''';
```

---

## パラメータ設計

| パラメータ名 | 型 | 必須 | デフォルト値 | 説明 |
|---|---|---|---|---|
| `P_TARGET_DB` | STRING | ✅ | - | プロファイル対象のデータベース名 |
| `P_TARGET_SCHEMA` | STRING | ✅ | - | プロファイル対象のスキーマ名 |
| `P_SAMPLE_PCT` | FLOAT | - | NULL | サンプリング割合（0.0～1.0）。NULLの場合は全件スキャン |
| `P_NOTE` | STRING | - | `'manual weekly all-tables run'` | 実行メモ（運用管理用） |

### パラメータ設計の背景
- P_SAMPLE_PCT: 大規模テーブル（数億行）に対しては、サンプリングでコスト削減が可能。NULLの場合は正確性を優先
- P_NOTE: 定期実行 vs アドホック実行の区別、担当者の記録など、運用トレーサビリティ確保

---

## 戻り値設計

### 構造（JSON/VARIANT）
```json
{
  "target_db": "GBPS253YS_DB",
  "target_schema": "PUBLIC",
  "tables_processed": 23,
  "results": [
    {
      "table": "CUSTOMERS",
      "run_id": "01HX...",
      "status": "SUCCEEDED"
    },
    {
      "table": "ORDERS",
      "status": "FAILED",
      "error": "Insufficient privileges"
    }
  ]
}
```

### フィールド定義
- `target_db` / `target_schema`: 処理対象の識別子
- `tables_processed`: 処理を試行したテーブル数
- `results`: 各テーブルの実行結果配列
  - `table`: テーブル名
  - `run_id`: 成功時のPROFILE_RUNSのID
  - `status`: `SUCCEEDED` または `FAILED`
  - `error`: 失敗時のエラーメッセージ（`SQLERRM`）

---

## 内部処理フロー

### ステップ1: 初期化
```sql
V_RESULTS := ARRAY_CONSTRUCT();
V_QDB := '"' || REPLACE(P_TARGET_DB,'"','""') || '"';
V_QSC := '''' || REPLACE(P_TARGET_SCHEMA,'''','''''') || '''';
```

### ステップ2: テーブル一覧取得
```sql
V_SQL_LIST := '
SELECT TABLE_NAME
FROM ' || V_QDB || '.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = ' || V_QSC || '
  AND TABLE_TYPE = ''BASE TABLE''
ORDER BY TABLE_NAME
';
V_TBL_RS := (EXECUTE IMMEDIATE :V_SQL_LIST);
```
- INFORMATION_SCHEMA.TABLES: Snowflake標準ビューでテーブルメタデータ取得
- フィルタ: ``TABLE_TYPE` = 'BASE TABLE'` でビュー/マテリアライズドビューを除外
- ソート: `ORDER BY `TABLE_NAME`` で処理順序を安定化

### ステップ3: ループ実行（個別テーブルプロファイル）
```sql
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
    
    -- RUN_IDを取得（RESULT_SCAN）
    SELECT $1::STRING
      INTO :V_RUN_ID
      FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
    
    -- 成功レコードを追加
    V_RESULTS := ARRAY_APPEND(V_RESULTS, OBJECT_CONSTRUCT(...));
  EXCEPTION
    WHEN OTHER THEN
      -- 失敗レコードを追加
      V_RESULTS := ARRAY_APPEND(V_RESULTS, OBJECT_CONSTRUCT(...));
  END;
END FOR;
```

重要な実装ポイント:
- RESULT_SCAN(LAST_QUERY_ID()): PROFILE_TABLEの戻り値（`RUN_ID`）を取得
- 列名依存回避: `$1::STRING` で最初の列を取得（列名に依存しない）
- TRY-CATCH: 個別テーブルの失敗が全体に波及しない

### ステップ4: 結果返却
```sql
RETURN OBJECT_CONSTRUCT(
  'target_db', P_TARGET_DB,
  'target_schema', P_TARGET_SCHEMA,
  'tables_processed', ARRAY_SIZE(V_RESULTS),
  'results', V_RESULTS
);
```

---

## 運用

### 実行例1: 本番DBの全テーブルプロファイル
```sql
CALL DB_DESIGN.PROFILE_ALL_TABLES(
  'GBPS253YS_DB',
  'PUBLIC',
  NULL,  -- 全件スキャン
  'weekly scheduled profile'
);
```

### 実行例2: サンプリングプロファイル（10%）
```sql
CALL DB_DESIGN.PROFILE_ALL_TABLES(
  'ANALYTICS_DB',
  'STAGING',
  0.1,  -- 10%サンプリング
  'exploratory profile for new schema'
);
```

### 実行例3: 結果の確認
```sql
-- 最新のプロファイル実行履歴を確認
SELECT *
FROM DB_DESIGN.PROFILE_RUNS
WHERE TARGET_DB = 'GBPS253YS_DB'
  AND TARGET_SCHEMA = 'PUBLIC'
ORDER BY AS_OF_AT DESC
LIMIT 10;

-- 特定テーブルのプロファイル詳細
SELECT *
FROM DB_DESIGN.PROFILE_RESULTS
WHERE TARGET_DB = 'GBPS253YS_DB'
  AND TARGET_SCHEMA = 'PUBLIC'
  AND TARGET_TABLE = 'CUSTOMERS'
  AND RUN_ID = '01HX...'
ORDER BY TARGET_COLUMN;
```

### タスクスケジューリング（Snowflake Task推奨）
```sql
CREATE OR REPLACE TASK DB_DESIGN.WEEKLY_PROFILE_ALL
  WAREHOUSE = 'COMPUTE_WH'
  SCHEDULE = 'USING CRON 0 3 * * 0 UTC'  -- 毎週日曜 03:00 UTC
AS
  CALL DB_DESIGN.PROFILE_ALL_TABLES(
    'GBPS253YS_DB',
    'PUBLIC',
    NULL,
    'automated weekly profile'
  );

ALTER TASK DB_DESIGN.WEEKLY_PROFILE_ALL RESUME;
```

### モニタリング指標
- 実行時間: ``ARRAY_SIZE`(results)` で処理テーブル数を確認、予想実行時間を推定
- 失敗率: `results` 配列内の `status='FAILED'` 件数を集計
- アラート条件: 失敗率が20%を超える場合は権限問題を疑う

---

## パフォーマンス考慮

### 実行時間の見積もり
- 1テーブルあたり: 平均30秒～2分（テーブルサイズに依存）
- 100テーブルのスキーマ: 約50分～3時間
- 推奨: 大規模スキーマは深夜バッチで実行

### コスト最適化
- サンプリング活用: ``P_SAMPLE_PCT` = 0.1` で90%のコスト削減が可能
- Warehouse選択: `EXECUTE AS OWNER` のため、プロシージャ実行者のデフォルトWHを使用。専用WHの設定を推奨
- AUTO_SUSPEND: プロファイル完了後、WHが自動停止するよう設定

### 並列化の検討（将来拡張）
現行はシーケンシャル実行だが、将来的には以下の並列化が可能：
- Snowflake Task DAG: 複数のTaskで異なるスキーマを並列実行
- Pythonプロシージャ: `concurrent.futures` でマルチスレッド化
- 外部オーケストレーター: Airflow等で複数プロファイルジョブを並列スケジュール

---

## エラーハンドリングとリトライ

### 想定エラーケース
| エラー | 原因 | 対処方法 |
|---|---|---|
| `Insufficient privileges` | テーブルへのSELECT権限不足 | GRANTで権限付与、または該当テーブルをスキップ |
| `Object does not exist` | 実行中にテーブルがDROP | 一時的なエラーとして記録、次回実行で解消 |
| `Statement execution time limit exceeded` | 巨大テーブル（数十億行）のスキャン | `P_SAMPLE_PCT` を設定してサンプリング |
| `Warehouse suspended` | 実行中にWH停止 | WHのAUTO_RESUME設定を確認 |

### リトライ戦略
- 自動リトライ: 実装なし（個別テーブルの失敗は記録のみ）
- 手動リトライ: 失敗したテーブルのみを後から [[design.PROFILE_TABLE]] で個別実行
- 冪等性: 同じテーブルを複数回実行しても問題なし（新しいRUN_IDで記録）

---

## セキュリティとアクセス制御

### 実行権限
- EXECUTE AS OWNER: プロシージャ所有者の権限で実行
- 必要な権限:
  - `SELECT` on ``INFORMATION_SCHEMA`.TABLES`
  - `USAGE` on target database and schema
  - `SELECT` on all tables in target schema
  - `USAGE` on [[design.DB_DESIGN]] schema
  - `EXECUTE` on [[DB_DESIGN.PROFILE_TABLE]]
  - `INSERT` on [[DB_DESIGN.PROFILE_RUNS]], [[DB_DESIGN.PROFILE_RESULTS]]

### 権限設計の推奨事項
```sql
-- プロファイル専用ロール
CREATE ROLE IF NOT EXISTS PROFILER_ROLE;

-- DB_DESIGNスキーマへのアクセス
GRANT USAGE ON SCHEMA DB_DESIGN TO ROLE PROFILER_ROLE;
GRANT EXECUTE ON PROCEDURE DB_DESIGN.PROFILE_ALL_TABLES(...) TO ROLE PROFILER_ROLE;

-- 対象スキーマの読み取り権限（例: PUBLIC）
GRANT USAGE ON DATABASE GBPS253YS_DB TO ROLE PROFILER_ROLE;
GRANT USAGE ON SCHEMA GBPS253YS_DB.PUBLIC TO ROLE PROFILER_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA GBPS253YS_DB.PUBLIC TO ROLE PROFILER_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA GBPS253YS_DB.PUBLIC TO ROLE PROFILER_ROLE;
```

---

## データ品質とバリデーション

### 入力バリデーション
- `P_TARGET_DB` / `P_TARGET_SCHEMA`: 存在しない場合、INFORMATION_SCHEMA.TABLESで0件となり、空の結果を返す
- `P_SAMPLE_PCT`: 範囲外の値（負数、1超）は [[design.PROFILE_TABLE]] 側でバリデーション

### 結果の妥当性チェック
- 想定テーブル数との照合: 事前に `SELECT COUNT(*) FROM `INFORMATION_SCHEMA`.TABLES` で期待値を確認
- 失敗テーブルの調査: `status='FAILED'` のテーブルはエラーメッセージを確認し、権限/データ品質問題を特定

---

## 拡張計画

### フェーズ2: 並列実行対応
- SnowflakeのTask DAGで複数スキーマを並列プロファイル
- `P_MAX_PARALLEL` パラメータで並列度を制御

### フェーズ3: インクリメンタルプロファイル
- 前回実行時からデータ変更がないテーブルはスキップ
- `LAST_ALTERED` タイムスタンプを比較してスキップ判定

### フェーズ4: プロファイル結果の差分分析
- 前回実行との比較（null_rate増加、distinct_count減少など）を自動検出
- アラート条件に達した場合、Snowflake Alertで通知

### フェーズ5: Dynamic Sampling
- テーブルサイズに応じて自動的にサンプリング割合を調整
- 小規模テーブル（<1M行）: 全件、大規模テーブル（>100M行）: 1%サンプリング

---

## 関連ドキュメント

### 上位設計
- [[design.DB_DESIGN]] - DB_DESIGNスキーマ全体の設計方針
- [[design.EXPORT_PROFILE_EVIDENCE_MD_VFINAL]] - プロファイル結果のMarkdownエクスポート
- [[design.INGEST_VAULT_MD]] - エクスポートしたMarkdownをSnowflakeに再取り込み

### 詳細設計
- [[design.PROFILE_TABLE]] - 個別テーブルのプロファイル実行
- [[design.PROFILE_RUNS]] - プロファイル実行履歴テーブル
- [[design.PROFILE_RESULTS]] - カラム単位のメトリクス蓄積テーブル

### 運用ドキュメント
- [[S3_DESIGN_VAULT_DB_DOCS]] - S3バケット設計（Markdownエクスポート先）
- `SNOWFLAKE_PROFILING_OPERATIONS` - プロファイル運用手順（未作成）

---

## 変更履歴

| 日付 | 変更者 | 変更内容 |
|---|---|---|
| 2026-01-02 | System | 初版作成（[[design.PROFILE_ALL_TABLES]]） |

---

## メタデータ

- 作成日: 2026-01-02
- 最終更新日: 2026-01-02
- ステータス: 運用中
- レビュー担当: DB設計チーム
- 次回レビュー予定: 2026-02-01
