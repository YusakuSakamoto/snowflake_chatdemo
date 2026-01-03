
---
type: agent_review
review_date: 2026-01-03
target: DB_DESIGN
---

# DB_DESIGN 設計レビュー

## 0. メタ情報
- 対象: DB_DESIGN
- レビュー日: 2026-01-03
- 対象ノート候補（PATH一覧）:
  - README_DB_DESIGN.md
  - design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
  - design/design.DB_DESIGN.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.AS_OF_AT.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.METRICS.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.RUN_ID.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_COLUMN.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_DB.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_SCHEMA.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_TABLE.md
  - master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md

## 1. サマリ（3行）
- 外部テーブル EXT_PROFILE_RESULTS の設計は基本的に適切だが、複合主キー設計において参照整合性の仕様不備がある
- VARIANT型の METRICS カラムは設計思想に沿った適切な選択だが、型安全性の運用的担保が不明確
- S3パーティショニング戦略とファイルフォーマットは外部テーブル最適化のベストプラクティスに準拠

## 2. Findings（重要度別）

### High
#### High-1: 複合主キー構成の参照整合性不備
- 指摘: RUN_ID と TARGET_COLUMN を複合主キーとする設計において、RUN_ID の参照先テーブル情報が不完全
- 影響: プロファイル実行履歴との論理的整合性が運用時に担保できず、データ品質問題やクエリエラーの原因となる
- 提案: RUN_ID カラムの ref_table_id に参照先（PROFILE_RUNS テーブル相当）のテーブルIDを明記し、論理的な参照関係を明確化する
- Evidence:
  - PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.RUN_ID.md
    抜粋: "ref_table_id: \nref_column: \nref_cardinality:"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "[[DB_DESIGN.PROFILE_RUNS.RUN_ID]] を起点として、対象テーブル・対象カラム・計測時点・計測結果を紐づける"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.RUN_ID.md
    変更内容: |
      ref_table_id: TBL_PROFILE_RUNS
      ref_column: RUN_ID
      ref_cardinality: many_to_one
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 今週

### Med
#### Med-1: ファイルフォーマット指定の不整合
- 指摘: 外部テーブル定義でファイルフォーマットが JSON と記載されているが、設計書では JSON Lines形式（NDJSON）を前提としている
- 影響: 実装時にファイル読み込みエラーや予期しない解析結果を招く可能性
- 提案: ファイルフォーマット指定を実際の用途（JSON Lines）に合わせて修正するか、設計書の記述を統一する
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "file_format: JSON"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "ファイルフォーマット：FF_JSON_LINES\n1行1JSONのJSON Lines形式（NDJSON）を採用"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      file_format: FF_JSON_LINES
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

#### Med-2: VARIANT型データ構造仕様の不明確さ
- 指摘: METRICS カラムのVARIANT型にどのような構造のJSONが格納されるかが仕様として明文化されていない
- 影響: データ品質検証やクエリ作成時に予期しない構造差異により運用障害を招く可能性
- 提案: METRICS に格納されるJSON構造のサンプルまたはスキーマ定義を設計書に追記する
- Evidence:
  - PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.METRICS.md
    抜粋: "カラム単位のプロファイル計測結果を格納するVARIANT。NULL率、件数、distinct数、最小値・最大値などを柔軟に保持する"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    変更内容: |
      JSON構造サンプルセクションを追加し、典型的なMETRICS構造例を記載
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 中
  - 推奨実施時期: 今月

#### Med-3: パーティション列の物理定義不足
- 指摘: パーティション列（YEAR/MONTH/DAY）が外部テーブル定義に記載されているが、対応するカラム定義ファイルが存在しない
- 影響: パーティションプルーニング機能の正常動作が不明確で、クエリ性能劣化やコスト増大を招く可能性
- 提案: パーティション列の物理定義（型、nullable等）を明確化するか、仮想列としての扱いを設計書で明記する
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "partition_by:\n  - YEAR\n  - MONTH\n  - DAY"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    変更内容: |
      パーティション列は仮想列として扱われ、S3パス構造から自動抽出される旨を明記
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 今月

## 3. 追加で集めたい情報
- 追加調査: PROFILE_RUNS テーブルの定義詳細
- 追加ツール実行案: list_table_related_doc_paths で PROFILE_RUNS テーブルの存在確認と定義取得

## 4. 改善提案（次アクション）
- 実施内容: RUN_ID カラムの参照関係定義の完全化とファイルフォーマット仕様の統一
- 期待効果: プロファイル結果データの整合性向上と実装時の設定ミス防止
- 優先度: High
- 変更対象PATH（案）: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.RUN_ID.md, master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
- 影響範囲: 中
- 実装難易度: 低
- 推奨実施時期: 今週
