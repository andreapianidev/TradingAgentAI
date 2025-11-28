'use client'

import { useEffect, useState } from 'react'
import { Target, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TradingStrategy } from '@/lib/supabase'

interface StrategyBadgeProps {
  className?: string
  showDetails?: boolean
  autoRefresh?: boolean
  refreshInterval?: number // in seconds
}

export default function StrategyBadge({
  className,
  showDetails = false,
  autoRefresh = true,
  refreshInterval = 60 // Default: refresh every 60 seconds
}: StrategyBadgeProps) {
  const [strategy, setStrategy] = useState<TradingStrategy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchStrategy = async () => {
    try {
      setError(false)
      const res = await fetch('/api/strategies')
      const data = await res.json()

      if (data.success) {
        const activeStrategy = data.strategies?.find((s: TradingStrategy) => s.is_active)
        setStrategy(activeStrategy || null)
      } else {
        setError(true)
      }
    } catch (err) {
      console.error('Error fetching active strategy:', err)
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStrategy()

    // Auto-refresh if enabled
    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchStrategy, refreshInterval * 1000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  if (loading) {
    return (
      <div className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500",
        className
      )}>
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        <span className="text-xs font-medium">Loading...</span>
      </div>
    )
  }

  if (error || !strategy) {
    return (
      <div className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400",
        className
      )}>
        <Target className="w-3.5 h-3.5" />
        <span className="text-xs font-medium">Strategy N/A</span>
      </div>
    )
  }

  const strategyColors = {
    scalping: {
      bg: 'bg-orange-100 dark:bg-orange-900/20',
      text: 'text-orange-700 dark:text-orange-400',
      border: 'border-orange-200 dark:border-orange-800'
    },
    scalping_moderato: {
      bg: 'bg-purple-100 dark:bg-purple-900/20',
      text: 'text-purple-700 dark:text-purple-400',
      border: 'border-purple-200 dark:border-purple-800'
    },
    swing_trading: {
      bg: 'bg-blue-100 dark:bg-blue-900/20',
      text: 'text-blue-700 dark:text-blue-400',
      border: 'border-blue-200 dark:border-blue-800'
    }
  }

  const colors = strategyColors[strategy.name as keyof typeof strategyColors] || {
    bg: 'bg-gray-100 dark:bg-gray-800',
    text: 'text-gray-700 dark:text-gray-300',
    border: 'border-gray-200 dark:border-gray-700'
  }

  if (showDetails) {
    return (
      <div className={cn(
        "inline-flex flex-col gap-1 px-3 py-2 rounded-lg border",
        colors.bg,
        colors.text,
        colors.border,
        className
      )}>
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4" />
          <span className="text-xs font-bold">{strategy.display_name}</span>
        </div>
        <div className="text-xs opacity-80 ml-6">
          {strategy.config.max_position_size_pct}% position • {strategy.config.max_total_exposure_pct}% exposure
        </div>
      </div>
    )
  }

  return (
    <div className={cn(
      "inline-flex items-center gap-2 px-3 py-1.5 rounded-full border",
      colors.bg,
      colors.text,
      colors.border,
      className
    )}>
      <Target className="w-3.5 h-3.5" />
      <span className="text-xs font-bold">{strategy.display_name}</span>
    </div>
  )
}
