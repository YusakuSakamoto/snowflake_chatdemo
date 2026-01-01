import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import styles from '@/styles/Home.module.css'

interface Message {
  user_id: string
  message: string
  timestamp: string
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
    try {
      const response = await axios.post(`${API_URL}/chat`, {
        user_id: userId,
        message: inputMessage
      })
      
      setMessages(response.data.recent_messages.reverse())
      setInputMessage('')
    } catch (error) {
      console.error('メッセージの送信に失敗しました:', error)
      alert('メッセージの送信に失敗しました')
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
                msg.user_id === userId ? styles.myMessage : styles.otherMessage
              }`}
            >
              <div className={styles.messageHeader}>
                <span className={styles.userName}>{msg.user_id}</span>
                <span className={styles.timestamp}>
                  {new Date(msg.timestamp).toLocaleString('ja-JP')}
                </span>
              </div>
              <div className={styles.messageContent}>{msg.message}</div>
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
