import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

export const dynamic = 'force-dynamic'

function getSupabaseClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables')
  }

  return createClient(supabaseUrl, supabaseKey)
}

interface WorkflowRun {
  id: number
  status: string
  conclusion: string | null
  created_at: string
  updated_at: string
  run_started_at: string
  html_url: string
}

export async function GET() {
  try {
    const supabase = getSupabaseClient()
    const githubToken = process.env.GITHUB_TOKEN
    const repoOwner = process.env.GITHUB_REPO_OWNER || 'andreapianidev'
    const repoName = process.env.GITHUB_REPO_NAME || 'TradingAgentAI'
    const workflowId = process.env.GITHUB_WORKFLOW_ID || 'trading-bot.yml'

    let workflowStatus = {
      isRunning: false,
      lastRun: null as WorkflowRun | null,
      nextScheduledRun: null as string | null,
      error: null as string | null
    }

    // Fetch workflow runs from GitHub
    if (githubToken) {
      try {
        const response = await fetch(
          `https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/${workflowId}/runs?per_page=5`,
          {
            headers: {
              'Accept': 'application/vnd.github.v3+json',
              'Authorization': `Bearer ${githubToken}`,
            },
            next: { revalidate: 30 } // Cache for 30 seconds
          }
        )

        if (response.ok) {
          const data = await response.json()
          const runs = data.workflow_runs || []

          if (runs.length > 0) {
            const latestRun = runs[0]
            workflowStatus.lastRun = {
              id: latestRun.id,
              status: latestRun.status,
              conclusion: latestRun.conclusion,
              created_at: latestRun.created_at,
              updated_at: latestRun.updated_at,
              run_started_at: latestRun.run_started_at,
              html_url: latestRun.html_url
            }
            workflowStatus.isRunning = latestRun.status === 'in_progress' || latestRun.status === 'queued'
          }

          // Calculate next scheduled run (every 15 minutes)
          const now = new Date()
          const minutes = now.getMinutes()
          const nextRunMinutes = Math.ceil(minutes / 15) * 15
          const nextRun = new Date(now)
          nextRun.setMinutes(nextRunMinutes, 0, 0)
          if (nextRun <= now) {
            nextRun.setMinutes(nextRun.getMinutes() + 15)
          }
          workflowStatus.nextScheduledRun = nextRun.toISOString()
        }
      } catch (ghError) {
        console.error('GitHub API error:', ghError)
        workflowStatus.error = 'Failed to fetch GitHub workflow status'
      }
    } else {
      workflowStatus.error = 'GITHUB_TOKEN not configured'
    }

    // Get latest portfolio snapshot from Supabase
    const { data: snapshot } = await supabase
      .from('trading_portfolio_snapshots')
      .select('*')
      .order('timestamp', { ascending: false })
      .limit(1)
      .single()

    // Get open positions count
    const { count: openPositions } = await supabase
      .from('trading_positions')
      .select('*', { count: 'exact', head: true })
      .eq('status', 'open')

    // Get latest cycle
    const { data: latestCycle } = await supabase
      .from('trading_cycles')
      .select('*')
      .order('started_at', { ascending: false })
      .limit(1)
      .single()

    return NextResponse.json({
      workflow: workflowStatus,
      isRunning: workflowStatus.isRunning,
      lastRun: workflowStatus.lastRun,
      nextScheduledRun: workflowStatus.nextScheduledRun,
      latestCycle,
      portfolio: snapshot ? {
        equity: snapshot.total_equity_usdc || 0,
        available: snapshot.available_balance_usdc || 0,
        exposure: snapshot.exposure_pct || 0,
        positions: openPositions || 0
      } : null
    })
  } catch (error) {
    console.error('Error fetching bot status:', error)
    return NextResponse.json(
      {
        isRunning: false,
        error: 'Failed to fetch bot status'
      },
      { status: 500 }
    )
  }
}
