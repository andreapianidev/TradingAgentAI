'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import {
  DollarSign,
  Cpu,
  TrendingUp,
  TrendingDown,
  Zap,
  RefreshCw,
  Info,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Clock,
  Target,
  BarChart3,
  Sparkles
} from 'lucide-react'
import { supabase, TradingCost, TradingDecision } from '@/lib/supabase'
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
  avgCostPerTrade: number
  savingsFromCache: number
}

interface EnrichedCost extends TradingCost {
  decision?: {
    action: string
    direction: string | null
    confidence: number
    reasoning: string
  }
}

export default function CostsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [recentCosts, setRecentCosts] = useState<EnrichedCost[]>([])
  const [totals, setTotals] = useState<CostTotals>({
    total: 0,
    llm: 0,
    fees: 0,
    llmCalls: 0,
    inputTokens: 0,
    outputTokens: 0,
    cachedTokens: 0,
    trades: 0,
    avgCostPerTrade: 0,
    savingsFromCache: 0
  })
  const [dailyCosts, setDailyCosts] = useState<{ date: string; llm: number; fees: number }[]>([])
  const [costBySymbol, setCostBySymbol] = useState<Record<string, { llm: number; fees: number; count: number }>>({})
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [isVisible, setIsVisible] = useState(false)
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Safe number conversion to avoid NaN
  const safeNumber = (value: unknown): number => {
    if (value === null || value === undefined) return 0
    const num = Number(value)
    return isNaN(num) ? 0 : num
  }

  const fetchData = useCallback(async () => {
    setRefreshing(true)
    try {
      const daysMap = { '7d': 7, '30d': 30, '90d': 90 }
      const days = daysMap[timeRange]
      const startDate = new Date()
      startDate.setDate(startDate.getDate() - days)

      // Fetch all costs for the period
      const { data: costs, error: costsError } = await supabase
        .from('trading_costs')
        .select('*')
        .gte('created_at', startDate.toISOString())
        .order('created_at', { ascending: false })

      if (costsError) {
        console.error('Error fetching costs:', costsError)
        throw costsError
      }

      // Fetch related decisions for enrichment
      const decisionIds = costs?.filter(c => c.decision_id).map(c => c.decision_id) || []
      let decisionsMap: Record<string, TradingDecision> = {}

      if (decisionIds.length > 0) {
        const { data: decisions } = await supabase
          .from('trading_decisions')
          .select('id, action, direction, confidence, reasoning')
          .in('id', decisionIds)

        if (decisions) {
          decisionsMap = decisions.reduce((acc, d) => {
            acc[d.id] = d
            return acc
          }, {} as Record<string, TradingDecision>)
        }
      }

      if (costs) {
        // Enrich costs with decision data
        const enrichedCosts: EnrichedCost[] = costs.map(cost => ({
          ...cost,
          decision: cost.decision_id ? decisionsMap[cost.decision_id] : undefined
        }))

        setRecentCosts(enrichedCosts)

        const llmCosts = costs.filter((c: TradingCost) => c.cost_type === 'llm')
        const feeCosts = costs.filter((c: TradingCost) => c.cost_type === 'trading_fee')

        // Calculate savings from cache
        const cachedTokens = llmCosts.reduce((sum: number, c: TradingCost) => sum + (c.cached_tokens || 0), 0)
        const savingsFromCache = cachedTokens * (DEEPSEEK_PRICING.input - DEEPSEEK_PRICING.cached)

        setTotals({
          total: costs.reduce((sum: number, c: TradingCost) => sum + safeNumber(c.cost_usd), 0),
          llm: llmCosts.reduce((sum: number, c: TradingCost) => sum + safeNumber(c.cost_usd), 0),
          fees: feeCosts.reduce((sum: number, c: TradingCost) => sum + safeNumber(c.cost_usd), 0),
          llmCalls: llmCosts.length,
          inputTokens: llmCosts.reduce((sum: number, c: TradingCost) => sum + safeNumber(c.input_tokens), 0),
          outputTokens: llmCosts.reduce((sum: number, c: TradingCost) => sum + safeNumber(c.output_tokens), 0),
          cachedTokens: cachedTokens,
          trades: feeCosts.length,
          avgCostPerTrade: feeCosts.length > 0
            ? feeCosts.reduce((sum: number, c: TradingCost) => sum + safeNumber(c.cost_usd), 0) / feeCosts.length
            : 0,
          savingsFromCache
        })

        // Group by day for chart
        const costsByDay: Record<string, { llm: number; fees: number }> = {}
        costs.forEach((c: TradingCost) => {
          const date = c.created_at?.split('T')[0] || 'unknown'
          if (!costsByDay[date]) {
            costsByDay[date] = { llm: 0, fees: 0 }
          }
          if (c.cost_type === 'llm') {
            costsByDay[date].llm += safeNumber(c.cost_usd)
          } else {
            costsByDay[date].fees += safeNumber(c.cost_usd)
          }
        })

        const dailyData = Object.entries(costsByDay)
          .map(([date, data]) => ({ date, ...data }))
          .sort((a, b) => a.date.localeCompare(b.date))

        setDailyCosts(dailyData)

        // Group by symbol
        const bySymbol: Record<string, { llm: number; fees: number; count: number }> = {}
        costs.forEach((c: TradingCost) => {
          const sym = c.symbol || 'Unknown'
          if (!bySymbol[sym]) {
            bySymbol[sym] = { llm: 0, fees: 0, count: 0 }
          }
          if (c.cost_type === 'llm') {
            bySymbol[sym].llm += safeNumber(c.cost_usd)
          } else {
            bySymbol[sym].fees += safeNumber(c.cost_usd)
          }
          bySymbol[sym].count++
        })
        setCostBySymbol(bySymbol)
        setLastUpdate(new Date())
      }
    } catch (error) {
      console.error('Error fetching costs:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [timeRange])

  // Initial load with fade-in animation
  useEffect(() => {
    fetchData().then(() => {
      setTimeout(() => setIsVisible(true), 100)
    })
  }, [fetchData])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    refreshIntervalRef.current = setInterval(() => {
      fetchData()
    }, 30000)

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
      }
    }
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
        <div className="relative">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-yellow-500/20 border-t-yellow-500"></div>
          <DollarSign className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 text-yellow-500 animate-pulse" />
        </div>
      </div>
    )
  }

  return (
    <div className={cn(
      "space-y-6 transition-all duration-500",
      isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <div className="p-2 bg-gradient-to-br from-yellow-500 to-amber-600 rounded-xl shadow-lg shadow-yellow-500/25">
              <DollarSign className="w-6 h-6 text-white" />
            </div>
            Operating Costs
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-2">
            <Activity className="w-4 h-4" />
            Track LLM API usage and trading fees in real-time
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Last Update */}
          <div className="hidden md:flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <Clock className="w-3.5 h-3.5" />
            Updated {lastUpdate.toLocaleTimeString()}
          </div>

          {/* Time Range Selector */}
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-xl p-1 shadow-inner">
            {(['7d', '30d', '90d'] as TimeRange[]).map(range => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={cn(
                  'px-4 py-2 text-sm rounded-lg transition-all duration-300 font-medium',
                  timeRange === range
                    ? 'bg-gradient-to-r from-yellow-500 to-amber-500 text-white shadow-md shadow-yellow-500/25 scale-105'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-gray-700'
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
            className={cn(
              "p-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-300 hover:scale-105",
              refreshing && "animate-pulse"
            )}
          >
            <RefreshCw className={cn('w-5 h-5 text-gray-600 dark:text-gray-400 transition-transform duration-500', refreshing && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Summary Cards with animations */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Cost */}
        <div className="group relative bg-gradient-to-br from-yellow-500/20 via-yellow-500/10 to-amber-500/5 border border-yellow-500/30 rounded-2xl p-6 hover:shadow-xl hover:shadow-yellow-500/10 transition-all duration-300 hover:-translate-y-1 overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-500/10 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-yellow-500/20 transition-colors" />
          <div className="relative">
            <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400 mb-3">
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <DollarSign className="w-5 h-5" />
              </div>
              <span className="text-sm font-semibold uppercase tracking-wide">Total Cost</span>
            </div>
            <div className="text-4xl font-bold text-gray-900 dark:text-white mb-1 tabular-nums">
              {formatCurrency(totals.total)}
            </div>
            <div className="text-sm text-gray-500 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              Last {timeRange.replace('d', ' days')}
            </div>
          </div>
        </div>

        {/* LLM Cost */}
        <div className="group relative bg-gradient-to-br from-purple-500/10 to-purple-500/5 border border-purple-500/20 rounded-2xl p-6 hover:shadow-xl hover:shadow-purple-500/10 transition-all duration-300 hover:-translate-y-1 overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-purple-500/20 transition-colors" />
          <div className="relative">
            <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 mb-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Cpu className="w-5 h-5" />
              </div>
              <span className="text-sm font-semibold uppercase tracking-wide">LLM API</span>
            </div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white mb-1 tabular-nums">
              {formatCurrency(totals.llm)}
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-500">{totals.llmCalls.toLocaleString()} calls</span>
              {totals.savingsFromCache > 0 && (
                <span className="text-green-500 flex items-center gap-0.5 text-xs">
                  <Sparkles className="w-3 h-3" />
                  -{formatCurrency(totals.savingsFromCache)} saved
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Trading Fees */}
        <div className="group relative bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20 rounded-2xl p-6 hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 hover:-translate-y-1 overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-blue-500/20 transition-colors" />
          <div className="relative">
            <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 mb-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <TrendingUp className="w-5 h-5" />
              </div>
              <span className="text-sm font-semibold uppercase tracking-wide">Trading Fees</span>
            </div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white mb-1 tabular-nums">
              {formatCurrency(totals.fees)}
            </div>
            <div className="text-sm text-gray-500">
              {totals.trades} trades executed
            </div>
          </div>
        </div>

        {/* Efficiency Metrics */}
        <div className="group relative bg-gradient-to-br from-green-500/10 to-green-500/5 border border-green-500/20 rounded-2xl p-6 hover:shadow-xl hover:shadow-green-500/10 transition-all duration-300 hover:-translate-y-1 overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-green-500/20 transition-colors" />
          <div className="relative">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400 mb-3">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <Zap className="w-5 h-5" />
              </div>
              <span className="text-sm font-semibold uppercase tracking-wide">Efficiency</span>
            </div>
            <div className="text-3xl font-bold text-gray-900 dark:text-white mb-1 tabular-nums">
              {totals.llmCalls > 0
                ? formatCurrency(totals.llm / totals.llmCalls)
                : '$0.00'}
            </div>
            <div className="text-sm text-gray-500">
              Average per LLM call
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cost Over Time - Enhanced Bar Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-gray-500" />
              Daily Cost Trend
            </h3>
            <div className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded-full">
              {dailyCosts.length} days
            </div>
          </div>
          <div className="h-[250px] flex items-end gap-1 overflow-x-auto pb-4 px-2">
            {dailyCosts.length === 0 ? (
              <div className="flex flex-col items-center justify-center w-full h-full text-gray-500">
                <BarChart3 className="w-12 h-12 mb-2 opacity-50" />
                <span>No cost data available</span>
              </div>
            ) : (
              dailyCosts.map((day, i) => (
                <div
                  key={day.date}
                  className="flex flex-col items-center min-w-[35px] group"
                  style={{
                    animation: `slideUp 0.5s ease-out ${i * 0.03}s both`
                  }}
                >
                  <div className="relative w-full flex flex-col-reverse" style={{ height: '200px' }}>
                    {/* LLM bar */}
                    <div
                      className="w-full bg-gradient-to-t from-purple-600 to-purple-400 rounded-t-lg transition-all duration-300 group-hover:from-purple-500 group-hover:to-purple-300 group-hover:shadow-lg group-hover:shadow-purple-500/25"
                      style={{ height: `${Math.max((day.llm / maxDailyCost) * 100, day.llm > 0 ? 2 : 0)}%` }}
                    />
                    {/* Fees bar */}
                    <div
                      className="w-full bg-gradient-to-t from-blue-600 to-blue-400 rounded-t-lg transition-all duration-300 group-hover:from-blue-500 group-hover:to-blue-300 group-hover:shadow-lg group-hover:shadow-blue-500/25"
                      style={{ height: `${Math.max((day.fees / maxDailyCost) * 100, day.fees > 0 ? 2 : 0)}%` }}
                    />
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-all duration-200 scale-95 group-hover:scale-100 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap z-10 shadow-xl">
                      <div className="font-semibold mb-1">{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-purple-400 rounded-full" />
                        LLM: {formatCurrency(day.llm)}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-blue-400 rounded-full" />
                        Fees: {formatCurrency(day.fees)}
                      </div>
                      <div className="border-t border-gray-700 mt-1 pt-1 font-semibold">
                        Total: {formatCurrency(day.llm + day.fees)}
                      </div>
                      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900" />
                    </div>
                  </div>
                  <div className="text-[10px] text-gray-500 mt-2 transform -rotate-45 origin-left whitespace-nowrap">
                    {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="flex items-center justify-center gap-6 mt-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-gradient-to-t from-purple-600 to-purple-400" />
              <span className="text-gray-500">LLM API</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-gradient-to-t from-blue-600 to-blue-400" />
              <span className="text-gray-500">Trading Fees</span>
            </div>
          </div>
        </div>

        {/* Cost Distribution & By Symbol */}
        <div className="space-y-6">
          {/* Cost Distribution */}
          <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-gray-500" />
              Cost Split
            </h3>
            <div className="space-y-4">
              {/* LLM */}
              <div className="group">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600 dark:text-gray-300 font-medium">LLM API</span>
                  <span className="text-purple-600 dark:text-purple-400 font-bold">
                    {totals.total > 0 ? ((totals.llm / totals.total) * 100).toFixed(1) : 0}%
                  </span>
                </div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full transition-all duration-1000 ease-out group-hover:shadow-lg group-hover:shadow-purple-500/25"
                    style={{ width: `${totals.total > 0 ? (totals.llm / totals.total) * 100 : 0}%` }}
                  />
                </div>
                <div className="text-xs text-gray-500 mt-1">{formatCurrency(totals.llm)}</div>
              </div>

              {/* Trading Fees */}
              <div className="group">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600 dark:text-gray-300 font-medium">Trading Fees</span>
                  <span className="text-blue-600 dark:text-blue-400 font-bold">
                    {totals.total > 0 ? ((totals.fees / totals.total) * 100).toFixed(1) : 0}%
                  </span>
                </div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-1000 ease-out group-hover:shadow-lg group-hover:shadow-blue-500/25"
                    style={{ width: `${totals.total > 0 ? (totals.fees / totals.total) * 100 : 0}%` }}
                  />
                </div>
                <div className="text-xs text-gray-500 mt-1">{formatCurrency(totals.fees)}</div>
              </div>

              {/* Paper trading note */}
              {totals.fees === 0 && (
                <div className="flex items-start gap-2 mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
                  <Info className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-yellow-600 dark:text-yellow-400">
                    <span className="font-semibold">Paper Trading Mode:</span> No actual fees charged. Live trading incurs ~0.075% per trade.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Cost By Symbol */}
          {Object.keys(costBySymbol).length > 0 && (
            <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">By Symbol</h3>
              <div className="space-y-2">
                {Object.entries(costBySymbol)
                  .sort(([,a], [,b]) => (b.llm + b.fees) - (a.llm + a.fees))
                  .slice(0, 5)
                  .map(([symbol, data]) => (
                    <div key={symbol} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-gray-900 dark:text-white">{symbol}</span>
                        <span className="text-xs text-gray-500">({data.count})</span>
                      </div>
                      <span className="font-mono text-sm text-gray-600 dark:text-gray-300">
                        {formatCurrency(data.llm + data.fees)}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* LLM Token Breakdown */}
      <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-purple-500" />
          DeepSeek API Token Breakdown
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-purple-500/10 to-purple-500/5 border border-purple-500/20 rounded-xl p-5 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300">
            <div className="flex items-center gap-2 text-sm text-purple-600 dark:text-purple-400 mb-2">
              <ArrowDownRight className="w-4 h-4" />
              Input Tokens
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">
              {totals.inputTokens.toLocaleString()}
            </div>
            <div className="text-xs text-purple-600/80 dark:text-purple-400/80 mt-1 font-mono">
              {formatCurrency(llmBreakdown.input)} @ $0.14/1M
            </div>
          </div>
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20 rounded-xl p-5 hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300">
            <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 mb-2">
              <ArrowUpRight className="w-4 h-4" />
              Output Tokens
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">
              {totals.outputTokens.toLocaleString()}
            </div>
            <div className="text-xs text-blue-600/80 dark:text-blue-400/80 mt-1 font-mono">
              {formatCurrency(llmBreakdown.output)} @ $0.28/1M
            </div>
          </div>
          <div className="bg-gradient-to-br from-green-500/10 to-green-500/5 border border-green-500/20 rounded-xl p-5 hover:shadow-lg hover:shadow-green-500/10 transition-all duration-300">
            <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400 mb-2">
              <Sparkles className="w-4 h-4" />
              Cached Tokens
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">
              {totals.cachedTokens.toLocaleString()}
            </div>
            <div className="text-xs text-green-600/80 dark:text-green-400/80 mt-1 font-mono">
              {formatCurrency(llmBreakdown.cached)} @ $0.014/1M
              <span className="ml-1 text-green-500 font-semibold">(90% off!)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Operations Table */}
      <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-gray-500" />
            Recent Operations
          </h3>
          <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded-full">
            {recentCosts.length} records
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-500 text-xs uppercase tracking-wider border-b border-gray-200 dark:border-gray-700">
                <th className="pb-3 font-semibold">Time</th>
                <th className="pb-3 font-semibold">Type</th>
                <th className="pb-3 font-semibold">Symbol</th>
                <th className="pb-3 font-semibold">Action</th>
                <th className="pb-3 font-semibold">Details</th>
                <th className="pb-3 font-semibold text-right">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {recentCosts.slice(0, 25).map((cost, index) => (
                <tr
                  key={cost.id}
                  className="text-sm hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                  style={{
                    animation: `fadeIn 0.3s ease-out ${index * 0.02}s both`
                  }}
                >
                  <td className="py-3 text-gray-500 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      {formatTimeAgo(cost.created_at)}
                    </div>
                  </td>
                  <td className="py-3">
                    <span className={cn(
                      'px-2.5 py-1 rounded-full text-xs font-semibold inline-flex items-center gap-1',
                      cost.cost_type === 'llm'
                        ? 'bg-purple-500/15 text-purple-600 dark:text-purple-400'
                        : 'bg-blue-500/15 text-blue-600 dark:text-blue-400'
                    )}>
                      {cost.cost_type === 'llm' ? (
                        <><Cpu className="w-3 h-3" /> LLM</>
                      ) : (
                        <><TrendingUp className="w-3 h-3" /> Trade</>
                      )}
                    </span>
                  </td>
                  <td className="py-3 text-gray-900 dark:text-white font-mono font-bold">
                    {cost.symbol || '-'}
                  </td>
                  <td className="py-3">
                    {cost.decision ? (
                      <span className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        cost.decision.action === 'open' && cost.decision.direction === 'long' && 'bg-green-500/15 text-green-600',
                        cost.decision.action === 'open' && cost.decision.direction === 'short' && 'bg-red-500/15 text-red-600',
                        cost.decision.action === 'close' && 'bg-gray-500/15 text-gray-600',
                        cost.decision.action === 'hold' && 'bg-yellow-500/15 text-yellow-600'
                      )}>
                        {cost.decision.action === 'open'
                          ? `OPEN ${cost.decision.direction?.toUpperCase()}`
                          : cost.decision.action.toUpperCase()}
                        {cost.decision.confidence && (
                          <span className="ml-1 opacity-75">
                            ({(cost.decision.confidence * 100).toFixed(0)}%)
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="py-3 text-gray-500 text-xs">
                    {cost.cost_type === 'llm' ? (
                      <span className="font-mono">
                        {(cost.input_tokens || 0).toLocaleString()} → {(cost.output_tokens || 0).toLocaleString()}
                        {(cost.cached_tokens || 0) > 0 && (
                          <span className="text-green-500 ml-1">
                            (+{(cost.cached_tokens || 0).toLocaleString()} cached)
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="font-mono">
                        {cost.trade_value_usd
                          ? `$${Number(cost.trade_value_usd).toLocaleString()} @ ${((cost.fee_rate || 0.00075) * 100).toFixed(3)}%`
                          : `${cost.fee_type || 'taker'} fee`
                        }
                      </span>
                    )}
                  </td>
                  <td className="py-3 text-right font-mono font-bold text-gray-900 dark:text-white">
                    {formatCurrency(Number(cost.cost_usd))}
                  </td>
                </tr>
              ))}
              {recentCosts.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-gray-500">
                    <div className="flex flex-col items-center gap-2">
                      <DollarSign className="w-12 h-12 opacity-30" />
                      <span>No cost data available yet</span>
                      <span className="text-xs">Costs will appear after the bot runs</span>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* CSS Animations */}
      <style jsx global>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
      `}</style>
    </div>
  )
}
