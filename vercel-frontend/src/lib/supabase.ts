const API = '/api/db'

async function call(action: string, params?: Record<string, unknown>) {
  const res = await fetch(API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, params }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }))
    throw new Error(err.error || `HTTP ${res.status}`)
  }
  return res.json()
}

// Company queries
export async function getCompanies(limit = 100) {
  // For homepage listing - uses getRecentAnalyses equivalent
  const data = await call('getRecentAnalyses', { limit })
  return data
}

export async function getCompany(symbol: string) {
  return call('getCompany', { symbol })
}

export async function getFinancialReports(symbol: string) {
  return call('getFinancialReports', { symbol })
}

export async function getPriceHistory(symbol: string, days = 365) {
  return call('getPriceHistory', { symbol, days })
}

export async function getAnalysis(symbol: string) {
  return call('getAnalysis', { symbol })
}

export async function getRecentAnalyses(limit = 20) {
  return call('getRecentAnalyses', { limit })
}

export async function getCompanyHighlights() {
  return call('getCompanyHighlights')
}
