'use client'

import { useEffect, useState, useCallback } from 'react'
import { supabase, TradingMarketContext, TradingAIAnalysis } from '@/lib/supabase'
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
  ExternalLink,
  Brain,
  Zap,
  AlertTriangle,
  Shield,
  ChevronUp,
  ChevronDown,
  Sparkles,
  Clock,
  BarChart2,
  Waves
} from 'lucide-react'

interface SymbolData {
  symbol: string
  context: TradingMarketContext | null
  analysis: TradingAIAnalysis | null
}

export default function MarketPage() {
  const [symbols, setSymbols] = useState<SymbolData[]>([
    { symbol: 'BTC', context: null, analysis: null },
    { symbol: 'ETH', context: null, analysis: null },
    { symbol: 'SOL', context: null, analysis: null }
  ])
  const [selectedSymbol, setSelectedSymbol] = useState('BTC')
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const fetchMarketData = useCallback(async () => {
    setLoading(true)
    try {
      const updatedSymbols = await Promise.all(
        symbols.map(async (s) => {
          // Fetch market context
          const { data: contextData } = await supabase
            .from('trading_market_contexts')
            .select('*')
            .eq('symbol', s.symbol)
            .order('timestamp', { ascending: false })
            .limit(1)
            .single()

          // Fetch AI analysis
          const { data: analysisData } = await supabase
            .from('trading_ai_analysis')
            .select('*')
            .eq('symbol', s.symbol)
            .order('analysis_date', { ascending: false })
            .limit(1)
            .single()

          return {
            ...s,
            context: contextData,
            analysis: analysisData
          }
        })
      )
      setSymbols(updatedSymbols)
      setLastUpdate(new Date())
    } catch (error) {
      console.error('Error fetching market data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMarketData()
    const interval = setInterval(fetchMarketData, 60000)
    return () => clearInterval(interval)
  }, [fetchMarketData])

  const currentSymbol = symbols.find(s => s.symbol === selectedSymbol)
  const ctx = currentSymbol?.context
  const analysis = currentSymbol?.analysis

  const getRsiColor = (rsi: number) => {
    if (rsi >= 70) return 'text-red-400'
    if (rsi <= 30) return 'text-green-400'
    return 'text-yellow-400'
  }

  const getRsiLabel = (rsi: number) => {
    if (rsi >= 70) return 'Overbought'
    if (rsi <= 30) return 'Oversold'
    return 'Neutral'
  }

  const getSentimentColor = (label: string) => {
    if (label === 'GREED' || label === 'EXTREME GREED') return 'text-green-400'
    if (label === 'FEAR' || label === 'EXTREME FEAR') return 'text-red-400'
    return 'text-yellow-400'
  }

  const getOutlookIcon = (outlook: string) => {
    switch (outlook) {
      case 'bullish': return <TrendingUp className="w-5 h-5 text-green-400" />
      case 'bearish': return <TrendingDown className="w-5 h-5 text-red-400" />
      case 'volatile': return <Zap className="w-5 h-5 text-yellow-400" />
      default: return <Activity className="w-5 h-5 text-gray-400" />
    }
  }

  const getOutlookColor = (outlook: string) => {
    switch (outlook) {
      case 'bullish': return 'from-green-500/20 to-green-500/5 border-green-500/30'
      case 'bearish': return 'from-red-500/20 to-red-500/5 border-red-500/30'
      case 'volatile': return 'from-yellow-500/20 to-yellow-500/5 border-yellow-500/30'
      default: return 'from-gray-500/20 to-gray-500/5 border-gray-500/30'
    }
  }

  const getMomentumIcon = (momentum: string) => {
    if (momentum === 'increasing') return <ChevronUp className="w-4 h-4 text-green-400" />
    if (momentum === 'decreasing') return <ChevronDown className="w-4 h-4 text-red-400" />
    return <Activity className="w-4 h-4 text-gray-400" />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart2 className="w-7 h-7 text-green-500" />
            Market Analysis
          </h1>
          <p className="text-gray-400 mt-1">Real-time technical indicators and AI-powered insights</p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdate && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Clock className="w-4 h-4" />
              <span>Updated {formatTimeAgo(lastUpdate.toISOString())}</span>
            </div>
          )}
          <button
            onClick={fetchMarketData}
            className="btn btn-secondary flex items-center gap-2 group"
          >
            <RefreshCw className={cn(
              "w-4 h-4 transition-transform",
              loading && "animate-spin",
              "group-hover:rotate-180"
            )} />
            Refresh
          </button>
        </div>
      </div>

      {/* Symbol Tabs */}
      <div className="flex gap-3">
        {symbols.map((s) => {
          const isSelected = selectedSymbol === s.symbol
          const priceChange = s.context?.price_change_24h || 0

          return (
            <button
              key={s.symbol}
              onClick={() => setSelectedSymbol(s.symbol)}
              className={cn(
                'relative px-6 py-4 rounded-xl font-medium transition-all duration-300 flex-1 max-w-[200px]',
                'border overflow-hidden group',
                isSelected
                  ? 'bg-gradient-to-br from-green-500/20 to-green-500/5 text-white border-green-500/40 shadow-lg shadow-green-500/10'
                  : 'bg-gray-800/50 text-gray-400 hover:text-white hover:bg-gray-800 border-gray-700/50 hover:border-gray-600'
              )}
            >
              {/* Animated background */}
              <div className={cn(
                "absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent",
                "translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000"
              )} />

              <div className="relative">
                <div className="text-xl font-bold">{s.symbol}</div>
                {s.context && (
                  <>
                    <div className="text-base mt-1">
                      {formatCurrency(parseFloat(String(s.context.price)))}
                    </div>
                    <div className={cn(
                      'text-xs mt-1 flex items-center justify-center gap-1',
                      priceChange >= 0 ? 'text-green-400' : 'text-red-400'
                    )}>
                      {priceChange >= 0 ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      {formatPercent(priceChange)}
                    </div>
                  </>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {loading && !ctx ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-green-500/20 rounded-full" />
            <div className="absolute top-0 left-0 w-16 h-16 border-4 border-green-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="text-gray-400 mt-4">Loading market data...</p>
        </div>
      ) : !ctx ? (
        <div className="text-center py-16 bg-gray-800/30 rounded-2xl border border-gray-700/50">
          <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-600" />
          <p className="text-gray-400 text-lg">No market data available</p>
          <p className="text-gray-500 text-sm mt-2">The bot needs to run first to collect market data</p>
        </div>
      ) : (
        <>
          {/* AI Analysis Card - Featured */}
          {analysis && (
            <div className={cn(
              "card border-2 bg-gradient-to-br transition-all duration-500",
              getOutlookColor(analysis.market_outlook)
            )}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/30">
                    <Brain className="w-6 h-6 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      AI Market Analysis
                      <Sparkles className="w-4 h-4 text-yellow-400 animate-pulse" />
                    </h3>
                    <p className="text-sm text-gray-400">
                      Generated by DeepSeek AI - {new Date(analysis.analysis_date).toLocaleDateString('it-IT', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getOutlookIcon(analysis.market_outlook)}
                  <span className={cn(
                    "px-3 py-1 rounded-full text-sm font-medium",
                    analysis.market_outlook === 'bullish' && "bg-green-500/20 text-green-400",
                    analysis.market_outlook === 'bearish' && "bg-red-500/20 text-red-400",
                    analysis.market_outlook === 'volatile' && "bg-yellow-500/20 text-yellow-400",
                    analysis.market_outlook === 'neutral' && "bg-gray-500/20 text-gray-400"
                  )}>
                    {analysis.market_outlook.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Analysis Summary */}
              <div className="mt-4 p-4 bg-gray-900/50 rounded-xl border border-gray-700/50">
                <p className="text-gray-200 leading-relaxed">{analysis.summary_text}</p>
              </div>

              {/* Analysis Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                <div className="p-3 bg-gray-900/30 rounded-lg border border-gray-700/30">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">Confidence</div>
                  <div className="text-lg font-bold text-white mt-1">
                    {((analysis.confidence_score || 0) * 100).toFixed(0)}%
                  </div>
                  <div className="mt-2 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full transition-all duration-500"
                      style={{ width: `${(analysis.confidence_score || 0) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="p-3 bg-gray-900/30 rounded-lg border border-gray-700/30">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">Trend Strength</div>
                  <div className="text-lg font-bold text-white mt-1 capitalize flex items-center gap-2">
                    {analysis.trend_strength || 'N/A'}
                    <Waves className={cn(
                      "w-4 h-4",
                      analysis.trend_strength === 'strong' && "text-green-400",
                      analysis.trend_strength === 'moderate' && "text-yellow-400",
                      analysis.trend_strength === 'weak' && "text-red-400"
                    )} />
                  </div>
                </div>
                <div className="p-3 bg-gray-900/30 rounded-lg border border-gray-700/30">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">Momentum</div>
                  <div className="text-lg font-bold text-white mt-1 capitalize flex items-center gap-2">
                    {analysis.momentum || 'N/A'}
                    {getMomentumIcon(analysis.momentum || '')}
                  </div>
                </div>
                <div className="p-3 bg-gray-900/30 rounded-lg border border-gray-700/30">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">Volatility</div>
                  <div className="text-lg font-bold text-white mt-1 capitalize flex items-center gap-2">
                    {analysis.volatility_level || 'N/A'}
                    <Zap className={cn(
                      "w-4 h-4",
                      analysis.volatility_level === 'high' && "text-red-400",
                      analysis.volatility_level === 'medium' && "text-yellow-400",
                      analysis.volatility_level === 'low' && "text-green-400"
                    )} />
                  </div>
                </div>
              </div>

              {/* Key Levels & Insights */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                {/* Key Levels */}
                {analysis.key_levels && (
                  <div className="p-4 bg-gray-900/30 rounded-xl border border-gray-700/30">
                    <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                      <Target className="w-4 h-4" /> Key Levels
                    </h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-red-400">R2</span>
                        <span className="text-white font-medium">
                          {formatCurrency(analysis.key_levels.resistance_2 || 0)}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-red-300">R1</span>
                        <span className="text-white font-medium">
                          {formatCurrency(analysis.key_levels.resistance_1 || 0)}
                        </span>
                      </div>
                      <div className="h-px bg-gradient-to-r from-transparent via-gray-600 to-transparent my-2" />
                      <div className="flex justify-between text-sm">
                        <span className="text-green-300">S1</span>
                        <span className="text-white font-medium">
                          {formatCurrency(analysis.key_levels.support_1 || 0)}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-green-400">S2</span>
                        <span className="text-white font-medium">
                          {formatCurrency(analysis.key_levels.support_2 || 0)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Risk Factors */}
                {analysis.risk_factors && analysis.risk_factors.length > 0 && (
                  <div className="p-4 bg-gray-900/30 rounded-xl border border-gray-700/30">
                    <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-400" /> Risk Factors
                    </h4>
                    <ul className="space-y-2">
                      {analysis.risk_factors.map((risk, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 flex-shrink-0" />
                          <span className="text-gray-300">{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Opportunities */}
                {analysis.opportunities && analysis.opportunities.length > 0 && (
                  <div className="p-4 bg-gray-900/30 rounded-xl border border-gray-700/30">
                    <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                      <Shield className="w-4 h-4 text-green-400" /> Opportunities
                    </h4>
                    <ul className="space-y-2">
                      {analysis.opportunities.map((opp, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-400 mt-1.5 flex-shrink-0" />
                          <span className="text-gray-300">{opp}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Price Card with Animation */}
          <div className="card bg-gradient-to-br from-gray-800/80 to-gray-900/80 border-gray-700/50">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-gray-400 text-sm flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  Live Price
                </div>
                <div className="text-5xl font-bold text-white mt-2 tracking-tight">
                  {formatCurrency(parseFloat(String(ctx.price)))}
                </div>
                <div className={cn(
                  'text-xl mt-2 flex items-center gap-2',
                  (ctx.price_change_24h || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                )}>
                  {(ctx.price_change_24h || 0) >= 0 ? (
                    <ArrowUpRight className="w-5 h-5" />
                  ) : (
                    <ArrowDownRight className="w-5 h-5" />
                  )}
                  {formatPercent(parseFloat(String(ctx.price_change_24h || 0)))}
                  <span className="text-gray-500 text-sm ml-1">(24h)</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-gray-400 text-sm">Last Update</div>
                <div className="text-white font-medium">{formatTimeAgo(ctx.timestamp)}</div>
                <div className="text-gray-500 text-xs mt-1">
                  Auto-refresh every 60s
                </div>
              </div>
            </div>
          </div>

          {/* Indicators Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* MACD */}
            <div className="card group hover:border-blue-500/30 transition-all duration-300">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-blue-500/10 group-hover:bg-blue-500/20 transition-colors">
                    <Activity className="w-5 h-5 text-blue-400" />
                  </div>
                  MACD (12-26-9)
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">MACD Line</span>
                  <span className={cn(
                    'font-medium text-lg',
                    (ctx.macd || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {parseFloat(String(ctx.macd || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Signal Line</span>
                  <span className="text-white font-medium">
                    {parseFloat(String(ctx.macd_signal || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Histogram</span>
                  <span className={cn(
                    'font-medium',
                    (ctx.macd_histogram || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {parseFloat(String(ctx.macd_histogram || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="pt-3 border-t border-gray-700/50">
                  <div className={cn(
                    'flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-lg',
                    (ctx.macd || 0) > (ctx.macd_signal || 0)
                      ? 'bg-green-500/10 text-green-400'
                      : 'bg-red-500/10 text-red-400'
                  )}>
                    {(ctx.macd || 0) > (ctx.macd_signal || 0) ? (
                      <TrendingUp className="w-4 h-4" />
                    ) : (
                      <TrendingDown className="w-4 h-4" />
                    )}
                    {(ctx.macd || 0) > (ctx.macd_signal || 0) ? 'Bullish Crossover' : 'Bearish Crossover'}
                  </div>
                </div>
              </div>
            </div>

            {/* RSI */}
            <div className="card group hover:border-purple-500/30 transition-all duration-300">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-purple-500/10 group-hover:bg-purple-500/20 transition-colors">
                    <Gauge className="w-5 h-5 text-purple-400" />
                  </div>
                  RSI (14)
                </h3>
              </div>
              <div className="text-center py-4">
                <div className={cn('text-5xl font-bold', getRsiColor(parseFloat(String(ctx.rsi || 50))))}>
                  {parseFloat(String(ctx.rsi || 50)).toFixed(1)}
                </div>
                <div className={cn(
                  'text-sm mt-2 px-3 py-1 rounded-full inline-block',
                  parseFloat(String(ctx.rsi || 50)) >= 70 ? 'bg-red-500/20 text-red-400' :
                  parseFloat(String(ctx.rsi || 50)) <= 30 ? 'bg-green-500/20 text-green-400' :
                  'bg-yellow-500/20 text-yellow-400'
                )}>
                  {getRsiLabel(parseFloat(String(ctx.rsi || 50)))}
                </div>
                <div className="mt-4 h-3 bg-gray-700 rounded-full overflow-hidden relative">
                  {/* Zones */}
                  <div className="absolute inset-0 flex">
                    <div className="w-[30%] bg-green-500/20" />
                    <div className="w-[40%] bg-yellow-500/20" />
                    <div className="w-[30%] bg-red-500/20" />
                  </div>
                  {/* Indicator */}
                  <div
                    className="absolute top-0 h-full w-1 bg-white rounded-full shadow-lg shadow-white/50 transition-all duration-500"
                    style={{ left: `calc(${ctx.rsi || 50}% - 2px)` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>Oversold (30)</span>
                  <span>Overbought (70)</span>
                </div>
              </div>
            </div>

            {/* EMA */}
            <div className="card group hover:border-cyan-500/30 transition-all duration-300">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-cyan-500/10 group-hover:bg-cyan-500/20 transition-colors">
                    <TrendingUp className="w-5 h-5 text-cyan-400" />
                  </div>
                  EMA Trend
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">EMA 2 (Fast)</span>
                  <span className="text-white font-medium text-lg">
                    {formatCurrency(parseFloat(String(ctx.ema2 || 0)))}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">EMA 20 (Slow)</span>
                  <span className="text-white font-medium">
                    {formatCurrency(parseFloat(String(ctx.ema20 || 0)))}
                  </span>
                </div>
                <div className="pt-3 border-t border-gray-700/50">
                  <div className={cn(
                    'flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-lg',
                    (ctx.ema2 || 0) > (ctx.ema20 || 0)
                      ? 'bg-green-500/10 text-green-400'
                      : 'bg-red-500/10 text-red-400'
                  )}>
                    {(ctx.ema2 || 0) > (ctx.ema20 || 0) ? (
                      <TrendingUp className="w-4 h-4" />
                    ) : (
                      <TrendingDown className="w-4 h-4" />
                    )}
                    {(ctx.ema2 || 0) > (ctx.ema20 || 0) ? 'Bullish Trend' : 'Bearish Trend'}
                  </div>
                </div>
              </div>
            </div>

            {/* Pivot Points */}
            <div className="card group hover:border-orange-500/30 transition-all duration-300">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-orange-500/10 group-hover:bg-orange-500/20 transition-colors">
                    <Target className="w-5 h-5 text-orange-400" />
                  </div>
                  Pivot Points
                </h3>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-red-400 p-2 bg-red-500/5 rounded-lg">
                  <span className="font-medium">R2</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_r2 || 0)))}</span>
                </div>
                <div className="flex justify-between text-red-300 p-2">
                  <span>R1</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_r1 || 0)))}</span>
                </div>
                <div className="flex justify-between text-white bg-gray-700/50 px-3 py-2 rounded-lg font-bold">
                  <span>PP</span>
                  <span>{formatCurrency(parseFloat(String(ctx.pivot_pp || 0)))}</span>
                </div>
                <div className="flex justify-between text-green-300 p-2">
                  <span>S1</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_s1 || 0)))}</span>
                </div>
                <div className="flex justify-between text-green-400 p-2 bg-green-500/5 rounded-lg">
                  <span className="font-medium">S2</span>
                  <span className="font-medium">{formatCurrency(parseFloat(String(ctx.pivot_s2 || 0)))}</span>
                </div>
              </div>
            </div>

            {/* Order Book */}
            <div className="card group hover:border-indigo-500/30 transition-all duration-300">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-indigo-500/10 group-hover:bg-indigo-500/20 transition-colors">
                    <BarChart3 className="w-5 h-5 text-indigo-400" />
                  </div>
                  Order Book
                </h3>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-green-400 flex items-center gap-2">
                    <ArrowUpRight className="w-4 h-4" /> Bid Volume
                  </span>
                  <span className="text-white font-medium">
                    {parseFloat(String(ctx.orderbook_bid_volume || 0)).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-red-400 flex items-center gap-2">
                    <ArrowDownRight className="w-4 h-4" /> Ask Volume
                  </span>
                  <span className="text-white font-medium">
                    {parseFloat(String(ctx.orderbook_ask_volume || 0)).toFixed(2)}
                  </span>
                </div>
                {/* Volume Bar */}
                <div className="h-3 bg-gray-700 rounded-full overflow-hidden flex">
                  <div
                    className="bg-gradient-to-r from-green-500 to-green-400 transition-all duration-500"
                    style={{
                      width: `${Math.min(100, ((ctx.orderbook_ratio || 1) / 2) * 100)}%`
                    }}
                  />
                </div>
                <div className="pt-3 border-t border-gray-700/50">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Bid/Ask Ratio</span>
                    <span className={cn(
                      'font-bold text-lg',
                      (ctx.orderbook_ratio || 1) > 1 ? 'text-green-400' : 'text-red-400'
                    )}>
                      {parseFloat(String(ctx.orderbook_ratio || 1)).toFixed(2)}
                    </span>
                  </div>
                  <div className={cn(
                    'text-xs mt-2 px-3 py-1 rounded-full inline-block',
                    (ctx.orderbook_ratio || 1) > 1
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'
                  )}>
                    {(ctx.orderbook_ratio || 1) > 1 ? 'Buying Pressure' : 'Selling Pressure'}
                  </div>
                </div>
              </div>
            </div>

            {/* Sentiment & Forecast */}
            <div className="card group hover:border-pink-500/30 transition-all duration-300">
              <div className="card-header">
                <h3 className="card-title flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-pink-500/10 group-hover:bg-pink-500/20 transition-colors">
                    <Activity className="w-5 h-5 text-pink-400" />
                  </div>
                  Sentiment & Forecast
                </h3>
              </div>
              <div className="space-y-4">
                <div>
                  <div className="text-gray-400 text-sm">Fear & Greed Index</div>
                  <div className={cn('text-3xl font-bold mt-1', getSentimentColor(ctx.sentiment_label || 'NEUTRAL'))}>
                    {ctx.sentiment_score || 50}
                  </div>
                  <div className={cn(
                    'text-sm px-3 py-1 rounded-full inline-block mt-1',
                    ctx.sentiment_label?.includes('GREED') ? 'bg-green-500/20 text-green-400' :
                    ctx.sentiment_label?.includes('FEAR') ? 'bg-red-500/20 text-red-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  )}>
                    {ctx.sentiment_label || 'NEUTRAL'}
                  </div>
                </div>
                <div className="pt-3 border-t border-gray-700/50">
                  <div className="text-gray-400 text-sm">Prophet Forecast (4h)</div>
                  <div className={cn(
                    'text-lg font-bold mt-1 flex items-center gap-2',
                    ctx.forecast_trend === 'bullish' ? 'text-green-400' :
                    ctx.forecast_trend === 'bearish' ? 'text-red-400' : 'text-gray-400'
                  )}>
                    {ctx.forecast_trend === 'bullish' && <TrendingUp className="w-5 h-5" />}
                    {ctx.forecast_trend === 'bearish' && <TrendingDown className="w-5 h-5" />}
                    {ctx.forecast_trend?.toUpperCase() || 'LATERAL'}
                  </div>
                  {ctx.forecast_target_price && (
                    <div className="text-sm text-gray-400 mt-1">
                      Target: <span className="text-white font-medium">
                        {formatCurrency(parseFloat(String(ctx.forecast_target_price)))}
                      </span>
                      <span className={cn(
                        'ml-2',
                        (ctx.forecast_change_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                      )}>
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
              <div className="card-header flex items-center justify-between">
                <h3 className="card-title flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-blue-500/10">
                    <Newspaper className="w-5 h-5 text-blue-400" />
                  </div>
                  Recent Crypto News
                </h3>
                {ctx.raw_data?.news && (
                  <span className="text-xs text-gray-500 px-2 py-1 bg-gray-800 rounded-full">
                    {ctx.raw_data.news.length} articles
                  </span>
                )}
              </div>
              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                {ctx.raw_data?.news && ctx.raw_data.news.length > 0 ? (
                  ctx.raw_data.news.slice(0, 8).map((news: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 p-3 bg-gray-800/50 rounded-xl border border-gray-700/30 hover:border-gray-600/50 transition-all group"
                    >
                      <div className={cn(
                        'w-2 h-2 mt-2 rounded-full flex-shrink-0 animate-pulse',
                        news.sentiment === 'positive' ? 'bg-green-500' :
                        news.sentiment === 'negative' ? 'bg-red-500' : 'bg-gray-500'
                      )} />
                      <div className="flex-1 min-w-0">
                        <div className="text-white text-sm font-medium line-clamp-2 group-hover:text-blue-400 transition-colors">
                          {news.title}
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <span className={cn(
                            'text-xs px-2 py-0.5 rounded-full font-medium',
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
                              className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors"
                            >
                              Read <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Newspaper className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p className="font-medium">No recent news available</p>
                    <p className="text-xs mt-1 text-gray-600">News will appear after bot runs</p>
                  </div>
                )}
              </div>
            </div>

            {/* Whale Alerts */}
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h3 className="card-title flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-cyan-500/10">
                    <Fish className="w-5 h-5 text-cyan-400" />
                  </div>
                  Whale Flow Analysis
                </h3>
                {ctx.raw_data?.whale_flow?.alert_count && (
                  <span className="text-xs text-gray-500 px-2 py-1 bg-gray-800 rounded-full">
                    {ctx.raw_data.whale_flow.alert_count} txns
                  </span>
                )}
              </div>
              {ctx.raw_data?.whale_flow ? (
                <div className="space-y-4">
                  {/* Flow Summary */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gradient-to-br from-red-500/10 to-red-500/5 border border-red-500/20 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-red-400 text-sm">
                        <ArrowDownRight className="w-4 h-4" />
                        Inflow to Exchange
                      </div>
                      <div className="text-2xl font-bold text-red-400 mt-2">
                        ${(ctx.raw_data.whale_flow.inflow_exchange || 0).toLocaleString()}
                      </div>
                      <div className="text-xs text-red-400/60 mt-1">Potential sell pressure</div>
                    </div>
                    <div className="bg-gradient-to-br from-green-500/10 to-green-500/5 border border-green-500/20 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-green-400 text-sm">
                        <ArrowUpRight className="w-4 h-4" />
                        Outflow from Exchange
                      </div>
                      <div className="text-2xl font-bold text-green-400 mt-2">
                        ${(ctx.raw_data.whale_flow.outflow_exchange || 0).toLocaleString()}
                      </div>
                      <div className="text-xs text-green-400/60 mt-1">Potential accumulation</div>
                    </div>
                  </div>

                  {/* Net Flow */}
                  <div className={cn(
                    'p-4 rounded-xl border',
                    (ctx.raw_data.whale_flow.net_flow || 0) > 0
                      ? 'bg-gradient-to-r from-green-500/10 to-green-500/5 border-green-500/30'
                      : (ctx.raw_data.whale_flow.net_flow || 0) < 0
                        ? 'bg-gradient-to-r from-red-500/10 to-red-500/5 border-red-500/30'
                        : 'bg-gradient-to-r from-gray-500/10 to-gray-500/5 border-gray-500/30'
                  )}>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-gray-400 text-sm">Net Flow</div>
                        <div className={cn(
                          'text-3xl font-bold',
                          (ctx.raw_data.whale_flow.net_flow || 0) > 0 ? 'text-green-400' :
                          (ctx.raw_data.whale_flow.net_flow || 0) < 0 ? 'text-red-400' : 'text-gray-400'
                        )}>
                          {(ctx.raw_data.whale_flow.net_flow || 0) > 0 ? '+' : ''}
                          ${(ctx.raw_data.whale_flow.net_flow || 0).toLocaleString()}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-gray-400 text-sm">Interpretation</div>
                        <div className={cn(
                          'text-sm font-medium mt-1 px-3 py-1 rounded-full',
                          (ctx.raw_data.whale_flow.net_flow || 0) > 0
                            ? 'bg-green-500/20 text-green-400'
                            : (ctx.raw_data.whale_flow.net_flow || 0) < 0
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-gray-500/20 text-gray-400'
                        )}>
                          {ctx.raw_data.whale_flow.interpretation || 'N/A'}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="text-xs text-gray-500 text-center py-2 bg-gray-800/30 rounded-lg">
                    Tracking transactions &gt; $1M in the last 24 hours
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Fish className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  <p className="font-medium">No whale data available</p>
                  <p className="text-xs mt-1 text-gray-600">Whale alerts will appear after bot runs</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
