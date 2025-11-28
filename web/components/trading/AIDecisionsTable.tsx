import { motion, AnimatePresence } from 'framer-motion'
import { TradingDecision } from '@/lib/supabase'
import { formatCurrency, formatDate, formatTimeAgo, cn, getStatusColor } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight, Minus, Eye, ChevronLeft, ChevronRight, History } from 'lucide-react'

interface AIDecisionsTableProps {
  decisions: TradingDecision[]
  loading: boolean
  page: number
  totalCount: number
  pageSize: number
  totalPages: number
  onPageChange: (page: number) => void
  onDecisionClick: (decisionId: string) => void
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

function getActionIcon(action: string, direction?: string) {
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

function getActionLabel(decision: TradingDecision) {
  if (decision.action === 'hold') return 'HOLD'
  return `${decision.action.toUpperCase()} ${decision.direction?.toUpperCase() || ''}`
}

export default function AIDecisionsTable({
  decisions,
  loading,
  page,
  totalCount,
  pageSize,
  totalPages,
  onPageChange,
  onDecisionClick
}: AIDecisionsTableProps) {
  return (
    <motion.div
      className="card overflow-hidden"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
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
                          onClick={() => onDecisionClick(decision.id)}
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
                onClick={() => onPageChange(Math.max(1, page - 1))}
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
                onClick={() => onPageChange(Math.min(totalPages, page + 1))}
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
  )
}
