'use client'

import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { getCompany, getFinancialReports, getKronosPrediction } from '@/lib/supabase'

// ── helpers ──────────────────────────────────────────
function pick(data: Record<string, any> | undefined, ...keys: string[]) {
  if (!data) return undefined
  for (const k of keys) {
    const v = data[k]
    if (v !== undefined && v !== null && !(typeof v === 'number' && isNaN(v))) return v
  }
  return undefined
}

function fmt(v: number | undefined | null, decimals = 0, suffix = ''): string {
  if (v === undefined || v === null || (typeof v === 'number' && isNaN(v))) return '—'
  return (v / (decimals === 0 ? 1 : 1_000_000_000)).toLocaleString('vi-VN', {
    maximumFractionDigits: decimals,
    minimumFractionDigits: 0,
  }) + suffix
}

function fmtPct(v: number | undefined | null): string {
  if (v === undefined || v === null || (typeof v === 'number' && isNaN(v))) return '—'
  return `${(v * 100).toFixed(1)}%`
}

function latest<T>(reports: any[], type: string, q: number, y: number): any | undefined {
  return reports.find(r => r.report_type === type && r.quarter === q && r.year === y)
}

// ── component ────────────────────────────────────────
export default function CompanyPage() {
  const params = useParams()
  const symbol = (params.symbol as string)?.toUpperCase()

  const [loading, setLoading] = useState(true)
  const [company, setCompany] = useState<any>(null)
  const [reports, setReports] = useState<any[]>([])
  const [kronos, setKronos] = useState<any>(null)

  useEffect(() => {
    if (!symbol) return
    Promise.all([
      getCompany(symbol).catch(() => null),
      getFinancialReports(symbol).catch(() => []),
      getKronosPrediction(symbol).catch(() => null),
    ]).then(([c, r, k]) => {
      setCompany(c)
      setReports(r)
      setKronos(k)
      setLoading(false)
    })
  }, [symbol])

  const rd  = (t: string, q: number, y: number) => latest(reports, t, q, y)?.report_data || {}
  const rdQ = rd('ratio',  1, 2026)
  const rdI = rd('income_statement', 1, 2026)
  const rdB = rd('balance_sheet', 1, 2026)

  // revenue: banks use interest_income, others use net_revenue
  const revenue = pick(rdI, 'n_3.net_revenue', 'n_1.interest_income_and_similar_income', 'n_1.revenue')
  const profit  = pick(rdI, 'xiii.net_profit_after_tax', 'n_18.net_profit_after_tax', 'xv.net_profit_atttributable_to_the_equity_holders_of_the_bank')
  const pbt     = pick(rdI, 'xi.profit_before_tax', 'n_15.profit_before_tax')
  const assets  = pick(rdB, 'total_assets')

  const eps     = pick(rdQ, 'trailing_eps')
  const bvps    = pick(rdQ, 'book_value_per_share_bvps')
  const pe      = pick(rdQ, 'p_e')
  const pb      = pick(rdQ, 'p_b')
  const roe     = pick(rdQ, 'roe_trailling')
  const roa     = pick(rdQ, 'roa_trailling')
  const div     = pick(rdQ, 'dividend_yield')

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-3 animate-pulse">⏳</div>
          <p>Đang tải dữ liệu {symbol}…</p>
        </div>
      </main>
    )
  }

  if (!company) {
    return (
      <main className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-2xl mx-auto text-center mt-20">
          <div className="text-6xl mb-4">🔍</div>
          <h1 className="text-2xl font-bold mb-2">Không tìm thấy {symbol}</h1>
          <p className="text-gray-500">Mã cổ phiếu này chưa được crawl. Hãy chạy pipeline trước.</p>
          <a href="/" className="text-blue-600 mt-4 inline-block">← Quay lại</a>
        </div>
      </main>
    )
  }

  const hasFinData = revenue !== undefined || profit !== undefined || assets !== undefined

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <a href="/" className="text-blue-600 text-sm">← Dashboard</a>
          <div className="flex items-center gap-3 mt-2">
            <h1 className="text-2xl font-bold">{symbol}</h1>
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">{company.exchange || ''}</span>
            <span className="text-sm text-gray-500">{company.industry || ''}</span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Financial Summary ── */}
        <div className="lg:col-span-2 space-y-6">
          {hasFinData && (
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <h2 className="text-lg font-semibold mb-4">💹 Tổng quan tài chính Q1/2026</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {[
                  ['Doanh thu/ TN lãi', revenue !== undefined, fmt(revenue, 2, ' tỷ')],
                  ['Lợi nhuận trước thuế', pbt !== undefined, fmt(pbt, 2, ' tỷ')],
                  ['Lợi nhuận sau thuế', profit !== undefined, fmt(profit, 2, ' tỷ')],
                  ['Tổng tài sản', assets !== undefined, fmt(assets, 2, ' tỷ')],
                ].map(([label, ok, val]) => ok && (
                  <div key={label as string} className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">{label}</div>
                    <div className="text-base font-bold mt-1 text-gray-800">{val}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Valuation ── */}
          {(eps !== undefined || pe !== undefined) && (
            <div className="bg-white rounded-xl p-6 shadow-sm border">
              <h2 className="text-lg font-semibold mb-4">📈 Định giá</h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  ['EPS', eps !== undefined, eps?.toLocaleString('vi-VN', { maximumFractionDigits: 0 }) + ' đ'],
                  ['P/E', pe !== undefined, pe?.toFixed(2)],
                  ['P/B', pb !== undefined, pb?.toFixed(2)],
                  ['BVPS', bvps !== undefined, bvps?.toLocaleString('vi-VN', { maximumFractionDigits: 0 }) + ' đ'],
                  ['ROE', roe !== undefined, roe?.toFixed(2) + '%'],
                  ['ROA', roa !== undefined, roa?.toFixed(2) + '%'],
                  ['Cổ tức', div !== undefined, fmtPct(div)],
                ].map(([label, ok, val]) => ok && (
                  <div key={label as string} className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">{label}</div>
                    <div className="text-base font-bold mt-1 text-gray-800">{val}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Company Info ── */}
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h2 className="text-lg font-semibold mb-4">📋 Thông tin doanh nghiệp</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Ngành', company.industry, true],
                ['Sàn', company.exchange, true],
                ['Vốn hóa', company.market_cap > 0 ? fmt(company.market_cap, 2, ' tỷ') : '—', true],
                ['CP lưu hành', company.shares_outstanding ? Number(company.shares_outstanding).toLocaleString() : '—', true],
              ].map(([label, val]) => (
                <div key={label as string} className="flex justify-between border-b border-gray-100 pb-2">
                  <dt className="text-gray-500">{label}</dt>
                  <dd className="font-medium">{val}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>

        {/* ── Sidebar ── */}
        <div className="space-y-6">

          {/* ── Kronos Prediction ── */}
          {kronos && kronos.metrics && (() => {
            const m = kronos.metrics
            const signalColors: Record<string, string> = {
              STRONG_BUY: 'text-green-700 bg-green-50 border-green-200',
              BUY: 'text-green-600 bg-green-50 border-green-200',
              NEUTRAL: 'text-yellow-700 bg-yellow-50 border-yellow-200',
              SELL: 'text-red-600 bg-red-50 border-red-200',
              STRONG_SELL: 'text-red-700 bg-red-50 border-red-200',
            }
            const sc = signalColors[m.signal] || 'text-gray-700 bg-gray-50 border-gray-200'
            return (
              <div className="bg-white rounded-xl p-6 shadow-sm border">
                <h2 className="text-lg font-semibold mb-4">🔮 Dự báo Kronos</h2>
                <div className={`inline-block px-3 py-1 rounded-full text-sm font-bold border ${sc} mb-4`}>
                  {m.signal} {m.change_pct > 0 ? '📈' : '📉'}
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm mt-3">
                  {[
                    ['Giá hiện tại', `$${m.current_price?.toFixed(2) || '—'}`],
                    ['Dự báo', `$${m.predicted_price?.toFixed(2) || '—'}`],
                    ['Thay đổi', `${m.change_pct > 0 ? '+' : ''}${m.change_pct?.toFixed(2) || '—'}%`],
                    ['Cơ hội tăng', m.upside_prob != null ? `${m.upside_prob.toFixed(0)}%` : '—'],
                    ['Biến động', m.volatility != null ? `${m.volatility.toFixed(1)}%` : '—'],
                    ['Cao nhất', m.predicted_high != null ? `$${m.predicted_high.toFixed(2)}` : '—'],
                    ['Thấp nhất', m.predicted_low != null ? `$${m.predicted_low.toFixed(2)}` : '—'],
                  ].map(([label, val]) => (
                    <div key={label as string} className="flex justify-between border-b border-gray-100 pb-1.5">
                      <span className="text-gray-500">{label}</span>
                      <span className="font-medium">{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}

          {/* ── Financial Reports ── */}
          <div className="bg-white rounded-xl p-6 shadow-sm border">
            <h2 className="text-lg font-semibold mb-4">📊 Báo cáo tài chính</h2>
            {reports.length === 0 ? (
              <p className="text-gray-400 text-sm">Chưa có dữ liệu</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 pr-3">Kỳ</th>
                      <th className="pb-2 pr-3">Loại</th>
                      <th className="pb-2">Nguồn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.slice(0, 15).map((r: any, i: number) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1.5 pr-3 text-gray-700">Q{r.quarter}/{r.year}</td>
                        <td className="py-1.5 pr-3 text-gray-600">{r.report_type}</td>
                        <td className="py-1.5 text-gray-400 text-xs">{r.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

      </div>
    </main>
  )
}
