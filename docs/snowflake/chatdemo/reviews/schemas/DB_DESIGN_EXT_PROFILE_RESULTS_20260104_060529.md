---
type: agent_review
review_date: 2026-01-03
target: EXT_PROFILE_RESULTS
---

# EXT_PROFILE_RESULTS 設計レビュー

## 0. メタ情報
- 対象: EXT_PROFILE_RESULTS
- レビュー日: 2026-01-03
- 対象ノート候補（PATH一覧）:
  - README_DB_DESIGN.md
  - design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
  - design/design.DB_DESIGN.md
  - master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md

## 1. サマリ（3行）
- master定義は最小限のメタデータのみで列定義が完全に不在のため、DDL生成や運用に支障が生じる可能性が高い。
- 設計意図は詳細に記述されているが、物理的な実装ルール（ステージ設計、ファイルフォーマット仕様）との整合性に不一致がある。
- パーティショニング戦略とS3統合設計は適切だが、運用上の制約事項（外部テーブルの制限）に対する対応策が不十分。

## 2. Findings（重要度別）

### Critical

#### Critical-1: 列定義の完全不足
- 指摘: master定義にカラム仕様が一切存在せず、外部テーブルとして最低限必要な列構造が不明
- 影響: DDL生成不能、データ取り込み処理の設計不整合、運用時の参照エラー発生リスク
- 提案: 設計書に記述された論理構造（RUN_ID、TARGET_DB、TARGET_SCHEMA等）をmaster列定義として正式化する
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "physical: EXT_PROFILE_RESULTS"（frontmatterのみで本文に列仕様なし）
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "[[DB_DESIGN.PROFILE_RESULTS.RUN_ID]] と [[DB_DESIGN.PROFILE_RESULTS.TARGET_COLUMN]] の複合キーにより、1run・1カラムあたり1行を前提とする"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      frontmatter下に本文として列定義セクションを追加
      （RUN_ID、TARGET_DB、TARGET_SCHEMA、TARGET_TABLE、TARGET_COLUMN、METRICS等）
- 実装メタ情報:
  - 影響範囲: 大
  - 実装難易度: 中
  - 推奨実施時期: 即時

### High

#### High-1: ファイルフォーマット定義の不整合
- 指摘: master定義では「JSON」、設計書では「FF_JSON_LINES（JSON Lines/NDJSON）」と異なる形式が記載されている
- 影響: 実際のS3ファイル形式とSnowflake外部テーブル定義の不一致により、データ読み取りエラーが発生する可能性
- 提案: 設計意図に合わせてmaster定義を「FF_JSON_LINES」に統一し、JSON Lines形式での運用を明確化する
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "file_format: JSON"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "ファイルフォーマット：FF_JSON_LINES 1行1JSONのJSON Lines形式（NDJSON）を採用し、ストリーミング書き込みと部分読み取りの効率化を図る"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      file_format: FF_JSON_LINES
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 即時

### Med

#### Med-1: ステージ名の相対性と明示不足
- 指摘: stage_nameがstage定義ファイルとの連携前提だが、stage_locationが相対パスのため、完全なS3パス構造が不明瞭
- 影響: 運用者がS3配置を誤解し、パーティション効果の阻害やコスト増加につながるリスク
- 提案: stage定義の明示的参照または、設計書のS3パス例をより具体的に記述する
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "stage_name: OBSIDIAN_VAULT_STAGE stage_location: profile_results/"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      コメント欄にS3完全パスの例を追記
      （例: s3://snowflake-chatdemo-vault-prod/profile_results/YEAR=YYYY/MONTH=MM/DAY=DD/）
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

#### Med-2: 外部テーブル制約の運用担保策不足
- 指摘: 設計書では制約強制の運用代替手段に言及しているが、具体的な検証クエリや監視項目が未定義
- 影響: データ品質問題の早期発見ができず、下流処理に不正データが伝播するリスク
- 提案: 重複検知クエリ、NULL混入チェック、パーティション整合性監視の具体案を設計書に追記する
- Evidence:
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "データ品質は書き込み側のプロセス（プロシージャ、外部アプリケーション）で担保する必要がある"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    変更内容: 運用監視セクションに具体的な検証クエリ例を追加
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 中
  - 推奨実施時期: 今月

### Low

#### Low-1: コメント記述の冗長性
- 指摘: master定義のコメントが長文で、frontmatterとして扱うには冗長すぎる
- 影響: DDL生成時のコメント部分が可読性を損なう可能性
- 提案: 1行程度の簡潔なコメントに短縮し、詳細は設計書側で管理する
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "comment: プロファイル処理により算出されたカラム単位の計測結果を保持する外部テーブル（S3直接参照）。1行が1回の実行（run）における1カラム分の結果を表し、品質確認・比較・監査・設計レビューの根拠として利用される。"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: comment: プロファイル実行結果の外部テーブル（S3直接参照）
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

## 3. 追加で集めたい情報

- 追加調査: 内部テーブル版（PROFILE_RESULTS）の列定義を確認し、外部テーブル版の列構造設計の参考とする
- 追加ツール実行案:
  - list_table_related_doc_paths でPROFILE_RESULTSの列情報取得
  - get_docs_by_paths でOBSIDIAN_VAULT_STAGEの定義確認

## 4. 改善提案（次アクション）

- 実施内容: master定義への列仕様追加とファイルフォーマット統一
  期待効果: DDL生成可能化とS3データ読み取りの安定性向上
  優先度: Critical
  変更対象PATH（案）: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
  影響範囲: 大
  実装難易度: 中
  推奨実施時期: 即時
