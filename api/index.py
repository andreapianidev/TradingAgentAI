"""
Vercel Serverless Function for Trading Agent.

This endpoint is called by Vercel Cron Jobs every 15 minutes.
"""
import json
import sys
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class handler(BaseHTTPRequestHandler):
    """HTTP request handler for Vercel serverless function."""

    def do_GET(self):
        """Handle GET requests."""
        path = self.path.split('?')[0]

        if path == '/api/run':
            self._run_trading_cycle()
        elif path == '/api/status':
            self._get_status()
        elif path == '/api/health':
            self._health_check()
        else:
            self._send_response(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/run':
            self._run_trading_cycle()
        else:
            self._send_response(404, {"error": "Not found"})

    def _run_trading_cycle(self):
        """Execute the trading cycle."""
        try:
            from core.agent import trading_agent

            # Run the cycle
            result = trading_agent.run_cycle()

            # Prepare response
            response = {
                "success": result.get("success", False),
                "timestamp": datetime.utcnow().isoformat(),
                "duration": result.get("duration_seconds", 0),
                "symbols": {}
            }

            # Add symbol summaries
            for symbol, symbol_result in result.get("symbols", {}).items():
                response["symbols"][symbol] = {
                    "action": symbol_result.get("action"),
                    "executed": symbol_result.get("executed", False),
                    "confidence": symbol_result.get("confidence", 0)
                }

            # Cleanup
            trading_agent.shutdown()

            self._send_response(200, response)

        except Exception as e:
            self._send_response(500, {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

    def _get_status(self):
        """Get agent status."""
        try:
            from exchange.portfolio import portfolio_manager
            from database.operations import db_ops
            from exchange.exchange_factory import get_exchange_client

            # Initialize connections - exchange_factory handles this
            exchange_client = get_exchange_client(auto_connect=True)

            # Get portfolio
            portfolio = portfolio_manager.get_portfolio_state()
            stats = db_ops.get_trading_stats()

            response = {
                "status": "running",
                "timestamp": datetime.utcnow().isoformat(),
                "portfolio": {
                    "equity": portfolio.get("total_equity", 0),
                    "available": portfolio.get("available_balance", 0),
                    "exposure_pct": portfolio.get("exposure_pct", 0),
                    "positions": portfolio.get("open_positions_count", 0)
                },
                "statistics": {
                    "total_trades": stats.get("total_trades", 0),
                    "win_rate": stats.get("win_rate", 0),
                    "total_pnl": stats.get("total_pnl", 0)
                }
            }

            exchange_client.disconnect()

            self._send_response(200, response)

        except Exception as e:
            self._send_response(500, {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

    def _health_check(self):
        """Simple health check endpoint."""
        self._send_response(200, {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        })

    def _send_response(self, status_code: int, data: dict):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
