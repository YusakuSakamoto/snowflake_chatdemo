# スキーマ設計：[[NAME_RESOLUTION]]

## 概要
[[NAME_RESOLUTION]] は、エンティティの名称解決（別名解決）を提供する専用スキーマである。

「部署A」「営業部」「Sales」といった異なる表記を、正規化した上で「DEPT_001（営業部）」という正式なエンティティに紐付けることで、自然言語クエリの精度を高める。

## 業務上の意味
- このスキーマが表す概念  
  ユーザーや外部システムが使う「あいまいな名称」と、データベース内の「正式なエンティティ」を結びつける辞書。

- 主な利用シーン  
  - Cortex Agent の自然言語クエリで、ユーザーが「営業の売上」と言ったら「DEPT_001」を検索
  - 外部システムからの連携データで、部署名の表記ゆれを吸収
  - UIのオートコンプリート機能で、ユーザー入力から候補を絞り込み

## 設計上の位置づけ
[[NAME_RESOLUTION]] スキーマは、以下のデータフロー全体の「名前解決レイヤー」として機能する：

1. ユーザー入力：あいまいな名称（略称、口語表現、表記ゆれ）
2. 名称解決（[[NAME_RESOLUTION]]） ← 本スキーマ
3. 正式なエンティティID取得
4. データアクセス（[[APP_PRODUCTION]] / [[APP_DEVELOPMENT]]）
5. 結果返却

本スキーマは、Cortex Agent や Procedure から常に参照される共通基盤である。

## スキーマ設計の基本方針

### 1. 手動辞書と自動生成辞書の統合
[[NAME_RESOLUTION]] スキーマは、以下の2種類の辞書を統合する：

#### 手動辞書（[[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL]]）
- 目的：人が追加・承認する別名（略称、社内用語、例外的な表記）
- 特徴：
  - 正の根拠（source of truth）であり、削除ではなく無効化で管理
  - 自動生成辞書より常に優先（priority が小）
  - メンテナンス性を重視し、変更履歴を追跡

#### 自動生成辞書（[[APP_PRODUCTION.V_ENTITY_ALIAS_AUTO]] など）
- 目的：マスタテーブルから機械的に生成できる別名
- 特徴：
  - 部署マスタ、顧客マスタなどから自動展開
  - 手動辞書に存在しない場合のフォールバック
  - VIEW として定義し、マスタ更新時に自動反映

#### 統合規則（[[APP_PRODUCTION.V_ENTITY_ALIAS_ALL]]）
- 目的：手動辞書と自動生成辞書を統合し、重複排除のルールを明示
- winner 決定ルール：
  1. priority が小さいものを優先
  2. priority が同じ場合は confidence が高いものを優先
  3. それでも同じ場合は手動辞書を優先（is_manual=true）

### 2. 物理検索用の確定辞書（[[NAME_RESOLUTION.DIM_ENTITY_ALIAS]]）
- 目的：統合規則（[[V_ENTITY_ALIAS_ALL]]）を物理化し、高速検索を実現
- 特徴：
  - refresh により全量再生成される（INSERT OVERWRITE）
  - alias_normalized + entity_type で一意な候補（winner）を保持
  - Agent / Procedure は本テーブルのみを参照して名称解決

### 3. 正規化関数の適用
名称解決では、以下の正規化関数を使用する：
- [[NORMALIZE_JA]]：全角→半角、小文字化、記号除去
- [[NORMALIZE_JA_DEPT]]：部署名専用（「部」「課」「グループ」などの接尾辞を除去）

正規化により、表記ゆれを吸収：
- 「営業部」「営業」「sales」→ すべて `eigyo` に正規化
- 「第1営業部」「第一営業部」→ すべて `dai1eigyo` に正規化

## テーブル構成

### 1. [[DIM_ENTITY_ALIAS_MANUAL]]（手動辞書）
- 役割：人が追加・承認する別名の管理
- 主要カラム：
  - `alias_raw`: 元の表記（「営業部」「Sales」など）
  - `alias_normalized`: 正規化後の文字列（「eigyo」など）
  - `entity_id`: 解決先のエンティティID（「DEPT_001」など）
  - `entity_type`: エンティティの種別（'department', 'customer', etc.）
  - `priority`: 優先度（小さいほど優先）
  - `is_active`: 有効/無効フラグ（無効化は削除ではなくfalseに設定）
  - `created_by`: 登録者
  - `approved_by`: 承認者（ワークフローがある場合）

- 運用：
  - UIまたはDMLで直接INSERT/UPDATE
  - 削除はせず、is_active=false で無効化
  - 変更履歴は audit テーブルで追跡（将来拡張）

### 2. [[V_ENTITY_ALIAS_AUTO]]（自動生成辞書・VIEW）
- 役割：マスタテーブルから自動生成できる別名
- 生成元例：
  - 部署マスタ（[[DEPARTMENT_MASTER]]）
  - 顧客マスタ（[[CUSTOMER_MASTER]]）
  - プロジェクトマスタ（[[PROJECT_MASTER]]）

- 生成ロジック例：
```sql
-- 部署マスタから別名を自動生成
SELECT 
  department_id AS entity_id,
  'department' AS entity_type,
  department_name AS alias_raw,
  NORMALIZE_JA_DEPT(department_name) AS alias_normalized,
  department_name AS entity_name,
  0.8 AS confidence,  -- 自動生成は0.8固定
  100 AS priority,    -- 手動辞書（1-99）より低い優先度
  TRUE AS is_active
FROM APP_PRODUCTION.DEPARTMENT_MASTER
WHERE is_active = TRUE;
```

### 3. [[V_ENTITY_ALIAS_ALL]]（統合規則・VIEW）
- 役割：手動辞書と自動生成辞書を統合し、winner を決定
- winner 決定ロジック：
```sql
-- 重複排除（alias_normalized + entity_type で最優先の1件のみ）
SELECT *
FROM (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY alias_normalized, entity_type
      ORDER BY priority ASC,      -- priority 小が優先
               confidence DESC,    -- confidence 大が優先
               is_manual DESC      -- 手動辞書を優先
    ) AS rank
  FROM (
    SELECT *, TRUE AS is_manual FROM NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL WHERE is_active = TRUE
    UNION ALL
    SELECT *, FALSE AS is_manual FROM APP_PRODUCTION.V_ENTITY_ALIAS_AUTO
  )
)
WHERE rank = 1;
```

### 4. [[DIM_ENTITY_ALIAS]]（物理検索用・確定辞書）
- 役割：[[V_ENTITY_ALIAS_ALL]] を物理化し、高速検索を実現
- 主要カラム：
  - `alias_normalized`: 正規化後の文字列（PRIMARY KEY の一部）
  - `entity_type`: エンティティ種別（PRIMARY KEY の一部）
  - `entity_id`: 解決先のエンティティID
  - `entity_name`: 正式名称（UI表示用）
  - `confidence`: 信頼度（0.0〜1.0）
  - `priority`: 優先度
  - `refresh_run_id`: refresh 実行単位の識別子
  - `refreshed_at`: refresh 実行時刻

- 運用：
  - refresh タスク（日次 or on-demand）で全量再生成
  - INSERT OVERWRITE または SWAP で原子的に切替

## 名称解決のクエリパターン

### パターン1：単一エンティティの解決
```sql
-- ユーザーが「営業部」と入力した場合
SELECT entity_id, entity_name, confidence
FROM NAME_RESOLUTION.DIM_ENTITY_ALIAS
WHERE alias_normalized = NORMALIZE_JA_DEPT('営業部')
  AND entity_type = 'department'
  AND is_active = TRUE;

-- 結果例：
-- entity_id: DEPT_001
-- entity_name: 営業部
-- confidence: 1.0
```

### パターン2：あいまい検索（前方一致）
```sql
-- ユーザーが「営業」と入力した場合（オートコンプリート）
SELECT entity_id, entity_name, alias_raw, confidence
FROM NAME_RESOLUTION.DIM_ENTITY_ALIAS
WHERE alias_normalized LIKE NORMALIZE_JA_DEPT('営業') || '%'
  AND entity_type = 'department'
  AND is_active = TRUE
ORDER BY confidence DESC, priority ASC
LIMIT 10;

-- 結果例：
-- DEPT_001 | 営業部 | 営業 | 1.0
-- DEPT_002 | 第1営業部 | 第1営業部 | 0.9
-- DEPT_003 | 第2営業部 | 第2営業部 | 0.9
```

### パターン3：複数エンティティの一括解決
```sql
-- Cortex Agent が「営業部とシステム部の売上」という質問を受けた場合
WITH user_input AS (
  SELECT '営業部' AS term, 'department' AS type
  UNION ALL
  SELECT 'システム部', 'department'
)
SELECT 
  u.term,
  e.entity_id,
  e.entity_name,
  e.confidence
FROM user_input u
LEFT JOIN NAME_RESOLUTION.DIM_ENTITY_ALIAS e
  ON NORMALIZE_JA_DEPT(u.term) = e.alias_normalized
  AND u.type = e.entity_type
  AND e.is_active = TRUE;
```

### パターン4：信頼度による候補の絞り込み
```sql
-- confidence が 0.7 以上の高信頼候補のみ取得
SELECT entity_id, entity_name, confidence
FROM NAME_RESOLUTION.DIM_ENTITY_ALIAS
WHERE alias_normalized = NORMALIZE_JA('顧客A')
  AND entity_type = 'customer'
  AND confidence >= 0.7
  AND is_active = TRUE
ORDER BY confidence DESC;
```

## 運用フロー

### 1. 初期セットアップ
1. 手動辞書テーブル（[[DIM_ENTITY_ALIAS_MANUAL]]）を作成
2. 自動生成辞書 VIEW（[[V_ENTITY_ALIAS_AUTO]]）を作成
3. 統合規則 VIEW（[[V_ENTITY_ALIAS_ALL]]）を作成
4. 物理検索用テーブル（[[DIM_ENTITY_ALIAS]]）を作成
5. 初回 refresh 実行

### 2. 日常運用
#### 手動辞書の更新（必要時）
```sql
-- 新しい別名を追加
INSERT INTO NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL (
  alias_raw, alias_normalized, entity_id, entity_type,
  entity_name, confidence, priority, is_active,
  created_by, created_at
) VALUES (
  'Sales', NORMALIZE_JA('Sales'), 'DEPT_001', 'department',
  '営業部', 1.0, 10, TRUE,
  'USER_123', CURRENT_TIMESTAMP()
);

-- 不要になった別名を無効化
UPDATE NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL
SET is_active = FALSE,
    updated_by = 'USER_123',
    updated_at = CURRENT_TIMESTAMP()
WHERE alias_raw = 'OldName' AND entity_type = 'department';
```

#### refresh 実行（日次 or on-demand）
```sql
-- Task または手動実行
CREATE OR REPLACE TASK refresh_entity_alias
  WAREHOUSE = ETL_WH
  SCHEDULE = 'USING CRON 0 2 * * * Asia/Tokyo'  -- 毎日2時
AS
BEGIN
  -- 一時テーブルに統合結果を生成
  CREATE OR REPLACE TRANSIENT TABLE NAME_RESOLUTION.DIM_ENTITY_ALIAS_TEMP AS
  SELECT 
    *,
    UUID_STRING() AS refresh_run_id,
    CURRENT_TIMESTAMP() AS refreshed_at
  FROM APP_PRODUCTION.V_ENTITY_ALIAS_ALL;

  -- 原子的に切替
  ALTER TABLE NAME_RESOLUTION.DIM_ENTITY_ALIAS SWAP WITH NAME_RESOLUTION.DIM_ENTITY_ALIAS_TEMP;
  DROP TABLE NAME_RESOLUTION.DIM_ENTITY_ALIAS_TEMP;
END;
```

### 3. 品質チェック
#### 重複チェック
```sql
-- alias_normalized + entity_type で重複がないか確認
SELECT alias_normalized, entity_type, COUNT(*) AS dup_count
FROM NAME_RESOLUTION.DIM_ENTITY_ALIAS
WHERE is_active = TRUE
GROUP BY 1, 2
HAVING COUNT(*) > 1;

-- 期待値：0件（重複なし）
```

#### カバレッジチェック
```sql
-- マスタテーブルのエンティティが辞書に含まれているか
SELECT d.department_id, d.department_name
FROM APP_PRODUCTION.DEPARTMENT_MASTER d
LEFT JOIN NAME_RESOLUTION.DIM_ENTITY_ALIAS e
  ON d.department_id = e.entity_id
  AND e.entity_type = 'department'
WHERE d.is_active = TRUE
  AND e.entity_id IS NULL;

-- 期待値：0件（全マスタが辞書に含まれている）
```

#### 解決率チェック
```sql
-- Cortex Agent のログから、名称解決の成功率を計算
SELECT 
  DATE_TRUNC('day', timestamp) AS day,
  COUNT(*) AS total_queries,
  COUNT_IF(resolved_entity_id IS NOT NULL) AS resolved,
  ROUND(resolved / total_queries * 100, 2) AS resolution_rate_pct
FROM LOG.CORTEX_CONVERSATIONS
WHERE message_role = 'user'
  AND year = 2026 AND month = 1
GROUP BY 1
ORDER BY 1;

-- 目標：resolution_rate_pct > 90%
```

## スキーマの拡張計画

### 1. 変更履歴の追跡
手動辞書の変更履歴をトラッキング：
```sql
CREATE TABLE NAME_RESOLUTION.AUDIT_ENTITY_ALIAS_MANUAL (
  audit_id VARCHAR PRIMARY KEY,
  operation VARCHAR,  -- INSERT / UPDATE / DELETE
  alias_raw VARCHAR,
  entity_id VARCHAR,
  entity_type VARCHAR,
  old_value VARIANT,
  new_value VARIANT,
  changed_by VARCHAR,
  changed_at TIMESTAMP_NTZ
);

-- トリガーまたはアプリケーション側で記録
```

### 2. 承認ワークフロー
手動辞書の追加に承認プロセスを導入：
```sql
-- pending 状態で登録し、承認後に is_active = TRUE
ALTER TABLE NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL
  ADD COLUMN approval_status VARCHAR DEFAULT 'pending';  -- pending / approved / rejected

-- 承認者が承認
UPDATE NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL
SET approval_status = 'approved',
    approved_by = 'MANAGER_USER',
    approved_at = CURRENT_TIMESTAMP(),
    is_active = TRUE
WHERE alias_raw = '新規別名' AND approval_status = 'pending';
```

### 3. 多言語対応
英語・中国語などの別名を追加：
```sql
ALTER TABLE NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL
  ADD COLUMN language VARCHAR DEFAULT 'ja';  -- ja / en / zh

-- 英語の別名を追加
INSERT INTO NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL (
  alias_raw, alias_normalized, entity_id, entity_type,
  entity_name, language, confidence, priority, is_active
) VALUES (
  'Sales Department', NORMALIZE_EN('Sales Department'), 'DEPT_001', 'department',
  '営業部', 'en', 1.0, 10, TRUE
);

-- クエリ時に言語指定
SELECT entity_id, entity_name
FROM NAME_RESOLUTION.DIM_ENTITY_ALIAS
WHERE alias_normalized = NORMALIZE_EN('Sales')
  AND entity_type = 'department'
  AND language = 'en'
  AND is_active = TRUE;
```

### 4. スコアリングモデルの改善
confidence を機械学習モデルで動的に調整：
```sql
-- 実際の解決成功率から confidence を更新
UPDATE NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL
SET confidence = (
  SELECT AVG(CASE WHEN resolved_correctly THEN 1.0 ELSE 0.0 END)
  FROM LOG.CORTEX_CONVERSATIONS
  WHERE resolved_entity_id = DIM_ENTITY_ALIAS_MANUAL.entity_id
    AND year >= 2026
)
WHERE entity_id IN (SELECT DISTINCT entity_id FROM LOG.CORTEX_CONVERSATIONS);
```

### 5. 類似度検索（Fuzzy Match）
完全一致しない場合に、編集距離やベクトル類似度で候補を提示：
```sql
-- Snowflake の EDITDISTANCE 関数を使用
SELECT 
  entity_id,
  entity_name,
  alias_normalized,
  EDITDISTANCE(alias_normalized, NORMALIZE_JA('eiygyo')) AS distance
FROM NAME_RESOLUTION.DIM_ENTITY_ALIAS
WHERE entity_type = 'department'
  AND EDITDISTANCE(alias_normalized, NORMALIZE_JA('eiygyo')) <= 2
ORDER BY distance ASC
LIMIT 5;

-- 将来的にはベクトル埋め込み + Cortex Search で実装
```

## セキュリティとアクセス制御

### 読み取り権限
```sql
-- Agent / Procedure / アナリストに読み取り権限
GRANT SELECT ON ALL TABLES IN SCHEMA NAME_RESOLUTION TO ROLE AGENT_ROLE;
GRANT SELECT ON ALL VIEWS IN SCHEMA NAME_RESOLUTION TO ROLE AGENT_ROLE;
```

### 書き込み権限
```sql
-- 手動辞書の更新は管理者のみ
GRANT INSERT, UPDATE ON TABLE NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL TO ROLE ENTITY_ADMIN;

-- 物理検索用テーブルは refresh タスクのみが更新
GRANT ALL ON TABLE NAME_RESOLUTION.DIM_ENTITY_ALIAS TO ROLE TASK_ROLE;
```

## 設計レビュー時のチェックポイント
- [ ] 手動辞書と自動生成辞書の統合ルールが明確か
- [ ] priority / confidence による winner 決定ロジックが妥当か
- [ ] 正規化関数（[[NORMALIZE_JA]] / [[NORMALIZE_JA_DEPT]]）が適切に適用されているか
- [ ] refresh が定期的に実行され、物理検索用テーブルが最新に保たれているか
- [ ] 重複チェック・カバレッジチェックが自動化されているか
- [ ] 名称解決の成功率（resolution_rate）が目標値（>90%）を達成しているか
- [ ] 手動辞書の変更履歴が追跡可能か（将来的に audit テーブルで実装）

## 参考リンク
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL]] - 手動辞書の詳細設計
- [[NAME_RESOLUTION.DIM_ENTITY_ALIAS]] - 物理検索用テーブルの詳細設計
- [[APP_PRODUCTION.V_ENTITY_ALIAS_AUTO]] - 自動生成辞書の実装
- [[APP_PRODUCTION.V_ENTITY_ALIAS_ALL]] - 統合規則の実装
- [[APP_PRODUCTION.RESOLVE_ENTITY_ALIAS]] - 名称解決 Procedure
