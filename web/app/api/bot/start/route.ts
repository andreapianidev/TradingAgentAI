import { NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { spawn } from 'child_process'
import path from 'path'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Store the bot process globally (in-memory for this server instance)
declare global {
  var botProcess: ReturnType<typeof spawn> | null
  var botCycleId: string | null
  var botStartedAt: string | null
}

global.botProcess = global.botProcess || null
global.botCycleId = global.botCycleId || null
global.botStartedAt = global.botStartedAt || null

export async function POST() {
  try {
    // Check if bot is already running
    if (global.botProcess && !global.botProcess.killed) {
      return NextResponse.json({
        success: false,
        error: 'Bot is already running',
        isRunning: true,
        cycleId: global.botCycleId
      }, { status: 400 })
    }

    const cycleId = crypto.randomUUID()
    const startedAt = new Date().toISOString()

    // Create cycle record
    await supabase.from('trading_cycles').insert({
      id: cycleId,
      started_at: startedAt,
      status: 'running',
      trading_mode: 'paper'
    })

    // Log bot start
    await supabase.from('trading_bot_logs').insert({
      log_level: 'INFO',
      message: 'Trading bot started from dashboard',
      component: 'BotController',
      cycle_id: cycleId,
      trading_mode: 'paper'
    })

    // Path to the trading bot
    const botPath = path.resolve(process.cwd(), '..', 'trading-agent')

    // Spawn the Python bot process
    const botProcess = spawn('python', ['main.py'], {
      cwd: botPath,
      env: {
        ...process.env,
        CYCLE_ID: cycleId,
        PYTHONUNBUFFERED: '1'
      },
      stdio: ['pipe', 'pipe', 'pipe']
    })

    global.botProcess = botProcess
    global.botCycleId = cycleId
    global.botStartedAt = startedAt

    // Handle stdout
    botProcess.stdout?.on('data', async (data) => {
      const message = data.toString().trim()
      if (message) {
        console.log('[BOT]', message)
      }
    })

    // Handle stderr
    botProcess.stderr?.on('data', async (data) => {
      const message = data.toString().trim()
      if (message) {
        console.error('[BOT ERROR]', message)
      }
    })

    // Handle process exit
    botProcess.on('close', async (code) => {
      console.log(`Bot process exited with code ${code}`)

      // Update cycle status
      await supabase
        .from('trading_cycles')
        .update({
          completed_at: new Date().toISOString(),
          status: code === 0 ? 'completed' : 'error'
        })
        .eq('id', cycleId)

      // Log bot stop
      await supabase.from('trading_bot_logs').insert({
        log_level: code === 0 ? 'INFO' : 'ERROR',
        message: `Trading bot stopped with exit code ${code}`,
        component: 'BotController',
        cycle_id: cycleId,
        trading_mode: 'paper'
      })

      global.botProcess = null
      global.botCycleId = null
      global.botStartedAt = null
    })

    botProcess.on('error', async (error) => {
      console.error('Bot process error:', error)

      await supabase.from('trading_bot_logs').insert({
        log_level: 'ERROR',
        message: `Bot process error: ${error.message}`,
        component: 'BotController',
        cycle_id: cycleId,
        trading_mode: 'paper'
      })

      global.botProcess = null
      global.botCycleId = null
      global.botStartedAt = null
    })

    return NextResponse.json({
      success: true,
      isRunning: true,
      cycleId,
      startedAt,
      message: 'Trading bot started successfully'
    })
  } catch (error) {
    console.error('Error starting bot:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to start trading bot' },
      { status: 500 }
    )
  }
}
