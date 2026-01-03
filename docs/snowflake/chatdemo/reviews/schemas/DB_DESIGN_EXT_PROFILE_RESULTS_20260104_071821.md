---
type: agent_review
review_date: 2026-01-03
target: DB_DESIGN.EXT_PROFILE_RESULTS
---

# DB_DESIGN.EXT_PROFILE_RESULTS 設計レビュー

## 0. メタ情報
- 対象: DB_DESIGN.EXT_PROFILE_RESULTS
- レビュー日: 2026-01-03
- 対象ノート候補（PATH一覧）:
  - README_DB_DESIGN.md
  - design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
  - design/design.DB_DESIGN.md
  - master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.AS_OF_AT.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.METRICS.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.RUN_ID.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_COLUMN.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_DB.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_SCHEMA.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_TABLE.md

## 1. サマリ（3行）
- 外部テーブルのファイル形式定義とパーティション設計に不整合があり、実運用で問題が発生する可能性が高い
- 複合主キー（RUN_ID + TARGET_COLUMN）の一意性担保策が運用レベルで明示されておらず、データ品質リスクがある
- ステージ定義の実体確認とリフレッシュ運用手順が不足しており、外部テーブルとしての基本機能に支障をきたす懸念がある

## 2. Findings（重要度別）

### High
#### High-1: ファイル形式定義の不整合
- 指摘: master定義でfile_format: JSONとなっているが、design設計書ではJSON Lines（NDJSON）形式を想定しており、実際のS3ファイル形式と不一致になる可能性が高い
- 影響: 外部テーブルからのデータ読み取り失敗、クエリエラー、ストリーミング書き込み処理との不整合
- 提案: file_formatをJSON_LINESまたはNDJSONに対応した形式に修正し、design設計書と一致させる
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "file_format: JSON"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "ファイルフォーマット：FF_JSON_LINES 1行1JSONのJSON Lines形式（NDJSON）を採用"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      file_format: JSON → file_format: JSON_LINES
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 即時

#### High-2: 外部ステージ実体の未確認
- 指摘: stage_name: OBSIDIAN_VAULT_STAGEが参照されているが、このステージの実際の定義と存在確認が行われていない
- 影響: 外部テーブル作成時の失敗、データアクセス不能、S3認証エラーの発生
- 提案: OBSIDIAN_VAULT_STAGEの定義をmaster/other配下に追加し、S3バケットとの接続確認を行う
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "stage_name: OBSIDIAN_VAULT_STAGE"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "ステージ名：[[design.OBSIDIAN_VAULT_STAGE]] S3バケット `s3://snowflake-chatdemo-vault-prod/` への外部ステージを前提とする"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/other/DB_DESIGN.OBSIDIAN_VAULT_STAGE.md
    変更内容: |
      新規作成：ステージ定義の追加
- 実装メタ情報:
  - 影響範囲: 大
  - 実装難易度: 中
  - 推奨実施時期: 即時

### Med
#### Med-1: 複合主キーの一意性運用担保策不足
- 指摘: RUN_ID + TARGET_COLUMNで複合主キーが設計されているが、外部テーブルでは制約強制されないため、重複データ検知・排除の運用手順が明示されていない
- 影響: 重複データの混入、分析結果の不正確性、データ品質問題の見逃し
- 提案: design設計書に重複検知クエリと排除手順を明記し、定期的な品質チェック運用を追加
- Evidence:
  - PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.RUN_ID.md
    抜粋: "pk: true"
  - PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_COLUMN.md
    抜粋: "pk: true"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    変更内容: 重複検知クエリと運用手順の追加
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 中
  - 推奨実施時期: 今月

#### Med-2: リフレッシュ運用手順の不明確性
- 指摘: auto_refresh: falseで手動リフレッシュ運用を採用しているが、具体的なリフレッシュタイミングと実行手順が設計書に記載されていない
- 影響: データの可視化遅延、運用担当者の判断迷い、リフレッシュ漏れによる古いデータ参照
- 提案: リフレッシュの実行タイミング（バッチ完了後等）と具体的なALTER文を設計書に明記
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "auto_refresh: false"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    変更内容: リフレッシュ運用手順の明記
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 今月

### Low
#### Low-1: パーティション設計とS3パス構造の整合性確認不足
- 指摘: partition_byでYEAR/MONTH/DAYが定義されているが、実際のS3パス構造（YEAR=YYYY/MONTH=MM/DAY=DD/）との整合性確認が設計書で明示されていない
- 影響: パーティションプルーニングの非効率化、クエリ性能の劣化、コスト増加
- 提案: S3パス命名規則とパーティション定義の対応表を設計書に追加
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "partition_by: - YEAR - MONTH - DAY"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    変更内容: パーティション対応表の追加
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

## 5. 改善提案（次アクション）
- 実施内容: master定義のfile_format修正とOBSIDIAN_VAULT_STAGEステージ定義の追加
  期待効果: 外部テーブルの基本機能確保とデータアクセス安定化
  優先度: High
  変更対象PATH（案）: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md, master/other/DB_DESIGN.OBSIDIAN_VAULT_STAGE.md
  影響範囲: 中
  実装難易度: 低
  推奨実施時期: 即時
