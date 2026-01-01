# テーブル名: [TABLE_NAME]

> [!info] 概要
> このテーブルの目的と主要な用途を記述

## 📊 基本情報

| 項目 | 内容 |
|------|------|
| **スキーマ** | [[schemas/schema_name]] |
| **作成日** | YYYY-MM-DD |
| **更新頻度** | 高頻度 / 中頻度 / 低頻度 |
| **データ量** | 〜100万行 / 〜1億行 / それ以上 |
| **関連テーブル** | [[table1]], [[table2]] |

**タグ**: #トランザクション #マスタ #ログ #分析

---

## 🏗️ テーブル定義

```sql
CREATE TABLE schema_name.table_name (
    id NUMBER(38,0) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ,
    
    CONSTRAINT pk_table_name PRIMARY KEY (id)
);
```

## 📋 カラム一覧

| カラム名 | データ型 | NULL | デフォルト | 説明 |
|----------|----------|------|------------|------|
| `id` | NUMBER(38,0) | NOT NULL | - | プライマリキー（自動採番） |
| `name` | VARCHAR(100) | NULL | - | 名称 |
| `created_at` | TIMESTAMP_NTZ | NOT NULL | CURRENT_TIMESTAMP() | 作成日時 |
| `updated_at` | TIMESTAMP_NTZ | NULL | - | 更新日時 |

## 🔗 リレーション

### 外部キー
- `parent_id` → [[tables/parent_table]].`id`

### 参照されるテーブル
- [[tables/child_table]].`this_table_id`

## 🚀 パフォーマンス設計

### クラスタリングキー
```sql
ALTER TABLE table_name CLUSTER BY (created_at DESC);
```

### インデックス
- 検索タグ: `column1`, `column2`
- マテリアライズドビュー: [[queries/mv_table_summary]]

### パーティショニング（外部テーブルの場合）
```
s3://bucket/table_name/
  year=2026/month=01/day=02/
```

## 📈 使用パターン

### 主要クエリ
1. **最新レコード取得**
   ```sql
   SELECT * FROM table_name 
   WHERE created_at >= DATEADD(day, -7, CURRENT_DATE())
   ORDER BY created_at DESC;
   ```

2. **集計クエリ**
   ```sql
   SELECT DATE_TRUNC('day', created_at) as date, COUNT(*)
   FROM table_name
   GROUP BY 1;
   ```

### アクセスパターン
- **読み取り**: 1000 qps
- **書き込み**: 100 qps
- **バッチ処理**: 日次 3:00 AM

## ⚠️ 注意事項

- [ ] 大量データのため、全件検索は避ける
- [ ] `created_at`にはインデックスが効いている
- [ ] 削除は論理削除（`deleted_at`を使用）

## 🔄 変更履歴

| 日付 | 変更内容 | 担当者 |
|------|----------|--------|
| 2026-01-02 | 初版作成 | - |

## 🔍 関連ドキュメント

- [[migrations/2026-01-02_create_table]]
- [[reviews/table_name_review]]
- [[queries/table_name_queries]]
