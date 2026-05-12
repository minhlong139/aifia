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
  return call('getCompanies', { limit })
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

export async function getCompanyHighlight(symbol: string) {
  return call('getCompanyHighlights', { symbol })
}

export async function getDataCoverage() {
  return call('getDataCoverage')
}

export async function getKronosPrediction(symbol: string) {
  return call('getKronosPrediction', { symbol })
}
