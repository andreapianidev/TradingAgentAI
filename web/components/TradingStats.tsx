'use client'

import { useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Target,
  Award,
  BarChart3,
  Clock
} from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { formatCurrency, formatPercent } from '@/lib/utils'

interface TradingStatsData {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  profitFactor: number
  avgWin: number
  avgLoss: number
  bestTrade: number
  worstTrade: number
  totalPnl: number
  avgTradeDuration: string
}

export default function TradingStats() {
  const [stats, setStats] = useState<TradingStatsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    setLoading(true)
    try {
      const { data: positions } = await supabase
        .from('trading_positions')
        .select('*')
        .eq('status', 'closed')
        .not('realized_pnl', 'is', null)

      if (positions && positions.length > 0) {
        const wins = positions.filter(p => (p.realized_pnl || 0) > 0)
        const losses = positions.filter(p => (p.realized_pnl || 0) < 0)

        const totalPnl = positions.reduce((sum, p) => sum + (p.realized_pnl || 0), 0)
        const grossProfit = wins.reduce((sum, p) => sum + (p.realized_pnl || 0), 0)
        const grossLoss = Math.abs(losses.reduce((sum, p) => sum + (p.realized_pnl || 0), 0))

        const avgWin = wins.length > 0
          ? wins.reduce((sum, p) => sum + (p.realized_pnl || 0), 0) / wins.length
          : 0
        const avgLoss = losses.length > 0
          ? Math.abs(losses.reduce((sum, p) => sum + (p.realized_pnl || 0), 0) / losses.length)
          : 0

        const pnls = positions.map(p => p.realized_pnl || 0)
        const bestTrade = Math.max(...pnls)
        const worstTrade = Math.min(...pnls)

        let avgDurationMs = 0
        const tradesWithDuration = positions.filter(p => p.entry_timestamp && p.exit_timestamp)
        if (tradesWithDuration.length > 0) {
          avgDurationMs = tradesWithDuration.reduce((sum, p) => {
            const entry = new Date(p.entry_timestamp).getTime()
            const exit = new Date(p.exit_timestamp).getTime()
            return sum + (exit - entry)
          }, 0) / tradesWithDuration.length
        }

        const avgDurationHours = avgDurationMs / (1000 * 60 * 60)
        let avgTradeDuration = ''
        if (avgDurationHours < 1) {
          avgTradeDuration = `${Math.round(avgDurationMs / (1000 * 60))}m`
        } else if (avgDurationHours < 24) {
          avgTradeDuration = `${avgDurationHours.toFixed(1)}h`
        } else {
          avgTradeDuration = `${(avgDurationHours / 24).toFixed(1)}d`
        }

        setStats({
          totalTrades: positions.length,
          winningTrades: wins.length,
          losingTrades: losses.length,
          winRate: (wins.length / positions.length) * 100,
          profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 10 : 0,
          avgWin,
          avgLoss,
          bestTrade,
          worstTrade,
          totalPnl,
          avgTradeDuration: avgTradeDuration || 'N/A'
        })
      } else {
        setStats(null)
      }
    } catch (error) {
      console.error('Error fetching trading stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse bg-gray-100 dark:bg-gray-800/50 rounded-xl p-6">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="bg-gray-100 dark:bg-gray-800/50 rounded-xl p-6 text-center text-gray-500">
        <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>No trading statistics yet</p>
        <p className="text-sm mt-1">Complete some trades to see your stats</p>
      </div>
    )
  }

  const StatCard = ({
    icon: Icon,
    label,
    value,
    subValue,
    color = 'text-gray-900 dark:text-white'
  }: {
    icon: any
    label: string
    value: string
    subValue?: string
    color?: string
  }) => (
    <div className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-4">
      <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-sm mb-2">
        <Icon className="w-4 h-4" />
        <span>{label}</span>
      </div>
      <div className={`text-xl font-bold ${color}`}>{value}</div>
      {subValue && <div className="text-xs text-gray-500 mt-1">{subValue}</div>}
    </div>
  )

  return (
    <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm dark:shadow-none">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <BarChart3 className="w-5 h-5" />
        Trading Statistics
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Award}
          label="Win Rate"
          value={`${stats.winRate.toFixed(1)}%`}
          subValue={`${stats.winningTrades}W / ${stats.losingTrades}L`}
          color={stats.winRate >= 50 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
        />

        <StatCard
          icon={Target}
          label="Total Trades"
          value={stats.totalTrades.toString()}
        />

        <StatCard
          icon={TrendingUp}
          label="Profit Factor"
          value={stats.profitFactor.toFixed(2)}
          color={stats.profitFactor >= 1 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
        />

        <StatCard
          icon={stats.totalPnl >= 0 ? TrendingUp : TrendingDown}
          label="Total P&L"
          value={formatCurrency(stats.totalPnl)}
          color={stats.totalPnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
        />

        <StatCard
          icon={TrendingUp}
          label="Avg Win"
          value={formatCurrency(stats.avgWin)}
          color="text-green-600 dark:text-green-400"
        />

        <StatCard
          icon={TrendingDown}
          label="Avg Loss"
          value={formatCurrency(stats.avgLoss)}
          color="text-red-600 dark:text-red-400"
        />

        <StatCard
          icon={Award}
          label="Best Trade"
          value={formatCurrency(stats.bestTrade)}
          color="text-green-600 dark:text-green-400"
        />

        <StatCard
          icon={TrendingDown}
          label="Worst Trade"
          value={formatCurrency(stats.worstTrade)}
          color="text-red-600 dark:text-red-400"
        />

        <StatCard
          icon={Clock}
          label="Avg Duration"
          value={stats.avgTradeDuration}
        />
      </div>
    </div>
  )
}
