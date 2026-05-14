import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

export const runtime = 'edge'

interface Company {
  symbol: string
  name: string | null
  industry: string | null
  exchange: string | null
  market_cap: number | null
  profile_text?: string | null
}

interface HighlightRow {
  symbol: string
  current_price: number | null
  price_change_1m: number | null
  price_change_3m: number | null
  price_change_1y: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  eps: number | null
  roe: number | null
  roa: number | null
  dividend_yield: number | null
  market_cap: number | null
  ai_rating: number | null
  ai_summary: string | null
  anomalies: string[] | null
}

interface KronosRow {
  symbol: string
  prediction_date: string | null
  metrics: Record<string, unknown> | null
  predicted_ohlcv: unknown
}

interface FinancialReport {
  symbol: string
  quarter: number
  year: number
  report_type: string
  report_data: Record<string, unknown>
  raw_text: string | null
}

interface PriceRow {
  symbol: string
  date: string
  close: number | null
  volume: number | null
}

interface AnalysisRow {
  symbol: string
  analysis_type: string
  summary: string | null
  score: number | null
  recommendations: string[] | null
  result: unknown
  created_at: string | null
}

interface EnrichedCompany {
  symbol: string
  name: string | null
  industry: string | null
  exchange: string | null
  kronosSignal: string | null
  aiRating: number | null
  peRatio: number | null
  priceChange: number | null
}

const INDUSTRY_KEYWORDS: Record<string, string[]> = {
  'ngân hàng': ['ngân hàng', 'bank'],
  'bất động sản': ['bất động sản', 'bđs', 'real estate'],
  'chứng khoán': ['chứng khoán', 'securities'],
  'bán lẻ': ['bán lẻ', 'retail'],
  'thép': ['thép', 'steel'],
  'xây dựng': ['xây dựng', 'construction'],
  'công nghệ': ['công nghệ', 'technology', 'tech'],
  'dược': ['dược', 'pharma'],
  'thủy sản': ['thủy sản', 'seafood'],
  'vận tải': ['vận tải', 'logistics'],
  'dầu khí': ['dầu khí', 'oil', 'gas'],
  'điện': ['điện', 'power', 'tiện ích'],
}

function parsePathSymbol(path?: string): string | null {
  const match = path?.match(/\/company\/([A-Za-z0-9]+)/)
  return match?.[1]?.toUpperCase() || null
}

function extractSymbols(message: string, validSymbols: Set<string>): string[] {
  return message
    .toUpperCase()
    .split(/[\s,;:.()[\]{}!?'"`/\\-]+/)
    .filter(word => validSymbols.has(word))
}

function detectIndustry(message: string): string | null {
  const lower = message.toLowerCase()
  for (const [industry, keywords] of Object.entries(INDUSTRY_KEYWORDS)) {
    if (keywords.some(keyword => lower.includes(keyword))) return industry
  }
  return null
}

function num(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'n/a'
  return value.toLocaleString('vi-VN', { maximumFractionDigits: digits })
}

function formatVndThousand(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'n/a'
  return `${Math.round(value * 1000).toLocaleString('vi-VN')} ₫`
}

function summarizeReportData(data: Record<string, unknown> | null | undefined) {
  if (!data) return {}
  const entries = Object.entries(data)
    .filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object')
    .slice(0, 40)
  return Object.fromEntries(entries)
}

function latestReportsByType(reports: FinancialReport[]) {
  const sorted = [...reports].sort((a, b) => b.year - a.year || b.quarter - a.quarter)
  const seen = new Set<string>()
  const result: Array<Record<string, unknown>> = []
  for (const report of sorted) {
    const key = `${report.symbol}:${report.report_type}`
    if (seen.has(key)) continue
    seen.add(key)
    result.push({
      symbol: report.symbol,
      period: `Q${report.quarter}/${report.year}`,
      type: report.report_type,
      data: summarizeReportData(report.report_data),
      raw_text: report.raw_text?.slice(0, 1200) || null,
    })
  }
  return result
}

function priceStats(rows: PriceRow[]) {
  const bySymbol = new Map<string, PriceRow[]>()
  for (const row of rows) {
    if (!bySymbol.has(row.symbol)) bySymbol.set(row.symbol, [])
    bySymbol.get(row.symbol)!.push(row)
  }
  return [...bySymbol.entries()].map(([symbol, items]) => {
    const sorted = items
      .filter(item => item.close !== null)
      .sort((a, b) => a.date.localeCompare(b.date))
    const first = sorted[0]
    const latest = sorted[sorted.length - 1]
    const change = first?.close && latest?.close
      ? (latest.close - first.close) / Math.abs(first.close) * 100
      : null
    const avgVolume = sorted.length
      ? sorted.reduce((sum, item) => sum + (item.volume || 0), 0) / sorted.length
      : null
    return {
      symbol,
      latest_date: latest?.date || null,
      latest_close: latest?.close || null,
      sampled_days: sorted.length,
      period_change_pct: change,
      avg_volume: avgVolume,
    }
  })
}

function chooseRelevantCompanies(
  message: string,
  currentPath: string | undefined,
  companies: Company[],
  highlights: Map<string, HighlightRow>,
  kronos: Map<string, KronosRow>,
) {
  const validSymbols = new Set(companies.map(company => company.symbol))
  const mentioned = extractSymbols(message, validSymbols)
  const pathSymbol = parsePathSymbol(currentPath)
  const industry = detectIndustry(message)
  const lower = message.toLowerCase()

  let selected = companies.filter(company => mentioned.includes(company.symbol))
  if (selected.length === 0 && pathSymbol && validSymbols.has(pathSymbol)) {
    selected = companies.filter(company => company.symbol === pathSymbol)
  }
  if (industry) {
    selected = companies.filter(company => company.industry?.toLowerCase().includes(industry))
  }

  if (selected.length === 0 && (lower.includes('kronos') || lower.includes('mua') || lower.includes('bán') || lower.includes('buy') || lower.includes('sell'))) {
    const wantsSell = lower.includes('bán') || lower.includes('sell') || lower.includes('giảm')
    const signals = wantsSell ? ['STRONG_SELL', 'SELL'] : ['STRONG_BUY', 'BUY']
    selected = companies.filter(company => signals.includes(String(kronos.get(company.symbol)?.metrics?.signal || '')))
  }

  if (selected.length === 0 && (lower.includes('top') || lower.includes('rating') || lower.includes('tốt') || lower.includes('khuyến nghị'))) {
    selected = [...companies]
      .sort((a, b) => (highlights.get(b.symbol)?.ai_rating || -1) - (highlights.get(a.symbol)?.ai_rating || -1))
      .slice(0, 20)
  }

  if (selected.length === 0) {
    selected = [...companies]
      .sort((a, b) => (highlights.get(b.symbol)?.ai_rating || -1) - (highlights.get(a.symbol)?.ai_rating || -1))
      .slice(0, 20)
  }

  return selected.slice(0, 25)
}

function buildCompanySnapshot(
  companies: Company[],
  highlights: Map<string, HighlightRow>,
  kronos: Map<string, KronosRow>,
  analyses: AnalysisRow[],
) {
  const analysisBySymbol = new Map<string, AnalysisRow>()
  for (const item of analyses) {
    if (!analysisBySymbol.has(item.symbol)) analysisBySymbol.set(item.symbol, item)
  }
  return companies.map(company => {
    const h = highlights.get(company.symbol)
    const k = kronos.get(company.symbol)
    const a = analysisBySymbol.get(company.symbol)
    let result: Record<string, any> = {}
    if (a?.result && typeof a.result === 'object') {
      result = a.result as Record<string, any>
    } else if (typeof a?.result === 'string') {
      try {
        result = JSON.parse(a.result)
      } catch {
        result = {}
      }
    }
    const resultRisks = [
      ...(Array.isArray(result.key_risks) ? result.key_risks : []),
      ...(Array.isArray(result.risks) ? result.risks : []),
      ...(Array.isArray(result.anomalies) ? result.anomalies.map((item: any) => item.description || item.label || String(item)) : []),
    ].filter(Boolean)
    return {
      symbol: company.symbol,
      name: company.name,
      industry: company.industry,
      exchange: company.exchange,
      market_cap: company.market_cap || h?.market_cap || null,
      profile: company.profile_text?.slice(0, 700) || null,
      valuation: {
        pe: h?.pe_ratio ?? null,
        pb: h?.pb_ratio ?? null,
        eps: h?.eps ?? null,
        roe: h?.roe ?? null,
        roa: h?.roa ?? null,
        dividend_yield: h?.dividend_yield ?? null,
      },
      price: {
        current_price: h?.current_price ?? null,
        change_1m_pct: h?.price_change_1m ?? null,
        change_3m_pct: h?.price_change_3m ?? null,
        change_1y_pct: h?.price_change_1y ?? null,
      },
      ai: {
        rating: h?.ai_rating ?? a?.score ?? null,
        summary: h?.ai_summary || a?.summary || result.summary || result.verdict || null,
        anomalies: h?.anomalies?.length ? h.anomalies : resultRisks,
        recommendations: a?.recommendations || result.recommendations || null,
      },
      kronos: {
        prediction_date: k?.prediction_date || null,
        metrics: k?.metrics || null,
      },
    }
  })
}

function enrichCompanies(
  companies: Company[],
  highlights: Map<string, HighlightRow>,
  kronos: Map<string, KronosRow>,
): EnrichedCompany[] {
  return companies.map(company => ({
    symbol: company.symbol,
    name: company.name,
    industry: company.industry,
    exchange: company.exchange,
    kronosSignal: String(kronos.get(company.symbol)?.metrics?.signal || '') || null,
    aiRating: highlights.get(company.symbol)?.ai_rating ?? null,
    peRatio: highlights.get(company.symbol)?.pe_ratio ?? null,
    priceChange: highlights.get(company.symbol)?.price_change_1m ?? null,
  }))
}

function latestRatio(symbol: string, reports: ReturnType<typeof latestReportsByType>) {
  const ratio = reports.find(report => report.symbol === symbol && report.type === 'ratio')
  const data = (ratio?.data || {}) as Record<string, unknown>
  return {
    pe: num(data.p_e) ?? num(data.pe) ?? null,
    pb: num(data.p_b) ?? num(data.pb) ?? null,
    roe: num(data.roe_trailling) ?? num(data.roe) ?? null,
    eps: num(data.trailing_eps) ?? num(data.eps) ?? null,
  }
}

function fallbackAnswer(
  message: string,
  snapshots: ReturnType<typeof buildCompanySnapshot>,
  stats: ReturnType<typeof priceStats>,
  reports: ReturnType<typeof latestReportsByType>,
) {
  const top = snapshots.slice(0, 8)
  const lines = [
    `Mình đã tổng hợp dữ liệu nội bộ AIFIA cho câu hỏi: "${message}".`,
    '',
    'Nhận định chính:',
    ...top.map(item => {
      const signal = String(item.kronos.metrics?.signal || 'n/a')
      const rating = formatNumber(num(item.ai.rating), 0)
      const ratio = latestRatio(item.symbol, reports)
      const pe = formatNumber(ratio.pe ?? num(item.valuation.pe), 1)
      const pb = formatNumber(ratio.pb ?? num(item.valuation.pb), 1)
      const roe = formatNumber(ratio.roe ?? num(item.valuation.roe), 1)
      const price = formatVndThousand(num(item.price.current_price))
      const change = formatNumber(num(item.price.change_1m_pct), 1)
      const summary = item.ai.summary ? ` ${item.ai.summary}` : ''
      return `- ${item.symbol}: ${item.industry || 'n/a'}; giá ${price}; 1M ${change}%; P/E ${pe}; P/B ${pb}; ROE ${roe}%; AIFIA ${rating}; Kronos ${signal}.${summary}`
    }),
  ]
  const risks = top.flatMap(item => item.ai.anomalies || []).slice(0, 6)
  if (risks.length) {
    lines.push('', 'Rủi ro/cảnh báo nổi bật:', ...risks.map(risk => `- ${risk}`))
  }
  if (stats.length) {
    lines.push('', 'Diễn biến giá mẫu:', ...stats.slice(0, 5).map(item =>
      `- ${item.symbol}: close mới nhất ${formatVndThousand(item.latest_close)}, biến động mẫu ${formatNumber(item.period_change_pct, 1)}% trong ${item.sampled_days} phiên.`
    ))
  }
  lines.push('', 'Kết luận: đây là bản tổng hợp rule-based từ dữ liệu đang có. Khi cấu hình OPENAI_API_KEY, AIFIA sẽ dùng model để hiểu câu hỏi sâu hơn, so sánh nhiều bảng và viết luận điểm tự nhiên hơn.')
  return lines.join('\n')
}

async function askOpenAI(question: string, context: unknown) {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) return null

  const model = process.env.OPENAI_MODEL || 'gpt-4o-mini'
  const baseUrl = (process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1').replace(/\/$/, '')
  const instructions = [
    'Bạn là AIFIA, trợ lý phân tích tài chính chứng khoán Việt Nam.',
    'Trả lời bằng tiếng Việt, đúng ngữ cảnh câu hỏi, ưu tiên dữ liệu đã cung cấp.',
    'Không bịa dữ liệu. Nếu dữ liệu thiếu, nói rõ thiếu phần nào.',
    'Tổng hợp từ nhiều bảng: hồ sơ công ty, highlights, BCTC, giá, Kronos, analysis_results, macro nếu có.',
    'Không đưa khuyến nghị đầu tư chắc chắn. Nêu rủi ro và các điểm cần kiểm chứng.',
    'Định dạng dễ đọc: nhận định chính, dữ liệu hỗ trợ, rủi ro, kết luận thực hành.',
  ].join('\n')
  const userContent = `Câu hỏi người dùng:\n${question}\n\nDữ liệu nội bộ AIFIA dạng JSON:\n${JSON.stringify(context)}`

  if (!baseUrl.includes('api.openai.com')) {
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: 'system', content: instructions },
          { role: 'user', content: userContent },
        ],
        temperature: 0.2,
        max_tokens: 1200,
      }),
    })

    if (!response.ok) {
      const detail = await response.text().catch(() => '')
      throw new Error(`AI provider ${response.status}: ${detail}`)
    }
    const data = await response.json()
    return data.choices?.[0]?.message?.content || null
  }

  const response = await fetch(`${baseUrl}/responses`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      instructions,
      input: userContent,
      max_output_tokens: 1200,
    }),
  })

  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(`OpenAI ${response.status}: ${detail}`)
  }
  const data = await response.json()
  return data.output_text
    || data.output?.flatMap((item: any) => item.content || []).map((part: any) => part.text).filter(Boolean).join('\n')
    || null
}

export async function POST(req: NextRequest) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.SUPABASE_SERVICE_KEY
  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.json({ error: 'Supabase chưa được cấu hình' }, { status: 500 })
  }

  const { message, currentPath } = await req.json()
  if (!message || typeof message !== 'string') {
    return NextResponse.json({ error: 'Vui lòng nhập câu hỏi' }, { status: 400 })
  }

  const supabase = createClient(supabaseUrl, supabaseKey)
  const [companiesRes, highlightsRes, kronosRes, macroRes] = await Promise.all([
    supabase.from('companies').select('symbol, name, industry, exchange, market_cap, profile_text').limit(200),
    supabase.from('company_highlights').select('*').limit(200),
    supabase.from('kronos_predictions').select('symbol, prediction_date, metrics, predicted_ohlcv').order('prediction_date', { ascending: false }).limit(200),
    supabase.from('macro_data').select('indicator, value, unit, period, source').limit(80),
  ])

  if (companiesRes.error) throw companiesRes.error
  const companies = (companiesRes.data || []) as Company[]
  const highlights = new Map((highlightsRes.data || []).map((item: HighlightRow) => [item.symbol, item]))
  const kronos = new Map<string, KronosRow>()
  for (const item of (kronosRes.data || []) as KronosRow[]) {
    if (!kronos.has(item.symbol)) kronos.set(item.symbol, item)
  }

  const relevantCompanies = chooseRelevantCompanies(message, currentPath, companies, highlights, kronos)
  const symbols = relevantCompanies.map(company => company.symbol)

  const [financialRes, priceRes, analysisRes] = symbols.length ? await Promise.all([
    supabase
      .from('financial_reports')
      .select('symbol, quarter, year, report_type, report_data, raw_text')
      .in('symbol', symbols)
      .order('year', { ascending: false })
      .order('quarter', { ascending: false })
      .limit(Math.min(symbols.length * 12, 240)),
    supabase
      .from('price_history')
      .select('symbol, date, close, volume')
      .in('symbol', symbols)
      .order('date', { ascending: false })
      .limit(Math.min(symbols.length * 260, 2500)),
    supabase
      .from('analysis_results')
      .select('symbol, analysis_type, summary, score, recommendations, result, created_at')
      .in('symbol', symbols)
      .order('created_at', { ascending: false })
      .limit(Math.min(symbols.length * 4, 100)),
  ]) : [{ data: [] }, { data: [] }, { data: [] }]

  const financialReports = (financialRes.data || []) as FinancialReport[]
  const priceRows = (priceRes.data || []) as PriceRow[]
  const analyses = (analysisRes.data || []) as AnalysisRow[]
  const snapshots = buildCompanySnapshot(relevantCompanies, highlights, kronos, analyses)
  const stats = priceStats(priceRows)
  const latestReports = latestReportsByType(financialReports)

  const context = {
    as_of: new Date().toISOString(),
    user_question: message,
    current_path: currentPath || null,
    selected_symbols: symbols,
    companies: snapshots,
    latest_financial_reports: latestReports,
    price_stats: stats,
    macro_data: macroRes.data || [],
  }

  let answer: string
  let usedAi = false
  try {
    const aiAnswer = await askOpenAI(message, context)
    answer = aiAnswer || fallbackAnswer(message, snapshots, stats, latestReports)
    usedAi = Boolean(aiAnswer)
  } catch (error) {
    console.error('AI chat error:', error)
    answer = fallbackAnswer(message, snapshots, stats, latestReports)
  }

  return NextResponse.json({
    answer,
    companies: enrichCompanies(relevantCompanies, highlights, kronos),
    resultsCount: relevantCompanies.length,
    usedAi,
  })
}
