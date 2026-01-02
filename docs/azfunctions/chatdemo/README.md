# Azure Functions Documentation

このディレクトリにはAzure Functionsの設計書を配置します。

## 📚 ドキュメント一覧

- **[命名規則](NAMING_CONVENTIONS_GUIDE.md)** - Python/Azure Functions固有の命名規則
- **[メンテナンスガイド](MAINTENANCE_GUIDE.md)** - 開発・テスト・デプロイ手順
- **[API仕様書](API_SPECIFICATION.md)** - エンドポイント一覧と使用方法

## 🎯 主要機能

### 1. チャット機能
- Snowflake Cortex Agentとの対話
- ストリーミング応答（SSE）対応
- メッセージ履歴管理

### 2. DB設計レビュー（NEW）
- Snowflake AgentによるDB設計の自動レビュー
- Markdown形式でレビュー結果を出力
- 命名規則・データ型・PK/FK整合性チェック

## 📋 エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/chat` | チャットメッセージ処理 |
| POST | `/api/chat/stream` | ストリーミングチャット（SSE） |
| POST | `/api/review/schema` | DB設計レビュー実行 |

## � 実装ノウハウ

### Snowflake Agent REST API統合

#### 重要な発見

**❌ SQLでのAgent実行は不可:**
```python
# これは動作しません
result = cursor.execute(
    "SELECT SNOWFLAKE.CORTEX.COMPLETE_AGENT(...)"
).fetchone()
```

**✅ REST API経由でのみ実行可能:**
```python
url = f"{base_url}/api/v2/databases/{db}/schemas/{schema}/agents/{agent}:run"
response = session.post(url, headers=headers, json=payload, stream=True)
```

#### SSEレスポンスの正しい解析

**Snowflake AgentのSSE形式:**
```python
# レスポンスイベント例
event: response.text.delta
data: {"content_index": 12, "text": "レビュー結果..."}

event: response.text
data: {"content_index": 12, "text": "完全なレスポンス..."}

event: done
data: [DONE]
```

**正しい解析コード:**
```python
for line in response.iter_lines():
    if line.startswith(b'data: '):
        decoded_line = line.decode('utf-8')
        json_str = decoded_line.replace('data: ', '')
        
        if json_str == '[DONE]':
            break
            
        try:
            data = json.loads(json_str)
            if 'text' in data:
                full_response += data['text']  # ✅ 正しい
        except json.JSONDecodeError:
            pass
```

**❌ 誤った実装例:**
```python
# これは動作しません
for chunk in response.iter_content():
    delta = parse_sse(chunk)
    text = delta.content  # ❌ 'content'フィールドは存在しない
```

#### Markdown抽出

AgentレスポンスからMarkdownブロックを抽出：
```python
def _extract_markdown(self, text: str) -> str:
    """~~~md ... ~~~ブロックを抽出"""
    pattern = r'~~~md\s*\n(.*?)\n~~~'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        return match.group(1)
    else:
        return text  # フォールバック: 全文を返す
```

#### ファイル保存

タイムスタンプ付きファイル名で保存：
```python
def _save_markdown(self, schema: str, markdown: str) -> str:
    """レビュー結果をMarkdownファイルとして保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{schema}_{timestamp}.md"
    filepath = self.output_dir / filename
    
    filepath.write_text(markdown, encoding='utf-8')
    return filename
```

### デバッグTips

#### 1. SSEストリームのロギング
```python
line_count = 0
for line in response.iter_lines():
    line_count += 1
    decoded_line = line.decode('utf-8')
    print(f"[Line {line_count}] {decoded_line[:200]}")  # 先頭200文字を出力

print(f"Total lines received: {line_count}")
print(f"Full response length: {len(full_response)}")
```

#### 2. Azure Functions実行時のログ確認
```bash
# ターミナルでログをリアルタイム表示
cd /home/yolo/pg/snowflake_chatdemo/app/azfunctions/chatdemo
func start --port 7071 2>&1 | tee /tmp/azfunc.log
```

#### 3. curlでのテスト
```bash
# リクエストボディをファイルから読み込み
cat > request.json << 'EOF'
{
  "target_schema": "DB_DESIGN",
  "max_tables": 3
}
EOF

curl -v -X POST http://localhost:7071/api/review/schema \
  -H "Content-Type: application/json" \
  -d @request.json
```

### パフォーマンス最適化

#### Token予算の調整
```yaml
# Agent定義
orchestration:
  budget:
    seconds: 1200      # 20分（複雑なスキーマ対応）
    tokens: 614400     # 60万トークン（DDL例・移行手順含む）
```

#### レスポンスサイズの制限
```python
# Markdownファイルサイズチェック
if len(markdown) > 100000:  # 100KB超過
    logger.warning(f"Large review output: {len(markdown)} bytes")
```

## 🔗 関連リンク

- 実際のコード: [app/azfunctions/chatdemo/](../../../app/azfunctions/chatdemo/)
- テストコード: [tests/azfunctions/chatdemo/](../../../tests/azfunctions/chatdemo/)
- Git運用規則: [docs/git/chatdemo/GIT_WORKFLOW.md](../../git/chatdemo/GIT_WORKFLOW.md)
- Snowflake設計ガイド: [docs/snowflake/chatdemo/MAINTENANCE_GUIDE.md](../../snowflake/chatdemo/MAINTENANCE_GUIDE.md)
