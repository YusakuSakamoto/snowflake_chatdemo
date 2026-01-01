# テーブル設計：[[design.DIM_ENTITY_ALIAS]]（物理検索用・確定辞書）

## 概要
NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]] は、名称解決（固有名詞解決）で利用する 物理検索用の確定辞書テーブルである。  
手動辞書（NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS_MANUAL]]）および自動生成辞書（APP_PRODUCTION.[[design.V_ENTITY_ALIAS_AUTO]] 等）を統合・重複排除した結果を、決定論的に検索できる形で保持する。

このテーブルは「検索のための最終形（materialized index）」であり、Agent / Procedure は原則として本テーブルのみを参照して候補解決を行う。  
正の根拠（source of truth）は手動辞書と自動生成辞書の統合規則であり、
NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]] 自体は refresh により再生成される。

## 役割と位置づけ
- 目的：高速・安定・決定論の名称解決を提供する
- 特徴：
  - alias_normalized + entity_type をキーに 一意な候補（winner）を保持
  - refresh_run_id により refresh 実行単位を追跡できる
  - refresh は INSERT OVERWRITE 等により 全量再生成される（部分更新前提にしない）

## 入力ソースとの関係

### 手動辞書との関係
- 手動辞書：NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS_MANUAL]]
  - 人が追加・承認する別名（略称、社内用語、例外、ルビ等）
  - is_active=false で無効化し、削除はしない
- [[design.DIM_ENTITY_ALIAS]] は手動辞書を最優先で取り込む（priority 小が優先）

### 自動生成辞書との関係
- 自動生成：APP_PRODUCTION.[[design.V_ENTITY_ALIAS_AUTO]]（および同等のDEV側）
  - マスタ/正規化VIEWから機械生成できる名称を展開
- [[design.DIM_ENTITY_ALIAS]] は自動生成辞書も取り込み、手動辞書と統合して winner を決定する

### 統合ビューとの関係
- 統合規則は APP_PRODUCTION.[[design.V_ENTITY_ALIAS_ALL]]（または同等）で表現される
- [[design.DIM_ENTITY_ALIAS]] は [[design.V_ENTITY_ALIAS_ALL]] を materialize したものとして運用する
  - 重複排除（winner 決定）は [[design.V_ENTITY_ALIAS_ALL]] の規則に従う

## カラム定義の思想

### 識別キー（主キー）
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].ALIAS_NORMALIZED]]
  - 正規化関数（[[design.NORMALIZE_JA]] / [[design.NORMALIZE_JA_DEPT]] 等）適用後の文字列
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].ENTITY_TYPE]]
  - 'department' / 'customer' / 'project' / 'order'
- 上記 2列で 1候補（winner）に決まることを保証するため、PRIMARY KEY を付与する  
  ※ Snowflake の制約は情報的制約（enforced ではない）だが、設計意図を明示する。

### 表記系
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].ALIAS_RAW]]
  - 人間に見せる元表記（入力表記）
  - 必須ではないが、説明可能性のため保持する

### 解決結果
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].ENTITY_ID]]
  - 対象エンティティのID（共通利用のため VARCHAR）
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].ENTITY_NAME]]
  - 正式名称（UI表示・確認用）

### スコアリング
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].CONFIDENCE]]
  - 0.0〜1.0 の信頼度（「正しさ」ではなく、どれくらい強い別名か）
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].PRIORITY]]
  - 小さいほど優先
  - MANUAL は AUTO より常に小さくする（運用ルール）

### 有効/無効
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].IS_ACTIVE]]
  - true のみ検索対象
  - 無効化は手動辞書側で行い、refresh により反映される

### リフレッシュ追跡
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].REFRESH_RUN_ID]]
  - refresh 実行単位の識別子（timestamp や UUID）
  - 監査・トラブルシュート時に「どの refresh で生成されたか」を追える
- [[NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS]].REFRESHED_AT]]
  - refresh 実行時刻

## 運用ルール（refresh）

### 基本方針
- refresh は 全量再生成（INSERT OVERWRITE / SWAP 等）を標準とする
- publish（適用）は原子的切替を推奨する
  - 例：`DIM_ENTITY_ALIAS__NEXT` を作成 → 検査 → SWAP

### refresh の入力
- refresh の入力は [[design.V_ENTITY_ALIAS_ALL]] の winner のみ（重複排除済）とする
- 既存の [[design.DIM_ENTITY_ALIAS]] の内容に依存した増分更新は前提としない

### refresh_run_id の生成
- refresh_run_id は refresh 実行時に生成し、全行に同値で付与する
- timestamp 文字列でもよいが、将来的には UUID を推奨する余地がある

## 制約（推奨）
- PRIMARY KEY: (alias_normalized, entity_type)
- CHECK（運用・品質目的）
  - entity_type は許容値のみ
  - confidence は 0.0〜1.0
  - priority は正の整数
  - is_active は true/false（NOT NULL）

※ Snowflake の CHECK は情報的制約であり、強制力は設定/運用に依存するが、
設計意図を明確にするため定義を推奨する。

## 関連
- 手動辞書：NAME_RESOLUTION.[[design.DIM_ENTITY_ALIAS_MANUAL]]
- 自動生成：APP_PRODUCTION.[[design.V_ENTITY_ALIAS_AUTO]]
- 統合ビュー：APP_PRODUCTION.[[design.V_ENTITY_ALIAS_ALL]]
- 解決プロシージャ：APP_PRODUCTION.[[design.RESOLVE_ENTITY_ALIAS]]（および *_TOOL ラッパー）

