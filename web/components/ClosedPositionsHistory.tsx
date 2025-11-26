'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  History,
  TrendingUp,
  TrendingDown,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  Filter,
  X,
  Sparkles
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

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1
    }
  }
}

const rowVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: {
      delay: i * 0.03,
      type: "spring" as const,
      stiffness: 100,
      damping: 15
    }
  }),
  exit: {
    opacity: 0,
    x: 20,
    transition: { duration: 0.2 }
  }
}

const filterVariants = {
  hidden: { opacity: 0, height: 0, marginBottom: 0 },
  visible: {
    opacity: 1,
    height: "auto",
    marginBottom: 16,
    transition: {
      type: "spring" as const,
      stiffness: 100,
      damping: 15
    }
  },
  exit: {
    opacity: 0,
    height: 0,
    marginBottom: 0,
    transition: { duration: 0.2 }
  }
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
      'take_profit': 'bg-green-500/20 text-green-400 border border-green-500/30',
      'stop_loss': 'bg-red-500/20 text-red-400 border border-red-500/30',
      'signal_reversal': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
      'manual': 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
      'trailing_stop': 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
    }

    const labels: Record<string, string> = {
      'take_profit': 'TP',
      'stop_loss': 'SL',
      'signal_reversal': 'Signal',
      'manual': 'Manual',
      'trailing_stop': 'Trail'
    }

    return (
      <motion.span
        className={`px-2 py-0.5 rounded text-xs font-medium ${colors[reason] || 'bg-gray-500/20 text-gray-400'}`}
        whileHover={{ scale: 1.1 }}
      >
        {labels[reason] || reason}
      </motion.span>
    )
  }

  if (loading && positions.length === 0) {
    return (
      <motion.div
        className="bg-gray-900/50 rounded-xl p-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="h-6 bg-gray-700 rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <motion.div
              key={i}
              className="h-12 bg-gray-700 rounded"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: [0.5, 1, 0.5], x: 0 }}
              transition={{
                opacity: { duration: 1.5, repeat: Infinity, delay: i * 0.1 },
                x: { duration: 0.3, delay: i * 0.05 }
              }}
            />
          ))}
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      className="bg-gray-900/50 rounded-xl p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 15 }}
    >
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <motion.h3
          className="text-lg font-semibold text-white flex items-center gap-2"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <motion.div
            className="p-1.5 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-lg"
            whileHover={{ rotate: 360 }}
            transition={{ duration: 0.5 }}
          >
            <History className="w-5 h-5 text-purple-400" />
          </motion.div>
          Closed Positions
          <motion.span
            className="text-sm text-gray-400 font-normal bg-gray-800 px-2 py-0.5 rounded-full"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
          >
            {totalCount}
          </motion.span>
          <motion.span
            animate={{ rotate: [0, 15, -15, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Sparkles className="w-4 h-4 text-yellow-400" />
          </motion.span>
        </motion.h3>
        <motion.button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            showFilters ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <motion.div
            animate={{ rotate: showFilters ? 180 : 0 }}
            transition={{ duration: 0.3 }}
          >
            <Filter className="w-4 h-4" />
          </motion.div>
          Filters
        </motion.button>
      </div>

      {/* Filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            className="bg-gray-800/50 rounded-lg p-4 flex flex-wrap gap-4 items-end overflow-hidden"
            variants={filterVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <label className="block text-xs text-gray-400 mb-1">Symbol</label>
              <input
                type="text"
                value={filterSymbol}
                onChange={(e) => { setFilterSymbol(e.target.value); setCurrentPage(1); }}
                placeholder="BTC, ETH..."
                className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded-lg w-28 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
            >
              <label className="block text-xs text-gray-400 mb-1">Direction</label>
              <select
                value={filterDirection}
                onChange={(e) => { setFilterDirection(e.target.value as 'all' | 'long' | 'short'); setCurrentPage(1); }}
                className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              >
                <option value="all">All</option>
                <option value="long">Long</option>
                <option value="short">Short</option>
              </select>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <label className="block text-xs text-gray-400 mb-1">Result</label>
              <select
                value={filterResult}
                onChange={(e) => { setFilterResult(e.target.value as 'all' | 'profit' | 'loss'); setCurrentPage(1); }}
                className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              >
                <option value="all">All</option>
                <option value="profit">Profit</option>
                <option value="loss">Loss</option>
              </select>
            </motion.div>
            <motion.button
              onClick={clearFilters}
              className="flex items-center gap-1 text-gray-400 hover:text-white text-sm px-3 py-1.5 hover:bg-gray-700 rounded-lg transition-colors"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <X className="w-4 h-4" />
              Clear
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      {positions.length === 0 ? (
        <motion.div
          className="text-center text-gray-500 py-12"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
          </motion.div>
          <p>No closed positions yet</p>
          <p className="text-sm mt-1">Positions will appear here after they are closed</p>
        </motion.div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                  <th className="pb-3 pr-4">
                    <motion.button
                      onClick={() => handleSort('symbol')}
                      className="flex items-center gap-1 hover:text-white transition-colors"
                      whileHover={{ x: 2 }}
                    >
                      Symbol
                      <ArrowUpDown className="w-3 h-3" />
                    </motion.button>
                  </th>
                  <th className="pb-3 pr-4">Direction</th>
                  <th className="pb-3 pr-4">Entry</th>
                  <th className="pb-3 pr-4">Exit</th>
                  <th className="pb-3 pr-4">
                    <motion.button
                      onClick={() => handleSort('exit_timestamp')}
                      className="flex items-center gap-1 hover:text-white transition-colors"
                      whileHover={{ x: 2 }}
                    >
                      Closed
                      <ArrowUpDown className="w-3 h-3" />
                    </motion.button>
                  </th>
                  <th className="pb-3 pr-4">Duration</th>
                  <th className="pb-3 pr-4">
                    <motion.button
                      onClick={() => handleSort('realized_pnl')}
                      className="flex items-center gap-1 hover:text-white transition-colors"
                      whileHover={{ x: 2 }}
                    >
                      P&L
                      <ArrowUpDown className="w-3 h-3" />
                    </motion.button>
                  </th>
                  <th className="pb-3 pr-4">
                    <motion.button
                      onClick={() => handleSort('realized_pnl_pct')}
                      className="flex items-center gap-1 hover:text-white transition-colors"
                      whileHover={{ x: 2 }}
                    >
                      P&L %
                      <ArrowUpDown className="w-3 h-3" />
                    </motion.button>
                  </th>
                  <th className="pb-3">Exit Reason</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence mode="popLayout">
                  {positions.map((position, index) => {
                    const isProfit = (position.realized_pnl || 0) >= 0
                    return (
                      <motion.tr
                        key={position.id}
                        custom={index}
                        variants={rowVariants}
                        initial="hidden"
                        animate="visible"
                        exit="exit"
                        className={`border-b border-gray-800 transition-colors ${
                          onPositionClick ? 'cursor-pointer' : ''
                        }`}
                        onClick={() => onPositionClick?.(position)}
                        whileHover={{
                          backgroundColor: "rgba(59, 130, 246, 0.05)",
                        }}
                        layout
                      >
                        <td className="py-3 pr-4">
                          <motion.span
                            className="font-medium text-white px-2 py-1 bg-gray-800 rounded-md inline-block"
                            whileHover={{ scale: 1.1 }}
                          >
                            {position.symbol}
                          </motion.span>
                        </td>
                        <td className="py-3 pr-4">
                          <motion.span
                            className={`px-2 py-0.5 rounded text-xs font-medium border ${
                              position.direction === 'long'
                                ? 'bg-green-500/20 text-green-400 border-green-500/30'
                                : 'bg-red-500/20 text-red-400 border-red-500/30'
                            }`}
                            whileHover={{ scale: 1.1 }}
                          >
                            {position.direction.toUpperCase()}
                          </motion.span>
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
                        <td className="py-3 pr-4">
                          <motion.span
                            className="text-gray-400 text-sm bg-gray-800/50 px-2 py-0.5 rounded"
                            whileHover={{ scale: 1.1 }}
                          >
                            {position.entry_timestamp && position.exit_timestamp
                              ? formatDuration(position.entry_timestamp, position.exit_timestamp)
                              : '-'}
                          </motion.span>
                        </td>
                        <td className="py-3 pr-4">
                          <motion.div
                            className={`flex items-center gap-1 ${
                              isProfit ? 'text-green-400' : 'text-red-400'
                            }`}
                            initial={{ scale: 0.8 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 200 }}
                          >
                            <motion.span
                              animate={isProfit ? { y: [0, -2, 0] } : { y: [0, 2, 0] }}
                              transition={{ duration: 1, repeat: Infinity, repeatDelay: 2 }}
                            >
                              {isProfit ? (
                                <TrendingUp className="w-4 h-4" />
                              ) : (
                                <TrendingDown className="w-4 h-4" />
                              )}
                            </motion.span>
                            <span className="font-medium">
                              {isProfit ? '+' : ''}{formatCurrency(position.realized_pnl || 0)}
                            </span>
                          </motion.div>
                        </td>
                        <td className="py-3 pr-4">
                          <motion.span
                            className={`font-medium ${
                              isProfit ? 'text-green-400' : 'text-red-400'
                            }`}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: index * 0.05 + 0.2 }}
                          >
                            {isProfit ? '+' : ''}{(position.realized_pnl_pct || 0).toFixed(2)}%
                          </motion.span>
                        </td>
                        <td className="py-3">
                          {getExitReasonBadge(position.exit_reason)}
                        </td>
                      </motion.tr>
                    )
                  })}
                </AnimatePresence>
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <motion.div
              className="flex justify-between items-center mt-4 pt-4 border-t border-gray-800"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <span className="text-sm text-gray-400">
                Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, totalCount)} of {totalCount}
              </span>
              <div className="flex items-center gap-2">
                <motion.button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  whileHover={{ scale: 1.1, x: -3 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <ChevronLeft className="w-5 h-5" />
                </motion.button>
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
                      <motion.button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`w-8 h-8 rounded-lg text-sm transition-colors ${
                          currentPage === pageNum
                            ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white'
                            : 'text-gray-400 hover:text-white hover:bg-gray-800'
                        }`}
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: i * 0.05 }}
                      >
                        {pageNum}
                      </motion.button>
                    )
                  })}
                </div>
                <motion.button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  whileHover={{ scale: 1.1, x: 3 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <ChevronRight className="w-5 h-5" />
                </motion.button>
              </div>
            </motion.div>
          )}
        </>
      )}
    </motion.div>
  )
}
