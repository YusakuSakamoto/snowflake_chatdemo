# [[SNOWFLAKE_DEMO_AGENT]] 設計書

## 概要

SNOWFLAKE_DEMO_AGENTは、Snowflakeデモ用のCortex Agentであり、部署・顧客・案件・オーダーの名称解決から部署スコープ展開、集計処理までを決定論的に実行する。LLMによる推測や文字列探索（LIKE/ILIKE）を使用せず、ツールを用いた確定的な名称解決を実現している。

## 業務上の意味

ユーザーが自然言語で「デジタルイノベーション部の売上を教えて」といった質問をした際、従来のテキスト検索では表記揺れや曖昧性によって誤った結果を返す可能性がある。本エージェントは、まずresolve_entity_aliasツールで名称を決定論的に解決し、さらに部署の場合はexpand_department_scopeで配下組織のスコープを展開することで、正確な集計範囲を確定する。

当社の会計年度ルール（7月1日〜翌年6月30日）や、「売上見込み」と「売上実績」の区別にも対応し、ユーザーの質問意図に応じて正しい期間条件を生成する。

## 設計上の位置づけ

本エージェントはAPP_PRODUCTIONスキーマに配置され、以下のツールと連携する。

- resolve_entity_alias: 名称を決定論的に解決（候補が複数ある場合はユーザーに選択を促す）
- expand_department_scope: 部署の配下組織IDを展開（部レベルの売上を課/グループレベルで集計する際に必須）
- text_to_sql: 確定した条件をもとにSemantic ModelからSQL生成

名称解決の結果（entity_id、entity_type）は直接SQLに使用せず、必ずSemantic Model上の列名（[[CUSTOMER_ID]]、[[ORDER_NUMBER]]、[[PROJECT_NUMBER]]、DEPARTMENT_ID等）へマッピングしてtext_to_sqlに渡す設計となっている。

## 機能

1. 固有名詞の抽出と名称解決
   - ユーザー質問から部署/顧客/案件/オーダーの候補語を抽出
   - resolve_entity_aliasツールを用いて決定論的に解決
   - 候補が複数ある場合はユーザーに選択を促す（next="disambiguate"）

2. 部署スコープの展開
   - 名称解決の結果がdepartmentタイプの場合、expand_department_scopeを必ず実行
   - 部レベルの指定でも配下の課/グループIDを取得し、売上を正しく集計

3. 集計期間の自動判定
   - 「売上見込み」「見込み売上」「年度売上」の場合: 当年度の期末（6月30日）まで（CURRENT_DATEで打ち切らない）
   - 「売上実績」「今まで」「現在まで」「YTD」の場合: 当年度のCURRENT_DATEまで

4. Semantic Modelへのマッピング
   - resolve_entity_aliasが返すentity_idは名称辞書上の共通キーであり、列名ではない
   - entity_typeに応じて正しい列名へマッピング（customer→CUSTOMERS.[[CUSTOMER_ID]]、order→ORDERS.[[ORDER_NUMBER]]、project→PROJECTS.[[PROJECT_NUMBER]]、department→PROJECTS.[[DEPARTMENT_ID]] IN (...)）

## パラメータ

本エージェントはユーザーからの自然言語質問を受け取り、以下のツールに対してJSON形式のパラメータを渡す。

resolve_entity_aliasへのパラメータ（payload_json）:
- term: 固有名詞候補（必須）
- max_candidates: 候補上限（必須、通常"8"）
- entity_type_hint: タイプヒント（任意、確信がある場合のみ'department'/'customer'/'project'/'order'）

expand_department_scopeへのパラメータ:
- fiscal_year: 年度（必須、ユーザー指定または最新年度）
- department_id: 部署ID（必須、resolve_entity_aliasの結果）
- include_self: 自部署を含むか（"Y"/"N"）
- max_nodes: 最大ノード数（"500"等）

text_to_sqlへの指示:
- 見込み: 「当年度のfiscal_start（7/1）〜fiscal_end（6/30）で集計し、CURRENT_DATEで打ち切らない」
- 実績/YTD: 「当年度のfiscal_start（7/1）〜min（fiscal_end, [[CURRENT_DATE]]）で集計する」

## 利用シーン

- デモ環境での自然言語データ分析: 「デジタルイノベーション部の2025年度の売上見込みを教えて」といった質問に対し、名称解決→スコープ展開→集計を自動実行
- 部署階層を考慮した集計: 部レベルの指定でも配下の課/グループレベルのデータを正しく集計
- 年度ルールの適用: 当社独自の会計年度ルール（7月1日〜6月30日）に従った期間集計
- 顧客/案件/オーダー分析: 顧客名や案件名の表記揺れを吸収し、正しいエンティティを特定して集計
- 名称曖昧性の解消: 候補が複数ある場合はユーザーに選択肢を提示し、確定後に集計実行
