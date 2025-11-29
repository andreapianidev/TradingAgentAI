import { cn, formatCurrency } from '@/lib/utils'
import { Wallet, TrendingUp, TrendingDown } from 'lucide-react'
import { PortfolioStats } from '@/lib/hooks/usePortfolioStats'

interface PortfolioOverviewProps {
  portfolioStats: PortfolioStats | null
  stats: {
    investedValue: number
    unrealizedPnl: number
    exposurePct: number
    open: number
    totalPnl: number
    totalPnlPct: number
  }
  mounted?: boolean
  animationDelay?: string
}

export default function PortfolioOverview({ portfolioStats, stats, mounted = true, animationDelay = '0.1s' }: PortfolioOverviewProps) {
  if (!portfolioStats) return null

  return (
    <div
      className={cn(
        "card p-4 bg-gradient-to-r from-gray-900/80 to-gray-800/50 border-gray-700/50",
        mounted && "animate-fade-in-up"
      )}
      style={{ animationDelay }}
    >
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className={cn(
            "p-3 rounded-xl",
            stats.totalPnl >= 0 ? "bg-green-500/10" : "bg-red-500/10"
          )}>
            <Wallet className={cn(
              "w-8 h-8",
              stats.totalPnl >= 0 ? "text-green-500" : "text-red-500"
            )} />
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Portfolio Value</div>
            <div className="text-2xl font-bold text-white">
              {formatCurrency(portfolioStats.totalEquity)}
            </div>
            <div className={cn(
              "flex items-center gap-1 text-sm font-medium",
              stats.totalPnl >= 0 ? "text-green-500" : "text-red-500"
            )}>
              {stats.totalPnl >= 0 ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              <span>{stats.totalPnl >= 0 ? '+' : ''}{formatCurrency(stats.totalPnl)}</span>
              <span className="text-gray-500">({stats.totalPnlPct >= 0 ? '+' : ''}{stats.totalPnlPct.toFixed(2)}%)</span>
              <span className="text-xs text-gray-500 ml-1">total</span>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-800/50 rounded-lg">
            <div className="text-xs text-gray-500">Invested</div>
            <div className="text-lg font-bold text-white">{formatCurrency(stats.investedValue)}</div>
          </div>
          <div className="text-center p-3 bg-gray-800/50 rounded-lg">
            <div className="text-xs text-gray-500">Unrealized P&L</div>
            <div className={cn(
              "text-lg font-bold",
              stats.unrealizedPnl >= 0 ? "text-green-500" : "text-red-500"
            )}>
              {stats.unrealizedPnl >= 0 ? '+' : ''}{formatCurrency(stats.unrealizedPnl)}
            </div>
          </div>
          <div className="text-center p-3 bg-gray-800/50 rounded-lg">
            <div className="text-xs text-gray-500">Exposure</div>
            <div className="text-lg font-bold text-white">{stats.exposurePct.toFixed(1)}%</div>
          </div>
          <div className="text-center p-3 bg-gray-800/50 rounded-lg">
            <div className="text-xs text-gray-500">Open Positions</div>
            <div className="text-lg font-bold text-green-500">{stats.open}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
