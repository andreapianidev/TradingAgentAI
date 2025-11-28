'use client'

import { useState } from 'react'
import { useTransitionData } from '@/hooks/useTransitionData'
import { formatCurrency, formatPercent, formatDate, getPnlColor } from '@/lib/utils'
import {
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  Zap,
  Shield,
  XCircle
} from 'lucide-react'

export default function TransitionsPage() {
  const { transition, positions, loading, refresh } = useTransitionData()
  const [cancelling, setCancelling] = useState(false)
  const [approving, setApproving] = useState(false)

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this transition?')) return

    setCancelling(true)
    try {
      const res = await fetch('/api/transitions/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transition_id: transition?.id,
          reason: 'User cancelled via dashboard'
        })
      })

      if (res.ok) {
        refresh()
      } else {
        alert('Failed to cancel transition')
      }
    } catch (err) {
      console.error('Cancel failed:', err)
      alert('Error cancelling transition')
    } finally {
      setCancelling(false)
    }
  }

  const handleApprove = async () => {
    setApproving(true)
    try {
      const res = await fetch('/api/transitions/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transition_id: transition?.id })
      })

      if (res.ok) {
        refresh()
        alert('Transition approved! Bot will close positions on next cycle.')
      } else {
        alert('Failed to approve transition')
      }
    } catch (err) {
      console.error('Approval failed:', err)
      alert('Error approving transition')
    } finally {
      setApproving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!transition) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Exchange Transition</h1>
        <div className="card p-8 text-center">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Active Transition</h3>
          <p className="text-gray-500 dark:text-gray-400">
            Change the exchange setting to initiate a transition.
          </p>
        </div>
      </div>
    )
  }

  const progress = transition.total_positions > 0
    ? (transition.positions_closed / transition.total_positions) * 100
    : 0

  const strategyInfo = {
    IMMEDIATE: {
      icon: Zap,
      color: 'text-red-500',
      bg: 'bg-red-500/10',
      desc: 'Closing all positions immediately'
    },
    PROFITABLE: {
      icon: TrendingUp,
      color: 'text-yellow-500',
      bg: 'bg-yellow-500/10',
      desc: 'Closing profitable, tightening SL on losers'
    },
    WAIT_PROFIT: {
      icon: Clock,
      color: 'text-blue-500',
      bg: 'bg-blue-500/10',
      desc: 'Waiting for all positions to reach profit'
    },
    MANUAL: {
      icon: Shield,
      color: 'text-purple-500',
      bg: 'bg-purple-500/10',
      desc: 'Awaiting manual approval'
    }
  }

  const strategy = strategyInfo[transition.transition_strategy as keyof typeof strategyInfo]
  const StrategyIcon = strategy.icon

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Exchange Transition</h1>
        <button
          onClick={refresh}
          disabled={loading}
          className="btn btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Status Card */}
      <div className="card">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-lg ${strategy.bg}`}>
              <StrategyIcon className={`w-6 h-6 ${strategy.color}`} />
            </div>
            <div>
              <h2 className="text-xl font-bold">
                {transition.from_exchange.toUpperCase()} → {transition.to_exchange.toUpperCase()}
              </h2>
              <p className="text-gray-500 dark:text-gray-400">{strategy.desc}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {transition.status === 'in_progress' && (
              <span className="px-3 py-1 bg-blue-500/10 text-blue-500 dark:text-blue-400 rounded-full text-sm font-medium">
                In Progress
              </span>
            )}
            {transition.status === 'pending' && (
              <span className="px-3 py-1 bg-yellow-500/10 text-yellow-500 dark:text-yellow-400 rounded-full text-sm font-medium">
                Pending
              </span>
            )}
            {transition.status === 'completed' && (
              <span className="px-3 py-1 bg-green-500/10 text-green-500 dark:text-green-400 rounded-full text-sm font-medium">
                Completed
              </span>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Progress</span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {transition.positions_closed} / {transition.total_positions} positions closed
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <div
              className="bg-green-500 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Remaining</div>
            <div className="text-2xl font-bold">{transition.positions_remaining}</div>
          </div>
          <div className="bg-green-50 dark:bg-green-500/5 rounded-lg p-4">
            <div className="text-sm text-green-600 dark:text-green-400 mb-1">In Profit</div>
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {transition.positions_in_profit}
            </div>
          </div>
          <div className="bg-red-50 dark:bg-red-500/5 rounded-lg p-4">
            <div className="text-sm text-red-600 dark:text-red-400 mb-1">In Loss</div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {transition.positions_in_loss}
            </div>
          </div>
          <div className="bg-blue-50 dark:bg-blue-500/5 rounded-lg p-4">
            <div className="text-sm text-blue-600 dark:text-blue-400 mb-1">Total P&L</div>
            <div className={`text-2xl font-bold ${getPnlColor(transition.total_pnl || 0)}`}>
              {formatCurrency(transition.total_pnl || 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Manual Approval Panel */}
      {transition.manual_override_required && !transition.manual_override_approved && (
        <div className="card bg-yellow-50 dark:bg-yellow-500/5 border-yellow-500/20">
          <div className="flex items-start gap-4">
            <AlertTriangle className="w-6 h-6 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-1" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-yellow-900 dark:text-yellow-500 mb-2">
                Manual Approval Required
              </h3>
              <p className="text-yellow-800 dark:text-yellow-400 mb-4">
                This transition requires your approval before positions can be closed.
                Review the positions below and approve when ready.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleApprove}
                  disabled={approving}
                  className="btn bg-yellow-600 hover:bg-yellow-700 text-white flex items-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  {approving ? 'Approving...' : 'Approve Transition'}
                </button>
                <button
                  onClick={handleCancel}
                  disabled={cancelling}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  <XCircle className="w-4 h-4" />
                  {cancelling ? 'Cancelling...' : 'Cancel Transition'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Positions Table */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Positions Being Transitioned</h3>
        {positions.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-center py-8">
            No open positions
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4">Symbol</th>
                  <th className="text-left py-3 px-4">Direction</th>
                  <th className="text-right py-3 px-4">Entry Price</th>
                  <th className="text-right py-3 px-4">Quantity</th>
                  <th className="text-right py-3 px-4">P&L</th>
                  <th className="text-right py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => {
                  const pnl = pos.unrealized_pnl || 0
                  const pnlPct = pos.unrealized_pnl_pct || 0
                  const isProfitable = pnl > 0

                  return (
                    <tr key={pos.id} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-3 px-4 font-medium">{pos.symbol}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          pos.direction === 'long'
                            ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                            : 'bg-red-500/10 text-red-600 dark:text-red-400'
                        }`}>
                          {pos.direction?.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">{formatCurrency(pos.entry_price || 0)}</td>
                      <td className="py-3 px-4 text-right">{pos.quantity?.toFixed(6)}</td>
                      <td className="py-3 px-4 text-right">
                        <div className={getPnlColor(pnl)}>
                          {formatCurrency(pnl)}
                          <span className="text-sm ml-1">({formatPercent(pnlPct)})</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {pos.status === 'open' ? (
                          <span className="px-2 py-1 bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded text-xs font-medium">
                            Open
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-gray-500/10 text-gray-600 dark:text-gray-400 rounded text-xs font-medium">
                            Closed
                          </span>
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

      {/* Timeline/Log */}
      {transition.transition_log && transition.transition_log.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Transition Log</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {transition.transition_log.map((log, idx) => (
              <div key={idx} className="flex items-start gap-3 text-sm">
                <span className="text-gray-400 dark:text-gray-500 font-mono text-xs">
                  {formatDate(log.timestamp)}
                </span>
                <span className={`font-medium ${
                  log.level === 'ERROR' ? 'text-red-500' :
                  log.level === 'WARNING' ? 'text-yellow-500' :
                  'text-gray-500 dark:text-gray-400'
                }`}>
                  [{log.level}]
                </span>
                <span className="text-gray-700 dark:text-gray-300 flex-1">
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
