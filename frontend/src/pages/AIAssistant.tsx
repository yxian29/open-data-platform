import { useState, useRef, useEffect } from 'react'
import { Bot, Send, Loader2, Table2, Trash2 } from 'lucide-react'
import { aiChat, getAiHistory } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sql?: string
  rows?: Record<string, unknown>[]
  cypher?: string
  graphResult?: Record<string, unknown>[]
}

interface HistoryEntry {
  role: 'user' | 'assistant'
  content: string
  metadata: { sql?: string | null; cypher?: string | null; graph_result?: Record<string, unknown>[] | null }
  created_at: string
}

const SESSION_KEY = 'ai_session_id'

export default function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | undefined>()
  const bottomRef = useRef<HTMLDivElement>(null)

  // Load persisted session on mount
  useEffect(() => {
    const saved = localStorage.getItem(SESSION_KEY)
    if (!saved) return
    setSessionId(saved)
    getAiHistory(saved)
      .then(res => {
        const history = res.data as HistoryEntry[]
        // Only apply if the user hasn't already sent a new message while we were fetching
        setMessages(prev => {
          if (prev.length > 0) return prev
          return history.map(h => {
            const meta = typeof h.metadata === 'string'
              ? JSON.parse(h.metadata)
              : (h.metadata ?? {})
            return {
              role: h.role,
              content: h.content,
              sql: meta.sql ?? undefined,
              rows: meta.rows ?? undefined,
              cypher: meta.cypher ?? undefined,
              graphResult: meta.graph_result ?? undefined,
            }
          })
        })
      })
      .catch(() => {}) // silently ignore if history unavailable
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const newChat = () => {
    localStorage.removeItem(SESSION_KEY)
    setSessionId(undefined)
    setMessages([])
  }

  const send = async () => {
    const query = input.trim()
    if (!query || loading) return
    setInput('')
    setMessages(m => [...m, { role: 'user', content: query }])
    setLoading(true)
    try {
      const res = await aiChat({ query, session_id: sessionId })
      const data = res.data
      setSessionId(data.session_id)
      localStorage.setItem(SESSION_KEY, data.session_id)
      setMessages(m => [...m, {
        role: 'assistant',
        content: data.answer,
        sql: data.sql,
        rows: data.rows,
        cypher: data.cypher,
        graphResult: data.graph_result,
      }])
    } catch (e: any) {
      setMessages(m => [...m, {
        role: 'assistant',
        content: `Error: ${e?.response?.data?.detail || e.message}`,
      }])
    } finally {
      setLoading(false)
    }
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-4rem)]">
      <div className="flex items-center gap-3 mb-4">
        <Bot className="text-blue-600" size={28} />
        <h1 className="text-2xl font-bold">AI Assistant</h1>
        <span className="text-xs text-gray-400 ml-2">Powered by Claude via local CLI bridge</span>
        {messages.length > 0 && (
          <button
            onClick={newChat}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs border border-red-200 rounded-lg text-red-500 hover:bg-red-50 transition-colors"
          >
            <Trash2 size={13} />
            Clear Chat
          </button>
        )}
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 min-h-0">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-16">
            <Bot size={48} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Ask anything about your data.</p>
            <p className="text-xs mt-1 text-gray-300">Examples: "Show top 5 customers", "Summarise the orders dataset"</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-1' : ''}`}>
              <div className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white border text-gray-800'
              }`}>
                {msg.content}
              </div>

              {msg.sql && (
                <div className="mt-2 bg-gray-900 rounded-lg p-3 text-xs font-mono text-green-300 overflow-x-auto">
                  <div className="text-gray-500 mb-1">Generated SQL</div>
                  {msg.sql}
                </div>
              )}

              {msg.cypher && (
                <div className="mt-2 bg-gray-900 rounded-lg p-3 text-xs font-mono text-cyan-300 overflow-x-auto">
                  <div className="text-gray-500 mb-1">Generated Cypher</div>
                  {msg.cypher}
                </div>
              )}

              {msg.rows && msg.rows.length > 0 && (
                <div className="mt-2 bg-white border rounded-lg overflow-hidden">
                  <div className="flex items-center gap-1 px-3 py-2 border-b bg-gray-50 text-xs text-gray-500">
                    <Table2 size={12} />
                    {msg.rows.length} row{msg.rows.length !== 1 ? 's' : ''}
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          {Object.keys(msg.rows[0]).map(col => (
                            <th key={col} className="text-left px-3 py-2 font-medium text-gray-600 border-b">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {msg.rows.map((row, ri) => (
                          <tr key={ri} className="border-b last:border-0 hover:bg-gray-50">
                            {Object.values(row).map((v, vi) => (
                              <td key={vi} className="px-3 py-2 text-gray-700">
                                {String(v ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {msg.graphResult && msg.graphResult.length > 0 && (
                <div className="mt-2 bg-white border border-cyan-200 rounded-lg overflow-hidden">
                  <div className="flex items-center gap-1 px-3 py-2 border-b bg-cyan-50 text-xs text-cyan-700">
                    <Table2 size={12} />
                    {msg.graphResult.length} result{msg.graphResult.length !== 1 ? 's' : ''}
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-cyan-50">
                        <tr>
                          {Object.keys(msg.graphResult[0]).map(col => (
                            <th key={col} className="text-left px-3 py-2 font-medium text-cyan-800 border-b border-cyan-200">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {msg.graphResult.map((row, ri) => (
                          <tr key={ri} className="border-b border-cyan-100 last:border-0 hover:bg-cyan-50">
                            {Object.values(row).map((v, vi) => (
                              <td key={vi} className="px-3 py-2 text-gray-700">
                                {typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border rounded-2xl px-4 py-3 flex items-center gap-2 text-sm text-gray-400">
              <Loader2 size={14} className="animate-spin" />
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="flex gap-2 items-end">
        <textarea
          className="flex-1 border rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={2}
          placeholder="Ask about your data... (Enter to send, Shift+Enter for newline)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-xl p-3 transition-colors"
        >
          {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
        </button>
      </div>
    </div>
  )
}
