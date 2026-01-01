import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeMermaid from 'rehype-mermaid'
import embed from 'vega-embed'
import styles from '@/styles/Home.module.css'

interface Message {
  user_id: string
  message: string
  ai_response?: string
  timestamp: string
  progress?: string[]
  tool_logs?: string[]
  charts?: any[]
}

// Vega-Liteチャートを描画するコンポーネント
function VegaChart({ spec, index }: { spec: any; index: number }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current && spec) {
      // 既存のチャートをクリア
      containerRef.current.innerHTML = ''
      
      // Y軸のラベルを折り返す処理
      const wrapLabel = (text: string, maxLength: number = 30) => {
        if (text.length <= maxLength) return text
        const parts = []
        for (let i = 0; i < text.length; i += maxLength) {
          parts.push(text.substring(i, i + maxLength))
        }
        return parts.join('\n')
      }
      
      // チャートのサイズを拡大し、Y軸ラベルの設定を調整
      const enlargedSpec = {
        ...spec,
        width: 600,
        height: 600,
        encoding: {
          ...spec.encoding,
          y: {
            ...spec.encoding.y,
            axis: {
              labelLimit: 400,
              labelFontSize: 11,
              labelAlign: 'left',
              labelExpr: 'length(datum.label) > 30 ? substring(datum.label, 0, 30) + "\\n" + substring(datum.label, 30, 60) + (length(datum.label) > 60 ? "\\n" + substring(datum.label, 60) : "") : datum.label'
            }
          }
        },
        config: {
          axisY: {
            labelLimit: 400,
            labelFontSize: 11,
            labelAlign: 'left',
            labelBaseline: 'middle'
          }
        },
        autosize: {
          type: 'fit',
          contains: 'padding'
        }
      }
      
      // チャートを描画
      embed(containerRef.current, enlargedSpec, {
        actions: false,
        renderer: 'svg'
      }).catch(err => {
        console.error('Chart rendering error:', err)
      })
    }
  }, [spec])

  return <div ref={containerRef} className={styles.vegaChart} />
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
        // チャートデータを抽出
        const charts: any[] = []
        if (response.data.tool_details) {
          for (const tool of response.data.tool_details) {
            if (tool.tool_name === 'data_to_chart' && tool.raw?.content) {
              for (const content of tool.raw.content) {
                if (content.json?.charts) {
                  try {
                    const chartSpecs = Array.isArray(content.json.charts) 
                      ? content.json.charts 
                      : [content.json.charts]
                    for (const chartStr of chartSpecs) {
                      if (typeof chartStr === 'string') {
                        charts.push(JSON.parse(chartStr))
                      } else {
                        charts.push(chartStr)
                      }
                    }
                  } catch (e) {
                    console.error('Chart parsing error:', e)
                  }
                }
              }
            }
          }
        }
        
        // AIの回答を追加
        const aiMessage: Message = {
          user_id: 'Snowflake AI',
          message: response.data.answer,
          ai_response: response.data.answer,
          timestamp: new Date().toISOString(),
          progress: response.data.progress,
          tool_logs: response.data.tool_logs,
          charts: charts.length > 0 ? charts : undefined
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
                {msg.charts && msg.charts.length > 0 && (
                  <div className={styles.chartContainer}>
                    {msg.charts.map((chart, chartIndex) => (
                      <div key={chartIndex} className={styles.chart}>
                        <VegaChart spec={chart} index={chartIndex} />
                      </div>
                    ))}
                  </div>
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
