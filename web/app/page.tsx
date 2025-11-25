'use client'

import { useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Target,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { formatCurrency, formatPercent, formatTimeAgo, cn, getPnlColor, getDirectionBgColor } from '@/lib/utils'
import { supabase, TradingPortfolioSnapshot, TradingPosition, TradingDecision, TradingAlert } from '@/lib/supabase'
import EquityChart from '@/components/EquityChart'
import RecentTrades from '@/components/RecentTrades'
import OpenPositions from '@/components/OpenPositions'
import AlertsPanel from '@/components/AlertsPanel'

interface DashboardStats {
  totalEquity: number
  availableBalance: number
  totalPnl: number
  totalPnlPct: number
  dailyPnl: number
  dailyPnlPct: number
  openPositionsCount: number
  exposurePct: number
  winRate: number
  totalTrades: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [positions, setPositions] = useState<TradingPosition[]>([])
  const [recentDecisions, setRecentDecisions] = useState<TradingDecision[]>([])
  const [alerts, setAlerts] = useState<TradingAlert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const fetchDashboardData = async () => {
    try {
      // Fetch latest portfolio snapshot
      const { data: snapshot } = await supabase
        .from('trading_portfolio_snapshots')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(1)
        .single()

      if (snapshot) {
        setStats({
          totalEquity: parseFloat(snapshot.total_equity_usdc) || 10000,
          availableBalance: parseFloat(snapshot.available_balance_usdc) || 10000,
          totalPnl: parseFloat(snapshot.total_pnl) || 0,
          totalPnlPct: parseFloat(snapshot.total_pnl_pct) || 0,
          dailyPnl: parseFloat(snapshot.daily_pnl) || 0,
          dailyPnlPct: parseFloat(snapshot.daily_pnl_pct) || 0,
          openPositionsCount: snapshot.open_positions_count || 0,
          exposurePct: parseFloat(snapshot.exposure_pct) || 0,
          winRate: parseFloat(snapshot.win_rate) || 0,
          totalTrades: snapshot.total_trades || 0
        })
      } else {
        // Default stats for new accounts
        setStats({
          totalEquity: 10000,
          availableBalance: 10000,
          totalPnl: 0,
          totalPnlPct: 0,
          dailyPnl: 0,
          dailyPnlPct: 0,
          openPositionsCount: 0,
          exposurePct: 0,
          winRate: 0,
          totalTrades: 0
        })
      }

      // Fetch open positions
      const { data: positionsData } = await supabase
        .from('trading_positions')
        .select('*')
        .eq('status', 'open')
        .order('entry_timestamp', { ascending: false })

      setPositions(positionsData || [])

      // Fetch recent decisions
      const { data: decisionsData } = await supabase
        .from('trading_decisions')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(10)

      setRecentDecisions(decisionsData || [])

      // Fetch unread alerts
      const { data: alertsData } = await supabase
        .from('trading_alerts')
        .select('*')
        .eq('is_read', false)
        .order('created_at', { ascending: false })
        .limit(5)

      setAlerts(alertsData || [])

    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Equity */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div className="stat-label">Total Equity</div>
            <DollarSign className="w-5 h-5 text-gray-500" />
          </div>
          <div className="stat-value">{formatCurrency(stats?.totalEquity || 0)}</div>
          <div className={cn('stat-change', getPnlColor(stats?.totalPnlPct || 0))}>
            {formatPercent(stats?.totalPnlPct || 0)} all time
          </div>
        </div>

        {/* Daily P&L */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div className="stat-label">Daily P&L</div>
            {(stats?.dailyPnl || 0) >= 0 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </div>
          <div className={cn('stat-value', getPnlColor(stats?.dailyPnl || 0))}>
            {formatCurrency(stats?.dailyPnl || 0)}
          </div>
          <div className={cn('stat-change', getPnlColor(stats?.dailyPnlPct || 0))}>
            {formatPercent(stats?.dailyPnlPct || 0)} today
          </div>
        </div>

        {/* Win Rate */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div className="stat-label">Win Rate</div>
            <Target className="w-5 h-5 text-gray-500" />
          </div>
          <div className="stat-value">{((stats?.winRate || 0) * 100).toFixed(1)}%</div>
          <div className="stat-change text-gray-400">
            {stats?.totalTrades || 0} total trades
          </div>
        </div>

        {/* Exposure */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div className="stat-label">Exposure</div>
            <Activity className="w-5 h-5 text-gray-500" />
          </div>
          <div className="stat-value">{(stats?.exposurePct || 0).toFixed(1)}%</div>
          <div className="stat-change text-gray-400">
            {stats?.openPositionsCount || 0} open positions
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Equity Chart - Takes 2 columns */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Equity Curve</h2>
            </div>
            <EquityChart />
          </div>
        </div>

        {/* Alerts Panel */}
        <div>
          <AlertsPanel alerts={alerts} />
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Open Positions */}
        <OpenPositions positions={positions} />

        {/* Recent Trades */}
        <RecentTrades decisions={recentDecisions} />
      </div>
    </div>
  )
}
