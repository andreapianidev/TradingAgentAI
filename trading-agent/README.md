<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-success.svg" alt="Status">
  <img src="https://img.shields.io/badge/AI-DeepSeek-purple.svg" alt="AI">
  <img src="https://img.shields.io/badge/Exchange-Hyperliquid-orange.svg" alt="Exchange">
</p>

<h1 align="center">🤖 Trading Agent AI</h1>

<p align="center">
  <strong>An autonomous AI-powered cryptocurrency trading agent using Large Language Models as the decision-making brain</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-configuration">Configuration</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## 🌟 Overview

**Trading Agent AI** is a fully autonomous cryptocurrency trading system that leverages the power of Large Language Models (LLMs) to make intelligent trading decisions. The agent analyzes multiple data sources including technical indicators, market sentiment, news feeds, and whale movements to execute trades on [Hyperliquid](https://hyperliquid.xyz) exchange.

> ⚠️ **Disclaimer**: This software is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Use at your own risk and never trade with money you can't afford to lose.

---

## ✨ Features

### 🧠 AI-Powered Decision Making
- **DeepSeek LLM Integration** - Uses state-of-the-art language models for trading decisions
- **Weighted Indicator Analysis** - Combines multiple signals with configurable importance weights
- **Natural Language Reasoning** - Every decision comes with detailed explanation

### 📊 Technical Analysis
- **MACD** - Moving Average Convergence Divergence
- **RSI** - Relative Strength Index with overbought/oversold detection
- **EMA** - Exponential Moving Averages (2 and 20 periods)
- **Pivot Points** - Support (S1, S2) and Resistance (R1, R2) levels
- **Volume Analysis** - Order book depth and buy/sell pressure

### 🔮 Predictive Analytics
- **Prophet Forecasting** - Meta's time series forecasting model
- **4-hour Price Predictions** - Target price with confidence intervals
- **Trend Detection** - Bullish, Bearish, or Lateral market classification

### 📰 Market Intelligence
- **Fear & Greed Index** - Real-time market sentiment from CoinMarketCap
- **News Feed Analysis** - RSS parsing with sentiment classification
- **Whale Alert Monitoring** - Large transaction tracking (reverse-engineered)

### 🛡️ Risk Management
- **Configurable Leverage** - 1x to 10x with confidence-based scaling
- **Position Sizing** - Dynamic sizing based on confidence and exposure
- **Stop Loss & Take Profit** - Automatic risk protection
- **Exposure Limits** - Maximum portfolio exposure controls

### 📱 Monitoring & Dashboard
- **Streamlit Dashboard** - Real-time portfolio monitoring
- **Equity Curve Tracking** - Performance visualization
- **Trade History** - Complete log of all decisions and executions
- **Export Functionality** - CSV export for analysis

---

## 🔄 How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRADING CYCLE (Every 15 min)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. DATA COLLECTION                                              │
│     • Hyperliquid: Price, OHLCV, Order Book                     │
│     • CoinMarketCap: Fear & Greed Index                         │
│     • News Feeds: Latest crypto news                            │
│     • Whale Alert: Large transactions                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. ANALYSIS & INDICATORS                                        │
│     • Technical: MACD, RSI, EMA, Volume                         │
│     • Pivot Points: Support & Resistance levels                 │
│     • Prophet: 4-hour price forecast                            │
│     • Order Book: Buy/Sell pressure ratio                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. LLM DECISION (DeepSeek)                                     │
│     • Receives all data in structured prompt                    │
│     • Applies trading rules and risk parameters                 │
│     • Returns: Action, Direction, Leverage, Confidence          │
│     • Provides detailed reasoning                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. VALIDATION & EXECUTION                                       │
│     • Validate confidence threshold (≥60%)                      │
│     • Check exposure limits (≤30%)                              │
│     • Execute trade on Hyperliquid                              │
│     • Set Stop Loss & Take Profit                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. LOGGING & PERSISTENCE                                        │
│     • Save market context to PostgreSQL                         │
│     • Record decision and reasoning                             │
│     • Update portfolio snapshot                                 │
│     • Generate logs                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
trading-agent/
├── 📄 main.py                    # Entry point - run trading cycle
├── 📄 requirements.txt           # Python dependencies
├── 📄 vercel.json               # Vercel deployment config
├── 📄 .env.example              # Environment template
│
├── 📁 api/
│   └── index.py                 # Serverless function for Vercel
│
├── 📁 config/
│   ├── settings.py              # Pydantic configuration
│   ├── prompts.py               # LLM system prompts
│   └── constants.py             # System constants
│
├── 📁 core/
│   ├── agent.py                 # Main orchestration logic
│   ├── llm_client.py            # DeepSeek API client
│   ├── risk_manager.py          # Risk calculations
│   └── decision_validator.py    # Decision validation
│
├── 📁 exchange/
│   ├── hyperliquid_client.py    # CCXT wrapper for Hyperliquid
│   ├── order_manager.py         # Order execution
│   └── portfolio.py             # Portfolio tracking
│
├── 📁 indicators/
│   ├── technical.py             # MACD, RSI, EMA calculations
│   ├── pivot_points.py          # Support/Resistance levels
│   ├── forecasting.py           # Prophet ML model
│   └── weights.py               # Indicator weighting system
│
├── 📁 data/
│   ├── market_data.py           # Exchange data collection
│   ├── sentiment.py             # Fear & Greed Index
│   ├── news_feed.py             # RSS news parser
│   ├── whale_alert.py           # Large transaction monitor
│   └── cache_manager.py         # API response caching
│
├── 📁 database/
│   ├── models.py                # SQLAlchemy ORM models
│   ├── connection.py            # Database connection
│   └── operations.py            # CRUD operations
│
├── 📁 dashboard/
│   └── app.py                   # Streamlit monitoring dashboard
│
└── 📁 utils/
    ├── logger.py                # Colored logging system
    ├── helpers.py               # Utility functions
    └── validators.py            # Input validation
```

---

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL database (local or cloud)
- API keys (see Configuration)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/andreapianidev/TradingAgentAI.git
cd TradingAgentAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor

# Run the agent
python main.py
```

---

## ⚙️ Configuration

### Required API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| **Hyperliquid** | Trading execution | [app.hyperliquid.xyz](https://app.hyperliquid.xyz) |
| **DeepSeek** | LLM decisions | [platform.deepseek.com](https://platform.deepseek.com) |
| **PostgreSQL** | Data persistence | [Supabase](https://supabase.com) / [Neon](https://neon.tech) |

### Optional API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| **CoinMarketCap** | Sentiment data | [coinmarketcap.com/api](https://coinmarketcap.com/api) |

### Trading Parameters

```env
# Risk Management
MAX_LEVERAGE=10              # Maximum leverage allowed
MAX_POSITION_SIZE_PCT=5.0    # Max position size (% of portfolio)
MAX_TOTAL_EXPOSURE_PCT=30.0  # Max total exposure
STOP_LOSS_PCT=3.0            # Default stop loss percentage
TAKE_PROFIT_PCT=5.0          # Default take profit percentage
MIN_CONFIDENCE_THRESHOLD=0.6 # Minimum confidence to trade
```

### Indicator Weights

The LLM uses these weights to evaluate signals:

| Indicator | Weight | Description |
|-----------|--------|-------------|
| Pivot Points | 0.8 | Support/Resistance levels |
| MACD | 0.7 | Momentum indicator |
| RSI | 0.7 | Overbought/Oversold |
| Prophet Forecast | 0.6 | Price prediction |
| Order Book | 0.5 | Buy/Sell pressure |
| Sentiment | 0.4 | Market fear/greed |
| News | 0.3 | Recent headlines |

---

## 🎮 Usage

### Run Single Cycle

```bash
python main.py
```

### Run Dashboard

```bash
streamlit run dashboard/app.py
```

Access at: http://localhost:8501

### Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

The agent will run automatically every 15 minutes via Vercel Cron Jobs.

### API Endpoints (Vercel)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/run` | GET/POST | Execute trading cycle |
| `/api/status` | GET | Get portfolio status |
| `/api/health` | GET | Health check |

---

## 📊 Dashboard Preview

The Streamlit dashboard provides:

- **Overview**: Equity curve, portfolio stats, recent trades
- **Positions**: Open positions with P&L tracking
- **Trade History**: Complete decision log with filtering
- **Market Analysis**: Live indicators and forecasts
- **Settings**: Configuration and manual controls

---

## 🤝 Contributing

**We're actively looking for contributors!** This is an open-source project and we welcome contributions of all kinds.

### Ways to Contribute

- 🐛 **Bug Reports**: Found a bug? Open an issue!
- 💡 **Feature Requests**: Have an idea? Let's discuss!
- 🔧 **Code Contributions**: Submit a pull request
- 📖 **Documentation**: Help improve our docs
- 🧪 **Testing**: Add tests or report edge cases
- 🌍 **Translations**: Help translate to other languages

### Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/TradingAgentAI.git

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and test
python -m pytest tests/

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# Open Pull Request
```

### Code Style

- Follow PEP 8 guidelines
- Add type hints to all functions
- Write docstrings for public methods
- Keep functions focused and small

---

## 📞 Contact

**Andrea Piani** - Project Creator

- 🌐 Website: [www.andreapiani.com](https://www.andreapiani.com)
- 📱 WhatsApp: [+39 351 624 8936](https://wa.me/393516248936)
- 🐙 GitHub: [@andreapianidev](https://github.com/andreapianidev)

Feel free to reach out for:
- Questions about the project
- Collaboration opportunities
- Bug reports
- Feature suggestions

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Andrea Piani

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## ⚠️ Disclaimer

This software is provided for educational and research purposes only.

- **Not Financial Advice**: This bot does not constitute financial advice
- **Risk of Loss**: Cryptocurrency trading involves substantial risk
- **No Guarantees**: Past performance does not guarantee future results
- **Use Responsibly**: Only trade with funds you can afford to lose
- **Test First**: Always test on testnet before using real funds

---

## 🙏 Acknowledgments

- [DeepSeek](https://deepseek.com) - LLM API
- [Hyperliquid](https://hyperliquid.xyz) - Exchange
- [CCXT](https://github.com/ccxt/ccxt) - Exchange connectivity
- [Prophet](https://facebook.github.io/prophet/) - Time series forecasting
- [Streamlit](https://streamlit.io) - Dashboard framework

---

<p align="center">
  <strong>⭐ Star this repo if you find it useful! ⭐</strong>
</p>

<p align="center">
  Made with ❤️ by <a href="https://www.andreapiani.com">Andrea Piani</a>
</p>
