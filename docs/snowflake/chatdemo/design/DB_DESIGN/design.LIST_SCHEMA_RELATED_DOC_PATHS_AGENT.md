# [[LIST_SCHEMA_RELATED_DOC_PATHS_AGENT]] 設計書

## 概要

LIST_SCHEMA_RELATED_DOC_PATHS_AGENTは、指定されたスキーマに関連するObsidian VaultのドキュメントPATHを列挙するストアドプロシージャである。上位設計ドキュメント（design/design.[[DB_DESIGN]].md、design/design.<SCHEMA>.md）と、当該スキーマに属するmaster/tablesのPATHを収集し、重複排除してJSON配列として返却する。

## 業務上の意味

スキーマ単位のデータベース設計レビューを実行する際、対象スキーマに関連する全ドキュメントを漏れなく収集する必要がある。本プロシージャは、スキーマ名を受け取り、上位設計ドキュメントとテーブルマスタ情報を自動的に列挙することで、レビュー対象範囲を確定する。

これにより、エージェントは「どのドキュメントを読むべきか」を手動で指定する必要がなくなり、スキーマ名だけで関連ドキュメント一覧を取得できる。MAX_TABLESパラメータにより、大規模スキーマでもテーブル数を制限し、レビュー範囲を調整可能である。

## 設計上の位置づけ

本プロシージャはDB_DESIGNスキーマに配置され、DOCS_OBSIDIAN_Vビューを参照する。DOCS_OBSIDIAN_Vは、Obsidian Vault内のMarkdownファイルをPATH、SCOPE、[[FILE_TYPE]]、TARGET_SCHEMA等のメタ情報とともに保持している。

本プロシージャは、OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENTからgeneric toolとして呼び出され、スキーマレビューの第1ステップ（ドキュメントPATH列挙）を担当する。列挙されたPATHリストは、次にget_docs_by_pathsに渡されて本文が取得される。

## 機能

1. 引数バリデーション
   - TARGET_SCHEMAがNULLまたは空文字列の場合、エラーを返却
   - MAX_TABLESは省略可能（デフォルト2000）、数値変換可能な文字列として受け取る

2. 上位設計ドキュメントの追加
   - 固定的にdesign/design.[[DB_DESIGN]].mdを含める（全スキーマ共通の設計方針）
   - design/design.<[[TARGET_SCHEMA]]>.mdを含める（対象スキーマの設計方針）

3. テーブルマスタの列挙
   - DOCS_OBSIDIAN_VからPATH LIKE 'master/tables/%'で絞り込み
   - [[TARGET_SCHEMA]] = :v_schemaでスキーマを絞り込み
   - ROW_NUMBERでMAX_TABLES件までに制限

4. 重複排除とソート
   - 上位設計とテーブルマスタを結合（[[ARRAY_CAT]]）
   - DISTINCTで重複を排除（同じPATHが複数回含まれる場合を想定）
   - PATH順にソートしてJSON配列として返却

5. 結果の返却
   - target_schema: 対象スキーマ名
   - count: 列挙されたPATH数
   - paths: PATH配列（VARIANT型）
   - paths_json: PATH配列のJSON文字列（get_docs_by_pathsにそのまま渡せる形式）

## パラメータ

[[TARGET_SCHEMA]]（必須）:
- 型: STRING
- 説明: 対象スキーマ名（例: "[[APP_PRODUCTION]]"、"[[DB_DESIGN]]"）
- 制約: NULLまたは空文字列は不可

[[MAX_TABLES]]（任意）:
- 型: STRING
- 説明: テーブル数上限を指定する文字列（例: "2000"）
- 制約: 数値に変換可能な文字列、省略時はデフォルト2000

## 利用シーン

- スキーマレビューのドキュメント範囲確定: OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENTが最初に本プロシージャを呼び出し、対象スキーマのドキュメントPATHリストを取得
- 上位設計とテーブルマスタの一括列挙: 設計方針ドキュメントとテーブル定義を一度に取得し、スキーマ全体の設計を俯瞰
- 大規模スキーマのレビュー範囲調整: MAX_TABLESを指定し、テーブル数が多いスキーマでもレビュー対象を制限
- 設計ドキュメントの棚卸し: 特定スキーマに関連するドキュメントが何件存在するかを確認
- レビューの自動化: スキーマ名だけを指定すれば、関連ドキュメントを自動的に列挙し、次のステップ（本文取得）に進める
