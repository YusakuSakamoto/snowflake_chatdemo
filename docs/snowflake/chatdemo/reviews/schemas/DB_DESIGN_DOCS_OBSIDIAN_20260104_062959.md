---
type: agent_review
review_date: 2026-01-03
target: DB_DESIGN.DOCS_OBSIDIAN
---

# DB_DESIGN.DOCS_OBSIDIAN 設計レビュー

## 0. メタ情報
- 対象: DB_DESIGN.DOCS_OBSIDIAN
- レビュー日: 2026-01-03
- 対象ノート候補（PATH一覧）:
  - README_DB_DESIGN.md
  - design/DB_DESIGN/design.DOCS_OBSIDIAN.md
  - design/design.DB_DESIGN.md
  - master/tables/DB_DESIGN.DOCS_OBSIDIAN.md

## 1. サマリ（3行）
- master定義に列定義が完全欠落しており、設計意図とmaster定義の乖離が深刻な状態である
- design文書では8個のカラムが詳細に定義されているが、masterでは全く反映されていない
- 設計レビューの基盤テーブルでありながら、SSOT（Single Source of Truth）原則に反している

## 2. Findings（重要度別）

### Critical
#### Critical-1: master定義の列定義完全欠落
- 指摘: master/tables/DB_DESIGN.DOCS_OBSIDIAN.md にfrontmatterのみが存在し、テーブル本文やカラム定義が一切記載されていない
- 影響: DDL生成対象であるmaster定義が不完全なため、実テーブル作成・更新時に設計意図が反映されない重大リスク
- 提案: design文書で定義された全8カラム（DOC_ID, PATH, FOLDER, CONTENT, FILE_LAST_MODIFIED, INGESTED_AT, OBJECT_ID, OBJECT_TYPE）をmaster定義に追加
- Evidence:
  - PATH: master/tables/DB_DESIGN.DOCS_OBSIDIAN.md
    抜粋: "# DOCS_OBSIDIAN"
  - PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    抜粋: "[[DB_DESIGN.DOCS_OBSIDIAN.DOC_ID]] は [[design.DOCS_OBSIDIAN]] における論理的な主キーであり、1ファイルを一意に識別する。"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/tables/DB_DESIGN.DOCS_OBSIDIAN.md
    変更内容: |
      frontmatter以下にカラム定義セクション追加
      各カラムのdomain, nullable, pk, comment属性を明記
- 実装メタ情報:
  - 影響範囲: 大
  - 実装難易度: 中
  - 推奨実施時期: 即時

#### Critical-2: SSOT原則違反による設計情報の分散
- 指摘: 設計の正本であるべきmaster定義が不完全な状態で、実質的な定義情報がdesign文書にのみ存在している
- 影響: README_DB_DESIGN.mdで宣言されたSSot原則に反し、定義の一元管理が破綻している
- 提案: master定義を設計の正本として完全化し、design文書は設計意図・背景のみに特化させる
- Evidence:
  - PATH: README_DB_DESIGN.md
    抜粋: "定義の変更は master のみで行い、設計判断は design に残す"
  - PATH: design/design.DB_DESIGN.md
    抜粋: "master/ | 機械可読な定義の正本（DDL生成対象）"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/tables/DB_DESIGN.DOCS_OBSIDIAN.md
    変更内容: |
      完全なテーブル定義追加
      design文書から定義情報を移動・統合
- 実装メタ情報:
  - 影響範囲: 大
  - 実装難易度: 高
  - 推奨実施時期: 即時

### High
#### High-1: カラム個別定義ファイルの不在
- 指摘: design文書で言及された8個のカラムに対応するmaster/columns/配下の個別定義ファイルが存在しない
- 影響: 列レベルの詳細設計（domain, nullable, pk）が正規化されておらず、横断的なカラム設計チェックが困難
- 提案: master/columns/DB_DESIGN.DOCS_OBSIDIAN.*.md形式で各カラムの個別定義を作成
- Evidence:
  - PATH: README_DB_DESIGN.md
    抜粋: "column: master/columns/<SCHEMA>.<TABLE>.<COLUMN>.md"
  - PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    抜粋: "[[DB_DESIGN.DOCS_OBSIDIAN.DOC_ID]]", "[[DB_DESIGN.DOCS_OBSIDIAN.PATH]]"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/
    変更内容: |
      8個のカラム定義ファイル作成
      各カラムのcolumn_id, table_id, domain, is_nullable, pk属性定義
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 中
  - 推奨実施時期: 今週

### Med
#### Med-1: 主キー設計の運用担保方針不明確
- 指摘: design文書でDOC_IDが主キーと述べられているが、Snowflake非enforced前提での一意性担保方法が不明確
- 影響: 重複レコード発生時の検知・対処方針が不明で、データ品質リスクが存在
- 提案: INGEST_VAULT_MD プロシージャでの一意性担保ロジックと検証クエリの明文化
- Evidence:
  - PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    抜粋: "実際の一意性担保は [[DB_DESIGN.INGEST_VAULT_MD]] の処理ロジックに依存する。"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    変更内容: 運用時の一意性検証クエリと重複対処手順を明記
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

## 3. 追加で集めたい情報
- 追加調査: master/columns/配下のカラム定義ファイルの有無確認
- 追加ツール実行案: list_table_related_doc_paths でINCLUDE_COLUMNS="true"を指定し、カラム定義の存在確認

## 4. 改善提案（次アクション）
- 実施内容: master定義の完全化（カラム定義追加）とカラム個別ファイル作成
  期待効果: SSOT原則の遵守とDDL生成基盤の安定化
  優先度: Critical
  変更対象PATH（案）: master/tables/DB_DESIGN.DOCS_OBSIDIAN.md, master/columns/DB_DESIGN.DOCS_OBSIDIAN.*.md
  影響範囲: 大
  実装難易度: 中
  推奨実施時期: 即時
