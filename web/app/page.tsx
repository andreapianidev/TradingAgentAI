'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Target,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw
} from 'lucide-react'
import { formatCurrency, formatPercent, formatTimeAgo, cn, getPnlColor, getDirectionBgColor } from '@/lib/utils'
import { supabase, TradingPortfolioSnapshot, TradingPosition, TradingDecision, TradingAlert } from '@/lib/supabase'
import EquityChart from '@/components/EquityChart'
import RecentTrades from '@/components/RecentTrades'
import OpenPositions from '@/components/OpenPositions'
import AlertsPanel from '@/components/AlertsPanel'
import CostSummaryCard from '@/components/CostSummaryCard'
import StrategyBadge from '@/components/StrategyBadge'

const SYNC_INTERVAL = 30000 // 30 seconds

interface DashboardStats {
  totalEquity: number
  availableBalance: number
  marginUsed: number
  totalPnl: number
  totalPnlPct: number
  dailyPnl: number
  dailyPnlPct: number
  openPositionsCount: number
  exposurePct: number
  winRate: number
  totalTrades: number
  timestamp?: string
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [positions, setPositions] = useState<TradingPosition[]>([])
  const [recentDecisions, setRecentDecisions] = useState<TradingDecision[]>([])
  const [alerts, setAlerts] = useState<TradingAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState<Date | null>(null)
  const [syncMessage, setSyncMessage] = useState<string | null>(null)

  // Helper: Calculate next bot run time (every 15 minutes)
  const calculateNextRun = (lastRunTimestamp?: string): number => {
    if (!lastRunTimestamp) return 15

    const lastRun = new Date(lastRunTimestamp).getTime()
    const now = Date.now()
    const elapsed = (now - lastRun) / 1000 / 60 // minutes
    const next = Math.max(0, 15 - Math.floor(elapsed))

    return next
  }

  // Helper: Determine indicator color based on data freshness
  const getDataFreshnessColor = (timestamp?: string): string => {
    if (!timestamp) return "bg-gray-500"

    const age = (Date.now() - new Date(timestamp).getTime()) / 1000 / 60 // minutes

    if (age < 5) return "bg-green-500 animate-pulse"
    if (age < 20) return "bg-yellow-500"
    return "bg-red-500 animate-pulse"
  }

  // Manual sync from Alpaca (optional feature)
  const manualSyncAlpaca = async () => {
    setSyncing(true)
    setSyncMessage(null)
    try {
      const res = await fetch('/api/positions/sync', { method: 'POST' })
      const data = await res.json()

      if (data.success) {
        setLastSync(new Date())
        setSyncMessage('✓ Synced successfully from Alpaca')
        await fetchDashboardData()
      } else if (!data.configured) {
        setSyncMessage('ℹ️ Alpaca sync not available (credentials not configured)')
      } else {
        setSyncMessage(`⚠️ Sync failed: ${data.error || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Sync error:', error)
      setSyncMessage('❌ Sync error: Could not connect to API')
    } finally {
      setSyncing(false)
      // Clear message after 5 seconds
      setTimeout(() => setSyncMessage(null), 5000)
    }
  }

  // Initial data fetch (no Alpaca sync)
  useEffect(() => {
    fetchDashboardData()
  }, [])

  // Auto-refresh Supabase data every 10 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      await fetchDashboardData()
    }, 10000)
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
          marginUsed: parseFloat(snapshot.margin_used_usdc) || 0,
          totalPnl: parseFloat(snapshot.total_pnl) || 0,
          totalPnlPct: parseFloat(snapshot.total_pnl_pct) || 0,
          dailyPnl: parseFloat(snapshot.daily_pnl) || 0,
          dailyPnlPct: parseFloat(snapshot.daily_pnl_pct) || 0,
          openPositionsCount: snapshot.open_positions_count || 0,
          exposurePct: parseFloat(snapshot.exposure_pct) || 0,
          winRate: parseFloat(snapshot.win_rate) || 0,
          totalTrades: snapshot.total_trades || 0,
          timestamp: snapshot.timestamp
        })
      } else {
        // No data yet - will show loading state
        setStats(null)
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

  // Show awaiting state when no data
  const showAwaitingState = !stats

  return (
    <div className="space-y-6">
      {/* Bot Status Bar */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between bg-gray-800/50 rounded-lg px-4 py-2 border border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-2 h-2 rounded-full",
              getDataFreshnessColor(stats?.timestamp)
            )} />
            <div className="flex flex-col">
              <span className="text-sm text-gray-300">
                {stats?.timestamp ? `Last bot run: ${formatTimeAgo(stats.timestamp)}` : 'Waiting for first bot run...'}
              </span>
              <span className="text-xs text-gray-500">
                Bot runs every 15 minutes • Next run in ~{calculateNextRun(stats?.timestamp)} min
              </span>
            </div>
            <div className="h-8 w-px bg-gray-700" />
            <StrategyBadge />
          </div>
          <button
            onClick={manualSyncAlpaca}
            disabled={syncing}
            className="text-sm text-gray-400 hover:text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
            title="Manually sync positions from Alpaca (if credentials configured)"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", syncing && "animate-spin")} />
            Sync Alpaca
          </button>
        </div>
        {syncMessage && (
          <div className={cn(
            "text-xs px-4 py-2 rounded-lg border",
            syncMessage.includes('✓') && "bg-green-500/10 border-green-500/20 text-green-400",
            syncMessage.includes('ℹ️') && "bg-blue-500/10 border-blue-500/20 text-blue-400",
            syncMessage.includes('⚠️') && "bg-yellow-500/10 border-yellow-500/20 text-yellow-400",
            syncMessage.includes('❌') && "bg-red-500/10 border-red-500/20 text-red-400"
          )}>
            {syncMessage}
          </div>
        )}
      </div>

      {showAwaitingState && (
        <div className="bg-yellow-100 dark:bg-yellow-500/10 border border-yellow-300 dark:border-yellow-500/20 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-500" />
          <div>
            <p className="text-yellow-700 dark:text-yellow-500 font-medium">Awaiting trading data</p>
            <p className="text-gray-600 dark:text-gray-400 text-sm">Start the trading bot to see real-time data</p>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Equity */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div className="stat-label">Total Equity</div>
            <DollarSign className="w-5 h-5 text-gray-500" />
          </div>
          <div className="stat-value">{stats ? formatCurrency(stats.totalEquity) : '—'}</div>
          <div className={cn('stat-change', stats ? getPnlColor(stats.totalPnlPct) : 'text-gray-500')}>
            {stats ? `${formatPercent(stats.totalPnlPct)} all time` : 'No data'}
          </div>
          {stats && (
            <div className="mt-2 pt-2 border-t border-gray-700/50 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Cash</span>
                <span className="text-gray-300">{formatCurrency(stats.availableBalance)}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Invested</span>
                <span className="text-gray-300">{formatCurrency(stats.marginUsed)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Daily P&L */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div className="stat-label">Daily P&L</div>
            {stats && stats.dailyPnl >= 0 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </div>
          <div className={cn('stat-value', stats ? getPnlColor(stats.dailyPnl) : 'text-gray-500')}>
            {stats ? formatCurrency(stats.dailyPnl) : '—'}
          </div>
          <div className={cn('stat-change', stats ? getPnlColor(stats.dailyPnlPct) : 'text-gray-500')}>
            {stats ? `${formatPercent(stats.dailyPnlPct)} today` : 'No data'}
          </div>
        </div>

        {/* Win Rate */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div className="stat-label">Win Rate</div>
            <Target className="w-5 h-5 text-gray-500" />
          </div>
          <div className="stat-value">{stats ? `${(stats.winRate * 100).toFixed(1)}%` : '—'}</div>
          <div className="stat-change text-gray-400">
            {stats ? `${stats.totalTrades} total trades` : 'No trades'}
          </div>
        </div>

        {/* Exposure */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <div className="stat-label">Exposure</div>
            <Activity className="w-5 h-5 text-gray-500" />
          </div>
          <div className="stat-value">{stats ? `${stats.exposurePct.toFixed(1)}%` : '—'}</div>
          <div className="stat-change text-gray-400">
            {stats ? `${stats.openPositionsCount} open positions` : 'No positions'}
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

        {/* Right Column: Alerts + Costs */}
        <div className="space-y-6">
          <AlertsPanel alerts={alerts} />
          <CostSummaryCard />
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Open Positions */}
        <OpenPositions positions={positions} onRefresh={fetchDashboardData} />

        {/* Recent Trades */}
        <RecentTrades decisions={recentDecisions} />
      </div>
    </div>
  )
}
