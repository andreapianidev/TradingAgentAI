'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  TrendingUp,
  History,
  BarChart3,
  Settings,
  Bot,
  Wallet
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Positions', href: '/positions', icon: TrendingUp },
  { name: 'Trade History', href: '/history', icon: History },
  { name: 'Market Analysis', href: '/market', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()

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
            <span className="text-sm text-gray-400">Paper Trading</span>
          </div>
          <div className="text-2xl font-bold text-white">$10,000.00</div>
          <div className="text-sm text-green-500">+0.00%</div>
        </div>
      </div>
    </div>
  )
}
