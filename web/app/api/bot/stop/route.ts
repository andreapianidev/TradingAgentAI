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

export async function POST() {
  try {
    const supabase = getSupabaseClient()
    const githubToken = process.env.GITHUB_TOKEN
    const repoOwner = process.env.GITHUB_REPO_OWNER || 'andreapianidev'
    const repoName = process.env.GITHUB_REPO_NAME || 'TradingAgentAI'
    const workflowId = process.env.GITHUB_WORKFLOW_ID || 'trading-bot.yml'

    if (!githubToken) {
      return NextResponse.json({
        success: false,
        error: 'GitHub token not configured'
      }, { status: 500 })
    }

    // Find running workflow
    const listResponse = await fetch(
      `https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/${workflowId}/runs?status=in_progress&per_page=5`,
      {
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': `Bearer ${githubToken}`,
        }
      }
    )

    if (!listResponse.ok) {
      return NextResponse.json({
        success: false,
        error: 'Failed to fetch running workflows'
      }, { status: 500 })
    }

    const data = await listResponse.json()
    const runningWorkflows = data.workflow_runs || []

    if (runningWorkflows.length === 0) {
      return NextResponse.json({
        success: false,
        error: 'No running workflow to stop',
        isRunning: false
      }, { status: 400 })
    }

    // Cancel all running workflows
    let cancelledCount = 0
    for (const run of runningWorkflows) {
      const cancelResponse = await fetch(
        `https://api.github.com/repos/${repoOwner}/${repoName}/actions/runs/${run.id}/cancel`,
        {
          method: 'POST',
          headers: {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': `Bearer ${githubToken}`,
          }
        }
      )

      if (cancelResponse.ok || cancelResponse.status === 202) {
        cancelledCount++
      }
    }

    // Log the stop action
    await supabase.from('trading_bot_logs').insert({
      log_level: 'WARNING',
      message: `Trading bot workflow cancelled from dashboard (${cancelledCount} runs stopped)`,
      component: 'Dashboard',
      trading_mode: 'paper'
    })

    // Create alert
    await supabase.from('trading_alerts').insert({
      alert_type: 'bot_stopped',
      severity: 'warning',
      title: 'Bot Workflow Cancelled',
      message: `${cancelledCount} running workflow(s) have been cancelled.`,
      trading_mode: 'paper'
    })

    return NextResponse.json({
      success: true,
      message: `Cancelled ${cancelledCount} running workflow(s)`,
      isRunning: false
    })
  } catch (error) {
    console.error('Error stopping bot:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to stop trading bot' },
      { status: 500 }
    )
  }
}
