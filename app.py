import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Family Stock Dashboard", layout="wide", page_icon="📈")

# ==================================================
# PASSWORD
# ==================================================
PASSWORD = "family2025"   # ← change this to whatever you want

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("""
        <style>
        .login-box {
            max-width: 400px;
            margin: 10vh auto;
            padding: 2.5rem;
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
            text-align: center;
        }
        .login-title {
            font-size: 2rem;
            font-weight: 700;
            color: #f1f5f9;
            margin-bottom: 0.25rem;
        }
        .login-sub {
            color: #64748b;
            margin-bottom: 2rem;
            font-size: 0.95rem;
        }
        </style>
        <div class="login-box">
            <div class="login-title">📈 Stock Dashboard</div>
            <div class="login-sub">Family Watchlist — Enter password to continue</div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed",
                            placeholder="Enter password...")
        if st.button("Login", use_container_width=True):
            if pwd == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

# ==================================================
# DEFAULT TICKERS
# ==================================================
DEFAULT_TICKERS = [
    "IREDA.NS", "BEL.NS", "AFFLE.NS", "HAVELLS.NS", "POLYCAB.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "ICICIGI.NS", "HDFCAMC.NS", "HDFCBANK.NS",
    "CDSL.NS", "NSDL.NS", "CAMS.NS", "KFINTECH.NS", "POWERINDIA.NS",
    "ABB.NS", "PAGEIND.NS", "MAZDOCK.NS", "COCHINSHIP.NS", "HAL.NS",
    "VOLTAS.NS", "WONDERLA.NS", "NAUKRI.NS", "ICICIAMC.NS", "SUPREMEIND.NS",
    "TATAELXSI.NS", "LT.NS", "SBIN.NS", "TCS.NS", "LTTS.NS",
    "INFY.NS", "VARUNBEV.NS"
]

if "tickers" not in st.session_state:
    st.session_state.tickers = DEFAULT_TICKERS.copy()

# ==================================================
# HELPERS — TECHNICAL
# ==================================================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def bollinger_label(close):
    ma = close.rolling(20).mean().iloc[-1]
    sd = close.rolling(20).std().iloc[-1]
    upper = ma + 2 * sd
    lower = ma - 2 * sd
    last = close.iloc[-1]
    zone = (upper - lower) * 0.20
    if last >= upper:
        return "Overbought"
    elif last <= lower:
        return "Oversold"
    elif last <= lower + zone:
        return "Underbought"
    return "Neutral"

def ma_cross(close):
    if len(close) < 200:
        return "NA"
    ma50 = close.tail(50).mean()
    ma200 = close.tail(200).mean()
    return "Golden Cross" if ma50 > ma200 else "Death Cross"

def momentum_label(close):
    if len(close) < 126:
        return "NA"
    r1 = (close.iloc[-1] / close.iloc[-21] - 1) * 100
    r3 = (close.iloc[-1] / close.iloc[-63] - 1) * 100
    r6 = (close.iloc[-1] / close.iloc[-126] - 1) * 100
    score = 0.5*r1 + 0.3*r3 + 0.2*r6
    if score >= 20:   return "Overbought"
    elif score >= 10: return "Bullish"
    elif score >= 3:  return "Positive"
    elif score > -3:  return "Neutral"
    elif score > -10: return "Underbought"
    return "Bearish"

# ==================================================
# LOAD TECHNICAL DATA
# ==================================================
@st.cache_data(ttl=900)
def load_technical(tickers):
    rows = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            info = stock.info
            close = hist["Close"]
            price = close.iloc[-1]
            rows.append({
                "Ticker": ticker,
                "Company": info.get("longName", ticker),
                "Sector": info.get("sector", "N/A"),
                "Price": round(price, 2),
                "52W High": round(close.max(), 2),
                "52W Low": round(close.min(), 2),
                "RSI": round(rsi(close).iloc[-1], 2),
                "Bollinger": bollinger_label(close),
                "MA Cross": ma_cross(close),
                "Momentum": momentum_label(close),
                "Day %": round(((close.iloc[-1] / close.iloc[-2]) - 1) * 100, 2),
                "Month %": round(((close.iloc[-1] / close.iloc[-21]) - 1) * 100, 2),
                "Year %": round(((close.iloc[-1] / close.iloc[0]) - 1) * 100, 2),
            })
        except:
            rows.append({
                "Ticker": ticker, "Company": "Error", "Sector": "",
                "Price": np.nan, "52W High": np.nan, "52W Low": np.nan,
                "RSI": np.nan, "Bollinger": "", "MA Cross": "",
                "Momentum": "", "Day %": np.nan, "Month %": np.nan, "Year %": np.nan
            })
    return pd.DataFrame(rows)

# ==================================================
# LOAD FUNDAMENTAL DATA
# ==================================================
@st.cache_data(ttl=3600)
def load_fundamentals(tickers, period="annual"):
    rows = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if period == "annual":
                bs  = stock.balance_sheet
                inc = stock.income_stmt
                cf  = stock.cashflow
            else:
                bs  = stock.quarterly_balance_sheet
                inc = stock.quarterly_income_stmt
                cf  = stock.quarterly_cashflow

            def g(df, *keys):
                for k in keys:
                    if k in df.index:
                        for col in df.columns:
                            v = df.loc[k, col]
                            if pd.notna(v) and v != 0:
                                return float(v)
                return np.nan

            current_assets      = g(bs, "Current Assets")
            current_liabilities = g(bs, "Current Liabilities")
            cash                = g(bs, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
            inventory           = g(bs, "Inventory")
            total_assets        = g(bs, "Total Assets")
            ppe                 = g(bs, "Net PPE", "Property Plant Equipment Net")
            total_debt          = g(bs, "Total Debt", "Long Term Debt")
            equity              = g(bs, "Stockholders Equity", "Total Equity Gross Minority Interest")
            receivables         = g(bs, "Accounts Receivable", "Net Receivables")
            payables            = g(bs, "Accounts Payable")

            revenue             = g(inc, "Total Revenue")
            ebitda              = g(inc, "EBITDA", "Normalized EBITDA")
            ebit                = g(inc, "EBIT", "Operating Income")
            net_income          = g(inc, "Net Income")
            interest_expense    = g(inc, "Interest Expense")
            cogs                = g(inc, "Cost Of Revenue")

            operating_cf        = g(cf, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")

            def safe(a, b, op="div"):
                if pd.isna(a) or pd.isna(b) or b == 0:
                    return np.nan
                return a / b if op == "div" else a - b

            current_ratio = safe(current_assets, current_liabilities)
            quick_ratio   = safe((current_assets - inventory) if pd.notna(inventory) else current_assets, current_liabilities)
            cash_ratio    = safe(cash, current_liabilities)

            ebitda_margin = safe(ebitda, revenue) * 100 if pd.notna(safe(ebitda, revenue)) else np.nan
            ebit_margin   = safe(ebit,   revenue) * 100 if pd.notna(safe(ebit,   revenue)) else np.nan
            npm           = safe(net_income, revenue) * 100 if pd.notna(safe(net_income, revenue)) else np.nan

            asset_turnover       = safe(revenue, total_assets)
            fixed_asset_turnover = safe(revenue, ppe)

            days_recv = safe(receivables, revenue) * 365 if pd.notna(safe(receivables, revenue)) else np.nan
            days_inv  = safe(inventory,   cogs)    * 365 if pd.notna(safe(inventory,   cogs))    else np.nan
            days_pay  = safe(payables,    cogs)    * 365 if pd.notna(safe(payables,    cogs))    else np.nan

            ccc             = (days_recv + days_inv - days_pay) if all(pd.notna([days_recv, days_inv, days_pay])) else np.nan
            operating_cycle = (days_recv + days_inv)             if all(pd.notna([days_recv, days_inv]))          else np.nan

            dte  = safe(total_debt, equity)
            icr  = safe(ebit, abs(interest_expense)) if pd.notna(interest_expense) else np.nan
            dscr_denom = (abs(interest_expense) + abs(total_debt) * 0.1) if all(pd.notna([interest_expense, total_debt])) else np.nan
            dscr = safe(operating_cf, dscr_denom) if dscr_denom else np.nan

            def fmt(v, dec=2):
                return round(float(v), dec) if pd.notna(v) else "N/A"

            rows.append({
                "Ticker": ticker,
                "Company": info.get("longName", ticker),
                "Current Ratio": fmt(current_ratio),
                "Quick Ratio": fmt(quick_ratio),
                "Cash Ratio": fmt(cash_ratio),
                "EBITDA Margin %": fmt(ebitda_margin),
                "EBIT Margin %": fmt(ebit_margin),
                "Net Profit Margin %": fmt(npm),
                "Asset Turnover": fmt(asset_turnover),
                "Fixed Asset Turnover": fmt(fixed_asset_turnover),
                "Cash Conversion Cycle (days)": fmt(ccc, 0),
                "Operating Cycle (days)": fmt(operating_cycle, 0),
                "Debt to Equity": fmt(dte),
                "Interest Coverage": fmt(icr),
                "DSCR": fmt(dscr),
            })
        except Exception:
            rows.append({
                "Ticker": ticker, "Company": "Error",
                "Current Ratio": "N/A", "Quick Ratio": "N/A", "Cash Ratio": "N/A",
                "EBITDA Margin %": "N/A", "EBIT Margin %": "N/A", "Net Profit Margin %": "N/A",
                "Asset Turnover": "N/A", "Fixed Asset Turnover": "N/A",
                "Cash Conversion Cycle (days)": "N/A", "Operating Cycle (days)": "N/A",
                "Debt to Equity": "N/A", "Interest Coverage": "N/A", "DSCR": "N/A",
            })
    return pd.DataFrame(rows)

# ==================================================
# GLOBAL STYLING
# ==================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #070d1a; }
.metric-card {
    background: #0d1829;
    border: 1px solid #1a2744;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.5rem;
}
.metric-label { color: #4a6fa5; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
.metric-ticker { color: #e2e8f0; font-size: 1.1rem; font-weight: 700; font-family: 'DM Mono', monospace; }
.metric-value-green { color: #22c55e; font-size: 0.9rem; font-weight: 600; }
.metric-value-red   { color: #ef4444; font-size: 0.9rem; font-weight: 600; }
.section-header {
    color: #94a3b8; font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.12em;
    margin: 1rem 0 0.5rem 0; padding-bottom: 0.25rem;
    border-bottom: 1px solid #1a2744;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# SIDEBAR
# ==================================================
with st.sidebar:
    st.markdown("### 📊 Navigation")
    page = st.radio("", ["Technical", "Fundamentals"], label_visibility="collapsed")

    st.markdown('<div class="section-header">Manage Watchlist</div>', unsafe_allow_html=True)

    new_ticker = st.text_input("Add Ticker", placeholder="e.g. WIPRO.NS")
    if st.button("➕ Add", use_container_width=True):
        val = new_ticker.strip().upper()
        if val and val not in st.session_state.tickers:
            st.session_state.tickers.append(val)
            st.cache_data.clear()
            st.rerun()

    remove_ticker = st.selectbox("Remove Ticker", [""] + st.session_state.tickers)
    if st.button("➖ Remove", use_container_width=True):
        if remove_ticker:
            st.session_state.tickers.remove(remove_ticker)
            st.cache_data.clear()
            st.rerun()

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.button("↺ Reset to Defaults", use_container_width=True):
        st.session_state.tickers = DEFAULT_TICKERS.copy()
        st.cache_data.clear()
        st.rerun()

    st.markdown('<div class="section-header">Watchlist</div>', unsafe_allow_html=True)
    for t in st.session_state.tickers:
        st.caption(f"• {t}")

    st.markdown("---")
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ==================================================
# PAGE: TECHNICAL
# ==================================================
if page == "Technical":
    st.title("📈 Technical Dashboard")

    with st.spinner("Loading market data..."):
        df = load_technical(tuple(st.session_state.tickers))

    num_cols = ["Price", "52W High", "52W Low", "RSI", "Day %", "Month %", "Year %"]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # Performance leader cards
    valid = df.dropna(subset=["Day %"])
    if not valid.empty:
        st.subheader("Performance Leaders")
        c1, c2, c3 = st.columns(3)

        def leader_card(col_obj, label_a, label_b, ticker_a, val_a, ticker_b, val_b):
            with col_obj:
                ca = "metric-value-green" if val_a >= 0 else "metric-value-red"
                cb = "metric-value-green" if val_b >= 0 else "metric-value-red"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">🏆 {label_a}</div>
                    <div class="metric-ticker">{ticker_a}</div>
                    <div class="{ca}">{val_a:+.2f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">📉 {label_b}</div>
                    <div class="metric-ticker">{ticker_b}</div>
                    <div class="{cb}">{val_b:+.2f}%</div>
                </div>
                """, unsafe_allow_html=True)

        dg = df.loc[df["Day %"].idxmax()];   dl = df.loc[df["Day %"].idxmin()]
        mg = df.loc[df["Month %"].idxmax()]; ml = df.loc[df["Month %"].idxmin()]
        yg = df.loc[df["Year %"].idxmax()];  yl = df.loc[df["Year %"].idxmin()]

        leader_card(c1, "Day Gainer",   "Day Loser",   dg["Ticker"], dg["Day %"],   dl["Ticker"], dl["Day %"])
        leader_card(c2, "Month Gainer", "Month Loser", mg["Ticker"], mg["Month %"], ml["Ticker"], ml["Month %"])
        leader_card(c3, "Year Gainer",  "Year Loser",  yg["Ticker"], yg["Year %"],  yl["Ticker"], yl["Year %"])

    st.markdown("---")

    def color_signal(val):
        if val in ["Overbought", "Bearish", "Death Cross"]:
            return "color: #ef4444; font-weight: 600"
        elif val in ["Underbought", "Bullish", "Golden Cross", "Oversold", "Positive"]:
            return "color: #22c55e; font-weight: 600"
        return "color: #94a3b8"

    def color_pct(val):
        try:
            return "color: #22c55e" if float(val) >= 0 else "color: #ef4444"
        except:
            return ""

    styled = (
        df.style
        .map(color_signal, subset=["Bollinger", "Momentum", "MA Cross"])
        .map(color_pct, subset=["Day %", "Month %", "Year %"])
        .format({c: "{:.2f}" for c in num_cols if c in df.columns}, na_rep="N/A")
    )

    st.subheader("Portfolio Table")
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500)

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        st.subheader("Sector Concentration")
        sector_df = df.groupby("Sector").size().reset_index(name="Count")
        fig_pie = px.pie(sector_df, names="Sector", values="Count", hole=0.45,
                         color_discrete_sequence=px.colors.sequential.Blues_r)
        fig_pie.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                               font_color="#94a3b8", margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    with right:
        st.subheader("Correlation Heatmap")
        price_data = pd.DataFrame()
        for ticker in st.session_state.tickers:
            try:
                temp = yf.Ticker(ticker).history(period="6mo")["Close"]
                price_data[ticker] = temp
            except:
                pass
        if not price_data.empty and price_data.shape[1] > 1:
            corr = price_data.pct_change().dropna().corr()
            fig_heat = px.imshow(corr, text_auto=".2f", aspect="auto",
                                 color_continuous_scale="RdYlGn", zmin=-1, zmax=1)
            fig_heat.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)",
                                   font_color="#94a3b8", margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Need at least 2 valid stocks for heatmap.")

    with st.expander("📖 How Signals Are Calculated"):
        st.markdown("""
**Bollinger Bands** — 20-day MA ± 2 standard deviations
- Overbought: above upper band | Oversold: below lower band | Underbought: bottom 20% of band range

**Momentum Score** — Weighted return: 50% × 1M + 30% × 3M + 20% × 6M
- Overbought ≥ 20 | Bullish 10–20 | Positive 3–10 | Neutral –3 to 3 | Underbought –10 to –3 | Bearish < –10

**MA Cross** — Golden Cross: 50DMA > 200DMA | Death Cross: 50DMA < 200DMA
        """)

# ==================================================
# PAGE: FUNDAMENTALS
# ==================================================
elif page == "Fundamentals":
    st.title("🏦 Fundamentals Dashboard")

    period_toggle = st.radio("Data Period", ["Annual (TTM)", "Quarterly (Latest)"], horizontal=True)
    period_key = "annual" if period_toggle == "Annual (TTM)" else "quarterly"

    with st.spinner("Loading fundamental data — this may take a minute for 30+ stocks..."):
        fdf = load_fundamentals(tuple(st.session_state.tickers), period=period_key)

    st.markdown("---")

    # ---- LIQUIDITY ----
    st.subheader("💧 Liquidity Ratios")
    st.caption("Ability to meet short-term obligations")

    def color_liquidity(val):
        try:
            v = float(val)
            if v >= 2:   return "color: #22c55e; font-weight: 600"
            elif v >= 1: return "color: #f59e0b; font-weight: 600"
            else:        return "color: #ef4444; font-weight: 600"
        except:
            return "color: #64748b"

    liq_cols = ["Ticker", "Company", "Current Ratio", "Quick Ratio", "Cash Ratio"]
    st.dataframe(
        fdf[liq_cols].style.map(color_liquidity, subset=["Current Ratio", "Quick Ratio", "Cash Ratio"]),
        use_container_width=True, hide_index=True
    )
    with st.expander("ℹ️ Liquidity Benchmarks"):
        st.markdown("""
| Ratio | 🟢 Healthy | 🟡 Caution | 🔴 Concern |
|---|---|---|---|
| Current Ratio | ≥ 2 | 1 – 2 | < 1 |
| Quick Ratio | ≥ 1 | 0.5 – 1 | < 0.5 |
| Cash Ratio | ≥ 0.5 | 0.2 – 0.5 | < 0.2 |
        """)

    st.markdown("---")

    # ---- PROFITABILITY ----
    st.subheader("📊 Profitability Ratios")
    st.caption("How efficiently the company generates profit from revenue")

    def color_margin(val):
        try:
            v = float(val)
            if v >= 20:  return "color: #22c55e; font-weight: 600"
            elif v >= 8: return "color: #f59e0b; font-weight: 600"
            elif v >= 0: return "color: #94a3b8"
            else:        return "color: #ef4444; font-weight: 600"
        except:
            return "color: #64748b"

    prof_cols = ["Ticker", "Company", "EBITDA Margin %", "EBIT Margin %", "Net Profit Margin %"]
    st.dataframe(
        fdf[prof_cols].style.map(color_margin, subset=["EBITDA Margin %", "EBIT Margin %", "Net Profit Margin %"]),
        use_container_width=True, hide_index=True
    )
    with st.expander("ℹ️ Profitability Benchmarks"):
        st.markdown("""
| Margin | 🟢 Strong | 🟡 Moderate | 🔴 Weak |
|---|---|---|---|
| EBITDA Margin % | ≥ 20% | 8 – 20% | < 8% |
| EBIT Margin % | ≥ 15% | 5 – 15% | < 5% |
| Net Profit Margin % | ≥ 15% | 5 – 15% | < 5% |
        """)

    st.markdown("---")

    # ---- EFFICIENCY ----
    st.subheader("⚙️ Efficiency Ratios")
    st.caption("How well the company utilises its assets to generate revenue")

    def color_turnover(val):
        try:
            v = float(val)
            if v >= 1.5:   return "color: #22c55e; font-weight: 600"
            elif v >= 0.5: return "color: #f59e0b"
            else:          return "color: #ef4444"
        except:
            return "color: #64748b"

    def color_ccc(val):
        try:
            v = float(val)
            if v <= 30:   return "color: #22c55e; font-weight: 600"
            elif v <= 60: return "color: #f59e0b"
            else:         return "color: #ef4444"
        except:
            return "color: #64748b"

    eff_cols = ["Ticker", "Company", "Asset Turnover", "Fixed Asset Turnover",
                "Cash Conversion Cycle (days)", "Operating Cycle (days)"]
    st.dataframe(
        fdf[eff_cols].style
        .map(color_turnover, subset=["Asset Turnover", "Fixed Asset Turnover"])
        .map(color_ccc, subset=["Cash Conversion Cycle (days)", "Operating Cycle (days)"]),
        use_container_width=True, hide_index=True
    )
    with st.expander("ℹ️ Efficiency Benchmarks"):
        st.markdown("""
| Metric | 🟢 Good | Notes |
|---|---|---|
| Asset Turnover | ≥ 1.5x | Higher = better utilisation of total assets |
| Fixed Asset Turnover | ≥ 2x | Higher = better utilisation of fixed assets |
| Cash Conversion Cycle | ≤ 30 days | Lower = cash comes back faster |
| Operating Cycle | ≤ 60 days | Lower = operations run faster |
        """)

    st.markdown("---")

    # ---- SOLVENCY ----
    st.subheader("🏛️ Solvency Ratios")
    st.caption("Long-term financial stability and ability to service debt")

    def color_dte(val):
        try:
            v = float(val)
            if v <= 0.5:   return "color: #22c55e; font-weight: 600"
            elif v <= 1.5: return "color: #f59e0b"
            else:          return "color: #ef4444; font-weight: 600"
        except:
            return "color: #64748b"

    def color_icr(val):
        try:
            v = float(val)
            if v >= 5:   return "color: #22c55e; font-weight: 600"
            elif v >= 2: return "color: #f59e0b"
            else:        return "color: #ef4444; font-weight: 600"
        except:
            return "color: #64748b"

    solv_cols = ["Ticker", "Company", "Debt to Equity", "Interest Coverage", "DSCR"]
    st.dataframe(
        fdf[solv_cols].style
        .map(color_dte, subset=["Debt to Equity"])
        .map(color_icr, subset=["Interest Coverage", "DSCR"]),
        use_container_width=True, hide_index=True
    )
    with st.expander("ℹ️ Solvency Benchmarks"):
        st.markdown("""
| Ratio | 🟢 Healthy | 🟡 Caution | 🔴 Concern |
|---|---|---|---|
| Debt to Equity | ≤ 0.5 | 0.5 – 1.5 | > 1.5 |
| Interest Coverage | ≥ 5x | 2 – 5x | < 2x |
| DSCR | ≥ 1.5x | 1 – 1.5x | < 1x |
        """)

    st.markdown("---")
    st.caption("⚠️ Data sourced from Yahoo Finance via yfinance. Some values may show N/A if not reported or unavailable for Indian-listed stocks.")
