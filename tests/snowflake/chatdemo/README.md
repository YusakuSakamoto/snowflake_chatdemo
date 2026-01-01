# Snowflake Tests

Snowflakeのスキーマ、クエリ、パフォーマンステストを配置します。

## 📁 構造

```
tests/snowflake/chatdemo/
├── schema/                      # スキーマ検証テスト
├── queries/                     # クエリテスト
├── performance/                 # パフォーマンステスト
└── fixtures/                    # テストデータ
```

## 🧪 テスト実行

```bash
cd /home/yolo/pg/snowflake_chatdemo
pytest tests/snowflake/chatdemo/ -v
```

## 📋 テストカバレッジ

### スキーマテスト
- [ ] テーブル存在確認
- [ ] カラム定義検証
- [ ] 制約確認

### クエリテスト
- [ ] Cortex Analytics クエリ
- [ ] 外部テーブルアクセス
- [ ] パーティション最適化

### パフォーマンステスト
- [ ] クエリ実行時間
- [ ] データスキャン量
- [ ] コスト見積もり
