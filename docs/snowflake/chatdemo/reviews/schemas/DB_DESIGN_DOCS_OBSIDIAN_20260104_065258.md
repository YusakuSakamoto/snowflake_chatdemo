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
  - master/columns/DB_DESIGN.DOCS_OBSIDIAN.CONTENT.md
  - master/columns/DB_DESIGN.DOCS_OBSIDIAN.DOC_ID.md
  - master/columns/DB_DESIGN.DOCS_OBSIDIAN.FILE_LAST_MODIFIED.md
  - master/columns/DB_DESIGN.DOCS_OBSIDIAN.FOLDER.md
  - master/columns/DB_DESIGN.DOCS_OBSIDIAN.INGESTED_AT.md
  - master/columns/DB_DESIGN.DOCS_OBSIDIAN.OBJECT_ID.md
  - master/columns/DB_DESIGN.DOCS_OBSIDIAN.OBJECT_TYPE.md
  - master/columns/DB_DESIGN.DOCS_OBSIDIAN.PATH.md
  - master/tables/DB_DESIGN.DOCS_OBSIDIAN.md

## 1. サマリ（3行）
- DB_DESIGN.DOCS_OBSIDIAN テーブルは Obsidian Vault の Markdown ファイルを1ファイル=1レコードで格納する設計として定義され、Agent プロシージャとの連携を前提とした包括的な設計意図が明確に記述されている。
- 主要な課題として、DOC_ID の domain 定義でハッシュ値想定にも関わらず VARCHAR の制約長未指定、INGESTED_AT のデフォルト値設定に関する運用面での課題が確認された。
- 全体として設計意図とmaster定義は整合しているが、型仕様やデフォルト値の運用面で改善余地がある。

## 2. Findings（重要度別）

### High
#### High-1: DOC_ID のdomain定義でVARCHAR制約長未指定
- 指摘: DOC_ID は主キーとしてハッシュ値を想定しているが、domain が VARCHAR で制約長が未指定
- 影響: ハッシュ値（MD5想定）なら32文字固定のはずだが、可変長のため予期しないパフォーマンス劣化や格納不整合のリスクがある
- 提案: ハッシュアルゴリズムを明確にし、VARCHAR(32) または VARCHAR(64) など固定長を明示する
- Evidence:
  - PATH: master/columns/DB_DESIGN.DOCS_OBSIDIAN.DOC_ID.md
    抜粋: "domain: VARCHAR"
  - PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    抜粋: "DOC_ID は design.DOCS_OBSIDIAN における論理的な主キーであり、1ファイルを一意に識別する"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/DB_DESIGN.DOCS_OBSIDIAN.DOC_ID.md
    変更内容: |
      domain: VARCHAR(32)  # または VARCHAR(64)、使用するハッシュアルゴリズムに応じて
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 低
  - 推奨実施時期: 今週

#### High-2: INGESTED_AT のdefault値運用とINGEST処理の整合性
- 指摘: INGESTED_AT に CURRENT_TIMESTAMP() がdefaultとして設定されているが、設計書では INGEST_VAULT_MD プロシージャが唯一の書き込み経路と明示されている
- 影響: プロシージャ外からの直接INSERT時にdefault値が適用され、取り込み元の追跡ができなくなる可能性がある
- 提案: プロシージャ経由の取り込みを前提とするなら、default を削除するか、専用のdefault値（例：'1900-01-01'）で異常検知できるようにする
- Evidence:
  - PATH: master/columns/DB_DESIGN.DOCS_OBSIDIAN.INGESTED_AT.md
    抜粋: "default: CURRENT_TIMESTAMP()"
  - PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    抜粋: "DB_DESIGN.DOCS_OBSIDIAN への INSERT / UPDATE / DELETE は DB_DESIGN.INGEST_VAULT_MD のみが行う"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: master/columns/DB_DESIGN.DOCS_OBSIDIAN.INGESTED_AT.md
    変更内容: |
      default:  # プロシージャ経由のみを前提とするためdefaultを削除
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 低
  - 推奨実施時期: 今週

### Med
#### Med-1: nullable設計でOBJECT_ID/OBJECT_TYPEが片方だけNULL許容
- 指摘: OBJECT_ID と OBJECT_TYPE は設計上セットで扱われるべきだが、両方とも NULL 許容で片方だけに値が入る可能性がある
- 影響: データ品質の観点で不完全な関連付けが発生し、Agent による設計オブジェクト探索の精度が低下する
- 提案: 両方NULL または両方非NULL のバリデーション運用ルールを設計書に明記する
- Evidence:
  - PATH: master/columns/DB_DESIGN.DOCS_OBSIDIAN.OBJECT_ID.md
    抜粋: "is_nullable: true"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    変更内容: OBJECT_ID と OBJECT_TYPE の関連バリデーション運用ルールを追記
- 実装メタ情報:
  - 影響範囲: 小
  - 実装難易度: 中
  - 推奨実施時期: 今月

#### Med-2: ファイル更新時刻とSnowflake取り込み時刻の運用監視設計
- 指摘: FILE_LAST_MODIFIED と INGESTED_AT の2つの時刻が存在するが、遅延監視やデータ鮮度管理の運用方針が明示されていない
- 影響: Vault の変更が Snowflake に反映されるまでの遅延を検知できず、設計レビューの品質が低下する可能性がある
- 提案: 遅延監視クエリやアラート設計を設計書に明記し、運用方針を明確化する
- Evidence:
  - PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    抜粋: "FILE_LAST_MODIFIED は Vault 側の更新時刻、INGESTED_AT は Snowflake への取り込み時刻を示し、両者を区別して扱う"
- Vault差分案（AIは編集しない）:
  - 変更対象PATH: design/DB_DESIGN/design.DOCS_OBSIDIAN.md
    変更内容: 遅延監視・データ鮮度管理の運用方針を追記
- 実装メタ情報:
  - 影響範囲: 中
  - 実装難易度: 中
  - 推奨実施時期: 今月

## 3. 改善提案（次アクション）
- 実施内容: DOC_ID の VARCHAR 制約長を明示し、INGESTED_AT のdefault値運用方針を整理する
  期待効果: 主キーの性能安定化と取り込み経路の追跡性向上
  優先度: High
  変更対象PATH（案）: master/columns/DB_DESIGN.DOCS_OBSIDIAN.DOC_ID.md, master/columns/DB_DESIGN.DOCS_OBSIDIAN.INGESTED_AT.md
  影響範囲: 小
  実装難易度: 低
  推奨実施時期: 今週
