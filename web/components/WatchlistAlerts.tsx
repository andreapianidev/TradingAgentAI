'use client'

import { useEffect, useState } from 'react'
import { Bell, Plus, Minus, RefreshCw, AlertCircle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Alert {
  id: string
  created_at: string
  alert_type: string
  severity: string
  message: string
  metadata?: any
}

interface WatchlistAlertsProps {
  className?: string
  maxItems?: number
  autoRefresh?: boolean
  refreshInterval?: number
}

export default function WatchlistAlerts({
  className,
  maxItems = 5,
  autoRefresh = true,
  refreshInterval = 30
}: WatchlistAlertsProps) {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const fetchAlerts = async () => {
    try {
      setError(false)
      const res = await fetch(`/api/alerts?limit=${maxItems * 2}`)
      const data = await res.json()

      if (data.success) {
        // Filter for watchlist alerts only
        const watchlistAlerts = (data.alerts || [])
          .filter((a: Alert) => a.alert_type?.startsWith('WATCHLIST_'))
          .slice(0, maxItems)
        setAlerts(watchlistAlerts)
      } else {
        setError(true)
      }
    } catch (err) {
      console.error('Error fetching alerts:', err)
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAlerts()

    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchAlerts, refreshInterval * 1000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  const getAlertIcon = (alertType: string) => {
    if (alertType === 'WATCHLIST_ADDED') {
      return <Plus className="w-4 h-4 text-green-600 dark:text-green-400" />
    }
    if (alertType === 'WATCHLIST_REMOVED') {
      return <Minus className="w-4 h-4 text-red-600 dark:text-red-400" />
    }
    return <Info className="w-4 h-4 text-blue-600 dark:text-blue-400" />
  }

  const getAlertColor = (alertType: string) => {
    if (alertType === 'WATCHLIST_ADDED') {
      return 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10'
    }
    if (alertType === 'WATCHLIST_REMOVED') {
      return 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10'
    }
    return 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/10'
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

  const getAlertLabel = (alertType: string) => {
    const labels: Record<string, string> = {
      'WATCHLIST_ADDED': 'Added',
      'WATCHLIST_REMOVED': 'Removed',
      'WATCHLIST_SCORE_CHANGED': 'Score Changed'
    }
    return labels[alertType] || alertType.replace('WATCHLIST_', '').replace('_', ' ')
  }

  if (loading) {
    return (
      <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow p-6", className)}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Watchlist Alerts</h3>
          <RefreshCw className="w-5 h-5 animate-spin text-gray-400" />
        </div>
        <div className="text-center py-8 text-gray-500">Loading alerts...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow p-6", className)}>
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>Failed to load alerts</span>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("bg-white dark:bg-gray-800 rounded-lg shadow", className)}>
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold">Watchlist Alerts</h3>
          </div>
          <button
            onClick={fetchAlerts}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
          Real-time portfolio changes
        </div>
      </div>

      <div className="p-6">
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No recent alerts
          </div>
        ) : (
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  "flex items-start gap-3 p-3 rounded-lg border transition-all",
                  getAlertColor(alert.alert_type)
                )}
              >
                <div className="mt-0.5">
                  {getAlertIcon(alert.alert_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium">
                      {getAlertLabel(alert.alert_type)}
                    </span>
                    <span className="text-xs text-gray-500">
                      {formatTimestamp(alert.created_at)}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {alert.message}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
