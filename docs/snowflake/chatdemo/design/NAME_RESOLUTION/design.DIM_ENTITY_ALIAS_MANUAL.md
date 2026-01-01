# テーブル設計：[[design.DIM_ENTITY_ALIAS_MANUAL]]（手動別名辞書）

## 概要
NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL は、名称解決（固有名詞解決）における 手動管理の別名辞書である。  
自動生成（AUTO）で拾えない略称・社内用語・例外表記・ルビ等を、人が責任を持って追加・維持する。

このテーブルは [[design.NAME_RESOLUTION]] スキーマにのみ存在し、アプリケーション（DEV/PROD）から共通利用される。  
本テーブルの内容は refresh により NAME_RESOLUTION.DIM_ENTITY_ALIAS（物理検索用）へ反映される。

## 役割と位置づけ
- 目的：AUTOでは解決できない表記揺れ・略称・社内用語を補完し、決定論的な解決を可能にする
- 特徴：
  - 人が登録・承認する（= 正しい候補として責任を持つ）
  - 削除しない（履歴・監査のため）
  - is_active=false により無効化する

## どんな別名を入れるか
- 略称
  - 例：「DI」「デジイノ」「本社DI」
- ルビ・読み
  - 例：「ﾃﾞｼﾞﾀﾙｲﾉﾍﾞｰｼｮﾝ」「でじたるいのべーしょん」（入力揺れ対策）
- 特定顧客の通称
- 表記が衝突するケースの補正（priority で winner を固定する）

## カラム定義の思想

### 別名（入力）
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.ALIAS_RAW]]
  - 人が入力・承認した別名（UI上で表示される元表記）
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.ALIAS_NORMALIZED]]
  - 正規化関数適用後の文字列
  - 検索・マッチのキーとして使用する
  - 運用上、`ALIAS_RAW` と `ALIAS_NORMALIZED` の対応が説明できることが重要

### 対象エンティティ
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.ENTITY_TYPE]]
  - 'department' / 'customer' / 'project' / 'order'
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.ENTITY_ID]]
  - 対象エンティティのID（共通利用のため VARCHAR）
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.ENTITY_NAME]]
  - 正式名称（確認用・表示用）

### 優先度と信頼度
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.PRIORITY]]
  - 小さいほど優先
  - MANUAL は AUTO より常に優先される値を設定する（例：100）
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.CONFIDENCE]]
  - 0.0〜1.0 の信頼度
  - 「正しさ」ではなく、候補の強さ（自動確定のしやすさ等）に使う
  - 手動追加は 0.6〜0.8 推奨（運用指針）

### 有効/無効と履歴
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.IS_ACTIVE]]
  - false で無効化（削除せず履歴保持）
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.NOTE]]
  - 由来、使いどころ、注意点、衝突時の意図などを記録
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.CREATED_BY]]
  - 追加したユーザー/システム名
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.CREATED_AT]]
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL.UPDATED_AT]]

## 運用ルール

### 追加・修正
- 新しい略称・ルビ・例外表記が発生した場合は MANUAL に追加する
- 既存行の意味が変わる場合は、NOTE に理由を残す

### 無効化
- 誤登録や不要になった別名は削除せず、is_active=false とする
- 無効化後も履歴は残り、refresh により下流の検索対象から外れる

### 衝突解決
- alias_normalized が衝突する場合は、priority を用いて winner を固定する
- どうしても一意に決められない場合は、候補提示（disambiguate）に倒すことを許容する

## 下流への反映
- 本テーブルは APP_PRODUCTION.V_ENTITY_ALIAS_ALL に取り込まれ、
  重複排除（winner決定）を経て NAME_RESOLUTION.DIM_ENTITY_ALIAS に materialize される
- refresh の単位は refresh_run_id で追跡可能とする

## 関連
- 物理検索用：NAME_RESOLUTION.DIM_ENTITY_ALIAS
- 自動生成：APP_PRODUCTION.V_ENTITY_ALIAS_AUTO
- 統合ビュー：APP_PRODUCTION.V_ENTITY_ALIAS_ALL
- 解決プロシージャ：APP_PRODUCTION.RESOLVE_ENTITY_ALIAS（および *_TOOL）

