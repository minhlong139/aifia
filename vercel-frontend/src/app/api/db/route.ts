import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY

export const runtime = 'edge'

export async function POST(req: NextRequest) {
  if (!supabaseUrl || !supabaseServiceKey) {
    return NextResponse.json({ error: 'Supabase not configured' }, { status: 500 })
  }

  const supabase = createClient(supabaseUrl, supabaseServiceKey)

  try {
    const { action, params } = await req.json()

    switch (action) {
      case 'getCompanies': {
        const { limit = 100 } = params
        const { data } = await supabase
          .from('companies')
          .select('symbol, name, industry, exchange')
          .order('symbol', { ascending: true })
          .limit(limit)
        return NextResponse.json(data ?? [])
      }

      case 'getCompany': {
        const { symbol } = params
        const { data, error } = await supabase
          .from('companies')
          .select('*')
          .eq('symbol', symbol.toUpperCase())
          .single()
        if (error && error.code !== 'PGRST116') throw error
        return NextResponse.json(data ?? null)
      }

      case 'getFinancialReports': {
        const { symbol } = params
        const { data } = await supabase
          .from('financial_reports')
          .select('*')
          .eq('symbol', symbol.toUpperCase())
          .order('year', { ascending: false })
          .order('quarter', { ascending: false })
        return NextResponse.json(data ?? [])
      }

      case 'getPriceHistory': {
        const { symbol, days = 365 } = params
        const { data } = await supabase
          .from('price_history')
          .select('*')
          .eq('symbol', symbol.toUpperCase())
          .order('date', { ascending: false })
          .limit(days)
        return NextResponse.json(data ?? [])
      }

      case 'getAnalysis': {
        const { symbol } = params
        const { data } = await supabase
          .from('analysis_results')
          .select('*')
          .eq('symbol', symbol.toUpperCase())
          .order('created_at', { ascending: false })
          .limit(1)
          .single()
        return NextResponse.json(data ?? null)
      }

      case 'getRecentAnalyses': {
        const { limit = 20 } = params
        const { data } = await supabase
          .from('analysis_results')
          .select('*, companies(name)')
          .order('created_at', { ascending: false })
          .limit(limit)
        return NextResponse.json(data ?? [])
      }

      case 'getCompanyHighlights': {
        const { data } = await supabase
          .from('company_highlights')
          .select('*')
          .order('ai_rating', { ascending: false })
          .limit(50)
        return NextResponse.json(data ?? [])
      }

      case 'getDataCoverage': {
        // Returns which symbols have financial/price + kronos data
        const [fin, price, kronos] = await Promise.all([
          supabase.from('financial_reports').select('symbol'),
          supabase.from('price_history').select('symbol'),
          supabase.from('kronos_predictions').select('symbol, metrics'),
        ])
        const finSet = new Set((fin.data || []).map(i => i.symbol))
        const priceSet = new Set((price.data || []).map(i => i.symbol))
        const coverage: Record<string, { financial: boolean; price: boolean; kronos: any | null }> = {}
        for (const s of new Set([...finSet, ...priceSet])) {
          coverage[s] = { financial: finSet.has(s), price: priceSet.has(s), kronos: null }
        }
        for (const k of (kronos.data || [])) {
          if (coverage[k.symbol]) coverage[k.symbol].kronos = k.metrics
        }
        return NextResponse.json(coverage)
      }

      case 'getKronosPrediction': {
        const { symbol } = params
        const { data } = await supabase
          .from('kronos_predictions')
          .select('*')
          .eq('symbol', symbol.toUpperCase())
          .order('prediction_date', { ascending: false })
          .limit(1)
          .single()
        return NextResponse.json(data ?? null)
      }

      default:
        return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 })
    }
  } catch (err: any) {
    console.error('API error:', err)
    return NextResponse.json({ error: err.message || 'Internal error' }, { status: 500 })
  }
}
