# RESOLVE_ENTITY_ALIAS_TOOL 設計書

## 概要

RESOLVE_ENTITY_ALIAS_TOOLは、Cortex Agent向けにRESOLVE_ENTITY_ALIASプロシージャをJSON形式でラップしたツールプロシージャである。Agentが自然言語質問から抽出した固有名詞をJSON形式で渡すと、内部でRESOLVE_ENTITY_ALIASを呼び出し、名称解決結果をVARIANT形式で返却する。

## 業務上の意味

Cortex Agentは、ツールの引数をJSON形式で渡す仕様となっている。RESOLVE_ENTITY_ALIASプロシージャは直接3つのパラメータ（term、max_candidates、entity_type_hint）を受け取る設計だが、Agent連携を容易にするため、本ツールがJSON形式のペイロードを受け取り、内部で適切な形式に変換してRESOLVE_ENTITY_ALIASを呼び出す。これにより、Agent定義のツール記述がシンプルになり、ツールの保守性が向上する。

## 設計上の位置づけ

RESOLVE_ENTITY_ALIAS_TOOLはAPP_PRODUCTIONスキーマに配置され、以下のオブジェクトと連携する。

- RESOLVE_ENTITY_ALIAS: 実際の名称解決ロジックを実行するプロシージャ
- SNOWFLAKE_DEMO_AGENT: 本ツールをresolve_entity_aliasツールとして登録し、自然言語質問から抽出した固有名詞の解決に使用

本ツールは、JSON形式のペイロードを受け取り、term、max_candidates、entity_type_hintを抽出してRESOLVE_ENTITY_ALIASを呼び出す。entity_type_hintが省略されている場合は2引数、指定されている場合は3引数で呼び出す。

## 機能

1. JSON形式のペイロード受け取り
   - payload_json (STRING): JSON形式のツール引数
   - 空文字列またはNULLの場合はデフォルト値として空オブジェクトを使用

2. パラメータの抽出とバリデーション
   - term: 固有名詞（必須）
   - max_candidates: 候補上限（任意、デフォルト"8"）
   - entity_type_hint: タイプヒント（任意、デフォルトは空文字列）

3. RESOLVE_ENTITY_ALIASの呼び出し
   - entity_type_hintが空の場合: 2引数呼び出し（term、max_candidates）
   - entity_type_hintが指定されている場合: 3引数呼び出し（term、max_candidates、entity_type_hint）

4. エラーハンドリング
   - termが未指定の場合: ok=false、next="error"、message="term is required"
   - JavaScript例外発生時: ok=false、next="error"、message=例外メッセージ、stack=スタックトレース

## パラメータ

- payload_json (STRING): JSON形式のツール引数（必須）
  - term (STRING): 解決対象の固有名詞（必須）
  - max_candidates (STRING): 候補上限（任意、デフォルト"8"）
  - entity_type_hint (STRING): タイプヒント（任意、'department'/'customer'/'project'/'order'または省略）

## 利用シーン

- Cortex Agentからの名称解決: SNOWFLAKE_DEMO_AGENTがツールとして呼び出し、ユーザー質問から抽出した固有名詞を解決
- JSON形式の統一: Agent定義のツール記述で、引数をJSON形式で記述することで、ツール定義がシンプルになる
- 非同期処理対応: Agentが複数の固有名詞を並行して解決する際に、各固有名詞に対してツールを非同期呼び出し
- エラー情報の伝達: 名称解決に失敗した場合、エラー情報をVARIANT形式でAgentに返却し、次のアクションを決定
- デバッグ支援: ツール呼び出し時のJSON引数とRESOLVE_ENTITY_ALIASの実行結果を一貫して記録
