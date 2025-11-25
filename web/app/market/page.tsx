'use client'

import { useEffect, useState } from 'react'
import { supabase, TradingMarketContext } from '@/lib/supabase'
import { formatCurrency, formatPercent, formatTimeAgo, cn } from '@/lib/utils'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  Gauge,
  BarChart3,
  RefreshCw,
  Newspaper,
  Fish,
  ArrowUpRight,
  ArrowDownRight,
  ExternalLink
} from 'lucide-react'

interface SymbolData {
  symbol: string
  context: TradingMarketContext | null
}

export default function MarketPage() {
  const [symbols, setSymbols] = useState<SymbolData[]>([
    { symbol: 'BTC', context: null },
    { symbol: 'ETH', context: null },
    { symbol: 'SOL', context: null }
  ])
  const [selectedSymbol, setSelectedSymbol] = useState('BTC')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMarketData()
    const interval = setInterval(fetchMarketData, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const fetchMarketData = async () => {
    setLoading(true)
    try {
      const updatedSymbols = await Promise.all(
        symbols.map(async (s) => {
          const { data } = await supabase
            .from('trading_market_contexts')
            .select('*')
            .eq('symbol', s.symbol)
            .order('timestamp', { ascending: false })
            .limit(1)
            .single()
          return { ...s, context: data }
        })
      )
      setSymbols(updatedSymbols)
    } catch (error) {
      console.error('Error fetching market data:', error)
    } finally {
      setLoading(false)
    }
  }

  const currentSymbol = symbols.find(s => s.symbol === selectedSymbol)
  const ctx = currentSymbol?.context

  const getRsiColor = (rsi: number) => {
    if (rsi >= 70) return 'text-red-500'
    if (rsi <= 30) return 'text-green-500'
    return 'text-yellow-500'
  }

  const getRsiLabel = (rsi: number) => {
    if (rsi >= 70) return 'Overbought'
    if (rsi <= 30) return 'Oversold'
    return 'Neutral'
  }

  const getSentimentColor = (label: string) => {
    if (label === 'GREED' || label === 'EXTREME GREED') return 'text-green-500'
    if (label === 'FEAR' || label === 'EXTREME FEAR') return 'text-red-500'
    return 'text-yellow-500'
  }

  const getForecastColor = (trend: string) => {
    if (trend === 'bullish') return 'text-green-500'
    if (trend === 'bearish') return 'text-red-500'
    return 'text-gray-500'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Market Analysis</h1>
          <p className="text-gray-400">Real-time technical indicators and market data</p>
        </div>
        <button
          onClick={fetchMarketData}
          className="btn btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Symbol Tabs */}
      <div className="flex gap-2">
        {symbols.map((s) => (
          <button
            key={s.symbol}
            onClick={() => setSelectedSymbol(s.symbol)}
            className={cn(
              'px-6 py-3 rounded-lg font-medium transition-all',
              selectedSymbol === s.symbol
                ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                : 'bg-gray-800/50 text-gray-400 hover:text-white hover:bg-gray-800'
            )}
          >
            <div className="text-lg">{s.symbol}</div>
            {s.context && (
              <div className="text-sm mt-1">
                {formatCurrency(parseFloat(String(s.context.price)))}
              </div>
            )}
          </button>
        ))}
      </div>

      {loading && !ctx ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
        </div>
      ) : !ctx ? (
        <div className="text-center py-12 text-gray-500">
          No market data available. The bot needs to run first.
        </div>
      ) : (
        <>
          {/* Price Card */}
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-gray-400 text-sm">Current Price</div>
                <div className="text-4xl font-bold text-white mt-1">
                  {formatCurrency(parseFloat(String(ctx.price)))}
                </div>
                <div className={cn(
                  'text-lg mt-1',
                  (ctx.price_change_24h || 0) >= 0 ? 'text-green-500' : 'text-red-500'
                )}>
                  {formatPercent(parseFloat(String(ctx.price_change_24h || 0)))} (24h)
                </div>
              </div>
              <div className="text-right">
                <div className="text-gray-400 text-sm">Last Update</div>
                <div className="text-white">{formatTimeAgo(ctx.timestamp)}</div>
              </div>
            </div>
          </div>

          {/* Indicators Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* MACD */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-500" />
                  MACD (12-26-9)
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">MACD Line</span>
                  <span className={cn(
                    'font-medium',
                    (ctx.macd || 0) >= 0 ? 'text-green-500' : 'text-red-500'
                  )}>
                    {parseFloat(String(ctx.macd || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Signal Line</span>
                  <span className="text-white">
                    {parseFloat(String(ctx.macd_signal || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Histogram</span>
                  <span className={cn(
                    'font-medium',
                    (ctx.macd_histogram || 0) >= 0 ? 'text-green-500' : 'text-red-500'
                  )}>
                    {parseFloat(String(ctx.macd_histogram || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="pt-2 border-t border-gray-700">
                  <span className={cn(
                    'text-sm font-medium',
                    (ctx.macd || 0) > (ctx.macd_signal || 0) ? 'text-green-500' : 'text-red-500'
                  )}>
                    {(ctx.macd || 0) > (ctx.macd_signal || 0) ? 'Bullish Crossover' : 'Bearish Crossover'}
                  </span>
                </div>
              </div>
            </div>

            {/* RSI */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <Gauge className="w-5 h-5 text-purple-500" />
                  RSI (14)
                </h3>
              </div>
              <div className="text-center py-4">
                <div className={cn('text-4xl font-bold', getRsiColor(parseFloat(String(ctx.rsi || 50))))}>
                  {parseFloat(String(ctx.rsi || 50)).toFixed(1)}
                </div>
                <div className={cn('text-sm mt-2', getRsiColor(parseFloat(String(ctx.rsi || 50))))}>
                  {getRsiLabel(parseFloat(String(ctx.rsi || 50)))}
                </div>
                <div className="mt-4 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full transition-all',
                      parseFloat(String(ctx.rsi || 50)) >= 70 ? 'bg-red-500' :
                      parseFloat(String(ctx.rsi || 50)) <= 30 ? 'bg-green-500' : 'bg-yellow-500'
                    )}
                    style={{ width: `${ctx.rsi || 50}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Oversold (30)</span>
                  <span>Overbought (70)</span>
                </div>
              </div>
            </div>

            {/* EMA */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-cyan-500" />
                  EMA Trend
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">EMA 2 (Fast)</span>
                  <span className="text-white font-medium">
                    {formatCurrency(parseFloat(String(ctx.ema2 || 0)))}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">EMA 20 (Slow)</span>
                  <span className="text-white font-medium">
                    {formatCurrency(parseFloat(String(ctx.ema20 || 0)))}
                  </span>
                </div>
                <div className="pt-2 border-t border-gray-700">
                  <span className={cn(
                    'text-sm font-medium',
                    (ctx.ema2 || 0) > (ctx.ema20 || 0) ? 'text-green-500' : 'text-red-500'
                  )}>
                    {(ctx.ema2 || 0) > (ctx.ema20 || 0) ? 'Bullish Trend (Price > EMA20)' : 'Bearish Trend (Price < EMA20)'}
                  </span>
                </div>
              </div>
            </div>

            {/* Pivot Points */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <Target className="w-5 h-5 text-orange-500" />
                  Pivot Points
                </h3>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-red-500">
                  <span>R2</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_r2 || 0)))}</span>
                </div>
                <div className="flex justify-between text-red-400">
                  <span>R1</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_r1 || 0)))}</span>
                </div>
                <div className="flex justify-between text-white bg-gray-700/50 px-2 py-1 rounded">
                  <span className="font-medium">PP</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_pp || 0)))}</span>
                </div>
                <div className="flex justify-between text-green-400">
                  <span>S1</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_s1 || 0)))}</span>
                </div>
                <div className="flex justify-between text-green-500">
                  <span>S2</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_s2 || 0)))}</span>
                </div>
              </div>
            </div>

            {/* Order Book */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-indigo-500" />
                  Order Book
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-green-500">Bid Volume</span>
                  <span className="text-white font-medium">
                    {parseFloat(String(ctx.orderbook_bid_volume || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-red-500">Ask Volume</span>
                  <span className="text-white font-medium">
                    {parseFloat(String(ctx.orderbook_ask_volume || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="pt-2 border-t border-gray-700">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Bid/Ask Ratio</span>
                    <span className={cn(
                      'font-medium',
                      (ctx.orderbook_ratio || 1) > 1 ? 'text-green-500' : 'text-red-500'
                    )}>
                      {parseFloat(String(ctx.orderbook_ratio || 1)).toFixed(2)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {(ctx.orderbook_ratio || 1) > 1 ? 'Buying Pressure' : 'Selling Pressure'}
                  </div>
                </div>
              </div>
            </div>

            {/* Sentiment & Forecast */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <Activity className="w-5 h-5 text-pink-500" />
                  Sentiment & Forecast
                </h3>
              </div>
              <div className="space-y-4">
                <div>
                  <div className="text-gray-400 text-sm">Fear & Greed Index</div>
                  <div className={cn('text-2xl font-bold', getSentimentColor(ctx.sentiment_label || 'NEUTRAL'))}>
                    {ctx.sentiment_score || 50}
                  </div>
                  <div className={cn('text-sm', getSentimentColor(ctx.sentiment_label || 'NEUTRAL'))}>
                    {ctx.sentiment_label || 'NEUTRAL'}
                  </div>
                </div>
                <div className="pt-3 border-t border-gray-700">
                  <div className="text-gray-400 text-sm">Prophet Forecast (4h)</div>
                  <div className={cn('text-lg font-medium mt-1', getForecastColor(ctx.forecast_trend || 'lateral'))}>
                    {ctx.forecast_trend?.toUpperCase() || 'LATERAL'}
                  </div>
                  {ctx.forecast_target_price && (
                    <div className="text-sm text-gray-400">
                      Target: {formatCurrency(parseFloat(String(ctx.forecast_target_price)))}
                      <span className={cn('ml-2', getForecastColor(ctx.forecast_trend || 'lateral'))}>
                        ({formatPercent(parseFloat(String(ctx.forecast_change_pct || 0)))})
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* News & Whale Alerts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent News */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <Newspaper className="w-5 h-5 text-blue-500" />
                  Recent Crypto News
                </h3>
              </div>
              <div className="space-y-3">
                {ctx.raw_data?.news && ctx.raw_data.news.length > 0 ? (
                  ctx.raw_data.news.slice(0, 5).map((news: any, idx: number) => (
                    <div key={idx} className="flex items-start gap-3 p-3 bg-gray-800/50 rounded-lg">
                      <div className={cn(
                        'w-2 h-2 mt-2 rounded-full flex-shrink-0',
                        news.sentiment === 'positive' ? 'bg-green-500' :
                        news.sentiment === 'negative' ? 'bg-red-500' : 'bg-gray-500'
                      )} />
                      <div className="flex-1 min-w-0">
                        <div className="text-white text-sm font-medium line-clamp-2">
                          {news.title}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={cn(
                            'text-xs px-2 py-0.5 rounded',
                            news.sentiment === 'positive' ? 'bg-green-500/20 text-green-400' :
                            news.sentiment === 'negative' ? 'bg-red-500/20 text-red-400' :
                            'bg-gray-500/20 text-gray-400'
                          )}>
                            {news.sentiment || 'neutral'}
                          </span>
                          {news.url && (
                            <a
                              href={news.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                            >
                              Read <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-6 text-gray-500">
                    <Newspaper className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>No recent news available</p>
                    <p className="text-xs mt-1">News will appear after bot runs</p>
                  </div>
                )}
              </div>
            </div>

            {/* Whale Alerts */}
            <div className="card">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <Fish className="w-5 h-5 text-cyan-500" />
                  Whale Flow Analysis
                </h3>
              </div>
              {ctx.raw_data?.whale_flow ? (
                <div className="space-y-4">
                  {/* Flow Summary */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                      <div className="flex items-center gap-2 text-red-400 text-sm">
                        <ArrowDownRight className="w-4 h-4" />
                        Inflow to Exchange
                      </div>
                      <div className="text-xl font-bold text-red-500 mt-1">
                        ${(ctx.raw_data.whale_flow.inflow_exchange || 0).toLocaleString()}
                      </div>
                      <div className="text-xs text-red-400/70">Potential sell pressure</div>
                    </div>
                    <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
                      <div className="flex items-center gap-2 text-green-400 text-sm">
                        <ArrowUpRight className="w-4 h-4" />
                        Outflow from Exchange
                      </div>
                      <div className="text-xl font-bold text-green-500 mt-1">
                        ${(ctx.raw_data.whale_flow.outflow_exchange || 0).toLocaleString()}
                      </div>
                      <div className="text-xs text-green-400/70">Potential accumulation</div>
                    </div>
                  </div>

                  {/* Net Flow */}
                  <div className={cn(
                    'p-4 rounded-lg border',
                    (ctx.raw_data.whale_flow.net_flow || 0) > 0
                      ? 'bg-green-500/10 border-green-500/20'
                      : (ctx.raw_data.whale_flow.net_flow || 0) < 0
                        ? 'bg-red-500/10 border-red-500/20'
                        : 'bg-gray-500/10 border-gray-500/20'
                  )}>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-gray-400 text-sm">Net Flow</div>
                        <div className={cn(
                          'text-2xl font-bold',
                          (ctx.raw_data.whale_flow.net_flow || 0) > 0 ? 'text-green-500' :
                          (ctx.raw_data.whale_flow.net_flow || 0) < 0 ? 'text-red-500' : 'text-gray-500'
                        )}>
                          {(ctx.raw_data.whale_flow.net_flow || 0) > 0 ? '+' : ''}
                          ${(ctx.raw_data.whale_flow.net_flow || 0).toLocaleString()}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-gray-400 text-sm">Interpretation</div>
                        <div className={cn(
                          'text-sm font-medium',
                          (ctx.raw_data.whale_flow.net_flow || 0) > 0 ? 'text-green-400' :
                          (ctx.raw_data.whale_flow.net_flow || 0) < 0 ? 'text-red-400' : 'text-gray-400'
                        )}>
                          {ctx.raw_data.whale_flow.interpretation || 'N/A'}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="text-xs text-gray-500 text-center">
                    Tracking {ctx.raw_data.whale_flow.alert_count || 0} transactions &gt; $1M
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 text-gray-500">
                  <Fish className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No whale data available</p>
                  <p className="text-xs mt-1">Whale alerts will appear after bot runs</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
