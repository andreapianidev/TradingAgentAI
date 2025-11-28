import { useEffect, useState, useCallback } from 'react'
import { supabase, TradingPortfolioSnapshot } from '@/lib/supabase'

const INITIAL_CAPITAL = 100000 // Starting capital for P&L calculations

export interface PortfolioStats {
  totalEquity: number
  totalPnl: number
  totalPnlPct: number
  unrealizedPnl: number
  investedValue: number
  exposurePct: number
}

export interface UsePortfolioStatsReturn {
  portfolioStats: PortfolioStats | null
  loading: boolean
  refreshStats: () => Promise<void>
}

export function usePortfolioStats(): UsePortfolioStatsReturn {
  const [portfolioStats, setPortfolioStats] = useState<PortfolioStats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchPortfolioStats = useCallback(async () => {
    setLoading(true)
    try {
      // Try live API first
      const liveRes = await fetch('/api/account/live')
      const liveData = await liveRes.json()

      if (liveData.success && liveData.account) {
        const equity = liveData.account.equity
        const totalPnl = equity - INITIAL_CAPITAL
        setPortfolioStats({
          totalEquity: equity,
          totalPnl: totalPnl,
          totalPnlPct: (totalPnl / INITIAL_CAPITAL) * 100,
          unrealizedPnl: liveData.account.totalUnrealizedPnl || 0,
          investedValue: liveData.account.positionsValue || 0,
          exposurePct: liveData.account.exposurePct || 0,
        })
        return
      }

      // Fallback to database snapshot
      const { data: snapshot } = await supabase
        .from('trading_portfolio_snapshots')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(1)
        .single()

      if (snapshot) {
        const equity = parseFloat(String(snapshot.total_equity_usdc)) || INITIAL_CAPITAL
        const totalPnl = equity - INITIAL_CAPITAL

        // Calculate invested value from positions
        const { data: openPositions } = await supabase
          .from('trading_positions')
          .select('entry_price, quantity')
          .eq('status', 'open')

        const investedValue = openPositions?.reduce((sum, p) => {
          return sum + (parseFloat(String(p.entry_price)) * parseFloat(String(p.quantity)))
        }, 0) || 0

        // Calculate unrealized P&L from open positions
        const { data: openPnl } = await supabase
          .from('trading_positions')
          .select('unrealized_pnl')
          .eq('status', 'open')

        const unrealizedPnl = openPnl?.reduce((sum, p) => {
          return sum + (parseFloat(String(p.unrealized_pnl || 0)))
        }, 0) || 0

        setPortfolioStats({
          totalEquity: equity,
          totalPnl: totalPnl,
          totalPnlPct: (totalPnl / INITIAL_CAPITAL) * 100,
          unrealizedPnl: unrealizedPnl,
          investedValue: investedValue,
          exposurePct: parseFloat(String(snapshot.exposure_pct)) || 0,
        })
      }
    } catch (error) {
      console.error('Error fetching portfolio stats:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPortfolioStats()
  }, [fetchPortfolioStats])

  return {
    portfolioStats,
    loading,
    refreshStats: fetchPortfolioStats
  }
}
