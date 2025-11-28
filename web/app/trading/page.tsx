'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Download, RefreshCw, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'
import { cn, formatCurrency } from '@/lib/utils'
import StrategyBadge from '@/components/StrategyBadge'
import TradingStats from '@/components/TradingStats'
import ClosedPositionsHistory from '@/components/ClosedPositionsHistory'
import DecisionDetailsModal from '@/components/DecisionDetailsModal'
import PortfolioOverview from '@/components/trading/PortfolioOverview'
import PositionStatsCards from '@/components/trading/PositionStatsCards'
import OpenPositionsTable from '@/components/trading/OpenPositionsTable'
import AIDecisionsTable from '@/components/trading/AIDecisionsTable'
import AllPositionsTable from '@/components/trading/AllPositionsTable'
import { useTradingPositions } from '@/lib/hooks/useTradingPositions'
import { useTradingDecisions } from '@/lib/hooks/useTradingDecisions'
import { usePortfolioStats } from '@/lib/hooks/usePortfolioStats'

type TabType = 'overview' | 'history' | 'decisions' | 'all'

const INITIAL_CAPITAL = 100000

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

export default function TradingPage() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [mounted, setMounted] = useState(false)
  const [selectedDecisionId, setSelectedDecisionId] = useState<string | null>(null)

  // Hooks
  const {
    positions,
    loading: positionsLoading,
    syncing,
    lastSync,
    syncError,
    syncPositions,
    refreshPositions,
    closePosition
  } = useTradingPositions({ autoSync: activeTab === 'overview' || activeTab === 'all' })

  const { portfolioStats } = usePortfolioStats()

  const [actionFilter, setActionFilter] = useState<string>('all')
  const [symbolFilter, setSymbolFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [decisionsPage, setDecisionsPage] = useState(1)

  const {
    decisions,
    loading: decisionsLoading,
    totalCount,
    pageSize,
    totalPages,
    setPage: setDecisionPage
  } = useTradingDecisions({
    actionFilter,
    symbolFilter,
    statusFilter,
    page: decisionsPage,
    pageSize: 20
  })

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    setDecisionPage(decisionsPage)
  }, [decisionsPage, setDecisionPage])

  // Calculate stats
  const openPositionsUnrealizedPnl = positions
    .filter(p => p.status === 'open')
    .reduce((sum, p) => sum + (parseFloat(String(p.unrealized_pnl || 0))), 0)

  const stats = {
    total: positions.length,
    open: positions.filter(p => p.status === 'open').length,
    closed: positions.filter(p => p.status === 'closed').length,
    totalPnl: portfolioStats?.totalPnl ?? 0,
    totalPnlPct: portfolioStats?.totalPnlPct ?? 0,
    unrealizedPnl: portfolioStats?.unrealizedPnl ?? openPositionsUnrealizedPnl,
    investedValue: portfolioStats?.investedValue ?? 0,
    exposurePct: portfolioStats?.exposurePct ?? 0,
  }

  const handleClosePosition = async (positionId: string) => {
    const success = await closePosition(positionId)
    if (success) {
      await refreshPositions()
    }
  }

  const exportDecisionsToCsv = () => {
    const headers = ['Timestamp', 'Symbol', 'Action', 'Direction', 'Leverage', 'Size %', 'Confidence', 'Status', 'Entry Price', 'Reasoning']
    const rows = decisions.map(d => [
      d.timestamp,
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
    a.download = `ai_decisions_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

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
        <div>
          <h1 className="text-2xl font-bold text-white title-gradient cursor-default">
            Trading
          </h1>
          <div className="flex items-center gap-3">
            <p className="text-gray-400 flex items-center gap-2">
              Portfolio, positions, and trading decisions
              {lastSync && (
                <span className="text-xs flex items-center gap-1">
                  {syncError ? (
                    <AlertCircle className="w-3 h-3 text-red-400 animate-pulse" />
                  ) : (
                    <CheckCircle className="w-3 h-3 text-green-400 sync-indicator" />
                  )}
                  <span className={cn(
                    "transition-colors duration-300",
                    syncError ? 'text-red-400' : 'text-green-400'
                  )}>
                    Synced {Math.round((Date.now() - lastSync.getTime()) / 1000)}s ago
                  </span>
                </span>
              )}
            </p>
            <div className="h-4 w-px bg-gray-700" />
            <StrategyBadge />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => syncPositions(true)}
            disabled={syncing}
            className="btn btn-secondary action-btn flex items-center gap-2"
          >
            <RefreshCw className={cn(
              "w-4 h-4 transition-transform duration-300",
              syncing && "animate-spin"
            )} />
            {syncing ? 'Syncing...' : 'Sync'}
          </button>
          {activeTab === 'decisions' && (
            <button
              onClick={exportDecisionsToCsv}
              className="btn btn-secondary action-btn flex items-center gap-2"
            >
              <Download className="w-4 h-4 group-hover:animate-bounce" />
              Export CSV
            </button>
          )}
        </div>
      </motion.div>

      {/* Tab Navigation */}
      <motion.div
        className="flex gap-2 border-b border-gray-700 relative"
        variants={itemVariants}
      >
        {[
          { id: 'overview' as TabType, label: 'Overview' },
          { id: 'history' as TabType, label: 'Position History' },
          { id: 'decisions' as TabType, label: 'AI Decisions' },
          { id: 'all' as TabType, label: 'All Positions' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-4 py-2 text-sm font-medium transition-colors relative',
              activeTab === tab.id
                ? 'text-green-400'
                : 'text-gray-400 hover:text-white'
            )}
          >
            {tab.label}
            {activeTab === tab.id && (
              <motion.div
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-green-500 to-emerald-500"
                layoutId="activeTab"
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              />
            )}
          </button>
        ))}
      </motion.div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 100, damping: 15 }}
            className="space-y-6"
          >
            {/* Portfolio Overview */}
            <PortfolioOverview
              portfolioStats={portfolioStats}
              stats={stats}
              mounted={mounted}
            />

            {/* Trading Stats */}
            <TradingStats />

            {/* Position Stats Cards */}
            <PositionStatsCards stats={stats} mounted={mounted} />

            {/* Open Positions Table */}
            <OpenPositionsTable
              positions={positions}
              loading={positionsLoading}
              mounted={mounted}
              onClosePosition={handleClosePosition}
              onRefresh={() => syncPositions(true)}
            />
          </motion.div>
        )}

        {/* Position History Tab */}
        {activeTab === 'history' && (
          <motion.div
            key="history"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 100, damping: 15 }}
          >
            <ClosedPositionsHistory pageSize={15} />
          </motion.div>
        )}

        {/* AI Decisions Tab */}
        {activeTab === 'decisions' && (
          <motion.div
            key="decisions"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 100, damping: 15 }}
            className="space-y-6"
          >
            {/* Decision Stats */}
            <motion.div
              className="grid grid-cols-1 md:grid-cols-4 gap-4"
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
                <div
                  key={stat.label}
                  className="stat-card group cursor-default"
                >
                  <div className="stat-label">{stat.label}</div>
                  <div className={cn("stat-value", stat.color)}>
                    {stat.value}
                  </div>
                </div>
              ))}
            </motion.div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-4">
              <select
                value={actionFilter}
                onChange={(e) => { setActionFilter(e.target.value); setDecisionsPage(1) }}
                className="select w-32"
              >
                <option value="all">All Actions</option>
                <option value="open">Open</option>
                <option value="close">Close</option>
                <option value="hold">Hold</option>
              </select>
              <select
                value={symbolFilter}
                onChange={(e) => { setSymbolFilter(e.target.value); setDecisionsPage(1) }}
                className="select w-32"
              >
                <option value="all">All Symbols</option>
                <option value="BTC">BTC</option>
                <option value="ETH">ETH</option>
                <option value="SOL">SOL</option>
              </select>
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setDecisionsPage(1) }}
                className="select w-36"
              >
                <option value="all">All Status</option>
                <option value="executed">Executed</option>
                <option value="skipped">Skipped</option>
                <option value="failed">Failed</option>
                <option value="pending">Pending</option>
              </select>
            </div>

            {/* AI Decisions Table */}
            <AIDecisionsTable
              decisions={decisions}
              loading={decisionsLoading}
              page={decisionsPage}
              totalCount={totalCount}
              pageSize={pageSize}
              totalPages={totalPages}
              onPageChange={setDecisionsPage}
              onDecisionClick={setSelectedDecisionId}
            />
          </motion.div>
        )}

        {/* All Positions Tab */}
        {activeTab === 'all' && (
          <motion.div
            key="all"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 100, damping: 15 }}
          >
            <AllPositionsTable
              positions={positions}
              loading={positionsLoading}
              mounted={mounted}
              onClosePosition={handleClosePosition}
              onRefresh={() => syncPositions(true)}
            />
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
