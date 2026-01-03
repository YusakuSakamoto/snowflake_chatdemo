---
type: agent_review
review_date: 2026-01-03
target: DB_DESIGN.EXT_PROFILE_RESULTS
---

# EXT_PROFILE_RESULTS 設計レビュー

## 0. メタ情報
- 対象: DB_DESIGN.EXT_PROFILE_RESULTS
- レビュー日: 2026-01-03
- 対象ノート候補（PATH一覧）:
  - README_DB_DESIGN.md
  - design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
  - design/design.DB_DESIGN.md
  - master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md

## 1. サマリ（3行）
- master定義にカラム仕様が全く存在せず、外部テーブルとして実装不能な状態
- file_formatやstage設定において、master定義とdesign文書間で不整合が発生
- 設計文書は非常に詳細だが、master定義が最小限すぎて実装とのギャップが大きい

## 2. Findings（重要度別）

### Critical
#### Critical-1: カラム定義の完全欠如
- 指摘: master定義にカラム仕様が全く存在しない
- 影響: DDL生成・実装が不可能、外部テーブルとして機能しない
- 提案: 最低限RUN_ID、TARGET_COLUMN、METRICS等の必須カラム定義を追加
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "type: externaltable...comment: プロファイル処理により算出されたカラム単位の計測結果を保持する外部テーブル"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "[[DB_DESIGN.PROFILE_RESULTS.RUN_ID]] と [[DB_DESIGN.PROFILE_RESULTS.TARGET_COLUMN]] の複合キーにより、1run・1カラムあたり1行を前提とする"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      カラム定義セクション追加
      - RUN_ID (VARCHAR): 実行ID
      - TARGET_COLUMN (VARCHAR): 対象カラム
      - METRICS (VARIANT): 計測結果
- 実装メタ情報:
  - 影響範囲: 大
  - 実装難易度: 中
  - 推奨実施時期: 即時

### High
#### High-1: ファイルフォーマット設定の不整合
- 指摘: master定義では"JSON"だが、design文書では"FF_JSON_LINES"について言及
- 影響: 外部テーブル作成時のフォーマット指定で実装エラーのリスク
- 提案: 設計意図に合わせてfile_formatをFF_JSON_LINESに統一
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "file_format: JSON"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "ファイルフォーマット：FF_JSON_LINES 1行1JSONのJSON Lines形式（NDJSON）を採用"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      file_format: FF_JSON_LINES
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 即時

### Med
#### Med-1: ステージ設定の詳細度不足
- 指摘: stage_locationが"profile_results/"と簡素すぎる
- 影響: 設計意図したパーティション構造との齟齬の可能性
- 提案: パーティション構造を考慮したstage_location設定の詳細化
- Evidence:
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "S3パス構造: s3://snowflake-chatdemo-vault-prod/profile_results/YEAR=YYYY/MONTH=MM/DAY=DD/"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: stage_locationの詳細化とパーティション構造の明示
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 今週

## 3. 追加で集めたい情報
- 追加調査: 内部テーブル版PROFILE_RESULTSのカラム定義参照
- 追加ツール実行案: list_table_related_doc_paths + get_docs_by_paths で内部テーブル版の仕様確認

## 4. 改善提案（次アクション）
- 実施内容: master定義へのカラム仕様追加とファイルフォーマット統一
  期待効果: 実装可能な外部テーブル定義の完成
  優先度: Critical
  変更対象PATH（案）: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
  影響範囲: 大
  実装難易度: 中
  推奨実施時期: 即時
