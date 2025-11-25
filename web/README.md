# Trading Bot Dashboard

Interfaccia web per il trading bot AI, deployabile su Vercel.

## Features

- **Dashboard**: Overview del portafoglio, equity curve, posizioni aperte e alert
- **Positions**: Gestione posizioni aperte e chiuse con export CSV
- **Trade History**: Storico completo delle decisioni AI con reasoning
- **Market Analysis**: Indicatori tecnici real-time (MACD, RSI, EMA, Pivot Points, Sentiment)
- **Settings**: Configurazione parametri del bot

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Database**: Supabase (PostgreSQL)
- **Charts**: Recharts
- **Icons**: Lucide React

## Database Tables (Supabase)

Tutte le tabelle hanno prefisso `trading_` per distinguerle da altri progetti:

| Tabella | Descrizione |
|---------|-------------|
| `trading_market_contexts` | Contesti di mercato (indicatori, sentiment, forecast) |
| `trading_decisions` | Decisioni AI con reasoning completo |
| `trading_positions` | Posizioni aperte/chiuse |
| `trading_portfolio_snapshots` | Snapshot del portafoglio |
| `trading_alerts` | Notifiche del bot |
| `trading_bot_logs` | Log di esecuzione |
| `trading_cycles` | Cicli di 15 minuti |
| `trading_daily_stats` | Statistiche giornaliere |
| `trading_settings` | Configurazione |

## Setup

### 1. Installa dipendenze

```bash
cd web
npm install
```

### 2. Configura variabili ambiente

Copia `.env.example` in `.env.local` e compila:

```bash
cp .env.example .env.local
```

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 3. Avvia in development

```bash
npm run dev
```

Apri http://localhost:3000

## Deploy su Vercel

### 1. Push su GitHub

```bash
git add .
git commit -m "Add trading bot dashboard"
git push
```

### 2. Importa su Vercel

1. Vai su [vercel.com](https://vercel.com)
2. Clicca "New Project"
3. Importa il repository
4. Configura la root directory: `web`
5. Aggiungi le variabili ambiente
6. Deploy!

### 3. Variabili ambiente su Vercel

Aggiungi queste variabili nelle Project Settings:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

## API Routes

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/status` | GET | Stato del bot e portafoglio |
| `/api/bot/toggle` | POST | Attiva/disattiva il bot |
| `/api/bot/run` | POST | Esegui ciclo manualmente |
| `/api/positions/close` | POST | Chiudi una posizione |

## Paper Trading vs Live Trading

Il bot usa la **stessa logica** per entrambe le modalità:

- **Paper Trading**: Dati di mercato reali, ordini simulati
- **Live Trading**: Dati di mercato reali, ordini reali su Hyperliquid

La modalità è controllata dall'impostazione `paper_trading_enabled` nelle Settings.

## Architettura

```
┌─────────────────────────────────────────────────────┐
│                  Next.js Dashboard                   │
│                    (Vercel)                          │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                    Supabase                          │
│              (PostgreSQL + RLS)                      │
│                                                      │
│  trading_market_contexts  trading_decisions          │
│  trading_positions        trading_portfolio_snapshots│
│  trading_alerts           trading_settings           │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              Python Trading Bot                      │
│                  (Railway)                           │
│                                                      │
│  Cron Job ogni 15 minuti:                           │
│  1. Raccoglie dati mercato (Hyperliquid)            │
│  2. Calcola indicatori tecnici                       │
│  3. Genera forecast (Prophet)                        │
│  4. Chiede decisione a LLM (DeepSeek)               │
│  5. Esegue ordine (Paper/Live)                      │
│  6. Salva tutto su Supabase                         │
└─────────────────────────────────────────────────────┘
```
