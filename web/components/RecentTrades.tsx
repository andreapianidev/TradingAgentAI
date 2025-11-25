'use client'

import { TradingDecision } from '@/lib/supabase'
import { formatCurrency, formatTimeAgo, cn, getStatusColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, Minus, Eye } from 'lucide-react'
import { useState } from 'react'

interface RecentTradesProps {
  decisions: TradingDecision[]
}

export default function RecentTrades({ decisions }: RecentTradesProps) {
  const [selectedDecision, setSelectedDecision] = useState<TradingDecision | null>(null)

  const getActionIcon = (action: string, direction?: string) => {
    if (action === 'hold') {
      return <Minus className="w-4 h-4 text-gray-500" />
    }
    if (action === 'open') {
      return direction === 'long' ? (
        <ArrowUpRight className="w-4 h-4 text-green-500" />
      ) : (
        <ArrowDownRight className="w-4 h-4 text-red-500" />
      )
    }
    if (action === 'close') {
      return direction === 'long' ? (
        <ArrowDownRight className="w-4 h-4 text-red-500" />
      ) : (
        <ArrowUpRight className="w-4 h-4 text-green-500" />
      )
    }
    return null
  }

  const getActionLabel = (decision: TradingDecision) => {
    if (decision.action === 'hold') return 'HOLD'
    if (decision.action === 'open') {
      return `OPEN ${decision.direction?.toUpperCase()}`
    }
    if (decision.action === 'close') {
      return `CLOSE ${decision.direction?.toUpperCase()}`
    }
    return decision.action.toUpperCase()
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Recent Decisions</h2>
        <span className="text-sm text-gray-400">{decisions.length} latest</span>
      </div>

      {decisions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No trading decisions yet
        </div>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Symbol</th>
                <th>Action</th>
                <th>Confidence</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((decision) => (
                <tr key={decision.id}>
                  <td className="text-gray-400 text-sm">
                    {formatTimeAgo(decision.timestamp)}
                  </td>
                  <td className="font-medium text-white">
                    {decision.symbol}
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      {getActionIcon(decision.action, decision.direction || undefined)}
                      <span className={cn(
                        'text-sm font-medium',
                        decision.action === 'hold' ? 'text-gray-500' :
                        decision.direction === 'long' ? 'text-green-500' : 'text-red-500'
                      )}>
                        {getActionLabel(decision)}
                      </span>
                      {decision.leverage && decision.leverage > 1 && (
                        <span className="text-xs text-gray-500 bg-gray-700/50 px-1.5 py-0.5 rounded">
                          {decision.leverage}x
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full rounded-full',
                            (decision.confidence || 0) >= 0.7 ? 'bg-green-500' :
                            (decision.confidence || 0) >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                          )}
                          style={{ width: `${(decision.confidence || 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-400">
                        {((decision.confidence || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className={cn(
                      'badge',
                      getStatusColor(decision.execution_status)
                    )}>
                      {decision.execution_status}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => setSelectedDecision(decision)}
                      className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
                      title="View reasoning"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reasoning Modal */}
      {selectedDecision && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-700">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white">
                  Decision Reasoning
                </h3>
                <button
                  onClick={() => setSelectedDecision(null)}
                  className="p-1 text-gray-400 hover:text-white"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <div className="text-sm text-gray-500">Symbol</div>
                  <div className="text-white font-medium">{selectedDecision.symbol}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Action</div>
                  <div className="text-white font-medium">{getActionLabel(selectedDecision)}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Confidence</div>
                  <div className="text-white font-medium">
                    {((selectedDecision.confidence || 0) * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Timestamp</div>
                  <div className="text-white font-medium">
                    {new Date(selectedDecision.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-2">Reasoning</div>
                <div className="bg-gray-800 rounded-lg p-4 text-gray-300 text-sm whitespace-pre-wrap">
                  {selectedDecision.reasoning || 'No reasoning provided'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
