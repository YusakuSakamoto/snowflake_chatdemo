# テーブル設計：PROFILE_RUNS

## 概要
[[DB_DESIGN.PROFILE_RUNS]] は、データベーステーブルに対して実行したプロファイル処理（例：行数、列統計、欠損率などの算出）の実行履歴を管理するテーブルである。  
1行が1回のプロファイル実行（= run）を表し、対象テーブル・実行条件・実行時間・実行状態を記録することで、監視・再実行・トラブルシュート・結果テーブルとの紐付けに利用する。


## 業務上の意味
- このテーブルが表す概念
    - 「プロファイル実行ジョブ（run）」の台帳（ジョブ管理・履歴管理）。
    - runは「いつ」「どの対象（DB / Schema / Table）に」「どんな条件（サンプル率、Warehouse、Role、コードバージョン）」で実行されたか、
      および「結果が成功／失敗／実行中のどれか」を表す。
    - 各runは RUN_ID により識別され、結果テーブル（PROFILE_RESULTS）と論理的に関連付けられる。
- どの業務で使われるか
    - データ品質管理・モニタリング業務
      - 定期的なプロファイル実行の成功／失敗の監視
      - 実行時間や実行頻度の把握
    - 障害対応・調査業務
      - 失敗したプロファイル実行の原因特定（NOTE・エラー情報の参照）
      - 同一対象テーブルに対する直近・過去の実行履歴の確認
    - 再実行・運用判断
      - 過去runとの比較による再実行要否の判断
      - 最新の成功runの特定
    - プロファイル結果参照の基点
      - PROFILE_RESULTS 等の結果テーブルを参照する際の起点キーとして利用

## データ更新ポリシー
- 本テーブル（PROFILE_RUNS）および関連する結果テーブル（PROFILE_RESULTS）のデータ更新（INSERT / UPDATE / DELETE）は、
  以下のストアドプロシージャからのみ行われることを前提とする。
    - DB_DESIGN.PROFILE_TABLE
- DB_DESIGN.PROFILE_COLUMN は、単一カラムに対するプロファイル結果を即時計算して返却するための参照・計算専用プロシージャであり、
  永続テーブルへの書き込みは行わない。
- アプリケーション、分析クエリ、運用作業等からの直接的な INSERT / UPDATE / DELETE は行わない。
- データ品質および整合性は、テーブル制約ではなく、プロシージャ内の処理ロジック（状態遷移、再実行制御、エラーハンドリング）によって担保する。

## 設計方針
- 主キーの選定理由
    - RUN_ID は1回のプロファイル実行を識別するためのサロゲートキーとする。
    - 同一テーブル・同一条件であっても、実行時刻やコードバージョンが異なる複数runが存在し得るため、自然キーではなくサロゲートキーを採用する。
    - RUN_ID はプロシージャ内で UUID 等により生成され、衝突が起きない前提で運用する。
- Snowflake 前提の考慮点
    - SnowflakeではPKやCHECK制約によるデータ排除が限定的であるため、データ整合性はDDL制約ではなく、プロシージャ内のロジックと運用ルールで担保する。
    - 書き込み処理は冪等（MERGE）とし、再実行や部分失敗時でも履歴が破綻しない設計とする。
    - 実運用で参照頻度が高い検索軸（例：TARGET_* + STARTED_AT、STATUS）を意識し、必要に応じてクラスタリング等を検討する（大量データ化した場合）。

## 注意点
- NULL可否の考え方
    - NOT NULL：runの識別や監視に必須な属性（RUN_ID / TARGET_DB / TARGET_SCHEMA / TARGET_TABLE / STARTED_AT / STATUS）
    - NULL許容：実行状況や起動経路により取得できない、または意味を持たない可能性がある属性
        - FINISHED_AT：実行中（STATUS='RUNNING'）はNULL、完了時に設定される
        - WAREHOUSE_NAME：自動選択や継承により実行時に明示されない場合がある
        - ROLE_NAME：セッションロール継承の場合はNULLとなることがある
        - GIT_COMMIT：手動実行等でコードバージョンを特定できない場合はNULL
        - NOTE：任意メモのためNULL可
    - NULL許容列については、NULLであることの意味をカラムコメントに明記する。
- 状態と時刻の整合性
    - STATUS='RUNNING' の間は FINISHED_AT はNULLであることを前提とする。
    - STATUS in ('SUCCEEDED','FAILED') の場合は FINISHED_AT が必ず設定される。
    - 状態遷移は原則として RUNNING → SUCCEEDED | FAILED のみとする。

## 将来拡張の余地
- プロファイル実行状態の拡張（例：CANCELLED / SKIPPED / TIMEOUT 等）
- 失敗理由や実行コンテキストの構造化
  - 追加候補：ERROR_CODE, ERROR_MESSAGE, TRIGGERED_BY, JOB_NAME, REQUEST_ID, UPDATED_AT
- 実行履歴増加時の検索・運用効率向上
  - 想定検索軸（TARGET_*、STARTED_AT、STATUS）に基づくクラスタリング検討
- 結果テーブル（PROFILE_RESULTS）との関係性の明確化
  - RUN_ID を軸とした 1 run : N results の関係を前提とする

## 関連


table_id:: TBL_20251226180943

```dataview
TABLE physical, domain, comment
FROM "master/columns"
WHERE table_id = this.table_id
SORT schema_id, physical
```

