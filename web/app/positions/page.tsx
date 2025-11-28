'use client'

import { useEffect, useState, useCallback } from 'react'
import { supabase, TradingPosition, TradingPortfolioSnapshot } from '@/lib/supabase'
import { formatCurrency, formatPercent, formatDate, cn, getPnlColor, getDirectionBgColor, getStatusColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, X, Filter, Download, RefreshCw, CheckCircle, AlertCircle, TrendingUp, TrendingDown, Activity, DollarSign, Wallet, PiggyBank, Target, BarChart3 } from 'lucide-react'
import StrategyBadge from '@/components/StrategyBadge'

const SYNC_INTERVAL = 30000 // 30 seconds
const INITIAL_CAPITAL = 100000 // Starting capital for P&L calculations

interface PortfolioStats {
  totalEquity: number
  totalPnl: number
  totalPnlPct: number
  unrealizedPnl: number
  investedValue: number
  exposurePct: number
}

export default function PositionsPage() {
  const [positions, setPositions] = useState<TradingPosition[]>([])
  const [portfolioStats, setPortfolioStats] = useState<PortfolioStats | null>(null)
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all')
  const [symbolFilter, setSymbolFilter] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState<Date | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [mounted, setMounted] = useState(false)

  // Trigger mount animation
  useEffect(() => {
    setMounted(true)
  }, [])

  // Sync positions from Alpaca
  const syncPositions = useCallback(async (showLoading = true) => {
    if (showLoading) setSyncing(true)
    setSyncError(null)

    try {
      const res = await fetch('/api/positions/sync', { method: 'POST' })
      const data = await res.json()

      if (data.success) {
        setLastSync(new Date())
        console.log('Positions synced:', data.results)
      } else {
        setSyncError(data.error || 'Sync failed')
      }
    } catch (error) {
      console.error('Error syncing positions:', error)
      setSyncError('Network error')
    } finally {
      setSyncing(false)
    }
  }, [])

  // Fetch portfolio stats from snapshot and live API
  const fetchPortfolioStats = useCallback(async () => {
    try {
      // Try live API first
      const liveRes = await fetch('/api/account/live')
      const liveData = await liveRes.json()

      if (liveData.success && liveData.account) {
        const equity = liveData.account.equity
        const totalPnl = equity - INITIAL_CAPITAL
        setPortfolioStats({
          totalEquity: equity,
          totalPnl: totalPnl,
          totalPnlPct: (totalPnl / INITIAL_CAPITAL) * 100,
          unrealizedPnl: liveData.account.totalUnrealizedPnl || 0,
          investedValue: liveData.account.positionsValue || 0,
          exposurePct: liveData.account.exposurePct || 0,
        })
        return
      }

      // Fallback to database snapshot
      const { data: snapshot } = await supabase
        .from('trading_portfolio_snapshots')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(1)
        .single()

      if (snapshot) {
        const equity = parseFloat(String(snapshot.total_equity_usdc)) || INITIAL_CAPITAL
        const totalPnl = equity - INITIAL_CAPITAL

        // Calculate invested value from positions
        const { data: openPositions } = await supabase
          .from('trading_positions')
          .select('entry_price, quantity')
          .eq('status', 'open')

        const investedValue = openPositions?.reduce((sum, p) => {
          return sum + (parseFloat(String(p.entry_price)) * parseFloat(String(p.quantity)))
        }, 0) || 0

        // Calculate unrealized P&L from open positions
        const { data: openPnl } = await supabase
          .from('trading_positions')
          .select('unrealized_pnl')
          .eq('status', 'open')

        const unrealizedPnl = openPnl?.reduce((sum, p) => {
          return sum + (parseFloat(String(p.unrealized_pnl || 0)))
        }, 0) || 0

        setPortfolioStats({
          totalEquity: equity,
          totalPnl: totalPnl,
          totalPnlPct: (totalPnl / INITIAL_CAPITAL) * 100,
          unrealizedPnl: unrealizedPnl,
          investedValue: investedValue,
          exposurePct: parseFloat(String(snapshot.exposure_pct)) || 0,
        })
      }
    } catch (error) {
      console.error('Error fetching portfolio stats:', error)
    }
  }, [])

  // Initial sync and fetch
  useEffect(() => {
    const init = async () => {
      await syncPositions(true)
      await Promise.all([fetchPositions(), fetchPortfolioStats()])
    }
    init()
  }, [])

  // Auto-sync every 30 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      await syncPositions(false)
      await Promise.all([fetchPositions(), fetchPortfolioStats()])
    }, SYNC_INTERVAL)

    return () => clearInterval(interval)
  }, [syncPositions, fetchPortfolioStats])

  // Fetch when filters change
  useEffect(() => {
    fetchPositions()
  }, [filter, symbolFilter])

  const fetchPositions = async () => {
    setLoading(true)
    try {
      let query = supabase
        .from('trading_positions')
        .select('*')
        .order('entry_timestamp', { ascending: false })

      if (filter !== 'all') {
        query = query.eq('status', filter)
      }

      if (symbolFilter !== 'all') {
        query = query.eq('symbol', symbolFilter)
      }

      const { data } = await query.limit(100)
      setPositions(data || [])
    } catch (error) {
      console.error('Error fetching positions:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleClosePosition = async (positionId: string) => {
    if (!confirm('Are you sure you want to close this position?')) return

    try {
      const res = await fetch('/api/positions/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position_id: positionId })
      })
      if (res.ok) {
        fetchPositions()
      }
    } catch (error) {
      console.error('Failed to close position:', error)
    }
  }

  const exportToCsv = () => {
    const headers = ['Symbol', 'Direction', 'Entry Date', 'Entry Price', 'Quantity', 'Leverage', 'Status', 'Exit Date', 'Exit Price', 'P&L', 'P&L %']
    const rows = positions.map(p => [
      p.symbol,
      p.direction,
      formatDate(p.entry_timestamp),
      p.entry_price,
      p.quantity,
      p.leverage,
      p.status,
      p.exit_timestamp ? formatDate(p.exit_timestamp) : '',
      p.exit_price || '',
      p.realized_pnl || p.unrealized_pnl || 0,
      p.realized_pnl_pct || p.unrealized_pnl_pct || 0
    ])

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `positions_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  // Calculate unrealized P&L from open positions in current view
  const openPositionsUnrealizedPnl = positions
    .filter(p => p.status === 'open')
    .reduce((sum, p) => sum + (parseFloat(String(p.unrealized_pnl || 0))), 0)

  const stats = {
    total: positions.length,
    open: positions.filter(p => p.status === 'open').length,
    closed: positions.filter(p => p.status === 'closed').length,
    // Use portfolio stats for accurate P&L, fallback to calculated
    totalPnl: portfolioStats?.totalPnl ?? 0,
    totalPnlPct: portfolioStats?.totalPnlPct ?? 0,
    unrealizedPnl: portfolioStats?.unrealizedPnl ?? openPositionsUnrealizedPnl,
    investedValue: portfolioStats?.investedValue ?? 0,
    exposurePct: portfolioStats?.exposurePct ?? 0,
    winRate: positions.filter(p => p.status === 'closed').length > 0
      ? (positions.filter(p => p.status === 'closed' && parseFloat(String(p.realized_pnl || 0)) > 0).length /
         positions.filter(p => p.status === 'closed').length) * 100
      : 0
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={cn(
        "flex items-center justify-between",
        mounted && "animate-fade-in-up"
      )}>
        <div>
          <h1 className="text-2xl font-bold text-white title-gradient cursor-default">
            Positions
          </h1>
          <div className="flex items-center gap-3">
            <p className="text-gray-400 flex items-center gap-2">
              Manage your trading positions
              {lastSync && (
                <span className="text-xs flex items-center gap-1">
                  {syncError ? (
                    <AlertCircle className="w-3 h-3 text-red-400 animate-pulse" />
                  ) : (
                    <CheckCircle className="w-3 h-3 text-green-400 sync-indicator" />
                  )}
                  <span className={cn(
                    "transition-colors duration-300",
                    syncError ? 'text-red-400' : 'text-green-400'
                  )}>
                    Synced {Math.round((Date.now() - lastSync.getTime()) / 1000)}s ago
                  </span>
                </span>
              )}
            </p>
            <div className="h-4 w-px bg-gray-700" />
            <StrategyBadge />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => syncPositions(true)}
            disabled={syncing}
            className="btn btn-secondary action-btn flex items-center gap-2"
          >
            <RefreshCw className={cn(
              "w-4 h-4 transition-transform duration-300",
              syncing && "animate-spin"
            )} />
            {syncing ? 'Syncing...' : 'Sync'}
          </button>
          <button
            onClick={exportToCsv}
            className="btn btn-secondary action-btn flex items-center gap-2"
          >
            <Download className="w-4 h-4 group-hover:animate-bounce" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Portfolio Overview */}
      {portfolioStats && (
        <div className={cn(
          "card p-4 bg-gradient-to-r from-gray-900/80 to-gray-800/50 border-gray-700/50",
          mounted && "animate-fade-in-up"
        )} style={{ animationDelay: '0.1s' }}>
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={cn(
                "p-3 rounded-xl",
                stats.totalPnl >= 0 ? "bg-green-500/10" : "bg-red-500/10"
              )}>
                <Wallet className={cn(
                  "w-8 h-8",
                  stats.totalPnl >= 0 ? "text-green-500" : "text-red-500"
                )} />
              </div>
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wide">Portfolio Value</div>
                <div className="text-2xl font-bold text-white">
                  {formatCurrency(portfolioStats.totalEquity)}
                </div>
                <div className={cn(
                  "flex items-center gap-1 text-sm font-medium",
                  stats.totalPnl >= 0 ? "text-green-500" : "text-red-500"
                )}>
                  {stats.totalPnl >= 0 ? (
                    <TrendingUp className="w-4 h-4" />
                  ) : (
                    <TrendingDown className="w-4 h-4" />
                  )}
                  <span>{stats.totalPnl >= 0 ? '+' : ''}{formatCurrency(stats.totalPnl)}</span>
                  <span className="text-gray-500">({stats.totalPnlPct >= 0 ? '+' : ''}{stats.totalPnlPct.toFixed(2)}%)</span>
                  <span className="text-xs text-gray-500 ml-1">total</span>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                <div className="text-xs text-gray-500">Invested</div>
                <div className="text-lg font-bold text-white">{formatCurrency(stats.investedValue)}</div>
              </div>
              <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                <div className="text-xs text-gray-500">Unrealized P&L</div>
                <div className={cn(
                  "text-lg font-bold",
                  stats.unrealizedPnl >= 0 ? "text-green-500" : "text-red-500"
                )}>
                  {stats.unrealizedPnl >= 0 ? '+' : ''}{formatCurrency(stats.unrealizedPnl)}
                </div>
              </div>
              <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                <div className="text-xs text-gray-500">Exposure</div>
                <div className="text-lg font-bold text-white">{stats.exposurePct.toFixed(1)}%</div>
              </div>
              <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                <div className="text-xs text-gray-500">Open Positions</div>
                <div className="text-lg font-bold text-green-500">{stats.open}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={cn(
          "stat-card stat-card-enhanced group cursor-default",
          mounted && "animate-fade-in-up"
        )} style={{ animationDelay: '0.15s' }}>
          <div className="flex items-center justify-between">
            <div className="stat-label">Total Positions</div>
            <div className="p-2 rounded-lg bg-gray-800/50 group-hover:bg-gray-700/50 transition-colors">
              <Activity className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors icon-bounce" />
            </div>
          </div>
          <div className="stat-value animate-count">{stats.total}</div>
        </div>
        <div className={cn(
          "stat-card stat-card-enhanced group cursor-default",
          mounted && "animate-fade-in-up"
        )} style={{ animationDelay: '0.2s' }}>
          <div className="flex items-center justify-between">
            <div className="stat-label">Open</div>
            <div className="p-2 rounded-lg bg-green-500/10 group-hover:bg-green-500/20 transition-colors">
              <TrendingUp className="w-4 h-4 text-green-500 group-hover:scale-110 transition-transform icon-bounce" />
            </div>
          </div>
          <div className="stat-value text-green-500 animate-count">{stats.open}</div>
        </div>
        <div className={cn(
          "stat-card stat-card-enhanced group cursor-default",
          mounted && "animate-fade-in-up"
        )} style={{ animationDelay: '0.25s' }}>
          <div className="flex items-center justify-between">
            <div className="stat-label">Closed</div>
            <div className="p-2 rounded-lg bg-blue-500/10 group-hover:bg-blue-500/20 transition-colors">
              <CheckCircle className="w-4 h-4 text-blue-500 group-hover:scale-110 transition-transform icon-bounce" />
            </div>
          </div>
          <div className="stat-value text-blue-500 animate-count">{stats.closed}</div>
        </div>
        <div className={cn(
          "stat-card stat-card-enhanced group cursor-default",
          mounted && "animate-fade-in-up"
        )} style={{ animationDelay: '0.3s' }}>
          <div className="flex items-center justify-between">
            <div className="stat-label">Unrealized P&L</div>
            <div className={cn(
              "p-2 rounded-lg transition-colors",
              stats.unrealizedPnl >= 0
                ? "bg-green-500/10 group-hover:bg-green-500/20"
                : "bg-red-500/10 group-hover:bg-red-500/20"
            )}>
              <BarChart3 className={cn(
                "w-4 h-4 group-hover:scale-110 transition-transform icon-bounce",
                stats.unrealizedPnl >= 0 ? "text-green-500" : "text-red-500"
              )} />
            </div>
          </div>
          <div className={cn(
            'stat-value animate-count',
            getPnlColor(stats.unrealizedPnl),
            stats.unrealizedPnl > 0 && 'pnl-positive'
          )}>
            {stats.unrealizedPnl >= 0 ? '+' : ''}{formatCurrency(stats.unrealizedPnl)}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className={cn(
        "flex items-center gap-4 flex-wrap",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.5s' }}>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400 hover:text-green-400 transition-colors cursor-default" />
          <span className="text-sm text-gray-400">Filter:</span>
        </div>
        <div className="flex gap-2">
          {(['all', 'open', 'closed'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={cn(
                'px-4 py-1.5 rounded-lg text-sm font-medium capitalize filter-btn',
                filter === status
                  ? 'bg-green-500/10 text-green-500 border border-green-500/30 shadow-[0_0_10px_rgba(34,197,94,0.2)] active'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/80 border border-transparent'
              )}
            >
              {status}
              {status === 'open' && stats.open > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400">
                  {stats.open}
                </span>
              )}
            </button>
          ))}
        </div>
        <select
          value={symbolFilter}
          onChange={(e) => setSymbolFilter(e.target.value)}
          className="select w-32 transition-all duration-300 hover:border-green-500/50 focus:shadow-[0_0_10px_rgba(34,197,94,0.2)]"
        >
          <option value="all">All Symbols</option>
          <option value="BTC">BTC</option>
          <option value="ETH">ETH</option>
          <option value="SOL">SOL</option>
        </select>
      </div>

      {/* Positions Table */}
      <div className={cn(
        "card overflow-hidden",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.6s' }}>
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <div className="relative">
              <div className="animate-spin rounded-full h-10 w-10 border-2 border-green-500/20 border-t-green-500"></div>
              <div className="absolute inset-0 animate-ping rounded-full h-10 w-10 border border-green-500/30"></div>
            </div>
            <span className="text-gray-400 text-sm animate-pulse">Loading positions...</span>
          </div>
        ) : positions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-gray-500">
            <Activity className="w-12 h-12 text-gray-600 animate-pulse" />
            <span>No positions found</span>
            <button
              onClick={() => syncPositions(true)}
              className="text-sm text-green-500 hover:text-green-400 transition-colors"
            >
              Try syncing positions
            </button>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-gray-400 font-medium">Symbol</th>
                  <th className="text-gray-400 font-medium">Direction</th>
                  <th className="text-gray-400 font-medium">Entry</th>
                  <th className="text-gray-400 font-medium">Size</th>
                  <th className="text-gray-400 font-medium">Leverage</th>
                  <th className="text-gray-400 font-medium">Exit</th>
                  <th className="text-gray-400 font-medium">P&L</th>
                  <th className="text-gray-400 font-medium">Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position, index) => {
                  const pnlValue = parseFloat(String(position.realized_pnl || position.unrealized_pnl || 0))
                  const pnlPctValue = parseFloat(String(position.realized_pnl_pct || position.unrealized_pnl_pct || 0))

                  return (
                    <tr
                      key={position.id}
                      className={cn(
                        "table-row-hover group",
                        mounted && "animate-fade-in-up"
                      )}
                      style={{ animationDelay: `${0.7 + index * 0.05}s` }}
                    >
                      <td className="font-semibold text-white">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-gradient-to-r from-green-400 to-emerald-500 group-hover:animate-pulse"></span>
                          {position.symbol}
                        </div>
                      </td>
                      <td>
                        <span className={cn(
                          'inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold uppercase direction-badge cursor-default',
                          'transition-all duration-300',
                          position.direction === 'long'
                            ? 'bg-green-500/15 text-green-400 border border-green-500/20 hover:bg-green-500/25 hover:shadow-[0_0_10px_rgba(34,197,94,0.3)]'
                            : 'bg-red-500/15 text-red-400 border border-red-500/20 hover:bg-red-500/25 hover:shadow-[0_0_10px_rgba(239,68,68,0.3)]'
                        )}>
                          {position.direction === 'long' ? (
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          ) : (
                            <ArrowDownRight className="w-3.5 h-3.5" />
                          )}
                          {position.direction}
                        </span>
                      </td>
                      <td>
                        <div className="text-white font-medium">{formatCurrency(parseFloat(String(position.entry_price)))}</div>
                        <div className="text-xs text-gray-500 mt-0.5">{formatDate(position.entry_timestamp)}</div>
                      </td>
                      <td className="text-gray-300 font-mono">{parseFloat(String(position.quantity)).toFixed(4)}</td>
                      <td>
                        <span className="bg-gray-700/60 px-2.5 py-1 rounded-lg text-sm font-medium text-gray-300 border border-gray-600/30 hover:bg-gray-600/60 transition-colors cursor-default">
                          {position.leverage}x
                        </span>
                      </td>
                      <td>
                        {position.exit_price ? (
                          <div>
                            <div className="text-white font-medium">{formatCurrency(parseFloat(String(position.exit_price)))}</div>
                            <div className="text-xs text-gray-500 mt-0.5">{formatDate(position.exit_timestamp!)}</div>
                          </div>
                        ) : (
                          <span className="text-gray-600 italic">Active</span>
                        )}
                      </td>
                      <td>
                        <div className={cn(
                          'font-semibold transition-all duration-300',
                          getPnlColor(pnlValue),
                          pnlValue > 0 && 'pnl-positive'
                        )}>
                          {pnlValue >= 0 ? '+' : ''}{formatCurrency(pnlValue)}
                        </div>
                        <div className={cn(
                          'text-xs mt-0.5 font-medium',
                          getPnlColor(pnlPctValue)
                        )}>
                          {pnlPctValue >= 0 ? '+' : ''}{formatPercent(pnlPctValue)}
                        </div>
                      </td>
                      <td>
                        <span className={cn(
                          'badge transition-all duration-300 cursor-default',
                          getStatusColor(position.status),
                          position.status === 'open' && 'badge-animated shadow-[0_0_8px_rgba(34,197,94,0.4)]'
                        )}>
                          <span className={cn(
                            "inline-block w-1.5 h-1.5 rounded-full mr-1.5",
                            position.status === 'open' ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
                          )}></span>
                          {position.status}
                        </span>
                      </td>
                      <td>
                        {position.status === 'open' && (
                          <button
                            onClick={() => handleClosePosition(position.id)}
                            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg close-btn"
                            title="Close position"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
