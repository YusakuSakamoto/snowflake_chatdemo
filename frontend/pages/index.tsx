import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
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
  const [userId, setUserId] = useState('anonymous')
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
      user_id: userId,
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
        <h1>Snowflake Chat Demo</h1>
        <div className={styles.userIdInput}>
          <label>ユーザーID: </label>
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="ユーザーIDを入力"
          />
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.messagesContainer}>
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`${styles.message} ${
                msg.user_id === userId ? styles.myMessage : 
                msg.user_id === 'Snowflake AI' ? styles.aiMessage :
                msg.user_id === 'System' ? styles.systemMessage :
                styles.otherMessage
              }`}
            >
              <div className={styles.messageHeader}>
                <span className={styles.userName}>
                  {msg.user_id === 'Snowflake AI' ? '🤖 Snowflake AI' : 
                   msg.user_id === 'System' ? '⚠️ System' : 
                   msg.user_id}
                </span>
                <span className={styles.timestamp}>
                  {new Date(msg.timestamp).toLocaleString('ja-JP')}
                </span>
              </div>
              <div className={styles.messageContent}>
                {msg.message}
                {msg.tool_logs && msg.tool_logs.length > 0 && (
                  <div className={styles.toolLogs}>
                    <small>🔧 使用ツール: {msg.tool_logs.join(', ')}</small>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendMessage} className={styles.inputForm}>
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="メッセージを入力..."
            disabled={loading}
            className={styles.messageInput}
          />
          <button type="submit" disabled={loading} className={styles.sendButton}>
            {loading ? '送信中...' : '送信'}
          </button>
        </form>
      </main>
    </div>
  )
}
