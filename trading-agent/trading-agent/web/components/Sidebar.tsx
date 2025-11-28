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
  Terminal,
  X,
  Menu,
  DollarSign,
  MessageSquare
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { supabase } from '@/lib/supabase'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Bot Console', href: '/bot', icon: Terminal },
  { name: 'Conversations', href: '/conversations', icon: MessageSquare },
  { name: 'Positions', href: '/positions', icon: TrendingUp },
  { name: 'Trade History', href: '/history', icon: History },
  { name: 'Market Analysis', href: '/market', icon: BarChart3 },
  { name: 'Costs', href: '/costs', icon: DollarSign },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [equity, setEquity] = useState<number | null>(null)
  const [pnlPct, setPnlPct] = useState<number>(0)
  const [tradingMode, setTradingMode] = useState<string>('paper')
  const [isOpen, setIsOpen] = useState(false)

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

  // Close sidebar when route changes on mobile
  useEffect(() => {
    setIsOpen(false)
  }, [pathname])

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-white dark:bg-gray-800 shadow-lg border border-gray-200 dark:border-gray-700"
      >
        <Menu className="w-5 h-5 text-gray-600 dark:text-gray-300" />
      </button>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={cn(
        "fixed lg:relative inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-900/80 backdrop-blur-sm border-r border-gray-200 dark:border-gray-800 flex flex-col transition-transform duration-300 lg:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Close button - mobile only */}
        <button
          onClick={() => setIsOpen(false)}
          className="lg:hidden absolute top-4 right-4 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        </button>

        {/* Logo */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 dark:text-white">Trading Bot</h1>
              <p className="text-xs text-gray-500">AI-Powered</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                  isActive
                    ? 'bg-green-500/10 text-green-600 dark:text-green-500 border border-green-500/20'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.name}</span>
              </Link>
            )
          })}
        </nav>

        {/* Bottom section */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <div className="bg-gray-100 dark:bg-gray-800/50 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <Wallet className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              <span className={cn(
                "text-sm font-medium",
                tradingMode === 'paper' ? "text-yellow-600 dark:text-yellow-500" : "text-green-600 dark:text-green-500"
              )}>
                {tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}
              </span>
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {equity !== null ? `$${equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
            </div>
            <div className={cn(
              "text-sm font-medium",
              pnlPct >= 0 ? "text-green-600 dark:text-green-500" : "text-red-600 dark:text-red-500"
            )}>
              {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
