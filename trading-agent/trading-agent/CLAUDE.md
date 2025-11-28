# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered cryptocurrency trading bot with a Next.js dashboard. The bot analyzes BTC, ETH, SOL using technical indicators and LLM-based decision making, executing trades via Alpaca's paper trading API.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel        │     │   Supabase      │     │ GitHub Actions  │
│   (Dashboard)   │◄───►│   (Database)    │◄───►│  (Python Bot)   │
│   Next.js 14    │     │   PostgreSQL    │     │  Cron 15 min    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

- **trading-agent/**: Python trading bot (runs on GitHub Actions)
- **web/**: Next.js 14 dashboard (deploys to Vercel)
- **Supabase**: PostgreSQL database with `trading_*` prefixed tables

## Commands

### Python Bot (trading-agent/)
```bash
cd trading-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py                    # Run single trading cycle
pytest                            # Run tests
```

### Next.js Dashboard (web/)
```bash
cd web
npm install
npm run dev                       # Development server
npm run build                     # Production build
npm run lint                      # ESLint
```

### GitHub Actions
The bot runs automatically every 15 minutes via `.github/workflows/trading-bot.yml`. Manual trigger available in GitHub Actions UI.

## Key Configuration

### Environment Variables
- **trading-agent/.env**: All secrets (API keys, Supabase credentials)
- **GitHub Secrets**: Same variables configured for Actions
- **web/.env.local**: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Important Settings
- `EXCHANGE=alpaca` - Always use Alpaca unless specified otherwise
- `PAPER_TRADING=true` - Paper trading mode (safe testing)
- `MIN_CONFIDENCE_THRESHOLD=0.6` - LLM must have 60%+ confidence to trade

## Database Tables (Supabase)

All tables use `trading_` prefix:
- `trading_decisions`: LLM trading decisions with reasoning
- `trading_positions`: Open/closed positions
- `trading_portfolio_snapshots`: Equity snapshots over time
- `trading_market_contexts`: Technical indicators, forecasts
- `trading_settings`: Runtime configuration
- `trading_alerts`: System alerts

## Trading Bot Flow

1. **Market Data**: Fetch OHLCV from Alpaca for BTC/USD, ETH/USD, SOL/USD
2. **Technical Analysis**: RSI, MACD, EMA, Pivot Points
3. **Forecasting**: Prophet time-series prediction
4. **Sentiment**: Fear & Greed Index, news feed
5. **LLM Decision**: DeepSeek analyzes all data, returns HOLD/OPEN/CLOSE
6. **Execution**: If confidence > 60%, execute via Alpaca API
7. **Database**: Save decision, market context, portfolio snapshot to Supabase

## Key Files

- `trading-agent/main.py`: Entry point
- `trading-agent/core/agent.py`: Main orchestration
- `trading-agent/core/llm_client.py`: DeepSeek LLM integration
- `trading-agent/exchange/alpaca_client.py`: Alpaca API wrapper
- `trading-agent/exchange/exchange_factory.py`: Exchange selection
- `trading-agent/config/settings.py`: Pydantic settings
- `web/lib/supabase.ts`: Supabase client + type definitions
- `web/app/page.tsx`: Dashboard home
- `web/app/bot/page.tsx`: Activity console
