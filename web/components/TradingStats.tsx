'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  Target,
  Award,
  BarChart3,
  Clock,
  Zap
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

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1
    }
  }
}

const cardVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 100,
      damping: 15
    }
  }
}

const numberVariants = {
  hidden: { opacity: 0, scale: 0.5 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 200,
      damping: 15
    }
  }
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
      <motion.div
        className="bg-gray-100 dark:bg-gray-800/50 rounded-xl p-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <motion.div
              key={i}
              className="h-20 bg-gray-200 dark:bg-gray-700 rounded-lg"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: [0.5, 1, 0.5], scale: 1 }}
              transition={{
                opacity: { duration: 1.5, repeat: Infinity, delay: i * 0.1 },
                scale: { duration: 0.3, delay: i * 0.05 }
              }}
            />
          ))}
        </div>
      </motion.div>
    )
  }

  if (!stats) {
    return (
      <motion.div
        className="bg-gray-100 dark:bg-gray-800/50 rounded-xl p-6 text-center text-gray-500"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 100, damping: 15 }}
      >
        <motion.div
          animate={{ y: [0, -10, 0], rotate: [0, 5, -5, 0] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
        </motion.div>
        <p>No trading statistics yet</p>
        <p className="text-sm mt-1">Complete some trades to see your stats</p>
      </motion.div>
    )
  }

  const StatCard = ({
    icon: Icon,
    label,
    value,
    subValue,
    color = 'text-gray-900 dark:text-white',
    index = 0,
    gradient
  }: {
    icon: any
    label: string
    value: string
    subValue?: string
    color?: string
    index?: number
    gradient?: string
  }) => (
    <motion.div
      className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-4 relative overflow-hidden group cursor-default"
      variants={cardVariants}
      whileHover={{
        scale: 1.02,
        transition: { type: "spring", stiffness: 400, damping: 15 }
      }}
    >
      {/* Animated gradient background on hover */}
      <motion.div
        className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${gradient || 'bg-gradient-to-br from-blue-500/10 to-purple-500/10'}`}
      />

      {/* Shimmer effect */}
      <motion.div
        className="absolute inset-0 opacity-0 group-hover:opacity-100"
        initial={{ x: '-100%' }}
        whileHover={{
          x: '100%',
          transition: { duration: 0.8, ease: "easeInOut" }
        }}
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)',
        }}
      />

      <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-sm mb-2 relative">
        <motion.div
          whileHover={{ rotate: 360, scale: 1.2 }}
          transition={{ duration: 0.5 }}
        >
          <Icon className="w-4 h-4" />
        </motion.div>
        <span>{label}</span>
      </div>
      <motion.div
        className={`text-xl font-bold ${color} relative`}
        variants={numberVariants}
      >
        {value}
      </motion.div>
      {subValue && (
        <motion.div
          className="text-xs text-gray-500 mt-1 relative"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {subValue}
        </motion.div>
      )}
    </motion.div>
  )

  return (
    <motion.div
      className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm dark:shadow-none"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      <motion.h3
        className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"
        variants={cardVariants}
      >
        <motion.div
          className="p-1.5 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg"
          whileHover={{ rotate: 360 }}
          transition={{ duration: 0.5 }}
        >
          <BarChart3 className="w-5 h-5 text-blue-400" />
        </motion.div>
        Trading Statistics
        <motion.span
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <Zap className="w-4 h-4 text-yellow-400" />
        </motion.span>
      </motion.h3>

      <motion.div
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
        variants={containerVariants}
      >
        <StatCard
          icon={Award}
          label="Win Rate"
          value={`${stats.winRate.toFixed(1)}%`}
          subValue={`${stats.winningTrades}W / ${stats.losingTrades}L`}
          color={stats.winRate >= 50 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
          index={0}
          gradient={stats.winRate >= 50 ? 'bg-gradient-to-br from-green-500/10 to-emerald-500/10' : 'bg-gradient-to-br from-red-500/10 to-rose-500/10'}
        />

        <StatCard
          icon={Target}
          label="Total Trades"
          value={stats.totalTrades.toString()}
          index={1}
        />

        <StatCard
          icon={TrendingUp}
          label="Profit Factor"
          value={stats.profitFactor.toFixed(2)}
          color={stats.profitFactor >= 1 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
          index={2}
          gradient={stats.profitFactor >= 1 ? 'bg-gradient-to-br from-green-500/10 to-emerald-500/10' : 'bg-gradient-to-br from-red-500/10 to-rose-500/10'}
        />

        <StatCard
          icon={stats.totalPnl >= 0 ? TrendingUp : TrendingDown}
          label="Total P&L"
          value={formatCurrency(stats.totalPnl)}
          color={stats.totalPnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
          index={3}
          gradient={stats.totalPnl >= 0 ? 'bg-gradient-to-br from-green-500/10 to-emerald-500/10' : 'bg-gradient-to-br from-red-500/10 to-rose-500/10'}
        />

        <StatCard
          icon={TrendingUp}
          label="Avg Win"
          value={formatCurrency(stats.avgWin)}
          color="text-green-600 dark:text-green-400"
          index={4}
          gradient="bg-gradient-to-br from-green-500/10 to-emerald-500/10"
        />

        <StatCard
          icon={TrendingDown}
          label="Avg Loss"
          value={formatCurrency(stats.avgLoss)}
          color="text-red-600 dark:text-red-400"
          index={5}
          gradient="bg-gradient-to-br from-red-500/10 to-rose-500/10"
        />

        <StatCard
          icon={Award}
          label="Best Trade"
          value={formatCurrency(stats.bestTrade)}
          color="text-green-600 dark:text-green-400"
          index={6}
          gradient="bg-gradient-to-br from-green-500/10 to-emerald-500/10"
        />

        <StatCard
          icon={TrendingDown}
          label="Worst Trade"
          value={formatCurrency(stats.worstTrade)}
          color="text-red-600 dark:text-red-400"
          index={7}
          gradient="bg-gradient-to-br from-red-500/10 to-rose-500/10"
        />

        <StatCard
          icon={Clock}
          label="Avg Duration"
          value={stats.avgTradeDuration}
          index={8}
        />
      </motion.div>
    </motion.div>
  )
}
