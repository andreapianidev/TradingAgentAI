'use client'

import { useState, useEffect } from 'react'
import { useTheme } from 'next-themes'
import { Bell, Zap, Clock, Activity, ExternalLink, Sun, Moon, Monitor } from 'lucide-react'
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
  const [mounted, setMounted] = useState(false)
  const { theme, setTheme, resolvedTheme } = useTheme()

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const statusRes = await fetch('/api/status')
      if (statusRes.ok) {
        const statusData = await statusRes.json()
        setTradingMode(statusData.trading_mode || 'paper')
        setAlertCount(statusData.unread_alerts || 0)
      }

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

  const cycleTheme = () => {
    if (theme === 'system') {
      setTheme('light')
    } else if (theme === 'light') {
      setTheme('dark')
    } else {
      setTheme('system')
    }
  }

  const getThemeIcon = () => {
    if (!mounted) return <Monitor className="w-4 h-4" />
    if (theme === 'system') return <Monitor className="w-4 h-4" />
    if (theme === 'light' || (theme === 'system' && resolvedTheme === 'light')) return <Sun className="w-4 h-4" />
    return <Moon className="w-4 h-4" />
  }

  return (
    <header className="h-14 md:h-16 bg-white dark:bg-gray-900/50 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800 px-4 md:px-6 flex items-center justify-between">
      {/* Left section - hidden on small screens to make room for hamburger */}
      <div className="hidden sm:flex items-center gap-2 md:gap-4 pl-8 lg:pl-0">
        {/* Trading Mode Badge */}
        <div className={cn(
          'flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 rounded-full text-xs md:text-sm font-medium',
          tradingMode === 'paper'
            ? 'bg-yellow-100 dark:bg-yellow-500/10 text-yellow-700 dark:text-yellow-500 border border-yellow-200 dark:border-yellow-500/20'
            : 'bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-500 border border-green-200 dark:border-green-500/20'
        )}>
          <Zap className="w-3 h-3 md:w-4 md:h-4" />
          <span className="hidden md:inline">{tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}</span>
          <span className="md:hidden">{tradingMode === 'paper' ? 'Paper' : 'Live'}</span>
        </div>

        {/* Workflow Status */}
        <div className={cn(
          'flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 rounded-full text-xs md:text-sm',
          workflow?.isRunning
            ? 'bg-blue-100 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400'
            : workflow?.lastRun?.conclusion === 'success'
              ? 'bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-400'
              : workflow?.lastRun?.conclusion === 'failure'
                ? 'bg-red-100 dark:bg-red-500/10 text-red-700 dark:text-red-400'
                : 'bg-gray-100 dark:bg-gray-500/10 text-gray-600 dark:text-gray-400'
        )}>
          <span className={cn('w-2 h-2 rounded-full', getStatusColor())} />
          <Activity className="w-3 h-3 md:w-4 md:h-4" />
          <span className="hidden md:inline">{getStatusText()}</span>
        </div>
      </div>

      {/* Center - Schedule Info - hidden on mobile */}
      <div className="hidden lg:flex items-center gap-6 text-sm">
        {workflow?.lastRun && (
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <Clock className="w-4 h-4" />
            <span>Last: {formatLastRun(workflow.lastRun.created_at)}</span>
            {workflow.lastRun.html_url && (
              <a
                href={workflow.lastRun.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        )}

        {workflow?.nextScheduledRun && !workflow.isRunning && (
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span>Next run in <span className="text-gray-900 dark:text-white font-medium">{formatTimeUntil(workflow.nextScheduledRun)}</span></span>
          </div>
        )}

        {workflow?.isRunning && (
          <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
            <span className="inline-block w-1 h-1 bg-blue-600 dark:bg-blue-400 rounded-full animate-ping" />
            <span>Bot is analyzing markets...</span>
          </div>
        )}
      </div>

      {/* Right section */}
      <div className="flex items-center gap-2 md:gap-3 ml-auto">
        {/* Auto-refresh indicator - hidden on mobile */}
        <span className="hidden md:inline text-xs text-gray-400 dark:text-gray-600">
          Auto-refresh 30s
        </span>

        {/* Theme toggle */}
        <button
          onClick={cycleTheme}
          className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title={`Theme: ${theme}`}
        >
          {getThemeIcon()}
        </button>

        {/* Alerts */}
        <button className="relative p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
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
