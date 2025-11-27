import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

function getSupabaseClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables')
  }

  return createClient(supabaseUrl, supabaseKey)
}

interface CleanupResult {
  table: string
  deleted: number
  retention: string
  error?: string
}

export async function POST(request: Request) {
  try {
    const { dryRun = false } = await request.json().catch(() => ({ dryRun: false }))
    const supabase = getSupabaseClient()
    const results: CleanupResult[] = []

    // Define retention policies (in days)
    const retentionPolicies = [
      { table: 'trading_bot_logs', days: 7, timestampCol: 'created_at' },
      { table: 'trading_market_contexts', days: 30, timestampCol: 'timestamp' },
      { table: 'trading_news', days: 30, timestampCol: 'created_at' },
      { table: 'trading_alerts', days: 30, timestampCol: 'created_at' },
      { table: 'trading_whale_alerts', days: 30, timestampCol: 'timestamp' },
      { table: 'trading_market_global', days: 30, timestampCol: 'timestamp' },
    ]

    for (const policy of retentionPolicies) {
      try {
        const cutoffDate = new Date()
        cutoffDate.setDate(cutoffDate.getDate() - policy.days)
        const cutoffISO = cutoffDate.toISOString()

        if (dryRun) {
          // Count records that would be deleted
          const { count, error } = await supabase
            .from(policy.table)
            .select('*', { count: 'exact', head: true })
            .lt(policy.timestampCol, cutoffISO)

          if (error) throw error

          results.push({
            table: policy.table,
            deleted: count || 0,
            retention: `${policy.days} days`,
          })
        } else {
          // Actually delete old records
          const { data, error } = await supabase
            .from(policy.table)
            .delete()
            .lt(policy.timestampCol, cutoffISO)
            .select()

          if (error) throw error

          results.push({
            table: policy.table,
            deleted: data?.length || 0,
            retention: `${policy.days} days`,
          })

          console.log(`Cleaned up ${data?.length || 0} records from ${policy.table} (older than ${policy.days} days)`)
        }
      } catch (error) {
        console.error(`Error cleaning ${policy.table}:`, error)
        results.push({
          table: policy.table,
          deleted: 0,
          retention: `${policy.days} days`,
          error: error instanceof Error ? error.message : 'Unknown error'
        })
      }
    }

    // Calculate summary
    const totalDeleted = results.reduce((sum, r) => sum + r.deleted, 0)
    const hasErrors = results.some(r => r.error)

    return NextResponse.json({
      success: !hasErrors,
      dryRun,
      message: dryRun
        ? `Dry run: Would delete ${totalDeleted} records`
        : `Cleanup complete: Deleted ${totalDeleted} records`,
      results,
      totalDeleted,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Database cleanup error:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to cleanup database'
      },
      { status: 500 }
    )
  }
}

export async function GET() {
  // Get current database stats
  try {
    const supabase = getSupabaseClient()
    const tables = [
      'trading_bot_logs',
      'trading_market_contexts',
      'trading_news',
      'trading_alerts',
      'trading_decisions',
      'trading_positions',
      'trading_portfolio_snapshots',
      'trading_costs'
    ]

    const stats = await Promise.all(
      tables.map(async (table) => {
        const { count, error } = await supabase
          .from(table)
          .select('*', { count: 'exact', head: true })

        return {
          table,
          records: error ? 0 : (count || 0)
        }
      })
    )

    return NextResponse.json({
      success: true,
      stats,
      totalRecords: stats.reduce((sum, s) => sum + s.records, 0)
    })
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get stats'
      },
      { status: 500 }
    )
  }
}
