'use client'

import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts'
import { supabase } from '@/lib/supabase'
import { formatCurrency } from '@/lib/utils'

interface ChartDataPoint {
  timestamp: string
  equity: number
  date: string
}

export default function EquityChart() {
  const [data, setData] = useState<ChartDataPoint[]>([])
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | 'all'>('7d')
  const [loading, setLoading] = useState(true)

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
        .select('timestamp, total_equity_usdc')
        .gte('timestamp', fromDate.toISOString())
        .order('timestamp', { ascending: true })

      if (snapshots && snapshots.length > 0) {
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
        // Generate sample data for demo
        const sampleData: ChartDataPoint[] = []
        const now = new Date()
        let equity = 10000
        for (let i = 30; i >= 0; i--) {
          const date = new Date(now)
          date.setDate(date.getDate() - i)
          equity = equity + (Math.random() - 0.48) * 100
          sampleData.push({
            timestamp: date.toISOString(),
            equity: Math.max(equity, 8000),
            date: date.toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric'
            })
          })
        }
        setData(sampleData)
      }
    } catch (error) {
      console.error('Error fetching chart data:', error)
    } finally {
      setLoading(false)
    }
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-lg">
          <p className="text-gray-400 text-sm">{label}</p>
          <p className="text-white font-semibold">
            {formatCurrency(payload[0].value)}
          </p>
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

  const minEquity = Math.min(...data.map(d => d.equity)) * 0.99
  const maxEquity = Math.max(...data.map(d => d.equity)) * 1.01

  return (
    <div>
      {/* Time Range Selector */}
      <div className="flex gap-2 mb-4">
        {(['24h', '7d', '30d', 'all'] as const).map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              timeRange === range
                ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            {range === 'all' ? 'All' : range.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="date"
              stroke="#6b7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#6b7280"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              domain={[minEquity, maxEquity]}
              tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#22c55e"
              strokeWidth={2}
              fill="url(#equityGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
