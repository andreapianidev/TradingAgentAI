'use client'

import { useState } from 'react'
import { TradingPosition } from '@/lib/supabase'
import { formatCurrency, formatPercent, formatTimeAgo, cn, getPnlColor, getDirectionBgColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, X, RefreshCw } from 'lucide-react'

interface OpenPositionsProps {
  positions: TradingPosition[]
  onRefresh?: () => void
}

export default function OpenPositions({ positions, onRefresh }: OpenPositionsProps) {
  const [syncing, setSyncing] = useState(false)

  const handleSyncPositions = async () => {
    setSyncing(true)
    try {
      const res = await fetch('/api/positions/sync', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        onRefresh?.()
      } else {
        console.error('Sync failed:', data.error)
      }
    } catch (error) {
      console.error('Failed to sync positions:', error)
    } finally {
      setSyncing(false)
    }
  }

  const handleClosePosition = async (positionId: string) => {
    try {
      const res = await fetch('/api/positions/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position_id: positionId })
      })
      if (res.ok) {
        window.location.reload()
      }
    } catch (error) {
      console.error('Failed to close position:', error)
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Open Positions</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500 dark:text-gray-400">{positions.length} active</span>
          <button
            onClick={handleSyncPositions}
            disabled={syncing}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg transition-colors disabled:opacity-50"
            title="Sync positions from Alpaca"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", syncing && "animate-spin")} />
            {syncing ? 'Syncing...' : 'Sync Alpaca'}
          </button>
        </div>
      </div>

      {positions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No open positions
        </div>
      ) : (
        <div className="space-y-3">
          {positions.map((position) => (
            <div
              key={position.id}
              className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-4 border border-gray-200 dark:border-gray-700/50"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-semibold text-gray-900 dark:text-white">
                    {position.symbol}
                  </span>
                  <span className={cn(
                    'px-2 py-0.5 rounded text-xs font-medium uppercase',
                    getDirectionBgColor(position.direction)
                  )}>
                    {position.direction === 'long' ? (
                      <span className="flex items-center gap-1">
                        <ArrowUpRight className="w-3 h-3" />
                        Long
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <ArrowDownRight className="w-3 h-3" />
                        Short
                      </span>
                    )}
                  </span>
                  <span className="text-xs text-gray-500 bg-gray-200 dark:bg-gray-700/50 px-2 py-0.5 rounded">
                    {position.leverage}x
                  </span>
                </div>
                <button
                  onClick={() => handleClosePosition(position.id)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-100 dark:hover:bg-red-500/10 rounded transition-colors"
                  title="Close position"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-gray-500">Entry Price</div>
                  <div className="text-gray-900 dark:text-white font-medium">
                    {formatCurrency(parseFloat(String(position.entry_price)))}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">Size</div>
                  <div className="text-gray-900 dark:text-white font-medium">
                    {parseFloat(String(position.quantity)).toFixed(4)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">Unrealized P&L</div>
                  <div className={cn(
                    'font-medium',
                    getPnlColor(parseFloat(String(position.unrealized_pnl || 0)))
                  )}>
                    {formatCurrency(parseFloat(String(position.unrealized_pnl || 0)))}
                    <span className="text-xs ml-1">
                      ({formatPercent(parseFloat(String(position.unrealized_pnl_pct || 0)))})
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50 text-xs text-gray-500">
                <div className="flex items-center gap-4">
                  {position.stop_loss_price && (
                    <span>
                      SL: <span className="text-red-600 dark:text-red-500">{formatCurrency(parseFloat(String(position.stop_loss_price)))}</span>
                    </span>
                  )}
                  {position.take_profit_price && (
                    <span>
                      TP: <span className="text-green-600 dark:text-green-500">{formatCurrency(parseFloat(String(position.take_profit_price)))}</span>
                    </span>
                  )}
                </div>
                <span>{formatTimeAgo(position.entry_timestamp)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
