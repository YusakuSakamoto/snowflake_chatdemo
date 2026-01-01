# [[design.LIST_TABLE_RELATED_DOC_PATHS_AGENT]] 設計書

## 概要

LIST_TABLE_RELATED_DOC_PATHS_AGENTは、指定されたスキーマ・テーブルに関連するObsidian VaultのドキュメントPATHを列挙するストアドプロシージャである。上位設計ドキュメント、テーブルマスタ、テーブル設計ドキュメント、およびオプションでカラムマスタを収集し、重複排除してJSON配列として返却する。

## 業務上の意味

テーブル単位のデータベース設計レビューや、特定のテーブル設計を詳細に確認する際、関連する全ドキュメントを漏れなく収集する必要がある。本プロシージャは、スキーマ名とテーブル名を受け取り、上位設計（DB全体、スキーマ全体）、テーブルマスタ、テーブル設計ドキュメント、さらにINCLUDE_COLUMNSフラグがtrueの場合はカラムマスタも含めて列挙する。

これにより、エージェントはテーブルレベルの詳細なレビューや、カラム単位の型・制約チェックを実行する際に必要なドキュメントを一括で取得できる。

## 設計上の位置づけ

本プロシージャはDB_DESIGNスキーマに配置され、[[design.DOCS_OBSIDIAN_V]]ビューを参照する。[[design.DOCS_OBSIDIAN_V]]は、Obsidian Vault内のMarkdownファイルをPATH、`TARGET_SCHEMA`、`TARGET_TABLE`、`TARGET_COLUMN`等のメタ情報とともに保持している。

本プロシージャは、[[design.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT]]からgeneric toolとして呼び出され、特定テーブルの詳細レビュー時（カラム情報が必要な場合）に使用される。列挙されたPATHリストは、[[design.GET_DOCS_BY_PATHS_AGENT]]に渡されて本文が取得される。

## 機能

1. 引数バリデーション
   - TARGET_SCHEMAがNULLまたは空文字列の場合、エラーを返却
   - TARGET_TABLEがNULLまたは空文字列の場合、エラーを返却
   - INCLUDE_COLUMNSは"true"/"false"/"1"/"0"/"yes"/"y"を受け付け、BOOLEANに変換（省略時はfalse）
   - MAX_COLUMNSは省略可能（デフォルト5000）、数値変換可能な文字列として受け取る

2. 上位設計ドキュメントの追加
   - design/[[design.DB_DESIGN]].md（全スキーマ共通の設計方針）
   - design/design.<`TARGET_SCHEMA`>.md（対象スキーマの設計方針）

3. テーブル固有ドキュメントの追加
   - master/tables/<SCHEMA>.<TABLE>.md（テーブルマスタ）
   - design/<SCHEMA>/design.<TABLE>.md（テーブル設計ドキュメント）

4. カラムマスタの列挙（INCLUDE_COLUMNSがtrueの場合のみ）
   - DOCS_OBSIDIAN_VからPATH LIKE 'master/columns/%'で絞り込み
   - `TARGET_SCHEMA` = :v_schema AND `TARGET_TABLE` = :v_tableでスキーマ・テーブルを絞り込み
   - ROW_NUMBERでMAX_COLUMNS件までに制限

5. 重複排除とソート
   - 上位設計、テーブル固有、カラムマスタを結合（`ARRAY_CAT`）
   - DISTINCTで重複を排除
   - PATH順にソートしてJSON配列として返却

6. 結果の返却
   - target_schema: 対象スキーマ名
   - target_table: 対象テーブル名
   - include_columns: カラムマスタを含めたかどうか
   - count: 列挙されたPATH数
   - paths: PATH配列（VARIANT型）
   - paths_json: PATH配列のJSON文字列（get_docs_by_pathsにそのまま渡せる形式）

## パラメータ

`TARGET_SCHEMA`（必須）:
- 型: STRING
- 説明: 対象スキーマ名（例: "[[design.APP_PRODUCTION]]"、"[[design.DB_DESIGN]]"）
- 制約: NULLまたは空文字列は不可

`TARGET_TABLE`（必須）:
- 型: STRING
- 説明: 対象テーブル名（例: "`CUSTOMER_MASTER`"、"[[design.DOCS_OBSIDIAN_V]]"）
- 制約: NULLまたは空文字列は不可

`INCLUDE_COLUMNS`（必須）:
- 型: STRING
- 説明: カラムマスタを含めるかどうか（"true"/"false"）
- 制約: "true"/"false"/"1"/"0"/"yes"/"y"を受け付け、BOOLEANに変換

`MAX_COLUMNS`（任意）:
- 型: STRING
- 説明: カラム数上限を指定する文字列（例: "5000"）
- 制約: 数値に変換可能な文字列、省略時はデフォルト5000

## 利用シーン

- テーブルレビュー時のドキュメント範囲確定: [[DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT]]が指摘のためカラム情報が必要なテーブルについて、本プロシージャを呼び出してドキュメントPATHリストを取得
- カラムレベルの詳細レビュー: INCLUDE_COLUMNSを"true"にしてカラムマスタを含め、カラム単位の型・制約・nullable設計をレビュー
- テーブル固有の設計確認: 特定テーブルの設計方針、テーブルマスタ、テーブル設計ドキュメントを一括で取得
- カラム数制限: MAX_COLUMNSを指定し、カラム数が多いテーブルでもレビュー対象カラムを制限
- 設計ドキュメントの棚卸し: 特定テーブルに関連するドキュメントが何件存在するかを確認（カラム含む/含まない）
- レビューの自動化: スキーマ名とテーブル名だけを指定すれば、関連ドキュメントを自動的に列挙し、次のステップ（本文取得）に進める
