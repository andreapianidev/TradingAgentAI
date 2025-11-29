import { cn, formatCurrency, getPnlColor } from '@/lib/utils'
import { Activity, TrendingUp, CheckCircle, BarChart3 } from 'lucide-react'

interface PositionStatsCardsProps {
  stats: {
    total: number
    open: number
    closed: number
    unrealizedPnl: number
  }
  mounted?: boolean
}

export default function PositionStatsCards({ stats, mounted = true }: PositionStatsCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div
        className={cn(
          "stat-card stat-card-enhanced group cursor-default",
          mounted && "animate-fade-in-up"
        )}
        style={{ animationDelay: '0.15s' }}
      >
        <div className="flex items-center justify-between">
          <div className="stat-label">Total Positions</div>
          <div className="p-2 rounded-lg bg-gray-800/50 group-hover:bg-gray-700/50 transition-colors">
            <Activity className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors icon-bounce" />
          </div>
        </div>
        <div className="stat-value animate-count">{stats.total}</div>
      </div>

      <div
        className={cn(
          "stat-card stat-card-enhanced group cursor-default",
          mounted && "animate-fade-in-up"
        )}
        style={{ animationDelay: '0.2s' }}
      >
        <div className="flex items-center justify-between">
          <div className="stat-label">Open</div>
          <div className="p-2 rounded-lg bg-green-500/10 group-hover:bg-green-500/20 transition-colors">
            <TrendingUp className="w-4 h-4 text-green-500 group-hover:scale-110 transition-transform icon-bounce" />
          </div>
        </div>
        <div className="stat-value text-green-500 animate-count">{stats.open}</div>
      </div>

      <div
        className={cn(
          "stat-card stat-card-enhanced group cursor-default",
          mounted && "animate-fade-in-up"
        )}
        style={{ animationDelay: '0.25s' }}
      >
        <div className="flex items-center justify-between">
          <div className="stat-label">Closed</div>
          <div className="p-2 rounded-lg bg-blue-500/10 group-hover:bg-blue-500/20 transition-colors">
            <CheckCircle className="w-4 h-4 text-blue-500 group-hover:scale-110 transition-transform icon-bounce" />
          </div>
        </div>
        <div className="stat-value text-blue-500 animate-count">{stats.closed}</div>
      </div>

      <div
        className={cn(
          "stat-card stat-card-enhanced group cursor-default",
          mounted && "animate-fade-in-up"
        )}
        style={{ animationDelay: '0.3s' }}
      >
        <div className="flex items-center justify-between">
          <div className="stat-label">Unrealized P&L</div>
          <div className={cn(
            "p-2 rounded-lg transition-colors",
            stats.unrealizedPnl >= 0
              ? "bg-green-500/10 group-hover:bg-green-500/20"
              : "bg-red-500/10 group-hover:bg-red-500/20"
          )}>
            <BarChart3 className={cn(
              "w-4 h-4 group-hover:scale-110 transition-transform icon-bounce",
              stats.unrealizedPnl >= 0 ? "text-green-500" : "text-red-500"
            )} />
          </div>
        </div>
        <div className={cn(
          'stat-value animate-count',
          getPnlColor(stats.unrealizedPnl),
          stats.unrealizedPnl > 0 && 'pnl-positive'
        )}>
          {stats.unrealizedPnl >= 0 ? '+' : ''}{formatCurrency(stats.unrealizedPnl)}
        </div>
      </div>
    </div>
  )
}
