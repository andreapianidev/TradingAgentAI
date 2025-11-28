'use client'

import { useEffect, useState } from 'react'
import {
  X,
  TrendingUp,
  TrendingDown,
  Activity,
  Brain,
  BarChart3,
  Clock,
  Target,
  Shield,
  Zap,
  AlertCircle,
  CheckCircle,
  XCircle,
  Loader2
} from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { TradingDecision, TradingMarketContext } from '@/lib/supabase'

interface DecisionDetailsModalProps {
  decisionId: string
  isOpen: boolean
  onClose: () => void
}

export default function DecisionDetailsModal({
  decisionId,
  isOpen,
  onClose
}: DecisionDetailsModalProps) {
  const [decision, setDecision] = useState<TradingDecision | null>(null)
  const [context, setContext] = useState<TradingMarketContext | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isOpen && decisionId) {
      fetchDecisionDetails()
    }
  }, [isOpen, decisionId])

  const fetchDecisionDetails = async () => {
    setLoading(true)
    try {
      // Fetch decision
      const { data: decisionData } = await supabase
        .from('trading_decisions')
        .select('*')
        .eq('id', decisionId)
        .single()

      if (decisionData) {
        setDecision(decisionData)

        // Fetch associated market context if available
        if (decisionData.context_id) {
          const { data: contextData } = await supabase
            .from('trading_market_contexts')
            .select('*')
            .eq('id', decisionData.context_id)
            .single()

          setContext(contextData)
        }
      }
    } catch (error) {
      console.error('Error fetching decision details:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  const getActionBadge = (action: string, direction?: string) => {
    if (action === 'hold') {
      return (
        <span className="px-3 py-1 rounded-full text-sm font-medium bg-gray-500/20 text-gray-400">
          HOLD
        </span>
      )
    }
    if (action === 'close') {
      return (
        <span className="px-3 py-1 rounded-full text-sm font-medium bg-orange-500/20 text-orange-400">
          CLOSE
        </span>
      )
    }
    if (action === 'open' && direction === 'long') {
      return (
        <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-500/20 text-green-400">
          OPEN LONG
        </span>
      )
    }
    if (action === 'open' && direction === 'short') {
      return (
        <span className="px-3 py-1 rounded-full text-sm font-medium bg-red-500/20 text-red-400">
          OPEN SHORT
        </span>
      )
    }
    return null
  }

  const getStatusBadge = (status: string) => {
    const configs: Record<string, { icon: any; color: string; label: string }> = {
      'executed': { icon: CheckCircle, color: 'text-green-400', label: 'Executed' },
      'pending': { icon: Clock, color: 'text-yellow-400', label: 'Pending' },
      'failed': { icon: XCircle, color: 'text-red-400', label: 'Failed' },
      'skipped': { icon: AlertCircle, color: 'text-gray-400', label: 'Skipped' }
    }
    const config = configs[status] || configs['skipped']
    const Icon = config.icon

    return (
      <div className={`flex items-center gap-1.5 ${config.color}`}>
        <Icon className="w-4 h-4" />
        <span className="text-sm font-medium">{config.label}</span>
      </div>
    )
  }

  const getRsiIndicator = (rsi?: number) => {
    if (!rsi) return null
    let color = 'text-gray-400'
    let label = 'Neutral'
    if (rsi >= 70) {
      color = 'text-red-400'
      label = 'Overbought'
    } else if (rsi <= 30) {
      color = 'text-green-400'
      label = 'Oversold'
    }
    return (
      <div className="flex items-center justify-between">
        <span className="text-gray-400">RSI</span>
        <div className="flex items-center gap-2">
          <span className={`font-medium ${color}`}>{rsi.toFixed(1)}</span>
          <span className={`text-xs ${color}`}>{label}</span>
        </div>
      </div>
    )
  }

  const getMacdIndicator = (macd?: number, signal?: number) => {
    if (macd === undefined || signal === undefined) return null
    const isBullish = macd > signal
    return (
      <div className="flex items-center justify-between">
        <span className="text-gray-400">MACD</span>
        <div className="flex items-center gap-2">
          <span className={`font-medium ${isBullish ? 'text-green-400' : 'text-red-400'}`}>
            {macd.toFixed(2)}
          </span>
          <span className={`text-xs ${isBullish ? 'text-green-400' : 'text-red-400'}`}>
            {isBullish ? 'Bullish' : 'Bearish'}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 rounded-xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain className="w-6 h-6 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">Decision Details</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        ) : !decision ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-500">
            <AlertCircle className="w-12 h-12 mb-3 opacity-50" />
            <p>Decision not found</p>
          </div>
        ) : (
          <div className="p-6 space-y-6">
            {/* Summary */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-2xl font-bold text-white">{decision.symbol}</span>
                {getActionBadge(decision.action, decision.direction)}
              </div>
              {getStatusBadge(decision.execution_status)}
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {decision.confidence !== undefined && (
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                    <Target className="w-4 h-4" />
                    <span>Confidence</span>
                  </div>
                  <div className={`text-xl font-bold ${
                    decision.confidence >= 0.7 ? 'text-green-400' :
                    decision.confidence >= 0.5 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {(decision.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              )}
              {decision.leverage && (
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                    <Zap className="w-4 h-4" />
                    <span>Leverage</span>
                  </div>
                  <div className="text-xl font-bold text-white">{decision.leverage}x</div>
                </div>
              )}
              {decision.stop_loss_pct && (
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                    <Shield className="w-4 h-4" />
                    <span>Stop Loss</span>
                  </div>
                  <div className="text-xl font-bold text-red-400">
                    {decision.stop_loss_pct.toFixed(1)}%
                  </div>
                </div>
              )}
              {decision.take_profit_pct && (
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
                    <TrendingUp className="w-4 h-4" />
                    <span>Take Profit</span>
                  </div>
                  <div className="text-xl font-bold text-green-400">
                    {decision.take_profit_pct.toFixed(1)}%
                  </div>
                </div>
              )}
            </div>

            {/* Reasoning */}
            {decision.reasoning && (
              <div className="bg-gray-800/50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
                  <Brain className="w-4 h-4" />
                  AI Reasoning
                </h3>
                <p className="text-white whitespace-pre-wrap">{decision.reasoning}</p>
              </div>
            )}

            {/* Technical Indicators */}
            {context && (
              <div className="bg-gray-800/50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  Technical Indicators
                </h3>
                <div className="space-y-3">
                  {/* Price */}
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Price</span>
                    <span className="font-medium text-white">
                      {formatCurrency(context.price)}
                      {context.price_change_24h != null && (
                        <span className={`ml-2 text-sm ${
                          context.price_change_24h >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {context.price_change_24h >= 0 ? '+' : ''}{context.price_change_24h.toFixed(2)}%
                        </span>
                      )}
                    </span>
                  </div>

                  {/* RSI */}
                  {getRsiIndicator(context.rsi)}

                  {/* MACD */}
                  {getMacdIndicator(context.macd, context.macd_signal)}

                  {/* EMA */}
                  {context.ema2 && context.ema20 && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">EMA Trend</span>
                      <span className={`font-medium ${
                        context.ema2 > context.ema20 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {context.ema2 > context.ema20 ? 'Bullish' : 'Bearish'}
                        <span className="text-xs text-gray-500 ml-2">
                          (EMA2: {context.ema2.toFixed(0)} / EMA20: {context.ema20.toFixed(0)})
                        </span>
                      </span>
                    </div>
                  )}

                  {/* Orderbook */}
                  {context.orderbook_ratio && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Order Book Ratio</span>
                      <span className={`font-medium ${
                        context.orderbook_ratio > 1 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {context.orderbook_ratio.toFixed(2)}
                        <span className="text-xs text-gray-500 ml-2">
                          ({context.orderbook_ratio > 1 ? 'Buy Pressure' : 'Sell Pressure'})
                        </span>
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Forecast */}
            {context && context.forecast_trend && (
              <div className="bg-gray-800/50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Prophet Forecast
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Trend</span>
                    <span className={`font-medium px-2 py-0.5 rounded ${
                      context.forecast_trend === 'up' ? 'bg-green-500/20 text-green-400' :
                      context.forecast_trend === 'down' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {context.forecast_trend.toUpperCase()}
                    </span>
                  </div>
                  {context.forecast_target_price && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Target Price</span>
                      <span className="font-medium text-white">
                        {formatCurrency(context.forecast_target_price)}
                      </span>
                    </div>
                  )}
                  {context.forecast_change_pct != null && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Expected Change</span>
                      <span className={`font-medium ${
                        context.forecast_change_pct >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {context.forecast_change_pct >= 0 ? '+' : ''}{context.forecast_change_pct.toFixed(2)}%
                      </span>
                    </div>
                  )}
                  {context.forecast_confidence != null && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Forecast Confidence</span>
                      <span className="font-medium text-white">
                        {(context.forecast_confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Sentiment */}
            {context && context.sentiment_label && (
              <div className="bg-gray-800/50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Market Sentiment
                </h3>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Fear & Greed</span>
                  <div className="flex items-center gap-2">
                    <span className={`font-medium ${
                      context.sentiment_label === 'Extreme Greed' || context.sentiment_label === 'Greed'
                        ? 'text-green-400' :
                      context.sentiment_label === 'Extreme Fear' || context.sentiment_label === 'Fear'
                        ? 'text-red-400' : 'text-yellow-400'
                    }`}>
                      {context.sentiment_score}
                    </span>
                    <span className="text-gray-400 text-sm">({context.sentiment_label})</span>
                  </div>
                </div>
              </div>
            )}

            {/* Execution Details */}
            {decision.execution_details && (
              <div className="bg-gray-800/50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Execution Details
                </h3>
                <div className="space-y-2 text-sm">
                  {decision.entry_price && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Entry Price</span>
                      <span className="text-white">{formatCurrency(decision.entry_price)}</span>
                    </div>
                  )}
                  {decision.entry_quantity && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Quantity</span>
                      <span className="text-white">{decision.entry_quantity}</span>
                    </div>
                  )}
                  {decision.order_id && (
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">Order ID</span>
                      <span className="text-white font-mono text-xs">{decision.order_id}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Timestamp */}
            <div className="text-center text-sm text-gray-500">
              <Clock className="w-4 h-4 inline-block mr-1" />
              {new Date(decision.timestamp).toLocaleString()}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
