'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  TrendingUp,
  History,
  BarChart3,
  Settings,
  Bot,
  Wallet,
  Terminal
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { supabase } from '@/lib/supabase'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Bot Console', href: '/bot', icon: Terminal },
  { name: 'Positions', href: '/positions', icon: TrendingUp },
  { name: 'Trade History', href: '/history', icon: History },
  { name: 'Market Analysis', href: '/market', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [equity, setEquity] = useState<number | null>(null)
  const [pnlPct, setPnlPct] = useState<number>(0)
  const [tradingMode, setTradingMode] = useState<string>('paper')

  useEffect(() => {
    const fetchPortfolio = async () => {
      const { data } = await supabase
        .from('trading_portfolio_snapshots')
        .select('total_equity_usdc, total_pnl_pct, trading_mode')
        .order('timestamp', { ascending: false })
        .limit(1)
        .single()

      if (data) {
        setEquity(parseFloat(data.total_equity_usdc))
        setPnlPct(parseFloat(data.total_pnl_pct) || 0)
        setTradingMode(data.trading_mode || 'paper')
      }
    }

    fetchPortfolio()
    const interval = setInterval(fetchPortfolio, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="w-64 bg-gray-900/80 backdrop-blur-sm border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Trading Bot</h1>
            <p className="text-xs text-gray-500">AI-Powered</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                isActive
                  ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              )}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>

      {/* Bottom section */}
      <div className="p-4 border-t border-gray-800">
        <div className="bg-gray-800/50 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-3">
            <Wallet className="w-5 h-5 text-gray-400" />
            <span className={cn(
              "text-sm",
              tradingMode === 'paper' ? "text-yellow-500" : "text-green-500"
            )}>
              {tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}
            </span>
          </div>
          <div className="text-2xl font-bold text-white">
            {equity !== null ? `$${equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
          </div>
          <div className={cn(
            "text-sm",
            pnlPct >= 0 ? "text-green-500" : "text-red-500"
          )}>
            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
          </div>
        </div>
      </div>
    </div>
  )
}
