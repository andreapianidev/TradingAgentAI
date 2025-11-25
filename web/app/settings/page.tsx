'use client'

import { useEffect, useState } from 'react'
import { supabase, TradingSetting } from '@/lib/supabase'
import { cn } from '@/lib/utils'
import {
  Settings,
  Save,
  RefreshCw,
  Shield,
  Zap,
  Bell,
  Database,
  AlertTriangle
} from 'lucide-react'

interface SettingsGroup {
  category: string
  icon: React.ReactNode
  settings: TradingSetting[]
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<TradingSetting[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [changes, setChanges] = useState<Record<string, any>>({})
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    fetchSettings()
  }, [])

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
      setMessage({ type: 'success', text: 'Settings saved successfully!' })
      setChanges({})
      fetchSettings()
    } catch (error) {
      console.error('Error saving settings:', error)
      setMessage({ type: 'error', text: 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

  const getValue = (setting: TradingSetting) => {
    if (changes.hasOwnProperty(setting.setting_key)) {
      return changes[setting.setting_key]
    }
    // Handle null/undefined setting_value
    if (setting.setting_value === null || setting.setting_value === undefined) {
      return ''
    }
    try {
      return JSON.parse(setting.setting_value)
    } catch {
      return setting.setting_value
    }
  }

  const groupedSettings: SettingsGroup[] = [
    {
      category: 'general',
      icon: <Settings className="w-5 h-5 text-blue-500" />,
      settings: settings.filter(s => s.category === 'general')
    },
    {
      category: 'trading',
      icon: <Zap className="w-5 h-5 text-green-500" />,
      settings: settings.filter(s => s.category === 'trading')
    },
    {
      category: 'risk',
      icon: <Shield className="w-5 h-5 text-orange-500" />,
      settings: settings.filter(s => s.category === 'risk')
    }
  ]

  const renderSettingInput = (setting: TradingSetting) => {
    const value = getValue(setting)
    const key = setting.setting_key

    // Boolean settings
    if (typeof value === 'boolean' || value === 'true' || value === 'false') {
      const boolValue = value === true || value === 'true'
      return (
        <button
          onClick={() => handleChange(key, !boolValue)}
          className={cn(
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
            boolValue ? 'bg-green-600' : 'bg-gray-600'
          )}
        >
          <span
            className={cn(
              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
              boolValue ? 'translate-x-6' : 'translate-x-1'
            )}
          />
        </button>
      )
    }

    // Array settings (like target_symbols)
    if (Array.isArray(value)) {
      return (
        <input
          type="text"
          value={value.join(', ')}
          onChange={(e) => handleChange(key, e.target.value.split(',').map(s => s.trim()))}
          className="input"
        />
      )
    }

    // Number settings
    if (typeof value === 'number' || (!isNaN(Number(value)) && value !== '')) {
      return (
        <input
          type="number"
          value={value ?? ''}
          onChange={(e) => handleChange(key, parseFloat(e.target.value) || 0)}
          className="input w-32"
          step={key.includes('pct') || key.includes('threshold') ? '0.1' : '1'}
        />
      )
    }

    // String settings
    return (
      <input
        type="text"
        value={value || ''}
        onChange={(e) => handleChange(key, e.target.value)}
        className="input"
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-gray-400">Configure your trading bot parameters</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchSettings}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={saveSettings}
            disabled={Object.keys(changes).length === 0 || saving}
            className="btn btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={cn(
          'p-4 rounded-lg flex items-center gap-2',
          message.type === 'success' ? 'bg-green-500/10 text-green-500 border border-green-500/20' :
          'bg-red-500/10 text-red-500 border border-red-500/20'
        )}>
          {message.type === 'success' ? (
            <Save className="w-5 h-5" />
          ) : (
            <AlertTriangle className="w-5 h-5" />
          )}
          {message.text}
        </div>
      )}

      {/* Warning Banner */}
      <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="text-yellow-500 font-medium">Paper Trading Mode Active</h4>
          <p className="text-yellow-500/80 text-sm mt-1">
            The bot is currently running in paper trading mode. No real trades will be executed.
            Change the "Paper Trading Enabled" setting to switch to live trading.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
        </div>
      ) : (
        <div className="space-y-6">
          {groupedSettings.map((group) => (
            <div key={group.category} className="card">
              <div className="card-header">
                <h2 className="card-title flex items-center gap-2">
                  {group.icon}
                  {group.category.charAt(0).toUpperCase() + group.category.slice(1)} Settings
                </h2>
              </div>
              <div className="space-y-4">
                {group.settings.map((setting) => (
                  <div
                    key={setting.setting_key}
                    className="flex items-center justify-between py-3 border-b border-gray-800 last:border-0"
                  >
                    <div className="flex-1">
                      <div className="text-white font-medium">
                        {formatLabel(setting.setting_key)}
                      </div>
                      {setting.description && (
                        <div className="text-sm text-gray-500 mt-0.5">
                          {setting.description}
                        </div>
                      )}
                    </div>
                    <div className="ml-4">
                      {renderSettingInput(setting)}
                    </div>
                  </div>
                ))}
                {group.settings.length === 0 && (
                  <div className="text-gray-500 text-center py-4">
                    No settings in this category
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Database Info */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title flex items-center gap-2">
            <Database className="w-5 h-5 text-gray-500" />
            Database Information
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Database</div>
            <div className="text-white">Supabase PostgreSQL</div>
          </div>
          <div>
            <div className="text-gray-500">Tables Prefix</div>
            <div className="text-white">trading_*</div>
          </div>
          <div>
            <div className="text-gray-500">RLS Enabled</div>
            <div className="text-green-500">Yes</div>
          </div>
        </div>
      </div>
    </div>
  )
}
