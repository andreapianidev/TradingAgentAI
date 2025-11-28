import { TradingPosition } from '@/lib/supabase'
import { formatCurrency, formatPercent, formatDate, cn, getPnlColor, getDirectionBgColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, X, Activity } from 'lucide-react'

interface OpenPositionsTableProps {
  positions: TradingPosition[]
  loading: boolean
  mounted?: boolean
  onClosePosition: (positionId: string) => Promise<void>
  onRefresh?: () => void
}

export default function OpenPositionsTable({
  positions,
  loading,
  mounted = true,
  onClosePosition,
  onRefresh
}: OpenPositionsTableProps) {
  const openPositions = positions.filter(p => p.status === 'open')

  return (
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
      ) : openPositions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-gray-500">
          <Activity className="w-12 h-12 text-gray-600 animate-pulse" />
          <span>No open positions</span>
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
                <th className="text-gray-400 font-medium">P&L</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {openPositions.map((position, index) => {
                const pnlValue = parseFloat(String(position.unrealized_pnl || 0))
                const pnlPctValue = parseFloat(String(position.unrealized_pnl_pct || 0))

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
                      <button
                        onClick={() => onClosePosition(position.id)}
                        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg close-btn"
                        title="Close position"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
