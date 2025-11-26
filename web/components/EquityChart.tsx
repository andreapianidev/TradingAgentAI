'use client'

import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  ReferenceLine
} from 'recharts'
import { Activity, TrendingUp, TrendingDown } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { formatCurrency, formatPercent } from '@/lib/utils'

interface ChartDataPoint {
  timestamp: string
  equity: number
  date: string
}

export default function EquityChart() {
  const [data, setData] = useState<ChartDataPoint[]>([])
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | 'all'>('7d')
  const [loading, setLoading] = useState(true)
  const [initialBalance, setInitialBalance] = useState<number | null>(null)
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    fetchChartData()
  }, [timeRange])

  const fetchChartData = async () => {
    setLoading(true)
    try {
      let fromDate = new Date()
      switch (timeRange) {
        case '24h':
          fromDate.setHours(fromDate.getHours() - 24)
          break
        case '7d':
          fromDate.setDate(fromDate.getDate() - 7)
          break
        case '30d':
          fromDate.setDate(fromDate.getDate() - 30)
          break
        case 'all':
          fromDate = new Date(0)
          break
      }

      const { data: snapshots } = await supabase
        .from('trading_portfolio_snapshots')
        .select('timestamp, total_equity_usdc, initial_balance')
        .gte('timestamp', fromDate.toISOString())
        .order('timestamp', { ascending: true })

      if (snapshots && snapshots.length > 0) {
        const firstInitialBalance = snapshots.find(s => s.initial_balance)?.initial_balance
        const firstEquity = parseFloat(snapshots[0].total_equity_usdc)
        setInitialBalance(firstInitialBalance ? parseFloat(firstInitialBalance) : firstEquity)

        setData(snapshots.map(s => ({
          timestamp: s.timestamp,
          equity: parseFloat(s.total_equity_usdc),
          date: new Date(s.timestamp).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })
        })))
      } else {
        setData([])
        setInitialBalance(null)
      }
    } catch (error) {
      console.error('Error fetching chart data:', error)
    } finally {
      setLoading(false)
    }
  }

  const isDark = mounted && resolvedTheme === 'dark'

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length && initialBalance) {
      const currentEquity = payload[0].value
      const pnl = currentEquity - initialBalance
      const pnlPct = ((currentEquity - initialBalance) / initialBalance) * 100
      const isProfit = pnl >= 0

      return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 shadow-lg">
          <p className="text-gray-500 dark:text-gray-400 text-sm">{label}</p>
          <p className="text-gray-900 dark:text-white font-semibold">
            {formatCurrency(currentEquity)}
          </p>
          <div className={`flex items-center gap-1 mt-1 ${isProfit ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {isProfit ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            <span className="text-sm font-medium">
              {isProfit ? '+' : ''}{formatCurrency(pnl)} ({isProfit ? '+' : ''}{pnlPct.toFixed(2)}%)
            </span>
          </div>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="animate-pulse text-gray-500">Loading chart...</div>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-gray-500">
        <Activity className="w-12 h-12 mb-3 opacity-50" />
        <p className="text-lg">No trading data yet</p>
        <p className="text-sm mt-1">Start the bot to see your equity curve</p>
      </div>
    )
  }

  const minEquity = Math.min(...data.map(d => d.equity)) * 0.99
  const maxEquity = Math.max(...data.map(d => d.equity)) * 1.01
  const currentEquity = data[data.length - 1]?.equity || 0
  const isInProfit = initialBalance ? currentEquity >= initialBalance : true

  const totalPnl = initialBalance ? currentEquity - initialBalance : 0
  const totalPnlPct = initialBalance ? ((currentEquity - initialBalance) / initialBalance) * 100 : 0

  // Colors based on theme
  const gridColor = isDark ? '#374151' : '#e5e7eb'
  const axisColor = isDark ? '#6b7280' : '#9ca3af'

  return (
    <div>
      {/* Header with P&L Summary */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
        <div className="flex gap-2">
          {(['24h', '7d', '30d', 'all'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                timeRange === range
                  ? isInProfit
                    ? 'bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-500 border border-green-200 dark:border-green-500/20'
                    : 'bg-red-100 dark:bg-red-500/10 text-red-700 dark:text-red-500 border border-red-200 dark:border-red-500/20'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              {range === 'all' ? 'All' : range.toUpperCase()}
            </button>
          ))}
        </div>

        {/* P&L Badge */}
        {initialBalance && (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
            isInProfit ? 'bg-green-100 dark:bg-green-500/10' : 'bg-red-100 dark:bg-red-500/10'
          }`}>
            {isInProfit ? (
              <TrendingUp className="w-4 h-4 text-green-600 dark:text-green-500" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-600 dark:text-red-500" />
            )}
            <span className={`font-semibold ${isInProfit ? 'text-green-700 dark:text-green-500' : 'text-red-700 dark:text-red-500'}`}>
              {isInProfit ? '+' : ''}{formatCurrency(totalPnl)}
            </span>
            <span className={`text-sm ${isInProfit ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              ({isInProfit ? '+' : ''}{totalPnlPct.toFixed(2)}%)
            </span>
          </div>
        )}
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="profitGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="lossGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis
              dataKey="date"
              stroke={axisColor}
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke={axisColor}
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={[minEquity, maxEquity]}
              tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
            />
            <Tooltip content={<CustomTooltip />} />

            {initialBalance && (
              <ReferenceLine
                y={initialBalance}
                stroke={axisColor}
                strokeDasharray="5 5"
                strokeWidth={1}
                label={{
                  value: 'Initial',
                  position: 'right',
                  fill: axisColor,
                  fontSize: 10
                }}
              />
            )}

            <Area
              type="monotone"
              dataKey="equity"
              stroke={isInProfit ? "#22c55e" : "#ef4444"}
              strokeWidth={2}
              fill={isInProfit ? "url(#profitGradient)" : "url(#lossGradient)"}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
