# VIEW設計：[[V_ENTITY_ALIAS_ALL]]（別名辞書の統合・winner決定）

## 概要
[[APP_PRODUCTION.V_ENTITY_ALIAS_ALL]] は、名称解決で利用する別名辞書を 統合し、重複を排除して winner を決定する参照用VIEWである。  
手動辞書（[[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL]]）と自動生成辞書（[[APP_PRODUCTION.V_ENTITY_ALIAS_AUTO]]）を UNION し、  
同一の (alias_normalized, entity_type) に対して priority / confidence に基づき1件に確定する。

本VIEWの出力は、物理検索用テーブル（[[NAME_RESOLUTION.DIM_ENTITY_ALIAS]]）へ refresh により materialize され、  
Agent / Procedure は原則として物理テーブル側を参照する（[[V_ENTITY_ALIAS_ALL]] は「定義」と「確認」に使う）。

## 入力ソース

### 手動辞書（MANUAL）
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL]]
- 特性：
  - 人が登録・承認する別名（略称、社内用語、例外、ルビ等）
  - is_active=true のみを対象
  - AUTO より優先される設計（priority を小さくする運用）

### 自動生成辞書（AUTO）
- [[APP_PRODUCTION.V_ENTITY_ALIAS_AUTO]]
- 特性：
  - マスタ/VIEWから機械生成できる名称を展開
  - is_active=true のみを対象

## 出力仕様（スキーマ）
[[V_ENTITY_ALIAS_ALL]] は以下の列を返す（統合後のwinner 1行）：

- alias_raw
- alias_normalized
- entity_type
- entity_id
- entity_name
- confidence
- priority
- is_active

※ 物理テーブル化（[[DIM_ENTITY_ALIAS]]）では refresh_run_id / refreshed_at など運用列を付与する。

## winner 決定ロジック（重複排除）
同一の (alias_normalized, entity_type) が複数行存在しうるため、以下の規則で winner を1件に決定する。

### ルール
- partition key:
  - alias_normalized, entity_type
- order:
  1. priority asc（小さいほど優先）
  2. confidence desc（高いほど優先）

このルールにより、
- MANUAL が AUTO より優先される（MANUAL の priority を小さく運用するため）
- 同一priority内では confidence が高い候補が勝つ

### 実装（典型）
- UNION ALL で MANUAL / AUTO を結合
- QUALIFY row_number() over (...) = 1 で winner を確定

## 運用・注意点

### [[V_ENTITY_ALIAS_ALL]] は正本ではない
- 「正本」は MANUAL + AUTO の生成規則であり、本VIEWはそれを統合した参照結果
- 検索性能や安定運用のため、実運用では [[NAME_RESOLUTION.DIM_ENTITY_ALIAS]] を参照する

### is_active の扱い
- MANUAL / AUTO それぞれで is_active=true のみ対象とする
- 無効化は削除でなく is_active=false とする（履歴保持）

### 衝突（alias_normalized の被り）
- 同じ alias_normalized が複数の entity_id に割り当たることは現実に起こり得る
- 本VIEWは winner を1件に潰すため、衝突が本質的に解消できない場合は、
  - priority を調整し winner を固定する
  - もしくは（別設計として）解決プロシージャ側で候補提示（disambiguate）に倒す
- 「衝突がありうる」こと自体は問題ではなく、winner を人が制御できることが重要

## 関連
- 手動辞書：[[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL]]
- 自動生成：[[APP_PRODUCTION.V_ENTITY_ALIAS_AUTO]]
- 物理検索用：[[NAME_RESOLUTION.DIM_ENTITY_ALIAS]]（refreshで生成）
- 解決プロシージャ：[[APP_PRODUCTION.RESOLVE_ENTITY_ALIAS]] / *_TOOL

