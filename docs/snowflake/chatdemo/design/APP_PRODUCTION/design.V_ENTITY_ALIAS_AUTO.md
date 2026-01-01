# VIEW設計：[[V_ENTITY_ALIAS_AUTO]]（自動生成 別名辞書）

## 概要
[[APP_PRODUCTION.V_ENTITY_ALIAS_AUTO]] は、名称解決で利用する別名（alias）を 業務データから自動生成する参照用VIEWである。  
部署・顧客・案件・オーダー等の「人が入力しうる名称」を網羅的に列挙し、正規化済みキー（alias_normalized）を付与して辞書化する。

本VIEWは「自動生成できる範囲」を担い、例外・略称・社内用語・ルビ等の手動補完は [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL]] に委ねる。  
最終的な統合は [[APP_PRODUCTION.V_ENTITY_ALIAS_ALL]]（winner決定）で行い、実運用では物理テーブル [[NAME_RESOLUTION.DIM_ENTITY_ALIAS]] を参照する。

## 生成方針（AUTOの責務）
- 「機械的に生成できる名称」を漏れなく列挙する
- 人手の判断を要する別名（略語衝突、社内用語、読みに依存）は扱わない
- alias_normalized を必ず付与し、決定論的な解決のためのキーとする
- is_active=true のみを出力対象とする（無効化は上流で制御）

## 入力ソース（想定）
[[V_ENTITY_ALIAS_AUTO]] は、以下のデータから alias を生成する。

### 部署（department）
- base: [[APP_PRODUCTION.DEPARTMENT_MASTER]]
- 生成候補（例）：
  - [[FULL_NAME]]（正式名称）
  - [[SHORT_NAME]]（略称）
  - [[COMBINED_NAME]]（複合正式：本部＋部門 等）
  - [[COMBINED_SHORT_NAME]]（複合略称）

### 顧客（customer）
- base: [[APP_PRODUCTION.V_CUSTOMER_MASTER]]（または同等の正規化ビュー）
- 生成候補（例）：
  - customer_name

### 案件（project）
- base: [[APP_PRODUCTION.V_PROJECT_MASTER]]（または同等の正規化ビュー）
- 生成候補（例）：
  - project_name（案件名）
  - subject（件名）

### オーダー（order）
- base: [[APP_PRODUCTION.V_ORDER_MASTER]]（または同等の正規化ビュー）
- 生成候補（例）：
  - order_name

※ どの VIEW / TABLE を参照するかは、[[APP_DEVELOPMENT]] / [[APP_PRODUCTION]] で同一仕様とし、配置差のみとする。

## 出力仕様（スキーマ）
[[V_ENTITY_ALIAS_AUTO]] は以下の列を返す（AUTO生成候補の列挙）：

- alias_raw
  - 元の表記（人が入力しうる名称の原文）
- alias_normalized
  - 正規化関数適用後のキー（決定論のための一致キー）
- entity_type
  - 'department' / 'customer' / 'project' / 'order'
- entity_id
  - 対応するマスタ側のID（共通利用のため文字列）
- entity_name
  - UI表示・確認用の正式名称
- confidence
  - AUTO生成の信頼度（生成元により段階付けしてよい）
- priority
  - winner決定用（AUTOは手動辞書より必ず大きい値にする）
- is_active
  - true を基本（無効化が必要な場合は上流や手動辞書側で制御する）

## 正規化ルール（alias_normalized）
- department:
  - [[APP_PRODUCTION.NORMALIZE_JA_DEPT]]（例：末尾の「部/課」等の扱いを含む）
- customer / project / order:
  - [[APP_PRODUCTION.NORMALIZE_JA]]（例：NFKC、空白除去、法人格除去 等）

重要：
- 正規化関数は「意味解釈」ではなく「表記揺れ吸収」のみに限定する
- 文字列LIKE/ILIKE探索での推測を前提にしない（辞書一致を前提にする）

## confidence / priority の考え方
- confidence は「正しさ」ではなく「生成元の信頼度」
  - 例：department の [[FULL_NAME]] は 1.00、略称は 0.85 など
- priority は「winner決定の優先度」
  - AUTOは原則 1000 固定など（MANUALは必ずそれより小さくする）

## 注意点
- 重複（同じ alias_normalized が複数行）は起こり得る
  - 本VIEWは列挙が責務であり、重複排除は [[APP_PRODUCTION.V_ENTITY_ALIAS_ALL]] で行う
- NULL 値は生成対象から除外する（where <col> is not null）
- entity_id / entity_name の定義は「解決に必要な最小限」に留める  
  （物理化・監査・履歴は [[DIM_ENTITY_ALIAS]] 側で担う）

## 関連
- 手動辞書：[[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL]]
- 統合VIEW：[[APP_PRODUCTION.V_ENTITY_ALIAS_ALL]]
- 物理検索用：[[NAME_RESOLUTION.DIM_ENTITY_ALIAS]]
- 解決プロシージャ：[[APP_PRODUCTION.RESOLVE_ENTITY_ALIAS]] / *_TOOL
- 正規化関数：[[APP_PRODUCTION.NORMALIZE_JA]], [[APP_PRODUCTION.NORMALIZE_JA_DEPT]]

