# RESOLVE_ENTITY_ALIAS 設計書

## 概要

RESOLVE_ENTITY_ALIASは、ユーザーが入力した固有名詞（顧客名、部署名、案件名、オーダー名等）をエンティティIDに決定論的に解決するストアドプロシージャである。曖昧なLIKE検索やLLM推測に頼らず、正規化テーブル（DIM_ENTITY_ALIAS）を用いた段階的検索により、確定的または候補提示のいずれかを返却する。

## 業務上の意味

自然言語データ分析では、ユーザーが「デジタルイノベーション部の売上を教えて」といった形で固有名詞を含む質問を投げる。従来のLIKE検索では表記揺れや部分一致により誤った候補を返したり、候補が多すぎて選択できなかったりする問題がある。本プロシージャは、正規化辞書を用いた決定論的な名称解決により、候補が1件に絞れる場合は自動確定し、複数候補がある場合はユーザーに選択を促すことで、誤った推測を排除する。

## 設計上の位置づけ

RESOLVE_ENTITY_ALIASはAPP_PRODUCTIONスキーマに配置され、以下のオブジェクトと連携する。

- NORMALIZE_JA: 入力文字列の汎用正規化
- NORMALIZE_JA_DEPT: 部署名の特化正規化
- DIM_ENTITY_ALIAS: エイリアステーブル（NAME_RESOLUTIONスキーマ）
- RESOLVE_ENTITY_ALIAS_TOOL: Cortex Agent向けのラッパーツール
- SNOWFLAKE_DEMO_AGENT: 名称解決の結果をもとに集計やスコープ展開を実行

本プロシージャは3段階の検索戦略（生の一致→正規化一致→正規化部分一致）を実施し、各段階で候補が1件のみの場合は自動確定、複数候補が残る場合はユーザーに選択を促す。

## 機能

1. 入力文字列の正規化
   - NORMALIZE_JAで汎用正規化
   - NORMALIZE_JA_DEPTで部署名特化正規化

2. 3段階の検索戦略
   - Step 1: alias_rawによる完全一致（生の入力との一致）
   - Step 2: alias_normalizedによる完全一致（正規化後の一致）
   - Step 3: alias_normalizedによる部分一致（LIKE検索）

3. 自動確定ロジック
   - 候補が1件のみの場合: resolved=候補、decided=true、next="aggregate"
   - 候補が複数でトップのconfidenceが0.95以上、かつ2位との差が0.10以上の場合: resolved=トップ候補、decided=true、next="aggregate"

4. 候補提示ロジック
   - 上記以外の場合: resolved=null、decided=false、next="disambiguate"、candidates=候補リスト

5. エンティティタイプヒント対応
   - entity_type_hintパラメータが指定されている場合は、そのタイプのみを検索
   - 未指定の場合は全タイプから検索

6. 優先度・信頼度による順序付け
   - priority昇順→confidence降順→alias_normalized長さ昇順でソート
   - 最大候補数はmax_candidatesパラメータで制御

## パラメータ

- term (STRING): 解決対象の固有名詞（必須）
- max_candidates (STRING): 候補上限（必須、文字列形式で渡す、通常"8"）
- entity_type_hint (STRING): タイプヒント（任意、'department'/'customer'/'project'/'order'または省略）

## 利用シーン

- 自然言語データ分析での固有名詞解決: ユーザーが「デジタルイノベーション部」と入力した場合に、DEPARTMENT_ID='D123'に確定
- 顧客名の名寄せ: 「ＡＢＣ株式会社」「ABC(株)」「エービーシー」といった表記揺れを同一顧客に解決
- 案件名・オーダー名の特定: 部分的な名称や略称から正しいプロジェクトやオーダーを特定
- 候補絞り込み: タイプヒントを指定することで、部署のみ・顧客のみといった限定検索を実現
- エージェント連携: Cortex Agentのツールとして呼び出され、名称解決結果をもとに集計やスコープ展開を実行
- データクリーニング: 重複エンティティの名寄せやマスタデータの正規化処理
