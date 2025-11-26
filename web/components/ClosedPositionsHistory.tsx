'use client'

import { useEffect, useState } from 'react'
import {
  History,
  TrendingUp,
  TrendingDown,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  Filter,
  X
} from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { TradingPosition } from '@/lib/supabase'

type SortField = 'exit_timestamp' | 'realized_pnl' | 'realized_pnl_pct' | 'symbol'
type SortDirection = 'asc' | 'desc'

interface ClosedPositionsHistoryProps {
  pageSize?: number
  onPositionClick?: (position: TradingPosition) => void
}

export default function ClosedPositionsHistory({
  pageSize = 10,
  onPositionClick
}: ClosedPositionsHistoryProps) {
  const [positions, setPositions] = useState<TradingPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [sortField, setSortField] = useState<SortField>('exit_timestamp')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [filterSymbol, setFilterSymbol] = useState<string>('')
  const [filterDirection, setFilterDirection] = useState<'all' | 'long' | 'short'>('all')
  const [filterResult, setFilterResult] = useState<'all' | 'profit' | 'loss'>('all')
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    fetchPositions()
  }, [currentPage, sortField, sortDirection, filterSymbol, filterDirection, filterResult])

  const fetchPositions = async () => {
    setLoading(true)
    try {
      let query = supabase
        .from('trading_positions')
        .select('*', { count: 'exact' })
        .eq('status', 'closed')
        .not('realized_pnl', 'is', null)

      // Apply filters
      if (filterSymbol) {
        query = query.ilike('symbol', `%${filterSymbol}%`)
      }
      if (filterDirection !== 'all') {
        query = query.eq('direction', filterDirection)
      }
      if (filterResult === 'profit') {
        query = query.gt('realized_pnl', 0)
      } else if (filterResult === 'loss') {
        query = query.lt('realized_pnl', 0)
      }

      // Apply sorting
      query = query.order(sortField, { ascending: sortDirection === 'asc' })

      // Apply pagination
      const from = (currentPage - 1) * pageSize
      const to = from + pageSize - 1
      query = query.range(from, to)

      const { data, count, error } = await query

      if (error) throw error

      setPositions(data || [])
      setTotalCount(count || 0)
    } catch (error) {
      console.error('Error fetching closed positions:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setFilterSymbol('')
    setFilterDirection('all')
    setFilterResult('all')
    setCurrentPage(1)
  }

  const totalPages = Math.ceil(totalCount / pageSize)

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (entry: string, exit: string) => {
    const ms = new Date(exit).getTime() - new Date(entry).getTime()
    const hours = ms / (1000 * 60 * 60)
    if (hours < 1) {
      return `${Math.round(ms / (1000 * 60))}m`
    } else if (hours < 24) {
      return `${hours.toFixed(1)}h`
    } else {
      return `${(hours / 24).toFixed(1)}d`
    }
  }

  const getExitReasonBadge = (reason?: string) => {
    if (!reason) return null

    const colors: Record<string, string> = {
      'take_profit': 'bg-green-500/20 text-green-400',
      'stop_loss': 'bg-red-500/20 text-red-400',
      'signal_reversal': 'bg-blue-500/20 text-blue-400',
      'manual': 'bg-gray-500/20 text-gray-400',
      'trailing_stop': 'bg-yellow-500/20 text-yellow-400'
    }

    const labels: Record<string, string> = {
      'take_profit': 'TP',
      'stop_loss': 'SL',
      'signal_reversal': 'Signal',
      'manual': 'Manual',
      'trailing_stop': 'Trail'
    }

    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[reason] || 'bg-gray-500/20 text-gray-400'}`}>
        {labels[reason] || reason}
      </span>
    )
  }

  if (loading && positions.length === 0) {
    return (
      <div className="animate-pulse bg-gray-800/50 rounded-xl p-6">
        <div className="h-6 bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-900/50 rounded-xl p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <History className="w-5 h-5" />
          Closed Positions
          <span className="text-sm text-gray-400 font-normal">({totalCount})</span>
        </h3>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            showFilters ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          <Filter className="w-4 h-4" />
          Filters
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-gray-800/50 rounded-lg p-4 mb-4 flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Symbol</label>
            <input
              type="text"
              value={filterSymbol}
              onChange={(e) => { setFilterSymbol(e.target.value); setCurrentPage(1); }}
              placeholder="BTC, ETH..."
              className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded-lg w-28 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Direction</label>
            <select
              value={filterDirection}
              onChange={(e) => { setFilterDirection(e.target.value as 'all' | 'long' | 'short'); setCurrentPage(1); }}
              className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="long">Long</option>
              <option value="short">Short</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Result</label>
            <select
              value={filterResult}
              onChange={(e) => { setFilterResult(e.target.value as 'all' | 'profit' | 'loss'); setCurrentPage(1); }}
              className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="profit">Profit</option>
              <option value="loss">Loss</option>
            </select>
          </div>
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 text-gray-400 hover:text-white text-sm px-3 py-1.5"
          >
            <X className="w-4 h-4" />
            Clear
          </button>
        </div>
      )}

      {/* Table */}
      {positions.length === 0 ? (
        <div className="text-center text-gray-500 py-12">
          <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No closed positions yet</p>
          <p className="text-sm mt-1">Positions will appear here after they are closed</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                  <th className="pb-3 pr-4">
                    <button
                      onClick={() => handleSort('symbol')}
                      className="flex items-center gap-1 hover:text-white"
                    >
                      Symbol
                      <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                  <th className="pb-3 pr-4">Direction</th>
                  <th className="pb-3 pr-4">Entry</th>
                  <th className="pb-3 pr-4">Exit</th>
                  <th className="pb-3 pr-4">
                    <button
                      onClick={() => handleSort('exit_timestamp')}
                      className="flex items-center gap-1 hover:text-white"
                    >
                      Closed
                      <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                  <th className="pb-3 pr-4">Duration</th>
                  <th className="pb-3 pr-4">
                    <button
                      onClick={() => handleSort('realized_pnl')}
                      className="flex items-center gap-1 hover:text-white"
                    >
                      P&L
                      <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                  <th className="pb-3 pr-4">
                    <button
                      onClick={() => handleSort('realized_pnl_pct')}
                      className="flex items-center gap-1 hover:text-white"
                    >
                      P&L %
                      <ArrowUpDown className="w-3 h-3" />
                    </button>
                  </th>
                  <th className="pb-3">Exit Reason</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => {
                  const isProfit = (position.realized_pnl || 0) >= 0
                  return (
                    <tr
                      key={position.id}
                      className={`border-b border-gray-800 hover:bg-gray-800/50 transition-colors ${
                        onPositionClick ? 'cursor-pointer' : ''
                      }`}
                      onClick={() => onPositionClick?.(position)}
                    >
                      <td className="py-3 pr-4">
                        <span className="font-medium text-white">{position.symbol}</span>
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          position.direction === 'long'
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-red-500/20 text-red-400'
                        }`}>
                          {position.direction.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-gray-300">
                        {formatCurrency(position.entry_price)}
                      </td>
                      <td className="py-3 pr-4 text-gray-300">
                        {position.exit_price ? formatCurrency(position.exit_price) : '-'}
                      </td>
                      <td className="py-3 pr-4 text-gray-400 text-sm">
                        {position.exit_timestamp ? formatDate(position.exit_timestamp) : '-'}
                      </td>
                      <td className="py-3 pr-4 text-gray-400 text-sm">
                        {position.entry_timestamp && position.exit_timestamp
                          ? formatDuration(position.entry_timestamp, position.exit_timestamp)
                          : '-'}
                      </td>
                      <td className="py-3 pr-4">
                        <div className={`flex items-center gap-1 ${
                          isProfit ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {isProfit ? (
                            <TrendingUp className="w-4 h-4" />
                          ) : (
                            <TrendingDown className="w-4 h-4" />
                          )}
                          <span className="font-medium">
                            {isProfit ? '+' : ''}{formatCurrency(position.realized_pnl || 0)}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`font-medium ${
                          isProfit ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {isProfit ? '+' : ''}{(position.realized_pnl_pct || 0).toFixed(2)}%
                        </span>
                      </td>
                      <td className="py-3">
                        {getExitReasonBadge(position.exit_reason)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center mt-4 pt-4 border-t border-gray-800">
              <span className="text-sm text-gray-400">
                Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, totalCount)} of {totalCount}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="flex gap-1">
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
                    let pageNum
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = currentPage - 2 + i
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`w-8 h-8 rounded-lg text-sm ${
                          currentPage === pageNum
                            ? 'bg-blue-500 text-white'
                            : 'text-gray-400 hover:text-white hover:bg-gray-800'
                        }`}
                      >
                        {pageNum}
                      </button>
                    )
                  })}
                </div>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
