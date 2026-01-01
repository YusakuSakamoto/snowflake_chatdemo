# [[design.EXPAND_DEPARTMENT_SCOPE_TOOL]] 設計書

## 概要

EXPAND_DEPARTMENT_SCOPE_TOOLは、指定された部署IDから配下組織のIDリストを展開するツールプロシージャである。部署階層（本部→部→課→グループ）を考慮し、指定された部署カテゴリに応じて配下の全部署IDを取得する。部レベルの売上を課/グループレベルで正しく集計する際に必須となる。

## 業務上の意味

部署階層を持つ組織では、「デジタルイノベーション部の売上」を問われた際、部に直接紐づく売上だけでなく、配下の課やグループの売上も含めて集計する必要がある。しかし、データベース上では案件やオーダーが直接「部」に紐づくのではなく、実際には「課」や「グループ」に紐づいているケースが多い。本ツールは、指定された部署IDから配下の全部署IDを展開することで、正しい集計範囲を確定する。

## 設計上の位置づけ

EXPAND_DEPARTMENT_SCOPE_TOOLはAPP_PRODUCTIONスキーマに配置され、以下のオブジェクトと連携する。

- [[design.DEPARTMENT_MASTER]]: 部署マスタテーブル（年度別の部署階層情報を保持）
- [[design.SNOWFLAKE_DEMO_AGENT]]: 本ツールをexpand_department_scopeツールとして登録し、部署名解決後に自動的に呼び出してスコープ展開を実行

本ツールは、年度と部署IDを受け取り、部署カテゴリ（本部/部/課/グループ）に応じて配下の部署IDリストを返却する。include_selfパラメータにより、指定部署自身をスコープに含めるかどうかを制御できる。

## 機能

1. JSON形式のペイロード受け取り
   - payload_json (STRING): JSON形式のツール引数
   - fiscal_year、department_id、include_self、max_nodesを抽出

2. 年度・部署IDのバリデーション
   - fiscal_yearが未指定の場合: DEPARTMENT_MASTERから最新年度を取得
   - department_idが未指定の場合: エラー返却

3. 部署IDの名称解決
   - 論理的なDEPARTMENT_IDで検索
   - 見つからない場合は物理的なIDカラムで検索し、DEPARTMENT_IDにマッピング

4. 部署カテゴリに応じたスコープ展開
   - グループ: 自身のみ（配下組織なし）
   - 課: DEPARTMENT_SECTION_CODEで配下のグループを検索
   - 部: DIVISION_CODEで配下の課/グループを検索
   - 本部: HEADQUARTERS_CODEで配下の部/課/グループを検索

5. include_selfによるフィルタ制御
   - include_self="Y": 指定部署自身を含む全カテゴリを返却
   - include_self="N": 指定部署より下位のカテゴリのみを返却

6. 結果の返却
   - resolved: 指定部署の詳細情報
   - scope.department_ids: 配下部署IDのリスト
   - scope.members: 配下部署の詳細情報リスト

## パラメータ

- payload_json (STRING): JSON形式のツール引数（必須）
  - fiscal_year (STRING): 年度（任意、未指定の場合は最新年度を使用）
  - department_id (STRING): 部署ID（必須、論理的なDEPARTMENT_ID）
  - include_self (STRING): 自部署を含むか（任意、"Y"/"N"、デフォルト"N"）
  - max_nodes (STRING): 最大ノード数（任意、デフォルト"500"）

## 利用シーン

- 部署階層を考慮した売上集計: 「デジタルイノベーション部の売上」を問われた際、配下の課/グループの売上を含めて集計
- 年度別の組織変更対応: 組織改編により部署階層が変更された場合でも、年度ごとの正しい階層情報を使用
- 配下組織の列挙: 特定部署の配下にどの課/グループが存在するかをリスト化
- IN句の生成: Semantic Modelへのクエリ生成時に、department_id IN (...)の形式で配下部署IDをフィルタ条件として渡す
- include_selfによる柔軟な集計: 自部署を含めるか除外するかをユーザーの質問意図に応じて制御
- 組織分析: 本部レベルでの全配下部署の一覧取得や、部署数のカウント
