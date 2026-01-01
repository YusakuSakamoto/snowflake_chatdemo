# 開発ノウハウとトラブルシューティング

## プロジェクト概要
Snowflake Cortex Agentを使用したチャットアプリケーション
- バックエンド: Azure Functions v4 (Python 3.11)
- フロントエンド: Next.js 14.2.35 + React 18.3.1 + TypeScript
- データベース: Snowflake
- 可視化: Vega-Lite, react-markdown

## Snowflake認証

### JWT認証の実装
**問題**: 初期の実装では`sub`クレームが空でエラーになった

**解決策**:
```python
# qualified_usernameはユーザー名のみ（account.userではない）
qualified_username = user

# issフォーマット: account.user.public_key_fingerprint
iss = f"{account}.{user}.{public_key_fp}"
```

**重要**: `X-Snowflake-Authorization-Token-Type: KEYPAIR_JWT`ヘッダーは不要（401エラーの原因）

### ロール設定
- `PUBLIC`ロールではなく専用ロール（例: `GBPS253YS_API_ROLE`）を使用
- ネットワークポリシーで接続元IPを制限

## Vega-Liteチャート描画

### 基本実装
```tsx
import embed from 'vega-embed';

function VegaChart({ spec }: { spec: any }) {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (containerRef.current && spec) {
      containerRef.current.innerHTML = '';
      embed(containerRef.current, spec, {
        actions: false,
        renderer: 'svg'
      });
    }
  }, [spec]);
  
  return <div ref={containerRef} />;
}
```

### チャートデータの抽出
Snowflake Cortex Agentは`tool_details`配列内の`data_to_chart`ツールでVega-Lite仕様を返す：

```typescript
if (tool.tool_name === 'data_to_chart' && tool.raw?.content) {
  for (const content of tool.raw.content) {
    if (content.json?.charts) {
      const chartSpecs = Array.isArray(content.json.charts) 
        ? content.json.charts 
        : [content.json.charts];
      for (const chartStr of chartSpecs) {
        if (typeof chartStr === 'string') {
          charts.push(JSON.parse(chartStr));
        } else {
          charts.push(chartStr);
        }
      }
    }
  }
}
```

### ラベル表示の問題と解決
**問題**: Y軸の長い部署名が「SI事...」のように省略される

**試行錯誤**:
1. `labelLimit`を大きくする → 効果なし
2. `labelLimit: 0`または`null` → 効果なし
3. `labelExpr`で改行を試みる → 改行が反映されない
4. `padding: { left: 500 }`で左スペースを拡大 → 効果なし
5. CSS `white-space: pre-wrap` → 効果なし

**結論**: Vega-Liteでの長いラベル表示には限界がある。Snowflakeから返される仕様をそのまま使用するのが最適。

**学び**: 
- Vega-Liteのラベル省略はデフォルト動作で、完全に防ぐのは困難
- 仕様を複雑にカスタマイズするより、Snowflakeの仕様を信頼する
- 水平棒グラフへの変換も検討したが、元の仕様を尊重する方針に

## テーブル表示の実装

### text_to_sqlの結果を自動テーブル化
Snowflakeの`text_to_sql`ツールは結果を配列で返すが、Markdownテーブルは含まれない：

```typescript
if (tool.tool_name === 'text_to_sql' && tool.output?.data) {
  const tableData = tool.output.data;
  if (Array.isArray(tableData) && tableData.length > 0) {
    // 1行目がヘッダー
    const headers = tableData[0];
    const rows = tableData.slice(1);
    
    // Markdownテーブルを生成
    let markdownTable = '\n\n| ' + headers.join(' | ') + ' |\n';
    markdownTable += '| ' + headers.map(() => '---').join(' | ') + ' |\n';
    
    for (const row of rows) {
      markdownTable += '| ' + row.join(' | ') + ' |\n';
    }
    
    answerText += markdownTable;
  }
}
```

### テーブルスタイリング
```css
.markdown table {
  border-collapse: collapse;
  width: 100%;
  margin: 1rem 0;
  border: 1px solid #d0d7de;
  font-size: 0.9rem;
  display: block;
  max-height: 500px;  /* 縦スクロール対応 */
  overflow-x: auto;
  overflow-y: auto;
}

.markdown tr:nth-child(even) td {
  background: #f6f8fa;  /* 交互の行色 */
}
```

## ReactMarkdownの設定

### 基本設定
```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeMermaid from 'rehype-mermaid';

<ReactMarkdown 
  remarkPlugins={[remarkGfm]}
  rehypePlugins={[rehypeMermaid]}
>
  {message}
</ReactMarkdown>
```

### 改行処理
**問題**: Snowflakeからの応答に過剰な改行が含まれる

**解決策**:
```tsx
{msg.message.replace(/\n\s*\n\s*\n/g, '\n\n').trim()}
```
連続する3つ以上の改行を2つに正規化

### CSSスタイリングのポイント

#### 行間の調整
```css
/* 見出しは詰める */
.markdown h1,
.markdown h2,
.markdown h3 {
  line-height: 1.2;
}

/* 本文とリストは適度な行間 */
.markdown p,
.markdown li {
  line-height: 1.7;
}
```

#### 余白の調整
```css
/* 見出しの余白は削除 */
.markdown h1,
.markdown h2,
.markdown h3 {
  /* margin-top, margin-bottomは設定しない */
}

/* リストと段落は最小限 */
.markdown ul,
.markdown ol {
  margin: 0.25rem 0;
}

.markdown li {
  margin: 0.1rem 0;
}

.markdown p {
  margin: 0.25rem 0;
}
```

#### white-space設定
**重要**: `white-space: pre-wrap`は削除する
- Markdownの改行処理を妨げる
- 無駄な縦スペースの原因になる

```css
.messageContent {
  word-wrap: break-word;
  line-height: 1.6;
  /* white-space: pre-wrap; は削除 */
}
```

## UIデザイン

### ChatGPTスタイルの実装
```css
/* 背景 */
body {
  background: #f7f7f8;
}

/* センター配置 */
.message {
  max-width: 48rem;
  margin: 0 auto;
}

/* 送信ボタン */
.sendButton {
  background: #10a37f;  /* ChatGPTグリーン */
}

/* メッセージの背景 */
.aiMessage {
  background: white;
}

.myMessage {
  background: #f7f7f8;
}
```

### 複数行入力の実装
```tsx
<textarea
  value={inputMessage}
  onChange={(e) => setInputMessage(e.target.value)}
  onKeyDown={(e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(e);
    }
  }}
  placeholder="メッセージを入力... (Shift+Enterで改行)"
/>
```
- Enter: 送信
- Shift+Enter: 改行

## Gitコミット管理

### コミットメッセージの一括変更
```bash
# 特定の範囲を変更
git filter-branch -f --msg-filter 'sed "s/old text/new text/"' HEAD~10..HEAD

# 全履歴を変更
git filter-branch -f --msg-filter 'sed "s/old text/new text/"' -- --all

# リモートに強制プッシュ
git push -f origin main
```

### 注意点
- `filter-branch`は履歴を書き換えるため、チームでの使用には注意
- `.git/refs/original/`が残る場合は削除: `rm -rf .git/refs/original`

## 開発環境

### ポート管理
- バックエンド: 7071
- フロントエンド: 3000-3004（自動的に次のポートを試行）

### 再起動コマンド
```bash
# バックエンド
lsof -ti:7071 | xargs kill -9 2>/dev/null
cd backend && func start --port 7071

# フロントエンド
lsof -ti:3000 | xargs kill -9 2>/dev/null
cd frontend && npm run dev
```

## トラブルシューティング

### Fast Refreshの無限ループ
**原因**: 編集が多すぎて自動リロードが繰り返される

**解決策**:
```bash
cd frontend && rm -rf .next && npm run dev
```

### 変更が反映されない
1. ブラウザのキャッシュをクリア（Ctrl+Shift+R）
2. `.next`フォルダを削除して再起動
3. ターミナルを確認してコンパイルエラーがないか確認

### Vega-Liteのエラー
- `spec`がnullでないか確認
- `spec.data.values`が存在するか確認
- コンソールログで仕様を出力: `console.log('Vega-Lite Spec:', JSON.stringify(spec, null, 2))`

## ベストプラクティス

1. **チャート**: Snowflakeから返される仕様をそのまま使用
2. **テーブル**: `text_to_sql`の結果を自動的にMarkdownテーブルに変換
3. **スタイリング**: 最小限の余白で詰めた表示
4. **改行**: 過剰な改行は正規表現で削除
5. **コミットメッセージ**: 日本語で明確に記述
6. **デバッグ**: コンソールログを活用

## 参考情報

### 使用パッケージ
- `vega-embed`: 7.1.0
- `react-markdown`: latest
- `remark-gfm`: latest (テーブルサポート)
- `rehype-mermaid`: latest (ダイアグラム)
- `playwright`: latest (Mermaid依存)

### Snowflake設定
- Account: PGPALAB-IY16795
- Database: GBPS253YS_DB
- Schema: APP_PRODUCTION
- Warehouse: GBPS253YS_WH
- Agent: SNOWFLAKE_DEMO_AGENT
- Role: GBPS253YS_API_ROLE
