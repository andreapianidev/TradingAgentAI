"""
Script to close a specific position on Alpaca.
Run this to close the orphaned SOL position before switching to paper mode.

Usage:
    python close_alpaca_position.py SOL
    python close_alpaca_position.py --all  # Close all positions
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def close_position(symbol: str = None, close_all: bool = False):
    """Close position(s) on Alpaca."""

    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import ClosePositionRequest

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    paper = os.getenv("ALPACA_PAPER_TRADING", "true").lower() == "true"

    if not api_key or not secret_key:
        print("❌ Error: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set")
        return False

    print(f"🔌 Connecting to Alpaca ({'Paper' if paper else 'LIVE'} mode)...")

    try:
        client = TradingClient(api_key, secret_key, paper=paper)

        # Get current positions
        positions = client.get_all_positions()

        if not positions:
            print("✅ No open positions found on Alpaca")
            return True

        print(f"\n📊 Current Alpaca Positions:")
        for pos in positions:
            pnl = float(pos.unrealized_pl)
            pnl_pct = float(pos.unrealized_plpc) * 100
            print(f"   {pos.symbol}: {float(pos.qty):.6f} @ ${float(pos.avg_entry_price):.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")

        if close_all:
            print("\n🔄 Closing ALL positions...")
            client.close_all_positions(cancel_orders=True)
            print("✅ All positions closed!")
            return True

        if symbol:
            # Find the position
            target_pos = None
            for pos in positions:
                # Handle both 'SOL' and 'SOLUSD' formats
                if pos.symbol.replace("USD", "") == symbol.replace("USD", ""):
                    target_pos = pos
                    break

            if not target_pos:
                print(f"❌ No position found for {symbol}")
                return False

            print(f"\n🔄 Closing {target_pos.symbol}...")

            # Close the position
            client.close_position(target_pos.symbol)

            pnl = float(target_pos.unrealized_pl)
            print(f"✅ Position closed! Realized P&L: ${pnl:.2f}")
            return True

        print("\n⚠️ Please specify a symbol or use --all")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def update_database(symbol: str):
    """Update the database to mark the position as closed."""
    from supabase import create_client
    from datetime import datetime

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("⚠️ Supabase credentials not found, skipping database update")
        return

    try:
        client = create_client(url, key)

        # Find the open position
        result = client.table("trading_positions") \
            .select("*") \
            .eq("symbol", symbol) \
            .eq("status", "open") \
            .eq("trading_mode", "live") \
            .execute()

        if not result.data:
            print(f"⚠️ No open {symbol} position found in database")
            return

        position = result.data[0]

        # Close it
        client.table("trading_positions").update({
            "status": "closed",
            "exit_timestamp": datetime.utcnow().isoformat(),
            "exit_reason": "manual_script",
            "exit_price": float(position["entry_price"]),  # Will be updated with real price
            "realized_pnl": 0,
            "realized_pnl_pct": 0
        }).eq("id", position["id"]).execute()

        print(f"✅ Database updated - {symbol} position marked as closed")

    except Exception as e:
        print(f"⚠️ Database update failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python close_alpaca_position.py SOL      # Close SOL position")
        print("  python close_alpaca_position.py --all    # Close all positions")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--all":
        success = close_position(close_all=True)
    else:
        symbol = arg.upper()
        success = close_position(symbol=symbol)
        if success:
            update_database(symbol)

    sys.exit(0 if success else 1)
