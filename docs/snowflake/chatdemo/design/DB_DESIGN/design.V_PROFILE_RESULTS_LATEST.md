# [[design.V_PROFILE_RESULTS_LATEST]] 設計書

## 概要

V_PROFILE_RESULTS_LATESTは、PROFILE_RUNSテーブルから最新の成功実行（STATUS='SUCCEEDED'）を特定し、その実行IDに紐づくPROFILE_RESULTS全レコードを取得するビューである。各テーブル・カラムごとに最新のプロファイル結果（メトリクス）を一覧化する。

## 業務上の意味

プロファイリングは定期的に実行されるため、同一テーブル・カラムに対して複数回の実行履歴が存在する。業務上、最新の結果のみを参照したい場合に本ビューを利用することで、古いプロファイル結果を除外し、最新のメトリクスのみを取得できる。

これにより、データ品質のモニタリング、異常検知、カラムごとの統計情報の最新状態を即座に確認可能となる。

## 設計上の位置づけ

本ビューはDB_DESIGNスキーマ内に配置され、以下の2テーブルを参照する：

- [[design.PROFILE_RUNS]]: プロファイル実行の履歴（実行ID、対象テーブル、ステータス、開始時刻等）
- [[design.PROFILE_RESULTS]]: 各実行で得られたカラムごとのプロファイル結果（メトリクスをVARIANT型で格納）

EXPORT_PROFILE_EVIDENCE_MD_VFINALプロシージャでは、本ビューを利用してObsidian Vaultに出力するプロファイルエビデンスを最新のものに限定している。

## クエリロジック

1. LATEST CTE: PROFILE_RUNSからSTATUS='SUCCEEDED'の実行を対象に、`TARGET_DB`、`TARGET_SCHEMA`、TARGET_TABLEごとにSTARTED_ATの最大値を取得
2. `LATEST_RUN` CTE: LATEST CTEの結果とPROFILE_RUNSを結合し、最新実行レコードのみを抽出
3. メインSELECT: PROFILE_RESULTSとLATEST_RUNをRUN_IDで結合し、最新実行に紐づく全カラムのプロファイル結果を返却

これにより、各テーブル・カラムごとに最新のSUCCEEDED実行のメトリクスのみが返される。

## 利用シーン

- EXPORT_PROFILE_EVIDENCE_MD_VFINALプロシージャ: 最新プロファイル結果をMarkdownエビデンスとして出力
- データ品質ダッシュボード: 最新のカラム統計情報を可視化
- 異常検知バッチ: 最新メトリクスをしきい値と比較して異常カラムを検出
- データカタログ連携: 最新のカラムプロファイルをメタデータとして外部ツールに提供

## 運用

- 本ビューは参照専用であり、INSERT/UPDATE/DELETE操作は不可
- PROFILE_RUNSおよびPROFILE_RESULTSが更新されると、自動的に最新結果を反映
- プロファイリングバッチが定期実行される限り、本ビューは常に最新状態を返す
- 実行履歴が増加してもパフォーマンス劣化を防ぐため、[[design.PROFILE_RUNS]].STARTED_ATにインデックス推奨
- 古いプロファイル履歴の削除運用を行う場合、最新以外のレコードを対象とすることで本ビューへの影響を回避可能
