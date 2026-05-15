'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getPriceHistory } from '@/lib/supabase'

type ChartKind = 'index' | 'stock'
type RangeKey = '1M' | '3M' | '6M' | '1Y'

interface PricePoint {
  symbol: string
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
}

interface MarketChartProps {
  symbol: string
  title: string
  subtitle?: string
  kind?: ChartKind
  days?: number
  defaultRange?: RangeKey
  className?: string
}

const RANGES: Array<{ key: RangeKey; label: string; sessions: number }> = [
  { key: '1M', label: '1T', sessions: 24 },
  { key: '3M', label: '3T', sessions: 66 },
  { key: '6M', label: '6T', sessions: 132 },
  { key: '1Y', label: '1N', sessions: 260 },
]

const FMT = new Intl.NumberFormat('vi-VN')

function formatDate(date: string) {
  const d = new Date(`${date}T00:00:00`)
  if (Number.isNaN(d.getTime())) return date
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
}

function formatCompact(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toLocaleString('vi-VN', { maximumFractionDigits: digits })}B`
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toLocaleString('vi-VN', { maximumFractionDigits: digits })}M`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toLocaleString('vi-VN', { maximumFractionDigits: digits })}K`
  return value.toLocaleString('vi-VN', { maximumFractionDigits: digits })
}

function formatPrice(value: number | null | undefined, kind: ChartKind) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  if (kind === 'index') return `${value.toLocaleString('vi-VN', { maximumFractionDigits: 2 })} điểm`
  return `${FMT.format(Math.round(value * 1000))} ₫`
}

function formatAxis(value: number, kind: ChartKind) {
  if (kind === 'index') return value.toLocaleString('vi-VN', { maximumFractionDigits: 0 })
  return value.toLocaleString('vi-VN', { maximumFractionDigits: 0 })
}

export default function MarketChart({
  symbol,
  title,
  subtitle,
  kind = 'stock',
  days = 365,
  defaultRange = '6M',
  className = '',
}: MarketChartProps) {
  const [rows, setRows] = useState<PricePoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeRange, setActiveRange] = useState<RangeKey>(defaultRange)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    getPriceHistory(symbol, days)
      .then(data => {
        if (cancelled) return
        setRows(Array.isArray(data) ? data : [])
      })
      .catch(err => {
        if (cancelled) return
        setError(err?.message || 'Không tải được dữ liệu giá')
        setRows([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [symbol, days])

  const points = useMemo(() => {
    return rows
      .filter(row => row.close !== null && row.date)
      .sort((a, b) => a.date.localeCompare(b.date))
      .map(row => ({
        ...row,
        close: Number(row.close),
        volume: row.volume ? Number(row.volume) : 0,
        label: formatDate(row.date),
      }))
  }, [rows])

  const visiblePoints = useMemo(() => {
    const range = RANGES.find(item => item.key === activeRange) || RANGES[2]
    return points.slice(-range.sessions)
  }, [activeRange, points])

  const stats = useMemo(() => {
    const first = visiblePoints[0]
    const latest = visiblePoints[visiblePoints.length - 1]
    const closes = visiblePoints.map(item => item.close).filter(Number.isFinite)
    const changePct = first?.close && latest?.close
      ? (latest.close - first.close) / Math.abs(first.close) * 100
      : null
    const high = closes.length ? Math.max(...closes) : null
    const low = closes.length ? Math.min(...closes) : null
    const avgVolume = visiblePoints.length
      ? visiblePoints.reduce((sum, item) => sum + (item.volume || 0), 0) / visiblePoints.length
      : null

    return { latest, changePct, high, low, avgVolume }
  }, [visiblePoints])

  const positive = (stats.changePct || 0) >= 0
  const lineColor = positive ? '#059669' : '#dc2626'

  return (
    <section className={`rounded-xl border border-gray-200 bg-white p-4 shadow-sm ${className}`}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-2">
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">{symbol}</span>
          </div>
          {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
        </div>
        <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
          {RANGES.map(range => (
            <button
              key={range.key}
              onClick={() => setActiveRange(range.key)}
              className={`min-w-10 rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
                activeRange === range.key
                  ? 'bg-white text-blue-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-800'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex h-72 items-center justify-center text-sm text-gray-400">Đang tải biểu đồ...</div>
      ) : error ? (
        <div className="flex h-72 items-center justify-center text-center text-sm text-red-500">{error}</div>
      ) : visiblePoints.length < 2 ? (
        <div className="flex h-72 items-center justify-center text-center text-sm text-gray-400">
          Chưa có đủ dữ liệu giá cho {symbol}. Hãy crawl/upload dữ liệu Vnstock vào Supabase.
        </div>
      ) : (
        <>
          <div className="mb-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <MiniStat label="Mới nhất" value={formatPrice(stats.latest?.close, kind)} />
            <MiniStat
              label="Biến động"
              value={`${stats.changePct && stats.changePct > 0 ? '+' : ''}${(stats.changePct || 0).toLocaleString('vi-VN', { maximumFractionDigits: 2 })}%`}
              color={positive ? 'text-green-700' : 'text-red-700'}
            />
            <MiniStat label="Cao/thấp" value={`${formatAxis(stats.high || 0, kind)} / ${formatAxis(stats.low || 0, kind)}`} />
            <MiniStat label="KL TB" value={formatCompact(stats.avgVolume, 1)} />
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={visiblePoints} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={`priceFill-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={lineColor} stopOpacity={0.22} />
                    <stop offset="95%" stopColor={lineColor} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={24}
                />
                <YAxis
                  yAxisId="price"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={value => formatAxis(Number(value), kind)}
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  tickLine={false}
                  axisLine={false}
                  width={46}
                />
                <YAxis yAxisId="volume" orientation="right" hide />
                <Tooltip
                  contentStyle={{ borderRadius: 8, borderColor: '#e5e7eb', fontSize: 12 }}
                  labelStyle={{ color: '#374151', fontWeight: 600 }}
                  formatter={(value, name) => {
                    if (name === 'volume') return [formatCompact(Number(value), 1), 'Khối lượng']
                    return [formatPrice(Number(value), kind), kind === 'index' ? 'Điểm' : 'Giá']
                  }}
                />
                <Bar yAxisId="volume" dataKey="volume" fill="#cbd5e1" opacity={0.28} barSize={4} />
                <Area
                  yAxisId="price"
                  type="monotone"
                  dataKey="close"
                  stroke={lineColor}
                  strokeWidth={2}
                  fill={`url(#priceFill-${symbol})`}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </section>
  )
}

function MiniStat({ label, value, color = 'text-gray-900' }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">{label}</div>
      <div className={`mt-0.5 truncate text-sm font-semibold tabular-nums ${color}`}>{value}</div>
    </div>
  )
}
