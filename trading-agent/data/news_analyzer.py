"""
Advanced News Analyzer - Sentiment, Relevance e Impact scoring per news.

Questo modulo migliora l'analisi delle news andando oltre il semplice keyword matching:
- Relevance scoring: quanto una news è rilevante per lo specifico symbol
- Context-aware sentiment: analisi sentiment considerando il contesto
- Impact scoring: stima dell'impatto potenziale sul prezzo
- Aggregation: score aggregato pesato di tutte le news
"""
from typing import Dict, Any, List

from utils.logger import get_logger

logger = get_logger(__name__)


class NewsAnalyzer:
    """Advanced news sentiment and relevance analyzer."""

    # Symbol-specific keywords per determinare relevance
    SYMBOL_KEYWORDS = {
        "BTC": {
            "direct": ["bitcoin", "btc"],
            "related": ["crypto", "cryptocurrency", "digital currency", "digital gold"],
            "high_impact": ["etf", "sec approval", "mining", "halving", "spot etf"]
        },
        "ETH": {
            "direct": ["ethereum", "eth", "ether"],
            "related": ["smart contract", "defi", "layer 2", "dapp"],
            "high_impact": ["merge", "shanghai upgrade", "eip", "gas fees", "staking"]
        },
        "SOL": {
            "direct": ["solana", "sol"],
            "related": ["nft", "web3", "blockchain"],
            "high_impact": ["outage", "network", "validator", "downtime"]
        }
    }

    # Sentiment keywords espansi con categorizzazione per strength
    POSITIVE_KEYWORDS = {
        "strong": ["breakthrough", "record", "surge", "soar", "rally", "milestone",
                   "approval", "launch", "adoption", "institutional"],
        "moderate": ["gain", "rise", "growth", "increase", "partnership", "upgrade",
                     "positive", "bullish", "optimistic"],
        "weak": ["recovery", "stabilize", "improve", "slight gain", "modest"]
    }

    NEGATIVE_KEYWORDS = {
        "strong": ["crash", "plunge", "hack", "scam", "fraud", "ban", "collapse",
                   "exploit", "stolen", "regulation", "lawsuit"],
        "moderate": ["fall", "drop", "decline", "decrease", "warning", "concern",
                     "dump", "bearish", "pessimistic"],
        "weak": ["correction", "pullback", "dip", "slight decline"]
    }

    def analyze_news_for_symbol(
        self,
        symbol: str,
        news_list: List[Dict[str, Any]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Analizza news con relevance, sentiment e impact scoring.

        Args:
            symbol: Trading symbol (BTC, ETH, SOL)
            news_list: Lista di news da analizzare (se None, usa get_recent_news)
            limit: Numero massimo di news da analizzare

        Returns:
            Analisi aggregata con score composito
        """
        # Se non fornita lista, importa e usa get_recent_news
        if news_list is None:
            try:
                from data.news_feed import get_recent_news
                news_list = get_recent_news(limit)
            except Exception as e:
                logger.warning(f"Error getting news: {e}")
                news_list = []

        if not news_list:
            return self._default_analysis(symbol)

        # Analizza ogni news
        analyzed_news = []
        total_weighted_sentiment = 0
        total_weight = 0

        for news_item in news_list:
            try:
                analysis = self._analyze_single_news(news_item, symbol)
                analyzed_news.append(analysis)

                # Weighted sentiment (più peso a news rilevanti e impattanti)
                weight = analysis["relevance"] * analysis["impact"]
                total_weighted_sentiment += analysis["sentiment_numeric"] * weight
                total_weight += weight

            except Exception as e:
                logger.debug(f"Error analyzing news item: {e}")
                continue

        if not analyzed_news:
            return self._default_analysis(symbol)

        # Sort by (impact * relevance) descending
        analyzed_news.sort(
            key=lambda x: x["relevance"] * x["impact"],
            reverse=True
        )

        # Aggregate sentiment (weighted average)
        avg_sentiment = total_weighted_sentiment / total_weight if total_weight > 0 else 0

        # Sentiment distribution
        sentiment_dist = {
            "positive": sum(1 for n in analyzed_news if n["sentiment"] == "positive"),
            "negative": sum(1 for n in analyzed_news if n["sentiment"] == "negative"),
            "neutral": sum(1 for n in analyzed_news if n["sentiment"] == "neutral")
        }

        # Overall score (0-1, dove 0.5 = neutro)
        overall_score = (avg_sentiment + 1) / 2  # Convert from -1/+1 to 0/1

        # Aggregate sentiment label
        if avg_sentiment > 0.3:
            agg_sentiment = "positive"
        elif avg_sentiment < -0.3:
            agg_sentiment = "negative"
        else:
            agg_sentiment = "neutral"

        # Calculate aggregate relevance and impact
        avg_relevance = sum(n["relevance"] for n in analyzed_news) / len(analyzed_news)
        avg_impact = sum(n["impact"] for n in analyzed_news) / len(analyzed_news)

        # Calculate confidence
        confidence = self._calculate_confidence(analyzed_news)

        return {
            "symbol": symbol,
            "news_analyzed": len(analyzed_news),
            "aggregate_sentiment": agg_sentiment,
            "sentiment_score": round(avg_sentiment, 3),  # -1 to +1
            "overall_score": round(overall_score, 3),    # 0 to 1
            "relevance_score": round(avg_relevance, 3),
            "impact_score": round(avg_impact, 3),
            "sentiment_distribution": sentiment_dist,
            "top_news": analyzed_news[:3],  # Top 3 più rilevanti
            "confidence": confidence
        }

    def _analyze_single_news(
        self,
        news_item: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """
        Analizza singola news con relevance, sentiment, impact.

        Returns:
            News item arricchito con score
        """
        title = news_item.get("title", "")
        summary = news_item.get("summary", "")
        text = f"{title} {summary}".lower()

        # Relevance scoring (quanto è rilevante per questo symbol)
        relevance = self._calculate_relevance(text, symbol)

        # Enhanced sentiment analysis (context-aware)
        sentiment, sentiment_numeric, strength = self._analyze_sentiment_advanced(text)

        # Impact scoring (quanto può impattare il prezzo)
        impact = self._calculate_impact(text, symbol, strength)

        return {
            **news_item,
            "relevance": round(relevance, 3),
            "sentiment": sentiment,
            "sentiment_numeric": round(sentiment_numeric, 3),  # -1 to +1
            "sentiment_strength": strength,
            "impact": round(impact, 3),
            "weight": round(relevance * impact, 3)  # Peso nel calcolo aggregato
        }

    def _calculate_relevance(self, text: str, symbol: str) -> float:
        """
        Calcola relevance score 0-1.

        Score alto se:
        - Menzione diretta del symbol
        - Termini high-impact rilevanti
        - Termini related rilevanti

        Returns:
            1.0 = menzione diretta + high impact term
            0.9 = menzione diretta
            0.7 = related term + high impact
            0.5 = related term
            0.3 = crypto generico
            0.1 = non rilevante
        """
        keywords = self.SYMBOL_KEYWORDS.get(symbol, {})

        # Check direct mention
        direct_keywords = keywords.get("direct", [])
        has_direct = any(kw in text for kw in direct_keywords)

        # Check related terms
        related_keywords = keywords.get("related", [])
        has_related = any(kw in text for kw in related_keywords)

        # Check high impact terms
        high_impact_keywords = keywords.get("high_impact", [])
        has_high_impact = any(kw in text for kw in high_impact_keywords)

        # Calcola score
        if has_direct and has_high_impact:
            return 1.0
        elif has_direct:
            return 0.9
        elif has_related and has_high_impact:
            return 0.7
        elif has_related:
            return 0.5
        elif "crypto" in text or "cryptocurrency" in text:
            return 0.3
        else:
            return 0.1

    def _analyze_sentiment_advanced(self, text: str) -> tuple:
        """
        Analisi sentiment context-aware.

        Migliora il semplice keyword matching considerando:
        - Strength delle keyword (strong/moderate/weak)
        - Negazioni nel testo
        - Combinazioni di termini

        Returns:
            (sentiment_label, sentiment_numeric, strength)
            sentiment_label: "positive" | "negative" | "neutral"
            sentiment_numeric: -1.0 to +1.0
            strength: "strong" | "moderate" | "weak"
        """
        # Count positive keywords by strength
        pos_strong = sum(1 for kw in self.POSITIVE_KEYWORDS["strong"] if kw in text)
        pos_moderate = sum(1 for kw in self.POSITIVE_KEYWORDS["moderate"] if kw in text)
        pos_weak = sum(1 for kw in self.POSITIVE_KEYWORDS["weak"] if kw in text)

        # Count negative keywords by strength
        neg_strong = sum(1 for kw in self.NEGATIVE_KEYWORDS["strong"] if kw in text)
        neg_moderate = sum(1 for kw in self.NEGATIVE_KEYWORDS["moderate"] if kw in text)
        neg_weak = sum(1 for kw in self.NEGATIVE_KEYWORDS["weak"] if kw in text)

        # Weighted scoring
        pos_score = pos_strong * 1.0 + pos_moderate * 0.6 + pos_weak * 0.3
        neg_score = neg_strong * 1.0 + neg_moderate * 0.6 + neg_weak * 0.3

        # Context checks (negazioni che invertono il sentiment)
        negation_terms = ["not", "no", "never", "don't", "doesn't", "won't", "isn't", "aren't"]
        has_negation = any(term in text for term in negation_terms)

        # Se c'è negazione, inverti score (approssimazione semplice)
        if has_negation:
            pos_score, neg_score = neg_score, pos_score

        # Determine sentiment
        if pos_score > neg_score:
            # Positive sentiment
            if pos_score >= 2:
                strength = "strong"
                numeric = 0.8
            elif pos_score >= 1:
                strength = "moderate"
                numeric = 0.5
            else:
                strength = "weak"
                numeric = 0.3
            return "positive", numeric, strength

        elif neg_score > pos_score:
            # Negative sentiment
            if neg_score >= 2:
                strength = "strong"
                numeric = -0.8
            elif neg_score >= 1:
                strength = "moderate"
                numeric = -0.5
            else:
                strength = "weak"
                numeric = -0.3
            return "negative", numeric, strength

        else:
            # Neutral sentiment
            return "neutral", 0.0, "weak"

    def _calculate_impact(
        self,
        text: str,
        symbol: str,
        sentiment_strength: str
    ) -> float:
        """
        Calcola impact score 0-1 basato su:
        - Tipo di news (regulatory, technical, market)
        - Sentiment strength
        - Symbol-specific high-impact terms

        Returns:
            Score 0.0-1.0 (quanto la news può impattare il prezzo)
        """
        # High impact terms generali
        regulatory_terms = ["sec", "regulation", "ban", "law", "government", "legal"]
        technical_terms = ["upgrade", "fork", "merge", "protocol", "network", "mainnet"]
        market_terms = ["etf", "institution", "adoption", "volume", "liquidity", "trading"]

        # Base impact
        base_impact = 0.5

        # Type boost (news regolamentari hanno impact maggiore)
        if any(term in text for term in regulatory_terms):
            base_impact += 0.3  # Regulatory news = alto impatto
        if any(term in text for term in technical_terms):
            base_impact += 0.2  # Technical news = moderato impatto
        if any(term in text for term in market_terms):
            base_impact += 0.2  # Market news = moderato impatto

        # Strength multiplier (sentiment forte = impatto maggiore)
        strength_multiplier = {
            "strong": 1.0,
            "moderate": 0.7,
            "weak": 0.4
        }
        base_impact *= strength_multiplier.get(sentiment_strength, 0.5)

        # Symbol-specific high-impact boost
        keywords = self.SYMBOL_KEYWORDS.get(symbol, {})
        high_impact_kw = keywords.get("high_impact", [])
        if any(kw in text for kw in high_impact_kw):
            base_impact += 0.1

        # Cap a 1.0
        return min(1.0, base_impact)

    def _calculate_confidence(self, analyzed_news: List[Dict]) -> float:
        """
        Calcola confidence nel news analysis.

        Confidence alta quando:
        - Ci sono molte news rilevanti
        - Il sentiment è consistente (tutte positive o tutte negative)
        - La rilevanza media è alta

        Returns:
            Score 0.0-1.0
        """
        if not analyzed_news:
            return 0.0

        num_news = len(analyzed_news)
        avg_relevance = sum(n["relevance"] for n in analyzed_news) / num_news

        # Consistenza sentiment (tutte positive o tutte negative = alta confidence)
        sentiments = [n["sentiment"] for n in analyzed_news]
        positive_ratio = sentiments.count("positive") / num_news
        negative_ratio = sentiments.count("negative") / num_news
        max_ratio = max(positive_ratio, negative_ratio)

        # Calcola confidence composito
        confidence = (
            min(1.0, num_news / 5) * 0.4 +    # più news = meglio (cap a 5)
            avg_relevance * 0.3 +               # più rilevanti = meglio
            max_ratio * 0.3                     # più consistenti = meglio
        )

        return round(confidence, 3)

    def _default_analysis(self, symbol: str) -> Dict[str, Any]:
        """Default analysis quando non ci sono news."""
        return {
            "symbol": symbol,
            "news_analyzed": 0,
            "aggregate_sentiment": "neutral",
            "sentiment_score": 0.0,
            "overall_score": 0.5,
            "relevance_score": 0.0,
            "impact_score": 0.0,
            "sentiment_distribution": {
                "positive": 0,
                "negative": 0,
                "neutral": 0
            },
            "top_news": [],
            "confidence": 0.0
        }


# Global instance
news_analyzer = NewsAnalyzer()
