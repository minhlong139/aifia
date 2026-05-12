import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

export const runtime = 'edge'

// ── Types ──────────────────────────────────────────────
interface Company {
  symbol: string
  name: string | null
  industry: string | null
  exchange: string | null
  market_cap: number | null
}

interface HighlightRow {
  symbol: string
  ai_rating: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  roe: number | null
  current_price: number | null
  price_change_1m: number | null
}

interface KronosRow {
  symbol: string
  metrics: {
    signal?: string
    current_price?: number
    predicted_price?: number
    change_pct?: number
    upside_prob?: number
    volatility?: number
  } | null
}

interface ChatResponse {
  answer: string
  companies: Array<{
    symbol: string
    name: string | null
    industry: string | null
    exchange: string | null
    kronosSignal: string | null
    aiRating: number | null
    peRatio: number | null
    priceChange: number | null
  }>
  resultsCount: number
}

// ── Vietnamese keyword sets ─────────────────────────────
const BUY_WORDS = ['mua', 'buy', 'tăng', 'lên', 'uptrend', 'tích cực', 'nên mua', 'mua vào', 'strong buy']
const SELL_WORDS = ['bán', 'sell', 'giảm', 'xuống', 'downtrend', 'tiêu cực', 'nên bán', 'bán ra', 'strong sell']
const KRONOS_WORDS = ['kronos', 'dự báo', 'dự đoán', 'tín hiệu', 'signal', 'k']
const INDUSTRY_WORDS = ['ngành', 'industry', 'lĩnh vực', 'nhóm']
const CHEAP_WORDS = ['rẻ', 'thấp', 'cheap', 'định giá thấp', 'pe thấp', 'pb thấp']
const EXPENSIVE_WORDS = ['đắt', 'cao', 'expensive', 'pe cao', 'pb cao']
const TOP_WORDS = ['top', 'mạnh', 'nhất', 'best', 'tốt', 'điểm cao', 'rating', 'xếp hạng']
const RECOMMEND_WORDS = ['khuyến nghị', 'recommend', 'nên', 'gợi ý']

// ── Detect industry from query ─────────────────────────
const INDUSTRY_MAP: Record<string, string[]> = {
  'ngân hàng': ['Ngân hàng', 'Bank'],
  'bank': ['Ngân hàng', 'Bank'],
  'bất động sản': ['Bất động sản', 'Real Estate'],
  'bđs': ['Bất động sản', 'Real Estate'],
  'chứng khoán': ['Chứng khoán', 'Securities'],
  'ck': ['Chứng khoán', 'Securities'],
  'thép': ['Thép', 'Steel'],
  'dầu khí': ['Dầu khí', 'Oil & Gas'],
  'điện': ['Điện', 'Electricity', 'Power'],
  'xây dựng': ['Xây dựng', 'Construction'],
  'xd': ['Xây dựng', 'Construction'],
  'bán lẻ': ['Bán lẻ', 'Retail'],
  'retail': ['Bán lẻ', 'Retail'],
  'thực phẩm': ['Thực phẩm', 'Food'],
  'food': ['Thực phẩm', 'Food'],
  'công nghệ': ['Công nghệ', 'Technology'],
  'tech': ['Công nghệ', 'Technology'],
  'dược': ['Dược', 'Pharmaceutical'],
  'pharma': ['Dược', 'Pharmaceutical'],
  'sản xuất': ['Sản xuất', 'Manufacturing'],
  'sx': ['Sản xuất', 'Manufacturing'],
  'bảo hiểm': ['Bảo hiểm', 'Insurance'],
  'insurance': ['Bảo hiểm', 'Insurance'],
  'vận tải': ['Vận tải', 'Transportation'],
  'logistics': ['Vận tải', 'Logistics'],
  'hàng tiêu dùng': ['Hàng tiêu dùng', 'Consumer'],
  'viễn thông': ['Viễn thông', 'Telecom'],
  'thủy sản': ['Thủy sản', 'Seafood', 'Thủy sản'],
}

function detectIndustry(message: string): string | null {
  const lower = message.toLowerCase()
  for (const [keyword, industries] of Object.entries(INDUSTRY_MAP)) {
    if (lower.includes(keyword)) return industries[0]
  }
  return null
}

// ── Extract symbol mentions ────────────────────────────
const VN100_SYMBOLS = new Set([
  'ACB','ANV','BCM','BID','BMP','BSI','BSR','BVH','BWE','CII',
  'CMG','CTD','CTG','CTR','CTS','DBC','DCM','DGC','DGW','DIG',
  'DPM','DSE','DXG','DXS','EIB','EVF','FPT','FRT','FTS','GAS',
  'GEE','GEX','GMD','GVR','HAG','HCM','HDB','HDC','HDG','HHV',
  'HPG','HSG','HT1','IMP','KBC','KDC','KDH','KOS','LPB','MBB',
  'MSB','MSN','MWG','NAB','NKG','NLG','NT2','NVL','OCB','PAN',
  'PC1','PDR','PHR','PLX','PNJ','POW','PVD','PVT','REE','SAB',
  'SBT','SCS','SHB','SIP','SJS','SSB','SSI','STB','SZC','TCB',
  'TCH','TPB','VCB','VCG','VCI','VGC','VHC','VHM','VIB','VIC',
  'VIX','VJC','VND','VNM','VPB','VPI','VPL','VRE','VSC','VTP',
])

function extractSymbols(message: string): string[] {
  const words = message.toUpperCase().split(/[\s,;.()]+/)
  return words.filter(w => VN100_SYMBOLS.has(w))
}

// ── Main handler ───────────────────────────────────────
export async function POST(req: NextRequest) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.SUPABASE_SERVICE_KEY
  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.json({ error: 'Supabase chưa được cấu hình' }, { status: 500 })
  }

  const supabase = createClient(supabaseUrl, supabaseKey)
  let { message } = await req.json()
  if (!message || typeof message !== 'string') {
    return NextResponse.json({ error: 'Vui lòng nhập câu hỏi' }, { status: 400 })
  }
  message = message.trim()

  // ── Step 1: Fetch data ──
  const [companiesRes, kronosRes, highlightsRes] = await Promise.all([
    supabase.from('companies').select('symbol, name, industry, exchange, market_cap'),
    supabase.from('kronos_predictions').select('symbol, metrics'),
    supabase.from('company_highlights').select('symbol, ai_rating, pe_ratio, pb_ratio, roe, current_price, price_change_1m'),
  ])

  const companies: Company[] = (companiesRes.data || []) as Company[]
  const kronosMap = new Map<string, KronosRow['metrics']>()
  for (const k of (kronosRes.data || []) as KronosRow[]) {
    if (k.metrics) kronosMap.set(k.symbol, k.metrics)
  }
  const highlightsMap = new Map<string, HighlightRow>()
  for (const h of (highlightsRes.data || []) as HighlightRow[]) {
    highlightsMap.set(h.symbol, h)
  }

  const lowerMsg = message.toLowerCase()

  // ── Step 2: Detect intent ──
  let matchedCompanies: Company[] = []
  let answer = ''
  let intentLabel = ''

  // --- 2a: Extract specific symbols ---
  const mentionedSymbols = extractSymbols(message)

  if (mentionedSymbols.length > 0 && !lowerMsg.includes('ngành') && !lowerMsg.includes('industry') && !lowerMsg.includes('tất cả') && !lowerMsg.includes('all') && !lowerMsg.includes('danh sách')) {
    // Specific symbol query
    matchedCompanies = companies.filter(c => mentionedSymbols.includes(c.symbol))
    if (matchedCompanies.length === 1) {
      const c = matchedCompanies[0]
      const k = kronosMap.get(c.symbol)
      const h = highlightsMap.get(c.symbol)
      const parts = [`📊 **${c.symbol}**`]
      if (c.name) parts.push(c.name)
      if (c.industry) parts.push(`Ngành: ${c.industry}`)
      if (c.exchange) parts.push(`Sàn: ${c.exchange}`)
      if (k?.signal) parts.push(`Kronos: ${k.signal}`)
      if (h?.ai_rating) parts.push(`AIFIA Rating: ${Math.round(h.ai_rating)}/100`)
      if (h?.pe_ratio) parts.push(`P/E: ${h.pe_ratio.toFixed(1)}x`)
      answer = parts.join(' · ')
    } else {
      answer = `Tìm thấy ${matchedCompanies.length} mã: ${matchedCompanies.map(c => c.symbol).join(', ')}`
    }
    intentLabel = 'symbol_lookup'
  }

  // --- 2b: Kronos signal ---
  else if (KRONOS_WORDS.some(w => lowerMsg.includes(w)) ||
           BUY_WORDS.some(w => lowerMsg.includes(w)) ||
           SELL_WORDS.some(w => lowerMsg.includes(w))) {
    const isBuy = BUY_WORDS.some(w => lowerMsg.includes(w)) && !SELL_WORDS.some(w => lowerMsg.includes(w))
    const isSell = SELL_WORDS.some(w => lowerMsg.includes(w)) && !BUY_WORDS.some(w => lowerMsg.includes(w))
    const isBullish = lowerMsg.includes('tăng') || lowerMsg.includes('lên')
    const isBearish = lowerMsg.includes('giảm') || lowerMsg.includes('xuống')

    // Determine signal filter
    let signalFilter: string[] = []
    if (isBuy || isBullish) signalFilter = ['STRONG_BUY', 'BUY']
    else if (isSell || isBearish) signalFilter = ['STRONG_SELL', 'SELL']
    else signalFilter = ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']

    // Filter companies by kronos signal (only those with data)
    for (const c of companies) {
      const k = kronosMap.get(c.symbol)
      if (k?.signal && signalFilter.includes(k.signal)) {
        matchedCompanies.push(c)
      }
    }

    // Sort: STRONG_BUY/STRONG_SELL first
    matchedCompanies.sort((a, b) => {
      const ka = kronosMap.get(a.symbol)
      const kb = kronosMap.get(b.symbol)
      const order = ['STRONG_BUY', 'STRONG_SELL', 'BUY', 'SELL']
      const ia = ka?.signal ? order.indexOf(ka.signal) : 99
      const ib = kb?.signal ? order.indexOf(kb.signal) : 99
      return ia - ib
    })

    const signalLabel = signalFilter.includes('STRONG_BUY') ? 'mua' : 'bán'
    answer = `📡 **${matchedCompanies.length} mã có tín hiệu Kronos ${signalLabel.toUpperCase()}**`
    intentLabel = 'kronos_signal'
  }

  // --- 2c: Industry ---
  else if (INDUSTRY_WORDS.some(w => lowerMsg.includes(w)) || Object.keys(INDUSTRY_MAP).some(k => lowerMsg.includes(k))) {
    const industry = detectIndustry(message)
    if (industry) {
      matchedCompanies = companies.filter(c =>
        c.industry?.toLowerCase().includes(industry.toLowerCase())
      )
      answer = `🏭 **${matchedCompanies.length} mã ngành ${industry}**`
      intentLabel = 'industry'
    }
  }

  // --- 2d: Top rated / Strongest (check BEFORE valuation to avoid 'cao' ambiguity) ---
  else if (TOP_WORDS.some(w => lowerMsg.includes(w)) || RECOMMEND_WORDS.some(w => lowerMsg.includes(w))) {
    // Sort by AI rating
    const withRating = companies
      .map(c => ({ company: c, rating: highlightsMap.get(c.symbol)?.ai_rating ?? -1 }))
      .filter(x => x.rating > 0)
      .sort((a, b) => b.rating - a.rating)
      .slice(0, 20)
    matchedCompanies = withRating.map(x => x.company)
    answer = `🏆 **Top ${matchedCompanies.length} mã có AIFIA Rating cao nhất**`
    intentLabel = 'top_rated'
  }

  // --- 2e: Valuation (PE/PB) ---
  // Only match if PE/PB is explicitly mentioned, OR if "định giá" is in the query
  else if (CHEAP_WORDS.some(w => lowerMsg.includes(w)) ||
           EXPENSIVE_WORDS.some(w => lowerMsg.includes(w)) ||
           lowerMsg.includes('định giá') ||
           lowerMsg.includes('valuation')) {
    const isExpensive = EXPENSIVE_WORDS.some(w => lowerMsg.includes(w)) || lowerMsg.includes('cao')
    const hasPE = lowerMsg.includes('pe') || lowerMsg.includes('p/e')
    const hasPB = lowerMsg.includes('pb') || lowerMsg.includes('p/b')

    // Default to check PE when neither PE nor PB is explicitly mentioned
    const checkPE = hasPE || (!hasPE && !hasPB)
    const checkPB = hasPB || (!hasPE && !hasPB && !checkPE)

    for (const c of companies) {
      const h = highlightsMap.get(c.symbol)
      if (!h) continue

      if (checkPE && h.pe_ratio !== null && h.pe_ratio > 0) {
        if (isExpensive && h.pe_ratio > 20) matchedCompanies.push(c)
        else if (!isExpensive && h.pe_ratio < 12) matchedCompanies.push(c)
      } else if (checkPB && h.pb_ratio !== null && h.pb_ratio > 0) {
        if (isExpensive && h.pb_ratio > 3) matchedCompanies.push(c)
        else if (!isExpensive && h.pb_ratio < 1) matchedCompanies.push(c)
      }
    }

    const suffix = isExpensive ? 'cao' : 'thấp'
    answer = `💵 **${matchedCompanies.length} mã có định giá ${suffix}**`
    intentLabel = 'valuation'

    // Fallback: if valuation found nothing but data exists, show a helpful message
    if (matchedCompanies.length === 0 && companies.length > 0) {
      const withPE = companies.filter(c => {
        const h = highlightsMap.get(c.symbol)
        return h !== undefined && h.pe_ratio !== null && h.pe_ratio > 0
      })
      answer = `💵 **0 mã có định giá ${suffix}** (${withPE.length} mã có dữ liệu P/E)`
    }
  }

  // --- 2f: All / list all ---
  else if (lowerMsg.includes('tất cả') || lowerMsg.includes('danh sách') || lowerMsg.includes('all') || lowerMsg === '') {
    matchedCompanies = companies
    answer = `📋 **Toàn bộ ${matchedCompanies.length} mã trong danh sách**`
    intentLabel = 'all'
  }

  // --- 2g: Default — try keyword match in symbol/name/industry ---
  else {
    const words = message.toUpperCase().split(/[\s,;.()]+/).filter((w: string) => w.length >= 2)
    matchedCompanies = companies.filter(c => {
      const searchTarget = [c.symbol, c.name?.toUpperCase() || '', c.industry?.toUpperCase() || ''].join(' ')
      return words.some((w: string) => searchTarget.includes(w))
    })
    if (matchedCompanies.length === 0) {
      matchedCompanies = companies
      answer = `🤔 Không tìm thấy kết quả cho "${message}". Hiển thị toàn bộ danh sách.`
    } else {
      answer = `🔍 **Tìm thấy ${matchedCompanies.length} mã**`
    }
    intentLabel = 'search'
  }

  // ── Step 3: Format response ──
  const enrichedCompanies = matchedCompanies.slice(0, 100).map(c => ({
    symbol: c.symbol,
    name: c.name,
    industry: c.industry,
    exchange: c.exchange,
    kronosSignal: kronosMap.get(c.symbol)?.signal || null,
    aiRating: highlightsMap.get(c.symbol)?.ai_rating ?? null,
    peRatio: highlightsMap.get(c.symbol)?.pe_ratio ?? null,
    priceChange: highlightsMap.get(c.symbol)?.price_change_1m ?? null,
  }))

  // Add hint for Kronos signals if query didn't match any
  if (enrichedCompanies.length > 0 && intentLabel === 'search') {
    const hasKronos = enrichedCompanies.some(c => c.kronosSignal)
    if (!hasKronos) {
      answer += '\n💡 Gợi ý: Gõ "mã nào kronos buy" để xem tín hiệu Kronos.'
    }
  }

  const response: ChatResponse = {
    answer,
    companies: enrichedCompanies,
    resultsCount: enrichedCompanies.length,
  }

  return NextResponse.json(response)
}
