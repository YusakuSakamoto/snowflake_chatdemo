# [[design.DOCS_OBSIDIAN_V]] 設計書

## 概要

DOCS_OBSIDIAN_Vは、DOCS_OBSIDIANテーブルに格納されたObsidian VaultのMarkdownファイルを解析し、Cortex SearchおよびCortex Agent向けに検索メタ情報を付与したビューである。ファイルパスやfrontmatterから、大分類（SCOPE）、詳細種別（FILE_TYPE）、対象日（RUN_DATE）、対象スキーマ・テーブル・カラム名を自動抽出する。

## 業務上の意味

Obsidian Vaultには、データベース設計のマスタ情報（master/）、設計ドキュメント（design/）、ビュー定義（views/）、テンプレート（templates/）など、複数種別のMarkdownが混在している。Cortex Agentが質問に応じて適切なドキュメントを検索・参照するためには、各ファイルの種別や対象オブジェクトを機械的に識別可能な形式で提供する必要がある。

本ビューにより、Agent実行時に「特定スキーマのマスタ情報のみ」「特定日付のプロファイルエビデンスのみ」といった絞り込み検索が可能となり、検索精度と応答速度が向上する。

## 設計上の位置づけ

本ビューはDB_DESIGNスキーマ内に配置され、DOCS_OBSIDIANテーブルを参照する。DOCS_OBSIDIANテーブルは、Ingestion PipelineによってObsidian VaultのMarkdownファイルがSnowflakeに取り込まれた状態を保持している。

本ビューはCortex SearchインデックスのベースVIEWとして利用され、Cortex Agentが自然言語クエリを受け取った際に、適切なMarkdownドキュメントを検索するための主要データソースとなる。

## クエリロジック

1. base CTE: DOCS_OBSIDIANからDOC_ID、PATH、FOLDER、CONTENT、INGESTED_ATを取得
2. parsed CTE: PATHおよびCONTENTを正規表現解析し、以下のメタ情報を抽出
   - SCOPE: PATH先頭セグメント（master/design/views/templates/other）から大分類を判定
   - FILE_TYPE: PATH詳細パターン（master/columns/、design/reviews/profiles/等）から詳細種別を判定
   - RUN_DATE: design/reviews配下の日付ディレクトリ、またはfrontmatter内のreview_date/generated_onフィールドから対象日を抽出
   - TARGET_SCHEMA: master/columnsの場合はPATHのスキーマ部分、design/reviewsの場合は日付直後のディレクトリ名から抽出
   - TARGET_TABLE: master/columnsの場合はPATHのテーブル部分、design/reviewsの場合は最終ディレクトリ名から抽出
   - TARGET_COLUMN: master/columns配下の場合のみ、PATHのカラム部分を抽出

3. メインSELECT: parsed CTEの全カラムを返却

## 利用シーン

- Cortex Search: 本ビューをベースにSearchインデックスを構築し、Agent質問時に関連ドキュメントを検索
- Cortex Agent: 検索結果を利用してコンテキストを取得し、自然言語で回答を生成
- マスタ参照API: 特定スキーマ・テーブルのマスタ情報を取得する際、SCOPE='master'およびTARGET_SCHEMA/TARGET_TABLEで絞り込み
- プロファイルエビデンス検索: RUN_DATEおよびFILE_TYPE='profile_evidence'で特定日付のプロファイル結果を抽出
- Agent Review検索: FILE_TYPE='agent_review'で過去のAgent実行レビュー結果を検索

## 運用

- 本ビューは参照専用であり、INSERT/UPDATE/DELETE操作は不可
- DOCS_OBSIDIANテーブルが更新されると、自動的に最新のMarkdownファイルを反映
- Cortex SearchインデックスはビューのUPDATED_ATを監視し、変更があれば再インデックス実行
- PATH規約が変更された場合、本ビュー内の正規表現パターンも合わせて修正が必要
- frontmatterのフィールド名（review_date、generated_on等）を変更する場合も、本ビューのREGEXP_SUBSTR部分を更新
- ファイル数増加に伴うパフォーマンス劣化を監視し、必要に応じてDOCS_OBSIDIAN.PATHにインデックスを追加
