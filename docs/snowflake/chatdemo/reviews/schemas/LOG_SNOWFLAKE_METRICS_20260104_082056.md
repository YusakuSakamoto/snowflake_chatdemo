---
type: agent_review
review_date: 2026-01-03
target: LOG.SNOWFLAKE_METRICS
---

# LOG.SNOWFLAKE_METRICS 設計レビュー

## 0. メタ情報
- 対象: LOG.SNOWFLAKE_METRICS
- レビュー日: 2026-01-03
- 対象ノート候補（PATH一覧）:
  - README_DB_DESIGN.md
  - design/LOG/design.SNOWFLAKE_METRICS.md
  - design/design.DB_DESIGN.md
  - design/design.LOG.md
  - master/columns/LOG.SNOWFLAKE_METRICS.DAY.md
  - master/columns/LOG.SNOWFLAKE_METRICS.HOUR.md
  - master/columns/LOG.SNOWFLAKE_METRICS.METADATA.md
  - master/columns/LOG.SNOWFLAKE_METRICS.METRIC_ID.md
  - master/columns/LOG.SNOWFLAKE_METRICS.METRIC_NAME.md
  - master/columns/LOG.SNOWFLAKE_METRICS.METRIC_VALUE.md
  - master/columns/LOG.SNOWFLAKE_METRICS.MONTH.md
  - master/columns/LOG.SNOWFLAKE_METRICS.QUERY_ID.md
  - master/columns/LOG.SNOWFLAKE_METRICS.TIMESTAMP.md
  - master/columns/LOG.SNOWFLAKE_METRICS.USER_NAME.md
  - master/columns/LOG.SNOWFLAKE_METRICS.WAREHOUSE_NAME.md
  - master/columns/LOG.SNOWFLAKE_METRICS.YEAR.md
  - master/externaltables/LOG.SNOWFLAKE_METRICS.md

## 1. サマリ（3行）
- SNOWFLAKE_METRICS の外部テーブル定義は基本的によく設計されている。
- 一意性担保の運用設計がやや曖昧で、PK設定不在とMETRIC_IDの位置づけに明確化が必要。
- パーティション戦略は適切だが、column定義の詳細化とセキュリティ観点での改善余地がある。

## 2. Findings（重要度別）

### High
#### High-1: 主キーによる一意性担保の設計不備
- 指摘: METRIC_ID列がpk: falseに設定されているが、design書で「論理的一意性」の主要カラムとして記述されている
- 影響: 重複データ検知の運用設計が曖昧になり、データ品質担保の方針が不明確
- 提案: METRIC_IDをpk: trueに設定するか、複合一意性（metric_id + timestamp + metric_name）を明示的に設計書に反映
- Evidence:
  - PATH: design/LOG/design.SNOWFLAKE_METRICS.md
    抜粋: "外部テーブルでは PK 制約は強制できないため、**論理的一意性**として以下を前提とする。* metric_id は「一意であるべき識別子」"
  - PATH: master/columns/LOG.SNOWFLAKE_METRICS.METRIC_ID.md
    抜粋: "pk: false"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/LOG.SNOWFLAKE_METRICS.METRIC_ID.md
    変更内容: |
      pk: true に変更するか、design書で複合キー運用を明示
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 今週

### Med
#### Med-1: パーティションカラムの説明不足
- 指摘: パーティションカラム（YEAR/MONTH/DAY/HOUR）のcommentが簡潔すぎ、S3パス由来の性質や運用前提が不明
- 影響: 運用者がパーティションプルーニングの重要性を理解せず、全スキャンクエリが発生するリスク
- 提案: コメントにS3パス由来であることとクエリ時の必須性を明記
- Evidence:
  - PATH: master/columns/LOG.SNOWFLAKE_METRICS.YEAR.md
    抜粋: "comment: パーティション:年"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/LOG.SNOWFLAKE_METRICS.YEAR.md等
    変更内容: commentに「S3パス由来、クエリ時必須指定」を追加
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

#### Med-2: METADATA列の活用ガイドライン不足
- 指摘: VARIANT型のMETADATA列の設計意図は明確だが、濫用防止の具体的ガイドラインが不足
- 影響: 主要分析軸が固定カラムからMETADATAに逃げることで、クエリ性能が悪化する可能性
- 提案: design書にMETADATA使用時の制約とガイドラインを追記
- Evidence:
  - PATH: design/LOG/design.SNOWFLAKE_METRICS.md
    抜粋: "設計判断：拡張領域として許容するが、主要分析軸は固定カラムで持つ（metadata 濫用を防ぐ）"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/LOG/design.SNOWFLAKE_METRICS.md
    変更内容: METADATAの具体的な使用制約を明記
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 中
  - 推奨実施時期: 今月

### Low
#### Low-1: USER_NAME列のプライバシー配慮の明文化不足
- 指摘: USER_NAME列の個人情報取扱いに関する注意がdesign書にあるが、master定義のcommentには反映されていない
- 影響: 開発者がプライバシーリスクに気づかず不適切な利用をする可能性
- 提案: master定義のcommentにプライバシー配慮の注意を追記
- Evidence:
  - PATH: design/LOG/design.SNOWFLAKE_METRICS.md
    抜粋: "user_name は個人特定につながり得るため、閲覧権限を最小化する"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/LOG.SNOWFLAKE_METRICS.USER_NAME.md
    変更内容: commentに「個人情報注意、権限制御必須」を追加
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

## 5. 改善提案（次アクション）
- 実施内容: METRIC_ID列の主キー設定見直しと重複検知運用の明文化
  期待効果: データ品質担保の運用設計を明確化
  優先度: High
  変更対象PATH（案）: master/columns/LOG.SNOWFLAKE_METRICS.METRIC_ID.md
  影響範囲: 中
  実装難易度: 低
  推奨実施時期: 今週
