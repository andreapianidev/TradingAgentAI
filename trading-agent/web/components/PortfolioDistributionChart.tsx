'use client'

import { useEffect, useState } from 'react'
import { PieChart, RefreshCw, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PositionAllocation {
  symbol: string
  value: number
  percentage: number
  tier: 'CORE' | 'OPPORTUNISTIC' | 'CASH'
}

interface PortfolioDistributionChartProps {
  className?: string
  autoRefresh?: boolean
  refreshInterval?: number
}

export default function PortfolioDistributionChart({
  className,
  autoRefresh = true,
  refreshInterval = 30
}: PortfolioDistributionChartProps) {
  const [allocations, setAllocations] = useState<PositionAllocation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [totalEquity, setTotalEquity] = useState(0)

  const fetchDistribution = async () => {
    try {
      setError(false)

      // Fetch portfolio state
      const statusRes = await fetch('/api/status')
      const statusData = await statusRes.json()

      if (!statusData.success) {
        setError(true)
        return
      }

      const portfolio = statusData.portfolio
      const positions = portfolio?.positions || []
      const availableBalance = portfolio?.available_balance || 0
      const equity = portfolio?.total_equity || 0

      setTotalEquity(equity)

      // Fetch watchlist to determine tier
      const watchlistRes = await fetch('/api/watchlist')
      const watchlistData = await watchlistRes.json()
      const watchlist = watchlistData.success ? watchlistData.watchlist : []

      // Build allocations
      const positionAllocations: PositionAllocation[] = positions.map((pos: any) => {
        const marketValue = parseFloat(pos.market_value || 0)
        const percentage = equity > 0 ? (marketValue / equity) * 100 : 0

        // Determine tier from watchlist
        const watchlistEntry = watchlist.find((w: any) => w.symbol === pos.symbol)
        const tier = watchlistEntry?.tier || 'CORE'

        return {
          symbol: pos.symbol,
          value: marketValue,
          percentage,
          tier
        }
      })

      // Add cash allocation
      if (availableBalance > 0) {
        positionAllocations.push({
          symbol: 'CASH',
          value: availableBalance,
          percentage: equity > 0 ? (availableBalance / equity) * 100 : 0,
          tier: 'CASH'
        })
      }

      // Sort by value descending
      positionAllocations.sort((a, b) => b.value - a.value)

      setAllocations(positionAllocations)
    } catch (err) {
      console.error('Error fetching distribution:', err)
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDistribution()

    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchDistribution, refreshInterval * 1000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  const getTierColor = (tier: string) => {
    const colors = {
      CORE: {
        bg: 'bg-purple-500',
        border: 'border-purple-600',
        text: 'text-purple-700 dark:text-purple-400'
      },
      OPPORTUNISTIC: {
        bg: 'bg-orange-500',
        border: 'border-orange-600',
        text: 'text-orange-700 dark:text-orange-400'
      },
      CASH: {
        bg: 'bg-green-500',
        border: 'border-green-600',
        text: 'text-green-700 dark:text-green-400'
      }
    }
    return colors[tier as keyof typeof colors] || colors.CASH
  }

  if (loading) {
    return (
      <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow p-6", className)}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Capital Distribution</h3>
          <RefreshCw className="w-5 h-5 animate-spin text-gray-400" />
        </div>
        <div className="text-center py-8 text-gray-500">Loading distribution...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow p-6", className)}>
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>Failed to load distribution</span>
        </div>
      </div>
    )
  }

  // Calculate totals by tier
  const coreTotalPct = allocations
    .filter(a => a.tier === 'CORE')
    .reduce((sum, a) => sum + a.percentage, 0)
  const opportunisticTotalPct = allocations
    .filter(a => a.tier === 'OPPORTUNISTIC')
    .reduce((sum, a) => sum + a.percentage, 0)
  const cashPct = allocations
    .find(a => a.symbol === 'CASH')?.percentage || 0

  return (
    <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow", className)}>
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PieChart className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold">Capital Distribution</h3>
          </div>
          <button
            onClick={fetchDistribution}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
          Total Equity: ${totalEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>

      <div className="p-6">
        {allocations.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No allocations found
          </div>
        ) : (
          <>
            {/* Summary by tier */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="text-center p-3 rounded-lg bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800">
                <div className="text-2xl font-bold text-purple-700 dark:text-purple-400">
                  {coreTotalPct.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">Core</div>
              </div>
              <div className="text-center p-3 rounded-lg bg-orange-50 dark:bg-orange-900/10 border border-orange-200 dark:border-orange-800">
                <div className="text-2xl font-bold text-orange-700 dark:text-orange-400">
                  {opportunisticTotalPct.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">Opportunistic</div>
              </div>
              <div className="text-center p-3 rounded-lg bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
                <div className="text-2xl font-bold text-green-700 dark:text-green-400">
                  {cashPct.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">Cash</div>
              </div>
            </div>

            {/* Visual bar chart */}
            <div className="mb-6">
              <div className="flex h-8 rounded-lg overflow-hidden">
                {allocations.map((alloc, idx) => {
                  const color = getTierColor(alloc.tier)
                  return alloc.percentage > 0 ? (
                    <div
                      key={`${alloc.symbol}-${idx}`}
                      className={cn(color.bg, "transition-all")}
                      style={{ width: `${alloc.percentage}%` }}
                      title={`${alloc.symbol}: ${alloc.percentage.toFixed(1)}%`}
                    />
                  ) : null
                })}
              </div>
            </div>

            {/* Detailed list */}
            <div className="space-y-2">
              {allocations.map((alloc, idx) => {
                const color = getTierColor(alloc.tier)
                return (
                  <div
                    key={`${alloc.symbol}-${idx}`}
                    className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(color.bg, "w-3 h-3 rounded-full")} />
                      <div>
                        <div className="font-medium">{alloc.symbol}</div>
                        <div className="text-xs text-gray-500">{alloc.tier}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">
                        ${alloc.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                      <div className={cn("text-sm font-medium", color.text)}>
                        {alloc.percentage.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
