'use client'

import { useEffect, useState } from 'react'
import { Clock, TrendingUp, TrendingDown, Minus, RefreshCw, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TradingDecision } from '@/lib/supabase'

interface DecisionTimelineProps {
  className?: string
  maxItems?: number
  autoRefresh?: boolean
  refreshInterval?: number
}

export default function DecisionTimeline({
  className,
  maxItems = 10,
  autoRefresh = true,
  refreshInterval = 60
}: DecisionTimelineProps) {
  const [decisions, setDecisions] = useState<TradingDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const fetchDecisions = async () => {
    try {
      setError(false)
      const res = await fetch('/api/status')
      const data = await res.json()

      if (data.success && data.recent_decisions) {
        setDecisions(data.recent_decisions.slice(0, maxItems))
      } else {
        setError(true)
      }
    } catch (err) {
      console.error('Error fetching decisions:', err)
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDecisions()

    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchDecisions, refreshInterval * 1000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  const toggleExpand = (id: string) => {
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

  const getActionIcon = (action: string, direction?: string) => {
    if (action === 'open') {
      return direction === 'long' ? (
        <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
      ) : (
        <TrendingDown className="w-5 h-5 text-red-600 dark:text-red-400" />
      )
    }
    if (action === 'close') {
      return <Minus className="w-5 h-5 text-blue-600 dark:text-blue-400" />
    }
    return <Minus className="w-5 h-5 text-gray-400" />
  }

  const getActionColor = (action: string, direction?: string) => {
    if (action === 'open') {
      return direction === 'long'
        ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10'
        : 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10'
    }
    if (action === 'close') {
      return 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/10'
    }
    return 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800'
  }

  const getStatusBadge = (status: string) => {
    const styles = {
      executed: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400',
      pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400',
      failed: 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400',
      skipped: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
    }
    return styles[status as keyof typeof styles] || styles.skipped
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  if (loading) {
    return (
      <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow p-6", className)}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Recent Decisions</h3>
          <RefreshCw className="w-5 h-5 animate-spin text-gray-400" />
        </div>
        <div className="text-center py-8 text-gray-500">Loading decisions...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow p-6", className)}>
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>Failed to load decisions</span>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow", className)}>
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold">Recent Decisions</h3>
          </div>
          <button
            onClick={fetchDecisions}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
          Last {decisions.length} trading decisions with AI reasoning
        </div>
      </div>

      <div className="p-6">
        {decisions.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No recent decisions found
          </div>
        ) : (
          <div className="space-y-3">
            {decisions.map((decision) => {
              const isExpanded = expandedIds.has(decision.id)
              const hasReasoning = decision.reasoning && decision.reasoning.trim().length > 0

              return (
                <div
                  key={decision.id}
                  className={cn(
                    "border rounded-lg overflow-hidden transition-all",
                    getActionColor(decision.action, decision.direction)
                  )}
                >
                  <div
                    className="p-4 cursor-pointer"
                    onClick={() => hasReasoning && toggleExpand(decision.id)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1">
                        <div className="mt-1">
                          {getActionIcon(decision.action, decision.direction)}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold">{decision.symbol}</span>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              {decision.action.toUpperCase()}
                              {decision.direction && ` ${decision.direction.toUpperCase()}`}
                            </span>
                            <span className={cn(
                              "text-xs px-2 py-0.5 rounded-full font-medium",
                              getStatusBadge(decision.execution_status)
                            )}>
                              {decision.execution_status}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            {formatTimestamp(decision.timestamp)}
                            {decision.confidence != null && (
                              <span className="ml-3">
                                Confidence: {(decision.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {hasReasoning && (
                        <div>
                          {isExpanded ? (
                            <ChevronUp className="w-5 h-5 text-gray-400" />
                          ) : (
                            <ChevronDown className="w-5 h-5 text-gray-400" />
                          )}
                        </div>
                      )}
                    </div>

                    {/* Expanded reasoning */}
                    {isExpanded && hasReasoning && (
                      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                        <div className="text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                          AI Reasoning:
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">
                          {decision.reasoning}
                        </div>
                        {decision.execution_details && (
                          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                            <div className="text-xs text-gray-500">
                              {decision.entry_price && (
                                <div>Entry Price: ${decision.entry_price.toFixed(2)}</div>
                              )}
                              {decision.entry_quantity && (
                                <div>Quantity: {decision.entry_quantity.toFixed(6)}</div>
                              )}
                              {decision.order_id && (
                                <div>Order ID: {decision.order_id}</div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
