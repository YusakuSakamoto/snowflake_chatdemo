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
- 外部テーブル EXT_PROFILE_RESULTS は設計思想・パーティション戦略・カラム定義において概ね良好な設計となっている
- 複合主キー（RUN_ID + TARGET_COLUMN）の設計は論理的に妥当だが、外部テーブルでの一意性担保方法が不明確
- ファイルフォーマット指定で「JSON」と「JSON Lines」の表記不一致があり、設定の曖昧さがある

## 2. Findings（重要度別）

### High
#### High-1: ファイルフォーマット指定の不一致
- 指摘: master定義では `file_format: JSON` だが、design文書では「JSON Lines形式（NDJSON）」と記述され、実際の期待フォーマットが不明確
- 影響: 実際のS3ファイル形式とSnowflake外部テーブル定義の不整合により、データ読み取りエラーやパフォーマンス劣化が発生するリスク
- 提案: `file_format` を具体的な名前（例：FF_JSON_LINES）に修正し、design側の記述と一致させる
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "file_format: JSON"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "1行1JSONのJSON Lines形式（NDJSON）を採用し"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      file_format: FF_JSON_LINES
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 即時

### Med
#### Med-1: 複合主キー設定の運用担保方針未明示
- 指摘: RUN_ID + TARGET_COLUMN の複合主キーが定義されているが、外部テーブルでは制約が強制されないため、重複データの検知・排除方針が不明確
- 影響: データ品質問題が発生した際の検知遅延や、下流処理での予期しない重複による計算誤差
- 提案: design文書に重複検知クエリの例と運用手順を明記する
- Evidence:
  - PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.RUN_ID.md
    抜粋: "pk: true"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    変更内容: |
      ## 重複検知・品質担保
      以下のクエリで定期的に一意性を確認：
      SELECT RUN_ID, TARGET_COLUMN, COUNT(*) 
      FROM DB_DESIGN.EXT_PROFILE_RESULTS 
      GROUP BY 1,2 HAVING COUNT(*) > 1;
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 今月

#### Med-2: logical フィールド未設定による可読性低下
- 指摘: 外部テーブル定義にlogicalフィールドが設定されておらず、business friendlyな表記がない
- 影響: Dataviewでの一覧表示や横断チェック時に、物理名のみでは用途が分かりにくい
- 提案: logical フィールドを追加（例：「プロファイル結果（外部）」）
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "physical: EXT_PROFILE_RESULTS"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: logical: プロファイル結果（外部）
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今月

### Low
#### Low-1: domain値の統一性向上
- 指摘: AS_OF_ATでdomain: TIMESTAMP_LTZと型名が直接使われているが、他カラムのVARCHAR等と表記が統一されていない
- 影響: domain分類の一貫性が欠け、横断的な型管理が困難
- 提案: 全カラムでdomain値を統一的なルール（型名またはビジネス概念名）に揃える
- Evidence:
  - PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.AS_OF_AT.md
    抜粋: "domain: TIMESTAMP_LTZ"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.AS_OF_AT.md
    変更内容: domain: timestamp
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: Q1

## 5. 改善提案（次アクション）
- 実施内容: ファイルフォーマット定義の統一とlogicalフィールド追加により、設定の明確化と可読性向上を図る
  期待効果: 外部テーブル定義の曖昧さ解消と運用時のトラブル予防
  優先度: High
  変更対象PATH（案）: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
  影響範囲: 小
  実装難易度: 低
  推奨実施時期: 即時
