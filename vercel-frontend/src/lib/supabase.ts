import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Company queries
export async function getCompanies(limit = 100) {
  const { data } = await supabase
    .from('companies')
    .select('*')
    .limit(limit)
  return data || []
}

export async function getCompany(symbol: string) {
  const { data } = await supabase
    .from('companies')
    .select('*')
    .eq('symbol', symbol.toUpperCase())
    .single()
  return data
}

export async function getFinancialReports(symbol: string) {
  const { data } = await supabase
    .from('financial_reports')
    .select('*')
    .eq('symbol', symbol.toUpperCase())
    .order('year', { ascending: false })
    .order('quarter', { ascending: false })
  return data || []
}

export async function getPriceHistory(symbol: string, days = 365) {
  const { data } = await supabase
    .from('price_history')
    .select('*')
    .eq('symbol', symbol.toUpperCase())
    .order('date', { ascending: false })
    .limit(days)
  return data || []
}

export async function getAnalysis(symbol: string) {
  const { data } = await supabase
    .from('analysis_results')
    .select('*')
    .eq('symbol', symbol.toUpperCase())
    .order('created_at', { ascending: false })
    .limit(1)
    .single()
  return data
}

export async function getRecentAnalyses(limit = 20) {
  const { data } = await supabase
    .from('analysis_results')
    .select('*, companies(name)')
    .order('created_at', { ascending: false })
    .limit(limit)
  return data || []
}

export async function getCompanyHighlights() {
  const { data } = await supabase
    .from('company_highlights')
    .select('*')
    .order('ai_rating', { ascending: false })
    .limit(50)
  return data || []
}
