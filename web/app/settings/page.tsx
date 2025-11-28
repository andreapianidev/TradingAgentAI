'use client'

import { useEffect, useState } from 'react'
import { supabase, TradingSetting } from '@/lib/supabase'
import { cn, formatDate } from '@/lib/utils'
import {
  Settings,
  Save,
  RefreshCw,
  Shield,
  Zap,
  Database,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  Info,
  ChevronDown,
  Sliders,
  Target,
  DollarSign,
  Percent,
  BarChart3,
  Power,
  Trash2,
  Eye
} from 'lucide-react'

interface SettingsGroup {
  category: string
  label: string
  icon: React.ReactNode
  iconColor: string
  description: string
  settings: TradingSetting[]
}

interface BotStatus {
  bot_active: boolean
  trading_mode: 'paper' | 'live'
  unread_alerts: number
  open_positions: number
  portfolio: {
    total_equity: number
    available_balance: number
    total_pnl: number
    total_pnl_pct: number
    exposure_pct: number
    last_update: string
  } | null
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<TradingSetting[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [changes, setChanges] = useState<Record<string, any>>({})
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [mounted, setMounted] = useState(false)
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    general: true,
    trading: true,
    risk: true
  })
  const [cleanupLoading, setCleanupLoading] = useState(false)
  const [cleanupResults, setCleanupResults] = useState<any>(null)
  const [dbStats, setDbStats] = useState<any>(null)

  useEffect(() => {
    setMounted(true)
    fetchSettings()
    fetchBotStatus()
    fetchDbStats()

    // Auto-refresh bot status every 30 seconds
    const interval = setInterval(fetchBotStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchDbStats = async () => {
    try {
      const res = await fetch('/api/database/cleanup')
      const data = await res.json()
      if (data.success) {
        setDbStats(data)
      }
    } catch (error) {
      console.error('Error fetching DB stats:', error)
    }
  }

  const runCleanup = async (dryRun: boolean = false) => {
    setCleanupLoading(true)
    setCleanupResults(null)
    try {
      const res = await fetch('/api/database/cleanup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dryRun })
      })
      const data = await res.json()
      setCleanupResults(data)
      if (!dryRun && data.success) {
        // Refresh stats after cleanup
        setTimeout(fetchDbStats, 1000)
      }
    } catch (error) {
      console.error('Cleanup error:', error)
      setCleanupResults({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to run cleanup'
      })
    } finally {
      setCleanupLoading(false)
    }
  }

  const fetchBotStatus = async () => {
    try {
      const res = await fetch('/api/status')
      const data = await res.json()
      if (data.success) {
        setBotStatus(data)
      }
    } catch (error) {
      console.error('Error fetching bot status:', error)
    } finally {
      setStatusLoading(false)
    }
  }

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('trading_settings')
        .select('*')
        .order('category')

      setSettings(data || [])
    } catch (error) {
      console.error('Error fetching settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (key: string, value: any) => {
    setChanges(prev => ({ ...prev, [key]: value }))
    // Clear message when user makes changes
    if (message) setMessage(null)
  }

  const saveSettings = async () => {
    setSaving(true)
    setMessage(null)
    try {
      for (const [key, value] of Object.entries(changes)) {
        await supabase
          .from('trading_settings')
          .update({ setting_value: JSON.stringify(value), updated_at: new Date().toISOString() })
          .eq('setting_key', key)
      }
      setMessage({ type: 'success', text: 'Settings saved successfully! Changes will take effect on the next bot cycle.' })
      setChanges({})
      fetchSettings()
      // Refresh bot status after saving
      setTimeout(fetchBotStatus, 1000)
    } catch (error) {
      console.error('Error saving settings:', error)
      setMessage({ type: 'error', text: 'Failed to save settings. Please try again.' })
    } finally {
      setSaving(false)
    }
  }

  const getValue = (setting: TradingSetting) => {
    if (changes.hasOwnProperty(setting.setting_key)) {
      return changes[setting.setting_key]
    }
    if (setting.setting_value === null || setting.setting_value === undefined) {
      return ''
    }
    try {
      return JSON.parse(setting.setting_value)
    } catch {
      return setting.setting_value
    }
  }

  const hasChanges = Object.keys(changes).length > 0

  const toggleSection = (category: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [category]: !prev[category]
    }))
  }

  const groupedSettings: SettingsGroup[] = [
    {
      category: 'general',
      label: 'General',
      icon: <Settings className="w-5 h-5 category-icon" />,
      iconColor: 'text-blue-500',
      description: 'Basic bot configuration and preferences',
      settings: settings.filter(s => s.category === 'general')
    },
    {
      category: 'trading',
      label: 'Trading',
      icon: <Zap className="w-5 h-5 category-icon" />,
      iconColor: 'text-green-500',
      description: 'Trading parameters and execution settings',
      settings: settings.filter(s => s.category === 'trading')
    },
    {
      category: 'risk',
      label: 'Risk Management',
      icon: <Shield className="w-5 h-5 category-icon" />,
      iconColor: 'text-orange-500',
      description: 'Stop loss, take profit, and exposure limits',
      settings: settings.filter(s => s.category === 'risk')
    }
  ]

  const getSettingIcon = (key: string) => {
    if (key.includes('symbol')) return <Target className="w-4 h-4" />
    if (key.includes('leverage')) return <TrendingUp className="w-4 h-4" />
    if (key.includes('pct') || key.includes('percent')) return <Percent className="w-4 h-4" />
    if (key.includes('price') || key.includes('balance')) return <DollarSign className="w-4 h-4" />
    if (key.includes('time') || key.includes('interval')) return <Clock className="w-4 h-4" />
    if (key.includes('enable') || key.includes('active')) return <Power className="w-4 h-4" />
    return <Sliders className="w-4 h-4" />
  }

  const renderSettingInput = (setting: TradingSetting) => {
    const value = getValue(setting)
    const key = setting.setting_key
    const isChanged = changes.hasOwnProperty(key)

    // Exchange selector (dropdown)
    if (key === 'exchange') {
      return (
        <select
          value={value || 'alpaca'}
          onChange={(e) => handleChange(key, e.target.value)}
          className={cn(
            "select select-enhanced w-44",
            isChanged && "ring-2 ring-green-500/50"
          )}
        >
          <option value="hyperliquid">Hyperliquid</option>
          <option value="alpaca">Alpaca</option>
        </select>
      )
    }

    // Timeframe selector (dropdown)
    if (key === 'timeframe') {
      return (
        <select
          value={value || '15m'}
          onChange={(e) => handleChange(key, e.target.value)}
          className={cn(
            "select select-enhanced w-36",
            isChanged && "ring-2 ring-green-500/50"
          )}
        >
          <option value="1m">1 minute</option>
          <option value="5m">5 minutes</option>
          <option value="15m">15 minutes</option>
          <option value="30m">30 minutes</option>
          <option value="1h">1 hour</option>
          <option value="4h">4 hours</option>
          <option value="1d">1 day</option>
        </select>
      )
    }

    // Boolean settings - Enhanced toggle switch
    if (typeof value === 'boolean' || value === 'true' || value === 'false') {
      const boolValue = value === true || value === 'true'
      return (
        <button
          onClick={() => handleChange(key, !boolValue)}
          className={cn(
            'relative inline-flex h-7 w-12 items-center rounded-full transition-all duration-300 toggle-switch',
            boolValue ? 'bg-green-600 active' : 'bg-gray-600',
            isChanged && "ring-2 ring-green-500/50"
          )}
        >
          <span
            className={cn(
              'inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition-all duration-300',
              boolValue ? 'translate-x-6' : 'translate-x-1'
            )}
          />
          <span className="sr-only">{boolValue ? 'Enabled' : 'Disabled'}</span>
        </button>
      )
    }

    // Array settings (like target_symbols)
    if (Array.isArray(value)) {
      return (
        <div className="flex flex-col gap-1">
          <input
            type="text"
            value={value.join(', ')}
            onChange={(e) => handleChange(key, e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
            className={cn(
              "input input-enhanced w-48",
              isChanged && "ring-2 ring-green-500/50"
            )}
            placeholder="BTC, ETH, SOL"
          />
          <span className="text-xs text-gray-500">Comma-separated values</span>
        </div>
      )
    }

    // Number settings
    if (typeof value === 'number' || (!isNaN(Number(value)) && value !== '')) {
      const isPercentage = key.includes('pct') || key.includes('percent')
      const isPrice = key.includes('price') || key.includes('balance')
      return (
        <div className="relative">
          <input
            type="number"
            value={value ?? ''}
            onChange={(e) => handleChange(key, parseFloat(e.target.value) || 0)}
            className={cn(
              "input input-enhanced w-36",
              isChanged && "ring-2 ring-green-500/50",
              (isPercentage || isPrice) && "pr-8"
            )}
            step={isPercentage ? '0.1' : '1'}
            min="0"
          />
          {isPercentage && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">%</span>
          )}
          {isPrice && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
          )}
        </div>
      )
    }

    // String settings
    return (
      <input
        type="text"
        value={value || ''}
        onChange={(e) => handleChange(key, e.target.value)}
        className={cn(
          "input input-enhanced",
          isChanged && "ring-2 ring-green-500/50"
        )}
      />
    )
  }

  const formatLabel = (key: string) => {
    return key
      .replace(/_/g, ' ')
      .replace(/pct/g, '%')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const isPaperTrading = botStatus?.trading_mode === 'paper'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={cn(
        "flex flex-col sm:flex-row sm:items-center justify-between gap-4",
        mounted && "animate-fade-in-up"
      )}>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white title-gradient cursor-default">
            Settings
          </h1>
          <p className="text-gray-500 dark:text-gray-400">Configure your trading bot parameters</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchSettings}
            disabled={loading}
            className="btn btn-secondary action-btn flex items-center gap-2"
          >
            <RefreshCw className={cn("w-4 h-4 transition-transform", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={saveSettings}
            disabled={!hasChanges || saving}
            className={cn(
              "btn btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all",
              hasChanges && !saving && "save-btn-active"
            )}
          >
            <Save className={cn("w-4 h-4", saving && "animate-pulse")} />
            {saving ? 'Saving...' : hasChanges ? `Save ${Object.keys(changes).length} Change${Object.keys(changes).length > 1 ? 's' : ''}` : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Bot Status Card */}
      <div className={cn(
        "card bot-status-card",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.1s' }}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={cn(
              "w-3 h-3 rounded-full status-dot",
              botStatus?.bot_active ? "bg-green-500 online" : "bg-red-500 offline"
            )} />
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                Bot Status
                {statusLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
                ) : (
                  <span className={cn(
                    "text-sm font-normal px-2 py-0.5 rounded-full",
                    botStatus?.bot_active
                      ? "bg-green-500/10 text-green-500"
                      : "bg-red-500/10 text-red-500"
                  )}>
                    {botStatus?.bot_active ? 'Active' : 'Inactive'}
                  </span>
                )}
              </h3>
              <p className="text-sm text-gray-500">
                {botStatus?.portfolio?.last_update
                  ? `Last update: ${formatDate(botStatus.portfolio.last_update)}`
                  : 'No recent activity'
                }
              </p>
            </div>
          </div>

          {botStatus && (
            <div className="flex flex-wrap items-center gap-4 sm:gap-6">
              <div className="text-center">
                <div className="text-sm text-gray-500">Mode</div>
                <div className={cn(
                  "font-semibold",
                  isPaperTrading ? "text-yellow-500" : "text-green-500"
                )}>
                  {isPaperTrading ? 'Paper' : 'Live'}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500">Positions</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {botStatus.open_positions}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-500">Alerts</div>
                <div className={cn(
                  "font-semibold",
                  botStatus.unread_alerts > 0 ? "text-red-500" : "text-gray-900 dark:text-white"
                )}>
                  {botStatus.unread_alerts}
                </div>
              </div>
              {botStatus.portfolio && (
                <div className="text-center">
                  <div className="text-sm text-gray-500">Equity</div>
                  <div className="font-semibold text-gray-900 dark:text-white">
                    ${botStatus.portfolio.total_equity?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={cn(
          'p-4 rounded-lg flex items-center gap-3 success-message',
          message.type === 'success'
            ? 'bg-green-500/10 text-green-500 border border-green-500/20'
            : 'bg-red-500/10 text-red-500 border border-red-500/20'
        )}>
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 flex-shrink-0" />
          )}
          <span>{message.text}</span>
          <button
            onClick={() => setMessage(null)}
            className="ml-auto p-1 hover:bg-white/10 rounded transition-colors"
          >
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Warning Banner */}
      {isPaperTrading && (
        <div className={cn(
          "warning-banner bg-yellow-100 dark:bg-yellow-500/10 border border-yellow-300 dark:border-yellow-500/20 rounded-lg p-4 flex items-start gap-3",
          mounted && "animate-fade-in-up"
        )} style={{ animationDelay: '0.2s' }}>
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-yellow-700 dark:text-yellow-500 font-medium">Paper Trading Mode Active</h4>
            <p className="text-yellow-600 dark:text-yellow-500/80 text-sm mt-1">
              The bot is currently running in paper trading mode. No real trades will be executed.
              Change the &quot;Paper Trading Enabled&quot; setting to switch to live trading.
            </p>
          </div>
        </div>
      )}

      {/* Unsaved Changes Indicator */}
      {hasChanges && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 flex items-center gap-3 success-message">
          <Info className="w-5 h-5 text-blue-500 flex-shrink-0" />
          <span className="text-blue-500 text-sm">
            You have {Object.keys(changes).length} unsaved change{Object.keys(changes).length > 1 ? 's' : ''}.
            Click &quot;Save Changes&quot; to apply them.
          </span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3">
          <div className="relative">
            <div className="animate-spin rounded-full h-10 w-10 border-2 border-green-500/20 border-t-green-500"></div>
            <div className="absolute inset-0 animate-ping rounded-full h-10 w-10 border border-green-500/30"></div>
          </div>
          <span className="text-gray-400 text-sm animate-pulse">Loading settings...</span>
        </div>
      ) : (
        <div className="space-y-4">
          {groupedSettings.map((group, groupIndex) => (
            <div
              key={group.category}
              className={cn(
                "card settings-card",
                mounted && "animate-fade-in-up"
              )}
              style={{ animationDelay: `${0.3 + groupIndex * 0.1}s` }}
            >
              {/* Section Header - Clickable */}
              <button
                onClick={() => toggleSection(group.category)}
                className="w-full card-header flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "p-2 rounded-lg transition-colors",
                    group.iconColor.replace('text-', 'bg-').replace('500', '500/10'),
                    "group-hover:scale-110 transition-transform"
                  )}>
                    <span className={group.iconColor}>{group.icon}</span>
                  </div>
                  <div className="text-left">
                    <h2 className="card-title">{group.label} Settings</h2>
                    <p className="text-sm text-gray-500 font-normal">{group.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full">
                    {group.settings.length} setting{group.settings.length !== 1 ? 's' : ''}
                  </span>
                  <ChevronDown className={cn(
                    "w-5 h-5 text-gray-400 accordion-icon transition-transform",
                    expandedSections[group.category] && "rotate-180"
                  )} />
                </div>
              </button>

              {/* Section Content */}
              <div className={cn(
                "accordion-content",
                expandedSections[group.category] ? "max-h-[2000px] opacity-100 mt-4" : "max-h-0 opacity-0"
              )}>
                <div className="space-y-1">
                  {group.settings.map((setting, index) => (
                    <div
                      key={setting.setting_key}
                      className={cn(
                        "setting-row flex flex-col sm:flex-row sm:items-center justify-between py-4 gap-3",
                        index !== group.settings.length - 1 && "border-b border-gray-200 dark:border-gray-800"
                      )}
                    >
                      <div className="flex items-start gap-3 flex-1">
                        <div className="p-1.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 mt-0.5">
                          {getSettingIcon(setting.setting_key)}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-900 dark:text-white font-medium">
                              {formatLabel(setting.setting_key)}
                            </span>
                            {changes.hasOwnProperty(setting.setting_key) && (
                              <span className="text-xs bg-green-500/10 text-green-500 px-1.5 py-0.5 rounded">
                                Modified
                              </span>
                            )}
                          </div>
                          {setting.description && (
                            <div className="text-sm text-gray-500 mt-0.5">
                              {setting.description}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="sm:ml-4 pl-9 sm:pl-0">
                        {renderSettingInput(setting)}
                      </div>
                    </div>
                  ))}
                  {group.settings.length === 0 && (
                    <div className="text-gray-500 text-center py-8 flex flex-col items-center gap-2">
                      <BarChart3 className="w-8 h-8 text-gray-400" />
                      <span>No settings in this category</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Schedule Settings */}
      <div className={cn(
        "card settings-card",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.55s' }}>
        <div className="card-header">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10">
              <Clock className="w-5 h-5 text-purple-500 category-icon" />
            </div>
            <div>
              <h2 className="card-title">Schedule Settings</h2>
              <p className="text-sm text-gray-500 font-normal">Configure when daily updates should run (UTC timezone)</p>
            </div>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          {/* AI Market Analysis Schedule */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="font-medium text-gray-900 dark:text-white mb-1">
                  AI Market Analysis
                </div>
                <div className="text-sm text-gray-500">
                  Daily comprehensive market analysis update time
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={changes.ai_analysis_schedule_hour ?? settings.find(s => s.setting_key === 'ai_analysis_schedule_hour')?.setting_value ?? 9}
                  onChange={(e) => handleChange('ai_analysis_schedule_hour', parseInt(e.target.value))}
                  className="w-20 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
                <span className="text-sm text-gray-500">:00 UTC</span>
              </div>
            </div>
          </div>

          {/* News Analysis Schedule */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="font-medium text-gray-900 dark:text-white mb-1">
                  News Analysis
                </div>
                <div className="text-sm text-gray-500">
                  Hours when news analysis should run (comma-separated)
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="6,12,18"
                  value={
                    changes.news_analysis_schedule_hours
                      ? Array.isArray(changes.news_analysis_schedule_hours)
                        ? changes.news_analysis_schedule_hours.join(',')
                        : String(changes.news_analysis_schedule_hours)
                      : (settings.find(s => s.setting_key === 'news_analysis_schedule_hours')?.setting_value as number[] || [6, 12, 18]).join(',')
                  }
                  onChange={(e) => {
                    const hours = e.target.value.split(',').map(h => parseInt(h.trim())).filter(h => !isNaN(h) && h >= 0 && h <= 23)
                    handleChange('news_analysis_schedule_hours', hours)
                  }}
                  className="w-32 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
                <span className="text-sm text-gray-500">UTC</span>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-500/5 border border-blue-200 dark:border-blue-500/20 rounded-lg p-3">
            <div className="text-sm text-blue-600 dark:text-blue-300 flex items-start gap-2">
              <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <div>
                The bot runs every 15 minutes. These settings determine during which hour the daily/periodic tasks should execute. All times are in UTC timezone.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Database Cleanup */}
      <div className={cn(
        "card settings-card",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.6s' }}>
        <div className="card-header">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/10">
                <Trash2 className="w-5 h-5 text-red-500 category-icon" />
              </div>
              <div>
                <h2 className="card-title">Database Cleanup</h2>
                <p className="text-sm text-gray-500 font-normal">Clean old logs and free up storage</p>
              </div>
            </div>
            <button
              onClick={fetchDbStats}
              className="btn btn-secondary flex items-center gap-2 text-sm"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh Stats
            </button>
          </div>
        </div>

        {/* Database Stats */}
        {dbStats && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            {dbStats.stats.map((stat: any) => (
              <div key={stat.table} className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-500 mb-1">{stat.table.replace('trading_', '')}</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {stat.records.toLocaleString()}
                </div>
                <div className="text-xs text-gray-400">records</div>
              </div>
            ))}
          </div>
        )}

        {/* Retention Policy Info */}
        <div className="mt-4 bg-blue-50 dark:bg-blue-500/5 border border-blue-200 dark:border-blue-500/20 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-700 dark:text-blue-400 mb-2">Retention Policy</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-blue-600 dark:text-blue-300">
            <div>• Bot Logs: <strong>7 days</strong></div>
            <div>• Market Data: <strong>30 days</strong></div>
            <div>• News: <strong>30 days</strong></div>
            <div>• Trading History: <strong>Forever</strong></div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-4 flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => runCleanup(true)}
            disabled={cleanupLoading}
            className="btn btn-secondary flex items-center justify-center gap-2"
          >
            <Eye className={cn("w-4 h-4", cleanupLoading && "animate-pulse")} />
            {cleanupLoading ? 'Checking...' : 'Preview Cleanup'}
          </button>
          <button
            onClick={() => runCleanup(false)}
            disabled={cleanupLoading}
            className="btn bg-red-600 hover:bg-red-700 text-white flex items-center justify-center gap-2"
          >
            <Trash2 className={cn("w-4 h-4", cleanupLoading && "animate-pulse")} />
            {cleanupLoading ? 'Cleaning...' : 'Run Cleanup'}
          </button>
        </div>

        {/* Cleanup Results */}
        {cleanupResults && (
          <div className={cn(
            "mt-4 p-4 rounded-lg border",
            cleanupResults.success
              ? "bg-green-50 dark:bg-green-500/5 border-green-200 dark:border-green-500/20"
              : "bg-red-50 dark:bg-red-500/5 border-red-200 dark:border-red-500/20"
          )}>
            <div className="flex items-center gap-2 mb-3">
              {cleanupResults.success ? (
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              ) : (
                <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              )}
              <h4 className={cn(
                "font-medium",
                cleanupResults.success
                  ? "text-green-700 dark:text-green-400"
                  : "text-red-700 dark:text-red-400"
              )}>
                {cleanupResults.message}
              </h4>
            </div>

            {cleanupResults.results && (
              <div className="space-y-2">
                {cleanupResults.results.map((result: any) => (
                  <div key={result.table} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-300">
                      {result.table}
                    </span>
                    <span className={cn(
                      "font-medium",
                      result.deleted > 0
                        ? "text-green-600 dark:text-green-400"
                        : "text-gray-500"
                    )}>
                      {result.deleted > 0 ? `${result.deleted.toLocaleString()} deleted` : 'No old records'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Database Info */}
      <div className={cn(
        "card settings-card",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.7s' }}>
        <div className="card-header">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gray-500/10">
              <Database className="w-5 h-5 text-gray-500 category-icon" />
            </div>
            <div>
              <h2 className="card-title">Database Information</h2>
              <p className="text-sm text-gray-500 font-normal">Connection and storage details</p>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mt-4">
          <div className="db-info-item">
            <div className="text-sm text-gray-500 mb-1">Provider</div>
            <div className="text-gray-900 dark:text-white font-medium flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              Supabase
            </div>
          </div>
          <div className="db-info-item">
            <div className="text-sm text-gray-500 mb-1">Database</div>
            <div className="text-gray-900 dark:text-white font-medium">PostgreSQL</div>
          </div>
          <div className="db-info-item">
            <div className="text-sm text-gray-500 mb-1">Tables Prefix</div>
            <div className="text-gray-900 dark:text-white font-medium font-mono">trading_*</div>
          </div>
          <div className="db-info-item">
            <div className="text-sm text-gray-500 mb-1">RLS Enabled</div>
            <div className="text-green-500 font-medium flex items-center gap-1">
              <CheckCircle className="w-4 h-4" />
              Yes
            </div>
          </div>
          <div className="db-info-item">
            <div className="text-sm text-gray-500 mb-1">Trading Tables Size</div>
            <div className="text-gray-900 dark:text-white font-medium">
              {dbStats?.tradingTablesSizeMB ? `${dbStats.tradingTablesSizeMB} MB` : '—'}
            </div>
          </div>
          <div className="db-info-item">
            <div className="text-sm text-gray-500 mb-1">Total DB Size</div>
            <div className="text-gray-900 dark:text-white font-medium">
              {dbStats?.totalDatabaseSizeMB ? `${dbStats.totalDatabaseSizeMB} MB` : '—'}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Tips */}
      <div className={cn(
        "bg-gradient-to-r from-green-500/5 to-blue-500/5 border border-green-500/10 rounded-lg p-4",
        mounted && "animate-fade-in-up"
      )} style={{ animationDelay: '0.8s' }}>
        <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2">
          <Info className="w-4 h-4 text-green-500" />
          Quick Tips
        </h3>
        <ul className="text-sm text-gray-500 space-y-1">
          <li>• Settings are synced with the trading bot every 15 minutes</li>
          <li>• Paper trading mode allows you to test strategies without real money</li>
          <li>• Set stop loss and take profit to manage risk automatically</li>
          <li>• Lower confidence threshold means more trades, but potentially riskier decisions</li>
        </ul>
      </div>
    </div>
  )
}
