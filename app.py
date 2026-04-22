import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np
import json
import os

st.set_page_config(page_title="Stock Dashboard", layout="wide")

# ==================================================
# SESSION STATE
# ==================================================


if "tickers" not in st.session_state:
    st.session_state.tickers = []

st.session_state.tickers.remove(remove_ticker)
save_tickers(st.session_state.tickers)
st.cache_data.clear()
st.rerun()
    
# ==================================================
# HELPERS
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

    if score >= 20:
        return "Overbought"
    elif score >= 10:
        return "Bullish"
    elif score >= 3:
        return "Positive"
    elif score > -3:
        return "Neutral"
    elif score > -10:
        return "Underbought"
    return "Bearish"

# ==================================================
# LOAD DATA
# ==================================================
@st.cache_data(ttl=900)
def load_data(tickers):
    rows = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            info = stock.info
            close = hist["Close"]

            price = close.iloc[-1]
            day_ret = ((close.iloc[-1] / close.iloc[-2]) - 1) * 100
            month_ret = ((close.iloc[-1] / close.iloc[-21]) - 1) * 100
            year_ret = ((close.iloc[-1] / close.iloc[0]) - 1) * 100

            rows.append({
                "Ticker": ticker,
                "Company Name": info.get("longName", ticker),
                "Sector": info.get("sector", "N/A"),
                "Price": round(price, 2),
                "52W High": round(close.max(), 2),
                "52W Low": round(close.min(), 2),
                "RSI": round(rsi(close).iloc[-1], 2),
                "Bollinger Bands": bollinger_label(close),
                "MA Cross": ma_cross(close),
                "Momentum Score": momentum_label(close),
                "Day %": round(day_ret, 2),
                "Month %": round(month_ret, 2),
                "Year %": round(year_ret, 2)
            })

        except:
            rows.append({
                "Ticker": ticker,
                "Company Name": "Error",
                "Sector": "",
                "Price": np.nan,
                "52W High": np.nan,
                "52W Low": np.nan,
                "RSI": np.nan,
                "Bollinger Bands": "",
                "MA Cross": "",
                "Momentum Score": "",
                "Day %": np.nan,
                "Month %": np.nan,
                "Year %": np.nan
            })

    return pd.DataFrame(rows)

# ==================================================
# UI
# ==================================================
# REPLACE ONLY YOUR UI SECTION
# (everything from st.title("Stock Dashboard") onward)

st.title("Stock Dashboard")

# ==================================================
# SIDEBAR CONTROLS
# ==================================================
with st.sidebar:
    st.header("Manage Stocks")

    new_ticker = st.text_input("Add Stock", placeholder="SBIN.NS / AAPL")

    if st.button("Add"):
        val = new_ticker.strip().upper()

        if val and val not in st.session_state.tickers:
            st.session_state.tickers.append(val)
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    remove_ticker = st.selectbox(
        "Remove Stock",
        [""] + st.session_state.tickers
    )

    if st.button("Remove"):
        if remove_ticker:
            st.session_state.tickers.remove(remove_ticker)
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("### Current Watchlist")
    for t in st.session_state.tickers:
        st.write("•", t)
        
# ==================================================
# DATA
# ==================================================
df = load_data(tuple(st.session_state.tickers))

num_cols = ["Price","52W High","52W Low","RSI","Day %","Month %","Year %"]
for col in num_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

# ==================================================
# TOP CARDS
# ==================================================
day_gainer = df.loc[df["Day %"].idxmax()]
day_loser = df.loc[df["Day %"].idxmin()]
month_gainer = df.loc[df["Month %"].idxmax()]
month_loser = df.loc[df["Month %"].idxmin()]
year_gainer = df.loc[df["Year %"].idxmax()]
year_loser = df.loc[df["Year %"].idxmin()]

st.subheader("Performance Leaders")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Day Gainer", f"{day_gainer['Ticker']}")
    st.caption(f"{day_gainer['Day %']:.2f}%")
    st.metric("Day Loser", f"{day_loser['Ticker']}")
    st.caption(f"{day_loser['Day %']:.2f}%")

with c2:
    st.metric("Month Gainer", f"{month_gainer['Ticker']}")
    st.caption(f"{month_gainer['Month %']:.2f}%")
    st.metric("Month Loser", f"{month_loser['Ticker']}")
    st.caption(f"{month_loser['Month %']:.2f}%")

with c3:
    st.metric("Year Gainer", f"{year_gainer['Ticker']}")
    st.caption(f"{year_gainer['Year %']:.2f}%")
    st.metric("Year Loser", f"{year_loser['Ticker']}")
    st.caption(f"{year_loser['Year %']:.2f}%")

# ==================================================
# MAIN LAYOUT: TABLE + PIE
# ==================================================
# REPLACE ONLY THIS SECTION:
# MAIN LAYOUT: TABLE + PIE

# ==================================================
# TABLE FULL WIDTH
# ==================================================
def color_signal(val):
    if val in ["Overbought", "Bearish", "Death Cross"]:
        return "color:red; font-weight:bold"
    elif val in ["Underbought", "Bullish", "Golden Cross", "Oversold"]:
        return "color:green; font-weight:bold"
    return "color:gray; font-weight:bold"

styled = df.style.map(
    color_signal,
    subset=["Bollinger Bands", "Momentum Score", "MA Cross"]
).format({
    "Price": "{:.2f}",
    "52W High": "{:.2f}",
    "52W Low": "{:.2f}",
    "RSI": "{:.2f}",
    "Day %": "{:.2f}",
    "Month %": "{:.2f}",
    "Year %": "{:.2f}"
})

st.subheader("Portfolio Table")
st.dataframe(styled, use_container_width=True, hide_index=True, height=450)

# ==================================================
# BELOW TABLE: PIE + CORRELATION HEATMAP
# ==================================================
left, right = st.columns(2)

# ---------------- PIE CHART ----------------
with left:
    st.subheader("Sector Concentration")

    sector_df = df.groupby("Sector").size().reset_index(name="Count")

    fig_pie = px.pie(
        sector_df,
        names="Sector",
        values="Count",
        hole=0.45
    )

    fig_pie.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    st.plotly_chart(fig_pie, use_container_width=True)

# ---------------- CORRELATION HEATMAP ----------------
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

        fig_heat = px.imshow(
            corr,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="RdYlGn",
            zmin=-1,
            zmax=1
        )

        fig_heat.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=40, b=10)
        )

        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Need at least 2 valid stocks for heatmap.")

# ==================================================
# FORMULA GUIDE
# ==================================================
st.markdown("---")
st.subheader("How Signals Are Decided")

st.markdown("""
### Bollinger Bands
- Upper Band = 20DMA + 2σ
- Lower Band = 20DMA - 2σ
- Overbought: Above upper band
- Oversold: Below lower band
- Underbought: Bottom 20% of band range

### Momentum Score
Weighted Returns:
- 1M = 50%
- 3M = 30%
- 6M = 20%

Labels:
- Overbought ≥ 20
- Bullish 10 to 20
- Positive 3 to 10
- Neutral -3 to 3
- Underbought -10 to -3
- Bearish < -10

### MA Cross
- Golden Cross = 50DMA > 200DMA
- Death Cross = 50DMA < 200DMA
""")
