# Agenti Claude Code per Trading Agent AI

Questo documento definisce agenti specializzati per Claude Code ottimizzati per lo sviluppo e la manutenzione del sistema di trading AI.

---

## 1. Trading Strategy Agent

**Scopo:** Analizzare e modificare le strategie di trading, i pesi degli indicatori e le regole decisionali.

**File chiave:**
- `trading-agent/config/prompts.py` - System prompt e regole di trading
- `trading-agent/indicators/weights.py` - Pesi degli indicatori
- `trading-agent/core/decision_validator.py` - Validazione decisioni
- `trading-agent/core/risk_manager.py` - Gestione del rischio

**Quando usarlo:**
- Modificare le condizioni di entry/exit (long/short)
- Aggiustare i pesi degli indicatori (MACD, RSI, Pivot Points, ecc.)
- Cambiare le soglie di confidence
- Ottimizzare le regole di stop loss e take profit

**Prompt esempio:**
```
Analizza la strategia di trading attuale e suggerisci modifiche per migliorare
il win rate. Considera i pesi degli indicatori in weights.py e le regole
nel system prompt in prompts.py.
```

---

## 2. Exchange Integration Agent

**Scopo:** Gestire le integrazioni con Hyperliquid e Alpaca, aggiungere nuovi exchange.

**File chiave:**
- `trading-agent/exchange/exchange_factory.py` - Factory pattern
- `trading-agent/exchange/hyperliquid_client.py` - Client Hyperliquid
- `trading-agent/exchange/alpaca_client.py` - Client Alpaca
- `trading-agent/exchange/order_manager.py` - Esecuzione ordini

**Quando usarlo:**
- Aggiungere supporto per nuovi exchange (Binance, Bybit, ecc.)
- Debuggare problemi di connessione API
- Modificare la logica di esecuzione ordini
- Implementare nuovi tipi di ordini (limit, trailing stop)

**Prompt esempio:**
```
Aggiungi il supporto per Binance Futures seguendo il pattern esistente
di hyperliquid_client.py. Implementa tutti i metodi del Protocol ExchangeClient.
```

---

## 3. Risk Management Agent

**Scopo:** Configurare e ottimizzare i parametri di gestione del rischio.

**File chiave:**
- `trading-agent/core/risk_manager.py` - Calcoli di rischio
- `trading-agent/config/settings.py` - Parametri configurabili
- `trading-agent/config/constants.py` - Costanti di sistema
- `trading-agent/exchange/portfolio.py` - Gestione portafoglio

**Quando usarlo:**
- Modificare limiti di leverage (1x-10x)
- Aggiustare position sizing (1%-5%)
- Cambiare limiti di esposizione totale (max 30%)
- Implementare nuove regole di risk management

**Prompt esempio:**
```
Implementa un sistema di risk management dinamico che riduca automaticamente
la position size quando il drawdown supera il 10%.
```

---

## 4. Dashboard Frontend Agent

**Scopo:** Sviluppare e mantenere la dashboard Next.js.

**File chiave:**
- `web/app/` - Pagine e route
- `web/components/` - Componenti React
- `web/lib/supabase.ts` - Tipi e client Supabase
- `web/lib/utils.ts` - Utility functions
- `web/app/api/` - API routes

**Quando usarlo:**
- Aggiungere nuove pagine o componenti
- Modificare grafici e visualizzazioni
- Implementare nuove funzionalità UI
- Correggere errori TypeScript
- Ottimizzare performance frontend

**Prompt esempio:**
```
Crea un nuovo componente per visualizzare il grafico dei pivot points
con supporto/resistenza usando Recharts.
```

---

## 5. Database & Supabase Agent

**Scopo:** Gestire schema database, migrazioni e operazioni CRUD.

**File chiave:**
- `trading-agent/database/supabase_operations.py` - Operazioni CRUD
- `trading-agent/database/models.py` - Modelli SQLAlchemy
- `web/lib/supabase.ts` - Tipi TypeScript

**Tabelle principali:**
- `trading_market_contexts` - Snapshot di mercato
- `trading_decisions` - Decisioni LLM
- `trading_positions` - Posizioni aperte/chiuse
- `trading_portfolio_snapshots` - Stato portafoglio
- `trading_bot_logs` - Log del bot
- `trading_settings` - Configurazioni

**Quando usarlo:**
- Aggiungere nuove tabelle o colonne
- Ottimizzare query database
- Implementare nuove operazioni CRUD
- Sincronizzare tipi tra Python e TypeScript

**Prompt esempio:**
```
Aggiungi una nuova tabella trading_backtests per salvare i risultati
dei backtest con schema appropriato e operazioni CRUD.
```

---

## 6. Technical Indicators Agent

**Scopo:** Aggiungere e modificare indicatori tecnici.

**File chiave:**
- `trading-agent/indicators/technical.py` - MACD, RSI, EMA
- `trading-agent/indicators/pivot_points.py` - Pivot Points
- `trading-agent/indicators/forecasting.py` - Prophet ML
- `trading-agent/indicators/weights.py` - Pesi indicatori

**Indicatori attuali:**
- MACD (12, 26, 9)
- RSI (14 periodi)
- EMA2, EMA20
- Pivot Points (PP, R1, R2, S1, S2)
- Prophet Forecast (4 ore)

**Quando usarlo:**
- Aggiungere nuovi indicatori (Bollinger Bands, ATR, Stochastic)
- Modificare parametri degli indicatori esistenti
- Implementare indicatori custom
- Ottimizzare calcoli per performance

**Prompt esempio:**
```
Aggiungi l'indicatore Bollinger Bands con periodi configurabili
e integralo nel flusso di analisi del TradingAgent.
```

---

## 7. Data Sources Agent

**Scopo:** Gestire le fonti dati esterne (news, sentiment, whale alerts).

**File chiave:**
- `trading-agent/data/sentiment.py` - Fear & Greed Index
- `trading-agent/data/news_feed.py` - RSS news feed
- `trading-agent/data/whale_alert.py` - Whale transactions
- `trading-agent/data/market_data.py` - Dati di mercato
- `trading-agent/data/cache_manager.py` - Caching

**Fonti attuali:**
- CoinMarketCap / Alternative.me (Sentiment)
- Cointelegraph / Bitcoin Magazine (News RSS)
- Whale-alert.io (Large transactions)

**Quando usarlo:**
- Aggiungere nuove fonti di dati (Twitter/X, Reddit, on-chain data)
- Implementare nuove API
- Ottimizzare caching
- Migliorare sentiment analysis

**Prompt esempio:**
```
Aggiungi integrazione con Santiment API per ottenere metriche on-chain
come exchange flow e whale activity.
```

---

## 8. LLM Prompt Engineering Agent

**Scopo:** Ottimizzare i prompt per DeepSeek e migliorare le decisioni AI.

**File chiave:**
- `trading-agent/config/prompts.py` - System e user prompts
- `trading-agent/core/llm_client.py` - Client DeepSeek
- `trading-agent/utils/logger.py` - Log LLM requests/responses

**Componenti prompt:**
- System prompt (ruolo, regole, pesi indicatori)
- User prompt (dati mercato formattati)
- Correction prompt (retry su errori)

**Quando usarlo:**
- Migliorare la qualità delle decisioni
- Ridurre falsi segnali
- Ottimizzare il formato JSON di output
- Aggiungere nuovi contesti al prompt

**Prompt esempio:**
```
Analizza gli ultimi 50 log di decisioni LLM e suggerisci modifiche
al system prompt per ridurre i falsi segnali di HOLD.
```

---

## 9. Debugging & Monitoring Agent

**Scopo:** Debuggare problemi e monitorare le performance del sistema.

**File chiave:**
- `trading-agent/utils/logger.py` - Sistema di logging
- `trading-agent/core/agent.py` - Ciclo di trading principale
- `web/app/bot/page.tsx` - Console log real-time
- `trading-agent/database/supabase_operations.py` - Log su DB

**Quando usarlo:**
- Investigare errori nel ciclo di trading
- Analizzare decisioni problematiche
- Debuggare connessioni API
- Monitorare performance del sistema

**Prompt esempio:**
```
Analizza i log degli ultimi 24 ore e identifica pattern di errori
ricorrenti nel ciclo di trading.
```

---

## 10. Backtesting & Analytics Agent

**Scopo:** Analizzare performance storiche e ottimizzare strategie.

**File chiave:**
- `trading-agent/database/supabase_operations.py` - Query storiche
- `trading-agent/exchange/portfolio.py` - Calcoli P&L
- `web/app/history/page.tsx` - Storico trades

**Metriche chiave:**
- Win rate
- Profit factor
- Max drawdown
- Sharpe ratio
- Average trade duration

**Quando usarlo:**
- Analizzare performance passate
- Ottimizzare parametri basandosi sui dati storici
- Identificare pattern vincenti/perdenti
- Creare report di performance

**Prompt esempio:**
```
Crea un sistema di backtesting che simuli le decisioni storiche
con diversi set di parametri di rischio.
```

---

## 11. Paper Trading Agent

**Scopo:** Gestire il sistema di paper trading e simulazioni.

**File chiave:**
- `trading-agent/exchange/paper_trading.py` - Client paper trading
- `trading-agent/exchange/portfolio.py` - SL/TP checks
- `paper_trading_data/paper_trading_state.json` - Stato salvato

**Funzionalità:**
- Simulazione ordini senza capitale reale
- Tracking P&L simulato
- Check automatico SL/TP
- Persistenza stato

**Quando usarlo:**
- Testare nuove strategie
- Debuggare logica di trading
- Validare modifiche prima del live

**Prompt esempio:**
```
Implementa la funzionalità di reset del paper trading
con un nuovo balance iniziale configurabile.
```

---

## 12. Deployment & DevOps Agent

**Scopo:** Gestire deployment, CI/CD e configurazioni infrastrutturali.

**File chiave:**
- `vercel.json` - Config Vercel (frontend)
- `trading-agent/vercel.json` - Config Vercel (bot serverless)
- `trading-agent/api/index.py` - Handler serverless
- `.github/workflows/` - GitHub Actions

**Quando usarlo:**
- Configurare deployment Vercel
- Impostare variabili ambiente
- Creare pipeline CI/CD
- Gestire secrets

**Prompt esempio:**
```
Configura un workflow GitHub Actions per eseguire test automatici
e deploy su Vercel ad ogni push su main.
```

---

## Configurazione Agenti in Claude Code

Per configurare questi agenti come slash commands in Claude Code, crea file nella directory `.claude/commands/`:

### Esempio: `.claude/commands/trading-strategy.md`

```markdown
Sei un esperto di trading algoritmico specializzato in strategie crypto.

Analizza e modifica la strategia di trading del sistema AgenteTradingAI.

File principali da considerare:
- trading-agent/config/prompts.py
- trading-agent/indicators/weights.py
- trading-agent/core/decision_validator.py

Quando modifichi la strategia:
1. Spiega il razionale delle modifiche
2. Considera l'impatto sul risk management
3. Suggerisci come testare le modifiche in paper trading
4. Documenta i cambiamenti

$ARGUMENTS
```

---

## Workflow Consigliato

1. **Sviluppo feature:** Usa l'agente specifico per il dominio
2. **Testing:** Passa a Paper Trading Agent per validare
3. **Debug:** Usa Debugging Agent se emergono problemi
4. **Deploy:** Usa DevOps Agent per il deployment
5. **Monitoring:** Usa Analytics Agent per monitorare performance

---

## Note Importanti

- **Sicurezza:** Mai esporre API keys nei prompt
- **Testing:** Sempre testare in paper trading prima del live
- **Backup:** Fare backup del database prima di modifiche schema
- **Logging:** Mantenere log dettagliati per debugging
- **Versionamento:** Usare git per tracciare modifiche significative
