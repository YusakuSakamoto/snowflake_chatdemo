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
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.AS_OF_AT.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.METRICS.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.RUN_ID.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_COLUMN.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_DB.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_SCHEMA.md
  - master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.TARGET_TABLE.md
  - master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md

## 1. サマリ（3行）
- EXT_PROFILE_RESULTS は外部テーブル設計として基本的に適切であり、Snowflakeの外部テーブル特性を理解した設計となっている
- カラム定義、主キー設計、パーティショニング戦略が論理的一貫性を持ち、S3連携による長期保存戦略が明確
- 一部のカラムでドメイン定義に改善余地があるものの、全体的に運用性とコスト効率を重視した設計

## 2. Findings（重要度別）

### Med
#### Med-1: file_format の詳細定義が曖昧
- 指摘: master定義で `file_format: JSON` となっているが、design書で言及されている `FF_JSON_LINES` との整合性が不明確
- 影響: DDL生成時にファイルフォーマットの指定が不正確になる可能性があり、外部テーブルの正常な機能に影響する
- 提案: file_format フィールドを `FF_JSON_LINES` に修正するか、master定義でより具体的なフォーマット指定を行う
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "file_format: JSON"
  - PATH: design/DB_DESIGN/design.EXT_PROFILE_RESULTS.md
    抜粋: "ファイルフォーマット：FF_JSON_LINES"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: |
      file_format: FF_JSON_LINES
- 実装メタ情報:
  - 影響範囲: [小]
  - 実装難易度: [低]
  - 推奨実施時期: [今週]

#### Med-2: AS_OF_ATカラムでドメイン名称の不一致
- 指摘: AS_OF_ATカラムのdomainが `TIMESTAMP_LTZ` となっているが、標準的な命名規則では型名ではなく論理的なドメイン名を使用すべき
- 影響: 他のタイムスタンプカラムとのドメイン設計で一貫性を保てず、横断的なレビューや型変更時の影響分析が困難
- 提案: domain を `timestamp` や `datetime` など、論理的なドメイン名に変更する
- Evidence:
  - PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.AS_OF_AT.md
    抜粋: "domain: TIMESTAMP_LTZ"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.AS_OF_AT.md
    変更内容: |
      domain: timestamp
- 実装メタ情報:
  - 影響範囲: [小]
  - 実装難易度: [低]
  - 推奨実施時期: [今月]

#### Med-3: VARIANTカラムでのドメイン定義の改善余地
- 指摘: METRICSカラムのdomainが単純に `VARIANT` となっているが、より具体的なドメイン名を使用することで設計意図を明確化できる
- 影響: 同種のJSON構造を持つカラム間での一貫性確保が困難で、将来的な構造変更時の影響範囲把握が不十分
- 提案: domain を `metrics_json` や `profile_data` など、用途を表すドメイン名に変更する
- Evidence:
  - PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.METRICS.md
    抜粋: "domain: VARIANT"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.METRICS.md
    変更内容: |
      domain: metrics_json
- 実装メタ情報:
  - 影響範囲: [小]
  - 実装難易度: [低]
  - 推奨実施時期: [今月]

### Low
#### Low-1: 外部テーブル特有の運用制約の明示不足
- 指摘: 外部テーブルの制約事項（INSERT/UPDATE/DELETE不可等）についての記述が設計書に含まれているが、master定義のコメントには反映されていない
- 影響: 運用者が制約を見落とし、不適切な操作を試行する可能性がある
- 提案: master定義のcommentに外部テーブル特有の制約について簡潔に追記する
- Evidence:
  - PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    抜粋: "comment: プロファイル処理により算出されたカラム単位の計測結果を保持する外部テーブル（S3直接参照）。1行が1回の実行（run）における1カラム分の結果を表し、品質確認・比較・監査・設計レビューの根拠として利用される。"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md
    変更内容: comment: プロファイル処理により算出されたカラム単位の計測結果を保持する外部テーブル（S3直接参照、読み取り専用）。1行が1回の実行（run）における1カラム分の結果を表し、品質確認・比較・監査・設計レビューの根拠として利用される。
- 実装メタ情報:
  - 影響範囲: [小]
  - 実装難易度: [低]
  - 推奨実施時期: [今月]

## 5. 改善提案（次アクション）
- 実施内容: file_formatの統一、ドメイン名称の論理化、運用制約の明示化を優先的に実施し、外部テーブル設計の一貫性を向上させる
  期待効果: DDL生成の正確性向上、横断的レビューの効率化、運用時のトラブル予防
  優先度: Med
  変更対象PATH（案）: master/externaltables/DB_DESIGN.EXT_PROFILE_RESULTS.md, master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.AS_OF_AT.md, master/columns/DB_DESIGN.EXT_PROFILE_RESULTS.METRICS.md
  影響範囲: [小]
  実装難易度: [低]
  推奨実施時期: [今週]
