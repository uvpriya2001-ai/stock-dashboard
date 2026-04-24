import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import plotly.express as px
import pandas as pd

# ---------------- Loading Tickers ----------------- #

st.set_page_config(page_title="Stock Dashboard", layout="wide")

WATCHLIST_FILE = "stocks.json"
DEFAULT_TICKERS = ["IREDA.NS", "BEL.NS", "TCS.NS", "ICICIGI.NS", "CDSL.NS", "POLYCAB.NS",
                   "INFY.NS", "HAL.NS", "HAVELLS.NS", "BAJAJ-AUTO.NS", "HDFCBANK.NS"
                  ]

def load_tickers():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get("tickers", DEFAULT_TICKERS)
        except:
            pass
    return DEFAULT_TICKERS.copy()

def save_tickers(tickers):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump({"tickers": tickers}, f, indent=4)

if "tickers" not in st.session_state:
    st.session_state.tickers = load_tickers()

# ---------------- Defining Indicators ----------------- #

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    if rsi >= 70:
      return "Overbought"
    elif rsi <= 30:
      return "Oversold"
    return "Neutral"

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

# ---------------- Load Data ----------------- #

@st.cache_data(ttl=600)
def load_data(tickers):
    rows = []

    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="1y")
            if hist.empty or len(hist) < 2:
                continue

            close = hist["Close"]

            day_ret = (close.iloc[-1] / close.iloc[-2] - 1) * 100
            month_ret = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else None
            year_ret = (close.iloc[-1] / close.iloc[0] - 1) * 100

            rows.append({
                "Ticker": ticker,
                "Price": round(close.iloc[-1], 2),
                "Day %": round(day_ret, 2),
                "Month %": round(month_ret, 2) if month_ret is not None else None,
                "Year %": round(year_ret, 2),
                "Bollinger Bands": bollinger_label(close),
                "MA Cross": ma_cross(close),
                "Momentum Score": momentum_label(close),
                "RSI": round(rsi(close).iloc[-1], 2)   
            })
        except:
            continue

    return pd.DataFrame(rows)

# ---------------- Sidebar ----------------- #

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

# ---------------- Top Gainers Card ----------------- #

st.title("Stock Dashboard")

df = load_data(tuple(st.session_state.tickers))

if df.empty:
    st.warning("No valid data found.")
    st.stop()

c1, c2, c3 = st.columns(3)

c1.metric("Top Day Gainer", df.loc[df["Day %"].idxmax(), "Ticker"], f'{df["Day %"].max():.2f}%')
c2.metric("Top Month Gainer", df["Ticker"][df["Month %"].fillna(-9999).idxmax()], f'{df["Month %"].max():.2f}%')
c3.metric("Top Year Gainer", df.loc[df["Year %"].idxmax(), "Ticker"], f'{df["Year %"].max():.2f}%')

# ---------------- Portfolio Dashboard ----------------- #

st.subheader("Portfolio")

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
st.dataframe(styled, use_container_width=True, hide_index=True)

# ---------------- Sector Dashboard ----------------- #

left, right = st.columns(2)

# ---------------- PIE CHART ---------------- #
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

# ---------------- CORRELATION HEATMAP ---------------- #

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
