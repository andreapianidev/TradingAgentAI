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
      // Bot logs - differentiate by component
      {
        table: 'trading_bot_logs',
        days: 30,
        timestampCol: 'created_at',
        description: 'LLM conversations, errors, decisions',
        filter: (supabase: any, cutoff: string) =>
          supabase.from('trading_bot_logs')
            .delete()
            .lt('created_at', cutoff)
            .in('component', ['llm', 'errors', 'decisions', 'data.news_analyzer'])
            .select()
      },
      {
        table: 'trading_bot_logs',
        days: 7,
        timestampCol: 'created_at',
        description: 'General debug logs',
        filter: (supabase: any, cutoff: string) =>
          supabase.from('trading_bot_logs')
            .delete()
            .lt('created_at', cutoff)
            .not('component', 'in', '(llm,errors,decisions,data.news_analyzer)')
            .select()
      },
      // Other tables
      { table: 'trading_market_contexts', days: 30, timestampCol: 'timestamp', description: 'Technical analysis data' },
      { table: 'trading_news', days: 30, timestampCol: 'created_at', description: 'News articles' },
      { table: 'trading_alerts', days: 30, timestampCol: 'created_at', description: 'System alerts' },
      { table: 'trading_whale_alerts', days: 30, timestampCol: 'timestamp', description: 'Whale activity' },
      { table: 'trading_market_global', days: 30, timestampCol: 'timestamp', description: 'Market sentiment' },
    ]

    for (const policy of retentionPolicies) {
      try {
        const cutoffDate = new Date()
        cutoffDate.setDate(cutoffDate.getDate() - policy.days)
        const cutoffISO = cutoffDate.toISOString()

        if (dryRun) {
          // Count records that would be deleted
          let count = 0
          let error = null

          if ('filter' in policy && typeof policy.filter === 'function') {
            // Use custom filter for complex queries
            const query = policy.filter(supabase, cutoffISO)
            // For dry run with custom filter, we need to count differently
            // This is a limitation - we'll show 0 for now or implement count later
            count = 0
          } else {
            const result = await supabase
              .from(policy.table)
              .select('*', { count: 'exact', head: true })
              .lt(policy.timestampCol, cutoffISO)
            count = result.count || 0
            error = result.error
          }

          if (error) throw error

          results.push({
            table: `${policy.table}${policy.description ? ` (${policy.description})` : ''}`,
            deleted: count,
            retention: `${policy.days} days`,
          })
        } else {
          // Actually delete old records
          let data, error

          if ('filter' in policy && typeof policy.filter === 'function') {
            // Use custom filter function
            const result = await policy.filter(supabase, cutoffISO)
            data = result.data
            error = result.error
          } else {
            // Use default filter
            const result = await supabase
              .from(policy.table)
              .delete()
              .lt(policy.timestampCol, cutoffISO)
              .select()
            data = result.data
            error = result.error
          }

          if (error) throw error

          const deletedCount = data?.length || 0
          const tableName = `${policy.table}${policy.description ? ` (${policy.description})` : ''}`

          results.push({
            table: tableName,
            deleted: deletedCount,
            retention: `${policy.days} days`,
          })

          console.log(`Cleaned up ${deletedCount} records from ${tableName} (older than ${policy.days} days)`)
        }
      } catch (error) {
        const tableName = `${policy.table}${policy.description ? ` (${policy.description})` : ''}`
        console.error(`Error cleaning ${tableName}:`, error)
        results.push({
          table: tableName,
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

    // Get total database size
    let sizeData: any = null
    try {
      const result = await supabase
        .rpc('get_trading_tables_size')
        .single()
      sizeData = result.data
    } catch (error) {
      console.warn('Could not fetch database size:', error)
    }

    const totalSize = Number(sizeData?.trading_tables_size || 0)
    const totalDbSize = Number(sizeData?.total_database_size || 0)

    return NextResponse.json({
      success: true,
      stats,
      totalRecords: stats.reduce((sum, s) => sum + s.records, 0),
      tradingTablesSizeBytes: totalSize,
      tradingTablesSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
      totalDatabaseSizeBytes: totalDbSize,
      totalDatabaseSizeMB: (totalDbSize / (1024 * 1024)).toFixed(2),
      lastUpdated: new Date().toISOString()
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
