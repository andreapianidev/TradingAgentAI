import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

export const dynamic = 'force-dynamic'

function getSupabaseClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables')
  }

  return createClient(supabaseUrl, supabaseKey)
}

async function callDeepSeekAPI(systemPrompt: string, userPrompt: string) {
  const apiKey = process.env.DEEPSEEK_API_KEY
  const baseUrl = process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com'
  const model = process.env.MODEL_NAME || 'deepseek-chat'

  if (!apiKey) {
    throw new Error('DEEPSEEK_API_KEY not configured')
  }

  const response = await fetch(`${baseUrl}/v1/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ],
      temperature: 0.3,
      max_tokens: 2000
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`DeepSeek API error: ${response.status} - ${error}`)
  }

  const data = await response.json()
  return {
    content: data.choices[0].message.content,
    usage: {
      input_tokens: data.usage.prompt_tokens,
      output_tokens: data.usage.completion_tokens,
      cached_tokens: data.usage.prompt_cache_hit_tokens || 0,
      cost_usd: calculateCost(data.usage),
      model,
      provider: 'deepseek'
    }
  }
}

function calculateCost(usage: any): number {
  // DeepSeek pricing: $0.27 per 1M input tokens, $1.10 per 1M output tokens
  const inputCost = (usage.prompt_tokens / 1_000_000) * 0.27
  const outputCost = (usage.completion_tokens / 1_000_000) * 1.10
  const cacheCostSavings = ((usage.prompt_cache_hit_tokens || 0) / 1_000_000) * 0.27 * 0.9 // 90% discount
  return inputCost + outputCost - cacheCostSavings
}

function parseAnalysisResponse(response: string): any | null {
  try {
    let cleaned = response.trim()
    cleaned = cleaned.replace(/^```json\s*/, '')
    cleaned = cleaned.replace(/\s*```$/, '')
    cleaned = cleaned.replace(/^```\s*/, '')

    // Try to find JSON in the response
    const jsonMatch = cleaned.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      cleaned = jsonMatch[0]
    }

    const analysis = JSON.parse(cleaned)

    // Validate required fields
    if (!analysis.summary_text || !analysis.market_outlook) {
      return null
    }

    return analysis
  } catch (e) {
    console.error('Failed to parse analysis response:', e)
    return null
  }
}

function getDefaultAnalysis(symbol: string, price: number, indicators: any, pivotPoints: any): any {
  const rsi = indicators.rsi || 50
  const macdBullish = indicators.macd_bullish || false

  let outlook = 'neutral'
  let summary = `${symbol} in fase di consolidamento. Attendere segnali più chiari prima di operare.`

  if (rsi > 70) {
    outlook = 'bearish'
    summary = `${symbol} mostra segnali di ipercomprato con RSI a ${rsi.toFixed(1)}. Si consiglia cautela per nuove posizioni long.`
  } else if (rsi < 30) {
    outlook = 'bullish'
    summary = `${symbol} in zona di ipervenduto con RSI a ${rsi.toFixed(1)}. Potenziale opportunità di acquisto.`
  } else if (macdBullish) {
    outlook = 'bullish'
    summary = `${symbol} mostra momentum positivo con MACD bullish. Trend in corso potrebbe continuare.`
  }

  return {
    summary_text: summary,
    market_outlook: outlook,
    confidence_score: 0.5,
    trend_strength: 'moderate',
    momentum: 'stable',
    volatility_level: 'medium',
    key_levels: {
      resistance_1: pivotPoints.r1 || price * 1.02,
      resistance_2: pivotPoints.r2 || price * 1.05,
      support_1: pivotPoints.s1 || price * 0.98,
      support_2: pivotPoints.s2 || price * 0.95
    },
    risk_factors: ['Volatilità di mercato', 'Sentiment incerto'],
    opportunities: ['Livelli chiave da monitorare']
  }
}

export async function POST(request: NextRequest) {
  try {
    const { symbol } = await request.json()

    if (!symbol || !['BTC', 'ETH', 'SOL'].includes(symbol)) {
      return NextResponse.json(
        { error: 'Invalid symbol. Must be BTC, ETH, or SOL' },
        { status: 400 }
      )
    }

    const supabase = getSupabaseClient()

    // Get latest market context
    const { data: context, error: contextError } = await supabase
      .from('trading_market_contexts')
      .select('*')
      .eq('symbol', symbol)
      .order('timestamp', { ascending: false })
      .limit(1)
      .single()

    if (contextError || !context) {
      return NextResponse.json(
        { error: 'No market context found for this symbol' },
        { status: 404 }
      )
    }

    // Extract data from context
    const price = parseFloat(String(context.price))
    const indicators = {
      rsi: context.rsi,
      macd: context.macd,
      macd_signal: context.macd_signal,
      macd_histogram: context.macd_histogram,
      ema2: context.ema2,
      ema20: context.ema20,
      macd_bullish: (context.macd || 0) > (context.macd_signal || 0),
      price_above_ema20: price > parseFloat(String(context.ema20 || 0))
    }
    const pivotPoints = {
      pp: context.pivot_pp,
      r1: context.pivot_r1,
      r2: context.pivot_r2,
      s1: context.pivot_s1,
      s2: context.pivot_s2
    }
    const forecast = {
      trend: context.forecast_trend,
      target_price: context.forecast_target_price,
      change_pct: context.forecast_change_pct
    }
    const sentiment = {
      score: context.sentiment_score || 50,
      label: context.sentiment_label || 'NEUTRAL'
    }

    // Build news summary from raw_data if available
    let newsData: any = {}
    if (context.raw_data?.news) {
      const news = context.raw_data.news
      newsData = {
        total_analyzed: news.length,
        high_impact_count: 0,
        aggregated_sentiment: {
          score: 50,
          label: 'neutral',
          interpretation: 'N/A'
        },
        symbol_sentiment: {
          score: 50,
          label: 'neutral'
        }
      }
    }

    // Build whale flow from raw_data if available
    let whaleFlow: any = null
    if (context.raw_data?.whale_flow) {
      whaleFlow = context.raw_data.whale_flow
    }

    // Build prompts
    const systemPrompt = `Sei un analista finanziario esperto di criptovalute.
Genera un'analisi di mercato concisa e professionale in italiano.
La tua analisi deve essere oggettiva, basata sui dati forniti, e utile per i trader.
Rispondi SOLO con un JSON valido senza markdown o commenti.`

    const newsAggregate = newsData.aggregated_sentiment || {}
    const symbolSentiment = newsData.symbol_sentiment || {}
    const newsSummary = newsData.total_analyzed ? `NEWS SENTIMENT (AI-analyzed):
- Articles analyzed: ${newsData.total_analyzed}
- High impact news: ${newsData.high_impact_count}
- Aggregated score: ${newsAggregate.score?.toFixed(2)} (${newsAggregate.label})
- ${symbol} specific: ${symbolSentiment.score?.toFixed(2)} (${symbolSentiment.label})
- Interpretation: ${newsAggregate.interpretation}` : ''

    const whaleSummary = whaleFlow ? `Whale Flow: $${whaleFlow.net_flow?.toLocaleString()} net (${whaleFlow.interpretation})` : ''

    const userPrompt = `Analizza ${symbol}/USD e genera un report di mercato.

DATI ATTUALI:
- Prezzo: $${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
- RSI (14): ${indicators.rsi?.toFixed(1)}
- MACD: ${indicators.macd?.toFixed(4)} (Signal: ${indicators.macd_signal?.toFixed(4)})
- MACD Trend: ${indicators.macd_bullish ? 'Bullish' : 'Bearish'}
- EMA2: $${indicators.ema2?.toFixed(2)} | EMA20: $${indicators.ema20?.toFixed(2)}
- Price vs EMA20: ${indicators.price_above_ema20 ? 'Above' : 'Below'}

PIVOT POINTS:
- R2: $${pivotPoints.r2?.toFixed(2)}
- R1: $${pivotPoints.r1?.toFixed(2)}
- PP: $${pivotPoints.pp?.toFixed(2)}
- S1: $${pivotPoints.s1?.toFixed(2)}
- S2: $${pivotPoints.s2?.toFixed(2)}

FORECAST (4h):
- Trend: ${forecast.trend || 'N/A'}
- Target: $${forecast.target_price?.toFixed(2)}
- Change: ${forecast.change_pct >= 0 ? '+' : ''}${forecast.change_pct?.toFixed(2)}%

SENTIMENT:
- Fear & Greed: ${sentiment.score} (${sentiment.label})
${newsSummary}
${whaleSummary}

Genera un JSON con questa struttura esatta:
{
    "summary_text": "Analisi di 3-4 frasi concise che descrivono la situazione attuale del mercato, i livelli chiave e le prospettive a breve termine.",
    "market_outlook": "bullish|bearish|neutral|volatile",
    "confidence_score": 0.0-1.0,
    "trend_strength": "strong|moderate|weak",
    "momentum": "increasing|decreasing|stable",
    "volatility_level": "high|medium|low",
    "key_levels": {
        "resistance_1": numero,
        "resistance_2": numero,
        "support_1": numero,
        "support_2": numero
    },
    "risk_factors": ["rischio 1", "rischio 2"],
    "opportunities": ["opportunità 1", "opportunità 2"]
}`

    // Call DeepSeek API
    let analysis: any
    let usage: any = {}

    try {
      const response = await callDeepSeekAPI(systemPrompt, userPrompt)
      usage = response.usage

      // Parse response
      analysis = parseAnalysisResponse(response.content)

      if (!analysis) {
        console.warn('Failed to parse DeepSeek response, using default analysis')
        analysis = getDefaultAnalysis(symbol, price, indicators, pivotPoints)
      }

      // Log the conversation
      try {
        await supabase.from('trading_bot_logs').insert({
          level: 'INFO',
          message: 'Manual AI analysis generated',
          details: {
            type: 'manual_analysis',
            symbol,
            system_prompt_preview: systemPrompt.substring(0, 200),
            user_prompt_preview: userPrompt.substring(0, 500),
            system_prompt_length: systemPrompt.length,
            user_prompt_length: userPrompt.length
          }
        })

        await supabase.from('trading_bot_logs').insert({
          level: 'INFO',
          message: 'Manual AI analysis response',
          details: {
            type: 'manual_analysis_response',
            symbol,
            raw_response: response.content.substring(0, 2000),
            parsed_analysis: analysis
          }
        })
      } catch (logError) {
        console.warn('Failed to log conversation:', logError)
      }

      // Save LLM cost
      if (usage.cost_usd > 0) {
        try {
          await supabase.from('trading_llm_costs').insert({
            symbol,
            input_tokens: usage.input_tokens,
            output_tokens: usage.output_tokens,
            cached_tokens: usage.cached_tokens,
            cost_usd: usage.cost_usd,
            model: usage.model,
            details: {
              provider: usage.provider,
              type: 'manual_daily_analysis',
              triggered_by: 'user'
            }
          })
        } catch (costError) {
          console.warn('Failed to save LLM cost:', costError)
        }
      }
    } catch (apiError) {
      console.error('DeepSeek API error:', apiError)
      analysis = getDefaultAnalysis(symbol, price, indicators, pivotPoints)
    }

    // Save analysis to database
    const analysisData = {
      analysis_date: new Date().toISOString().split('T')[0], // Today's date YYYY-MM-DD
      symbol,
      summary_text: analysis.summary_text,
      market_outlook: analysis.market_outlook,
      confidence_score: analysis.confidence_score || 0.5,
      key_levels: analysis.key_levels,
      risk_factors: analysis.risk_factors,
      opportunities: analysis.opportunities,
      trend_strength: analysis.trend_strength,
      momentum: analysis.momentum,
      volatility_level: analysis.volatility_level,
      indicators_snapshot: indicators,
      news_sentiment_summary: newsData,
      trading_mode: 'paper'
    }

    const { data: savedAnalysis, error: saveError } = await supabase
      .from('trading_ai_analysis')
      .upsert(analysisData, { onConflict: 'analysis_date,symbol' })
      .select()
      .single()

    if (saveError) {
      console.error('Failed to save analysis:', saveError)
      return NextResponse.json(
        { error: 'Failed to save analysis', details: saveError.message },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      analysis: savedAnalysis,
      usage: {
        input_tokens: usage.input_tokens,
        output_tokens: usage.output_tokens,
        cost_usd: usage.cost_usd?.toFixed(6)
      }
    })
  } catch (error: any) {
    console.error('Error generating analysis:', error)
    return NextResponse.json(
      { error: 'Internal server error', details: error.message },
      { status: 500 }
    )
  }
}
