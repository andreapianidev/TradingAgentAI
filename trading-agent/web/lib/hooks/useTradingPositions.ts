import { useEffect, useState, useCallback } from 'react'
import { supabase, TradingPosition } from '@/lib/supabase'

const SYNC_INTERVAL = 30000 // 30 seconds

export interface UseTradingPositionsOptions {
  filter?: 'all' | 'open' | 'closed'
  symbolFilter?: string
  autoSync?: boolean
  limit?: number
}

export interface UseTradingPositionsReturn {
  positions: TradingPosition[]
  loading: boolean
  syncing: boolean
  lastSync: Date | null
  syncError: string | null
  syncPositions: (showLoading?: boolean) => Promise<void>
  refreshPositions: () => Promise<void>
  closePosition: (positionId: string) => Promise<boolean>
}

export function useTradingPositions(options: UseTradingPositionsOptions = {}): UseTradingPositionsReturn {
  const {
    filter = 'all',
    symbolFilter = 'all',
    autoSync = true,
    limit = 100
  } = options

  const [positions, setPositions] = useState<TradingPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState<Date | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

  // Sync positions from Alpaca
  const syncPositions = useCallback(async (showLoading = true) => {
    if (showLoading) setSyncing(true)
    setSyncError(null)

    try {
      const res = await fetch('/api/positions/sync', { method: 'POST' })
      const data = await res.json()

      if (data.success) {
        setLastSync(new Date())
        console.log('Positions synced:', data.results)
      } else {
        setSyncError(data.error || 'Sync failed')
      }
    } catch (error) {
      console.error('Error syncing positions:', error)
      setSyncError('Network error')
    } finally {
      setSyncing(false)
    }
  }, [])

  // Fetch positions from database
  const fetchPositions = useCallback(async () => {
    setLoading(true)
    try {
      let query = supabase
        .from('trading_positions')
        .select('*')
        .order('entry_timestamp', { ascending: false })

      if (filter !== 'all') {
        query = query.eq('status', filter)
      }

      if (symbolFilter !== 'all') {
        query = query.eq('symbol', symbolFilter)
      }

      const { data } = await query.limit(limit)
      setPositions(data || [])
    } catch (error) {
      console.error('Error fetching positions:', error)
    } finally {
      setLoading(false)
    }
  }, [filter, symbolFilter, limit])

  // Close a position
  const closePosition = useCallback(async (positionId: string): Promise<boolean> => {
    if (!confirm('Are you sure you want to close this position?')) return false

    try {
      const res = await fetch('/api/positions/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position_id: positionId })
      })

      if (res.ok) {
        await fetchPositions()
        return true
      }
      return false
    } catch (error) {
      console.error('Failed to close position:', error)
      return false
    }
  }, [fetchPositions])

  // Initial sync and fetch
  useEffect(() => {
    const init = async () => {
      if (autoSync) {
        await syncPositions(true)
      }
      await fetchPositions()
    }
    init()
  }, [])

  // Auto-sync every 30 seconds
  useEffect(() => {
    if (!autoSync) return

    const interval = setInterval(async () => {
      await syncPositions(false)
      await fetchPositions()
    }, SYNC_INTERVAL)

    return () => clearInterval(interval)
  }, [syncPositions, fetchPositions, autoSync])

  // Fetch when filters change
  useEffect(() => {
    fetchPositions()
  }, [filter, symbolFilter])

  return {
    positions,
    loading,
    syncing,
    lastSync,
    syncError,
    syncPositions,
    refreshPositions: fetchPositions,
    closePosition
  }
}
