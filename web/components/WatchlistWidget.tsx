'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Target, RefreshCw, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TradingWatchlist } from '@/lib/supabase'

interface WatchlistWidgetProps {
  className?: string
  maxItems?: number
  autoRefresh?: boolean
  refreshInterval?: number
}

export default function WatchlistWidget({
  className,
  maxItems = 10,
  autoRefresh = true,
  refreshInterval = 60
}: WatchlistWidgetProps) {
  const [watchlist, setWatchlist] = useState<TradingWatchlist[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchWatchlist = async () => {
    try {
      setError(false)
      const res = await fetch('/api/watchlist')
      const data = await res.json()

      if (data.success) {
        setWatchlist(data.watchlist || [])
      } else {
        setError(true)
      }
    } catch (err) {
      console.error('Error fetching watchlist:', err)
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWatchlist()

    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchWatchlist, refreshInterval * 1000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  const getScoreColor = (score: number | undefined | null) => {
    if (!score) return 'text-gray-400'
    if (score >= 75) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-blue-600 dark:text-blue-400'
    if (score >= 45) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getScoreBg = (score: number | undefined | null) => {
    if (!score) return 'bg-gray-100 dark:bg-gray-800'
    if (score >= 75) return 'bg-green-100 dark:bg-green-900/20'
    if (score >= 60) return 'bg-blue-100 dark:bg-blue-900/20'
    if (score >= 45) return 'bg-yellow-100 dark:bg-yellow-900/20'
    return 'bg-red-100 dark:bg-red-900/20'
  }

  const getTierBadge = (tier: string) => {
    const colors = {
      CORE: 'bg-purple-100 text-purple-700 dark:bg-purple-900/20 dark:text-purple-400',
      OPPORTUNISTIC: 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400',
      SATELLITE: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
    }
    return colors[tier as keyof typeof colors] || colors.SATELLITE
  }

  if (loading) {
    return (
      <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow p-6", className)}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Active Watchlist</h3>
          <RefreshCw className="w-5 h-5 animate-spin text-gray-400" />
        </div>
        <div className="text-center py-8 text-gray-500">Loading watchlist...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow p-6", className)}>
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>Failed to load watchlist</span>
        </div>
      </div>
    )
  }

  const displayList = watchlist.slice(0, maxItems)
  const coreCoins = displayList.filter(w => w.tier === 'CORE')
  const opportunisticCoins = displayList.filter(w => w.tier === 'OPPORTUNISTIC')

  return (
    <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow", className)}>
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold">Active Watchlist</h3>
          </div>
          <button
            onClick={fetchWatchlist}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        <div className="flex gap-4 mt-3 text-sm text-gray-600 dark:text-gray-400">
          <span>Total: {watchlist.length}</span>
          <span>Core: {coreCoins.length}</span>
          <span>Opportunistic: {opportunisticCoins.length}</span>
        </div>
      </div>

      <div className="p-6">
        {watchlist.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No active watchlist entries
          </div>
        ) : (
          <div className="space-y-3">
            {displayList.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1">
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{item.symbol}</span>
                      <span className={cn(
                        "text-xs px-2 py-0.5 rounded-full font-medium",
                        getTierBadge(item.tier)
                      )}>
                        {item.tier}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {item.opportunity_level || 'N/A'}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {/* Price change */}
                  {item.percent_change_24h != null && (
                    <div className={cn(
                      "flex items-center gap-1 text-sm font-medium",
                      item.percent_change_24h >= 0
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400"
                    )}>
                      {item.percent_change_24h >= 0 ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : (
                        <TrendingDown className="w-4 h-4" />
                      )}
                      <span>{item.percent_change_24h > 0 ? '+' : ''}{item.percent_change_24h.toFixed(2)}%</span>
                    </div>
                  )}

                  {/* Score */}
                  <div className={cn(
                    "flex items-center justify-center w-16 h-16 rounded-lg",
                    getScoreBg(item.opportunity_score)
                  )}>
                    <div className="text-center">
                      <div className={cn(
                        "text-xl font-bold",
                        getScoreColor(item.opportunity_score)
                      )}>
                        {item.opportunity_score?.toFixed(0) || 'N/A'}
                      </div>
                      <div className="text-xs text-gray-500">score</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {watchlist.length > maxItems && (
          <div className="text-center mt-4 text-sm text-gray-500">
            +{watchlist.length - maxItems} more in watchlist
          </div>
        )}
      </div>
    </div>
  )
}
