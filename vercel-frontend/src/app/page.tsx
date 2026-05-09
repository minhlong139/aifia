'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, useMemo } from 'react'
import { getCompanies } from '@/lib/supabase'

interface Company {
  symbol: string
  name: string | null
  industry: string | null
  exchange: string | null
}

export default function HomePage() {
  const router = useRouter()
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    getCompanies(100)
      .then(setCompanies)
      .catch(() => setCompanies([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase()
    if (!q) return companies
    return companies.filter(c =>
      c.symbol.includes(q) ||
      (c.name?.toUpperCase().includes(q))
    )
  }, [companies, search])

  const grouped = useMemo(() => {
    const map = new Map<string, Company[]>()
    for (const c of filtered) {
      const letter = c.symbol[0]?.toUpperCase() || '#'
      if (!map.has(letter)) map.set(letter, [])
      map.get(letter)!.push(c)
    }
    // Sort letters
    const sorted = [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
    // Each group is already sorted by symbol from API
    return sorted
  }, [filtered])

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🏦</span>
            <h1 className="text-lg font-bold">AIFIA</h1>
            <span className="text-gray-500 text-xs hidden sm:inline">AI Financial Intelligence</span>
          </div>
        </div>
        {/* Search bar */}
        <div className="max-w-7xl mx-auto px-4 pb-3">
          <input
            type="text"
            placeholder="Gõ mã hoặc tên công ty để lọc…"
            className="w-full px-4 py-2.5 border border-gray-300 rounded-xl bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoFocus
          />
        </div>
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
            <p>{search ? `Không tìm thấy mã nào khớp "${search}"` : 'Chưa có dữ liệu'}</p>
          </div>
        ) : (
          <>
            <div className="text-sm text-gray-400 mb-3">
              {search ? `Tìm thấy ${filtered.length} mã` : `Tổng số ${companies.length} mã`}
            </div>
            {grouped.map(([letter, items]) => (
              <section key={letter} className="mb-5">
                <h2 className="text-lg font-bold text-gray-700 mb-2 sticky top-[104px] bg-gray-50 py-1 z-10">
                  {letter}
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                  {items.map((c) => (
                    <button
                      key={c.symbol}
                      onClick={() => router.push(`/company/${c.symbol}`)}
                      className="text-left bg-white rounded-xl px-3 py-2.5 shadow-sm border border-gray-200 hover:border-blue-400 hover:shadow-md active:scale-[0.98] transition-all"
                    >
                      <div className="font-bold text-sm text-blue-700">{c.symbol}</div>
                      <div className="text-xs text-gray-500 truncate">{c.name || c.industry || '—'}</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">{c.exchange || ''}</div>
                    </button>
                  ))}
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
