
# テーブル設計：PROFILE_RESULTS

## 概要
[[DB_DESIGN.PROFILE_RESULTS]] は、データベーステーブルの各カラムに対して算出されたプロファイル計測結果を保持するテーブルである。  
1行が「1回のプロファイル実行（run）」における「1カラム分の計測結果」を表し、  
[[DB_DESIGN.PROFILE_RUNS.RUN_ID]] を起点として、対象テーブル・対象カラム・計測時点・計測結果を紐づける。

本テーブルは、プロファイル処理の結果を永続化し、品質確認・比較・監査・設計レビューの根拠として利用される。

## 業務上の意味
- このテーブルが表す概念  
  - 「プロファイル結果（column-level metrics）」の蓄積。
  - 1行は、ある run における、ある 1カラムの計測結果を表す。
  - 計測対象は  
    [[DB_DESIGN.PROFILE_RESULTS.TARGET_DB]] /  
    [[DB_DESIGN.PROFILE_RESULTS.TARGET_SCHEMA]] /  
    [[DB_DESIGN.PROFILE_RESULTS.TARGET_TABLE]] /  
    [[DB_DESIGN.PROFILE_RESULTS.TARGET_COLUMN]]  
    により特定される。
- 主な利用シーン  
  - データ品質確認、設計レビュー、過去比較、異常検知の根拠データ

## 関連テーブル・プロシージャとの関係

### PROFILE_RUNS との関係
[[DB_DESIGN.PROFILE_RUNS]] はプロファイル実行単位（run）の管理テーブルであり、  
PROFILE_RESULTS はその run に紐づく結果詳細を保持する。

- 関係性  
  [[DB_DESIGN.PROFILE_RUNS]]（1） → [[DB_DESIGN.PROFILE_RESULTS]]（N）
- 関連キー  
  - [[DB_DESIGN.PROFILE_RESULTS.RUN_ID]]  
    → [[DB_DESIGN.PROFILE_RUNS.RUN_ID]]

PROFILE_RESULTS は、必ず既存の run に紐づく結果としてのみ存在する前提とする。

### PROFILE_TABLE との関係
[[DB_DESIGN.PROFILE_TABLE]] は、**単一テーブルを対象としてプロファイル処理を実行するためのストアドプロシージャ**である。

- PROFILE_TABLE は指定された  
  TARGET_DB / TARGET_SCHEMA / TARGET_TABLE  
  に含まれる全カラムを対象にプロファイル計測を行う。
- 実行時には新たな run を生成し（PROFILE_RUNS に記録）、  
  各カラムごとの計測結果を PROFILE_RESULTS に書き込む。
- PROFILE_RESULTS は、PROFILE_TABLE による実行結果を永続化する格納先となる。

### PROFILE_COLUMN との関係
[[DB_DESIGN.PROFILE_COLUMN]] は、**単一カラムを対象に即時計測を行うためのプロシージャ**である。

- PROFILE_COLUMN は参照・計算用途を主目的とし、  
  原則として PROFILE_RESULTS への永続書き込みは行わない。
- ただし、設計上は PROFILE_COLUMN で算出されるメトリクスは  
  PROFILE_RESULTS.METRICS と同一構造・同一意味を持つことを前提とする。
- これにより、単発計測結果と永続結果を同一の解釈軸で扱える。

### PROFILE_ALL_TABLES との関係
[[DB_DESIGN.PROFILE_ALL_TABLES]] は、**複数テーブル（スキーマ単位、DB単位など）を横断してプロファイル処理を実行するオーケストレーション用プロシージャ**である。

- PROFILE_ALL_TABLES は内部で  
  [[DB_DESIGN.PROFILE_TABLE]] を複数回呼び出す構成を取る。
- 各テーブルごとに run が生成され、  
  その結果として PROFILE_RESULTS に多数のレコードが蓄積される。
- PROFILE_RESULTS は、スキーマ横断・全体横断での品質状況把握の基礎データとなる。

## データ更新ポリシー
- PROFILE_RESULTS への INSERT / UPDATE / DELETE は、以下のプロシージャ群からのみ行われる。
  - [[DB_DESIGN.PROFILE_TABLE]]
  - （間接的に）[[DB_DESIGN.PROFILE_ALL_TABLES]]
- 分析クエリ、アプリケーション、運用作業からの直接更新は行わない。
- 同一 run・同一カラムに対する再計測時は、UPSERT または再生成を前提とする。

## 設計方針

### 主キーの考え方
- 主キーは以下の複合キーとする。
  - [[DB_DESIGN.PROFILE_RESULTS.RUN_ID]]
  - [[DB_DESIGN.PROFILE_RESULTS.TARGET_COLUMN]]
- 設計理由
  - 1回の run において、同一カラムの結果は高々 1行である。
  - run が異なれば、同一カラムでも別結果として共存する必要がある。

Snowflake の PRIMARY KEY 制約は情報的な制約であり、  
実際の一意性担保はプロシージャ側の処理ロジックに依存する。

### メトリクス表現
- [[DB_DESIGN.PROFILE_RESULTS.METRICS]] は VARIANT 型とし、  
  行数、NULL 率、distinct 数、最小値・最大値などを柔軟に格納する。
- メトリクス構造は固定せず、将来拡張を許容する。

### 時点の扱い
- [[DB_DESIGN.PROFILE_RESULTS.AS_OF_AT]] は、計測対象データの論理時点を示す。
- 実行時刻や状態は run 側（PROFILE_RUNS）で管理する。

## 注意点
- NOT NULL 列  
  [[DB_DESIGN.PROFILE_RESULTS.RUN_ID]],  
  [[DB_DESIGN.PROFILE_RESULTS.TARGET_COLUMN]],  
  [[DB_DESIGN.PROFILE_RESULTS.AS_OF_AT]],  
  [[DB_DESIGN.PROFILE_RESULTS.METRICS]],  
  [[DB_DESIGN.PROFILE_RESULTS.TARGET_DB]],  
  [[DB_DESIGN.PROFILE_RESULTS.TARGET_SCHEMA]],  
  [[DB_DESIGN.PROFILE_RESULTS.TARGET_TABLE]]

## 将来拡張の余地
- メトリクス構造の高度化（分布情報、異常検知指標）
- run 情報と結果を統合的に扱うビューの整備
- 大量実行時の検索・集計効率向上

## 関連

- 関連テーブル：[[DB_DESIGN.PROFILE_RUNS]]
- 関連プロシージャ：[[DB_DESIGN.PROFILE_TABLE]], [[DB_DESIGN.PROFILE_COLUMN]], [[DB_DESIGN.PROFILE_ALL_TABLES]]

