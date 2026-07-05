import { useState, useEffect, useRef } from 'react'
import { useChatAuth } from '../hooks/useChatAuth'
import { getAccessToken } from '../../admin/api/client'

const SESSION_KEY = 'zao_widget_chat_session'

function resolveUrl(url) {
  const base = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
  return url.startsWith('/') ? `${base}${url}` : url
}

async function chatApiFetch(url, options = {}) {
  const adminToken = getAccessToken()
  const farmerToken = localStorage.getItem('zao_farmer_token')
  const token = adminToken || farmerToken

  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  }

  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(resolveUrl(url), config)
  return res
}

export default function ChatWidget() {
  const { isAuthenticated, loading } = useChatAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY))
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (sessionId && isOpen) {
      chatApiFetch(`/api/chat/?session_id=${sessionId}`).then(async (res) => {
        if (res.ok) {
          const data = await res.json()
          if (data.messages?.length) setMessages(data.messages)
        }
      }).catch(() => {})
    }
  }, [isOpen, sessionId])

  if (loading || !isAuthenticated) return null

  const sendMessage = async (text) => {
    const msg = text || input
    if (!msg.trim()) return
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setInput('')
    setSending(true)
    try {
      const res = await chatApiFetch('/api/chat/', {
        method: 'POST',
        body: JSON.stringify({ message: msg, session_id: sessionId }),
      })
      if (!res.ok) throw new Error('Chat failed')
      const data = await res.json()
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id)
        localStorage.setItem(SESSION_KEY, data.session_id)
      }
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I had trouble responding. Please try again.' }])
    } finally { setSending(false) }
  }

  const suggestions = [
    { label: 'Check my balance', icon: 'account_balance' },
    { label: 'When is next payment?', icon: 'calendar_month' },
    { label: 'How do disputes work?', icon: 'help' },
    { label: 'Contact my cooperative', icon: 'call' },
  ]

  return (
    <>
      <style>{`
        @keyframes chatBounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
      `}</style>

      {isOpen ? (
        <div className="fixed bottom-6 right-6 w-80 sm:w-96 h-[500px] max-h-[80vh] bg-surface rounded-2xl shadow-2xl flex flex-col z-50 border border-outline-variant overflow-hidden"
          style={{ maxWidth: 'calc(100vw - 48px)' }}>
          <div className="flex items-center gap-3 px-4 py-3 bg-primary text-on-primary rounded-t-2xl">
            <div className="w-9 h-9 rounded-full bg-on-primary/20 flex items-center justify-center">
              <span className="material-symbols-outlined text-on-primary text-lg">smart_toy</span>
            </div>
            <div className="flex-1">
              <p className="font-semibold text-sm">Zao AI Assistant</p>
              <p className="text-xs text-on-primary/80">Ask me anything</p>
            </div>
            <button onClick={() => setIsOpen(false)} className="p-1 hover:bg-on-primary/10 rounded-full">
              <span className="material-symbols-outlined text-lg">close</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-center py-4">
                <p className="text-sm text-on-surface-variant mb-4">How can I help you today?</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {suggestions.map((s) => (
                    <button key={s.label} onClick={() => sendMessage(s.label)}
                      className="inline-flex items-center px-3 py-1.5 rounded-full border border-outline-variant bg-surface-container text-xs whitespace-nowrap hover:bg-primary-container hover:border-primary gap-1.5 transition-colors">
                      <span className="material-symbols-outlined text-sm">{s.icon}</span>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i}
                className={m.role === 'user'
                  ? 'bg-primary text-on-primary rounded-[18px_18px_4px_18px] px-4 py-2.5 max-w-[85%] self-end text-sm leading-relaxed'
                  : 'bg-surface-container border border-outline-variant rounded-[18px_18px_18px_4px] px-4 py-2.5 max-w-[85%] self-start text-sm leading-relaxed'}>
                {m.content}
              </div>
            ))}
            {sending && (
              <div className="bg-surface-container border border-outline-variant rounded-[18px_18px_18px_4px] px-4 py-2.5 max-w-[85%] self-start text-sm">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-on-surface-variant animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-on-surface-variant animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-on-surface-variant animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={(e) => { e.preventDefault(); sendMessage() }} className="flex gap-2 p-3 border-t border-outline-variant">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              className="flex-1 px-3 py-2.5 rounded-xl border-2 border-outline-variant bg-background text-sm outline-none focus:border-primary min-h-[44px]"
              disabled={sending}
            />
            <button type="submit" disabled={sending || !input.trim()}
              className="bg-primary text-on-primary px-3 py-2 rounded-xl min-h-[44px] min-w-[44px] flex items-center justify-center hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed">
              <span className="material-symbols-outlined text-sm">send</span>
            </button>
          </form>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-primary text-on-primary rounded-full shadow-lg flex items-center justify-center z-50 hover:bg-primary-container hover:text-primary transition-colors"
          aria-label="Open chat"
        >
          <span className="material-symbols-outlined text-2xl">chat</span>
        </button>
      )}
    </>
  )
}