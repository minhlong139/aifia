'use client'

import { useRouter } from 'next/navigation'
import { useState, useRef, useEffect, useCallback } from 'react'

// ── Types ──────────────────────────────────────────────
interface ChatCompany {
  symbol: string
  name: string | null
  industry: string | null
  exchange: string | null
  kronosSignal: string | null
  aiRating: number | null
  peRatio: number | null
  priceChange: number | null
}

interface ChatState {
  messages: Array<{ role: 'user' | 'assistant'; text: string }>
  companies: ChatCompany[]
  loading: boolean
  hasQueried: boolean
}

// ── Props ──────────────────────────────────────────────
interface ChatBotProps {
  onResultsChange?: (results: ChatCompany[] | null) => void
}

// ── Kronos signal helper ──────────────────────────────
function signalIcon(signal: string | null): { icon: string; color: string; bg: string; text: string } | null {
  if (!signal) return null
  const map: Record<string, { icon: string; color: string; bg: string; text: string }> = {
    STRONG_BUY:    { icon: '🔥', color: 'text-green-700', bg: 'bg-green-100', text: 'MUA MẠNH' },
    BUY:           { icon: '⚡', color: 'text-green-600', bg: 'bg-green-50', text: 'MUA' },
    NEUTRAL:       { icon: '➖', color: 'text-yellow-700', bg: 'bg-yellow-50', text: 'TRUNG LẬP' },
    SELL:          { icon: '⚠️', color: 'text-red-600', bg: 'bg-red-50', text: 'BÁN' },
    STRONG_SELL:   { icon: '💀', color: 'text-red-700', bg: 'bg-red-100', text: 'BÁN MẠNH' },
  }
  return map[signal] || null
}

function ratingColor(rating: number | null): string {
  if (rating === null) return ''
  if (rating >= 75) return 'text-green-600'
  if (rating >= 60) return 'text-blue-600'
  if (rating >= 45) return 'text-yellow-600'
  return 'text-red-600'
}

function priceChangeColor(pct: number | null): string {
  if (pct === null) return ''
  return pct > 0 ? 'text-green-600' : pct < 0 ? 'text-red-600' : ''
}

// ── Example suggestions ───────────────────────────────
const SUGGESTIONS = [
  '📡 Mã nào Kronos MUA?',
  '🔥 Mã nào Kronos STRONG BUY?',
  '🏦 Cổ phiếu ngành ngân hàng',
  '🏆 Top mã AIFIA rating cao',
  '💵 Cổ phiếu P/E thấp',
  '🏭 Cổ phiếu ngành bất động sản',
]

export default function ChatBot({ onResultsChange }: ChatBotProps) {
  const router = useRouter()
  const [input, setInput] = useState('')
  const [state, setState] = useState<ChatState>({
    messages: [],
    companies: [],
    loading: false,
    hasQueried: false,
  })
  const resultsRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const lastQueryRef = useRef('')

  // Notify parent of results changes
  useEffect(() => {
    onResultsChange?.(state.hasQueried ? state.companies : null)
  }, [state.companies, state.hasQueried, onResultsChange])

  const handleSubmit = useCallback(async (query: string) => {
    const q = query.trim()
    if (!q || state.loading) return

    // Skip if same query was just submitted
    if (q === lastQueryRef.current) return
    lastQueryRef.current = q

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, { role: 'user', text: q }],
      loading: true,
      hasQueried: true,
    }))

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      setState(prev => ({
        messages: [...prev.messages, { role: 'assistant', text: data.answer }],
        companies: data.companies || [],
        loading: false,
        hasQueried: true,
      }))
    } catch {
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, { role: 'assistant', text: '❌ Lỗi kết nối, vui lòng thử lại.' }],
        loading: false,
        hasQueried: true,
      }))
    }

    setInput('')
  }, [state.loading])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSubmit(input)
  }

  const clearChat = () => {
    setState({ messages: [], companies: [], loading: false, hasQueried: false })
    lastQueryRef.current = ''
    setInput('')
    inputRef.current?.focus()
  }

  return (
    <div className="border-b bg-white shadow-sm">
      {/* Input area */}
      <div className="max-w-7xl mx-auto px-4 pb-3 pt-1">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">💬</span>
            <input
              ref={inputRef}
              type="text"
              placeholder="Hỏi AI về cổ phiếu… (vd: 'mã nào kronos mua?')"
              className="w-full pl-9 pr-4 py-2.5 border border-blue-200 rounded-xl bg-blue-50/30 text-base md:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={state.loading}
            />
          </div>
          <button
            onClick={() => handleSubmit(input)}
            disabled={state.loading || !input.trim()}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
          >
            {state.loading ? (
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Đang tra
              </span>
            ) : (
              '🔍 Hỏi'
            )}
          </button>
          {state.hasQueried && (
            <button
              onClick={clearChat}
              className="px-3 py-2.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-xl text-sm transition-colors"
              title="Xoá & quay lại danh sách"
            >
              ✕
            </button>
          )}
        </div>

        {/* Suggestions (only show when no query active) */}
        {!state.hasQueried && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => handleSubmit(s)}
                className="text-xs px-2.5 py-1.5 bg-gray-100 hover:bg-blue-50 hover:text-blue-700 rounded-lg text-gray-500 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Results area — fixed height prevents layout jumping */}
      {state.hasQueried && (
        <div className="max-w-7xl mx-auto px-4 pb-3">
          {/* Chat answer */}
          <div className="mb-3">
            {state.messages.slice(-2).map((msg, i) => (
              <div
                key={i}
                className={`text-sm mb-1 ${
                  msg.role === 'user'
                    ? 'text-gray-400 text-right'
                    : 'text-gray-800 font-medium'
                }`}
              >
                {msg.role === 'user' ? (
                  <span className="inline-block bg-blue-50 text-blue-700 px-3 py-1.5 rounded-xl text-xs">
                    {msg.text}
                  </span>
                ) : (
                  <div className="flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5">🤖</span>
                    <span className="whitespace-pre-wrap text-sm">{msg.text}</span>
                  </div>
                )}
              </div>
            ))}
            {state.loading && (
              <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
                <span className="w-3 h-3 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
                Đang phân tích…
              </div>
            )}
          </div>

          {/* Company results grid — fixed height with overflow scroll */}
          <div
            ref={resultsRef}
            className="overflow-y-auto rounded-xl border border-gray-100 bg-gray-50/50"
            style={{ maxHeight: '420px', minHeight: '120px' }}
          >
            {state.companies.length === 0 && !state.loading ? (
              <div className="flex items-center justify-center h-[120px] text-gray-400 text-sm">
                Không tìm thấy kết quả phù hợp
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 p-3">
                {state.companies.map(c => {
                  const sig = signalIcon(c.kronosSignal)
                  return (
                    <button
                      key={c.symbol}
                      onClick={() => router.push(`/company/${c.symbol}`)}
                      className="text-left bg-white rounded-xl px-3 py-2.5 shadow-sm border border-gray-200 transition-all hover:shadow-md hover:border-blue-400 active:scale-[0.98]"
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full shrink-0 bg-green-400" />
                        <span className="font-bold text-sm text-blue-700">{c.symbol}</span>
                        {sig && (
                          <span className={`ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded ${sig.bg} ${sig.color}`}>
                            {sig.icon}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 truncate pl-4">{c.industry || '—'}</div>
                      <div className="flex items-center gap-2 pl-4 mt-0.5">
                        {c.aiRating !== null && (
                          <span className={`text-[10px] font-semibold ${ratingColor(c.aiRating)}`}>
                            ⭐{Math.round(c.aiRating)}
                          </span>
                        )}
                        {c.peRatio !== null && (
                          <span className="text-[10px] text-gray-400">P/E {c.peRatio.toFixed(1)}</span>
                        )}
                        {c.priceChange !== null && (
                          <span className={`text-[10px] font-medium ${priceChangeColor(c.priceChange)}`}>
                            {c.priceChange > 0 ? '+' : ''}{c.priceChange.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Result count */}
          {!state.loading && state.companies.length > 0 && (
            <div className="text-xs text-gray-400 mt-2 text-center">
              {state.companies.length} mã — Click vào mã để xem chi tiết
            </div>
          )}
        </div>
      )}
    </div>
  )
}
