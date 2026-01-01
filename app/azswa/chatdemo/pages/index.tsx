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
  tool_details?: any[]
  charts?: any[]
  isComplete?: boolean
}

// Vega-Liteチャートを描画するコンポーネント
function VegaChart({ spec, index }: { spec: any; index: number }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current && spec) {
      // 既存のチャートをクリア
      containerRef.current.innerHTML = ''
      
      // チャートを描画
      embed(containerRef.current, spec, {
        actions: false,
        renderer: 'svg'
      }).catch(err => {
        console.error('Chart rendering error:', err)
      })
    }
  }, [spec])

  return <div ref={containerRef} className={styles.vegaChart} />
}

// プログレス情報とツール詳細を表示するコンポーネント
function ToolDetails({ progress, tool_logs, tool_details, isComplete }: { 
  progress?: string[], 
  tool_logs?: string[], 
  tool_details?: any[],
  isComplete?: boolean 
}) {
  const [isExpanded, setIsExpanded] = useState(!isComplete)

  if (!progress && !tool_logs && !tool_details) return null

  return (
    <div className={styles.toolDetailsContainer}>
      <button 
        className={styles.toolDetailsToggle}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span>{isExpanded ? '▼' : '▶'}</span>
        <span>実行詳細 ({progress?.length || 0}ステップ, {tool_details?.length || 0}ツール)</span>
      </button>
      
      {isExpanded && (
        <div className={styles.toolDetailsContent}>
          {/* プログレス表示（Markdownでレンダリング） */}
          {progress && progress.length > 0 && (
            <div className={styles.progressSection}>
              <h4>📋 実行ステップ</h4>
              <ol className={styles.progressList}>
                {progress.map((step, index) => (
                  <li key={index}>
                    <div className={styles.progressMarkdown}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {step}
                      </ReactMarkdown>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}
          
          {/* ツール詳細表示 */}
          {tool_details && tool_details.length > 0 && (
            <div className={styles.toolSection}>
              <h4>🔧 使用ツール詳細</h4>
              {tool_details.map((tool, index) => (
                <div key={index} className={styles.toolItem}>
                  <div className={styles.toolHeader}>
                    <span className={styles.toolName}>
                      {index + 1}. {tool.tool_name}
                    </span>
                    <span className={`${styles.toolStatus} ${styles[tool.status]}`}>
                      {tool.status === 'success' ? '✓' : '✗'} {tool.status}
                    </span>
                  </div>
                  
                  {tool.elapsed_ms && (
                    <div className={styles.toolElapsed}>
                      ⏱️ {tool.elapsed_ms}ms
                    </div>
                  )}
                  
                  {/* 入力情報を詳細表示 */}
                  {tool.input && Object.keys(tool.input).length > 0 && (
                    <div className={styles.toolInputSection}>
                      <div className={styles.sectionLabel}>📥 入力:</div>
                      {tool.input.sql ? (
                        <div className={styles.sqlBlock}>
                          <pre className={styles.sqlCode}>{tool.input.sql}</pre>
                        </div>
                      ) : (
                        <pre className={styles.jsonCode}>
                          {JSON.stringify(tool.input, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                  
                  {/* 出力情報を詳細表示 */}
                  {tool.output && Object.keys(tool.output).length > 0 && (
                    <div className={styles.toolOutputSection}>
                      <div className={styles.sectionLabel}>📤 出力:</div>
                      {tool.output.data && Array.isArray(tool.output.data) && tool.output.data.length > 0 ? (
                        <div className={styles.dataPreview}>
                          {tool.output.data.length}行のデータ（先頭{Math.min(3, tool.output.data.length)}行を表示）
                          <pre className={styles.jsonCode}>
                            {JSON.stringify(tool.output.data.slice(0, 3), null, 2)}
                          </pre>
                          {tool.output.data.length > 3 && (
                            <div className={styles.moreData}>...残り{tool.output.data.length - 3}行</div>
                          )}
                        </div>
                      ) : (
                        <pre className={styles.jsonCode}>
                          {JSON.stringify(tool.output, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                  
                  {/* raw情報を表示 */}
                  {tool.raw && (
                    <div className={styles.toolRawSection}>
                      <div className={styles.sectionLabel}>🔍 Raw:</div>
                      <pre className={styles.jsonCode}>
                        {JSON.stringify(tool.raw, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {/* ツールログ表示 */}
          {tool_logs && tool_logs.length > 0 && (
            <div className={styles.logsSection}>
              <h4>📝 ログ</h4>
              <pre className={styles.logsPre}>
                {tool_logs.join('\n')}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
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

    // 処理中メッセージを追加
    const processingMessage: Message = {
      user_id: 'Snowflake AI',
      message: '処理中...',
      timestamp: new Date().toISOString(),
      progress: ['🔄 Snowflake Cortex Agentに接続中...'],
      tool_logs: [],
      tool_details: [],
      isComplete: false
    }
    setMessages(prev => [...prev, processingMessage])
    const messageIndex = messages.length + 1 // ユーザーメッセージの次

    try {
      // Snowflake Cortex Agentのストリーミングエンドポイントを使用
      const response = await axios.post(`${API_URL}/chat-stream`, {
        text: currentMessage,
        message: currentMessage
      })
      
      console.log('Snowflake Response:', response.data)
      console.log('Answer text:', response.data.answer)
      console.log('Tool details:', JSON.stringify(response.data.tool_details, null, 2))

      // レスポンスを受け取ったら、処理中メッセージを更新（tool_detailsを表示）
      if (response.data.progress || response.data.tool_details) {
        setMessages(prev => {
          const newMessages = [...prev]
          newMessages[messageIndex] = {
            ...newMessages[messageIndex],
            progress: response.data.progress || [],
            tool_details: response.data.tool_details || [],
            isComplete: false
          }
          return newMessages
        })
      }
      
      if (response.data.ok && response.data.answer) {
        // チャートデータとテーブルデータを抽出
        const charts: any[] = []
        let answerText = response.data.answer
        
        if (response.data.tool_details) {
          for (const tool of response.data.tool_details) {
            // チャートデータの処理
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
            
            // テーブルデータの処理
            if (tool.tool_name === 'text_to_sql') {
              // 複数の場所からデータを取得を試みる
              let tableData = null
              
              // 1. tool.output.data
              if (tool.output?.data && Array.isArray(tool.output.data)) {
                tableData = tool.output.data
              }
              // 2. tool.raw.content[].json.result_set.data
              else if (tool.raw?.content) {
                for (const content of tool.raw.content) {
                  if (content.json?.result_set?.data && Array.isArray(content.json.result_set.data)) {
                    tableData = content.json.result_set.data
                    break
                  }
                }
              }
              
              if (tableData && tableData.length > 0) {
                console.log('テーブルデータを発見:', tableData.length, '行')
                // Markdownテーブルに変換
                const headers = tableData[0]
                const rows = tableData.slice(1)
                
                let markdownTable = '\n\n| ' + headers.join(' | ') + ' |\n'
                markdownTable += '| ' + headers.map(() => '---').join(' | ') + ' |\n'
                
                for (const row of rows) {
                  markdownTable += '| ' + row.join(' | ') + ' |\n'
                }
                
                answerText += markdownTable
              } else {
                console.log('テーブルデータが見つかりません。tool:', JSON.stringify(tool, null, 2))
              }
            }
          }
        }
        
        // AIの回答を追加
        const aiMessage: Message = {
          user_id: 'Snowflake AI',
          message: answerText,
          ai_response: answerText,
          timestamp: new Date().toISOString(),
          progress: response.data.progress,
          tool_logs: response.data.tool_logs,
          tool_details: response.data.tool_details,
          charts: charts.length > 0 ? charts : undefined,
          isComplete: true
        }
        
        // 処理中メッセージを完了メッセージで更新
        setMessages(prev => {
          const newMessages = [...prev]
          newMessages[messageIndex] = aiMessage
          return newMessages
        })
      } else {
        throw new Error('AIからの応答がありません')
      }
    } catch (error) {
      console.error('メッセージの送信に失敗しました:', error)
      
      // 処理中メッセージをエラーメッセージで更新
      const errorMessage: Message = {
        user_id: 'System',
        message: 'エラー: メッセージの送信に失敗しました。Snowflakeへの接続を確認してください。',
        timestamp: new Date().toISOString(),
        isComplete: true
      }
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[messageIndex] = errorMessage
        return newMessages
      })
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
                  <>
                    {/* ツール詳細表示 */}
                    {msg.user_id === 'Snowflake AI' && (
                      <ToolDetails 
                        progress={msg.progress}
                        tool_logs={msg.tool_logs}
                        tool_details={msg.tool_details}
                        isComplete={msg.isComplete}
                      />
                    )}
                    
                    <div className={styles.markdown}>
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeMermaid]}
                      >
                        {msg.message.replace(/\n\s*\n\s*\n/g, '\n\n').trim()}
                      </ReactMarkdown>
                    </div>
                  </>
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
