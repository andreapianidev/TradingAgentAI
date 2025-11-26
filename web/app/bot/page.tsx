'use client'

import { useEffect, useState, useRef } from 'react'
import {
  Terminal,
  RefreshCw,
  Trash2,
  Bot,
  Brain,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  Clock,
  Target,
  BarChart3,
  Filter,
  Newspaper,
  Fish,
  Waves,
  ExternalLink
} from 'lucide-react'
import { cn, formatCurrency, formatPercent } from '@/lib/utils'
import { supabase, TradingDecision, TradingPortfolioSnapshot } from '@/lib/supabase'

interface ActivityLog {
  id: string
  timestamp: string
  type: 'decision' | 'market' | 'portfolio' | 'system' | 'news' | 'whale'
  level: 'info' | 'success' | 'warning' | 'error'
  symbol?: string
  action?: string
  message: string
  details?: any
  url?: string
}

type FilterType = 'all' | 'decision' | 'market' | 'portfolio' | 'news' | 'whale'

export default function BotConsolePage() {
  const [activities, setActivities] = useState<ActivityLog[]>([])
  const [latestSnapshot, setLatestSnapshot] = useState<TradingPortfolioSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<FilterType>('all')
  const logsEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchActivityData()
    const interval = setInterval(fetchActivityData, 5000) // Poll every 5 seconds
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [activities, autoScroll])

  const fetchActivityData = async () => {
    setLoading(true)
    try {
      // Fetch recent decisions
      const { data: decisions } = await supabase
        .from('trading_decisions')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(50)

      // Fetch recent market contexts
      const { data: markets } = await supabase
        .from('trading_market_contexts')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(30)

      // Fetch recent portfolio snapshots
      const { data: snapshots } = await supabase
        .from('trading_portfolio_snapshots')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(20)

      // Fetch recent news
      const { data: news } = await supabase
        .from('trading_news')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(30)

      // Fetch recent whale alerts
      const { data: whaleAlerts } = await supabase
        .from('trading_whale_alerts')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(20)

      if (snapshots && snapshots.length > 0) {
        setLatestSnapshot(snapshots[0])
      }

      // Convert to activity logs
      const logs: ActivityLog[] = []

      // Add decisions
      decisions?.forEach(d => {
        const isOpen = d.action?.toLowerCase() === 'open'
        const isClose = d.action?.toLowerCase() === 'close'
        const direction = d.direction?.toUpperCase()

        logs.push({
          id: `decision-${d.id}`,
          timestamp: d.timestamp,
          type: 'decision',
          level: d.action === 'HOLD' ? 'info' : 'success',
          symbol: d.symbol,
          action: d.action,
          message: d.action === 'HOLD'
            ? `HOLD ${d.symbol} - Confidence: ${((d.confidence || 0) * 100).toFixed(0)}%`
            : `${d.action} ${direction} ${d.symbol} - Confidence: ${((d.confidence || 0) * 100).toFixed(0)}%`,
          details: {
            reasoning: d.reasoning,
            confidence: d.confidence,
            entry_price: d.entry_price,
            stop_loss: d.stop_loss,
            take_profit: d.take_profit,
            position_size_pct: d.position_size_pct
          }
        })
      })

      // Add market contexts
      markets?.forEach(m => {
        // Use correct column names from trading_market_contexts table
        const forecast = m.forecast_trend || 'N/A'
        const rsi = m.rsi ? parseFloat(m.rsi).toFixed(1) : 'N/A'
        const price = m.price ? parseFloat(m.price) : 0

        logs.push({
          id: `market-${m.id}`,
          timestamp: m.timestamp,
          type: 'market',
          level: 'info',
          symbol: m.symbol,
          message: `${m.symbol} Analysis: $${price.toLocaleString()} | RSI: ${rsi} | Forecast: ${forecast}`,
          details: {
            price: m.price,
            change_24h: m.price_change_24h,
            rsi: m.rsi,
            macd: m.macd,
            forecast_trend: m.forecast_trend,
            forecast_target: m.forecast_target_price
          }
        })
      })

      // Add portfolio snapshots
      snapshots?.forEach(s => {
        logs.push({
          id: `portfolio-${s.id}`,
          timestamp: s.timestamp,
          type: 'portfolio',
          level: 'info',
          message: `Portfolio Update: ${formatCurrency(parseFloat(s.total_equity_usdc || '0'))} | Exposure: ${parseFloat(s.exposure_pct || '0').toFixed(1)}% | Positions: ${s.open_positions_count || 0}`,
          details: {
            equity: s.total_equity_usdc,
            available: s.available_balance_usdc,
            exposure: s.exposure_pct,
            daily_pnl: s.daily_pnl,
            daily_pnl_pct: s.daily_pnl_pct
          }
        })
      })

      // Add news
      news?.forEach(n => {
        const sentimentEmoji = n.sentiment === 'positive' ? '📈' : n.sentiment === 'negative' ? '📉' : '📊'
        logs.push({
          id: `news-${n.id}`,
          timestamp: n.published_at || n.created_at,
          type: 'news',
          level: n.sentiment === 'negative' ? 'warning' : 'info',
          message: `${sentimentEmoji} ${n.title}`,
          url: n.url,
          details: {
            summary: n.summary,
            source: n.source,
            sentiment: n.sentiment,
            symbols: n.symbols
          }
        })
      })

      // Add whale alerts
      whaleAlerts?.forEach(w => {
        const amountUsd = parseFloat(w.amount_usd || '0')
        const flowIcon = w.flow_direction === 'inflow' ? '🔴' : w.flow_direction === 'outflow' ? '🟢' : '⚪'
        const flowLabel = w.flow_direction === 'inflow' ? 'TO Exchange' : w.flow_direction === 'outflow' ? 'FROM Exchange' : 'Transfer'

        logs.push({
          id: `whale-${w.id}`,
          timestamp: w.transaction_time || w.created_at,
          type: 'whale',
          level: amountUsd > 10000000 ? 'warning' : 'info',
          symbol: w.symbol,
          message: `${flowIcon} ${w.symbol} Whale: $${(amountUsd / 1000000).toFixed(1)}M ${flowLabel}`,
          details: {
            amount: w.amount,
            amount_usd: amountUsd,
            blockchain: w.blockchain,
            from_type: w.from_type,
            to_type: w.to_type,
            flow_direction: w.flow_direction,
            tx_hash: w.tx_hash
          }
        })
      })

      // Sort by timestamp
      logs.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

      setActivities(logs)
    } catch (error) {
      console.error('Failed to fetch activity data:', error)
    } finally {
      setLoading(false)
    }
  }

  const clearOldLogs = async () => {
    // This just clears the local view - keeps the database data
    setActivities([])
  }

  const toggleLogExpand = (logId: string) => {
    setExpandedLogs(prev => {
      const next = new Set(prev)
      if (next.has(logId)) {
        next.delete(logId)
      } else {
        next.add(logId)
      }
      return next
    })
  }

  const getLogIcon = (type: string, action?: string) => {
    switch (type) {
      case 'decision':
        if (action === 'HOLD') return <Clock className="w-4 h-4 text-gray-400" />
        if (action === 'OPEN') return <TrendingUp className="w-4 h-4 text-green-500" />
        if (action === 'CLOSE') return <TrendingDown className="w-4 h-4 text-blue-500" />
        return <Brain className="w-4 h-4 text-purple-500" />
      case 'market':
        return <BarChart3 className="w-4 h-4 text-cyan-500" />
      case 'portfolio':
        return <DollarSign className="w-4 h-4 text-yellow-500" />
      case 'news':
        return <Newspaper className="w-4 h-4 text-orange-500" />
      case 'whale':
        return <Fish className="w-4 h-4 text-blue-400" />
      default:
        return <Terminal className="w-4 h-4 text-gray-500" />
    }
  }

  const getLogColor = (type: string, level: string) => {
    if (level === 'error') return 'text-red-400'
    if (level === 'warning') return 'text-yellow-400'

    switch (type) {
      case 'decision': return 'text-purple-400'
      case 'market': return 'text-cyan-400'
      case 'portfolio': return 'text-yellow-400'
      case 'news': return 'text-orange-400'
      case 'whale': return 'text-blue-400'
      default: return 'text-gray-400'
    }
  }

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts)
    return date.toLocaleTimeString('it-IT', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatDate = (ts: string) => {
    return new Date(ts).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit'
    })
  }

  const filteredActivities = activities.filter(a => {
    if (filter === 'all') return true
    return a.type === filter
  })

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Terminal className="w-6 h-6 text-green-500" />
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Activity Console</h1>
          </div>
          <span className="text-sm text-gray-500">
            Real-time trading activity
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter */}
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 overflow-x-auto">
            {(['all', 'decision', 'market', 'portfolio', 'news', 'whale'] as FilterType[]).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  'px-3 py-1.5 rounded text-sm transition-colors whitespace-nowrap',
                  filter === f
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                )}
              >
                {f === 'all' ? 'All' : f === 'whale' ? 'Whale' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={cn(
              'p-2 rounded-lg transition-colors',
              autoScroll
                ? 'bg-green-100 dark:bg-green-500/10 text-green-600 dark:text-green-500'
                : 'text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
            )}
            title="Auto-scroll"
          >
            <ChevronDown className="w-5 h-5" />
          </button>

          <button
            onClick={fetchActivityData}
            className="p-2 text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={cn("w-5 h-5", loading && "animate-spin")} />
          </button>

          <button
            onClick={clearOldLogs}
            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
            title="Clear view"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Status Bar */}
      {latestSnapshot && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <DollarSign className="w-5 h-5 text-green-500" />
            <div>
              <div className="text-xs text-gray-500">Equity</div>
              <div className="font-bold text-gray-900 dark:text-white">{formatCurrency(Number(latestSnapshot.total_equity_usdc) || 0)}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-blue-500" />
            <div>
              <div className="text-xs text-gray-500">Available</div>
              <div className="font-bold text-gray-900 dark:text-white">{formatCurrency(Number(latestSnapshot.available_balance_usdc) || 0)}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-yellow-500" />
            <div>
              <div className="text-xs text-gray-500">Exposure</div>
              <div className="font-bold text-gray-900 dark:text-white">{(Number(latestSnapshot.exposure_pct) || 0).toFixed(1)}%</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Bot className="w-5 h-5 text-purple-500" />
            <div>
              <div className="text-xs text-gray-500">Open Positions</div>
              <div className="font-bold text-gray-900 dark:text-white">{latestSnapshot.open_positions_count || 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* Activity Output */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto bg-white dark:bg-gray-950 font-mono text-sm"
      >
        {filteredActivities.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Terminal className="w-16 h-16 mb-4 opacity-30" />
            <p>No activity yet.</p>
            <p className="text-xs mt-1">Start the bot from the header to see trading activity.</p>
          </div>
        ) : (
          <div className="p-4 space-y-1">
            {filteredActivities.map((log, index) => {
              // Check if we should show date separator
              const showDate = index === 0 ||
                formatDate(log.timestamp) !== formatDate(filteredActivities[index - 1].timestamp)

              return (
                <div key={log.id}>
                  {showDate && (
                    <div className="flex items-center gap-2 py-2 mt-2 first:mt-0">
                      <div className="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
                      <span className="text-xs text-gray-500 dark:text-gray-600 px-2">{formatDate(log.timestamp)}</span>
                      <div className="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
                    </div>
                  )}

                  <div className="group">
                    <div
                      className={cn(
                        'flex items-start gap-2 py-1.5 px-2 rounded hover:bg-gray-100 dark:hover:bg-gray-900/50',
                        log.details && 'cursor-pointer'
                      )}
                      onClick={() => log.details && toggleLogExpand(log.id)}
                    >
                      {/* Expand icon */}
                      {log.details ? (
                        expandedLogs.has(log.id) ? (
                          <ChevronDown className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                        )
                      ) : (
                        <span className="w-4 flex-shrink-0" />
                      )}

                      {/* Icon */}
                      <span className="flex-shrink-0 mt-0.5">
                        {getLogIcon(log.type, log.action)}
                      </span>

                      {/* Timestamp */}
                      <span className="text-gray-600 flex-shrink-0">
                        {formatTimestamp(log.timestamp)}
                      </span>

                      {/* Type badge */}
                      <span className={cn(
                        'flex-shrink-0 px-1.5 py-0.5 rounded text-xs uppercase',
                        log.type === 'decision' && 'bg-purple-500/10 text-purple-400',
                        log.type === 'market' && 'bg-cyan-500/10 text-cyan-400',
                        log.type === 'portfolio' && 'bg-yellow-500/10 text-yellow-400',
                        log.type === 'news' && 'bg-orange-500/10 text-orange-400',
                        log.type === 'whale' && 'bg-blue-500/10 text-blue-400'
                      )}>
                        {log.type}
                      </span>

                      {/* Symbol */}
                      {log.symbol && (
                        <span className="text-gray-900 dark:text-white font-semibold flex-shrink-0">
                          {log.symbol}
                        </span>
                      )}

                      {/* Message */}
                      <span className={cn('break-all', getLogColor(log.type, log.level))}>
                        {log.message}
                      </span>

                      {/* External link for news */}
                      {log.url && (
                        <a
                          href={log.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="flex-shrink-0 p-1 text-gray-400 hover:text-blue-400 transition-colors"
                          title="Open article"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>

                    {/* Expanded Details */}
                    {log.details && expandedLogs.has(log.id) && (
                      <div className="ml-6 mt-1 mb-2 p-3 bg-gray-100 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
                        {log.type === 'decision' && log.details.reasoning && (
                          <div className="mb-3">
                            <div className="text-xs text-gray-500 mb-1">LLM Reasoning:</div>
                            <p className="text-sm text-gray-700 dark:text-gray-300">{log.details.reasoning}</p>
                          </div>
                        )}
                        {log.type === 'news' && log.details.summary && (
                          <div className="mb-3">
                            <div className="text-xs text-gray-500 mb-1">Summary:</div>
                            <p className="text-sm text-gray-700 dark:text-gray-300">{log.details.summary}</p>
                            {log.details.source && (
                              <p className="text-xs text-gray-500 mt-2">Source: {log.details.source}</p>
                            )}
                          </div>
                        )}
                        {log.type === 'whale' && (
                          <div className="mb-3 space-y-1">
                            <div className="text-xs text-gray-500">Transaction Details:</div>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <div className="text-gray-600 dark:text-gray-400">Amount:</div>
                              <div className="text-gray-900 dark:text-white">${log.details.amount_usd?.toLocaleString()}</div>
                              <div className="text-gray-600 dark:text-gray-400">From:</div>
                              <div className="text-gray-900 dark:text-white">{log.details.from_type || 'Unknown'}</div>
                              <div className="text-gray-600 dark:text-gray-400">To:</div>
                              <div className="text-gray-900 dark:text-white">{log.details.to_type || 'Unknown'}</div>
                              <div className="text-gray-600 dark:text-gray-400">Flow:</div>
                              <div className={cn(
                                log.details.flow_direction === 'inflow' && 'text-red-400',
                                log.details.flow_direction === 'outflow' && 'text-green-400'
                              )}>
                                {log.details.flow_direction === 'inflow' ? '→ Exchange (Sell pressure)' :
                                 log.details.flow_direction === 'outflow' ? '← Exchange (Buy pressure)' : 'Transfer'}
                              </div>
                            </div>
                          </div>
                        )}
                        {log.type !== 'news' && log.type !== 'whale' && (
                          <pre className="text-xs text-gray-500 dark:text-gray-400 whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(log.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      {/* Footer with stats */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-500">
        <div className="flex flex-wrap items-center gap-3">
          <span>{filteredActivities.length} activities</span>
          <span className="hidden sm:inline text-gray-300 dark:text-gray-700">|</span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-purple-500" /> {activities.filter(a => a.type === 'decision').length}
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-500" /> {activities.filter(a => a.type === 'market').length}
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-yellow-500" /> {activities.filter(a => a.type === 'portfolio').length}
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-orange-500" /> {activities.filter(a => a.type === 'news').length}
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-400" /> {activities.filter(a => a.type === 'whale').length}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-3 h-3" />
          <span>Auto-refresh 5s</span>
        </div>
      </div>
    </div>
  )
}
