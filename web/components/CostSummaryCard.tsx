'use client'

import { useEffect, useState } from 'react'
import { DollarSign, Cpu, TrendingUp } from 'lucide-react'
import { supabase, TradingCost } from '@/lib/supabase'
import { cn } from '@/lib/utils'
import Link from 'next/link'

interface CostData {
  total: number
  llm: number
  fees: number
  llmCalls: number
}

export default function CostSummaryCard() {
  const [todayCosts, setTodayCosts] = useState<CostData | null>(null)
  const [monthCosts, setMonthCosts] = useState<number>(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCosts()
    const interval = setInterval(fetchCosts, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const fetchCosts = async () => {
    try {
      const today = new Date().toISOString().split('T')[0]
      const monthStart = new Date()
      monthStart.setDate(1)
      monthStart.setHours(0, 0, 0, 0)

      // Get today's costs
      const { data: todayData } = await supabase
        .from('trading_costs')
        .select('cost_type, cost_usd')
        .gte('created_at', today)

      if (todayData) {
        const llmCosts = todayData
          .filter((c: TradingCost) => c.cost_type === 'llm')
          .reduce((sum: number, c: TradingCost) => sum + Number(c.cost_usd), 0)
        const feeCosts = todayData
          .filter((c: TradingCost) => c.cost_type === 'trading_fee')
          .reduce((sum: number, c: TradingCost) => sum + Number(c.cost_usd), 0)

        setTodayCosts({
          total: llmCosts + feeCosts,
          llm: llmCosts,
          fees: feeCosts,
          llmCalls: todayData.filter((c: TradingCost) => c.cost_type === 'llm').length
        })
      } else {
        setTodayCosts({ total: 0, llm: 0, fees: 0, llmCalls: 0 })
      }

      // Get month-to-date costs
      const { data: monthData } = await supabase
        .from('trading_costs')
        .select('cost_usd')
        .gte('created_at', monthStart.toISOString())

      if (monthData) {
        setMonthCosts(monthData.reduce((sum: number, c: { cost_usd: number }) => sum + Number(c.cost_usd), 0))
      }
    } catch (error) {
      console.error('Error fetching costs:', error)
      setTodayCosts({ total: 0, llm: 0, fees: 0, llmCalls: 0 })
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    if (value < 0.01 && value > 0) {
      return `$${value.toFixed(4)}`
    }
    return `$${value.toFixed(2)}`
  }

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 p-6 animate-pulse">
        <div className="h-24 bg-gray-200 dark:bg-gray-700/50 rounded-lg"></div>
      </div>
    )
  }

  return (
    <Link href="/costs" className="block">
      <div className="bg-white dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 p-6 hover:border-yellow-500/40 transition-all duration-300 group cursor-pointer">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-yellow-500/10 group-hover:bg-yellow-500/20 transition-colors">
              <DollarSign className="w-5 h-5 text-yellow-500" />
            </div>
            <h3 className="font-medium text-gray-900 dark:text-white">Operating Costs</h3>
          </div>
          <span className="text-xs text-gray-500 group-hover:text-yellow-500 transition-colors">
            View Details &rarr;
          </span>
        </div>

        <div className="space-y-3">
          {/* Today's Total */}
          <div className="flex items-center justify-between">
            <span className="text-gray-500 dark:text-gray-400 text-sm">Today</span>
            <span className="text-xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(todayCosts?.total || 0)}
            </span>
          </div>

          {/* Breakdown */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-200 dark:border-gray-700/50">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-500" />
              <div>
                <div className="text-xs text-gray-500">LLM API</div>
                <div className="text-sm font-medium text-purple-600 dark:text-purple-400">
                  {formatCurrency(todayCosts?.llm || 0)}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-500" />
              <div>
                <div className="text-xs text-gray-500">Trading Fees</div>
                <div className="text-sm font-medium text-blue-600 dark:text-blue-400">
                  {formatCurrency(todayCosts?.fees || 0)}
                </div>
              </div>
            </div>
          </div>

          {/* Month-to-date */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700/50">
            <span className="text-xs text-gray-500">This Month</span>
            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
              {formatCurrency(monthCosts)}
            </span>
          </div>
        </div>
      </div>
    </Link>
  )
}
