'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { getCompanies, getDataCoverage } from '@/lib/supabase'
import ChatBot from '@/components/ChatBot'

interface Company {
  symbol: string
  name: string | null
  industry: string | null
  exchange: string | null
}

type CoverageMap = Record<string, { financial: boolean; price: boolean; kronos: any | null }>

export default function HomePage() {
  const router = useRouter()
  const [companies, setCompanies] = useState<Company[]>([])
  const [coverage, setCoverage] = useState<CoverageMap>({})
  const [loading, setLoading] = useState(true)
  const [chatResults, setChatResults] = useState<Array<{
    symbol: string
    name: string | null
    industry: string | null
    exchange: string | null
    kronosSignal: string | null
    aiRating: number | null
    peRatio: number | null
    priceChange: number | null
  }> | null>(null)

  useEffect(() => {
    Promise.all([
      getCompanies(100),
      getDataCoverage(),
    ])
      .then(([companies, cov]) => {
        setCompanies(companies)
        setCoverage(cov as CoverageMap)
      })
      .catch(() => setCompanies([]))
      .finally(() => setLoading(false))
  }, [])

  // When chat returns results, use those. Otherwise show all companies.
  const displayed = useMemo(() => {
    if (chatResults !== null) {
      // Map chat results back to our local company data for full coverage info
      return chatResults.map(chatC => {
        const localC = companies.find(c => c.symbol === chatC.symbol)
        return {
          symbol: chatC.symbol,
          name: localC?.name ?? chatC.name,
          industry: localC?.industry ?? chatC.industry,
          exchange: localC?.exchange ?? chatC.exchange,
        }
      })
    }
    return companies
  }, [chatResults, companies])

  const grouped = useMemo(() => {
    const map = new Map<string, Company[]>()
    for (const c of displayed) {
      const letter = c.symbol[0]?.toUpperCase() || '#'
      if (!map.has(letter)) map.set(letter, [])
      map.get(letter)!.push(c)
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [displayed])

  const dataCount = useMemo(() =>
    companies.filter(c => coverage[c.symbol]?.financial).length,
    [companies, coverage]
  )

  const handleResultsChange = useCallback((results: any[] | null) => {
    setChatResults(results)
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
          <div className="text-xs text-gray-400">{dataCount}/{companies.length} có dữ liệu</div>
        </div>
        {/* ChatBot replaces the old search input */}
        <ChatBot onResultsChange={handleResultsChange} />
      </header>

      <div className="max-w-7xl mx-auto px-4 py-4">
        {loading ? (
          <div className="text-center py-20 text-gray-400">
            <div className="text-4xl mb-3 animate-pulse">⏳</div>
            <p>Đang tải danh sách cổ phiếu…</p>
          </div>
        ) : grouped.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <div className="text-4xl mb-3">🔍</div>
            <p>{chatResults ? 'Không tìm thấy mã nào phù hợp' : 'Chưa có dữ liệu'}</p>
          </div>
        ) : (
          <>
            <div className="text-sm text-gray-400 mb-3">
              {chatResults
                ? `Kết quả tìm kiếm: ${displayed.length} mã`
                : `Tổng số ${companies.length} mã — ${dataCount} có BCTC`}
            </div>
            {grouped.map(([letter, items]) => (
              <section key={letter} className="mb-5">
                <h2 className="text-lg font-bold text-gray-700 mb-2 sticky top-[104px] bg-gray-50 py-1 z-10">
                  {letter}
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
                        className={`text-left bg-white rounded-xl px-3 py-2.5 shadow-sm border transition-all hover:shadow-md active:scale-[0.98] ${
                          hasData
                            ? 'border-gray-200 hover:border-blue-400'
                            : 'border-gray-100 opacity-60 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full shrink-0 ${hasData ? 'bg-green-400' : 'bg-gray-300'}`} />
                          <span className="font-bold text-sm text-blue-700">{c.symbol}</span>
                          {kronos && kronos.signal && kronos.signal !== 'NEUTRAL' && (
                            <span className={`ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded ${
                              kronos.signal.includes('BUY') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                            }`}>
                              {kronos.signal === 'STRONG_BUY' ? '🔥' : kronos.signal === 'STRONG_SELL' ? '💀' : kronos.signal === 'BUY' ? '⚡' : '⚠️'}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 truncate pl-4">{c.industry || '—'}</div>
                        <div className="text-[10px] text-gray-400 mt-0.5 pl-4">{c.exchange || ''}</div>
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
        <p>AIFIA — AI Financial Intelligence Assistant • Dữ liệu từ Vnstock</p>
      </footer>
    </main>
  )
}
