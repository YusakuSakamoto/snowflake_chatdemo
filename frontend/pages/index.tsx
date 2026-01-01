import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeMermaid from 'rehype-mermaid'
import styles from '@/styles/Home.module.css'

interface Message {
  user_id: string
  message: string
  ai_response?: string
  timestamp: string
  progress?: string[]
  tool_logs?: string[]
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7071/api'

  useEffect(() => {
    fetchMessages()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enterキーのみで送信、Shift+Enterで改行
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(e as any)
    }
  }

  const fetchMessages = async () => {
    try {
      const response = await axios.get(`${API_URL}/messages?limit=50`)
      setMessages(response.data.messages.reverse())
    } catch (error) {
      console.error('メッセージの取得に失敗しました:', error)
    }
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!inputMessage.trim()) return

    setLoading(true)
    
    // ユーザーメッセージを即座に表示
    const userMessage: Message = {
      user_id: 'user',
      message: inputMessage,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    const currentMessage = inputMessage
    setInputMessage('')

    try {
      // Snowflake Cortex Agentのストリーミングエンドポイントを使用
      const response = await axios.post(`${API_URL}/chat-stream`, {
        text: currentMessage,
        message: currentMessage
      })
      
      console.log('Snowflake Response:', response.data)
      
      if (response.data.ok && response.data.answer) {
        // AIの回答を追加
        const aiMessage: Message = {
          user_id: 'Snowflake AI',
          message: response.data.answer,
          ai_response: response.data.answer,
          timestamp: new Date().toISOString(),
          progress: response.data.progress,
          tool_logs: response.data.tool_logs
        }
        setMessages(prev => [...prev, aiMessage])
      } else {
        throw new Error('AIからの応答がありません')
      }
    } catch (error) {
      console.error('メッセージの送信に失敗しました:', error)
      
      // エラーメッセージを表示
      const errorMessage: Message = {
        user_id: 'System',
        message: 'エラー: メッセージの送信に失敗しました。Snowflakeへの接続を確認してください。',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>❄️ Snowflake Chat Demo</h1>
        <p className={styles.subtitle}>Snowflake Cortex Agentに質問してみましょう</p>
      </header>

      <main className={styles.main}>
        <div className={styles.messagesContainer}>
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`${styles.message} ${
                msg.user_id === 'user' ? styles.myMessage : 
                msg.user_id === 'Snowflake AI' ? styles.aiMessage :
                msg.user_id === 'System' ? styles.systemMessage :
                styles.otherMessage
              }`}
            >
              <div className={styles.messageHeader}>
                <span className={styles.userName}>
                  {msg.user_id === 'Snowflake AI' ? '❄️ Snowflake AI' : 
                   msg.user_id === 'System' ? '⚠️ System' : 
                   'あなた'}
                </span>
                <span className={styles.timestamp}>
                  {new Date(msg.timestamp).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className={styles.messageContent}>
                {msg.user_id === 'Snowflake AI' || msg.user_id === 'System' ? (
                  <div className={styles.markdown}>
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeMermaid]}
                    >
                      {msg.message}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div>{msg.message}</div>
                )}
                {msg.tool_logs && msg.tool_logs.length > 0 && (
                  <div className={styles.toolLogs}>
                    <small>🔧 {msg.tool_logs.join(', ')}</small>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendMessage} className={styles.inputForm}>
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="メッセージを入力... (Shift+Enterで改行)"
            disabled={loading}
            className={styles.messageInput}
            rows={3}
          />
          <button type="submit" disabled={loading} className={styles.sendButton}>
            {loading ? '送信中...' : '送信'}
          </button>
        </form>
      </main>
    </div>
  )
}
