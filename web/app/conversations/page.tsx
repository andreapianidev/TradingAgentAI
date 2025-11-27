'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { supabase, TradingBotLog } from '@/lib/supabase'
import { formatDate, formatTimeAgo, cn } from '@/lib/utils'
import {
  MessageSquare,
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Filter,
  Sparkles,
  Brain,
  Cpu,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Copy,
  Check
} from 'lucide-react'

// Types for LLM conversation data
interface LLMRequest {
  type: 'llm_request'
  system_prompt_preview?: string
  user_prompt_preview?: string
  system_prompt_length?: number
  user_prompt_length?: number
}

interface LLMResponse {
  type: 'llm_response'
  raw_response?: string
  parsed_decision?: {
    action?: string
    symbol?: string
    direction?: string
    confidence?: number
    reasoning?: string
    leverage?: number
    position_size_pct?: number
    stop_loss_pct?: number
    take_profit_pct?: number
  }
}

interface ConversationPair {
  id: string
  symbol: string
  timestamp: string
  request?: TradingBotLog
  response?: TradingBotLog
  requestDetails?: LLMRequest
  responseDetails?: LLMResponse
}

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring" as const, stiffness: 100, damping: 15 }
  }
}

const cardVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    transition: {
      delay: i * 0.05,
      type: "spring" as const,
      stiffness: 100,
      damping: 15
    }
  })
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationPair[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [symbolFilter, setSymbolFilter] = useState<string>('all')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const fetchConversations = useCallback(async () => {
    try {
      // Fetch LLM logs (both requests and responses)
      const { data, error } = await supabase
        .from('trading_bot_logs')
        .select('*')
        .eq('component', 'llm')
        .order('created_at', { ascending: false })
        .limit(200)

      if (error) {
        console.error('Error fetching conversations:', error)
        return
      }

      if (!data) {
        setConversations([])
        return
      }

      // Group requests and responses into conversation pairs
      const pairs: ConversationPair[] = []
      const processedIds = new Set<string>()

      for (const log of data) {
        if (processedIds.has(log.id)) continue

        const details = log.details as LLMRequest | LLMResponse | null

        if (details?.type === 'llm_request') {
          // Find matching response (next log with same symbol and type llm_response)
          const responseLog = data.find(
            l => l.symbol === log.symbol &&
                 !processedIds.has(l.id) &&
                 l.id !== log.id &&
                 (l.details as LLMResponse)?.type === 'llm_response' &&
                 new Date(l.created_at).getTime() > new Date(log.created_at).getTime() &&
                 new Date(l.created_at).getTime() - new Date(log.created_at).getTime() < 120000 // within 2 minutes
          )

          pairs.push({
            id: log.id,
            symbol: log.symbol || 'Unknown',
            timestamp: log.created_at,
            request: log,
            response: responseLog,
            requestDetails: details as LLMRequest,
            responseDetails: responseLog?.details as LLMResponse
          })

          processedIds.add(log.id)
          if (responseLog) processedIds.add(responseLog.id)
        } else if (details?.type === 'llm_response' && !processedIds.has(log.id)) {
          // Orphan response (no matching request found)
          pairs.push({
            id: log.id,
            symbol: log.symbol || 'Unknown',
            timestamp: log.created_at,
            response: log,
            responseDetails: details as LLMResponse
          })
          processedIds.add(log.id)
        }
      }

      // Filter by symbol if needed
      const filtered = symbolFilter === 'all'
        ? pairs
        : pairs.filter(p => p.symbol === symbolFilter)

      setConversations(filtered)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }, [symbolFilter])

  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(fetchConversations, 30000)
    return () => clearInterval(interval)
  }, [autoRefresh, fetchConversations])

  const toggleExpanded = (id: string) => {
    setExpandedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const getActionIcon = (action?: string, direction?: string) => {
    if (action === 'news_analysis') return <MessageSquare className="w-4 h-4 text-blue-500" />
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
    return <Brain className="w-4 h-4 text-purple-500" />
  }

  const getActionColor = (action?: string) => {
    switch (action) {
      case 'news_analysis': return 'text-blue-500 bg-blue-500/10 border-blue-500/30'
      case 'open': return 'text-green-500 bg-green-500/10 border-green-500/30'
      case 'close': return 'text-red-500 bg-red-500/10 border-red-500/30'
      case 'hold': return 'text-gray-400 bg-gray-500/10 border-gray-500/30'
      default: return 'text-purple-500 bg-purple-500/10 border-purple-500/30'
    }
  }

  const uniqueSymbols = Array.from(new Set(conversations.map(c => c.symbol))).sort()

  return (
    <motion.div
      className="space-y-6"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {/* Header */}
      <motion.div
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        variants={itemVariants}
      >
        <div className="flex items-center gap-3">
          <motion.div
            className="p-2 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-xl"
            whileHover={{ rotate: 360 }}
            transition={{ duration: 0.5 }}
          >
            <MessageSquare className="w-6 h-6 text-purple-400" />
          </motion.div>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              AI Conversations
              <motion.span
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Sparkles className="w-5 h-5 text-yellow-400" />
              </motion.span>
            </h1>
            <p className="text-gray-400">DeepSeek API calls and AI reasoning</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Symbol Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
              className="select w-32"
            >
              <option value="all">All Symbols</option>
              {uniqueSymbols.map(symbol => (
                <option key={symbol} value={symbol}>{symbol}</option>
              ))}
            </select>
          </div>

          {/* Auto-refresh toggle */}
          <motion.button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              autoRefresh
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-gray-800 text-gray-400 border border-gray-700'
            )}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <motion.div
              animate={autoRefresh ? { rotate: 360 } : {}}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            >
              <RefreshCw className="w-4 h-4" />
            </motion.div>
            {autoRefresh ? 'Auto' : 'Manual'}
          </motion.button>

          {/* Manual refresh */}
          <motion.button
            onClick={() => { setLoading(true); fetchConversations() }}
            className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 hover:text-white transition-colors"
            whileHover={{ scale: 1.1, rotate: 180 }}
            whileTap={{ scale: 0.9 }}
          >
            <RefreshCw className="w-5 h-5" />
          </motion.button>
        </div>
      </motion.div>

      {/* Stats */}
      <motion.div
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
        variants={containerVariants}
      >
        {[
          { label: 'Total Conversations', value: conversations.length, icon: MessageSquare, color: 'text-purple-400' },
          { label: 'Open Decisions', value: conversations.filter(c => c.responseDetails?.parsed_decision?.action === 'open').length, icon: ArrowUpRight, color: 'text-green-400' },
          { label: 'Close Decisions', value: conversations.filter(c => c.responseDetails?.parsed_decision?.action === 'close').length, icon: ArrowDownRight, color: 'text-red-400' },
          { label: 'Hold Decisions', value: conversations.filter(c => c.responseDetails?.parsed_decision?.action === 'hold').length, icon: Minus, color: 'text-gray-400' }
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            className="stat-card"
            custom={i}
            variants={cardVariants}
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center gap-2 mb-2">
              <stat.icon className={cn("w-4 h-4", stat.color)} />
              <span className="stat-label">{stat.label}</span>
            </div>
            <motion.div
              className="stat-value text-white"
              key={stat.value}
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
            >
              {stat.value}
            </motion.div>
          </motion.div>
        ))}
      </motion.div>

      {/* Conversations List */}
      <motion.div className="space-y-4" variants={itemVariants}>
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <motion.div
              className="relative"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <div className="w-12 h-12 border-4 border-gray-700 border-t-purple-500 rounded-full" />
            </motion.div>
            <motion.p
              className="text-gray-400 text-sm"
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              Loading conversations...
            </motion.p>
          </div>
        ) : conversations.length === 0 ? (
          <motion.div
            className="text-center py-12 text-gray-500"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
            </motion.div>
            <p>No AI conversations found</p>
            <p className="text-sm mt-1">Conversations will appear when the bot makes LLM calls</p>
          </motion.div>
        ) : (
          <AnimatePresence>
            {conversations.map((conv, index) => {
              const isExpanded = expandedIds.has(conv.id)
              const decision = conv.responseDetails?.parsed_decision

              return (
                <motion.div
                  key={conv.id}
                  custom={index}
                  variants={cardVariants}
                  initial="hidden"
                  animate="visible"
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="card overflow-hidden"
                >
                  {/* Header - Always visible */}
                  <motion.div
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800/30 transition-colors"
                    onClick={() => toggleExpanded(conv.id)}
                  >
                    <div className="flex items-center gap-4">
                      <motion.div
                        className="p-2 bg-purple-500/20 rounded-lg"
                        whileHover={{ rotate: 15 }}
                      >
                        <Cpu className="w-5 h-5 text-purple-400" />
                      </motion.div>

                      <div>
                        <div className="flex items-center gap-3">
                          <span className="font-bold text-white text-lg">{conv.symbol}</span>
                          {decision && (
                            <span className={cn(
                              'px-2 py-0.5 rounded-md text-xs font-medium border flex items-center gap-1',
                              getActionColor(decision.action)
                            )}>
                              {getActionIcon(decision.action, decision.direction)}
                              {decision.action?.toUpperCase()}
                              {decision.direction && ` ${decision.direction.toUpperCase()}`}
                            </span>
                          )}
                          {decision?.confidence && (
                            <span className="text-sm text-gray-400">
                              {(decision.confidence * 100).toFixed(0)}% confidence
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                          <span>{formatTimeAgo(conv.timestamp)}</span>
                          <span className="text-gray-600">|</span>
                          <span>{formatDate(conv.timestamp)}</span>
                        </div>
                      </div>
                    </div>

                    <motion.div
                      animate={{ rotate: isExpanded ? 180 : 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    </motion.div>
                  </motion.div>

                  {/* Expanded Content */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="border-t border-gray-800"
                      >
                        <div className="p-4 space-y-4">
                          {/* Request Section */}
                          {conv.requestDetails && (
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm font-medium text-blue-400">
                                <User className="w-4 h-4" />
                                <span>Request to DeepSeek</span>
                                {conv.requestDetails.user_prompt_length && (
                                  <span className="text-gray-500 text-xs">
                                    ({conv.requestDetails.user_prompt_length.toLocaleString()} chars)
                                  </span>
                                )}
                              </div>

                              {/* System Prompt Preview */}
                              {conv.requestDetails.system_prompt_preview && (
                                <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-gray-500 uppercase tracking-wider">System Prompt</span>
                                    <motion.button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        copyToClipboard(conv.requestDetails!.system_prompt_preview || '', `sys-${conv.id}`)
                                      }}
                                      className="p-1 hover:bg-gray-800 rounded"
                                      whileHover={{ scale: 1.1 }}
                                      whileTap={{ scale: 0.9 }}
                                    >
                                      {copiedId === `sys-${conv.id}` ? (
                                        <Check className="w-3 h-3 text-green-400" />
                                      ) : (
                                        <Copy className="w-3 h-3 text-gray-500" />
                                      )}
                                    </motion.button>
                                  </div>
                                  <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
                                    {conv.requestDetails.system_prompt_preview}
                                  </pre>
                                </div>
                              )}

                              {/* User Prompt Preview */}
                              {conv.requestDetails.user_prompt_preview && (
                                <div className="bg-blue-900/20 rounded-lg p-3 border border-blue-800/30">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-blue-400 uppercase tracking-wider">User Prompt (Market Data)</span>
                                    <motion.button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        copyToClipboard(conv.requestDetails!.user_prompt_preview || '', `usr-${conv.id}`)
                                      }}
                                      className="p-1 hover:bg-gray-800 rounded"
                                      whileHover={{ scale: 1.1 }}
                                      whileTap={{ scale: 0.9 }}
                                    >
                                      {copiedId === `usr-${conv.id}` ? (
                                        <Check className="w-3 h-3 text-green-400" />
                                      ) : (
                                        <Copy className="w-3 h-3 text-gray-500" />
                                      )}
                                    </motion.button>
                                  </div>
                                  <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                                    {conv.requestDetails.user_prompt_preview}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Response Section */}
                          {conv.responseDetails && (
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm font-medium text-green-400">
                                <Bot className="w-4 h-4" />
                                <span>DeepSeek Response</span>
                              </div>

                              {/* Parsed Decision */}
                              {decision && (
                                <div className="bg-green-900/20 rounded-lg p-3 border border-green-800/30">
                                  <div className="text-xs text-green-400 uppercase tracking-wider mb-2">Parsed Decision</div>
                                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                                    <div>
                                      <span className="text-gray-500">Action:</span>
                                      <span className={cn(
                                        "ml-2 font-medium",
                                        decision.action === 'open' ? 'text-green-400' :
                                        decision.action === 'close' ? 'text-red-400' : 'text-gray-400'
                                      )}>
                                        {decision.action?.toUpperCase()}
                                      </span>
                                    </div>
                                    {decision.direction && (
                                      <div>
                                        <span className="text-gray-500">Direction:</span>
                                        <span className={cn(
                                          "ml-2 font-medium",
                                          decision.direction === 'long' ? 'text-green-400' : 'text-red-400'
                                        )}>
                                          {decision.direction.toUpperCase()}
                                        </span>
                                      </div>
                                    )}
                                    <div>
                                      <span className="text-gray-500">Confidence:</span>
                                      <span className="ml-2 text-white font-medium">
                                        {((decision.confidence || 0) * 100).toFixed(1)}%
                                      </span>
                                    </div>
                                    {decision.leverage && (
                                      <div>
                                        <span className="text-gray-500">Leverage:</span>
                                        <span className="ml-2 text-white font-medium">{decision.leverage}x</span>
                                      </div>
                                    )}
                                    {decision.position_size_pct && (
                                      <div>
                                        <span className="text-gray-500">Size:</span>
                                        <span className="ml-2 text-white font-medium">{decision.position_size_pct}%</span>
                                      </div>
                                    )}
                                    {decision.stop_loss_pct && (
                                      <div>
                                        <span className="text-gray-500">Stop Loss:</span>
                                        <span className="ml-2 text-red-400 font-medium">{decision.stop_loss_pct}%</span>
                                      </div>
                                    )}
                                    {decision.take_profit_pct && (
                                      <div>
                                        <span className="text-gray-500">Take Profit:</span>
                                        <span className="ml-2 text-green-400 font-medium">{decision.take_profit_pct}%</span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* AI Reasoning */}
                              {decision?.reasoning && (
                                <div className="bg-purple-900/20 rounded-lg p-3 border border-purple-800/30">
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                      <Brain className="w-4 h-4 text-purple-400" />
                                      <span className="text-xs text-purple-400 uppercase tracking-wider">AI Reasoning</span>
                                    </div>
                                    <motion.button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        copyToClipboard(decision.reasoning || '', `reason-${conv.id}`)
                                      }}
                                      className="p-1 hover:bg-gray-800 rounded"
                                      whileHover={{ scale: 1.1 }}
                                      whileTap={{ scale: 0.9 }}
                                    >
                                      {copiedId === `reason-${conv.id}` ? (
                                        <Check className="w-3 h-3 text-green-400" />
                                      ) : (
                                        <Copy className="w-3 h-3 text-gray-500" />
                                      )}
                                    </motion.button>
                                  </div>
                                  <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
                                    {decision.reasoning}
                                  </p>
                                </div>
                              )}

                              {/* Raw Response */}
                              {conv.responseDetails.raw_response && (
                                <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-gray-500 uppercase tracking-wider">Raw Response</span>
                                    <motion.button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        copyToClipboard(conv.responseDetails!.raw_response || '', `raw-${conv.id}`)
                                      }}
                                      className="p-1 hover:bg-gray-800 rounded"
                                      whileHover={{ scale: 1.1 }}
                                      whileTap={{ scale: 0.9 }}
                                    >
                                      {copiedId === `raw-${conv.id}` ? (
                                        <Check className="w-3 h-3 text-green-400" />
                                      ) : (
                                        <Copy className="w-3 h-3 text-gray-500" />
                                      )}
                                    </motion.button>
                                  </div>
                                  <pre className="text-xs text-gray-400 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                                    {conv.responseDetails.raw_response}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}

                          {/* No response warning */}
                          {!conv.responseDetails && (
                            <div className="bg-yellow-900/20 rounded-lg p-3 border border-yellow-800/30">
                              <p className="text-sm text-yellow-400">
                                Response not found or still pending...
                              </p>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </AnimatePresence>
        )}
      </motion.div>
    </motion.div>
  )
}
