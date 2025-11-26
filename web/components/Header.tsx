'use client'

import { useState, useEffect } from 'react'
import { Bell, Zap, Clock, Activity, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'

interface WorkflowStatus {
  isRunning: boolean
  lastRun?: {
    status: string
    conclusion: string | null
    created_at: string
    html_url: string
  }
  nextScheduledRun?: string
  error?: string
}

export default function Header() {
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper')
  const [alertCount, setAlertCount] = useState(0)
  const [workflow, setWorkflow] = useState<WorkflowStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000) // Every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      // Fetch general status
      const statusRes = await fetch('/api/status')
      if (statusRes.ok) {
        const statusData = await statusRes.json()
        setTradingMode(statusData.trading_mode || 'paper')
        setAlertCount(statusData.unread_alerts || 0)
      }

      // Fetch workflow status
      const botRes = await fetch('/api/bot/status')
      if (botRes.ok) {
        const botData = await botRes.json()
        setWorkflow({
          isRunning: botData.isRunning,
          lastRun: botData.lastRun,
          nextScheduledRun: botData.nextScheduledRun,
          error: botData.workflow?.error
        })
      }
    } catch (error) {
      console.error('Failed to fetch status:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatTimeUntil = (isoString: string) => {
    const target = new Date(isoString)
    const now = new Date()
    const diffMs = target.getTime() - now.getTime()
    const diffMins = Math.round(diffMs / 60000)

    if (diffMins <= 0) return 'any moment'
    if (diffMins === 1) return '1 min'
    return `${diffMins} min`
  }

  const formatLastRun = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleTimeString('it-IT', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusColor = () => {
    if (!workflow) return 'bg-gray-500'
    if (workflow.isRunning) return 'bg-blue-500 animate-pulse'
    if (workflow.lastRun?.conclusion === 'success') return 'bg-green-500'
    if (workflow.lastRun?.conclusion === 'failure') return 'bg-red-500'
    return 'bg-yellow-500'
  }

  const getStatusText = () => {
    if (!workflow) return 'Loading...'
    if (workflow.error) return 'Config needed'
    if (workflow.isRunning) return 'Running now'
    if (workflow.lastRun?.conclusion === 'success') return 'Last run: OK'
    if (workflow.lastRun?.conclusion === 'failure') return 'Last run: Failed'
    return 'Scheduled'
  }

  return (
    <header className="h-16 bg-gray-900/50 backdrop-blur-sm border-b border-gray-800 px-6 flex items-center justify-between">
      {/* Left section */}
      <div className="flex items-center gap-4">
        {/* Trading Mode Badge */}
        <div className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium',
          tradingMode === 'paper'
            ? 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20'
            : 'bg-green-500/10 text-green-500 border border-green-500/20'
        )}>
          <Zap className="w-4 h-4" />
          {tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}
        </div>

        {/* Workflow Status */}
        <div className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
          workflow?.isRunning
            ? 'bg-blue-500/10 text-blue-400'
            : workflow?.lastRun?.conclusion === 'success'
              ? 'bg-green-500/10 text-green-400'
              : workflow?.lastRun?.conclusion === 'failure'
                ? 'bg-red-500/10 text-red-400'
                : 'bg-gray-500/10 text-gray-400'
        )}>
          <span className={cn('w-2 h-2 rounded-full', getStatusColor())} />
          <Activity className="w-4 h-4" />
          {getStatusText()}
        </div>
      </div>

      {/* Center - Schedule Info */}
      <div className="flex items-center gap-6 text-sm">
        {workflow?.lastRun && (
          <div className="flex items-center gap-2 text-gray-400">
            <Clock className="w-4 h-4" />
            <span>Last: {formatLastRun(workflow.lastRun.created_at)}</span>
            {workflow.lastRun.html_url && (
              <a
                href={workflow.lastRun.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        )}

        {workflow?.nextScheduledRun && !workflow.isRunning && (
          <div className="flex items-center gap-2 text-gray-400">
            <span className="text-gray-600">|</span>
            <span>Next run in <span className="text-white font-medium">{formatTimeUntil(workflow.nextScheduledRun)}</span></span>
          </div>
        )}

        {workflow?.isRunning && (
          <div className="flex items-center gap-2 text-blue-400">
            <span className="inline-block w-1 h-1 bg-blue-400 rounded-full animate-ping" />
            <span>Bot is analyzing markets...</span>
          </div>
        )}
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        {/* Auto-refresh indicator */}
        <span className="text-xs text-gray-600">
          Auto-refresh 30s
        </span>

        {/* Alerts */}
        <button className="relative p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
          <Bell className="w-5 h-5" />
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs text-white flex items-center justify-center">
              {alertCount > 9 ? '9+' : alertCount}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
