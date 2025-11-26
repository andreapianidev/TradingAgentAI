'use client'

import { useEffect, useState, useCallback } from 'react'
import { supabase, TradingPosition } from '@/lib/supabase'
import { formatCurrency, formatPercent, formatDate, cn, getPnlColor, getDirectionBgColor, getStatusColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, X, Filter, Download, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'

const SYNC_INTERVAL = 30000 // 30 seconds

export default function PositionsPage() {
  const [positions, setPositions] = useState<TradingPosition[]>([])
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all')
  const [symbolFilter, setSymbolFilter] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState<Date | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

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

  // Initial sync and fetch
  useEffect(() => {
    const init = async () => {
      await syncPositions(true)
      await fetchPositions()
    }
    init()
  }, [])

  // Auto-sync every 30 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      await syncPositions(false)
      await fetchPositions()
    }, SYNC_INTERVAL)

    return () => clearInterval(interval)
  }, [syncPositions])

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

  const stats = {
    total: positions.length,
    open: positions.filter(p => p.status === 'open').length,
    closed: positions.filter(p => p.status === 'closed').length,
    totalPnl: positions.reduce((sum, p) => sum + (parseFloat(String(p.realized_pnl || 0))), 0),
    winRate: positions.filter(p => p.status === 'closed').length > 0
      ? (positions.filter(p => p.status === 'closed' && parseFloat(String(p.realized_pnl || 0)) > 0).length /
         positions.filter(p => p.status === 'closed').length) * 100
      : 0
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Positions</h1>
          <p className="text-gray-400 flex items-center gap-2">
            Manage your trading positions
            {lastSync && (
              <span className="text-xs flex items-center gap-1">
                {syncError ? (
                  <AlertCircle className="w-3 h-3 text-red-400" />
                ) : (
                  <CheckCircle className="w-3 h-3 text-green-400" />
                )}
                <span className={syncError ? 'text-red-400' : 'text-green-400'}>
                  Synced {Math.round((Date.now() - lastSync.getTime()) / 1000)}s ago
                </span>
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => syncPositions(true)}
            disabled={syncing}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={cn("w-4 h-4", syncing && "animate-spin")} />
            {syncing ? 'Syncing...' : 'Sync'}
          </button>
          <button
            onClick={exportToCsv}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="stat-label">Total Positions</div>
          <div className="stat-value">{stats.total}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Open</div>
          <div className="stat-value text-green-500">{stats.open}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Closed</div>
          <div className="stat-value text-blue-500">{stats.closed}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Realized P&L</div>
          <div className={cn('stat-value', getPnlColor(stats.totalPnl))}>
            {formatCurrency(stats.totalPnl)}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-400">Filter:</span>
        </div>
        <div className="flex gap-2">
          {(['all', 'open', 'closed'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize',
                filter === status
                  ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              )}
            >
              {status}
            </button>
          ))}
        </div>
        <select
          value={symbolFilter}
          onChange={(e) => setSymbolFilter(e.target.value)}
          className="select w-32"
        >
          <option value="all">All Symbols</option>
          <option value="BTC">BTC</option>
          <option value="ETH">ETH</option>
          <option value="SOL">SOL</option>
        </select>
      </div>

      {/* Positions Table */}
      <div className="card">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
          </div>
        ) : positions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No positions found
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Direction</th>
                  <th>Entry</th>
                  <th>Size</th>
                  <th>Leverage</th>
                  <th>Exit</th>
                  <th>P&L</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => (
                  <tr key={position.id}>
                    <td className="font-medium text-white">{position.symbol}</td>
                    <td>
                      <span className={cn(
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium uppercase',
                        getDirectionBgColor(position.direction)
                      )}>
                        {position.direction === 'long' ? (
                          <ArrowUpRight className="w-3 h-3" />
                        ) : (
                          <ArrowDownRight className="w-3 h-3" />
                        )}
                        {position.direction}
                      </span>
                    </td>
                    <td>
                      <div className="text-white">{formatCurrency(parseFloat(String(position.entry_price)))}</div>
                      <div className="text-xs text-gray-500">{formatDate(position.entry_timestamp)}</div>
                    </td>
                    <td className="text-gray-300">{parseFloat(String(position.quantity)).toFixed(4)}</td>
                    <td>
                      <span className="bg-gray-700/50 px-2 py-0.5 rounded text-sm">
                        {position.leverage}x
                      </span>
                    </td>
                    <td>
                      {position.exit_price ? (
                        <div>
                          <div className="text-white">{formatCurrency(parseFloat(String(position.exit_price)))}</div>
                          <div className="text-xs text-gray-500">{formatDate(position.exit_timestamp!)}</div>
                        </div>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                    <td>
                      <div className={cn('font-medium', getPnlColor(parseFloat(String(position.realized_pnl || position.unrealized_pnl || 0))))}>
                        {formatCurrency(parseFloat(String(position.realized_pnl || position.unrealized_pnl || 0)))}
                      </div>
                      <div className={cn('text-xs', getPnlColor(parseFloat(String(position.realized_pnl_pct || position.unrealized_pnl_pct || 0))))}>
                        {formatPercent(parseFloat(String(position.realized_pnl_pct || position.unrealized_pnl_pct || 0)))}
                      </div>
                    </td>
                    <td>
                      <span className={cn('badge', getStatusColor(position.status))}>
                        {position.status}
                      </span>
                    </td>
                    <td>
                      {position.status === 'open' && (
                        <button
                          onClick={() => handleClosePosition(position.id)}
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors"
                          title="Close position"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
