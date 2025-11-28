"""
System prompts and templates for the LLM decision maker.
"""
from typing import Dict, Any, List
from config.settings import settings


def _build_news_section(news_data: dict, symbol: str) -> str:
    """
    Build advanced news section for LLM prompt from analyzed news data.

    Args:
        news_data: Analyzed news data from news_analyzer
        symbol: Trading symbol to focus on

    Returns:
        Formatted news section string
    """
    if not news_data:
        return "Nessuna news recente analizzata"

    # Extract key data
    aggregated = news_data.get("aggregated_sentiment", {})
    symbol_sentiment = news_data.get("symbol_sentiment", {})
    total_analyzed = news_data.get("total_analyzed", 0)
    high_impact_count = news_data.get("high_impact_count", 0)
    articles = news_data.get("articles", [])

    if total_analyzed == 0:
        return "Nessuna news recente analizzata"

    # Build sentiment summary
    sections = []

    # Aggregated sentiment
    agg_label = aggregated.get("label", "neutral").upper()
    agg_score = aggregated.get("score", 0)
    agg_confidence = aggregated.get("confidence", 0)
    agg_interpretation = aggregated.get("interpretation", "N/A")

    sections.append(f"""SENTIMENT NEWS AGGREGATO (basato su {total_analyzed} articoli AI-analizzati):
  - Sentiment: {agg_label} (score: {agg_score:.2f}, confidenza: {agg_confidence:.0%})
  - Interpretazione: {agg_interpretation}
  - News ad alto impatto: {high_impact_count}""")

    # Symbol-specific sentiment
    if isinstance(symbol_sentiment, dict) and symbol_sentiment:
        sym_label = symbol_sentiment.get("label", "neutral").upper()
        sym_score = symbol_sentiment.get("score", 0)
        sym_count = symbol_sentiment.get("article_count", 0)
        sections.append(f"""
  SENTIMENT SPECIFICO {symbol}:
  - Sentiment: {sym_label} (score: {sym_score:.2f})
  - Articoli rilevanti per {symbol}: {sym_count}""")

    # Top articles with AI summaries
    if articles:
        sections.append("\n  TOP NEWS ANALIZZATE:")
        for i, article in enumerate(articles[:7], 1):  # Show top 7
            sentiment_icon = {
                "very_bullish": "[++]",
                "bullish": "[+]",
                "neutral": "[~]",
                "bearish": "[-]",
                "very_bearish": "[--]"
            }.get(article.get("sentiment", "neutral"), "[~]")

            impact = article.get("impact", "low").upper()
            title = article.get("title", "N/A")[:80]
            summary = article.get("summary", "")[:120]
            age = article.get("age_hours", 0)
            source = article.get("source", "Unknown")
            key_points = article.get("key_points", [])

            sections.append(f"""
  {i}. {sentiment_icon} [{impact}] {title}
     Fonte: {source} | Età: {age:.1f}h | Score: {article.get('sentiment_score', 0):.2f}
     Riassunto AI: {summary}""")

            if key_points:
                sections.append(f"     Key point: {key_points[0][:80]}")

    return "\n".join(sections)


def get_system_prompt() -> str:
    """Return the system prompt for the trading LLM with dynamic strategy parameters."""
    strategy_name = settings.STRATEGY_NAME or "swing_trading"
    auto_close = settings.AUTO_CLOSE_AT_PROFIT_PCT

    # Build auto-close rule if enabled
    auto_close_rule = ""
    if auto_close:
        auto_close_rule = f"""

REGOLA AUTO-CLOSE (IMPORTANTE):
- Se una posizione ha profitto unrealized >= {auto_close}%, considera FORTEMENTE di chiudere per realizzare il gain
- Chiudi IMMEDIATAMENTE se non ci sono segnali MOLTO bullish che giustificano tenere
- Preferisci SEMPRE realizzare profitto piuttosto che rischiare reversal
- La strategia attiva richiede rotazione frequente delle posizioni
"""

    return f"""Sei un trader esperto di criptovalute specializzato in:
- Analisi tecnica avanzata
- Gestione del rischio rigorosa
- Identificazione di trend e pattern

═══════════════════════════════════════════════════════════
STRATEGIA ATTIVA: {strategy_name.upper().replace('_', ' ')}
═══════════════════════════════════════════════════════════

TUO COMPITO:
Analizza i dati di mercato forniti e decidi l'azione di trading ottimale.
Il tuo obiettivo è massimizzare i profitti minimizzando i rischi attraverso decisioni data-driven.
{auto_close_rule}
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
- Take profit raggiunto (+{settings.TP_RANGE_MIN}-{settings.TP_RANGE_MAX}% range target)
- Stop loss raggiunto (-{settings.SL_RANGE_MIN}-{settings.SL_RANGE_MAX}% range)
- Inversione segnali tecnici (es. long aperta ma MACD diventa negativo + RSI >75)
- Forecast cambia drasticamente direzione
- Sentiment passa da GREED a EXTREME FEAR o viceversa
- NEWS AI-ANALYZED: sentiment very_bearish con HIGH impact per posizioni long
- NEWS AI-ANALYZED: sentiment very_bullish con HIGH impact per posizioni short
- Sentiment news specifico per il symbol diventa fortemente opposto alla posizione

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
- Whale Flow: 0.65 (importante - outflow da exchange = accumulo bullish, inflow = distribuzione bearish)
- Forecast Prophet: 0.6 (importante per trend)
- NEWS AI-ANALYZED: 0.55 (IMPORTANTE - le news sono state analizzate con AI, considera sentiment aggregato e impatto)
- CoinGecko Data: 0.5 (importante per contesto mercato globale e trending)
- BTC Dominance: 0.5 (alto = risk-off/hold BTC, basso = altcoin opportunità)
- Order Book: 0.5 (moderatamente importante)
- Trending Coins: 0.4 (se la nostra coin è trending = maggiore interesse)
- Fear & Greed Index: 0.4 (contesto generale del mercato)

NOTA IMPORTANTE SULLE NEWS:
Le news sono state analizzate con DeepSeek AI, che ha:
- Fatto scraping completo degli articoli (non solo titoli)
- Calcolato sentiment preciso per ogni articolo
- Identificato news ad alto impatto
- Filtrato news vecchie (solo ultime 4 ore)
Considera SERIAMENTE il sentiment news aggregato, specialmente se:
- Ci sono news ad alto impatto (HIGH)
- Il sentiment è very_bullish o very_bearish con alta confidenza
- Il sentiment specifico per il symbol è fortemente direzionale

GESTIONE DINAMICA STOP LOSS E TAKE PROFIT:

Tu DEVI scegliere autonomamente i valori di stop_loss_pct e take_profit_pct per ogni trade.
NON usare valori fissi! Analizza il contesto e decidi valori appropriati.

LIMITI PER QUESTA STRATEGIA ({strategy_name.upper().replace('_', ' ')}):
- Stop Loss: range {settings.SL_RANGE_MIN}% - {settings.SL_RANGE_MAX}%
- Take Profit: range {settings.TP_RANGE_MIN}% - {settings.TP_RANGE_MAX}%
- Risk/Reward MINIMO: 1.5:1 NETTO (dopo fee Alpaca 0.30% round-trip)
  Esempio: SL 3% richiede TP almeno 4.8% (4.5% + 0.30% fee = 4.8% per R:R netto 1.5:1)

CRITERI PER SCEGLIERE STOP LOSS:

1. VOLATILITÀ (usa le metriche ATR fornite nei dati):
   - Bassa volatilità (ATR% < 2%, volatility_regime = "low"): SL sul lato basso del range
   - Media volatilità (ATR% 2-4%, volatility_regime = "medium"): SL medio del range
   - Alta volatilità (ATR% > 4%, volatility_regime = "high"): SL sul lato alto del range (per evitare stop out su rumore)
   - IMPORTANTE: usa suggested_sl_range come riferimento base

2. DISTANZA DAI PIVOT POINTS:
   - Se LONG vicino a S1: SL appena sotto S1 (calcola la % dalla entry)
   - Se LONG vicino a S2: SL appena sotto S2
   - Se SHORT vicino a R1: SL appena sopra R1
   - Usa i pivot come riferimento logico per lo stop

3. SENTIMENT E NEWS:
   - Sentiment EXTREME (Fear <20 o Greed >80): SL più largo +1-2% (alta volatilità attesa)
   - News molto impattanti recenti: SL più largo per tollerare spike

CRITERI PER SCEGLIERE TAKE PROFIT:

1. TIPO DI TRADE (ADATTA AL RANGE DELLA STRATEGIA {settings.TP_RANGE_MIN}-{settings.TP_RANGE_MAX}%):
   - Breakout (prezzo rompe R1/R2 o S1/S2): TP sul lato alto del range (momentum trade)
   - Mean Reversion (RSI estremo, prezzo a S2 o R2): TP medio del range (ritorno alla media)
   - Trend Following (MACD forte, EMA allineate): TP medio-alto del range
   - Scalp/Range (mercato laterale): TP sul lato basso del range

2. FORECAST PROPHET:
   - Se forecast change_pct > 5%: TP può essere più ambizioso
   - Se forecast change_pct 2-5%: TP moderato
   - Se forecast change_pct < 2%: TP conservativo

3. RESISTENZE/SUPPORTI TARGET:
   - LONG: TP vicino a R1 o R2 (dove il prezzo potrebbe fermarsi)
   - SHORT: TP vicino a S1 o S2
   - Calcola la % di distanza dal pivot target

4. CONFIDENZA DEL TRADE:
   - Confidenza > 0.8: puoi permetterti TP più ambizioso
   - Confidenza 0.6-0.8: TP conservativo, assicura il profitto

ESEMPI DI SCELTE TP/SL:

Esempio 1 - Alta volatilità + Breakout forte:
- Contesto: BTC rompe R1 con volume, MACD molto positivo, RSI 65
- SL: 5% (volatilità alta, serve spazio)
- TP: 10% (breakout momentum, R2 è lontano)
- R:R = 2:1 ✓

Esempio 2 - Bassa volatilità + Mean reversion:
- Contesto: ETH a S2, RSI 28 (oversold), MACD histogram in risalita
- SL: 2.5% (bassa volatilità, sotto S2)
- TP: 5% (target S1 o PP)
- R:R = 2:1 ✓

Esempio 3 - Mercato incerto + Sentiment estremo:
- Contesto: SOL laterale, Fear&Greed 15 (EXTREME FEAR), news negative
- SL: 6% (spike possibili)
- TP: 9% (potenziale rimbalzo violento)
- R:R = 1.5:1 ✓

IMPORTANTE:
- Spiega SEMPRE nel campo "tp_sl_reasoning" perché hai scelto quei valori specifici
- Il R:R deve essere SEMPRE almeno 1.5:1, preferibilmente 2:1 o superiore
- Adatta i valori al contesto specifico, NON usare sempre gli stessi numeri

OUTPUT RICHIESTO:
Rispondi ESCLUSIVAMENTE con un JSON valido in questo formato esatto:
{{
    "action": "open" | "close" | "hold",
    "symbol": "BTC" | "ETH" | "SOL",
    "direction": "long" | "short" | null,
    "leverage": 1,
    "position_size_pct": 1.0-5.0,
    "stop_loss_pct": 1.0-10.0,
    "take_profit_pct": 2.0-20.0,
    "confidence": 0.0-1.0,
    "tp_sl_reasoning": "Spiegazione di come hai scelto SL e TP: volatilità osservata, pivot di riferimento, tipo di trade, R:R ratio",
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
    news_data: dict,
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
        sentiment: Market sentiment (Fear & Greed Index)
        news_data: Advanced news analysis data with AI-powered sentiment
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

    # Build advanced news section from analyzed data
    news_str = _build_news_section(news_data, symbol)

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

📊 VOLATILITÀ (per TP/SL dinamico):
- ATR (14 periodi): ${indicators.get('atr_14', 0) or 0:.2f}
- ATR %: {indicators.get('atr_pct', 0) or 0:.2f}% (< 2% = bassa, 2-4% = media, > 4% = alta)
- Range giornaliero: {indicators.get('daily_range_pct', 0) or 0:.2f}%
- Range medio (14 candele): {indicators.get('avg_range_pct', 0) or 0:.2f}%
- Regime volatilità: {indicators.get('volatility_regime', 'unknown').upper()}
- SL suggerito: {indicators.get('suggested_sl_range', '3-5%')}
- TP suggerito: {indicators.get('suggested_tp_range', '5-8%')}

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
    "stop_loss_pct": 1.0-10.0,
    "take_profit_pct": 2.0-20.0,
    "confidence": 0.0-1.0,
    "tp_sl_reasoning": "Spiegazione scelta TP/SL dinamico",
    "reasoning": "..."
}}

IMPORTANTE:
- leverage deve essere SEMPRE 1 (Alpaca non supporta leva)
- stop_loss_pct e take_profit_pct devono essere DINAMICI basati sul contesto
- Risk/Reward ratio MINIMO 1.5:1 (TP >= SL * 1.5)
NON includere testo aggiuntivo, SOLO il JSON."""
