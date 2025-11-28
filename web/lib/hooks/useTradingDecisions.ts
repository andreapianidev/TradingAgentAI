import { useEffect, useState, useCallback } from 'react'
import { supabase, TradingDecision } from '@/lib/supabase'

export interface UseTradingDecisionsOptions {
  actionFilter?: string
  symbolFilter?: string
  statusFilter?: string
  page?: number
  pageSize?: number
}

export interface UseTradingDecisionsReturn {
  decisions: TradingDecision[]
  loading: boolean
  totalCount: number
  page: number
  pageSize: number
  totalPages: number
  setPage: (page: number) => void
  refreshDecisions: () => Promise<void>
}

export function useTradingDecisions(options: UseTradingDecisionsOptions = {}): UseTradingDecisionsReturn {
  const {
    actionFilter = 'all',
    symbolFilter = 'all',
    statusFilter = 'all',
    page: initialPage = 1,
    pageSize = 20
  } = options

  const [decisions, setDecisions] = useState<TradingDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(initialPage)

  const fetchDecisions = useCallback(async () => {
    setLoading(true)
    try {
      let query = supabase
        .from('trading_decisions')
        .select('*', { count: 'exact' })
        .order('timestamp', { ascending: false })

      if (actionFilter !== 'all') {
        query = query.eq('action', actionFilter)
      }
      if (symbolFilter !== 'all') {
        query = query.eq('symbol', symbolFilter)
      }
      if (statusFilter !== 'all') {
        query = query.eq('execution_status', statusFilter)
      }

      const { data, count } = await query
        .range((page - 1) * pageSize, page * pageSize - 1)

      setDecisions(data || [])
      setTotalCount(count || 0)
    } catch (error) {
      console.error('Error fetching decisions:', error)
    } finally {
      setLoading(false)
    }
  }, [actionFilter, symbolFilter, statusFilter, page, pageSize])

  useEffect(() => {
    fetchDecisions()
  }, [fetchDecisions])

  const totalPages = Math.ceil(totalCount / pageSize)

  return {
    decisions,
    loading,
    totalCount,
    page,
    pageSize,
    totalPages,
    setPage,
    refreshDecisions: fetchDecisions
  }
}
