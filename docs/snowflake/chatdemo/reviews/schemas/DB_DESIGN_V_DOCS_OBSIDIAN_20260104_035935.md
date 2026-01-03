
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
  - design/design.DB_DESIGN.md
  - design/DB_DESIGN/design.V_DOCS_OBSIDIAN.md
  - master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md

## 1. サマリ（3行）
- DB_DESIGN スキーマは Obsidian Vault を正本とした DB 設計管理基盤として明確に定義され、設計思想と制約ルールが適切に文書化されている
- V_DOCS_OBSIDIAN ビューは複雑な正規表現を含むクエリロジックで設計されているが、カラムドキュメントとコメントに不整合が見られる
- スキーマ全体の命名規則と基本方針は十分に整備されているが、運用監視とエラーハンドリングの設計に改善の余地がある

## 2. Findings（重要度別）

### High
#### High-1: V_DOCS_OBSIDIAN のカラムドキュメント不整合
- 指摘: master定義のview_idとschema_idに対応するカラムがビューSQLに存在しない
- 影響: Cortex Agent/Searchがビュー構造を誤認識し、不正な検索クエリを生成する可能性
- 提案: ビューSQLにview_idとschema_idを追加するか、master定義から削除して整合性を保つ
- Evidence:
  - PATH: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
    抜粋: "view_id: VW_20251227014013"、"schema_id: SCH_20251226180633"
  - PATH: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
    抜粋: "SELECT DOC_ID, PATH, FOLDER, CONTENT, UPDATED_AT, SCOPE, FILE_TYPE..."
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
    変更内容: |
      frontmatterからview_idとschema_idを削除、またはSELECT句にリテラル値として追加
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 即時

#### High-2: 正規表現パターンの複雑性とメンテナンス性
- 指摘: V_DOCS_OBSIDIAN の正規表現が複雑で、PATH規約変更時の影響範囲が大きい
- 影響: パス規約変更時にビューロジックの修正が必要になり、修正漏れによるデータ抽出エラーのリスク
- 提案: 正規表現パターンを定数テーブル化するか、より単純な文字列操作に分解する
- Evidence:
  - PATH: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
    抜粋: "REGEXP_SUBSTR( PATH, 'master/columns/([^.]+)\\\\\\\\.'..."
  - PATH: design/DB_DESIGN/design.V_DOCS_OBSIDIAN.md
    抜粋: "PATH規約が変更された場合、本ビュー内の正規表現パターンも合わせて修正が必要"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
    変更内容: |
      正規表現を単純な SPLIT / SUBSTRING 操作に変更、またはマスタテーブルでパターン管理
- 実装メタ情報:
  - 影響範囲: 大
  - 実装難易度: 中
  - 推奨実施時期: 今月

### Med
#### Med-1: 運用監視項目の設計詳細不足
- 指摘: プロファイル・Agent実行の監視項目が抽象的で、具体的な閾値や対応手順が不明
- 影響: 運用時にパフォーマンス劣化やエラーを検知できない可能性
- 提案: 具体的な監視項目と閾値を design に明記し、アラート設計を追加する
- Evidence:
  - PATH: design/DB_DESIGN/design.V_DOCS_OBSIDIAN.md
    抜粋: "ファイル数増加に伴うパフォーマンス劣化を監視し"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.V_DOCS_OBSIDIAN.md
    変更内容: 具体的な監視項目（実行時間、ファイル数、エラー率）と閾値を追加
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

#### Med-2: frontmatter フィールド名の標準化不足
- 指摘: review_date と generated_on の使い分けルールが不明確
- 影響: Agent が日付情報を正しく抽出できないケースが発生する可能性
- 提案: frontmatter フィールド名の標準化ルールを README に追加
- Evidence:
  - PATH: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
    抜粋: "review_date"、"generated_on"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: README_DB_DESIGN.md
    変更内容: frontmatter フィールド名の使い分けルールを追加
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

### Low
#### Low-1: SQL コメントの不足
- 指摘: V_DOCS_OBSIDIAN のSQL内に複雑な正規表現の説明コメントがない
- 影響: メンテナンス時の理解が困難
- 提案: 各正規表現パターンに説明コメントを追加
- Evidence:
  - PATH: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
    抜粋: "REGEXP_SUBSTR( PATH, 'master/columns/([^.]+)\\\\\\\\.' ..."
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
    変更内容: SQL内の各正規表現に説明コメントを追加
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

## 5. 改善提案（次アクション）
- 実施内容: V_DOCS_OBSIDIAN ビューのメタデータ整合性確保と正規表現の簡素化
  期待効果: Agent/Search の安定性向上と保守性の改善
  優先度: High
  変更対象PATH（案）: master/views/DB_DESIGN.V_DOCS_OBSIDIAN.md
  影響範囲: 中
  実装難易度: 低
  推奨実施時期: 即時
