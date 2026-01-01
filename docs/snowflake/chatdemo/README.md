# Obsidian × Snowflake  
設計資産・名称解決・売上データ基盤 README

本リポジトリ（Obsidian Vault）は、  
**DB設計・設計レビュー・名称解決・売上分析アプリケーション**を  
Snowflake 上で再現性高く運用するための設計正本である。

設計・判断・レビュー・生成結果を明確に分離し、  
LLM / Agent を含む自動化を **推測に頼らず安全に成立させる** ことを目的とする。

---

## Contents

```dataview
LIST
FROM ""
WHERE !startswith(file.path, "master/")
```

---

## 全体思想（最重要）

- **Obsidian Vault 上の Markdown（.md）が唯一の設計正本**
- Snowflake 上の DDL / VIEW / TABLE / PROCEDURE / AGENT はすべて「結果物」
- Agent は実DBや実データを直接解釈しない
- 判断・存在確認・不足指摘は、必ず Vault 上の実在する .md を根拠とする

---

## スキーマ境界と責務（最重要）

本基盤では、用途ごとに明確なスキーマ境界を設ける。

| スキーマ            | 役割         |
| --------------- | ---------- |
| DB_DESIGN       | 設計・設計レビュー  |
| IMPORT          | データ取込・検査   |
| NAME_RESOLUTION | 名称解決（手動辞書） |
| APP_DEVELOPMENT | アプリケーション開発 |
| APP_PRODUCTION  | アプリケーション本番 |

---

## APP_PRODUCTION（楽々販売データ）について

APP_PRODUCTION は、楽々販売由来の売上・案件・部署データを扱う **業務ドメイン**である。  
APP_PRODUCTION は **単一スキーマではなく、用途別スキーマに分散して配置される**。

※ APP_PRODUCTION は業務ドメイン名であり、Snowflake のスキーマ名ではない。

---

### IMPORT

- 楽々販売から取得した CSV / API データの取込先（Raw / Landing）
- データは「止めない」「加工しない」前提で保持する
- 取込失敗・欠損・不正値の混入を許容する
- 正規化・集計・名称解決はここでは行わない

例（APP_PRODUCTION ドメイン）：
- ANKEN_MEISAI（取込用）
- DEPARTMENT_MASTER（取込用）

---

### NAME_RESOLUTION

- 業務データ全体で共通利用する **名称解決の手動辞書**を保持する
- APP_PRODUCTION 固有・全社共通を問わず、人手で管理する別名はここに集約する

例：
- DIM_ENTITY_ALIAS_MANUAL

#### 配置ルール
- 手動管理辞書は NAME_RESOLUTION にのみ存在する
- 自動生成の別名、正規化関数、解決ロジック  
  （UDF / VIEW / PROCEDURE / AGENT）は配置しない  
  → APP_DEVELOPMENT / APP_PRODUCTION に配置する

#### 手動辞書の位置づけ
- 自動生成で拾えない略称・社内用語・例外表記を補完する
- 削除は禁止（is_active=false による無効化のみ）
- 自動生成（AUTO）より常に優先される
- confidence は「正しさ」ではなく「信頼度」を表す

---

### APP_DEVELOPMENT

- アプリケーション開発・検証用のオブジェクト群
- 実験・検証・改善を許容する
- 本番と同一仕様・同一構造を前提とするが、データは開発用

例：
- 正規化 VIEW（V_PROJECT_MASTER, V_INVOICE 等）
- 名称解決ロジック（UDF / VIEW / PROCEDURE）
- 開発用 Agent / セマンティックモデル

---

### APP_PRODUCTION

- 本番アプリケーション用のオブジェクト群
- SLA・監査・権限管理を前提とする
- IMPORT で検査 OK となったデータのみを反映する

例：
- 本番用 正規化 VIEW
- 本番用 正本テーブル（DIM_ / FACT_ / AGG_）
- 本番用 名称解決ロジック（DEV と同仕様）
- 本番用 Agent / 実行ログ

---

## DEV → PROD 反映ルール

本リポジトリにおける DEV / PROD の切り替えは、  
**「設計の差」ではなく「配置先スキーマの差」**のみで表現する。

### 基本方針
- APP_DEVELOPMENT と APP_PRODUCTION は **同一仕様**
- SQL / VIEW / FUNCTION / PROCEDURE / AGENT は原則として同一コード
- 差異は以下に限定する
  - データ量
  - 権限
  - 実行頻度（TASK）
  - 参照先（DEV 用 / PROD 用 RAW）

### 反映手順（標準）
1. APP_DEVELOPMENT で設計・検証を完了させる
2. DB_DESIGN 上の設計レビューで妥当性を確認する
3. 同一 DDL を APP_PRODUCTION に apply する
4. 本番データで結果差分が出ないことを確認する

### 禁止事項
- DEV だけに存在するロジック
- PROD だけに存在する正規化ルール
- DEV / PROD で異なる意味を持つ VIEW 名・カラム名

---

## IMPORT → APP_PRODUCTION（正本は物理：CORE / MART）

- IMPORT は Raw / Landing および検査の層（失敗してよい）
- APP_PRODUCTION は正規化後の正本（CORE / MART）を物理テーブルとして保持する（失敗してはいけない）
- publish は「検査 OK となった取込 run」を入力とする
- APP_PRODUCTION に未検査・途中状態のデータを出さない
- publish は原子的切替（例：__NEXT を作成して SWAP）を標準とする

---

## 名称解決失敗時の振る舞い（Agent ルール）

### 禁止事項
- 文字列 LIKE / ILIKE による推測
- LLM による意味解釈での補完
- 「たぶんこれです」という断定

### 正常系フロー
1. resolve_entity_alias を必ず実行する
2. next = "aggregate" の場合のみ集計に進む
3. department の場合は expand_department_scope を必ず実行する

### 曖昧系フロー（disambiguate）
- 候補を日本語で列挙する
- ユーザーに明示的に選択を求める
- この時点では SQL を生成しない

### エラー系フロー
- next = "error" の場合
  - 不足している情報（年度・正式名称など）を短く提示する
  - 推測で補完しない

---

## DB_DESIGN（参考）

- DB_DESIGN は設計そのもの（DDL / VIEW / 名称解決）をレビューするための基盤
- 業務データは保持しない
- Obsidian Vault 上の Markdown を設計正本とする

---

## 設計思想（要約）

- 設計は Markdown（Vault）を正本とする
- データは IMPORT → APP_* に流れる
- 名称は NAME_RESOLUTION で人が責任を持つ
- Agent は「考えない」、決定論を実行する

この構成により、
- 説明可能性
- 再現性
- 監査耐性
- 人による制御

を同時に満たす。
