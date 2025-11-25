'use client'

import { useState, useEffect } from 'react'
import { Bell, Play, Square, RefreshCw, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Header() {
  const [botActive, setBotActive] = useState(false)
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [alertCount, setAlertCount] = useState(0)

  useEffect(() => {
    // Fetch initial state
    fetchBotStatus()
    const interval = setInterval(fetchBotStatus, 30000) // Every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchBotStatus = async () => {
    try {
      const res = await fetch('/api/status')
      if (res.ok) {
        const data = await res.json()
        setBotActive(data.bot_active || false)
        setTradingMode(data.trading_mode || 'paper')
        setLastUpdate(new Date())
        setAlertCount(data.unread_alerts || 0)
      }
    } catch (error) {
      console.error('Failed to fetch bot status:', error)
    }
  }

  const toggleBot = async () => {
    try {
      const res = await fetch('/api/bot/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !botActive })
      })
      if (res.ok) {
        setBotActive(!botActive)
      }
    } catch (error) {
      console.error('Failed to toggle bot:', error)
    }
  }

  const runCycle = async () => {
    try {
      const res = await fetch('/api/bot/run', { method: 'POST' })
      if (res.ok) {
        setLastUpdate(new Date())
      }
    } catch (error) {
      console.error('Failed to run cycle:', error)
    }
  }

  return (
    <header className="h-16 bg-gray-900/50 backdrop-blur-sm border-b border-gray-800 px-6 flex items-center justify-between">
      {/* Left section */}
      <div className="flex items-center gap-4">
        <div className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium',
          tradingMode === 'paper'
            ? 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20'
            : 'bg-green-500/10 text-green-500 border border-green-500/20'
        )}>
          <Zap className="w-4 h-4" />
          {tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}
        </div>

        <div className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
          botActive
            ? 'bg-green-500/10 text-green-500'
            : 'bg-gray-500/10 text-gray-500'
        )}>
          <span className={cn(
            'w-2 h-2 rounded-full',
            botActive ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
          )} />
          {botActive ? 'Bot Active' : 'Bot Inactive'}
        </div>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        {lastUpdate && (
          <span className="text-xs text-gray-500">
            Last update: {lastUpdate.toLocaleTimeString()}
          </span>
        )}

        <button
          onClick={runCycle}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          title="Run trading cycle"
        >
          <RefreshCw className="w-5 h-5" />
        </button>

        <button
          onClick={toggleBot}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
            botActive
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-green-600 hover:bg-green-700 text-white'
          )}
        >
          {botActive ? (
            <>
              <Square className="w-4 h-4" />
              Stop Bot
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Start Bot
            </>
          )}
        </button>

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
