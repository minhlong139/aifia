'use client'

import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState, useMemo } from 'react'
import { getCompany, getFinancialReports, getKronosPrediction, getCompanies } from '@/lib/supabase'

// ── helpers ──────────────────────────────────────────
function pick(data: Record<string, any> | undefined, ...keys: string[]) {
  if (!data) return undefined
  for (const k of keys) { const v = data[k]; if (v !== undefined && v !== null && !(typeof v === 'number' && isNaN(v))) return v }
  return undefined
}

const FMT = new Intl.NumberFormat('vi-VN')
function fmtVND(v: number | undefined | null): string {
  if (v === undefined || v === null || (typeof v === 'number' && isNaN(v))) return '—'
  return FMT.format(Math.round(v * 1000)) + ' ₫'
}
function fmtT(v: number | undefined | null, decimals = 2): string {
  if (v === undefined || v === null || (typeof v === 'number' && isNaN(v))) return '—'
  return (v / 1_000_000_000).toLocaleString('vi-VN', { maximumFractionDigits: decimals, minimumFractionDigits: 0 }) + ' tỷ'
}
function fmtPct(v: number | undefined | null): string {
  if (v === undefined || v === null || (typeof v === 'number' && isNaN(v))) return '—'
  return (v * 100).toLocaleString('vi-VN', { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + '%'
}
function rd(reports: any[], t: string, q: number, y: number) {
  return reports.find(r => r.report_type === t && r.quarter === q && r.year === y)?.report_data || {}
}

// ── P&L key fields (common across all company types) ──
const PL_FIELDS = [
  { key: 'revenue', label: 'Doanh thu', keys: ['n_3.net_revenue', 'n_1.revenue', 'n_1.interest_income_and_similar_income', 'gross_profit', 'net_sales'] },
  { key: 'gross_profit', label: 'Lợi nhuận gộp', keys: ['n_5.gross_profit', 'gross_profit'] },
  { key: 'operating', label: 'LN từ HĐKD', keys: ['n_11.operating_profit', 'ix.operating_profit_before_provision_for_credit_losses'] },
  { key: 'pbt', label: 'LN trước thuế', keys: ['xi.profit_before_tax', 'n_15.profit_before_tax', 'profit_before_tax'] },
  { key: 'np', label: 'LN sau thuế', keys: ['xiii.net_profit_after_tax', 'n_18.net_profit_after_tax', 'xv.net_profit_atttributable_to_the_equity_holders_of_the_bank', 'net_profit_after_tax'] },
]
function getPL(income: any[]) {
  const sorted = [...income].sort((a, b) => b.year - a.year || b.quarter - a.quarter)
  const latest = sorted[0]
  if (!latest) return { latest: null, fields: {} }
  const d = latest.report_data || {}
  const fields: Record<string, number> = {}
  for (const f of PL_FIELDS) {
    const v = pick(d, ...f.keys)
    if (v !== undefined) fields[f.key] = v
  }
  return { latest: `${latest.quarter}/${latest.year}`, fields }
}

// ── Component ────────────────────────────────────────
export default function CompanyPage() {
  const router = useRouter()
  const params = useParams()
  const curSymbol = (params.symbol as string)?.toUpperCase()

  const [loading, setLoading] = useState(true)
  const [company, setCompany] = useState<any>(null)
  const [reports, setReports] = useState<any[]>([])
  const [kronos, setKronos] = useState<any>(null)
  const [allSymbols, setAllSymbols] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState<'pl' | 'balance' | 'cf'>('pl')

  // Fetch all data
  useEffect(() => {
    if (!curSymbol) return
    setLoading(true)
    Promise.all([
      getCompany(curSymbol).catch(() => null),
      getFinancialReports(curSymbol).catch(() => []),
      getKronosPrediction(curSymbol).catch(() => null),
      getCompanies(100).catch(() => [] as any[]),
    ]).then(([c, r, k, companies]) => {
      setCompany(c)
      setReports(r)
      setKronos(k)
      setAllSymbols((companies as any[]).map((x: any) => x.symbol))
      setLoading(false)
    })
  }, [curSymbol])

  // Prev / Next
  const navIdx = useMemo(() => allSymbols.indexOf(curSymbol), [allSymbols, curSymbol])
  const prev = navIdx > 0 ? allSymbols[navIdx - 1] : null
  const next = navIdx < allSymbols.length - 1 ? allSymbols[navIdx + 1] : null

  // Parse reports
  const incomeReports = useMemo(() => reports.filter(r => r.report_type === 'income_statement'), [reports])
  const balanceReports = useMemo(() => reports.filter(r => r.report_type === 'balance_sheet'), [reports])

  // P&L table with comparison
  const plTable = useMemo(() => {
    const sorted = [...incomeReports].sort((a, b) => b.year - a.year || b.quarter - a.quarter).slice(0, 4)
    if (!sorted.length) return null
    return { headers: sorted.map(r => `Q${r.quarter}/${r.year}`), data: sorted.map(r => r.report_data || {}) }
  }, [incomeReports])

  // Balance sheet latest
  const bsLatest = useMemo(() => {
    const sorted = [...balanceReports].sort((a, b) => b.year - a.year || b.quarter - a.quarter)[0]
    if (!sorted) return null
    const d = sorted.report_data || {}
    return {
      period: `Q${sorted.quarter}/${sorted.year}`,
      ta: pick(d, 'total_assets'),
      tl: pick(d, 'total_liabilities'),
      eq: pick(d, 'owners_equity', 'd.owners_equity', 'i.owners_equity'),
      cash: pick(d, 'i.cash_gold_and_silver_precious_stones', 'cash_and_cash_equivalents'),
      loans: pick(d, 'vi.loans_advances_and_finance_leases_to_customers', 'loans_to_customers'),
      deposits: pick(d, 'iii.deposits_from_customers', 'deposits_from_customers'),
    }
  }, [balanceReports])

  // Anomalies
  const anomalies = useMemo(() => {
    const sorted = [...incomeReports].sort((a, b) => b.year - a.year || b.quarter - a.quarter)
    const list: { fieldKey: string; label: string; change: number; from: string; to: string; severity: string }[] = []
    for (let i = 0; i < Math.min(sorted.length - 1, 3); i++) {
      const cur = sorted[i], prv = sorted[i + 1]
      const dc = cur.report_data || {}, dp = prv.report_data || {}
      for (const f of PL_FIELDS) {
        const vc = pick(dc, ...f.keys), vp = pick(dp, ...f.keys)
        if (vc !== undefined && vp !== undefined && vp !== 0) {
          const change = (vc - vp) / Math.abs(vp) * 100
          if (Math.abs(change) > 20) {
            list.push({
              fieldKey: f.key,
              label: f.label,
              change,
              from: `Q${prv.quarter}/${prv.year}`,
              to: `Q${cur.quarter}/${cur.year}`,
              severity: Math.abs(change) > 50 ? 'high' : Math.abs(change) > 30 ? 'medium' : 'low',
            })
          }
        }
      }
    }
    return list
  }, [incomeReports])

  if (loading) return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center"><div className="text-4xl mb-3 animate-pulse">⏳</div><p>Đang tải dữ liệu {curSymbol}…</p></div>
    </main>
  )
  if (!company) return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto text-center mt-20">
        <div className="text-6xl mb-4">🔍</div>
        <h1 className="text-2xl font-bold mb-2">Không tìm thấy {curSymbol}</h1>
        <p className="text-gray-500">Mã cổ phiếu này chưa được crawl.</p>
        <a href="/" className="text-blue-600 mt-4 inline-block">← Quay lại</a>
      </div>
    </main>
  )

  const rdQ = rd(reports, 'ratio', 1, 2026)
  const eps = pick(rdQ, 'trailing_eps'), pe = pick(rdQ, 'p_e'), pb = pick(rdQ, 'p_b')
  const bvps = pick(rdQ, 'book_value_per_share_bvps'), roe = pick(rdQ, 'roe_trailling'), roa = pick(rdQ, 'roa_trailling')

  return (
    <main className="min-h-screen bg-gray-50">
      {/* ── Header with prev/next ── */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between mb-1">
            <a href="/" className="text-blue-600 text-sm">← Dashboard</a>
            <div className="flex items-center gap-1 text-sm">
              {prev ? (
                <button onClick={() => router.push(`/company/${prev}`)} className="px-2 py-1 hover:bg-gray-100 rounded">
                  ◀ <span className="hidden sm:inline">{prev}</span>
                </button>
              ) : <span className="px-2 py-1 text-gray-300">◀</span>}
              <span className="font-bold text-gray-700 mx-2">{curSymbol}</span>
              {next ? (
                <button onClick={() => router.push(`/company/${next}`)} className="px-2 py-1 hover:bg-gray-100 rounded">
                  <span className="hidden sm:inline">{next}</span> ▶
                </button>
              ) : <span className="px-2 py-1 text-gray-300">▶</span>}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-4 grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* ════ LEFT / MAIN ════ */}
        <div className="lg:col-span-2 space-y-4">

          {/* ── Company Info ── */}
          <div className="bg-white rounded-xl p-5 shadow-sm border">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{curSymbol}</h1>
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">{company.exchange || ''}</span>
              <span className="text-sm text-gray-500">{company.industry || ''}</span>
            </div>
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
              <div><span className="text-gray-500">Vốn hóa</span><br/><b>{company.market_cap > 0 ? fmtT(company.market_cap) : '—'}</b></div>
              <div><span className="text-gray-500">CP lưu hành</span><br/><b>{company.shares_outstanding ? FMT.format(Number(company.shares_outstanding)) : '—'}</b></div>
              {eps !== undefined && <div><span className="text-gray-500">EPS</span><br/><b>{eps.toLocaleString('vi-VN', {maxFractionDigits:0})} ₫</b></div>}
              {pe !== undefined && <div><span className="text-gray-500">P/E</span><br/><b>{pe.toLocaleString('vi-VN', {maximumFractionDigits:2, minimumFractionDigits:2})}</b></div>}
              {pb !== undefined && <div><span className="text-gray-500">P/B</span><br/><b>{pb.toLocaleString('vi-VN', {maximumFractionDigits:2, minimumFractionDigits:2})}</b></div>}
              {roe !== undefined && <div><span className="text-gray-500">ROE</span><br/><b>{roe.toLocaleString('vi-VN', {maximumFractionDigits:2, minimumFractionDigits:2})}%</b></div>}
            </div>
          </div>

          {/* ── P&L Detailed Comparison ── */}
          {plTable && (
            <div className="bg-white rounded-xl p-5 shadow-sm border overflow-x-auto">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold">💹 KQKD theo quý</h2>
                <div className="flex gap-1 text-xs">
                  {['pl','balance','cf'].map(t => (
                    <button key={t} onClick={() => setActiveTab(t as any)}
                      className={`px-2.5 py-1 rounded ${activeTab===t ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
                      {t==='pl'?'KQKD':t==='balance'?'CĐKT':'LCTT'}
                    </button>
                  ))}
                </div>
              </div>

              {activeTab === 'pl' && (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="py-2 pr-4 text-left text-gray-500 font-medium">Chỉ tiêu</th>
                      {plTable.headers.map((h, i) => (
                        <th key={i} className={`py-2 px-2 text-right font-medium ${i===0?'text-blue-700':'text-gray-500'}`}>{h}</th>
                      ))}
                      {plTable.headers[1] && <th className="py-2 pl-2 text-right text-gray-500 font-medium">% Tăng/giảm</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {PL_FIELDS.map(f => {
                      const vals = plTable.data.map(d => pick(d, ...f.keys))
                      const hasAny = vals.some(v => v !== undefined)
                      if (!hasAny) return null
                      const change = vals[0] !== undefined && vals[1] !== undefined && vals[1] !== 0
                        ? ((vals[0] - vals[1]) / Math.abs(vals[1]) * 100) : null
                      const isAnomaly = change !== null && Math.abs(change) > 20
                      return (
                        <tr key={f.key} className="border-b last:border-0 hover:bg-gray-50">
                          <td className="py-2 pr-4 text-gray-700">{f.label}</td>
                          {vals.map((v, i) => (
                            <td key={i} className={`py-2 px-2 text-right font-medium tabular-nums ${i===0?'text-gray-900':'text-gray-600'}`}>
                              {v !== undefined ? fmtT(v) : '—'}
                            </td>
                          ))}
                          <td className={`py-2 pl-2 text-right font-medium tabular-nums ${isAnomaly ? 'text-red-600' : 'text-gray-500'}`}>
                            {change !== null ? `${change > 0 ? '+' : ''}${change.toLocaleString('vi-VN', {maximumFractionDigits:1, minimumFractionDigits:1})}%` : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}

              {activeTab === 'balance' && bsLatest && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {[
                    ['Tổng tài sản', bsLatest.ta, fmtT],
                    ['Nợ phải trả', bsLatest.tl, fmtT],
                    ['VCSH', bsLatest.eq, fmtT],
                    ['Tiền mặt', bsLatest.cash, fmtT],
                    ['Cho vay KH', bsLatest.loans, fmtT],
                    ['Tiền gửi KH', bsLatest.deposits, fmtT],
                  ].filter(([,v]) => v).map(([label, val, fn]) => (
                    <div key={label as string} className="flex justify-between border-b border-gray-100 pb-2">
                      <span className="text-gray-500">{label}</span>
                      <span className="font-medium">{(fn as any)(val)}</span>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'cf' && <p className="text-gray-400 text-sm py-4 text-center">Dữ liệu LCTT sẽ được bổ sung sau</p>}
            </div>
          )}

          {/* ── Anomalies ── */}
          {anomalies.length > 0 && (
            <div className="bg-white rounded-xl p-5 shadow-sm border">
              <h2 className="text-lg font-semibold mb-3">⚠️ Biến động bất thường</h2>
              <div className="space-y-2">
                {anomalies.slice(0, 8).map((a, i) => (
                  <div key={i} className={`p-3 rounded-lg text-sm ${
                    a.severity === 'high' ? 'bg-red-50 text-red-700 border border-red-200' :
                    a.severity === 'medium' ? 'bg-yellow-50 text-yellow-700 border border-yellow-200' :
                    'bg-gray-50 text-gray-600 border border-gray-200'
                  }`}>
                    <b>{a.label}</b> thay đổi <b>{a.change > 0 ? '+' : ''}{a.change.toLocaleString('vi-VN', {maximumFractionDigits:1, minimumFractionDigits:1})}%</b>
                    <span className="text-gray-500"> ({a.from} → {a.to})</span>
                    {Math.abs(a.change) > 50 && (
                      <span className="ml-2 text-xs font-bold">
                        {a.change > 0 ? '🚀 Tăng đột biến' : '💥 Giảm mạnh'}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── AI nhận định ── */}
          {anomalies.length > 0 && (
            <div className="bg-white rounded-xl p-5 shadow-sm border">
              <h2 className="text-lg font-semibold mb-3">🤖 Nhận định AI</h2>
              <div className="text-sm text-gray-700 leading-relaxed">
                {(() => {
                  const severe = anomalies.filter(a => a.severity === 'high').length
                  const positive = anomalies.filter(a => a.change > 0 && a.fieldKey !== 'operating').length
                  const negative = anomalies.filter(a => a.change < 0).length
                  const parts: string[] = []
                  if (severe > 0) parts.push(`Có ${severe} biến động lớn (>50%) cần lưu ý.`)
                  if (positive > negative) parts.push('Nhìn chung xu hướng kinh doanh khả quan với nhiều chỉ số tăng trưởng.')
                  else if (negative > positive) parts.push('Áp lực lên lợi nhuận gia tăng, cần theo dõi sát các chỉ số chi phí.')
                  else parts.push('Kết quả kinh doanh có sự phân hóa giữa các chỉ số.')
                  parts.push('Khuyến nghị xem xét báo cáo giải trình của doanh nghiệp để có đánh giá chính xác hơn.')
                  return parts.join(' ')
                })()}
              </div>
            </div>
          )}
        </div>

        {/* ════ RIGHT / SIDEBAR ════ */}
        <div className="space-y-4">

          {/* ── Kronos ── */}
          {kronos?.metrics && (() => {
            const m = kronos.metrics
            const sc: Record<string,string> = {STRONG_BUY:'text-green-700 bg-green-50 border-green-200', BUY:'text-green-600 bg-green-50 border-green-200', NEUTRAL:'text-yellow-700 bg-yellow-50 border-yellow-200', SELL:'text-red-600 bg-red-50 border-red-200', STRONG_SELL:'text-red-700 bg-red-50 border-red-200'}
            return (
              <div className="bg-white rounded-xl p-5 shadow-sm border">
                <h2 className="text-lg font-semibold mb-3">🔮 Dự báo Kronos</h2>
                <div className={`inline-block px-3 py-1 rounded-full text-sm font-bold border ${sc[m.signal]||''} mb-3`}>
                  {m.signal} {m.change_pct>0?'📈':'📉'}
                </div>
                <div className="space-y-2 text-sm">
                  {[
                    ['Giá hiện tại', fmtVND(m.current_price)],
                    ['Dự báo', fmtVND(m.predicted_price)],
                    ['Thay đổi', `${m.change_pct>0?'+':''}${(m.change_pct??0).toLocaleString('vi-VN', {maximumFractionDigits:2, minimumFractionDigits:2})}%`],
                    ['Cơ hội tăng', m.upside_prob!=null?`${m.upside_prob.toLocaleString('vi-VN', {maximumFractionDigits:0})}%`:'—'],
                    ['Biến động', m.volatility!=null?`${m.volatility.toLocaleString('vi-VN', {maximumFractionDigits:1, minimumFractionDigits:1})}%`:'—'],
                    ['Cao nhất', fmtVND(m.predicted_high)],
                    ['Thấp nhất', fmtVND(m.predicted_low)],
                  ].map(([l,v]) => (
                    <div key={l as string} className="flex justify-between border-b border-gray-100 pb-1.5">
                      <span className="text-gray-500">{l}</span><span className="font-medium">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}

          {/* ── Reports List ── */}
          <div className="bg-white rounded-xl p-5 shadow-sm border">
            <h2 className="text-lg font-semibold mb-3">📊 Danh sách BCTC</h2>
            {reports.length === 0 ? <p className="text-gray-400 text-sm">Chưa có dữ liệu</p> : (
              <div className="max-h-64 overflow-y-auto text-sm space-y-1">
                {reports.slice(0, 20).map((r: any, i: number) => (
                  <div key={i} className="flex justify-between text-gray-600 py-1 border-b border-gray-50">
                    <span>Q{r.quarter}/{r.year}</span>
                    <span className="text-xs text-gray-400">{r.report_type === 'income_statement' ? 'KQKD' : r.report_type === 'balance_sheet' ? 'CĐKT' : r.report_type === 'cash_flow' ? 'LCTT' : r.report_type}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </main>
  )
}
