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

// ── Dynamic suggestion pools ──────────────────────────
const SUGGESTION_POOLS: Record<string, string[]> = {
  default: [
    '📡 Mã nào Kronos MUA?',
    '🔥 Mã nào Kronos STRONG BUY?',
    '🏦 Cổ phiếu ngành ngân hàng',
    '🏆 Top mã AIFIA rating cao',
    '💵 Cổ phiếu P/E thấp',
    '🏭 Cổ phiếu ngành bất động sản',
    '📈 Mã nào tăng giá nhất?',
    '🔍 Mã nào mới AI chấm điểm?',
    '💼 Cổ phiếu ngành thép',
    '🛒 Cổ phiếu ngành bán lẻ',
    '⚡ Mã Kronos khuyến nghị?',
    '📊 Cổ phiếu thanh khoản cao',
    '📉 Mã nào giảm mạnh?',
    '💊 Cổ phiếu ngành dược',
    '🏗️ Cổ phiếu ngành xây dựng',
    '🔋 Cổ phiếu ngành năng lượng',
  ],
  mua_buy: [
    '📡 Mã Kronos BUY khác?',
    '⭐ Top 5 Kronos mạnh nhất?',
    '🏆 Mã AIFIA rating cao nhất?',
    '💵 P/E của mã này?',
    '📈 Kronos BUY ngành nào?',
    '🔥 Mã STRONG BUY mọi ngành?',
    '📡 Lọc mã BUY theo sàn?',
    '⚡ BUY + rating > 70?',
  ],
  strong_buy: [
    '🔥 STRONG BUY toàn bộ?',
    '📡 Tín hiệu MUA mới nhất?',
    '🏆 TOP STRONG BUY hôm nay?',
    '⚡ Cổ phiếu nóng nhất?',
    '📈 STRONG BUY ngành nào?',
    '💀 Có mã nào STRONG SELL?',
    '🔥 Lọc STRONG BUY riêng HOSE?',
    '📊 STRONG BUY + thanh khoản?',
  ],
  sell: [
    '⚠️ Mã nào SELL?',
    '💀 STRONG SELL nào?',
    '📊 Kronos cảnh báo?',
    '🔍 Mã rủi ro cao?',
    '🏦 Ngành nào nhiều SELL?',
    '📉 Mã giảm nhiều nhất?',
    '⚠️ SELL + rating thấp?',
    '💀 TOP 5 STRONG SELL?',
  ],
  bank: [
    '🏦 Tất cả ngân hàng?',
    '📊 Ngân hàng nào P/E thấp?',
    '⭐ Rating ngân hàng cao nhất?',
    '📈 Ngân hàng tăng nhiều?',
    '💵 Cổ tức ngân hàng?',
    '🔄 Ngân hàng Kronos BUY?',
    '🏦 So sánh các ngân hàng?',
    '📉 Ngân hàng giảm?',
  ],
  rating: [
    '🏆 Top 10 rating cao nhất?',
    '⭐ Rating thấp nhất?',
    '📊 So sánh rating theo ngành?',
    '💵 Rating cao + P/E thấp?',
    '🔍 Mã rating tăng gần đây?',
    '🔥 Cổ phiếu rating 80+?',
    '⭐ Rating 90+ có mã nào?',
    '📈 Rating + Kronos cùng chiều?',
  ],
  pe: [
    '💵 P/E dưới 10 những mã nào?',
    '📊 P/E theo từng ngành?',
    '⭐ P/E thấp + rating cao?',
    '🏦 P/E ngành ngân hàng?',
    '📈 P/E thấp nhất thị trường?',
    '🔄 Cổ phiếu P/E hấp dẫn?',
    '💵 P/E bao nhiêu là tốt?',
    '📊 Lọc mã P/E > 0?',
  ],
  price_up: [
    '📈 Mã tăng giá nhiều nhất?',
    '🔥 Top mã tăng hôm nay?',
    '📊 Ngành nào tăng mạnh?',
    '💵 Mã tăng + P/E thấp?',
    '📈 Mã tăng + Kronos BUY?',
    '🏆 TOP 10 tăng giá?',
    '📈 Cổ phiếu tăng đều?',
    '⚡ Mã nóng nhất hôm nay?',
  ],
  industry: [
    '🏭 Cổ phiếu ngành bất động sản?',
    '🛒 Cổ phiếu ngành bán lẻ?',
    '💼 Cổ phiếu ngành thép?',
    '🔋 Cổ phiếu ngành năng lượng?',
    '💊 Cổ phiếu ngành dược?',
    '🏗️ Cổ phiếu ngành xây dựng?',
    '📡 Cổ phiếu ngành công nghệ?',
    '🚢 Cổ phiếu ngành vận tải?',
  ],
}

// Pick 6 suggestions from a pool, cycling through them
function pickSuggestions(pool: string[], cycle: number): string[] {
  const N = 6
  const start = (cycle * N) % pool.length
  const result: string[] = []
  for (let i = 0; i < N; i++) {
    result.push(pool[(start + i) % pool.length])
  }
  return result
}

function detectPool(query: string): string[] {
  const q = query.toLowerCase()
  if (q.includes('strong_buy') || q.includes('strong buy') || q.includes('mua mạnh')) return SUGGESTION_POOLS.strong_buy
  if (q.includes('bán') || q.includes('sell') || q.includes('strong_sell') || q.includes('strong sell') || q.includes('cảnh báo') || q.includes('rủi ro')) return SUGGESTION_POOLS.sell
  if (q.includes('mua') || q.includes('buy') || q.includes('khuyến nghị') || q.includes('tín hiệu') || q.includes('kronos mua')) return SUGGESTION_POOLS.mua_buy
  if (q.includes('ngân hàng') || q.includes('bank') || q.includes('bidv') || q.includes('vcb') || q.includes('ctg')) return SUGGESTION_POOLS.bank
  if (q.includes('rating') || q.includes('điểm') || q.includes('chấm') || q.includes('aifia rating') || q.includes('xếp hạng')) return SUGGESTION_POOLS.rating
  if (q.includes('pe') || q.includes('p/e') || q.includes('p e')) return SUGGESTION_POOLS.pe
  if (q.includes('tăng') || q.includes('giá') || q.includes('up') || q.includes('tốt nhất') || q.includes('nóng')) return SUGGESTION_POOLS.price_up
  if (q.includes('ngành') || q.includes('industry') || q.includes('bất động sản') || q.includes('thép') || q.includes('bán lẻ') || q.includes('dược') || q.includes('năng lượng') || q.includes('xây dựng') || q.includes('công nghệ') || q.includes('vận tải')) return SUGGESTION_POOLS.industry
  return SUGGESTION_POOLS.default
}

export default function ChatBot({ onResultsChange }: ChatBotProps) {
  const router = useRouter()
  const [input, setInput] = useState('')
  const [state, setState] = useState<ChatState>({
    messages: [],
    companies: [],
    loading: false,
    hasQueried: false,
  })
  const [suggestionsExpanded, setSuggestionsExpanded] = useState(true)
  const [suggestionCycle, setSuggestionCycle] = useState(0)
  const [suggestions, setSuggestions] = useState(() => pickSuggestions(SUGGESTION_POOLS.default, 0))
  const resultsRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const lastQueryRef = useRef('')
  const headerRef = useRef<HTMLDivElement>(null)

  // Auto-collapse suggestions on scroll
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 60) {
        setSuggestionsExpanded(false)
      } else {
        setSuggestionsExpanded(true)
      }
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

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

      // Rotate suggestions based on the query topic
      const pool = detectPool(q)
      setSuggestionCycle(prev => {
        const next = prev + 1
        setSuggestions(pickSuggestions(pool, next))
        return next
      })
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
    // Reset suggestions to default
    setSuggestionCycle(0)
    setSuggestions(pickSuggestions(SUGGESTION_POOLS.default, 0))
    setSuggestionsExpanded(true)
  }

  return (
    <div className="border-b bg-white shadow-sm" ref={headerRef}>
      {/* Input area */}
      <div className="max-w-7xl mx-auto px-4 pb-3 pt-1">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400 pointer-events-none">💬</span>
            <input
              ref={inputRef}
              type="text"
              placeholder="Hỏi AI về cổ phiếu… (vd: 'mã nào kronos mua?')"
              className="w-full pl-9 pr-10 py-2.5 border border-blue-200 rounded-xl bg-blue-50/30 text-base md:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={state.loading}
            />
            {/* Clear button inside input */}
            {state.hasQueried && (
              <button
                onClick={clearChat}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-full text-sm transition-colors"
                title="Xoá & quay lại danh sách"
                tabIndex={-1}
              >
                ✕
              </button>
            )}
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
        </div>

        {/* Suggestions — collapsible, auto-hide on scroll */}
        {!state.hasQueried && (
          <div className="mt-2">
            <div
              className={`flex flex-wrap gap-1.5 overflow-hidden transition-all duration-200 ${
                suggestionsExpanded ? 'max-h-[80px]' : 'max-h-0'
              }`}
            >
              {suggestions.map((s, i) => (
                <button
                  key={`${suggestionCycle}-${i}`}
                  onClick={() => handleSubmit(s)}
                  className="text-xs px-2.5 py-1.5 bg-gray-100 hover:bg-blue-50 hover:text-blue-700 rounded-lg text-gray-500 transition-colors whitespace-nowrap"
                >
                  {s}
                </button>
              ))}
            </div>
            {!suggestionsExpanded && (
              <button
                onClick={() => setSuggestionsExpanded(true)}
                className="text-xs text-blue-500 hover:text-blue-700 mt-1 transition-colors"
              >
                📋 Xem gợi ý
              </button>
            )}
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
                      onMouseEnter={() => router.prefetch(`/company/${c.symbol}`)}
                      className="text-left bg-white rounded-xl px-3 py-2.5 shadow-sm border border-gray-200 transition-all hover:shadow-md hover:border-blue-400 active:scale-[0.98]"
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-sm text-blue-700">{c.symbol}</span>
                        {sig && (
                          <span className={`ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded ${sig.bg} ${sig.color}`}>
                            {sig.icon}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 truncate">{c.industry || '—'}</div>
                      <div className="flex items-center gap-2 mt-0.5">
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
