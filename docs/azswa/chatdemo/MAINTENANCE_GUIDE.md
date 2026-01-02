# Azure Static Web Apps (Next.js) メンテナンスガイド

## 概要
本ドキュメントは、Azure Static Web Apps（Next.js + TypeScript）プロジェクトのメンテナンス規則と手順を定義します。

---

## 命名規則

詳細は [NAMING_CONVENTIONS_GUIDE.md](NAMING_CONVENTIONS_GUIDE.md) を参照してください。

### 主要ルール
- コンポーネント: `PascalCase`
- 関数: `camelCase`
- 定数: `UPPERCASE_WITH_UNDERSCORES`
- 型・インターフェース: `PascalCase`（`I` プレフィックス不要）
- CSSモジュール: `camelCase`

---

## 開発環境セットアップ

### 1. Node.js環境
```bash
# Node.js 18以上を推奨
node --version  # v18.x.x 以上

# npmまたはyarn
npm --version
```

### 2. 依存関係インストール
```bash
cd app/azswa/chatdemo
npm install
```

### 3. 環境変数設定
```bash
# .env.local.exampleをコピー
cp .env.local.example .env.local

# 必要な環境変数を設定
# NEXT_PUBLIC_API_BASE_URL など
```

### 4. ローカル開発サーバー起動
```bash
# 開発モード（ホットリロード有効）
npm run dev

# ブラウザで確認
# http://localhost:3000
```

---

## プロジェクト構造

```
app/azswa/chatdemo/
├── pages/                      # Next.jsページ
│   ├── _app.tsx               # アプリケーションラッパー
│   ├── _document.tsx          # HTMLドキュメント
│   └── index.tsx              # トップページ
├── components/                 # 再利用可能コンポーネント
├── hooks/                      # カスタムフック
├── utils/                      # ユーティリティ関数
├── types/                      # 型定義
├── styles/                     # スタイル
├── public/                     # 静的ファイル
├── .env.local                  # 環境変数（Git管理外）
├── next.config.js              # Next.js設定
├── tsconfig.json               # TypeScript設定
└── package.json                # 依存関係
```

---

## コーディング規則

### 1. TypeScriptスタイルガイド

#### 型定義を必ず使用
```tsx
// 良い例
interface Message {
  user_id: string
  message: string
  ai_response?: string
  timestamp: string
}

function ChatMessage({ message }: { message: Message }) {
  return <div>{message.message}</div>
}

// 悪い例
function ChatMessage({ message }: any) {  // any禁止
  return <div>{message.message}</div>
}
```

#### Propsの型定義
```tsx
// 良い例
interface ChatMessageProps {
  message: Message
  onDelete?: (id: string) => void
  className?: string
}

export default function ChatMessage({ 
  message, 
  onDelete,
  className 
}: ChatMessageProps) {
  // 実装
}

// 悪い例
export default function ChatMessage(props) {  // 型なし
  // 実装
}
```

### 2. Reactベストプラクティス

#### 関数コンポーネント推奨
```tsx
// 良い例（関数コンポーネント）
export default function MessageList({ messages }: MessageListProps) {
  return (
    <ul>
      {messages.map(msg => (
        <li key={msg.timestamp}>{msg.message}</li>
      ))}
    </ul>
  )
}

// 悪い例（クラスコンポーネント - 非推奨）
class MessageList extends React.Component {
  render() {
    return <ul>...</ul>
  }
}
```

#### Hooks使用ルール
```tsx
// 良い例
function MessageInput() {
  // Hooksはコンポーネントのトップレベルで呼び出す
  const [text, setText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  useEffect(() => {
    // 副作用処理
  }, [])
  
  return <input value={text} onChange={e => setText(e.target.value)} />
}

// 悪い例
function MessageInput() {
  if (condition) {
    const [text, setText] = useState('')  // 条件付きHooks禁止
  }
  
  return <input />
}
```

#### Key属性の適切な使用
```tsx
// 良い例
{messages.map((msg, index) => (
  <ChatMessage 
    key={`${msg.user_id}-${msg.timestamp}`}  // 一意なキー
    message={msg} 
  />
))}

// 悪い例
{messages.map((msg, index) => (
  <ChatMessage 
    key={index}  // インデックスをキーにするのは非推奨
    message={msg} 
  />
))}
```

### 3. 状態管理

#### ローカル状態（useState）
```tsx
function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  // シンプルな状態管理
}
```

#### カスタムフックでロジック分離
```tsx
// hooks/useMessages.ts
export function useMessages() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMessages = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/messages')
      const data = await response.json()
      setMessages(data.messages)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました')
    } finally {
      setIsLoading(false)
    }
  }

  const addMessage = (message: Message) => {
    setMessages(prev => [...prev, message])
  }

  return { messages, isLoading, error, fetchMessages, addMessage }
}

// 使用例
function ChatPage() {
  const { messages, isLoading, error, fetchMessages } = useMessages()
  
  useEffect(() => {
    fetchMessages()
  }, [])
  
  return <div>...</div>
}
```

### 4. スタイリング

#### CSSモジュール使用
```tsx
// styles/Chat.module.css
.container {
  max-width: 1200px;
  margin: 0 auto;
}

.messageList {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

// components/ChatPage.tsx
import styles from '@/styles/Chat.module.css'

export default function ChatPage() {
  return (
    <div className={styles.container}>
      <ul className={styles.messageList}>
        {/* メッセージ一覧 */}
      </ul>
    </div>
  )
}
```

#### 条件付きクラス名
```tsx
import classNames from 'classnames'

<div className={classNames(
  styles.message,
  {
    [styles.userMessage]: message.user_id === currentUserId,
    [styles.aiMessage]: message.ai_response,
    [styles.loading]: isLoading
  }
)} />
```

### 5. APIクライアント

#### 統一されたAPIクライアント
```tsx
// utils/api-client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:7071/api'
const API_TIMEOUT = parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '30000')

export interface ApiResponse<T = any> {
  status: 'success' | 'error'
  message?: string
  data?: T
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT)

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('リクエストがタイムアウトしました')
    }
    throw error
  }
}

export async function postMessage(message: string): Promise<ApiResponse<Message[]>> {
  return apiRequest('/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export async function getMessages(limit: number = 10): Promise<ApiResponse<Message[]>> {
  return apiRequest(`/messages?limit=${limit}`)
}
```

---

## エラーハンドリング

### 1. try-catchパターン
```tsx
async function handleSendMessage() {
  try {
    setIsLoading(true)
    setError(null)
    
    const response = await postMessage(inputText)
    
    if (response.status === 'success') {
      setMessages(response.data || [])
      setInputText('')
    } else {
      throw new Error(response.message || '送信に失敗しました')
    }
  } catch (error) {
    console.error('Message send error:', error)
    setError(error instanceof Error ? error.message : '予期しないエラー')
  } finally {
    setIsLoading(false)
  }
}
```

### 2. エラー境界（Error Boundary）
```tsx
// components/ErrorBoundary.tsx
import React, { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div>
          <h2>エラーが発生しました</h2>
          <p>{this.state.error?.message}</p>
        </div>
      )
    }

    return this.props.children
  }
}

// 使用例
<ErrorBoundary>
  <ChatPage />
</ErrorBoundary>
```

---

## パフォーマンス最適化

### 1. React.memo使用
```tsx
import { memo } from 'react'

interface ChatMessageProps {
  message: Message
}

export const ChatMessage = memo(function ChatMessage({ message }: ChatMessageProps) {
  return (
    <div>
      <p>{message.message}</p>
      <span>{message.timestamp}</span>
    </div>
  )
}, (prevProps, nextProps) => {
  // 再レンダリング判定
  return prevProps.message.timestamp === nextProps.message.timestamp
})
```

### 2. useCallback使用
```tsx
function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  
  // 関数をメモ化して子コンポーネントの再レンダリングを防ぐ
  const handleDeleteMessage = useCallback((id: string) => {
    setMessages(prev => prev.filter(msg => msg.timestamp !== id))
  }, [])
  
  return (
    <div>
      {messages.map(msg => (
        <ChatMessage 
          key={msg.timestamp}
          message={msg}
          onDelete={handleDeleteMessage}
        />
      ))}
    </div>
  )
}
```

### 3. useMemo使用
```tsx
function MessageList({ messages }: { messages: Message[] }) {
  // 重い計算をメモ化
  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
  }, [messages])
  
  return (
    <ul>
      {sortedMessages.map(msg => (
        <li key={msg.timestamp}>{msg.message}</li>
      ))}
    </ul>
  )
}
```

### 4. 動的インポート
```tsx
import dynamic from 'next/dynamic'

// 重いコンポーネントを遅延ロード
const VegaChart = dynamic(() => import('@/components/VegaChart'), {
  loading: () => <p>チャート読込中...</p>,
  ssr: false  // サーバーサイドレンダリング無効化
})

function ChartPage() {
  return <VegaChart spec={chartSpec} />
}
```

---

## テスト規則

### 1. テストライブラリセットアップ
```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom jest
```

### 2. コンポーネントテスト
```tsx
// __tests__/components/ChatMessage.test.tsx
import { render, screen } from '@testing-library/react'
import ChatMessage from '@/components/ChatMessage'

describe('ChatMessage', () => {
  const mockMessage: Message = {
    user_id: 'user1',
    message: 'Hello',
    timestamp: '2026-01-02T12:00:00Z'
  }

  it('renders message text', () => {
    render(<ChatMessage message={mockMessage} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('displays timestamp', () => {
    render(<ChatMessage message={mockMessage} />)
    expect(screen.getByText(/2026-01-02/)).toBeInTheDocument()
  })

  it('handles missing ai_response', () => {
    render(<ChatMessage message={mockMessage} />)
    expect(screen.queryByText(/AI:/)).not.toBeInTheDocument()
  })
})
```

### 3. カスタムフックテスト
```tsx
// __tests__/hooks/useMessages.test.ts
import { renderHook, act } from '@testing-library/react'
import { useMessages } from '@/hooks/useMessages'

describe('useMessages', () => {
  it('initializes with empty messages', () => {
    const { result } = renderHook(() => useMessages())
    expect(result.current.messages).toEqual([])
    expect(result.current.isLoading).toBe(false)
  })

  it('adds message correctly', () => {
    const { result } = renderHook(() => useMessages())
    
    act(() => {
      result.current.addMessage({
        user_id: 'user1',
        message: 'Test',
        timestamp: '2026-01-02T12:00:00Z'
      })
    })
    
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].message).toBe('Test')
  })
})
```

---

## ビルド・デプロイ

### 1. ビルド前チェックリスト
- [ ] すべてのテストが通過
- [ ] TypeScriptエラーなし（`npm run build`）
- [ ] ESLintエラーなし（`npm run lint`）
- [ ] 環境変数が正しく設定されている
- [ ] 本番用APIエンドポイントが設定されている

### 2. ローカルビルド
```bash
# プロダクションビルド
npm run build

# ビルド結果確認
npm run start

# ブラウザで確認（本番モード）
# http://localhost:3000
```

### 3. Azure Static Web Appsへのデプロイ
```bash
# Azure CLIでログイン
az login

# Static Web Appにデプロイ
# GitHub Actionsまたは手動デプロイ
```

### 4. GitHub Actionsによる自動デプロイ
```yaml
# .github/workflows/azure-static-web-apps.yml
name: Azure Static Web Apps CI/CD

on:
  push:
    branches:
      - main
  pull_request:
    types: [opened, synchronize, reopened, closed]
    branches:
      - main

jobs:
  build_and_deploy_job:
    runs-on: ubuntu-latest
    name: Build and Deploy Job
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: true
      
      - name: Build And Deploy
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "/app/azswa/chatdemo"
          api_location: ""
          output_location: ".next"
```

---

## トラブルシューティング

### 1. ビルドエラー
```bash
# TypeScriptエラー
npm run build
# エラーメッセージを確認して型定義を修正

# 依存関係エラー
rm -rf node_modules package-lock.json
npm install
```

### 2. APIリクエストエラー
```tsx
// CORSエラー確認
// バックエンドでCORS設定が必要

// タイムアウトエラー
// NEXT_PUBLIC_API_TIMEOUT を延長

// ネットワークエラー
console.log('API Base URL:', process.env.NEXT_PUBLIC_API_BASE_URL)
```

### 3. スタイルが反映されない
```bash
# CSSモジュールのキャッシュクリア
rm -rf .next
npm run dev
```

---

## Git運用規則

本プロジェクトは統一されたGit運用規則に従います。

詳細は [docs/git/chatdemo/GIT_WORKFLOW.md](../../git/chatdemo/GIT_WORKFLOW.md) を参照してください。

### コミットメッセージ例
```bash
# 良い例
git commit -m "feat: メッセージストリーミング表示機能追加"
git commit -m "fix: チャート描画時のメモリリーク修正"
git commit -m "refactor: APIクライアントをカスタムフックに移行"
git commit -m "style: CSSモジュールのクラス名を統一"

# 悪い例
git commit -m "update"
git commit -m "fix bug"
git commit -m "Add feature"  # 英語（日本語推奨）
```

---

## セキュリティベストプラクティス

### 1. 環境変数管理
```bash
# ❌ 悪い例（コードにハードコード）
const API_URL = "https://api.example.com"

# ✅ 良い例（環境変数使用）
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL
```

### 2. XSS対策
```tsx
// Reactは自動でエスケープするが、dangerouslySetInnerHTMLは避ける

// ❌ 悪い例
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// ✅ 良い例
<div>{userInput}</div>

// Markdown表示にはライブラリ使用
import ReactMarkdown from 'react-markdown'
<ReactMarkdown>{userInput}</ReactMarkdown>
```

### 3. CSRF対策
```tsx
// Azure Static Web Appsは自動でCSRF保護を提供
// カスタムAPIの場合はトークン検証が必要
```

---

## 参考ドキュメント

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [Azure Static Web Apps Documentation](https://learn.microsoft.com/azure/static-web-apps/)
- [命名規則](NAMING_CONVENTIONS_GUIDE.md)
- [Git運用規則](../../git/chatdemo/GIT_WORKFLOW.md)
