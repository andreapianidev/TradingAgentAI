import { useState, useEffect, useCallback } from 'react'
import { supabase, TradingExchangeTransition, TradingPosition } from '@/lib/supabase'

interface UseTransitionDataReturn {
  transition: TradingExchangeTransition | null
  positions: TradingPosition[]
  loading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

export function useTransitionData(pollInterval = 10000): UseTransitionDataReturn {
  const [transition, setTransition] = useState<TradingExchangeTransition | null>(null)
  const [positions, setPositions] = useState<TradingPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchData = useCallback(async () => {
    try {
      // Get active transition
      const { data: transitionData, error: transError } = await supabase
        .from('trading_exchange_transitions')
        .select('*')
        .in('status', ['pending', 'in_progress'])
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle()

      if (transError) throw transError

      setTransition(transitionData)

      if (transitionData) {
        // Get positions in this transition
        const { data: positionsData, error: posError } = await supabase
          .from('trading_positions')
          .select('*')
          .eq('transition_id', transitionData.id)
          .eq('status', 'open')

        if (posError) throw posError
        setPositions(positionsData || [])
      } else {
        setPositions([])
      }

      setError(null)
    } catch (err) {
      setError(err as Error)
      console.error('Error fetching transition data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()

    // Poll for updates
    if (pollInterval > 0) {
      const interval = setInterval(fetchData, pollInterval)
      return () => clearInterval(interval)
    }
  }, [fetchData, pollInterval])

  return {
    transition,
    positions,
    loading,
    error,
    refresh: fetchData
  }
}
