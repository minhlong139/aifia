'use client'

import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { getCompany, getFinancialReports, getPriceHistory, getAnalysis } from '@/lib/supabase'

export default function CompanyPage() {
  const params = useParams()
  const symbol = (params.symbol as string)?.toUpperCase()

  const [loading, setLoading] = useState(true)
  const [company, setCompany] = useState<any>(null)
  const [reports, setReports] = useState<any[]>([])
  const [prices, setPrices] = useState<any[]>([])
  const [analysis, setAnalysis] = useState<any>(null)

  useEffect(() => {
    if (!symbol) return

    async function load() {
      const [c, r, p, a] = await Promise.all([
        getCompany(symbol).catch(() => null),
        getFinancialReports(symbol).catch(() => []),
        getPriceHistory(symbol).catch(() => []),
        getAnalysis(symbol).catch(() => null),
      ])

      setCompany(c)
      setReports(r)
      setPrices(p)
      setAnalysis(a)
      setLoading(false)
    }

    load()
  }, [symbol])

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-pulse">⏳</div>
          <p>Đang tải dữ liệu {symbol}...</p>
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
          <p className="text-gray-500">
            Mã cổ phiếu này chưa được crawl. Hãy chạy pipeline trước.
          </p>
          <a href="/" className="text-blue-600 mt-4 inline-block">← Quay lại</a>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <a href="/" className="text-blue-600 text-sm">← Dashboard</a>
          <div className="flex items-center gap-3 mt-2">
            <h1 className="text-2xl font-bold">{symbol}</h1>
            <span className="text-gray-500">{company.name || company.company_name || ''}</span>
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
              {company.exchange || ''}
            </span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Analysis */}
        {analysis && (
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg p-6 shadow-sm border">
              <h2 className="text-lg font-semibold mb-4">🤖 AI Analysis</h2>
              <div className="flex items-center gap-4 mb-4">
                <div className={`text-3xl font-bold ${
                  (analysis.score || 0) >= 70 ? 'text-green-600' : 
                  (analysis.score || 0) >= 50 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {analysis.score?.toFixed(0) || '--'}/100
                </div>
                <div>
                  <div className="text-sm text-gray-500">Overall Score</div>
                  <div className="text-sm">
                    Rủi ro: {analysis.result?.risk_level || 'N/A'}
                  </div>
                </div>
              </div>
              <p className="text-gray-700">{analysis.summary}</p>

              {analysis.result?.anomalies?.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-semibold text-red-700 mb-2">⚠️ Phát hiện bất thường</h3>
                  {analysis.result.anomalies.map((a: any, i: number) => (
                    <div key={i} className="bg-red-50 p-3 rounded mb-2 text-sm">
                      <span className={`font-semibold ${
                        a.severity === 'high' ? 'text-red-700' : 
                        a.severity === 'medium' ? 'text-yellow-700' : 'text-gray-700'
                      }`}>{a.severity.toUpperCase()}</span>: {a.description}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Company Info */}
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">📋 Thông tin</h2>
          <dl className="space-y-3 text-sm">
            {[
              ['Ngành', company.industry],
              ['Sàn', company.exchange],
              ['Vốn hóa', company.market_cap > 0
                ? `${(company.market_cap/1e9).toFixed(0)} tỷ`
                : '—'],
              ['CP lưu hành', company.shares_outstanding
                ? Number(company.shares_outstanding).toLocaleString()
                : '—'],
            ].map(([label, value]) => (
              <div key={label as string} className="flex justify-between">
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium">{value || 'N/A'}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Financial Reports */}
        <div className="lg:col-span-2 bg-white rounded-lg p-6 shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">📊 Báo cáo tài chính</h2>
          {reports.length === 0 ? (
            <p className="text-gray-400 text-sm">Chưa có dữ liệu</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2">Kỳ</th>
                    <th className="pb-2">Loại</th>
                    <th className="pb-2">Nguồn</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.slice(0, 10).map((r: any, i: number) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-2">Q{r.quarter}/{r.year}</td>
                      <td className="py-2">{r.report_type}</td>
                      <td className="py-2 text-gray-500">{r.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
