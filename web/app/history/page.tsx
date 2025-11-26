'use client'

import { useEffect, useState } from 'react'
import { supabase, TradingDecision } from '@/lib/supabase'
import { formatCurrency, formatDate, formatTimeAgo, cn, getStatusColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, Minus, Filter, Download, Eye, ChevronLeft, ChevronRight } from 'lucide-react'
import DecisionDetailsModal from '@/components/DecisionDetailsModal'
import ClosedPositionsHistory from '@/components/ClosedPositionsHistory'
import TradingStats from '@/components/TradingStats'

export default function HistoryPage() {
  const [decisions, setDecisions] = useState<TradingDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [selectedDecisionId, setSelectedDecisionId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'decisions' | 'positions'>('decisions')

  // Filters
  const [actionFilter, setActionFilter] = useState<string>('all')
  const [symbolFilter, setSymbolFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const pageSize = 20

  useEffect(() => {
    fetchHistory()
  }, [page, actionFilter, symbolFilter, statusFilter])

  const fetchHistory = async () => {
    setLoading(true)
    try {
      let query = supabase
        .from('trading_decisions')
        .select('*', { count: 'exact' })
        .order('timestamp', { ascending: false })

      if (actionFilter !== 'all') {
        query = query.eq('action', actionFilter)
      }
      if (symbolFilter !== 'all') {
        query = query.eq('symbol', symbolFilter)
      }
      if (statusFilter !== 'all') {
        query = query.eq('execution_status', statusFilter)
      }

      const { data, count } = await query
        .range((page - 1) * pageSize, page * pageSize - 1)

      setDecisions(data || [])
      setTotalCount(count || 0)
    } catch (error) {
      console.error('Error fetching history:', error)
    } finally {
      setLoading(false)
    }
  }

  const getActionIcon = (action: string, direction?: string) => {
    if (action === 'hold') return <Minus className="w-4 h-4 text-gray-500" />
    if (action === 'open') {
      return direction === 'long'
        ? <ArrowUpRight className="w-4 h-4 text-green-500" />
        : <ArrowDownRight className="w-4 h-4 text-red-500" />
    }
    if (action === 'close') {
      return direction === 'long'
        ? <ArrowDownRight className="w-4 h-4 text-red-500" />
        : <ArrowUpRight className="w-4 h-4 text-green-500" />
    }
    return null
  }

  const getActionLabel = (decision: TradingDecision) => {
    if (decision.action === 'hold') return 'HOLD'
    return `${decision.action.toUpperCase()} ${decision.direction?.toUpperCase() || ''}`
  }

  const exportToCsv = () => {
    const headers = ['Timestamp', 'Symbol', 'Action', 'Direction', 'Leverage', 'Size %', 'Confidence', 'Status', 'Entry Price', 'Reasoning']
    const rows = decisions.map(d => [
      formatDate(d.timestamp),
      d.symbol,
      d.action,
      d.direction || '',
      d.leverage || '',
      d.position_size_pct || '',
      ((d.confidence || 0) * 100).toFixed(1) + '%',
      d.execution_status,
      d.entry_price || '',
      `"${(d.reasoning || '').replace(/"/g, '""')}"`
    ])

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `trade_history_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  const totalPages = Math.ceil(totalCount / pageSize)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Trade History</h1>
          <p className="text-gray-400">All trading decisions and closed positions</p>
        </div>
        <button
          onClick={exportToCsv}
          className="btn btn-secondary flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Trading Stats */}
      <TradingStats />

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('decisions')}
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'decisions'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-white'
          )}
        >
          AI Decisions
        </button>
        <button
          onClick={() => setActiveTab('positions')}
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'positions'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-white'
          )}
        >
          Closed Positions
        </button>
      </div>

      {/* Closed Positions Tab */}
      {activeTab === 'positions' && (
        <ClosedPositionsHistory pageSize={15} />
      )}

      {/* Decisions Tab */}
      {activeTab === 'decisions' && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="stat-card">
              <div className="stat-label">Total Decisions</div>
              <div className="stat-value">{totalCount}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Open Actions</div>
              <div className="stat-value text-green-500">
                {decisions.filter(d => d.action === 'open').length}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Close Actions</div>
              <div className="stat-value text-red-500">
                {decisions.filter(d => d.action === 'close').length}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Hold Actions</div>
              <div className="stat-value text-gray-400">
                {decisions.filter(d => d.action === 'hold').length}
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">Filters:</span>
            </div>
            <select
              value={actionFilter}
              onChange={(e) => { setActionFilter(e.target.value); setPage(1) }}
              className="select w-32"
            >
              <option value="all">All Actions</option>
              <option value="open">Open</option>
              <option value="close">Close</option>
              <option value="hold">Hold</option>
            </select>
            <select
              value={symbolFilter}
              onChange={(e) => { setSymbolFilter(e.target.value); setPage(1) }}
              className="select w-32"
            >
              <option value="all">All Symbols</option>
              <option value="BTC">BTC</option>
              <option value="ETH">ETH</option>
              <option value="SOL">SOL</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
              className="select w-36"
            >
              <option value="all">All Status</option>
              <option value="executed">Executed</option>
              <option value="skipped">Skipped</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
            </select>
          </div>

          {/* Table */}
          <div className="card">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
              </div>
            ) : decisions.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No decisions found
              </div>
            ) : (
              <>
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Symbol</th>
                        <th>Action</th>
                        <th>Leverage</th>
                        <th>Size</th>
                        <th>Confidence</th>
                        <th>Status</th>
                        <th>Entry Price</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {decisions.map((decision) => (
                        <tr key={decision.id}>
                          <td>
                            <div className="text-white">{formatTimeAgo(decision.timestamp)}</div>
                            <div className="text-xs text-gray-500">{formatDate(decision.timestamp)}</div>
                          </td>
                          <td className="font-medium text-white">{decision.symbol}</td>
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
                            </div>
                          </td>
                          <td>
                            {decision.leverage ? (
                              <span className="bg-gray-700/50 px-2 py-0.5 rounded text-sm">
                                {decision.leverage}x
                              </span>
                            ) : '-'}
                          </td>
                          <td className="text-gray-300">
                            {decision.position_size_pct ? `${decision.position_size_pct}%` : '-'}
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
                            <span className={cn('badge', getStatusColor(decision.execution_status))}>
                              {decision.execution_status}
                            </span>
                          </td>
                          <td className="text-gray-300">
                            {decision.entry_price ? formatCurrency(parseFloat(String(decision.entry_price))) : '-'}
                          </td>
                          <td>
                            <button
                              onClick={() => setSelectedDecisionId(decision.id)}
                              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
                              title="View details"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-800">
                  <div className="text-sm text-gray-400">
                    Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of {totalCount}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-gray-400">
                      Page {page} of {totalPages}
                    </span>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </>
      )}

      {/* Decision Details Modal */}
      <DecisionDetailsModal
        decisionId={selectedDecisionId || ''}
        isOpen={!!selectedDecisionId}
        onClose={() => setSelectedDecisionId(null)}
      />
    </div>
  )
}
