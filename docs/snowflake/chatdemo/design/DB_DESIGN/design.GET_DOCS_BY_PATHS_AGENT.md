# [[design.GET_DOCS_BY_PATHS_AGENT]] 設計書

## 概要

GET_DOCS_BY_PATHS_AGENTは、Obsidian Vault内のドキュメントを指定されたPATHリスト（JSON配列）から一括取得するストアドプロシージャである。DOCS_OBSIDIAN_Vビューから該当するドキュメント本文とメタ情報を取得し、存在しないPATHについてはmissingリストとして返却する。

## 業務上の意味

Cortex Agentがレビューやクエリ実行時に複数のドキュメントを参照する必要がある場合、1ファイルずつ個別に検索するよりも、PATHリストを一括で渡して一度に取得する方が効率的である。本プロシージャは、list_schema_related_doc_pathsやlist_table_related_doc_pathsで列挙されたPATHリストを受け取り、該当する全ドキュメントの本文を一括で返却する。

存在しないPATHについてもmissingリストとして明示的に返すことで、エージェントがどのドキュメントが欠落しているかを把握でき、適切なエラーハンドリングが可能となる。

## 設計上の位置づけ

本プロシージャはDB_DESIGNスキーマに配置され、DOCS_OBSIDIAN_Vビューを参照する。DOCS_OBSIDIAN_Vはmaster、design、reviews等のObsidian VaultのMarkdownファイルを格納したビューである。

本プロシージャは、OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENTをはじめとする各種Cortex Agentからgeneric toolとして呼び出され、ドキュメント本文取得の共通インターフェースとして機能する。

## 機能

1. JSON配列の解析とバリデーション
   - PATHS_JSON引数をPARSE_JSONで配列型に変換
   - 配列型でない場合はエラーメッセージを返却
   - PATHS_JSONがNULLまたは空文字列の場合もエラー

2. ドキュメントの一括取得（docs配列）
   - PATHS_JSON内の各PATHについて、[[design.DOCS_OBSIDIAN_V]].PATHと照合
   - 存在するドキュメントについて、以下の情報を含むオブジェクトを配列化
     - path, doc_id, folder, scope, file_type, run_date
     - target_schema, target_table, target_column
     - updated_at, content（MAX_CHARSで指定された文字数まで切り詰め）

3. 欠落ドキュメントの列挙（missing配列）
   - PATHS_JSON内のPATHでDOCS_OBSIDIAN_Vに存在しないものをリストアップ
   - 存在しないPATHをmissing配列として返却

4. 結果の返却
   - docs配列、missing配列、各カウントをVARIANT型で返却
   - docsはREQ_PATH順にソート、missingもREQ_PATH順にソート

## パラメータ

`PATHS_JSON`（必須）:
- 型: STRING
- 説明: JSON配列文字列（例: ["design/design.[[design.DB_DESIGN]].md", "master/tables/APP_PRODUCTION.CUSTOMER_MASTER.md"]）
- 制約: NULLまたは空文字列は不可、配列型でない場合はエラー

`MAX_CHARS`（任意）:
- 型: STRING
- 説明: ドキュメント本文の最大文字数を指定（例: "5000"）
- 制約: 数値に変換可能な文字列、省略時はCONTENT全文を返却

## 利用シーン

- スキーマレビュー時のドキュメント一括取得: list_schema_related_doc_pathsで取得したPATHリストを渡し、スキーマに関連する全ドキュメントを一度に取得
- テーブルレビュー時のカラムドキュメント取得: list_table_related_doc_pathsで取得したPATHリスト（カラムを含む）を渡し、テーブルとカラムの設計情報を一括取得
- Evidenceの具体的な抜粋取得: レビュー時に指摘の根拠となる特定のドキュメントPATHリストを渡し、Evidence用の抜粋を取得
- ドキュメント存在確認: 指定したPATHリストのうち、どのドキュメントが存在し、どのドキュメントが欠落しているかを確認
- 大量ドキュメントの効率的取得: 個別検索ではなく一括取得によりクエリ実行回数を削減し、パフォーマンスを向上
