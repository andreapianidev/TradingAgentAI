"""
Streamlit dashboard for trading agent monitoring.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from database.connection import init_db, db_manager
from database.operations import db_ops
from exchange.exchange_factory import get_exchange_client
from exchange.portfolio import portfolio_manager

# Page config
st.set_page_config(
    page_title="Trading Agent Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .positive { color: #00FF00; }
    .negative { color: #FF4444; }
</style>
""", unsafe_allow_html=True)


def init_connections():
    """Initialize database and exchange connections."""
    if "initialized" not in st.session_state:
        try:
            init_db()
            exchange_client = get_exchange_client(auto_connect=True)
            st.session_state.exchange_client = exchange_client
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Initialization error: {e}")
            st.session_state.initialized = False


def render_sidebar():
    """Render the sidebar navigation."""
    st.sidebar.title("📈 Trading Agent")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Positions", "Trade History", "Market Analysis", "Settings"]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Last Update:** {datetime.now().strftime('%H:%M:%S')}")

    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (60s)", value=False)
    if auto_refresh:
        st.rerun()

    return page


def render_overview():
    """Render the overview page."""
    st.title("📊 Overview")

    # Get portfolio state
    try:
        portfolio = portfolio_manager.get_portfolio_state()
        stats = db_ops.get_trading_stats()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Equity",
            f"${portfolio.get('total_equity', 0):,.2f}",
            delta=f"{portfolio.get('total_pnl_pct', 0):.2f}%" if portfolio.get('total_pnl_pct') else None
        )

    with col2:
        st.metric(
            "Available Balance",
            f"${portfolio.get('available_balance', 0):,.2f}"
        )

    with col3:
        st.metric(
            "Exposure",
            f"{portfolio.get('exposure_pct', 0):.1f}%"
        )

    with col4:
        st.metric(
            "Open Positions",
            portfolio.get('open_positions_count', 0)
        )

    st.markdown("---")

    # Trading statistics
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Trading Statistics")
        stat_col1, stat_col2, stat_col3 = st.columns(3)

        with stat_col1:
            st.metric("Total Trades", stats.get('total_trades', 0))

        with stat_col2:
            win_rate = stats.get('win_rate', 0) * 100
            st.metric("Win Rate", f"{win_rate:.1f}%")

        with stat_col3:
            total_pnl = stats.get('total_pnl', 0)
            st.metric(
                "Total P&L",
                f"${total_pnl:,.2f}",
                delta_color="normal" if total_pnl >= 0 else "inverse"
            )

    with col2:
        st.subheader("📊 Win/Loss Distribution")
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)

        if wins + losses > 0:
            fig = px.pie(
                values=[wins, losses],
                names=['Wins', 'Losses'],
                color_discrete_sequence=['#00FF00', '#FF4444']
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No closed trades yet")

    # Equity curve
    st.markdown("---")
    st.subheader("📈 Equity Curve")

    equity_data = portfolio_manager.get_equity_curve(500)
    if equity_data:
        df = pd.DataFrame(equity_data)
        fig = px.line(
            df,
            x='timestamp',
            y='equity',
            title='Portfolio Equity Over Time'
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Time",
            yaxis_title="Equity (USDC)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity data available yet")

    # Recent trades
    st.markdown("---")
    st.subheader("🔄 Recent Trades")

    recent_trades = db_ops.get_recent_trade_decisions(limit=10)
    if recent_trades:
        trade_data = []
        for trade in recent_trades:
            trade_data.append({
                "Time": trade.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Symbol": trade.symbol,
                "Action": trade.action.upper(),
                "Direction": trade.direction.upper() if trade.direction else "-",
                "Confidence": f"{float(trade.confidence or 0):.2%}",
                "Status": trade.execution_status,
            })

        st.dataframe(pd.DataFrame(trade_data), use_container_width=True)
    else:
        st.info("No trades yet")


def render_positions():
    """Render the positions page."""
    st.title("📍 Positions")

    # Open positions from exchange
    portfolio = portfolio_manager.get_portfolio_state()
    positions = portfolio.get('positions', [])

    if positions:
        st.subheader("Open Positions")

        for pos in positions:
            with st.expander(f"{pos['symbol']} - {pos['direction'].upper()}", expanded=True):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Entry Price", f"${pos['entry_price']:,.2f}")

                with col2:
                    st.metric("Quantity", f"{pos['quantity']:.6f}")

                with col3:
                    st.metric("Leverage", f"{pos['leverage']}x")

                with col4:
                    pnl = pos.get('unrealized_pnl', 0)
                    pnl_pct = pos.get('unrealized_pnl_pct', 0)
                    st.metric(
                        "Unrealized P&L",
                        f"${pnl:,.2f}",
                        delta=f"{pnl_pct:.2f}%"
                    )

                if pos.get('liquidation_price'):
                    st.warning(f"⚠️ Liquidation Price: ${pos['liquidation_price']:,.2f}")

    else:
        st.info("No open positions")

    # Closed positions
    st.markdown("---")
    st.subheader("Closed Positions")

    closed = db_ops.get_closed_positions(limit=50)
    if closed:
        closed_data = []
        for pos in closed:
            closed_data.append({
                "Exit Time": pos.exit_timestamp.strftime("%Y-%m-%d %H:%M") if pos.exit_timestamp else "-",
                "Symbol": pos.symbol,
                "Direction": pos.direction.upper(),
                "Entry": f"${float(pos.entry_price):,.2f}",
                "Exit": f"${float(pos.exit_price):,.2f}" if pos.exit_price else "-",
                "P&L": f"${float(pos.realized_pnl or 0):,.2f}",
                "P&L %": f"{float(pos.realized_pnl_pct or 0):.2f}%",
                "Exit Reason": pos.exit_reason or "-",
            })

        st.dataframe(pd.DataFrame(closed_data), use_container_width=True)
    else:
        st.info("No closed positions")


def render_trade_history():
    """Render the trade history page."""
    st.title("📜 Trade History")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        symbol_filter = st.selectbox(
            "Symbol",
            ["All"] + settings.symbols_list
        )

    with col2:
        action_filter = st.selectbox(
            "Action",
            ["All", "open", "close", "hold"]
        )

    with col3:
        limit = st.number_input("Limit", min_value=10, max_value=500, value=100)

    # Get trades
    symbol = None if symbol_filter == "All" else symbol_filter
    trades = db_ops.get_recent_trade_decisions(symbol=symbol, limit=limit)

    if action_filter != "All":
        trades = [t for t in trades if t.action == action_filter]

    if trades:
        trade_data = []
        for trade in trades:
            trade_data.append({
                "Time": trade.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Symbol": trade.symbol,
                "Action": trade.action.upper(),
                "Direction": trade.direction.upper() if trade.direction else "-",
                "Leverage": trade.leverage or "-",
                "Size %": f"{float(trade.position_size_pct or 0):.1f}%",
                "Confidence": f"{float(trade.confidence or 0):.2%}",
                "Status": trade.execution_status,
                "Entry Price": f"${float(trade.entry_price):,.2f}" if trade.entry_price else "-",
            })

        df = pd.DataFrame(trade_data)
        st.dataframe(df, use_container_width=True)

        # Export button
        csv = df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "trade_history.csv",
            "text/csv"
        )

        # Show reasoning for selected trade
        st.markdown("---")
        st.subheader("Trade Details")

        selected_idx = st.selectbox(
            "Select trade to view reasoning",
            range(len(trades)),
            format_func=lambda i: f"{trades[i].timestamp} - {trades[i].symbol} {trades[i].action}"
        )

        if selected_idx is not None:
            trade = trades[selected_idx]
            st.markdown(f"**Reasoning:**")
            st.text(trade.reasoning or "No reasoning provided")

    else:
        st.info("No trades found")


def render_market_analysis():
    """Render the market analysis page."""
    st.title("📈 Market Analysis")

    symbol = st.selectbox("Symbol", settings.symbols_list)

    # Get latest market context
    context = db_ops.get_latest_market_context(symbol)

    if context:
        st.markdown(f"**Last Update:** {context.timestamp}")

        # Price and indicators
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Technical Indicators")
            st.metric("Price", f"${float(context.price):,.2f}")
            st.metric("RSI", f"{float(context.rsi or 0):.2f}")
            st.metric("MACD", f"{float(context.macd or 0):.6f}")
            st.metric("MACD Signal", f"{float(context.macd_signal or 0):.6f}")

        with col2:
            st.subheader("🎯 Pivot Points")
            st.metric("PP", f"${float(context.pivot_pp or 0):,.2f}")
            st.metric("R1", f"${float(context.pivot_r1 or 0):,.2f}")
            st.metric("R2", f"${float(context.pivot_r2 or 0):,.2f}")
            st.metric("S1", f"${float(context.pivot_s1 or 0):,.2f}")
            st.metric("S2", f"${float(context.pivot_s2 or 0):,.2f}")

        st.markdown("---")

        # Forecast
        st.subheader("🔮 Forecast")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Trend", context.forecast_trend or "N/A")

        with col2:
            st.metric("Target Price", f"${float(context.forecast_target_price or 0):,.2f}")

        with col3:
            st.metric("Confidence", f"{float(context.forecast_confidence or 0):.2%}")

        # Sentiment
        st.markdown("---")
        st.subheader("🌡️ Sentiment")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Label", context.sentiment_label or "N/A")

        with col2:
            st.metric("Score", f"{context.sentiment_score or 50}/100")

    else:
        st.info(f"No market data for {symbol}")


def render_settings():
    """Render the settings page."""
    st.title("⚙️ Settings")

    st.subheader("Current Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Trading Parameters**")
        st.text(f"Symbols: {', '.join(settings.symbols_list)}")
        st.text(f"Timeframe: {settings.TIMEFRAME}")
        st.text(f"Max Leverage: {settings.MAX_LEVERAGE}x")
        st.text(f"Max Position Size: {settings.MAX_POSITION_SIZE_PCT}%")
        st.text(f"Max Exposure: {settings.MAX_TOTAL_EXPOSURE_PCT}%")

    with col2:
        st.markdown("**Risk Parameters**")
        st.text(f"Stop Loss: {settings.STOP_LOSS_PCT}%")
        st.text(f"Take Profit: {settings.TAKE_PROFIT_PCT}%")
        st.text(f"Min Confidence: {settings.MIN_CONFIDENCE_THRESHOLD}")
        st.text(f"Testnet: {settings.HYPERLIQUID_TESTNET}")

    st.markdown("---")
    st.subheader("Manual Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Run Trading Cycle"):
            with st.spinner("Running cycle..."):
                try:
                    from core.agent import run_trading_cycle
                    result = run_trading_cycle()
                    st.success("Cycle completed!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        if st.button("🔌 Reconnect Exchange"):
            with st.spinner("Reconnecting..."):
                try:
                    exchange_client.disconnect()
                    exchange_client.connect()
                    st.success("Reconnected!")
                except Exception as e:
                    st.error(f"Error: {e}")


def main():
    """Main dashboard function."""
    init_connections()

    page = render_sidebar()

    if page == "Overview":
        render_overview()
    elif page == "Positions":
        render_positions()
    elif page == "Trade History":
        render_trade_history()
    elif page == "Market Analysis":
        render_market_analysis()
    elif page == "Settings":
        render_settings()


if __name__ == "__main__":
    main()
