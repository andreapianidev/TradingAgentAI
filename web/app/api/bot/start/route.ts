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
        error: 'GitHub token not configured. Add GITHUB_TOKEN to environment variables.',
      }, { status: 500 })
    }

    // Trigger GitHub Actions workflow
    const response = await fetch(
      `https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/${workflowId}/dispatches`,
      {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': `Bearer ${githubToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ref: 'main'
        })
      }
    )

    if (!response.ok && response.status !== 204) {
      const error = await response.text()
      console.error('GitHub API error:', error)
      return NextResponse.json({
        success: false,
        error: `Failed to trigger workflow: ${response.status}`
      }, { status: 500 })
    }

    const cycleId = crypto.randomUUID()
    const startedAt = new Date().toISOString()

    // Log the manual trigger
    await supabase.from('trading_bot_logs').insert({
      log_level: 'INFO',
      message: 'Trading bot manually triggered from dashboard (GitHub Actions)',
      component: 'Dashboard',
      cycle_id: cycleId,
      trading_mode: 'paper'
    })

    // Create alert
    await supabase.from('trading_alerts').insert({
      alert_type: 'bot_triggered',
      severity: 'info',
      title: 'Bot Triggered Manually',
      message: 'Trading bot workflow has been triggered on GitHub Actions. It will start within a few seconds.',
      trading_mode: 'paper'
    })

    return NextResponse.json({
      success: true,
      message: 'Trading bot triggered on GitHub Actions',
      startedAt,
      note: 'The workflow typically starts within 10-30 seconds'
    })
  } catch (error) {
    console.error('Error triggering bot:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to trigger trading bot' },
      { status: 500 }
    )
  }
}
