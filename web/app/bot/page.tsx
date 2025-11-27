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
  ExternalLink,
  Gauge,
  LineChart,
  ArrowUpDown,
  Crosshair,
  Zap,
  BookOpen,
  Globe
} from 'lucide-react'
import { cn, formatCurrency, formatPercent } from '@/lib/utils'
import { supabase, TradingDecision, TradingPortfolioSnapshot, TradingMarketContext } from '@/lib/supabase'

interface ActivityLog {
  id: string
  timestamp: string
  type: 'decision' | 'market' | 'portfolio' | 'system' | 'news' | 'whale' | 'sentiment' | 'global'
  level: 'info' | 'success' | 'warning' | 'error'
  symbol?: string
  action?: string
  message: string
  details?: any
  url?: string
}

interface LiveAccountData {
  success: boolean
  configured: boolean
  timestamp?: string
  account?: {
    equity: number
    cash: number
    buyingPower: number
    positionsValue: number
    lastEquity: number
    dailyPnl: number
    dailyPnlPct: number
    totalUnrealizedPnl: number
    exposurePct: number
    positionsCount: number
  }
  positions?: Array<{
    symbol: string
    qty: number
    entryPrice: number
    currentPrice: number
    marketValue: number
    unrealizedPnl: number
    unrealizedPnlPct: number
    changeToday: number
  }>
  mode?: 'paper' | 'live'
  error?: string
}

interface DatabasePortfolioData {
  totalEquity: number
  availableBalance: number
  investedValue: number
  unrealizedPnl: number
  exposurePct: number
  positionsCount: number
  dailyPnl: number
  totalPnl: number
  totalPnlPct: number
  positions: Array<{
    symbol: string
    entryPrice: number
    quantity: number
    marketValue: number
    unrealizedPnl: number
    unrealizedPnlPct: number
  }>
}

const INITIAL_CAPITAL = 100000

type FilterType = 'all' | 'decision' | 'market' | 'portfolio' | 'news' | 'whale' | 'sentiment' | 'global'

export default function BotConsolePage() {
  const [activities, setActivities] = useState<ActivityLog[]>([])
  const [latestSnapshot, setLatestSnapshot] = useState<TradingPortfolioSnapshot | null>(null)
  const [liveAccount, setLiveAccount] = useState<LiveAccountData | null>(null)
  const [dbPortfolio, setDbPortfolio] = useState<DatabasePortfolioData | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<FilterType>('all')
  const logsEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Fetch portfolio data from database as fallback
  const fetchDatabasePortfolio = async () => {
    try {
      // Get latest portfolio snapshot
      const { data: snapshot } = await supabase
        .from('trading_portfolio_snapshots')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(1)
        .single()

      // Get open positions
      const { data: openPositions } = await supabase
        .from('trading_positions')
        .select('*')
        .eq('status', 'open')

      if (snapshot) {
        const equity = parseFloat(String(snapshot.total_equity_usdc)) || INITIAL_CAPITAL
        const availableBalance = parseFloat(String(snapshot.available_balance_usdc)) || equity

        // Calculate invested value and unrealized P&L from positions
        let investedValue = 0
        let unrealizedPnl = 0
        const positionsData: DatabasePortfolioData['positions'] = []

        if (openPositions) {
          for (const pos of openPositions) {
            const entryPrice = parseFloat(String(pos.entry_price)) || 0
            const quantity = parseFloat(String(pos.quantity)) || 0
            const posUnrealizedPnl = parseFloat(String(pos.unrealized_pnl)) || 0
            const posUnrealizedPnlPct = parseFloat(String(pos.unrealized_pnl_pct)) || 0
            const marketValue = entryPrice * quantity + posUnrealizedPnl

            investedValue += entryPrice * quantity
            unrealizedPnl += posUnrealizedPnl

            positionsData.push({
              symbol: pos.symbol,
              entryPrice,
              quantity,
              marketValue,
              unrealizedPnl: posUnrealizedPnl,
              unrealizedPnlPct: posUnrealizedPnlPct,
            })
          }
        }

        const totalPnl = equity - INITIAL_CAPITAL
        const totalPnlPct = (totalPnl / INITIAL_CAPITAL) * 100

        setDbPortfolio({
          totalEquity: equity,
          availableBalance,
          investedValue,
          unrealizedPnl,
          exposurePct: parseFloat(String(snapshot.exposure_pct)) || 0,
          positionsCount: openPositions?.length || 0,
          dailyPnl: parseFloat(String(snapshot.daily_pnl)) || 0,
          totalPnl,
          totalPnlPct,
          positions: positionsData,
        })
      }
    } catch (error) {
      console.error('Error fetching database portfolio:', error)
    }
  }

  useEffect(() => {
    fetchActivityData()
    fetchLiveAccount()
    fetchDatabasePortfolio()
    const activityInterval = setInterval(fetchActivityData, 5000) // Poll every 5 seconds
    const liveInterval = setInterval(() => {
      fetchLiveAccount()
      fetchDatabasePortfolio()
    }, 10000) // Live data every 10 seconds
    return () => {
      clearInterval(activityInterval)
      clearInterval(liveInterval)
    }
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

      // Fetch recent market contexts with ALL data
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

      // Fetch whale flow summaries
      const { data: whaleFlows } = await supabase
        .from('trading_whale_flow_summary')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(10)

      // Fetch CoinGecko global market data
      const { data: globalMarket } = await supabase
        .from('trading_market_global')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(10)

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
        const execStatus = d.execution_status?.toLowerCase()

        // Determine log level based on execution status
        let level: 'info' | 'success' | 'warning' | 'error' = 'info'
        if (execStatus === 'executed') level = 'success'
        else if (execStatus === 'failed') level = 'error'
        else if (execStatus === 'skipped') level = 'warning'
        else if (d.action === 'HOLD' || d.action === 'hold') level = 'info'

        // Build status indicator
        const statusIcon = execStatus === 'executed' ? '✅'
          : execStatus === 'failed' ? '❌'
          : execStatus === 'skipped' ? '⏭️'
          : '⏳'

        // Build message with execution status
        let message = ''
        if (d.action === 'HOLD' || d.action === 'hold') {
          message = `HOLD ${d.symbol} - Confidence: ${((d.confidence || 0) * 100).toFixed(0)}%`
        } else {
          message = `${statusIcon} ${d.action?.toUpperCase()} ${direction} ${d.symbol} - Confidence: ${((d.confidence || 0) * 100).toFixed(0)}%`
          if (execStatus === 'executed' && d.entry_price) {
            message += ` @ $${parseFloat(d.entry_price).toLocaleString()}`
          }
          if (execStatus === 'failed') {
            const errorMsg = d.execution_details?.error || 'Unknown error'
            message += ` [FAILED: ${errorMsg}]`
          }
        }

        logs.push({
          id: `decision-${d.id}`,
          timestamp: d.timestamp,
          type: 'decision',
          level,
          symbol: d.symbol,
          action: d.action,
          message,
          details: {
            reasoning: d.reasoning,
            confidence: d.confidence,
            execution_status: d.execution_status,
            execution_details: d.execution_details,
            entry_price: d.entry_price,
            entry_quantity: d.entry_quantity,
            order_id: d.order_id,
            stop_loss_pct: d.stop_loss_pct,
            take_profit_pct: d.take_profit_pct,
            position_size_pct: d.position_size_pct,
            leverage: d.leverage
          }
        })
      })

      // Add market contexts with FULL details
      markets?.forEach(m => {
        const forecast = m.forecast_trend || 'N/A'
        const rsi = m.rsi ? parseFloat(m.rsi).toFixed(1) : 'N/A'
        const price = m.price ? parseFloat(m.price) : 0
        const macd = m.macd ? parseFloat(m.macd) : null
        const macdSignal = m.macd_signal ? parseFloat(m.macd_signal) : null
        const macdHistogram = m.macd_histogram ? parseFloat(m.macd_histogram) : null
        const ema2 = m.ema2 ? parseFloat(m.ema2) : null
        const ema20 = m.ema20 ? parseFloat(m.ema20) : null

        // Determine trend from MACD
        const macdTrend = macd !== null && macdSignal !== null
          ? (macd > macdSignal ? 'BULLISH' : 'BEARISH')
          : 'N/A'

        // RSI interpretation
        const rsiValue = m.rsi ? parseFloat(m.rsi) : 50
        const rsiStatus = rsiValue > 70 ? '(OVERBOUGHT)' : rsiValue < 30 ? '(OVERSOLD)' : ''

        logs.push({
          id: `market-${m.id}`,
          timestamp: m.timestamp,
          type: 'market',
          level: 'info',
          symbol: m.symbol,
          message: `${m.symbol} Analysis: $${price.toLocaleString()} | RSI: ${rsi}${rsiStatus} | MACD: ${macdTrend} | Forecast: ${forecast.toUpperCase()}`,
          details: {
            // Price
            price: m.price,
            change_24h: m.price_change_24h,
            // Technical Indicators
            rsi: m.rsi,
            rsi_status: rsiStatus,
            macd: m.macd,
            macd_signal: m.macd_signal,
            macd_histogram: m.macd_histogram,
            macd_trend: macdTrend,
            ema2: m.ema2,
            ema20: m.ema20,
            price_vs_ema20: ema20 ? (price > ema20 ? 'ABOVE' : 'BELOW') : 'N/A',
            // Pivot Points
            pivot_pp: m.pivot_pp,
            pivot_r1: m.pivot_r1,
            pivot_r2: m.pivot_r2,
            pivot_s1: m.pivot_s1,
            pivot_s2: m.pivot_s2,
            pivot_distance_pct: m.pivot_distance_pct,
            // Forecast
            forecast_trend: m.forecast_trend,
            forecast_target_price: m.forecast_target_price,
            forecast_change_pct: m.forecast_change_pct,
            forecast_confidence: m.forecast_confidence,
            // Order Book
            orderbook_bid_volume: m.orderbook_bid_volume,
            orderbook_ask_volume: m.orderbook_ask_volume,
            orderbook_ratio: m.orderbook_ratio,
            // Sentiment
            sentiment_label: m.sentiment_label,
            sentiment_score: m.sentiment_score
          }
        })

        // Add a separate sentiment log if sentiment data exists
        if (m.sentiment_score !== null && m.sentiment_score !== undefined) {
          const score = m.sentiment_score
          const label = m.sentiment_label || 'NEUTRAL'
          let interpretation = ''
          if (score <= 25) interpretation = 'Extreme Fear - Potential buying opportunity'
          else if (score <= 45) interpretation = 'Fear - Market uncertainty'
          else if (score <= 55) interpretation = 'Neutral - Market indecision'
          else if (score <= 75) interpretation = 'Greed - Market optimism'
          else interpretation = 'Extreme Greed - Potential selling opportunity'

          logs.push({
            id: `sentiment-${m.id}`,
            timestamp: m.timestamp,
            type: 'sentiment',
            level: score <= 25 || score >= 75 ? 'warning' : 'info',
            message: `Fear & Greed Index: ${score} (${label}) - ${interpretation}`,
            details: {
              score,
              label,
              interpretation
            }
          })
        }
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
            margin_used: s.margin_used_usdc,
            exposure: s.exposure_pct,
            daily_pnl: s.daily_pnl,
            daily_pnl_pct: s.daily_pnl_pct,
            total_pnl: s.total_pnl,
            total_pnl_pct: s.total_pnl_pct,
            open_positions_count: s.open_positions_count,
            trading_mode: s.trading_mode
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

      // Add CoinGecko global market data
      globalMarket?.forEach(g => {
        const btcDom = g.btc_dominance ? parseFloat(g.btc_dominance) : 0
        const mcapChange = g.market_cap_change_24h_pct ? parseFloat(g.market_cap_change_24h_pct) : 0
        const totalMcap = g.total_market_cap_usd ? parseFloat(g.total_market_cap_usd) : 0
        const trendingSymbols = g.trending_symbols || []
        const trackedTrending = g.tracked_trending || []

        const mcapTrend = mcapChange >= 0 ? '📈' : '📉'
        const trendingStr = trendingSymbols.slice(0, 5).join(', ') || 'N/A'

        logs.push({
          id: `global-${g.id}`,
          timestamp: g.timestamp || g.created_at,
          type: 'global',
          level: Math.abs(mcapChange) > 3 ? 'warning' : 'info',
          message: `${mcapTrend} Market: BTC ${btcDom.toFixed(1)}% | MCap $${(totalMcap/1e12).toFixed(2)}T (${mcapChange >= 0 ? '+' : ''}${mcapChange.toFixed(2)}%) | Trending: ${trendingStr}`,
          details: {
            btc_dominance: btcDom,
            eth_dominance: g.eth_dominance ? parseFloat(g.eth_dominance) : 0,
            total_market_cap: totalMcap,
            total_volume_24h: g.total_volume_24h_usd ? parseFloat(g.total_volume_24h_usd) : 0,
            market_cap_change_24h: mcapChange,
            active_cryptocurrencies: g.active_cryptocurrencies,
            trending_coins: g.trending_coins || [],
            trending_symbols: trendingSymbols,
            tracked_trending: trackedTrending
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

  const fetchLiveAccount = async () => {
    try {
      const response = await fetch('/api/account/live')
      const data: LiveAccountData = await response.json()
      if (data.success) {
        setLiveAccount(data)
      }
    } catch (error) {
      console.error('Failed to fetch live account data:', error)
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
      case 'sentiment':
        return <Gauge className="w-4 h-4 text-pink-500" />
      case 'global':
        return <Globe className="w-4 h-4 text-teal-500" />
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
      case 'sentiment': return 'text-pink-400'
      case 'global': return 'text-teal-400'
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

  // Render expanded market details with all indicators
  const renderMarketDetails = (details: any) => {
    return (
      <div className="space-y-4">
        {/* Price Section */}
        <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-4 h-4 text-green-500" />
            <span className="text-xs font-semibold text-gray-500 uppercase">Price Data</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Current Price:</span>
              <span className="text-gray-900 dark:text-white font-mono">${parseFloat(details.price || 0).toLocaleString()}</span>
            </div>
            {details.change_24h && (
              <div className="flex justify-between">
                <span className="text-gray-500">24h Change:</span>
                <span className={cn("font-mono", parseFloat(details.change_24h) >= 0 ? "text-green-500" : "text-red-500")}>
                  {parseFloat(details.change_24h) >= 0 ? '+' : ''}{parseFloat(details.change_24h).toFixed(2)}%
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Technical Indicators */}
        <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <LineChart className="w-4 h-4 text-cyan-500" />
            <span className="text-xs font-semibold text-gray-500 uppercase">Technical Indicators</span>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
            {/* RSI */}
            <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
              <div className="text-xs text-gray-500">RSI (14)</div>
              <div className={cn(
                "text-lg font-bold",
                parseFloat(details.rsi || 50) > 70 ? "text-red-500" :
                parseFloat(details.rsi || 50) < 30 ? "text-green-500" : "text-gray-900 dark:text-white"
              )}>
                {details.rsi ? parseFloat(details.rsi).toFixed(1) : 'N/A'}
              </div>
              <div className="text-xs text-gray-500">{details.rsi_status}</div>
            </div>

            {/* MACD */}
            <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
              <div className="text-xs text-gray-500">MACD</div>
              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {details.macd ? parseFloat(details.macd).toFixed(4) : 'N/A'}
              </div>
              <div className={cn(
                "text-xs",
                details.macd_trend === 'BULLISH' ? "text-green-500" : "text-red-500"
              )}>
                {details.macd_trend}
              </div>
            </div>

            {/* MACD Signal */}
            <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
              <div className="text-xs text-gray-500">Signal Line</div>
              <div className="text-lg font-bold text-gray-900 dark:text-white">
                {details.macd_signal ? parseFloat(details.macd_signal).toFixed(4) : 'N/A'}
              </div>
            </div>

            {/* MACD Histogram */}
            <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
              <div className="text-xs text-gray-500">Histogram</div>
              <div className={cn(
                "text-lg font-bold",
                parseFloat(details.macd_histogram || 0) >= 0 ? "text-green-500" : "text-red-500"
              )}>
                {details.macd_histogram ? parseFloat(details.macd_histogram).toFixed(4) : 'N/A'}
              </div>
            </div>

            {/* EMA2 */}
            <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
              <div className="text-xs text-gray-500">EMA (2)</div>
              <div className="text-lg font-bold text-gray-900 dark:text-white font-mono">
                ${details.ema2 ? parseFloat(details.ema2).toLocaleString(undefined, {maximumFractionDigits: 2}) : 'N/A'}
              </div>
            </div>

            {/* EMA20 */}
            <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
              <div className="text-xs text-gray-500">EMA (20)</div>
              <div className="text-lg font-bold text-gray-900 dark:text-white font-mono">
                ${details.ema20 ? parseFloat(details.ema20).toLocaleString(undefined, {maximumFractionDigits: 2}) : 'N/A'}
              </div>
              <div className={cn(
                "text-xs",
                details.price_vs_ema20 === 'ABOVE' ? "text-green-500" : "text-red-500"
              )}>
                Price {details.price_vs_ema20}
              </div>
            </div>
          </div>
        </div>

        {/* Pivot Points */}
        {(details.pivot_pp || details.pivot_r1 || details.pivot_s1) && (
          <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <Crosshair className="w-4 h-4 text-purple-500" />
              <span className="text-xs font-semibold text-gray-500 uppercase">Pivot Points</span>
            </div>
            <div className="grid grid-cols-5 gap-2 text-sm text-center">
              <div className="bg-red-500/10 p-2 rounded">
                <div className="text-xs text-red-400">R2</div>
                <div className="text-red-500 font-mono font-bold">
                  ${details.pivot_r2 ? parseFloat(details.pivot_r2).toLocaleString() : '-'}
                </div>
              </div>
              <div className="bg-red-500/5 p-2 rounded">
                <div className="text-xs text-red-300">R1</div>
                <div className="text-red-400 font-mono font-bold">
                  ${details.pivot_r1 ? parseFloat(details.pivot_r1).toLocaleString() : '-'}
                </div>
              </div>
              <div className="bg-purple-500/10 p-2 rounded">
                <div className="text-xs text-purple-400">PP</div>
                <div className="text-purple-500 font-mono font-bold">
                  ${details.pivot_pp ? parseFloat(details.pivot_pp).toLocaleString() : '-'}
                </div>
              </div>
              <div className="bg-green-500/5 p-2 rounded">
                <div className="text-xs text-green-300">S1</div>
                <div className="text-green-400 font-mono font-bold">
                  ${details.pivot_s1 ? parseFloat(details.pivot_s1).toLocaleString() : '-'}
                </div>
              </div>
              <div className="bg-green-500/10 p-2 rounded">
                <div className="text-xs text-green-400">S2</div>
                <div className="text-green-500 font-mono font-bold">
                  ${details.pivot_s2 ? parseFloat(details.pivot_s2).toLocaleString() : '-'}
                </div>
              </div>
            </div>
            {details.pivot_distance_pct && (
              <div className="text-center mt-2 text-xs text-gray-500">
                Distance from PP: <span className="text-gray-900 dark:text-white">{parseFloat(details.pivot_distance_pct).toFixed(2)}%</span>
              </div>
            )}
          </div>
        )}

        {/* Forecast */}
        {details.forecast_trend && (
          <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-yellow-500" />
              <span className="text-xs font-semibold text-gray-500 uppercase">Prophet Forecast</span>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
              <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                <div className="text-xs text-gray-500">Trend</div>
                <div className={cn(
                  "text-lg font-bold uppercase",
                  details.forecast_trend?.toLowerCase() === 'up' || details.forecast_trend?.toLowerCase() === 'bullish' ? "text-green-500" :
                  details.forecast_trend?.toLowerCase() === 'down' || details.forecast_trend?.toLowerCase() === 'bearish' ? "text-red-500" : "text-gray-500"
                )}>
                  {details.forecast_trend?.toUpperCase() || 'N/A'}
                </div>
              </div>
              <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                <div className="text-xs text-gray-500">Target Price</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white font-mono">
                  ${details.forecast_target_price ? parseFloat(details.forecast_target_price).toLocaleString() : 'N/A'}
                </div>
              </div>
              <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                <div className="text-xs text-gray-500">Expected Change</div>
                <div className={cn(
                  "text-lg font-bold",
                  parseFloat(details.forecast_change_pct || 0) >= 0 ? "text-green-500" : "text-red-500"
                )}>
                  {details.forecast_change_pct ? `${parseFloat(details.forecast_change_pct) >= 0 ? '+' : ''}${parseFloat(details.forecast_change_pct).toFixed(2)}%` : 'N/A'}
                </div>
              </div>
              <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                <div className="text-xs text-gray-500">Confidence</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {details.forecast_confidence ? `${(parseFloat(details.forecast_confidence) * 100).toFixed(0)}%` : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Order Book */}
        {(details.orderbook_bid_volume || details.orderbook_ask_volume) && (
          <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-4 h-4 text-indigo-500" />
              <span className="text-xs font-semibold text-gray-500 uppercase">Order Book</span>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="bg-green-500/10 p-2 rounded text-center">
                <div className="text-xs text-green-400">Bid Volume</div>
                <div className="text-lg font-bold text-green-500 font-mono">
                  {details.orderbook_bid_volume ? parseFloat(details.orderbook_bid_volume).toLocaleString(undefined, {maximumFractionDigits: 2}) : 'N/A'}
                </div>
              </div>
              <div className="bg-red-500/10 p-2 rounded text-center">
                <div className="text-xs text-red-400">Ask Volume</div>
                <div className="text-lg font-bold text-red-500 font-mono">
                  {details.orderbook_ask_volume ? parseFloat(details.orderbook_ask_volume).toLocaleString(undefined, {maximumFractionDigits: 2}) : 'N/A'}
                </div>
              </div>
              <div className={cn(
                "p-2 rounded text-center",
                parseFloat(details.orderbook_ratio || 1) > 1 ? "bg-green-500/10" : "bg-red-500/10"
              )}>
                <div className="text-xs text-gray-500">Bid/Ask Ratio</div>
                <div className={cn(
                  "text-lg font-bold",
                  parseFloat(details.orderbook_ratio || 1) > 1 ? "text-green-500" : "text-red-500"
                )}>
                  {details.orderbook_ratio ? parseFloat(details.orderbook_ratio).toFixed(2) : 'N/A'}
                </div>
                <div className="text-xs text-gray-500">
                  {parseFloat(details.orderbook_ratio || 1) > 1.2 ? 'Buying Pressure' :
                   parseFloat(details.orderbook_ratio || 1) < 0.8 ? 'Selling Pressure' : 'Balanced'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Sentiment */}
        {details.sentiment_score !== null && details.sentiment_score !== undefined && (
          <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <Gauge className="w-4 h-4 text-pink-500" />
              <span className="text-xs font-semibold text-gray-500 uppercase">Market Sentiment</span>
            </div>
            <div className="flex items-center gap-4">
              <div className={cn(
                "text-3xl font-bold",
                details.sentiment_score <= 25 ? "text-red-500" :
                details.sentiment_score <= 45 ? "text-orange-500" :
                details.sentiment_score <= 55 ? "text-gray-500" :
                details.sentiment_score <= 75 ? "text-lime-500" : "text-green-500"
              )}>
                {details.sentiment_score}
              </div>
              <div>
                <div className={cn(
                  "font-semibold",
                  details.sentiment_score <= 25 ? "text-red-500" :
                  details.sentiment_score <= 45 ? "text-orange-500" :
                  details.sentiment_score <= 55 ? "text-gray-500" :
                  details.sentiment_score <= 75 ? "text-lime-500" : "text-green-500"
                )}>
                  {details.sentiment_label || 'NEUTRAL'}
                </div>
                <div className="text-xs text-gray-500">Fear & Greed Index</div>
              </div>
              {/* Sentiment Bar */}
              <div className="flex-1 h-2 bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full relative">
                <div
                  className="absolute w-3 h-3 bg-white border-2 border-gray-800 rounded-full -top-0.5 transform -translate-x-1/2"
                  style={{ left: `${details.sentiment_score}%` }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

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
            {(['all', 'decision', 'market', 'portfolio', 'news', 'whale', 'sentiment', 'global'] as FilterType[]).map(f => (
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

      {/* Live Portfolio Status Bar */}
      {(liveAccount?.account || dbPortfolio || latestSnapshot) && (
        <div className="border-b border-gray-200 dark:border-gray-800">
          {/* Main Portfolio Value */}
          <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-900/50 dark:to-gray-800/30">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className={cn(
                  "p-3 rounded-xl",
                  (dbPortfolio?.totalPnl ?? 0) >= 0 ? "bg-green-500/10" : "bg-red-500/10"
                )}>
                  <DollarSign className={cn(
                    "w-8 h-8",
                    (dbPortfolio?.totalPnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
                  )} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 uppercase tracking-wide">Portfolio Value</span>
                    {liveAccount?.configured && liveAccount?.success && (
                      <span className="flex items-center gap-1 px-1.5 py-0.5 bg-green-500/10 text-green-500 text-xs rounded">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                        LIVE
                      </span>
                    )}
                    {!liveAccount?.success && dbPortfolio && (
                      <span className="flex items-center gap-1 px-1.5 py-0.5 bg-blue-500/10 text-blue-500 text-xs rounded">
                        DB
                      </span>
                    )}
                    {(liveAccount?.mode === 'paper' || (!liveAccount?.success && dbPortfolio)) && (
                      <span className="px-1.5 py-0.5 bg-yellow-500/10 text-yellow-600 text-xs rounded">
                        PAPER
                      </span>
                    )}
                  </div>
                  <div className="text-3xl font-bold text-gray-900 dark:text-white">
                    {formatCurrency(liveAccount?.account?.equity ?? dbPortfolio?.totalEquity ?? Number(latestSnapshot?.total_equity_usdc) ?? INITIAL_CAPITAL)}
                  </div>
                  {/* Show Total P&L from initial capital */}
                  {(liveAccount?.account || dbPortfolio) && (
                    <div className={cn(
                      "flex items-center gap-1 text-sm font-medium",
                      (dbPortfolio?.totalPnl ?? liveAccount?.account?.dailyPnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
                    )}>
                      {(dbPortfolio?.totalPnl ?? liveAccount?.account?.dailyPnl ?? 0) >= 0 ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : (
                        <TrendingDown className="w-4 h-4" />
                      )}
                      <span>{(dbPortfolio?.totalPnl ?? 0) >= 0 ? '+' : ''}{formatCurrency(dbPortfolio?.totalPnl ?? liveAccount?.account?.dailyPnl ?? 0)}</span>
                      <span className="text-gray-500">({(dbPortfolio?.totalPnlPct ?? liveAccount?.account?.dailyPnlPct ?? 0) >= 0 ? '+' : ''}{(dbPortfolio?.totalPnlPct ?? liveAccount?.account?.dailyPnlPct ?? 0).toFixed(2)}%)</span>
                      <span className="text-xs text-gray-400 ml-1">total</span>
                    </div>
                  )}
                </div>
              </div>
              {liveAccount?.timestamp && (
                <div className="text-xs text-gray-400">
                  Updated: {new Date(liveAccount.timestamp).toLocaleTimeString('it-IT')}
                </div>
              )}
            </div>
          </div>

          {/* Breakdown Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 p-4 bg-gray-50/50 dark:bg-gray-900/30">
            <div className="flex items-center gap-3">
              <Activity className="w-5 h-5 text-blue-500" />
              <div>
                <div className="text-xs text-gray-500">Cash</div>
                <div className="font-bold text-gray-900 dark:text-white">
                  {formatCurrency(liveAccount?.account?.cash ?? dbPortfolio?.availableBalance ?? Number(latestSnapshot?.available_balance_usdc) ?? 0)}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-purple-500" />
              <div>
                <div className="text-xs text-gray-500">Invested</div>
                <div className="font-bold text-gray-900 dark:text-white">
                  {formatCurrency(liveAccount?.account?.positionsValue ?? dbPortfolio?.investedValue ?? 0)}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {(liveAccount?.account?.totalUnrealizedPnl ?? dbPortfolio?.unrealizedPnl ?? 0) >= 0 ? (
                <TrendingUp className="w-5 h-5 text-green-500" />
              ) : (
                <TrendingDown className="w-5 h-5 text-red-500" />
              )}
              <div>
                <div className="text-xs text-gray-500">Unrealized P&L</div>
                <div className={cn(
                  "font-bold",
                  (liveAccount?.account?.totalUnrealizedPnl ?? dbPortfolio?.unrealizedPnl ?? 0) >= 0 ? "text-green-500" : "text-red-500"
                )}>
                  {(liveAccount?.account?.totalUnrealizedPnl ?? dbPortfolio?.unrealizedPnl ?? 0) >= 0 ? '+' : ''}{formatCurrency(liveAccount?.account?.totalUnrealizedPnl ?? dbPortfolio?.unrealizedPnl ?? 0)}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-yellow-500" />
              <div>
                <div className="text-xs text-gray-500">Exposure</div>
                <div className="font-bold text-gray-900 dark:text-white">
                  {(liveAccount?.account?.exposurePct ?? dbPortfolio?.exposurePct ?? Number(latestSnapshot?.exposure_pct) ?? 0).toFixed(1)}%
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Bot className="w-5 h-5 text-cyan-500" />
              <div>
                <div className="text-xs text-gray-500">Positions</div>
                <div className="font-bold text-gray-900 dark:text-white">
                  {liveAccount?.account?.positionsCount ?? dbPortfolio?.positionsCount ?? latestSnapshot?.open_positions_count ?? 0}
                </div>
              </div>
            </div>
          </div>

          {/* Open Positions Detail - show from live API or database */}
          {((liveAccount?.positions && liveAccount.positions.length > 0) || (dbPortfolio?.positions && dbPortfolio.positions.length > 0)) && (
            <div className="px-4 pb-4 bg-gray-50/50 dark:bg-gray-900/30">
              <div className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Open Positions</div>
              <div className="flex flex-wrap gap-2">
                {(liveAccount?.positions || dbPortfolio?.positions || []).map(pos => (
                  <div
                    key={pos.symbol}
                    className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <span className="font-semibold text-gray-900 dark:text-white">{pos.symbol}</span>
                    <span className="text-xs text-gray-500">{formatCurrency(pos.marketValue)}</span>
                    <span className={cn(
                      "text-xs font-medium px-1.5 py-0.5 rounded",
                      (pos.unrealizedPnl ?? 0) >= 0
                        ? "bg-green-500/10 text-green-500"
                        : "bg-red-500/10 text-red-500"
                    )}>
                      {(pos.unrealizedPnl ?? 0) >= 0 ? '+' : ''}{(pos.unrealizedPnlPct ?? 0).toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
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
                        log.type === 'whale' && 'bg-blue-500/10 text-blue-400',
                        log.type === 'sentiment' && 'bg-pink-500/10 text-pink-400',
                        log.type === 'global' && 'bg-teal-500/10 text-teal-400'
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
                        {log.type === 'decision' && (
                          <>
                            {/* Execution Status Banner */}
                            {log.details.execution_status && log.details.execution_status !== 'skipped' && (
                              <div className={cn(
                                'mb-3 p-2 rounded text-sm font-medium',
                                log.details.execution_status === 'executed' && 'bg-green-500/10 text-green-400 border border-green-500/20',
                                log.details.execution_status === 'failed' && 'bg-red-500/10 text-red-400 border border-red-500/20',
                                log.details.execution_status === 'pending' && 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                              )}>
                                {log.details.execution_status === 'executed' && (
                                  <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                      <CheckCircle className="w-4 h-4" />
                                      <span>Trade Executed Successfully</span>
                                    </div>
                                    <div className="text-xs opacity-80 grid grid-cols-2 gap-2 mt-2">
                                      {log.details.entry_price && <div>Entry: ${parseFloat(log.details.entry_price).toLocaleString()}</div>}
                                      {log.details.entry_quantity && <div>Qty: {parseFloat(log.details.entry_quantity).toFixed(6)}</div>}
                                      {log.details.order_id && <div className="col-span-2">Order ID: {log.details.order_id}</div>}
                                    </div>
                                  </div>
                                )}
                                {log.details.execution_status === 'failed' && (
                                  <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                      <AlertCircle className="w-4 h-4" />
                                      <span>Trade Failed</span>
                                    </div>
                                    <div className="text-xs opacity-80 mt-1">
                                      Error: {log.details.execution_details?.error || 'Unknown error'}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Trade Parameters */}
                            {(log.details.position_size_pct || log.details.leverage || log.details.stop_loss_pct || log.details.take_profit_pct) && (
                              <div className="mb-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                                {log.details.position_size_pct && (
                                  <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                                    <div className="text-gray-500">Position Size</div>
                                    <div className="text-gray-900 dark:text-white font-medium">{log.details.position_size_pct}%</div>
                                  </div>
                                )}
                                {log.details.leverage && (
                                  <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                                    <div className="text-gray-500">Leverage</div>
                                    <div className="text-gray-900 dark:text-white font-medium">{log.details.leverage}x</div>
                                  </div>
                                )}
                                {log.details.stop_loss_pct && (
                                  <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                                    <div className="text-gray-500">Stop Loss</div>
                                    <div className="text-red-400 font-medium">-{log.details.stop_loss_pct}%</div>
                                  </div>
                                )}
                                {log.details.take_profit_pct && (
                                  <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                                    <div className="text-gray-500">Take Profit</div>
                                    <div className="text-green-400 font-medium">+{log.details.take_profit_pct}%</div>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* LLM Reasoning */}
                            {log.details.reasoning && (
                              <div className="mb-3">
                                <div className="text-xs text-gray-500 mb-1">LLM Reasoning:</div>
                                <p className="text-sm text-gray-700 dark:text-gray-300">{log.details.reasoning}</p>
                              </div>
                            )}
                          </>
                        )}
                        {log.type === 'market' && renderMarketDetails(log.details)}
                        {log.type === 'sentiment' && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-4">
                              <div className={cn(
                                "text-4xl font-bold",
                                log.details.score <= 25 ? "text-red-500" :
                                log.details.score <= 45 ? "text-orange-500" :
                                log.details.score <= 55 ? "text-gray-500" :
                                log.details.score <= 75 ? "text-lime-500" : "text-green-500"
                              )}>
                                {log.details.score}
                              </div>
                              <div>
                                <div className={cn(
                                  "text-lg font-semibold",
                                  log.details.score <= 25 ? "text-red-500" :
                                  log.details.score <= 45 ? "text-orange-500" :
                                  log.details.score <= 55 ? "text-gray-500" :
                                  log.details.score <= 75 ? "text-lime-500" : "text-green-500"
                                )}>
                                  {log.details.label}
                                </div>
                                <div className="text-sm text-gray-500">{log.details.interpretation}</div>
                              </div>
                            </div>
                            {/* Sentiment Bar */}
                            <div className="mt-3">
                              <div className="h-3 bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full relative">
                                <div
                                  className="absolute w-4 h-4 bg-white border-2 border-gray-800 rounded-full -top-0.5 transform -translate-x-1/2 shadow"
                                  style={{ left: `${log.details.score}%` }}
                                />
                              </div>
                              <div className="flex justify-between text-xs text-gray-500 mt-1">
                                <span>Extreme Fear</span>
                                <span>Neutral</span>
                                <span>Extreme Greed</span>
                              </div>
                            </div>
                          </div>
                        )}
                        {log.type === 'portfolio' && (
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                            <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                              <div className="text-xs text-gray-500">Total Equity</div>
                              <div className="text-lg font-bold text-gray-900 dark:text-white">
                                {formatCurrency(parseFloat(log.details.equity || 0))}
                              </div>
                            </div>
                            <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                              <div className="text-xs text-gray-500">Available Cash</div>
                              <div className="text-lg font-bold text-gray-900 dark:text-white">
                                {formatCurrency(parseFloat(log.details.available || 0))}
                              </div>
                            </div>
                            <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                              <div className="text-xs text-gray-500">Margin Used</div>
                              <div className="text-lg font-bold text-gray-900 dark:text-white">
                                {formatCurrency(parseFloat(log.details.margin_used || 0))}
                              </div>
                            </div>
                            <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                              <div className="text-xs text-gray-500">Exposure</div>
                              <div className="text-lg font-bold text-gray-900 dark:text-white">
                                {parseFloat(log.details.exposure || 0).toFixed(1)}%
                              </div>
                            </div>
                            {log.details.daily_pnl !== undefined && (
                              <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                                <div className="text-xs text-gray-500">Daily P&L</div>
                                <div className={cn(
                                  "text-lg font-bold",
                                  parseFloat(log.details.daily_pnl || 0) >= 0 ? "text-green-500" : "text-red-500"
                                )}>
                                  {parseFloat(log.details.daily_pnl || 0) >= 0 ? '+' : ''}{formatCurrency(parseFloat(log.details.daily_pnl || 0))}
                                </div>
                              </div>
                            )}
                            <div className="bg-gray-200 dark:bg-gray-800 p-2 rounded">
                              <div className="text-xs text-gray-500">Positions</div>
                              <div className="text-lg font-bold text-gray-900 dark:text-white">
                                {log.details.open_positions_count || 0}
                              </div>
                            </div>
                          </div>
                        )}
                        {log.type === 'news' && (
                          <div className="mb-3 space-y-2">
                            {/* Sentiment and Source row */}
                            <div className="flex items-center gap-3">
                              <span className={cn(
                                "px-2 py-1 rounded text-xs font-medium uppercase",
                                log.details.sentiment === 'positive' && "bg-green-500/20 text-green-400",
                                log.details.sentiment === 'negative' && "bg-red-500/20 text-red-400",
                                log.details.sentiment === 'neutral' && "bg-gray-500/20 text-gray-400"
                              )}>
                                {log.details.sentiment === 'positive' ? '📈 Positive' :
                                 log.details.sentiment === 'negative' ? '📉 Negative' : '📊 Neutral'}
                              </span>
                              {log.details.source && (
                                <span className="text-xs text-gray-500">
                                  Source: <span className="text-gray-400">{log.details.source}</span>
                                </span>
                              )}
                            </div>

                            {/* Summary */}
                            {log.details.summary && (
                              <div>
                                <div className="text-xs text-gray-500 mb-1">Summary:</div>
                                <p className="text-sm text-gray-700 dark:text-gray-300">{log.details.summary}</p>
                              </div>
                            )}

                            {/* Related symbols */}
                            {log.details.symbols && log.details.symbols.length > 0 && (
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-gray-500">Related:</span>
                                <div className="flex gap-1">
                                  {log.details.symbols.map((s: string) => (
                                    <span key={s} className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-800 rounded text-xs font-mono">
                                      {s}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                        {log.type === 'whale' && (
                          <div className="mb-3 space-y-1">
                            <div className="text-xs text-gray-500">Transaction Details:</div>
                            <div className="grid grid-cols-2 gap-2 text-sm">
                              <div className="text-gray-600 dark:text-gray-400">Amount:</div>
                              <div className="text-gray-900 dark:text-white font-mono">${log.details.amount_usd?.toLocaleString()}</div>
                              {log.details.amount && (
                                <>
                                  <div className="text-gray-600 dark:text-gray-400">Crypto Amount:</div>
                                  <div className="text-gray-900 dark:text-white font-mono">{parseFloat(log.details.amount).toLocaleString()}</div>
                                </>
                              )}
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
                              {log.details.blockchain && (
                                <>
                                  <div className="text-gray-600 dark:text-gray-400">Blockchain:</div>
                                  <div className="text-gray-900 dark:text-white">{log.details.blockchain}</div>
                                </>
                              )}
                              {log.details.tx_hash && (
                                <>
                                  <div className="text-gray-600 dark:text-gray-400">TX Hash:</div>
                                  <div className="text-gray-900 dark:text-white font-mono text-xs truncate">{log.details.tx_hash}</div>
                                </>
                              )}
                            </div>
                          </div>
                        )}
                        {log.type === 'global' && (
                          <div className="space-y-4">
                            {/* Market Overview */}
                            <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
                              <div className="flex items-center gap-2 mb-2">
                                <Globe className="w-4 h-4 text-teal-500" />
                                <span className="text-xs font-semibold text-gray-500 uppercase">Global Market Overview</span>
                              </div>
                              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                                <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                                  <div className="text-xs text-gray-500">BTC Dominance</div>
                                  <div className="text-lg font-bold text-orange-500">
                                    {log.details.btc_dominance?.toFixed(1) || 'N/A'}%
                                  </div>
                                </div>
                                <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                                  <div className="text-xs text-gray-500">ETH Dominance</div>
                                  <div className="text-lg font-bold text-blue-500">
                                    {log.details.eth_dominance?.toFixed(1) || 'N/A'}%
                                  </div>
                                </div>
                                <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                                  <div className="text-xs text-gray-500">Total Market Cap</div>
                                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                                    ${log.details.total_market_cap ? (log.details.total_market_cap / 1e12).toFixed(2) : '0'}T
                                  </div>
                                </div>
                                <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                                  <div className="text-xs text-gray-500">24h Change</div>
                                  <div className={cn(
                                    "text-lg font-bold",
                                    (log.details.market_cap_change_24h || 0) >= 0 ? "text-green-500" : "text-red-500"
                                  )}>
                                    {(log.details.market_cap_change_24h || 0) >= 0 ? '+' : ''}{log.details.market_cap_change_24h?.toFixed(2) || '0'}%
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* 24h Volume */}
                            <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
                              <div className="flex items-center gap-2 mb-2">
                                <BarChart3 className="w-4 h-4 text-purple-500" />
                                <span className="text-xs font-semibold text-gray-500 uppercase">Trading Volume</span>
                              </div>
                              <div className="grid grid-cols-2 gap-3 text-sm">
                                <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                                  <div className="text-xs text-gray-500">24h Volume</div>
                                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                                    ${log.details.total_volume_24h ? (log.details.total_volume_24h / 1e9).toFixed(1) : '0'}B
                                  </div>
                                </div>
                                <div className="bg-gray-100 dark:bg-gray-900 p-2 rounded">
                                  <div className="text-xs text-gray-500">Active Cryptos</div>
                                  <div className="text-lg font-bold text-gray-900 dark:text-white">
                                    {log.details.active_cryptocurrencies?.toLocaleString() || 'N/A'}
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Trending Coins */}
                            {log.details.trending_coins && log.details.trending_coins.length > 0 && (
                              <div className="bg-gray-200 dark:bg-gray-800 rounded-lg p-3">
                                <div className="flex items-center gap-2 mb-2">
                                  <TrendingUp className="w-4 h-4 text-green-500" />
                                  <span className="text-xs font-semibold text-gray-500 uppercase">Trending Coins (24h)</span>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {log.details.trending_coins.slice(0, 7).map((coin: any, idx: number) => (
                                    <div
                                      key={coin.id || idx}
                                      className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-900 rounded-lg"
                                    >
                                      <span className="text-xs text-gray-500">#{coin.rank || idx + 1}</span>
                                      <span className="font-semibold text-gray-900 dark:text-white">{coin.symbol || coin.name}</span>
                                      {coin.market_cap_rank && (
                                        <span className="text-xs text-gray-500">MCap #{coin.market_cap_rank}</span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                                {log.details.tracked_trending && log.details.tracked_trending.length > 0 && (
                                  <div className="mt-2 text-xs text-yellow-500">
                                    Your tracked coins trending: {log.details.tracked_trending.join(', ')}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
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
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-pink-500" /> {activities.filter(a => a.type === 'sentiment').length}
          </span>
          <span className="hidden sm:flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-teal-500" /> {activities.filter(a => a.type === 'global').length}
          </span>
        </div>
        <button
          onClick={() => setAutoScroll(!autoScroll)}
          className={cn(
            "flex items-center gap-2 px-2 py-1 rounded transition-colors",
            autoScroll
              ? "text-green-600 dark:text-green-500 hover:bg-green-50 dark:hover:bg-green-500/10"
              : "text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
          )}
          title={autoScroll ? "Click to pause auto-scroll" : "Click to resume auto-scroll"}
        >
          <Clock className={cn("w-3 h-3", !autoScroll && "opacity-50")} />
          <span>{autoScroll ? "Auto-scroll ON" : "Auto-scroll OFF"}</span>
        </button>
      </div>
    </div>
  )
}
