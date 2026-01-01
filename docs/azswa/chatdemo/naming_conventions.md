# Azure Static Web Apps (Next.js) 命名規則

## 概要
本ドキュメントは、Azure Static Web Apps（Next.js + TypeScript）プロジェクトにおける命名規則を定義します。一貫性のある命名により、コードの可読性と保守性が向上します。

---

## TypeScript / JavaScript 命名規則

### ファイル・ディレクトリ（File / Directory）
- **形式**: `lowercase-with-hyphens` または `camelCase`
- **Next.js特有**: `pages/` ディレクトリはルーティングに直結
- **例**:
  ```
  pages/
  ├── index.tsx              # トップページ（/）
  ├── _app.tsx              # アプリケーションラッパー
  ├── _document.tsx         # HTMLドキュメント
  ├── chat.tsx              # チャットページ（/chat）
  └── about.tsx             # アバウトページ（/about）
  
  components/
  ├── ChatMessage.tsx       # チャットメッセージコンポーネント
  ├── MessageInput.tsx      # メッセージ入力コンポーネント
  ├── VegaChart.tsx         # Vegaチャートコンポーネント
  └── ToolDetails.tsx       # ツール詳細コンポーネント
  
  styles/
  ├── globals.css           # グローバルスタイル
  ├── Home.module.css       # Homeページモジュールスタイル
  └── Chat.module.css       # Chatページモジュールスタイル
  
  utils/
  ├── api-client.ts         # APIクライアント
  ├── formatters.ts         # フォーマッター
  └── validators.ts         # バリデーター
  ```

### コンポーネント（Component）
- **形式**: `PascalCase`
- **ファイル名**: コンポーネント名と一致
- **例**:
  ```tsx
  // components/ChatMessage.tsx
  export default function ChatMessage({ message }: ChatMessageProps) {
    return <div>{message}</div>
  }
  
  // components/VegaChart.tsx
  export function VegaChart({ spec }: VegaChartProps) {
    return <div ref={containerRef} />
  }
  
  // components/MessageInput.tsx
  export default function MessageInput({ onSend }: MessageInputProps) {
    return <input />
  }
  ```

### 関数（Function）
- **形式**: `camelCase`
- **動詞始まり推奨**
- **例**:
  ```tsx
  // 良い例
  function handleSubmit(event: FormEvent) { }
  function fetchMessages() { }
  function formatTimestamp(date: Date) { }
  function validateInput(value: string) { }
  async function sendMessage(text: string) { }
  
  // 悪い例
  function Submit() { }           // PascalCase（関数はcamelCase）
  function get_messages() { }     // snake_case（JSではcamelCase）
  function msg() { }              // 略語で意味不明
  ```

### 変数・定数（Variable / Constant）
- **形式**: 
  - 変数: `camelCase`
  - 定数: `UPPERCASE_WITH_UNDERSCORES` または `camelCase`
- **例**:
  ```tsx
  // 変数
  const userName = "Alice"
  const messageList = []
  const isLoading = false
  const apiEndpoint = "https://..."
  
  // 定数（設定値）
  const API_BASE_URL = "https://api.example.com"
  const MAX_MESSAGE_LENGTH = 5000
  const DEFAULT_TIMEOUT = 3000
  
  // 定数（enumライク）
  const MessageRole = {
    USER: 'user',
    ASSISTANT: 'assistant',
    SYSTEM: 'system'
  } as const
  ```

### インターフェース・型（Interface / Type）
- **形式**: `PascalCase`
- **プレフィックス**: `I` は使用しない（TypeScript推奨）
- **例**:
  ```tsx
  // 良い例
  interface Message {
    user_id: string
    message: string
    ai_response?: string
    timestamp: string
  }
  
  interface ChatMessageProps {
    message: Message
    onDelete?: (id: string) => void
  }
  
  type ApiResponse<T> = {
    status: 'success' | 'error'
    data?: T
    error?: string
  }
  
  // 悪い例
  interface IMessage { }          // Iプレフィックス不要
  interface messageType { }       // camelCase（PascalCase推奨）
  type response = { }             // lowercase（PascalCase推奨）
  ```

### React Hooks
- **形式**: `use` プレフィックス + `PascalCase`
- **例**:
  ```tsx
  // 良い例
  function useMessages() {
    const [messages, setMessages] = useState<Message[]>([])
    return { messages, setMessages }
  }
  
  function useChatStream(endpoint: string) {
    // ストリーミングロジック
  }
  
  function useDebounce<T>(value: T, delay: number) {
    // デバウンスロジック
  }
  
  // 悪い例
  function getMessages() { }      // useプレフィックスなし
  function UseMessages() { }      // 関数名がPascalCase
  ```

### イベントハンドラー
- **形式**: `handle` または `on` プレフィックス + `動詞` + `名詞`
- **例**:
  ```tsx
  // 良い例
  function handleSubmit(event: FormEvent) { }
  function handleMessageSend(text: string) { }
  function handleInputChange(event: ChangeEvent) { }
  function onMessageReceived(message: Message) { }
  
  // Propsとして渡す場合
  interface MessageInputProps {
    onSend: (text: string) => void
    onChange?: (value: string) => void
    onFocus?: () => void
  }
  ```

---

## CSS / スタイリング命名規則

### CSSモジュール（CSS Modules）
- **ファイル名**: `{ComponentName}.module.css`
- **クラス名**: `camelCase`
- **例**:
  ```css
  /* Home.module.css */
  .container {
    padding: 2rem;
  }
  
  .messageList {
    display: flex;
    flex-direction: column;
  }
  
  .messageItem {
    margin-bottom: 1rem;
  }
  
  .primaryButton {
    background-color: blue;
  }
  ```
  
  ```tsx
  // 使用例
  import styles from '@/styles/Home.module.css'
  
  <div className={styles.container}>
    <ul className={styles.messageList}>
      <li className={styles.messageItem}>...</li>
    </ul>
  </div>
  ```

### グローバルCSS
- **ファイル名**: `globals.css`
- **クラス名**: `kebab-case`
- **例**:
  ```css
  /* globals.css */
  .btn-primary {
    background-color: blue;
  }
  
  .message-container {
    padding: 1rem;
  }
  
  .text-center {
    text-align: center;
  }
  ```

---

## 環境変数（Environment Variables）

### 命名規則
- **形式**: `NEXT_PUBLIC_` プレフィックス（ブラウザ公開用）
- **それ以外**: `UPPERCASE_WITH_UNDERSCORES`（サーバーサイドのみ）
- **例**:
  ```bash
  # ブラウザで利用可能（NEXT_PUBLIC_必須）
  NEXT_PUBLIC_API_BASE_URL=https://api.example.com
  NEXT_PUBLIC_API_TIMEOUT=5000
  NEXT_PUBLIC_ENABLE_DEBUG=false
  
  # サーバーサイドのみ
  API_SECRET_KEY=secret123
  DATABASE_URL=postgres://...
  ```

### .env.local構造
```bash
# API設定
NEXT_PUBLIC_API_BASE_URL=http://localhost:7071/api
NEXT_PUBLIC_API_TIMEOUT=30000

# 機能フラグ
NEXT_PUBLIC_ENABLE_STREAMING=true
NEXT_PUBLIC_ENABLE_CHARTS=true

# デバッグ
NEXT_PUBLIC_DEBUG_MODE=false
```

---

## ディレクトリ構造規則

```
app/azswa/chatdemo/
├── pages/                      # Next.jsページ（ルーティング）
│   ├── _app.tsx               # アプリケーションラッパー
│   ├── _document.tsx          # HTMLドキュメント
│   ├── index.tsx              # トップページ（/）
│   └── api/                   # API Routes（オプション）
│       └── hello.ts
├── components/                 # 再利用可能コンポーネント
│   ├── ChatMessage.tsx
│   ├── MessageInput.tsx
│   ├── VegaChart.tsx
│   └── ToolDetails.tsx
├── hooks/                      # カスタムフック
│   ├── useMessages.ts
│   ├── useChatStream.ts
│   └── useDebounce.ts
├── utils/                      # ユーティリティ関数
│   ├── api-client.ts
│   ├── formatters.ts
│   └── validators.ts
├── types/                      # 型定義
│   ├── message.ts
│   └── api.ts
├── styles/                     # スタイル
│   ├── globals.css
│   ├── Home.module.css
│   └── Chat.module.css
├── public/                     # 静的ファイル
│   ├── favicon.ico
│   └── images/
├── .env.local                  # 環境変数（Git管理外）
├── .env.local.example          # 環境変数テンプレート
├── next.config.js              # Next.js設定
├── tsconfig.json               # TypeScript設定
└── package.json                # 依存関係
```

---

## API クライアント命名規則

### APIエンドポイント関数
- **形式**: `{HTTP動詞}{リソース名}`
- **例**:
  ```tsx
  // utils/api-client.ts
  
  // 良い例
  export async function postMessage(message: string): Promise<ApiResponse> { }
  export async function getMessages(limit?: number): Promise<Message[]> { }
  export async function deleteMessage(id: string): Promise<void> { }
  export async function updateMessage(id: string, content: string): Promise<Message> { }
  
  // 悪い例
  export async function sendMsg(msg: string) { }      // 略語
  export async function get(limit: number) { }        // 不明確
  export async function api_post_message() { }        // snake_case
  ```

### API レスポンス型
```tsx
// types/api.ts
export interface ApiResponse<T = any> {
  status: 'success' | 'error'
  message?: string
  data?: T
  timestamp?: string
}

export interface MessageResponse extends ApiResponse<Message[]> {
  recent_messages: Message[]
}
```

---

## テスト命名規則

### テストファイル
- **形式**: `{ComponentName}.test.tsx` または `{fileName}.spec.ts`
- **例**:
  ```
  __tests__/
  ├── components/
  │   ├── ChatMessage.test.tsx
  │   ├── VegaChart.test.tsx
  │   └── MessageInput.test.tsx
  ├── utils/
  │   ├── api-client.test.ts
  │   └── formatters.test.ts
  └── pages/
      └── index.test.tsx
  ```

### テストケース
- **形式**: `describe` + `it/test`
- **例**:
  ```tsx
  describe('ChatMessage', () => {
    it('renders message text correctly', () => {
      // テスト
    })
    
    it('displays timestamp in correct format', () => {
      // テスト
    })
    
    it('handles missing ai_response gracefully', () => {
      // テスト
    })
  })
  
  describe('API Client', () => {
    test('postMessage sends correct payload', async () => {
      // テスト
    })
    
    test('getMessages returns array of messages', async () => {
      // テスト
    })
  })
  ```

---

## 禁止事項

### ❌ 避けるべき命名
```tsx
// 悪い例
function Msg() { }                      // 略語
const usr_name = "Alice"                // snake_case（JSではcamelCase）
interface IMessageProps { }             // Iプレフィックス不要
const Component1 = () => { }            // 意味不明な数字
function getData() { }                  // 汎用的すぎる名前
```

### ❌ 避けるべきパターン
- デフォルトエクスポートの乱用（名前付きエクスポート推奨）
- `any` 型の多用（適切な型定義）
- グローバル変数の使用
- 過度に長いコンポーネント名

---

## ベストプラクティス

### ✅ 推奨パターン

#### 型定義の活用
```tsx
// types/message.ts
export interface Message {
  user_id: string
  message: string
  ai_response?: string
  timestamp: string
  progress?: string[]
  tool_logs?: string[]
  isComplete?: boolean
}

export type MessageRole = 'user' | 'assistant' | 'system'

export interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
}
```

#### Props型定義
```tsx
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
  // コンポーネント実装
}
```

#### カスタムフック
```tsx
// hooks/useMessages.ts
export function useMessages() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMessages = async () => {
    setIsLoading(true)
    try {
      const data = await getMessages()
      setMessages(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました')
    } finally {
      setIsLoading(false)
    }
  }

  return { messages, isLoading, error, fetchMessages }
}
```

#### エラーハンドリング
```tsx
try {
  const response = await postMessage(text)
  if (response.status === 'success') {
    setMessages(response.data || [])
  } else {
    throw new Error(response.message || '送信に失敗しました')
  }
} catch (error) {
  console.error('Message send error:', error)
  setError(error instanceof Error ? error.message : '予期しないエラー')
}
```

---

## Markdown / ドキュメント命名規則

### READMEファイル
- **形式**: `README.md` または `{Topic}.md`
- **例**:
  - `README.md` - プロジェクト概要
  - `DEPLOYMENT.md` - デプロイ手順
  - `CONTRIBUTING.md` - コントリビューションガイド

---

## 参考資料

- [Next.js Documentation](https://nextjs.org/docs)
- [TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
