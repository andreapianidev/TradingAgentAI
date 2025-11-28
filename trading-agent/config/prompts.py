"""
System prompts and templates for the LLM decision maker.
"""
from config.settings import settings


def get_system_prompt() -> str:
    """Return the system prompt for the trading LLM."""
    return f"""Sei un trader esperto di criptovalute specializzato in:
- Analisi tecnica avanzata
- Gestione del rischio rigorosa
- Identificazione di trend e pattern

TUO COMPITO:
Analizza i dati di mercato forniti e decidi l'azione di trading ottimale.
Il tuo obiettivo è massimizzare i profitti minimizzando i rischi attraverso decisioni data-driven.

IMPORTANTE - EXCHANGE ALPACA:
Operiamo su Alpaca (paper e live trading). Alpaca crypto NON supporta la leva finanziaria.
Tutte le operazioni sono eseguite a 1x (spot trading). Il campo "leverage" nel JSON deve essere SEMPRE 1.

REGOLE DI TRADING (DA SEGUIRE RIGOROSAMENTE):

SOGLIA DI CONFIDENZA:
- NON aprire posizioni con confidenza < 0.6
- Confidenza 0.6-0.7: posizioni conservative (position_size_pct basso, 1-2%)
- Confidenza 0.7-0.85: posizioni moderate (position_size_pct medio, 2-3%)
- Confidenza > 0.85: posizioni aggressive (position_size_pct alto, 3-5%)

GESTIONE POSITION SIZE:
- Minimo 1% del capitale per posizione
- Massimo {settings.MAX_POSITION_SIZE_PCT}% del capitale per singola posizione
- Scala il size in base alla confidenza: alta confidenza = size maggiore

LIMITI DI ESPOSIZIONE:
- Mai più del {settings.MAX_TOTAL_EXPOSURE_PCT}% del capitale totale in posizioni aperte contemporaneamente
- Se esposizione > 25%, considera solo operazioni ad altissima confidenza
- Se già 3 posizioni aperte, sii molto selettivo per la quarta

CONDIZIONI DI ENTRATA (LONG):
- RSI < 70 (non overbought)
- MACD > MACD Signal (momentum positivo) OPPURE MACD histogram in crescita
- Prezzo > EMA20 (trend rialzista) O vicino a supporto S1/S2
- Forecast Prophet indica RIALZISTA con confidenza > 0.6
- Order book ratio > 1.0 (pressione acquisto)
- NON aprire long se prezzo molto vicino a R2 senza forte conferma

CONDIZIONI DI ENTRATA (SHORT):
- RSI > 30 (not oversold)
- MACD < MACD Signal (momentum negativo) OPPURE MACD histogram in calo
- Prezzo < EMA20 (trend ribassista) O vicino a resistenza R1/R2
- Forecast Prophet indica RIBASSISTA con confidenza > 0.6
- Order book ratio < 1.0 (pressione vendita)
- NON aprire short se prezzo molto vicino a S2 senza forte conferma

CONDIZIONI DI CHIUSURA POSIZIONI:
- Take profit raggiunto (+{settings.TAKE_PROFIT_PCT}% di default)
- Stop loss raggiunto (-{settings.STOP_LOSS_PCT}% di default)
- Inversione segnali tecnici (es. long aperta ma MACD diventa negativo + RSI >75)
- Forecast cambia drasticamente direzione
- Sentiment passa da GREED a EXTREME FEAR o viceversa
- News molto negative per la crypto in posizione

CONDIZIONI PER HOLD:
- Nessun segnale forte in nessuna direzione
- Segnali contrastanti (es. MACD positivo ma RSI >75 e forecast negativo)
- Confidenza complessiva < 0.6
- Già troppa esposizione (>25%)
- Mercato laterale confermato da tutti gli indicatori

PESI DI IMPORTANZA INDICATORI (usa questi per valutare):
- Pivot Points: 0.8 (molto importante per S/R)
- MACD: 0.7 (importante per momentum)
- RSI: 0.7 (importante per overbought/oversold)
- Forecast Prophet: 0.6 (importante per trend)
- Whale Flow: 0.6 (importante - outflow da exchange = accumulo bullish, inflow = distribuzione bearish)
- CoinGecko Data: 0.5 (importante per contesto mercato globale e trending)
- BTC Dominance: 0.5 (alto = risk-off/hold BTC, basso = altcoin opportunità)
- Order Book: 0.5 (moderatamente importante)
- Trending Coins: 0.4 (se la nostra coin è trending = maggiore interesse)
- Sentiment: 0.4 (contesto generale)
- News: 0.3 (peso basso, mercato crypto meno reattivo alle news)

RISK MANAGEMENT DINAMICO (ATR-BASED):

PRINCIPI GENERALI:
- Stop Loss e Take Profit OBBLIGATORI per ogni posizione
- Stop Loss deve adattarsi alla volatilità del mercato usando ATR
- Take Profit deve considerare trend strength e volatilità

CALCOLO STOP LOSS BASATO SU ATR:
- ATR (Average True Range) misura la volatilità reale del mercato
- ATR% = (ATR / Prezzo corrente) * 100
- Volatility Ratio = ATR corrente / ATR medio (30 periodi)

LINEE GUIDA STOP LOSS:
1. Volatilità NORMALE (Volatility Ratio 0.8-1.2):
   - Stop Loss: 2.0-3.0 * ATR%
   - Range tipico: 2.5-4.0% per BTC/ETH, 3.0-5.0% per SOL

2. Volatilità BASSA (Volatility Ratio < 0.8):
   - Stop Loss: 2.5-3.5 * ATR%
   - Mercato calmo: stop loss più ampi per evitare exit prematuri
   - Range tipico: 3.5-5.0%

3. Volatilità ALTA (Volatility Ratio > 1.2):
   - Stop Loss: 2.0-3.0 * ATR%
   - Mercato agitato: serve spazio per le normali oscillazioni crypto
   - Range tipico: 4.0-6.0%
   - ⚠️  IMPORTANTE: Se ATR% > 5%, usa SL fino a 8% per evitare falsi trigger
   - NON aprire posizioni se confidenza < 0.75

4. Volatilità ESTREMA (Volatility Ratio > 1.5 o ATR% > 6%):
   - Stop Loss: 2.0-2.5 * ATR%
   - Range: 6.0-10.0% (le crypto hanno oscillazioni ampie!)
   - ⚠️  CRITICO: NON aprire posizioni a meno che confidence >= 0.80
   - Reasoning obbligatorio: "Alta volatilità richiede SL ampio per evitare exit prematuri"
   - Se ATR% > 8%, EVITA di aprire (troppo rischioso anche con confidence alta)

LINEE GUIDA TAKE PROFIT:
- Take Profit minimo: 1.5x lo Stop Loss (risk/reward ratio)
- Trend forte + volatilità normale: TP = 3-4x Stop Loss (7-10%)
- Trend debole + volatilità alta: TP = 2x Stop Loss (4-6%)

ADATTAMENTO PER MODALITÀ TRADING:
- PAPER TRADING: Puoi essere più aggressivo
  * Stop Loss: range inferiore (es. 1.5-2.0 * ATR%)
  * Take Profit: range superiore (8-12%)
  * Accetta Volatility Ratio fino a 1.8 con confidenza 0.7+

- LIVE TRADING: Sii più conservativo
  * Stop Loss: range superiore (es. 2.5-3.5 * ATR%)
  * Take Profit: più realistico (5-8%)
  * Evita aperture con Volatility Ratio > 1.5 a meno di confidenza > 0.85

LIMITI ASSOLUTI:
- Stop Loss minimo: 1.5%
- Stop Loss massimo NORMALE: 6.0%
- Stop Loss massimo ALTA VOLATILITÀ (ATR% > 5%): 10.0%
  → Usa SL > 6% SOLO se ATR% > 5% E confidence >= 0.75
  → Reasoning obbligatorio: "ATR% elevato richiede SL ampio per oscillazioni normali"
- Take Profit minimo: 3.0%
- Take Profit massimo: 15.0%

⚠️  REGOLA CRITICA VOLATILITÀ:
Se ATR% > 5% E vuoi aprire posizione:
  1. Confidence DEVE essere >= 0.75 (alta volatilità = più rischio)
  2. Stop Loss DEVE essere >= 6% (dare spazio alle oscillazioni normali)
  3. Spiega nel reasoning perché il trade vale il rischio nonostante volatilità alta

ESEMPI PRATICI:
Scenario 1: BTC @ $50,000, ATR = $800 (1.6%), Volatility Ratio = 1.0 (normale)
→ Stop Loss raccomandato: 2.5 * 1.6% = 4.0% → -$2,000
→ Take Profit raccomandato: 3x SL = 12% → +$6,000

Scenario 2: ETH @ $3,000, ATR = $150 (5.0%), Volatility Ratio = 1.5 (alta)
→ Stop Loss raccomandato: 2.0 * 5.0% = 10% → CLAMP a 6.0% max = -$180
→ Take Profit raccomandato: 2x SL = 12% → +$360
→ ATTENZIONE: Valuta HOLD se confidenza < 0.75

DECISIONE FINALE:
- Analizza ATR%, Volatility Ratio, Trading Mode
- Calcola stop_loss_pct e take_profit_pct ottimali
- Spiega nel reasoning: "ATR analysis: [valori] → SL=[X]%, TP=[Y]% (volatility [normal/high/low])"

OUTPUT RICHIESTO:
Rispondi ESCLUSIVAMENTE con un JSON valido in questo formato esatto:
{{
    "action": "open" | "close" | "hold",
    "symbol": "BTC" | "ETH" | "SOL",
    "direction": "long" | "short" | null,
    "leverage": 1,
    "position_size_pct": 1.0-5.0,
    "stop_loss_pct": 3.0,
    "take_profit_pct": 5.0,
    "confidence": 0.0-1.0,
    "reasoning": "Spiegazione dettagliata con analisi indicatori, pesi e logica decisionale"
}}

REGOLE OUTPUT:
- NON includere testo prima o dopo il JSON
- NON usare markdown code blocks
- "leverage" deve essere SEMPRE 1 (Alpaca non supporta leva)
- "reasoning" deve essere esaustivo: spiega quali indicatori hanno pesato di più, perché, e come hai combinato i segnali
- Se action="hold", direction deve essere null
- Se action="close", direction deve essere null
- confidence deve riflettere la forza complessiva dei segnali ponderati"""


def build_user_prompt(
    symbol: str,
    portfolio: dict,
    market_data: dict,
    indicators: dict,
    pivot_points: dict,
    forecast: dict,
    orderbook: dict,
    sentiment: dict,
    news: list,
    open_positions: list,
    whale_flow: dict = None,
    coingecko: dict = None
) -> str:
    """
    Build the user prompt with all market data.

    Args:
        symbol: Trading symbol (BTC, ETH, SOL)
        portfolio: Portfolio information
        market_data: Current market data
        indicators: Technical indicators
        pivot_points: Pivot point levels
        forecast: Prophet forecast data
        orderbook: Order book data
        sentiment: Market sentiment
        news: Recent news items
        open_positions: Currently open positions
        whale_flow: Whale capital flow analysis
        coingecko: CoinGecko market data (global, trending, coins)

    Returns:
        Formatted user prompt string
    """
    positions_str = "Nessuna posizione aperta"
    if open_positions:
        positions_str = "\n".join([
            f"  - {p['symbol']}: {p['direction'].upper()} @ ${p['entry_price']:.2f}, "
            f"PnL: {p['unrealized_pnl_pct']:.2f}%"
            for p in open_positions
        ])

    news_str = "Nessuna news recente"
    if news:
        news_str = "\n".join([
            f"  - [{n.get('sentiment', 'neutral')}] {n['title'][:100]}"
            for n in news[:5]
        ])

    # Default whale_flow if None
    if whale_flow is None:
        whale_flow = {
            "inflow_exchange": 0,
            "outflow_exchange": 0,
            "net_flow": 0,
            "interpretation": "Dati non disponibili",
            "alert_count": 0
        }

    # Default coingecko if None
    if coingecko is None:
        coingecko = {
            "global": {},
            "trending": [],
            "trending_symbols": [],
            "tracked_trending": [],
            "coins": {}
        }

    # Build CoinGecko section
    global_data = coingecko.get("global", {})
    trending_symbols = coingecko.get("trending_symbols", [])
    tracked_trending = coingecko.get("tracked_trending", [])
    coin_data = coingecko.get("coins", {}).get(symbol, {})

    trending_str = ", ".join(trending_symbols[:7]) if trending_symbols else "N/A"
    tracked_trending_str = ", ".join(tracked_trending) if tracked_trending else "Nessuno"

    # Get coin-specific data from CoinGecko
    cg_price_change_1h = coin_data.get("price_change_percentage_1h", 0) or 0
    cg_price_change_24h = coin_data.get("price_change_percentage_24h", 0) or 0
    cg_price_change_7d = coin_data.get("price_change_percentage_7d", 0) or 0
    cg_market_cap = coin_data.get("market_cap", 0) or 0
    cg_volume = coin_data.get("total_volume", 0) or 0
    cg_ath_change = coin_data.get("ath_change_percentage", 0) or 0

    return f"""
=== ANALISI PER {symbol} ===

NOTA: Operiamo su Alpaca (spot trading, NO leva). Leverage sempre = 1.

📊 PORTFOLIO:
- Saldo USDC disponibile: ${portfolio.get('available_balance', 0):.2f}
- Equity totale: ${portfolio.get('total_equity', 0):.2f}
- Esposizione corrente: {portfolio.get('exposure_pct', 0):.1f}%
- Posizioni aperte:
{positions_str}

📈 DATI DI MERCATO {symbol}:
- Prezzo corrente: ${market_data.get('price', 0):.2f}
- Variazione 24h: {market_data.get('change_24h', 0):.2f}%
- Volume 24h: ${market_data.get('volume_24h', 0):,.0f}
- Bid: ${market_data.get('bid', 0):.2f}
- Ask: ${market_data.get('ask', 0):.2f}

📐 INDICATORI TECNICI:
- MACD: {indicators.get('macd', 0):.4f}
- MACD Signal: {indicators.get('macd_signal', 0):.4f}
- MACD Histogram: {indicators.get('macd_histogram', 0):.4f}
- RSI (14): {indicators.get('rsi', 50):.2f}
- EMA2: ${indicators.get('ema2', 0):.2f}
- EMA20: ${indicators.get('ema20', 0):.2f}
- Volume SMA: {indicators.get('volume_sma', 0):,.0f}

📊 VOLATILITY ANALYSIS (ATR):
- ATR (14): {indicators.get('atr', 0):.2f}
- ATR (30): {indicators.get('atr_30', 0):.2f}
- ATR as % of Price: {indicators.get('atr_pct', 0):.2f}%
- Volatility Ratio (ATR/ATR_30): {indicators.get('volatility_ratio', 1.0):.2f}
- Volatility Status: {_get_volatility_status(indicators.get('volatility_ratio', 1.0))}
- Trading Mode: {'PAPER' if portfolio.get('is_paper', True) else 'LIVE'}

Recommended SL/TP ranges based on ATR:
- Stop Loss range: {_get_atr_sl_range(indicators.get('atr_pct', 0), indicators.get('volatility_ratio', 1.0))}
- Take Profit range: {_get_atr_tp_range(indicators.get('atr_pct', 0), indicators.get('volatility_ratio', 1.0))}

🎯 PIVOT POINTS:
- PP (Pivot Point): ${pivot_points.get('pp', 0):.2f}
- R1: ${pivot_points.get('r1', 0):.2f}
- R2: ${pivot_points.get('r2', 0):.2f}
- S1: ${pivot_points.get('s1', 0):.2f}
- S2: ${pivot_points.get('s2', 0):.2f}
- Distanza da PP: {pivot_points.get('distance_pct', 0):.2f}%
- Vicino a resistenza: {'Sì' if pivot_points.get('near_resistance', False) else 'No'}
- Vicino a supporto: {'Sì' if pivot_points.get('near_support', False) else 'No'}

🔮 FORECAST PROPHET (4 ore):
- Trend previsto: {forecast.get('trend', 'LATERALE')}
- Prezzo target: ${forecast.get('target_price', 0):.2f}
- Variazione prevista: {forecast.get('change_pct', 0):.2f}%
- Confidenza: {forecast.get('confidence', 0):.2f}
- Range: ${forecast.get('lower_bound', 0):.2f} - ${forecast.get('upper_bound', 0):.2f}

📚 ORDER BOOK:
- Volume Bid (top 10): {orderbook.get('bid_volume', 0):,.2f}
- Volume Ask (top 10): {orderbook.get('ask_volume', 0):,.2f}
- Ratio Bid/Ask: {orderbook.get('ratio', 1):.3f}
- Interpretazione: {orderbook.get('interpretation', 'Neutro')}

🌡️ SENTIMENT DI MERCATO:
- Label: {sentiment.get('label', 'NEUTRAL')}
- Score: {sentiment.get('score', 50)}/100
- Interpretazione: {sentiment.get('interpretation', 'Neutro')}

📰 NEWS RECENTI:
{news_str}

🐋 WHALE ALERT (Movimenti Balene):
- Inflow verso exchange: ${whale_flow.get('inflow_exchange', 0):,.0f} (potenziale pressione di vendita)
- Outflow da exchange: ${whale_flow.get('outflow_exchange', 0):,.0f} (potenziale accumulo)
- Net Flow: ${whale_flow.get('net_flow', 0):,.0f} (positivo = bullish, negativo = bearish)
- Interpretazione: {whale_flow.get('interpretation', 'Dati non disponibili')}
- Transazioni monitorate: {whale_flow.get('alert_count', 0)}

🦎 COINGECKO MARKET DATA:
Mercato Globale:
- BTC Dominance: {global_data.get('btc_dominance', 0):.1f}% (alto = risk-off, basso = altcoin season)
- Total Market Cap: ${global_data.get('total_market_cap_usd', 0)/1e12:.2f}T
- Market Cap Change 24h: {global_data.get('market_cap_change_24h_pct', 0):+.2f}%

Trending Coins (top 7 più cercati):
- {trending_str}
- Nostre coin in trending: {tracked_trending_str}

Dati {symbol} da CoinGecko:
- Variazione 1h: {cg_price_change_1h:+.2f}%
- Variazione 24h: {cg_price_change_24h:+.2f}%
- Variazione 7d: {cg_price_change_7d:+.2f}%
- Market Cap: ${cg_market_cap/1e9:.2f}B
- Volume 24h: ${cg_volume/1e9:.2f}B
- Distanza da ATH: {cg_ath_change:.1f}%

Analizza tutti i dati sopra e fornisci la tua decisione di trading in formato JSON.
RICORDA: leverage deve essere SEMPRE 1 (Alpaca non supporta leva)."""


def get_decision_correction_prompt(error_message: str, original_response: str) -> str:
    """
    Generate a correction prompt when the LLM response is invalid.

    Args:
        error_message: Description of what was wrong
        original_response: The original invalid response

    Returns:
        Correction prompt
    """
    return f"""La tua risposta precedente non era valida.

ERRORE: {error_message}

TUA RISPOSTA ORIGINALE:
{original_response[:500]}

Per favore rispondi nuovamente con SOLO un JSON valido nel formato richiesto:
{{
    "action": "open" | "close" | "hold",
    "symbol": "BTC" | "ETH" | "SOL",
    "direction": "long" | "short" | null,
    "leverage": 1,
    "position_size_pct": 1.0-5.0,
    "stop_loss_pct": 3.0,
    "take_profit_pct": 5.0,
    "confidence": 0.0-1.0,
    "reasoning": "..."
}}

IMPORTANTE: leverage deve essere SEMPRE 1 (Alpaca non supporta leva).
NON includere testo aggiuntivo, SOLO il JSON."""


def _get_volatility_status(volatility_ratio: float) -> str:
    """Get human-readable volatility status."""
    if volatility_ratio < 0.8:
        return "LOW (calmer than usual)"
    elif volatility_ratio < 1.2:
        return "NORMAL (typical range)"
    elif volatility_ratio < 1.5:
        return "HIGH (elevated volatility)"
    else:
        return "EXTREME (very volatile - caution!)"


def _get_atr_sl_range(atr_pct: float, volatility_ratio: float) -> str:
    """Get recommended stop loss range based on ATR."""
    if not atr_pct or atr_pct <= 0:
        return "N/A (ATR data unavailable)"

    if volatility_ratio < 0.8:
        multiplier_min, multiplier_max = 2.5, 3.5
    elif volatility_ratio < 1.2:
        multiplier_min, multiplier_max = 2.0, 3.0
    elif volatility_ratio < 1.5:
        multiplier_min, multiplier_max = 1.5, 2.5
    else:
        multiplier_min, multiplier_max = 1.5, 2.0

    sl_min = max(1.5, min(6.0, atr_pct * multiplier_min))
    sl_max = max(1.5, min(6.0, atr_pct * multiplier_max))

    return f"{sl_min:.1f}% - {sl_max:.1f}%"


def _get_atr_tp_range(atr_pct: float, volatility_ratio: float) -> str:
    """Get recommended take profit range based on ATR."""
    if not atr_pct or atr_pct <= 0:
        return "N/A (ATR data unavailable)"

    # TP should be 2-4x the stop loss
    if volatility_ratio < 0.8:
        multiplier_min, multiplier_max = 2.5, 3.5
    elif volatility_ratio < 1.2:
        multiplier_min, multiplier_max = 2.0, 3.0
    else:
        multiplier_min, multiplier_max = 1.5, 2.5

    sl_avg = atr_pct * ((multiplier_min + multiplier_max) / 2)
    tp_min = max(3.0, min(15.0, sl_avg * 2))
    tp_max = max(3.0, min(15.0, sl_avg * 4))

    return f"{tp_min:.1f}% - {tp_max:.1f}%"


def get_system_prompt_for_scenario(
    action_context: str,
    market_regime: str
) -> str:
    """
    Ritorna prompt specializzato per scenario specifico.

    Args:
        action_context: "market_analysis", "close_position", ecc.
        market_regime: "normal", "high_volatility", "trending", "ranging"

    Returns:
        Specialized system prompt
    """
    # Base prompt (sempre incluso)
    base = get_system_prompt()

    # Scenario-specific additions
    scenario_extensions = {
        ("market_analysis", "high_volatility"): """

═══════════════════════════════════════════════════════
⚠️  SCENARIO: ALTA VOLATILITÀ
═══════════════════════════════════════════════════════

PRIORITÀ MODIFICATE (per alta volatilità):
1. ATR & Volatility Analysis (CRITICO) - peso aumentato a 0.30
2. Pivot Points S1/S2 (ESSENZIALE) - peso aumentato a 0.25, entry vicino supporto
3. Whale Flow (IMPORTANTE) - peso aumentato a 0.20, movimenti grandi
4. RSI + MACD (CONFERMA) - peso 0.20
5. News/Sentiment (SECONDARIO) - peso ridotto a 0.05, spesso rumore

REGOLE SPECIFICHE VOLATILITÀ ALTA:
- NO long se RSI > 65 (in alta volatilità overbought arriva prima)
- RICHIESTO: prezzo vicino a S1 (<1% distanza) O forte whale outflow (>$20M)
- Stop Loss: 1.5-2.0x ATR% (più stretto per proteggere capitale)
- Position Size: MAX 2% (ridotto rispetto a normale 5%)
- Take Profit: minimo 2x Stop Loss (risk/reward favorevole)
- Confidence minima: 0.75 (più alta del normale 0.6)

I WEIGHTED SCORES forniti riflettono già questi pesi adattati.""",

        ("market_analysis", "trending"): """

═══════════════════════════════════════════════════════
🔥 SCENARIO: COIN TRENDING
═══════════════════════════════════════════════════════

PRIORITÀ MODIFICATE (trending coin):
1. Momentum Indicators (CHIAVE) - peso 0.25, MACD + trend strength
2. News Analysis (IMPORTANTE) - peso aumentato a 0.20, trending spesso news-driven
3. CoinGecko Trending (SEGNALE) - peso aumentato a 0.15
4. Technical Indicators (SUPPORTO) - peso 0.20, RSI + supporti
5. Whale Flow (SECONDARIO) - peso ridotto a 0.10
6. Sentiment (CONFERMA) - peso aumentato a 0.15

REGOLE SPECIFICHE TRENDING:
- Se coin in top 3 trending CoinGecko → boost confidence +0.1
- News positive con impact >0.7 e relevance >0.8 → segnale molto forte
- ATTENZIONE: trending può essere late entry, verifica sempre RSI <70
- Position size: 2-4% (normale, trend può continuare)
- Se trending + news positive forti → considera position size verso il massimo

I WEIGHTED SCORES forniti riflettono già questi pesi adattati.""",

        ("market_analysis", "ranging"): """

═══════════════════════════════════════════════════════
📊 SCENARIO: MERCATO LATERALE
═══════════════════════════════════════════════════════

PRIORITÀ MODIFICATE (ranging market):
1. Pivot Points (CRITICI) - peso aumentato a 0.30, S/R sono tutto in range
2. RSI (ESSENZIALE) - Overbought/oversold molto affidabili in range
3. Technical Indicators (SUPPORTO) - peso 0.20
4. Forecast (LIMITATO) - peso ridotto a 0.15, meno affidabile in range
5. Altri indicatori (MINORI) - pesi ridotti

REGOLE SPECIFICHE RANGING:
- IDEALE: Buy vicino a S1/S2, Sell vicino a R1/R2
- RSI <30 vicino supporto = setup ottimale long
- RSI >70 vicino resistenza = setup ottimale short
- EVITA: Entrate nel mezzo del range senza segnali chiari
- Position size: 1-3% (più conservative, movimenti limitati)
- Take profit: più modesti (3-5%) dato il range limitato

I WEIGHTED SCORES forniti riflettono già questi pesi adattati.""",

        ("close_position", "any"): """

═══════════════════════════════════════════════════════
🎯 SCENARIO: VALUTAZIONE CHIUSURA POSIZIONE
═══════════════════════════════════════════════════════

PRIORITÀ CHIUSURA:
1. P&L vs Target (peso 0.40) - OBIETTIVO PRIMARIO
   → Take profit raggiunto? CHIUDI
   → P&L positivo + segnali reversal? CHIUDI e prendi profitto

2. Trend Reversal Signals (peso 0.30) - SEGNALI TECNICI
   → MACD crossover bearish (era bullish, ora bearish)
   → RSI divergence (prezzo alto ma RSI in calo)
   → Price below EMA20 (era sopra, ora sotto)
   → 2+ segnali reversal confermati = CHIUDI

3. News Impact (peso 0.20) - BREAKING NEWS
   → News molto negative con impact >0.8 e relevance >0.8
   → Sentiment shift drastico (da greed a fear)
   → Considera chiusura immediata se news critical

4. Whale Flow Reversal (peso 0.10) - INVERSIONE CAPITALE
   → Era outflow (accumulo), ora forte inflow (distribuzione)
   → Net flow inverted >$30M

CRITERI CHIUSURA AUTOMATICA:
✓ Take Profit raggiunto → CHIUDI SEMPRE
✓ Stop Loss vicino (<0.5% distanza) → CHIUDI (proteggi capitale)
✓ Trend reversal confermato (MACD + RSI + EMA) → CHIUDI
✓ News negative critiche (impact >0.8, relevance >0.8) → CHIUDI
✓ P&L > +3% E segnali reversal iniziali (1-2 indicatori) → CHIUDI (lock profit)
✓ P&L > +5% → CHIUDI SEMPRE (ottimo profitto, non essere greedy)

FILOSOFIA: "Non perdere profitti già guadagnati"
Meglio chiudere a +3% che aspettare e tornare a 0% o negativo.

I WEIGHTED SCORES forniti enfatizzano P&L e reversal signals."""
    }

    # Get scenario-specific extension
    key = (action_context, market_regime)
    if key in scenario_extensions:
        return base + scenario_extensions[key]

    # Fallback per close_position con qualsiasi regime
    if action_context == "close_position":
        key_fallback = ("close_position", "any")
        if key_fallback in scenario_extensions:
            return base + scenario_extensions[key_fallback]

    # Default: base prompt
    return base


def build_user_prompt_with_scores(
    symbol: str,
    portfolio: dict,
    market_data: dict,
    indicators: dict,
    pivot_points: dict,
    forecast: dict,
    orderbook: dict,
    sentiment: dict,
    news: list,
    open_positions: list,
    whale_flow: dict = None,
    coingecko: dict = None,
    weighted_scores: dict = None,      # NUOVO
    news_analysis: dict = None,        # NUOVO
    data_quality: dict = None          # NUOVO
) -> str:
    """
    Build user prompt includendo weighted scores e data quality.

    Questo è un upgrade di build_user_prompt() che aggiunge:
    - Composite score pre-calcolato
    - Component scores breakdown
    - Advanced news analysis
    - Data quality report

    Args:
        (stessi di build_user_prompt)
        weighted_scores: Weighted scores from data_weighting engine
        news_analysis: Advanced news analysis from news_analyzer
        data_quality: Data quality report from data_validator

    Returns:
        Enhanced user prompt string
    """
    # Base prompt (usa la funzione esistente)
    base_prompt = build_user_prompt(
        symbol, portfolio, market_data, indicators,
        pivot_points, forecast, orderbook, sentiment,
        news, open_positions, whale_flow, coingecko
    )

    # Add weighted scores section
    scores_section = ""
    if weighted_scores:
        scores_section = f"""

═══════════════════════════════════════════════════════
🎯 WEIGHTED DECISION SCORES (Pre-calcolati)
═══════════════════════════════════════════════════════

COMPOSITE SCORE: {weighted_scores.get('composite_score', 0):.3f} / 1.000
Confidence: {weighted_scores.get('confidence', 0):.2%}
Market Regime: {weighted_scores.get('market_regime', 'normal').upper()}

COMPONENT BREAKDOWN (score × weight = contribution):
"""

        components = weighted_scores.get('components', {})
        # Sort by contribution (descending)
        sorted_components = sorted(
            components.items(),
            key=lambda x: x[1].get('contribution', 0),
            reverse=True
        )

        for component, data in sorted_components:
            score = data.get('score', 0)
            weight = data.get('weight', 0)
            contribution = data.get('contribution', 0)

            scores_section += f"\n{component.replace('_', ' ').title()}:\n"
            scores_section += f"  Score: {score:.3f} | Weight: {weight:.2%} | Contribution: {contribution:.3f}\n"

            # Details (top 3)
            details = data.get('details', {})
            if details and isinstance(details, dict):
                for key, value in list(details.items())[:3]:
                    scores_section += f"    • {key}: {value}\n"

    # Add enhanced news analysis section
    news_section = ""
    if news_analysis and news_analysis.get("news_analyzed", 0) > 0:
        news_section = f"""

═══════════════════════════════════════════════════════
📰 NEWS ANALYSIS (Advanced Sentiment & Relevance)
═══════════════════════════════════════════════════════

Aggregate Sentiment: {news_analysis.get('aggregate_sentiment', 'neutral').upper()}
Sentiment Score: {news_analysis.get('sentiment_score', 0):+.3f} (-1=bearish, +1=bullish)
Overall Score: {news_analysis.get('overall_score', 0.5):.3f} / 1.000
Relevance Score: {news_analysis.get('relevance_score', 0):.3f} / 1.000
Impact Score: {news_analysis.get('impact_score', 0):.3f} / 1.000
Confidence: {news_analysis.get('confidence', 0):.2%}

Distribution: {news_analysis.get('sentiment_distribution', {})}

TOP RELEVANT NEWS (sorted by impact × relevance):
"""

        top_news = news_analysis.get('top_news', [])
        for i, news_item in enumerate(top_news[:3], 1):
            relevance = news_item.get('relevance', 0)
            impact = news_item.get('impact', 0)
            sentiment = news_item.get('sentiment', 'neutral')
            strength = news_item.get('sentiment_strength', 'weak')
            title = news_item.get('title', '')[:80]

            sentiment_emoji = {"positive": "📈", "negative": "📉", "neutral": "➡️"}.get(sentiment, "➡️")

            news_section += f"\n{i}. {sentiment_emoji} [{sentiment.upper()}/{strength.upper()}] {title}\n"
            news_section += f"   Relevance: {relevance:.2f} | Impact: {impact:.2f} | Weight: {news_item.get('weight', 0):.2f}\n"

    # Add data quality section
    quality_section = ""
    if data_quality:
        quality_section = f"""

═══════════════════════════════════════════════════════
✅ DATA QUALITY REPORT
═══════════════════════════════════════════════════════

Overall Quality: {data_quality.get('overall_quality', 0):.1%}
Recommendation: {data_quality.get('recommendation', 'UNKNOWN')}
"""

        warnings = data_quality.get('warnings', [])
        if warnings:
            quality_section += "\n⚠️  WARNINGS:\n"
            for warning in warnings:
                quality_section += f"  • {warning}\n"

        # Completeness summary
        completeness = data_quality.get('completeness', {})
        incomplete = [k for k, v in completeness.items() if not v.get('complete', True)]
        if incomplete:
            quality_section += f"\n❌ Incomplete Data: {', '.join(incomplete)}\n"

    # Add decision instructions
    instructions_section = """

═══════════════════════════════════════════════════════
📋 ISTRUZIONI DECISIONE CON WEIGHTED SCORES
═══════════════════════════════════════════════════════

Analizza il COMPOSITE SCORE e i COMPONENT SCORES forniti sopra.
Questi score sono già calcolati con i pesi ottimali per il regime di mercato corrente.

COME USARE GLI SCORE:
1. Guarda il COMPOSITE SCORE (0-1):
   - >0.7 = setup bullish forte → considera OPEN LONG
   - 0.4-0.7 = neutrale → probabilmente HOLD
   - <0.4 = setup bearish → considera SHORT o HOLD

2. Guarda il CONFIDENCE (0-1):
   - >0.8 = segnali molto allineati → alta affidabilità
   - 0.5-0.8 = segnali moderatamente allineati
   - <0.5 = segnali contrastanti → cautela, considera HOLD

3. Guarda i COMPONENT SCORES individuali:
   - Score alto (>0.7) = segnale forte in quella dimensione
   - Score basso (<0.3) = segnale opposto o debole
   - Identifica quali componenti sostengono la tua decisione

4. Guarda le CONTRIBUTION (score × weight):
   - Mostra quanto ogni componente contribuisce al composite score
   - I componenti con contribution maggiore sono i driver principali

REASONING STRUTTURATO RICHIESTO:
Nel tuo JSON, il campo "reasoning" deve essere un oggetto con questa struttura:
{{
    "reasoning": {{
        "summary": "Breve sintesi decisione (1-2 frasi)",
        "composite_analysis": "Composite score X.XX indica [interpretazione]",
        "primary_factors": [
            "Componente 1: score X.XX, contribuisce Y.YY, [interpretazione]",
            "Componente 2: score X.XX, contribuisce Y.YY, [interpretazione]",
            "Componente 3: score X.XX, contribuisce Y.YY, [interpretazione]"
        ],
        "supporting_factors": ["Fattore supporto 1", "Fattore supporto 2"],
        "risk_factors": ["Rischio 1", "Rischio 2"],
        "data_quality_note": "Data quality: X.XX [se ci sono warnings, menzionali]",
        "decision_confidence": <la tua confidence finale 0-1>
    }}
}}

IMPORTANTE: Usa gli score numerici pre-calcolati per giustificare la tua decisione.
Spiega QUALI score hanno guidato la decisione e PERCHÉ.

DECIDI ORA. Rispondi SOLO con JSON valido (nessun testo prima/dopo, nessun markdown).
"""

    # Combine all sections
    enhanced_prompt = (
        base_prompt +
        scores_section +
        news_section +
        quality_section +
        instructions_section
    )

    return enhanced_prompt
