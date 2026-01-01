# Snowflake オブジェクト命名規則

## 概要
本ドキュメントは、Snowflakeのデータベースオブジェクトに対する命名規則を定義します。一貫性のある命名により、オブジェクトの種類や用途を即座に識別でき、保守性とコードの可読性が向上します。

## 命名規則一覧

### スキーマ（Schema）
- **形式**: `大文字の英単語`
- **例**: 
  - `APP_PRODUCTION` - 本番アプリケーションデータ
  - `APP_DEVELOPMENT` - 開発環境データ
  - `DB_DESIGN` - DB設計・メタデータ管理
  - `NAME_RESOLUTION` - エンティティ名解決
  - `LOG` - ログデータ集約

### テーブル（Table）
- **形式**: `大文字の英単語_大文字の英単語`
- **例**:
  - `ANKEN_MEISAI` - 案件明細テーブル
  - `DEPARTMENT_MASTER` - 部署マスタ
  - `DOCS_OBSIDIAN` - Obsidianドキュメント管理
  - `PROFILE_RESULTS` - プロファイル結果
  - `PROFILE_RUNS` - プロファイル実行履歴

### ビュー（View）
- **形式**: `V_` + `大文字の英単語_大文字の英単語`
- **プレフィックス**: `V_`
- **例**:
  - `V_CUSTOMER_MASTER` - 顧客マスタビュー
  - `V_ORDER_MASTER` - 受注マスタビュー
  - `V_PROJECT_FACT` - プロジェクトファクトビュー
  - `V_ENTITY_ALIAS_ALL` - エンティティエイリアス統合ビュー
  - `V_PROFILE_RESULTS_LATEST` - 最新プロファイル結果ビュー

### マテリアライズドビュー（Materialized View）
- **形式**: `MV_` + `大文字の英単語_大文字の英単語`
- **プレフィックス**: `MV_`
- **例**:
  - `MV_DAILY_SALES_SUMMARY` - 日次売上サマリー
  - `MV_CUSTOMER_PROFILE` - 顧客プロファイル
  - `MV_PROJECT_METRICS` - プロジェクトメトリクス

### 外部テーブル（External Table）
- **形式**: 通常のテーブルと同じ、または `_EXTERNAL` サフィックス
- **例**:
  - `CORTEX_CONVERSATIONS` - Cortex対話ログ（外部テーブル）
  - `AZFUNCTIONS_LOGS` - Azure Functions実行ログ（外部テーブル）
  - `PROFILE_RESULTS_EXTERNAL` - プロファイル結果（外部テーブル）
  - `PROFILE_RUNS_EXTERNAL` - プロファイル実行履歴（外部テーブル）

### カラム（Column）
- **形式**: `大文字の英単語_大文字の英単語` または `小文字の英単語_小文字の英単語`
- **推奨**: 大文字（Snowflakeの標準に従う）
- **例**:
  - `CUSTOMER_ID` - 顧客ID
  - `CREATED_AT` - 作成日時
  - `TARGET_DB` - 対象データベース
  - `TARGET_SCHEMA` - 対象スキーマ
  - `TARGET_TABLE` - 対象テーブル
  - `TARGET_COLUMN` - 対象カラム

### プロシージャ（Procedure）
- **形式**: `大文字の英単語_大文字の英単語`
- **動詞始まり推奨**:
  - `PROFILE_TABLE` - テーブルプロファイル実行
  - `PROFILE_COLUMN` - カラムプロファイル実行
  - `PROFILE_ALL_TABLES` - 全テーブルプロファイル実行
  - `EXPORT_PROFILE_EVIDENCE_MD_VFINAL` - プロファイル結果エクスポート
  - `INGEST_VAULT_MD` - Vaultドキュメント取り込み
  - `RESOLVE_ENTITY_ALIAS` - エンティティエイリアス解決

### 関数（Function）
- **形式**: `大文字の英単語_大文字の英単語`
- **動詞始まり推奨**:
  - `NORMALIZE_JA` - 日本語正規化
  - `NORMALIZE_JA_DEPT` - 部署名正規化

### Cortex Agentツール（Tool）
- **形式**: `動詞_名詞_TOOL` または `動詞_名詞_AGENT`
- **例**:
  - `RESOLVE_ENTITY_ALIAS_TOOL` - エンティティエイリアス解決ツール
  - `EXPAND_DEPARTMENT_SCOPE_TOOL` - 部署スコープ展開ツール
  - `GET_DOCS_BY_PATHS_AGENT` - ドキュメントパス検索エージェント
  - `LIST_SCHEMA_RELATED_DOC_PATHS_AGENT` - スキーマ関連ドキュメントパス一覧エージェント

### ステージ（Stage）
- **形式**: `大文字の英単語_STAGE`
- **サフィックス**: `_STAGE`
- **例**:
  - `OBSIDIAN_VAULT_STAGE` - Obsidian Vault用S3ステージ

### ファイルフォーマット（File Format）
- **形式**: `FF_` + `大文字の英単語`
- **プレフィックス**: `FF_`
- **例**:
  - `FF_JSON_LINES` - JSON Lines形式
  - `FF_CSV_STANDARD` - 標準CSV形式
  - `FF_MD_LINE` - Markdown行単位形式

### パーティションカラム（Partition Column）
- **形式**: 小文字の英単語
- **例**:
  - `year` - 年パーティション
  - `month` - 月パーティション
  - `day` - 日パーティション
  - `hour` - 時間パーティション

## 設計ドキュメント命名規則

### 設計ドキュメント（Design Document）
- **形式**: `design.` + `スキーマ名` または `design.` + `オブジェクト名`
- **拡張子**: `.md`
- **例**:
  - `design.APP_PRODUCTION.md` - APP_PRODUCTIONスキーマ設計
  - `design.ANKEN_MEISAI.md` - ANKEN_MEISAIテーブル設計
  - `design.V_CUSTOMER_MASTER.md` - V_CUSTOMER_MASTERビュー設計
  - `design.PROFILE_TABLE.md` - PROFILE_TABLEプロシージャ設計

### マスター定義ファイル（Master Definition）
- **形式**: `スキーマ名.オブジェクト名.md`
- **例**:
  - `APP_PRODUCTION.ANKEN_MEISAI.md` - テーブル定義
  - `DB_DESIGN.V_PROFILE_RESULTS_LATEST.md` - ビュー定義
  - `LOG.CORTEX_CONVERSATIONS.md` - 外部テーブル定義

## Obsidian リンク規則

### オブジェクト参照
設計ドキュメント内でテーブル名、カラム名、ビュー名などを参照する際は、Obsidianの内部リンク記法 `[[]]` を使用します。

#### テーブル参照
```markdown
[[ANKEN_MEISAI]] テーブルは、案件明細のランディングテーブルです。
[[DEPARTMENT_MASTER]] から部署情報を取得します。
```

#### カラム参照
```markdown
[[CUSTOMER_ID]] カラムは顧客を一意に識別します。
[[TARGET_SCHEMA]] には対象スキーマ名が格納されます。
```

#### ビュー参照
```markdown
[[V_CUSTOMER_MASTER]] ビューは、顧客マスタの最新状態を提供します。
[[V_ENTITY_ALIAS_ALL]] で統合されたエイリアス情報を参照します。
```

#### プロシージャ参照
```markdown
[[PROFILE_ALL_TABLES]] を実行して全テーブルをプロファイルします。
[[RESOLVE_ENTITY_ALIAS]] でエンティティ名を解決します。
```

#### 設計書相互参照
```markdown
詳細は [[design.ANKEN_MEISAI]] を参照してください。
[[design.APP_PRODUCTION]] にスキーマ全体の設計方針があります。
```

### リンクの利点
- **名称変更への対応**: Obsidianでファイル名を変更すると、リンクしているすべてのドキュメントが自動更新される
- **トレーサビリティ**: オブジェクト間の依存関係を追跡しやすい
- **ナビゲーション**: Ctrl+クリックで即座に定義元へジャンプ可能
- **グラフビュー**: オブジェクト間の関係を視覚化できる

## 命名の原則

### 1. 一貫性
- 同じ種類のオブジェクトには同じ命名パターンを適用
- プレフィックス・サフィックスを統一

### 2. 明確性
- 略語を避け、完全な英単語を使用（ただし、ID, DBなど一般的な略語は可）
- オブジェクトの用途が名前から理解できるようにする

### 3. 簡潔性
- 長すぎる名前は避ける（40文字以内推奨）
- 冗長な単語を省略（例: `TABLE_` プレフィックスは不要）

### 4. 予約語の回避
- SnowflakeのSQL予約語は避ける（例: `SELECT`, `FROM`, `WHERE`）
- 使用する場合はダブルクォートで囲む

### 5. 大文字・小文字の使い分け
- **スキーマ・テーブル・カラム**: 大文字（Snowflake標準）
- **パーティションカラム**: 小文字（Hiveスタイル互換）

## 既存オブジェクトの移行

### ビュー名の修正
現在、一部のビューが `V_` プレフィックスなしで命名されている場合、以下の手順で移行：

1. 新しい名前でビューを作成（例: `CUSTOMER_MASTER` → `V_CUSTOMER_MASTER`）
2. 依存するビュー・プロシージャを更新
3. 古いビューを削除
4. 設計ドキュメントを更新

### マテリアライズドビューの導入
現在、マテリアライズドビューが存在しない場合、以下のガイドラインで導入：

- 頻繁にクエリされる集計ビューを対象
- `MV_` プレフィックスを使用
- リフレッシュ戦略を明確に定義（FULL, INCREMENTAL）

## 関連ドキュメント

- [[design.APP_PRODUCTION]] - APP_PRODUCTIONスキーマ設計
- [[design.DB_DESIGN]] - DB_DESIGNスキーマ設計
- [[design.LOG]] - LOGスキーマ設計
- [[design.NAME_RESOLUTION]] - NAME_RESOLUTIONスキーマ設計
- [[README_DB_DESIGN]] - DB設計全体のREADME

## 変更履歴

| 日付 | 変更者 | 変更内容 |
|---|---|---|
| 2026-01-02 | System | 初版作成（命名規則の標準化、Obsidianリンク規則の追加） |

## メタデータ

- 作成日: 2026-01-02
- 最終更新日: 2026-01-02
- ステータス: 運用中
- レビュー担当: DB設計チーム
- 次回レビュー予定: 2026-02-01
