'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { getCompanies, getDataCoverage, getCompanyHighlights } from '@/lib/supabase'
import ChatBot from '@/components/ChatBot'
import MarketChart from '@/components/MarketChart'

interface Company {
  symbol: string
  name: string | null
  industry: string | null
  exchange: string | null
}

interface ChatCompany extends Company {
  kronosSignal: string | null
  aiRating: number | null
  peRatio: number | null
  priceChange: number | null
}

interface ChatResult {
  answer: string
  companies: ChatCompany[]
}

interface Highlight {
  symbol: string
  current_price: number | null
  price_change_1m: number | null
  price_change_3m: number | null
  price_change_1y: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  ai_rating: number | null
  ai_summary: string | null
}

type CoverageMap = Record<string, { financial: boolean; price: boolean; kronos: any | null }>

function signalIcon(signal: string | null): { icon: string; color: string; bg: string } | null {
  if (!signal) return null
  const map: Record<string, { icon: string; color: string; bg: string }> = {
    STRONG_BUY: { icon: '🔥', color: 'text-green-700', bg: 'bg-green-100' },
    BUY: { icon: '⚡', color: 'text-green-600', bg: 'bg-green-50' },
    NEUTRAL: { icon: '➖', color: 'text-yellow-700', bg: 'bg-yellow-50' },
    SELL: { icon: '⚠️', color: 'text-red-600', bg: 'bg-red-50' },
    STRONG_SELL: { icon: '💀', color: 'text-red-700', bg: 'bg-red-100' },
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

function signalWeight(signal: string | null): number {
  const weights: Record<string, number> = {
    STRONG_BUY: 40,
    BUY: 28,
    NEUTRAL: 8,
    SELL: -22,
    STRONG_SELL: -36,
  }
  return signal ? (weights[signal] || 0) : 0
}

function actionLabel(signal: string | null, rating: number | null, change: number | null): string {
  if (signal === 'STRONG_BUY' && (rating || 0) >= 70) return 'Mua theo dõi'
  if (signal === 'BUY') return 'Tăng tỷ trọng'
  if (signal === 'STRONG_SELL') return 'Né / giảm mạnh'
  if (signal === 'SELL') return 'Giảm tỷ trọng'
  if ((rating || 0) >= 78 && (change || 0) >= 0) return 'Ưu tiên quan sát'
  if ((rating || 0) >= 65) return 'Giữ / theo dõi'
  return 'Trung lập'
}

function actionClass(action: string): string {
  if (action.includes('Mua') || action.includes('Tăng')) return 'bg-green-50 text-green-700 border-green-200'
  if (action.includes('Né') || action.includes('Giảm')) return 'bg-red-50 text-red-700 border-red-200'
  if (action.includes('Ưu tiên') || action.includes('Giữ')) return 'bg-blue-50 text-blue-700 border-blue-200'
  return 'bg-gray-50 text-gray-600 border-gray-200'
}

export default function HomePage() {
  const router = useRouter()
  const [companies, setCompanies] = useState<Company[]>([])
  const [coverage, setCoverage] = useState<CoverageMap>({})
  const [highlights, setHighlights] = useState<Highlight[]>([])
  const [loading, setLoading] = useState(true)
  const [chatResult, setChatResult] = useState<ChatResult | null>(null)

  useEffect(() => {
    Promise.all([
      getCompanies(100),
      getDataCoverage(),
      getCompanyHighlights().catch(() => []),
    ])
      .then(([companies, cov, h]) => {
        setCompanies(companies)
        setCoverage(cov as CoverageMap)
        setHighlights(Array.isArray(h) ? h : [])
      })
      .catch(() => setCompanies([]))
      .finally(() => setLoading(false))
  }, [])

  // Group by industry (A-Z), within each group sort by symbol (A-Z)
  const grouped = useMemo(() => {
    const map = new Map<string, Company[]>()
    // Sort companies by symbol first for within-group order
    const sorted = [...companies].sort((a, b) => a.symbol.localeCompare(b.symbol))
    for (const c of sorted) {
      const industry = c.industry?.trim() || 'Khác'
      if (!map.has(industry)) map.set(industry, [])
      map.get(industry)!.push(c)
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [companies])

  const dataCount = useMemo(() =>
    companies.filter(c => coverage[c.symbol]?.financial).length,
    [companies, coverage]
  )

  const highlightMap = useMemo(() => {
    return new Map(highlights.map(item => [item.symbol, item]))
  }, [highlights])

  const recommendations = useMemo(() => {
    return companies
      .map(company => {
        const h = highlightMap.get(company.symbol)
        const signal = String(coverage[company.symbol]?.kronos?.signal || '') || null
        const rating = h?.ai_rating ?? null
        const change = h?.price_change_1m ?? null
        return {
          ...company,
          highlight: h,
          signal,
          rating,
          change,
          action: actionLabel(signal, rating, change),
          rankScore: (rating || 0) + signalWeight(signal) + Math.max(Math.min(change || 0, 12), -12),
        }
      })
      .filter(item => item.highlight || item.signal)
      .sort((a, b) => b.rankScore - a.rankScore)
      .slice(0, 6)
  }, [companies, coverage, highlightMap])

  const handleResultsChange = useCallback((results: ChatResult | null) => {
    setChatResult(results)
  }, [])

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🏦</span>
            <h1 className="text-lg font-bold">AIFIA</h1>
            <span className="text-gray-500 text-xs hidden sm:inline">AI Financial Intelligence</span>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-400">{dataCount}/{companies.length} có dữ liệu</div>
            <div className="text-[10px] text-gray-300">
              {(() => {
                const dates = Object.values(coverage)
                  .map((c: any) => c?.kronos?.prediction_date || c?.kronos?.created_at)
                  .filter(Boolean)
                  .sort()
                return dates.length ? `Cập nhật: ${dates[dates.length - 1]}` : 'Đang tải...'
              })()}
            </div>
          </div>
        </div>
        {/* ChatBot replaces the old search input */}
        <ChatBot onResultsChange={handleResultsChange} />
      </header>

      {/* ── Hide main list when chat is active to avoid z-index overlap ── */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        {chatResult === null && (
          <section className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <MarketChart
              symbol="VNINDEX"
              title="Toàn cảnh VNINDEX"
              kind="index"
              defaultRange="6M"
              className="lg:col-span-2"
            />
            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Khuyến nghị nổi bật</h2>
                  <p className="mt-1 text-xs text-gray-500">Xếp hạng theo AIFIA rating, Kronos và biến động 1 tháng</p>
                </div>
                <span className="rounded bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">{recommendations.length}</span>
              </div>
              {recommendations.length === 0 ? (
                <div className="py-10 text-center text-sm text-gray-400">Chưa có dữ liệu khuyến nghị</div>
              ) : (
                <div className="space-y-2">
                  {recommendations.map(item => (
                    <button
                      key={item.symbol}
                      onClick={() => router.push(`/company/${item.symbol}`)}
                      onMouseEnter={() => router.prefetch(`/company/${item.symbol}`)}
                      className="w-full rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-left transition-colors hover:border-blue-200 hover:bg-blue-50"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-blue-700">{item.symbol}</span>
                        <span className={`rounded border px-2 py-0.5 text-[10px] font-semibold ${actionClass(item.action)}`}>
                          {item.action}
                        </span>
                        {item.rating !== null && (
                          <span className={`ml-auto text-xs font-semibold ${ratingColor(item.rating)}`}>
                            {Math.round(item.rating)}
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                        <span className="truncate">{item.industry || 'Chưa phân ngành'}</span>
                        {item.highlight?.pe_ratio !== null && item.highlight?.pe_ratio !== undefined && item.highlight.pe_ratio > 0 && (
                          <span>P/E {item.highlight.pe_ratio.toFixed(1)}</span>
                        )}
                        {item.change !== null && (
                          <span className={priceChangeColor(item.change)}>
                            {item.change > 0 ? '+' : ''}{item.change.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {loading ? (
          <div className="text-center py-20 text-gray-400">
            <div className="text-4xl mb-3 animate-pulse">⏳</div>
            <p>Đang tải danh sách cổ phiếu…</p>
          </div>
        ) : chatResult !== null ? (
          <section>
            <div className="mb-4 rounded-xl border border-blue-100 bg-white p-4 shadow-sm">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-500">
                Phân tích từ AIFIA
              </div>
              <div className="whitespace-pre-wrap text-sm leading-6 text-gray-800">
                {chatResult.answer}
              </div>
            </div>
            {chatResult.companies.length === 0 ? (
              <div className="text-center py-20 text-gray-400">
                <div className="text-4xl mb-3">🔍</div>
                <p>Không tìm thấy kết quả phù hợp</p>
              </div>
            ) : (
              <>
                <div className="text-sm text-gray-400 mb-3">
                  {chatResult.companies.length} mã — Click vào mã để xem chi tiết
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                  {chatResult.companies.map(c => {
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
              </>
            )}
          </section>
        ) : grouped.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <div className="text-4xl mb-3">🔍</div>
            <p>Chưa có dữ liệu</p>
          </div>
        ) : (
          <>
            <div className="text-sm text-gray-400 mb-3">
              Tổng số {companies.length} mã — {dataCount} có BCTC
            </div>
            {grouped.map(([industry, items]) => (
              <section key={industry} className="mb-5">
                <h2 className="text-lg font-bold text-gray-700 mb-2 sticky top-[104px] bg-gray-50 py-1">
                  {industry} <span className="text-sm font-normal text-gray-400">({items.length})</span>
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                  {items.map((c) => {
                    const cov = coverage[c.symbol]
                    const hasData = cov?.financial
                    const kronos = cov?.kronos
                    return (
                      <button
                        key={c.symbol}
                        onClick={() => router.push(`/company/${c.symbol}`)}
                        onMouseEnter={() => router.prefetch(`/company/${c.symbol}`)}
                        className={`text-left bg-white rounded-xl px-3 py-2.5 shadow-sm border transition-all hover:shadow-md active:scale-[0.98] ${
                          hasData
                            ? 'border-gray-200 hover:border-blue-400'
                            : 'border-gray-100 opacity-60 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-sm text-blue-700">{c.symbol}</span>
                          {kronos && kronos.signal && kronos.signal !== 'NEUTRAL' && (
                            <span className={`ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded ${
                              kronos.signal.includes('BUY') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                            }`}>
                              {kronos.signal === 'STRONG_BUY' ? '🔥' : kronos.signal === 'STRONG_SELL' ? '💀' : kronos.signal === 'BUY' ? '⚡' : '⚠️'}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 truncate">{c.industry || '—'}</div>
                        <div className="text-[10px] text-gray-400 mt-0.5">{c.exchange || ''}</div>
                      </button>
                    )
                  })}
                </div>
              </section>
            ))}
          </>
        )}
      </div>

      <footer className="border-t mt-6 py-4 text-center text-xs text-gray-400">
        <p>AIFIA — AI Financial Intelligence Assistant</p>
        <p className="mt-1 text-[10px] text-gray-300">
          Dữ liệu cập nhật: {(() => {
            const dates = Object.values(coverage)
              .map((c: any) => c?.kronos?.prediction_date || c?.kronos?.created_at)
              .filter(Boolean)
              .sort()
            return dates.length ? dates[dates.length - 1] : '—'
          })()}
        </p>
      </footer>
    </main>
  )
}
