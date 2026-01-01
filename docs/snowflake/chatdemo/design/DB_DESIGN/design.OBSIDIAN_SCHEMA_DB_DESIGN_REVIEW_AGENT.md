# OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT 設計書

## 概要

OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENTは、Obsidian Vault（master/design/reviews）を根拠に、スキーマ単位のデータベース設計を静的にレビューするCortex Agentである。Cortex Searchを使用せず、ストアドプロシージャ（generic tool）のみを用いてPATH列挙→本文取得の流れで実行し、NULL引数の送信を禁止することで安定動作を実現している。

## 業務上の意味

データベース設計の正本はObsidian Vault内のMarkdownファイルであり、これらを機械的にレビューすることで、命名規則の一貫性、型定義の妥当性、PK/FK設計の適切性、履歴管理の網羅性といった設計品質を定量的に評価できる。

従来の手動レビューでは見落としがちな細かな不整合や、複数テーブルにまたがる概念の統一性を、エージェントが自動検出し、Evidenceとして具体的なVaultパスと抜粋を提示する。これにより、設計レビューの精度向上と効率化を実現する。

## 設計上の位置づけ

本エージェントはDB_DESIGNスキーマに配置され、以下のストアドプロシージャをgeneric toolとして利用する。

- list_schema_related_doc_paths: 対象スキーマに関連するドキュメントPATHを列挙
- get_docs_by_paths: 指定されたPATHリストから本文を一括取得
- list_table_related_doc_paths: 特定テーブルに関連するドキュメントPATH（カラム含む）を列挙

Cortex SearchやDBの実データ/DDLへの直接参照は禁止されており、あくまでVault内のMarkdownを唯一の根拠としてレビューを実行する。

## 機能

1. スキーマレビュー手順（必須実行）
   - list_schema_related_doc_pathsを実行し、対象スキーマのドキュメントPATHリストを取得
   - get_docs_by_pathsにPATHリストを渡し、本文を一括取得
   - 全体を読み込み、命名・概念の一貫性、型統一、nullable/defaultの妥当性等をレビュー

2. テーブル詳細レビュー（必要時のみ）
   - 指摘のためカラム情報が必要なテーブルのみ、list_table_related_doc_pathsを実行
   - include_columnsを"true"にしてカラムドキュメントも含めて取得
   - get_docs_by_pathsで本文を取得し、カラムレベルの詳細レビュー

3. Evidenceの収集（必須ルール）
   - 各指摘につきちょうど2件のEvidenceを提示
   - PATHはVault上に実在する.mdファイルのみ（必ず.mdで終わる）
   - PATH不明の指摘は成立させない
   - Evidence2件が揃わない指摘はHighにしない

4. 重要度別の出力制限
   - High指摘は最大3件
   - Findings合計は10件以内
   - 重要度別の抜粋とVault差分案を含む

## パラメータ

本エージェントはスキーマ名を受け取り、以下のツールに対して文字列形式のパラメータを渡す（JSONのnullは禁止）。

list_schema_related_doc_pathsへのパラメータ:
- target_schema: 対象スキーマ名（必須）
- max_tables: テーブル数上限（任意、省略時は2000、文字列で指定："2000"）

get_docs_by_pathsへのパラメータ:
- paths_json: JSON配列文字列（必須、list_schema_related_doc_pathsから取得）
- max_chars: 文字数上限（任意、省略可能、指定する場合は文字列："5000"）

list_table_related_doc_pathsへのパラメータ:
- target_schema: 対象スキーマ名（必須）
- target_table: 対象テーブル名（必須）
- include_columns: カラムを含むか（必須、"true"または"false"）
- max_columns: カラム数上限（任意、省略時は5000、文字列で指定："5000"）

## 利用シーン

- スキーマ単位の設計レビュー実行: 「DB_DESIGNスキーマをレビューして」といった指示で、スキーマ全体の設計品質を自動評価
- 命名規則チェック: スキーマ内の複数テーブルで命名の一貫性が保たれているかを横断的に検証
- 型定義・制約の統一性確認: 同一概念（顧客ID、部署ID等）が複数テーブルで同じ型・制約で定義されているかを検証
- PK/FK設計の妥当性評価: 不変性・一意性の観点からPK/FK設計が適切かを評価
- 履歴管理・監査設計の網羅性確認: 状態管理カラム、時刻カラム、履歴テーブルの有無を確認し、運用拡張性を評価
- 設計レビューの自動化: 定期的にエージェントを実行し、設計変更時の影響を自動検出
- レビュー結果のVault保存: 出力結果はreviews/ディレクトリに保存可能なMarkdown形式で生成
