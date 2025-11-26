'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  DollarSign,
  Cpu,
  TrendingUp,
  Zap,
  RefreshCw,
  Info
} from 'lucide-react'
import { supabase, TradingCost } from '@/lib/supabase'
import { cn } from '@/lib/utils'

type TimeRange = '7d' | '30d' | '90d'

// DeepSeek pricing constants
const DEEPSEEK_PRICING = {
  input: 0.14 / 1_000_000,
  output: 0.28 / 1_000_000,
  cached: 0.014 / 1_000_000,
}

interface CostTotals {
  total: number
  llm: number
  fees: number
  llmCalls: number
  inputTokens: number
  outputTokens: number
  cachedTokens: number
  trades: number
}

export default function CostsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [recentCosts, setRecentCosts] = useState<TradingCost[]>([])
  const [totals, setTotals] = useState<CostTotals>({
    total: 0,
    llm: 0,
    fees: 0,
    llmCalls: 0,
    inputTokens: 0,
    outputTokens: 0,
    cachedTokens: 0,
    trades: 0
  })
  const [dailyCosts, setDailyCosts] = useState<{ date: string; llm: number; fees: number }[]>([])

  const fetchData = useCallback(async () => {
    setRefreshing(true)
    try {
      const daysMap = { '7d': 7, '30d': 30, '90d': 90 }
      const days = daysMap[timeRange]
      const startDate = new Date()
      startDate.setDate(startDate.getDate() - days)

      // Fetch all costs for the period
      const { data: costs } = await supabase
        .from('trading_costs')
        .select('*')
        .gte('created_at', startDate.toISOString())
        .order('created_at', { ascending: false })

      if (costs) {
        setRecentCosts(costs)

        const llmCosts = costs.filter((c: TradingCost) => c.cost_type === 'llm')
        const feeCosts = costs.filter((c: TradingCost) => c.cost_type === 'trading_fee')

        setTotals({
          total: costs.reduce((sum: number, c: TradingCost) => sum + Number(c.cost_usd), 0),
          llm: llmCosts.reduce((sum: number, c: TradingCost) => sum + Number(c.cost_usd), 0),
          fees: feeCosts.reduce((sum: number, c: TradingCost) => sum + Number(c.cost_usd), 0),
          llmCalls: llmCosts.length,
          inputTokens: llmCosts.reduce((sum: number, c: TradingCost) => sum + (c.input_tokens || 0), 0),
          outputTokens: llmCosts.reduce((sum: number, c: TradingCost) => sum + (c.output_tokens || 0), 0),
          cachedTokens: llmCosts.reduce((sum: number, c: TradingCost) => sum + (c.cached_tokens || 0), 0),
          trades: feeCosts.length
        })

        // Group by day for chart
        const costsByDay: Record<string, { llm: number; fees: number }> = {}
        costs.forEach((c: TradingCost) => {
          const date = c.created_at.split('T')[0]
          if (!costsByDay[date]) {
            costsByDay[date] = { llm: 0, fees: 0 }
          }
          if (c.cost_type === 'llm') {
            costsByDay[date].llm += Number(c.cost_usd)
          } else {
            costsByDay[date].fees += Number(c.cost_usd)
          }
        })

        const dailyData = Object.entries(costsByDay)
          .map(([date, data]) => ({ date, ...data }))
          .sort((a, b) => a.date.localeCompare(b.date))

        setDailyCosts(dailyData)
      }
    } catch (error) {
      console.error('Error fetching costs:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [timeRange])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const formatCurrency = (value: number) => {
    if (value < 0.01 && value > 0) {
      return `$${value.toFixed(4)}`
    }
    return `$${value.toFixed(2)}`
  }

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return 'just now'
  }

  // Calculate token cost breakdown
  const llmBreakdown = {
    input: totals.inputTokens * DEEPSEEK_PRICING.input,
    output: totals.outputTokens * DEEPSEEK_PRICING.output,
    cached: totals.cachedTokens * DEEPSEEK_PRICING.cached
  }

  // Calculate max for chart scaling
  const maxDailyCost = Math.max(...dailyCosts.map(d => d.llm + d.fees), 0.01)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <DollarSign className="w-7 h-7 text-yellow-500" />
            Operating Costs
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Track LLM API usage and trading fees
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Time Range Selector */}
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            {(['7d', '30d', '90d'] as TimeRange[]).map(range => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-md transition-all',
                  timeRange === range
                    ? 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                )}
              >
                {range}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            onClick={fetchData}
            disabled={refreshing}
            className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            <RefreshCw className={cn('w-4 h-4 text-gray-600 dark:text-gray-400', refreshing && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Cost */}
        <div className="bg-gradient-to-br from-yellow-500/10 to-yellow-500/5 border border-yellow-500/20 rounded-xl p-6">
          <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400 mb-2">
            <DollarSign className="w-5 h-5" />
            <span className="text-sm font-medium">Total Cost</span>
          </div>
          <div className="text-3xl font-bold text-gray-900 dark:text-white">
            {formatCurrency(totals.total)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Last {timeRange.replace('d', ' days')}
          </div>
        </div>

        {/* LLM Cost */}
        <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 mb-2">
            <Cpu className="w-5 h-5" />
            <span className="text-sm font-medium">LLM API</span>
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {formatCurrency(totals.llm)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {totals.llmCalls.toLocaleString()} calls
          </div>
        </div>

        {/* Trading Fees */}
        <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 mb-2">
            <TrendingUp className="w-5 h-5" />
            <span className="text-sm font-medium">Trading Fees</span>
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {formatCurrency(totals.fees)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {totals.trades} trades
          </div>
        </div>

        {/* Avg Cost Per Trade */}
        <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400 mb-2">
            <Zap className="w-5 h-5" />
            <span className="text-sm font-medium">Avg Per Call</span>
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {totals.llmCalls > 0
              ? formatCurrency(totals.llm / totals.llmCalls)
              : '$0.00'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            LLM cost per decision
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cost Over Time - Simple Bar Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Daily Cost Trend
          </h3>
          <div className="h-[250px] flex items-end gap-1 overflow-x-auto pb-4">
            {dailyCosts.length === 0 ? (
              <div className="flex items-center justify-center w-full h-full text-gray-500">
                No cost data available
              </div>
            ) : (
              dailyCosts.map((day, i) => (
                <div key={day.date} className="flex flex-col items-center min-w-[30px] group">
                  <div className="relative w-full flex flex-col-reverse" style={{ height: '200px' }}>
                    {/* LLM bar */}
                    <div
                      className="w-full bg-purple-500/80 rounded-t transition-all group-hover:bg-purple-500"
                      style={{ height: `${(day.llm / maxDailyCost) * 100}%` }}
                    />
                    {/* Fees bar */}
                    <div
                      className="w-full bg-blue-500/80 rounded-t transition-all group-hover:bg-blue-500"
                      style={{ height: `${(day.fees / maxDailyCost) * 100}%` }}
                    />
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10">
                      {day.date}: {formatCurrency(day.llm + day.fees)}
                    </div>
                  </div>
                  <div className="text-[10px] text-gray-500 mt-1 rotate-45 origin-left">
                    {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="flex items-center gap-4 mt-2 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-purple-500" />
              <span className="text-gray-500">LLM API</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-blue-500" />
              <span className="text-gray-500">Trading Fees</span>
            </div>
          </div>
        </div>

        {/* Cost Distribution */}
        <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Cost Distribution
          </h3>
          <div className="space-y-4">
            {/* LLM */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-500">LLM API</span>
                <span className="text-purple-600 dark:text-purple-400 font-medium">
                  {totals.total > 0 ? ((totals.llm / totals.total) * 100).toFixed(1) : 0}%
                </span>
              </div>
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all"
                  style={{ width: `${totals.total > 0 ? (totals.llm / totals.total) * 100 : 0}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 mt-1">{formatCurrency(totals.llm)}</div>
            </div>

            {/* Trading Fees */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-500">Trading Fees</span>
                <span className="text-blue-600 dark:text-blue-400 font-medium">
                  {totals.total > 0 ? ((totals.fees / totals.total) * 100).toFixed(1) : 0}%
                </span>
              </div>
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${totals.total > 0 ? (totals.fees / totals.total) * 100 : 0}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 mt-1">{formatCurrency(totals.fees)}</div>
            </div>

            {/* Paper trading note */}
            {totals.fees === 0 && (
              <div className="flex items-start gap-2 mt-4 p-3 bg-yellow-500/10 rounded-lg">
                <Info className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-yellow-600 dark:text-yellow-400">
                  Paper trading mode: no actual fees charged. Live trading would incur 0.075% per trade.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* LLM Token Breakdown */}
      <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-purple-500" />
          DeepSeek API Breakdown
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Input Tokens</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {totals.inputTokens.toLocaleString()}
            </div>
            <div className="text-xs text-purple-600 dark:text-purple-400 mt-1">
              {formatCurrency(llmBreakdown.input)} @ $0.14/1M
            </div>
          </div>
          <div className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Output Tokens</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {totals.outputTokens.toLocaleString()}
            </div>
            <div className="text-xs text-purple-600 dark:text-purple-400 mt-1">
              {formatCurrency(llmBreakdown.output)} @ $0.28/1M
            </div>
          </div>
          <div className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Cached Tokens</div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {totals.cachedTokens.toLocaleString()}
            </div>
            <div className="text-xs text-green-600 dark:text-green-400 mt-1">
              {formatCurrency(llmBreakdown.cached)} @ $0.014/1M (90% savings)
            </div>
          </div>
        </div>
      </div>

      {/* Recent Costs Table */}
      <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Recent Operations
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-500 text-sm border-b border-gray-200 dark:border-gray-700">
                <th className="pb-3 font-medium">Time</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Symbol</th>
                <th className="pb-3 font-medium">Details</th>
                <th className="pb-3 font-medium text-right">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {recentCosts.slice(0, 20).map((cost) => (
                <tr key={cost.id} className="text-sm hover:bg-gray-50 dark:hover:bg-gray-800/30">
                  <td className="py-3 text-gray-500">
                    {formatTimeAgo(cost.created_at)}
                  </td>
                  <td className="py-3">
                    <span className={cn(
                      'px-2 py-1 rounded-full text-xs font-medium',
                      cost.cost_type === 'llm'
                        ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400'
                        : 'bg-blue-500/20 text-blue-600 dark:text-blue-400'
                    )}>
                      {cost.cost_type === 'llm' ? 'LLM API' : 'Trading Fee'}
                    </span>
                  </td>
                  <td className="py-3 text-gray-900 dark:text-white font-medium">
                    {cost.symbol || '-'}
                  </td>
                  <td className="py-3 text-gray-500 text-xs">
                    {cost.cost_type === 'llm' ? (
                      `${(cost.input_tokens || 0).toLocaleString()} in / ${(cost.output_tokens || 0).toLocaleString()} out`
                    ) : (
                      `${cost.fee_type || 'taker'} fee`
                    )}
                  </td>
                  <td className="py-3 text-right font-mono text-gray-900 dark:text-white">
                    {formatCurrency(Number(cost.cost_usd))}
                  </td>
                </tr>
              ))}
              {recentCosts.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-gray-500">
                    No cost data available yet. Costs will appear after the bot runs.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
