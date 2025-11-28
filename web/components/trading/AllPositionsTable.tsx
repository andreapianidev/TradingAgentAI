import { useState } from 'react'
import { TradingPosition } from '@/lib/supabase'
import { formatCurrency, formatPercent, formatDate, cn, getPnlColor, getStatusColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, X, Activity, Filter, Download } from 'lucide-react'

interface AllPositionsTableProps {
  positions: TradingPosition[]
  loading: boolean
  mounted?: boolean
  onClosePosition: (positionId: string) => Promise<void>
  onRefresh?: () => void
}

export default function AllPositionsTable({
  positions,
  loading,
  mounted = true,
  onClosePosition,
  onRefresh
}: AllPositionsTableProps) {
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all')
  const [symbolFilter, setSymbolFilter] = useState<string>('all')

  const filteredPositions = positions.filter(p => {
    if (filter !== 'all' && p.status !== filter) return false
    if (symbolFilter !== 'all' && p.symbol !== symbolFilter) return false
    return true
  })

  const stats = {
    total: filteredPositions.length,
    open: filteredPositions.filter(p => p.status === 'open').length,
    closed: filteredPositions.filter(p => p.status === 'closed').length
  }

  const exportToCsv = () => {
    const headers = ['Symbol', 'Direction', 'Entry Date', 'Entry Price', 'Quantity', 'Leverage', 'Status', 'Exit Date', 'Exit Price', 'P&L', 'P&L %']
    const rows = filteredPositions.map(p => [
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
    a.download = `all_positions_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  return (
    <div className="space-y-4">
      {/* Filters and Export */}
      <div className={cn(
        "flex items-center justify-between flex-wrap gap-4",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.2s' }}>
        <div className="flex items-center gap-4 flex-wrap">
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
        <button
          onClick={exportToCsv}
          className="btn btn-secondary action-btn flex items-center gap-2"
        >
          <Download className="w-4 h-4 group-hover:animate-bounce" />
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div className={cn(
        "card overflow-hidden",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.4s' }}>
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <div className="relative">
              <div className="animate-spin rounded-full h-10 w-10 border-2 border-green-500/20 border-t-green-500"></div>
              <div className="absolute inset-0 animate-ping rounded-full h-10 w-10 border border-green-500/30"></div>
            </div>
            <span className="text-gray-400 text-sm animate-pulse">Loading positions...</span>
          </div>
        ) : filteredPositions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-gray-500">
            <Activity className="w-12 h-12 text-gray-600 animate-pulse" />
            <span>No positions found</span>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="text-sm text-green-500 hover:text-green-400 transition-colors"
              >
                Try refreshing
              </button>
            )}
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
                {filteredPositions.map((position, index) => {
                  const pnlValue = parseFloat(String(position.realized_pnl || position.unrealized_pnl || 0))
                  const pnlPctValue = parseFloat(String(position.realized_pnl_pct || position.unrealized_pnl_pct || 0))

                  return (
                    <tr
                      key={position.id}
                      className={cn(
                        "table-row-hover group",
                        mounted && "animate-fade-in-up"
                      )}
                      style={{ animationDelay: `${0.5 + index * 0.05}s` }}
                    >
                      <td className="font-semibold text-white">
                        <div className="flex items-center gap-2">
                          <span className={cn(
                            "w-2 h-2 rounded-full",
                            position.status === 'open'
                              ? "bg-gradient-to-r from-green-400 to-emerald-500 group-hover:animate-pulse"
                              : "bg-gray-600"
                          )}></span>
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
                            onClick={() => onClosePosition(position.id)}
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
