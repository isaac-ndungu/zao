import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { t } from '../i18n'

export default function FarmerChat() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('zao_chat_session'))
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (sessionId) {
      apiFetch(`/api/chat/?session_id=${sessionId}`).then(async (res) => {
        if (res.ok) {
          const data = await res.json()
          if (data.messages?.length) setMessages(data.messages)
        }
      }).catch(() => {})
    }
  }, [sessionId])

  const sendMessage = async (text) => {
    const msg = text || input
    if (!msg.trim()) return
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setInput('')
    setSending(true)
    try {
      const res = await apiFetch('/api/chat/', {
        method: 'POST',
        body: JSON.stringify({ message: msg, session_id: sessionId }),
      })
      if (!res.ok) throw new Error('Chat failed')
      const data = await res.json()
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id)
        localStorage.setItem('zao_chat_session', data.session_id)
      }
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I had trouble responding. Please try again.' }])
    } finally { setSending(false) }
  }

  const suggestions = [
    { label: t('checkBalance'), icon: 'account_balance' },
    { label: t('nextPayment'), icon: 'calendar_month' },
    { label: t('howDisputes'), icon: 'help' },
    { label: t('contactCoop'), icon: 'call' },
  ]

  return (
    <div className="flex flex-col h-[calc(100vh-100px)]">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate('/farmer/dashboard')} aria-label="Back to dashboard" className="p-1">
          <span className="material-symbols-outlined">arrow_back</span>
        </button>
        <div className="w-9 h-9 rounded-full bg-info-container flex items-center justify-center">
          <span className="material-symbols-outlined text-info text-lg">smart_toy</span>
        </div>
        <div>
          <p className="font-semibold text-sm">Zao AI Assistant</p>
          <p className="text-xs text-on-surface-variant">Ask me anything</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pb-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <p className="text-sm text-on-surface-variant mb-4">How can I help you today?</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {suggestions.map((s) => (
                <button key={s.label} onClick={() => sendMessage(s.label)} className="inline-flex items-center px-4 py-2 rounded-full border-2 border-outline-variant bg-surface-container text-sm whitespace-nowrap min-h-[36px] active:bg-primary-container active:border-primary gap-1.5">
                  <span className="material-symbols-outlined text-sm">{s.icon}</span>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'bg-primary text-on-primary rounded-[18px_18px_4px_18px] px-4 py-3 max-w-[80%] self-end text-sm leading-relaxed' : 'bg-surface-container border border-outline-variant rounded-[18px_18px_18px_4px] px-4 py-3 max-w-[80%] self-start text-sm leading-relaxed'}>
            {m.content}
          </div>
        ))}
        {sending && (
          <div className="bg-surface-container border border-outline-variant rounded-[18px_18px_18px_4px] px-4 py-3 max-w-[80%] self-start text-sm leading-relaxed">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-on-surface-variant animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 rounded-full bg-on-surface-variant animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 rounded-full bg-on-surface-variant animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); sendMessage() }} className="flex gap-2 pt-3 border-t border-outline-variant">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t('typeMessage')}
          className="w-full px-3.5 py-3 rounded-xl border-2 border-outline-variant bg-surface text-sm outline-none focus:border-primary min-h-[44px] flex-1"
          disabled={sending}
        />
        <button type="submit" disabled={sending || !input.trim()} className="bg-primary text-on-primary px-4 py-2 rounded-xl text-xs font-semibold min-h-[36px] hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed !px-4">
          <span className="material-symbols-outlined">send</span>
        </button>
      </form>
    </div>
  )
}
