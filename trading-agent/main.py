#!/usr/bin/env python3
"""
Trading Agent - Main Entry Point

This script runs a single trading cycle for the AI trading agent.
Designed to be executed as a cron job every 15 minutes.
"""
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import trading_agent
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main entry point for the trading agent."""
    logger.info("=" * 60)
    logger.info("TRADING AGENT STARTING")
    logger.info(f"Time: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    try:
        # Run the trading cycle
        result = trading_agent.run_cycle()

        # Log summary
        if result.get("success"):
            logger.info("Trading cycle completed successfully")

            for symbol, symbol_result in result.get("symbols", {}).items():
                action = symbol_result.get("action", "unknown")
                executed = symbol_result.get("executed", False)
                logger.info(
                    f"  {symbol}: {action.upper()} "
                    f"{'(EXECUTED)' if executed else '(NOT EXECUTED)'}"
                )
        else:
            logger.error(f"Trading cycle failed: {result.get('error')}")

        # Log any errors
        for error in result.get("errors", []):
            logger.error(f"  Error: {error}")

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        trading_agent.shutdown()

    logger.info("=" * 60)
    logger.info("TRADING AGENT FINISHED")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
