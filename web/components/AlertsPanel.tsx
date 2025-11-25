'use client'

import { TradingAlert } from '@/lib/supabase'
import { formatTimeAgo, cn, getSeverityColor } from '@/lib/utils'
import { Bell, AlertTriangle, Info, AlertCircle, Check } from 'lucide-react'
import { supabase } from '@/lib/supabase'

interface AlertsPanelProps {
  alerts: TradingAlert[]
}

export default function AlertsPanel({ alerts }: AlertsPanelProps) {
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      default:
        return <Info className="w-4 h-4 text-blue-500" />
    }
  }

  const markAsRead = async (alertId: string) => {
    try {
      await supabase
        .from('trading_alerts')
        .update({ is_read: true, read_at: new Date().toISOString() })
        .eq('id', alertId)
      window.location.reload()
    } catch (error) {
      console.error('Failed to mark alert as read:', error)
    }
  }

  const markAllAsRead = async () => {
    try {
      const alertIds = alerts.map(a => a.id)
      await supabase
        .from('trading_alerts')
        .update({ is_read: true, read_at: new Date().toISOString() })
        .in('id', alertIds)
      window.location.reload()
    } catch (error) {
      console.error('Failed to mark all alerts as read:', error)
    }
  }

  return (
    <div className="card h-full">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-gray-400" />
          <h2 className="card-title">Alerts</h2>
        </div>
        {alerts.length > 0 && (
          <button
            onClick={markAllAsRead}
            className="text-sm text-gray-400 hover:text-white flex items-center gap-1"
          >
            <Check className="w-4 h-4" />
            Mark all read
          </button>
        )}
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No new alerts</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-80 overflow-y-auto">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={cn(
                'bg-gray-800/50 rounded-lg p-3 border-l-2 cursor-pointer hover:bg-gray-800/70 transition-colors',
                alert.severity === 'critical' ? 'border-red-500' :
                alert.severity === 'warning' ? 'border-yellow-500' : 'border-blue-500'
              )}
              onClick={() => markAsRead(alert.id)}
            >
              <div className="flex items-start gap-3">
                {getSeverityIcon(alert.severity)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-sm font-medium text-white truncate">
                      {alert.title}
                    </h4>
                    <span className="text-xs text-gray-500 whitespace-nowrap">
                      {formatTimeAgo(alert.created_at)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 mt-1 line-clamp-2">
                    {alert.message}
                  </p>
                  {alert.symbol && (
                    <span className="inline-block mt-2 text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
                      {alert.symbol}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
