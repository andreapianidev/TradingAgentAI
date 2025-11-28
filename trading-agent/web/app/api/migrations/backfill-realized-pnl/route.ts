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

export async function POST() {
  try {
    const supabase = getSupabaseClient()

    // Get all closed positions without realized_pnl
    const { data: closedPositions, error: fetchError } = await supabase
      .from('trading_positions')
      .select('*')
      .eq('status', 'closed')
      .is('realized_pnl', null)

    if (fetchError) throw fetchError

    if (!closedPositions || closedPositions.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No positions to backfill',
        updated: 0
      })
    }

    console.log(`Backfilling ${closedPositions.length} closed positions`)

    let updated = 0
    let failed = 0
    const errors: string[] = []

    for (const position of closedPositions) {
      try {
        const entryPrice = parseFloat(String(position.entry_price))
        const quantity = parseFloat(String(position.quantity))
        const unrealizedPnl = parseFloat(String(position.unrealized_pnl || 0))
        const direction = position.direction

        // Estimate exit price from last known unrealized_pnl
        // For long: exit_price = entry_price + (unrealized_pnl / quantity)
        // For short: exit_price = entry_price - (unrealized_pnl / quantity)
        let exitPrice: number

        if (quantity > 0) {
          if (direction === 'long') {
            exitPrice = entryPrice + (unrealizedPnl / quantity)
          } else {
            exitPrice = entryPrice - (unrealizedPnl / quantity)
          }
        } else {
          // Fallback to entry price if quantity is 0 or invalid
          exitPrice = entryPrice
        }

        // Calculate realized P&L
        let realizedPnl: number
        if (direction === 'long') {
          realizedPnl = (exitPrice - entryPrice) * quantity
        } else {
          realizedPnl = (entryPrice - exitPrice) * quantity
        }

        const costBasis = entryPrice * quantity
        const realizedPnlPct = costBasis > 0 ? (realizedPnl / costBasis) * 100 : 0

        // Update position
        const { error: updateError } = await supabase
          .from('trading_positions')
          .update({
            exit_price: exitPrice,
            realized_pnl: realizedPnl,
            realized_pnl_pct: realizedPnlPct,
            updated_at: new Date().toISOString()
          })
          .eq('id', position.id)

        if (updateError) {
          console.error(`Failed to update position ${position.id}:`, updateError)
          failed++
          errors.push(`${position.symbol}: ${updateError.message}`)
        } else {
          updated++
          console.log(
            `✓ Updated ${position.symbol}: exit_price=$${exitPrice.toFixed(2)}, realized_pnl=$${realizedPnl.toFixed(2)} (${realizedPnlPct.toFixed(2)}%)`
          )
        }
      } catch (error) {
        console.error(`Error processing position ${position.id}:`, error)
        failed++
        errors.push(`${position.symbol}: ${error instanceof Error ? error.message : 'Unknown error'}`)
      }
    }

    return NextResponse.json({
      success: true,
      message: `Backfill complete: ${updated} updated, ${failed} failed`,
      updated,
      failed,
      errors: errors.length > 0 ? errors : undefined
    })
  } catch (error) {
    console.error('Error in backfill migration:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to backfill realized P&L'
      },
      { status: 500 }
    )
  }
}

export async function GET() {
  // Also support GET requests for easy testing
  return POST()
}
