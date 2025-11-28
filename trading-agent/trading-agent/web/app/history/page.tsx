'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { supabase, TradingDecision } from '@/lib/supabase'
import { formatCurrency, formatDate, formatTimeAgo, cn, getStatusColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, Minus, Filter, Download, Eye, ChevronLeft, ChevronRight, History, Sparkles } from 'lucide-react'
import DecisionDetailsModal from '@/components/DecisionDetailsModal'
import ClosedPositionsHistory from '@/components/ClosedPositionsHistory'
import TradingStats from '@/components/TradingStats'

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring" as const,
      stiffness: 100,
      damping: 15
    }
  }
}

const tableRowVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: {
      delay: i * 0.05,
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

const statCardVariants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    transition: {
      delay: i * 0.1,
      type: "spring" as const,
      stiffness: 100,
      damping: 15
    }
  }),
  hover: {
    scale: 1.02,
    transition: { type: "spring" as const, stiffness: 400, damping: 10 }
  }
}

const pulseAnimation = {
  scale: [1, 1.02, 1],
  transition: {
    duration: 2,
    repeat: Infinity,
    ease: "easeInOut" as const
  }
}

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
    <motion.div
      className="space-y-6"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {/* Header */}
      <motion.div
        className="flex items-center justify-between"
        variants={itemVariants}
      >
        <div className="flex items-center gap-3">
          <motion.div
            className="p-2 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-xl"
            whileHover={{ rotate: 360 }}
            transition={{ duration: 0.5 }}
          >
            <History className="w-6 h-6 text-blue-400" />
          </motion.div>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              Trade History
              <motion.span
                animate={pulseAnimation}
              >
                <Sparkles className="w-5 h-5 text-yellow-400" />
              </motion.span>
            </h1>
            <p className="text-gray-400">All trading decisions and closed positions</p>
          </div>
        </div>
        <motion.button
          onClick={exportToCsv}
          className="btn btn-secondary flex items-center gap-2"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Download className="w-4 h-4" />
          Export CSV
        </motion.button>
      </motion.div>

      {/* Trading Stats */}
      <motion.div variants={itemVariants}>
        <TradingStats />
      </motion.div>

      {/* Tab Navigation */}
      <motion.div
        className="flex gap-2 border-b border-gray-700 relative"
        variants={itemVariants}
      >
        <button
          onClick={() => setActiveTab('decisions')}
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors relative',
            activeTab === 'decisions'
              ? 'text-blue-400'
              : 'text-gray-400 hover:text-white'
          )}
        >
          AI Decisions
          {activeTab === 'decisions' && (
            <motion.div
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-purple-500"
              layoutId="activeTab"
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            />
          )}
        </button>
        <button
          onClick={() => setActiveTab('positions')}
          className={cn(
            'px-4 py-2 text-sm font-medium transition-colors relative',
            activeTab === 'positions'
              ? 'text-blue-400'
              : 'text-gray-400 hover:text-white'
          )}
        >
          Closed Positions
          {activeTab === 'positions' && (
            <motion.div
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-purple-500"
              layoutId="activeTab"
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            />
          )}
        </button>
      </motion.div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {/* Closed Positions Tab */}
        {activeTab === 'positions' && (
          <motion.div
            key="positions"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ type: "spring", stiffness: 100, damping: 15 }}
          >
            <ClosedPositionsHistory pageSize={15} />
          </motion.div>
        )}

        {/* Decisions Tab */}
        {activeTab === 'decisions' && (
          <motion.div
            key="decisions"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 100, damping: 15 }}
          >
            {/* Stats */}
            <motion.div
              className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {[
                { label: 'Total Decisions', value: totalCount, color: 'text-white' },
                { label: 'Open Actions', value: decisions.filter(d => d.action === 'open').length, color: 'text-green-500' },
                { label: 'Close Actions', value: decisions.filter(d => d.action === 'close').length, color: 'text-red-500' },
                { label: 'Hold Actions', value: decisions.filter(d => d.action === 'hold').length, color: 'text-gray-400' }
              ].map((stat, i) => (
                <motion.div
                  key={stat.label}
                  className="stat-card group cursor-default"
                  custom={i}
                  variants={statCardVariants}
                  whileHover="hover"
                >
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                  />
                  <div className="stat-label relative">{stat.label}</div>
                  <motion.div
                    className={cn("stat-value relative", stat.color)}
                    key={stat.value}
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ type: "spring", stiffness: 200, damping: 15 }}
                  >
                    {stat.value}
                  </motion.div>
                </motion.div>
              ))}
            </motion.div>

            {/* Filters */}
            <motion.div
              className="flex flex-wrap items-center gap-4 mb-6"
              variants={itemVariants}
            >
              <div className="flex items-center gap-2">
                <motion.div
                  whileHover={{ rotate: 180 }}
                  transition={{ duration: 0.3 }}
                >
                  <Filter className="w-4 h-4 text-gray-400" />
                </motion.div>
                <span className="text-sm text-gray-400">Filters:</span>
              </div>
              <motion.select
                value={actionFilter}
                onChange={(e) => { setActionFilter(e.target.value); setPage(1) }}
                className="select w-32"
                whileFocus={{ scale: 1.02 }}
              >
                <option value="all">All Actions</option>
                <option value="open">Open</option>
                <option value="close">Close</option>
                <option value="hold">Hold</option>
              </motion.select>
              <motion.select
                value={symbolFilter}
                onChange={(e) => { setSymbolFilter(e.target.value); setPage(1) }}
                className="select w-32"
                whileFocus={{ scale: 1.02 }}
              >
                <option value="all">All Symbols</option>
                <option value="BTC">BTC</option>
                <option value="ETH">ETH</option>
                <option value="SOL">SOL</option>
              </motion.select>
              <motion.select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
                className="select w-36"
                whileFocus={{ scale: 1.02 }}
              >
                <option value="all">All Status</option>
                <option value="executed">Executed</option>
                <option value="skipped">Skipped</option>
                <option value="failed">Failed</option>
                <option value="pending">Pending</option>
              </motion.select>
            </motion.div>

            {/* Table */}
            <motion.div
              className="card overflow-hidden"
              variants={itemVariants}
            >
              {loading ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <motion.div
                    className="relative"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  >
                    <div className="w-12 h-12 border-4 border-gray-700 border-t-green-500 rounded-full" />
                  </motion.div>
                  <motion.p
                    className="text-gray-400 text-sm"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    Loading decisions...
                  </motion.p>
                </div>
              ) : decisions.length === 0 ? (
                <motion.div
                  className="text-center py-12 text-gray-500"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                >
                  <motion.div
                    animate={{ y: [0, -10, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  </motion.div>
                  No decisions found
                </motion.div>
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
                        <AnimatePresence mode="popLayout">
                          {decisions.map((decision, index) => (
                            <motion.tr
                              key={decision.id}
                              custom={index}
                              variants={tableRowVariants}
                              initial="hidden"
                              animate="visible"
                              exit="exit"
                              whileHover={{
                                backgroundColor: "rgba(59, 130, 246, 0.05)",
                                transition: { duration: 0.2 }
                              }}
                              layout
                            >
                              <td>
                                <div className="text-white">{formatTimeAgo(decision.timestamp)}</div>
                                <div className="text-xs text-gray-500">{formatDate(decision.timestamp)}</div>
                              </td>
                              <td>
                                <motion.span
                                  className="font-medium text-white px-2 py-1 bg-gray-800 rounded-md"
                                  whileHover={{ scale: 1.1 }}
                                >
                                  {decision.symbol}
                                </motion.span>
                              </td>
                              <td>
                                <motion.div
                                  className="flex items-center gap-2"
                                  whileHover={{ x: 5 }}
                                >
                                  <motion.span
                                    animate={decision.action !== 'hold' ? { scale: [1, 1.2, 1] } : {}}
                                    transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 2 }}
                                  >
                                    {getActionIcon(decision.action, decision.direction || undefined)}
                                  </motion.span>
                                  <span className={cn(
                                    'text-sm font-medium',
                                    decision.action === 'hold' ? 'text-gray-500' :
                                    decision.direction === 'long' ? 'text-green-500' : 'text-red-500'
                                  )}>
                                    {getActionLabel(decision)}
                                  </span>
                                </motion.div>
                              </td>
                              <td>
                                {decision.leverage ? (
                                  <motion.span
                                    className="bg-gray-700/50 px-2 py-0.5 rounded text-sm"
                                    whileHover={{ scale: 1.1, backgroundColor: "rgba(59, 130, 246, 0.2)" }}
                                  >
                                    {decision.leverage}x
                                  </motion.span>
                                ) : '-'}
                              </td>
                              <td className="text-gray-300">
                                {decision.position_size_pct ? `${decision.position_size_pct}%` : '-'}
                              </td>
                              <td>
                                <div className="flex items-center gap-2">
                                  <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                    <motion.div
                                      className={cn(
                                        'h-full rounded-full',
                                        (decision.confidence || 0) >= 0.7 ? 'bg-gradient-to-r from-green-500 to-emerald-400' :
                                        (decision.confidence || 0) >= 0.5 ? 'bg-gradient-to-r from-yellow-500 to-orange-400' : 'bg-gradient-to-r from-red-500 to-rose-400'
                                      )}
                                      initial={{ width: 0 }}
                                      animate={{ width: `${(decision.confidence || 0) * 100}%` }}
                                      transition={{ duration: 0.8, ease: "easeOut", delay: index * 0.05 }}
                                    />
                                  </div>
                                  <motion.span
                                    className="text-sm text-gray-400"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: index * 0.05 + 0.3 }}
                                  >
                                    {((decision.confidence || 0) * 100).toFixed(0)}%
                                  </motion.span>
                                </div>
                              </td>
                              <td>
                                <motion.span
                                  className={cn('badge', getStatusColor(decision.execution_status))}
                                  whileHover={{ scale: 1.1 }}
                                >
                                  {decision.execution_status}
                                </motion.span>
                              </td>
                              <td className="text-gray-300">
                                {decision.entry_price ? formatCurrency(parseFloat(String(decision.entry_price))) : '-'}
                              </td>
                              <td>
                                <motion.button
                                  onClick={() => setSelectedDecisionId(decision.id)}
                                  className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
                                  title="View details"
                                  whileHover={{ scale: 1.2, rotate: 15 }}
                                  whileTap={{ scale: 0.9 }}
                                >
                                  <Eye className="w-4 h-4" />
                                </motion.button>
                              </td>
                            </motion.tr>
                          ))}
                        </AnimatePresence>
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  <motion.div
                    className="flex items-center justify-between mt-4 pt-4 border-t border-gray-800"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                  >
                    <div className="text-sm text-gray-400">
                      Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of {totalCount}
                    </div>
                    <div className="flex items-center gap-2">
                      <motion.button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        whileHover={{ scale: 1.1, x: -3 }}
                        whileTap={{ scale: 0.9 }}
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </motion.button>
                      <span className="text-sm text-gray-400">
                        Page <motion.span key={page} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>{page}</motion.span> of {totalPages}
                      </span>
                      <motion.button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        whileHover={{ scale: 1.1, x: 3 }}
                        whileTap={{ scale: 0.9 }}
                      >
                        <ChevronRight className="w-4 h-4" />
                      </motion.button>
                    </div>
                  </motion.div>
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Decision Details Modal */}
      <DecisionDetailsModal
        decisionId={selectedDecisionId || ''}
        isOpen={!!selectedDecisionId}
        onClose={() => setSelectedDecisionId(null)}
      />
    </motion.div>
  )
}
