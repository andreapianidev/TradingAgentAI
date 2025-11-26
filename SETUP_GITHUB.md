# Setup GitHub Actions per Trading Bot

## Architettura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel        │     │   Supabase      │     │ GitHub Actions  │
│   (Dashboard)   │◄───►│   (Database)    │◄───►│  (Bot Python)   │
│   Next.js       │     │   PostgreSQL    │     │  Cron 15 min    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Step 1: Crea Repository GitHub

1. Vai su [github.com/new](https://github.com/new)
2. Nome: `trading-agent` (o quello che preferisci)
3. Privato (consigliato per le API keys)
4. Clicca "Create repository"

## Step 2: Push del codice

```bash
cd /path/to/AgenteTradingAI
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TUO_USERNAME/trading-agent.git
git push -u origin main
```

## Step 3: Configura i Secrets

Vai su: `GitHub Repo → Settings → Secrets and variables → Actions → New repository secret`

### Secrets OBBLIGATORI:

| Nome Secret | Valore |
|-------------|--------|
| `EXCHANGE` | `alpaca` |
| `ALPACA_API_KEY` | La tua API key Alpaca |
| `ALPACA_SECRET_KEY` | La tua Secret key Alpaca |
| `ALPACA_PAPER_TRADING` | `true` |
| `ALPACA_BASE_URL` | `https://paper-api.alpaca.markets` |
| `DEEPSEEK_API_KEY` | La tua API key DeepSeek |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| `MODEL_NAME` | `deepseek-chat` |
| `SUPABASE_URL` | `https://lbloovcuaxkhvgovayoo.supabase.co` |
| `SUPABASE_SERVICE_KEY` | La tua Supabase service key |

### Secrets Trading Parameters:

| Nome Secret | Valore Default |
|-------------|----------------|
| `TARGET_SYMBOLS` | `BTC,ETH,SOL` |
| `TIMEFRAME` | `15m` |
| `MAX_LEVERAGE` | `10` |
| `DEFAULT_LEVERAGE` | `3` |
| `MAX_POSITION_SIZE_PCT` | `5.0` |
| `MAX_TOTAL_EXPOSURE_PCT` | `30.0` |

### Secrets Risk Management:

| Nome Secret | Valore Default |
|-------------|----------------|
| `ENABLE_STOP_LOSS` | `true` |
| `ENABLE_TAKE_PROFIT` | `true` |
| `STOP_LOSS_PCT` | `3.0` |
| `TAKE_PROFIT_PCT` | `5.0` |
| `MIN_CONFIDENCE_THRESHOLD` | `0.6` |

### Secrets LLM:

| Nome Secret | Valore Default |
|-------------|----------------|
| `LLM_TEMPERATURE` | `0.3` |
| `LLM_MAX_TOKENS` | `2000` |

### Secrets Opzionali:

| Nome Secret | Valore |
|-------------|--------|
| `COINMARKETCAP_API_KEY` | API key CoinMarketCap (per Fear & Greed) |
| `NEWS_FEED_URL` | `https://cointelegraph.com/rss` |
| `PAPER_TRADING` | `false` |
| `PAPER_TRADING_INITIAL_BALANCE` | `10000.0` |

## Step 4: Verifica il Workflow

1. Vai su `Actions` nel tuo repo GitHub
2. Dovresti vedere "Trading Bot" workflow
3. Clicca "Run workflow" per testarlo manualmente
4. Il workflow girerà automaticamente ogni 15 minuti

## Step 5: Deploy Dashboard su Vercel

1. Vai su [vercel.com](https://vercel.com)
2. Importa il repo GitHub
3. **Root Directory**: `web`
4. **Framework Preset**: `Next.js`
5. Aggiungi Environment Variables:
   - `NEXT_PUBLIC_SUPABASE_URL` = il tuo Supabase URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = la tua Supabase anon key

## Monitoraggio

- **GitHub Actions**: Controlla i log su `Actions` tab
- **Supabase**: Controlla i dati su `Table Editor`
- **Dashboard Vercel**: Vedi tutto in tempo reale

## Costi

| Servizio | Piano | Costo |
|----------|-------|-------|
| GitHub Actions | Free | 2000 min/mese |
| Vercel | Hobby | Gratis |
| Supabase | Free | Gratis (500MB) |
| DeepSeek | Pay-as-you-go | ~$0.001/chiamata |
| Alpaca | Free | Gratis (paper trading) |

**Totale: ~$0-5/mese** (solo DeepSeek API usage)

## Troubleshooting

### Il workflow fallisce?
- Controlla i Secrets (nomi esatti, maiuscole)
- Guarda i log su Actions → Run selezionato

### Nessun dato sulla dashboard?
- Verifica che Supabase URL e Key siano corretti
- Controlla che il bot abbia scritto dati (Supabase Table Editor)

### Bot non fa trade?
- La confidence deve essere > 60% (MIN_CONFIDENCE_THRESHOLD)
- Controlla i log del reasoning LLM
