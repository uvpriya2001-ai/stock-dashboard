import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import plotly.express as px

st.set_page_config(page_title="Stock Dashboard", layout="wide")

# ---------------- Loading Tickers ----------------- #

WATCHLIST_FILE = "stocks.json"

DEFAULT_TICKERS = [
    "IREDA.NS", "BEL.NS", "TCS.NS", "ICICIGI.NS", "CDSL.NS",
    "POLYCAB.NS", "INFY.NS", "HAL.NS", "HAVELLS.NS",
    "BAJAJ-AUTO.NS", "HDFCBANK.NS"
]

def load_tickers():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get("tickers", DEFAULT_TICKERS)
        except Exception:
            pass
    return DEFAULT_TICKERS.copy()

def save_tickers(tickers):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump({"tickers": tickers}, f, indent=4)

if "tickers" not in st.session_state:
    st.session_state.tickers = load_tickers()

# ---------------- Indicators ----------------- #

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    value = (100 - (100 / (1 + rs))).iloc[-1]

    if pd.isna(value):
        return "NA"
    elif value < 30:
        return "Underbought"
    elif value > 70:
        return "Overbought"
    return "Neutral"

def bollinger_label(close):
    if len(close) < 20:
        return "NA"

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

    score = 0.5 * r1 + 0.3 * r3 + 0.2 * r6

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
    price_map = {}

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            info = stock.info

            if hist.empty or len(hist) < 2:
                continue

            close = hist["Close"]
            price_map[ticker] = close

            day_ret = (close.iloc[-1] / close.iloc[-2] - 1) * 100
            month_ret = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else None
            year_ret = (close.iloc[-1] / close.iloc[0] - 1) * 100

            rows.append({
                "Ticker": ticker,
                "Sector": info.get("sector", "Unknown"),
                "Price": round(close.iloc[-1], 2),
                "52W High": round(close.max(), 2),
                "52W Low": round(close.min(), 2),
                "Day %": round(day_ret, 2),
                "Month %": round(month_ret, 2) if month_ret is not None else None,
                "Year %": round(year_ret, 2),
                "Bollinger Bands": bollinger_label(close),
                "MA Cross": ma_cross(close),
                "Momentum Score": momentum_label(close),
                "RSI": rsi(close)
            })

        except Exception:
            continue

    return pd.DataFrame(rows), price_map

# ---------------- Sidebar ----------------- #

with st.sidebar:
    st.header("Manage Stocks")

    new_ticker = st.text_input("Add Stock", placeholder="SBIN.NS")

    if st.button("Add"):
        val = new_ticker.strip().upper()
        if val and val not in st.session_state.tickers:
            st.session_state.tickers.append(val)
            save_tickers(st.session_state.tickers)
            st.cache_data.clear()
            st.rerun()

    remove_ticker = st.selectbox("Remove Stock", placeholder="SBIN.NS", [""] + st.session_state.tickers)

    if st.button("Remove"):
        if remove_ticker:
            st.session_state.tickers.remove(remove_ticker)
            save_tickers(st.session_state.tickers)
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------------- Main ----------------- #

st.title("Stock Dashboard")

df, price_map = load_data(tuple(st.session_state.tickers))

if df.empty:
    st.warning("No valid data found.")
    st.stop()

c1, c2, c3 = st.columns(3)

c1.metric("Top Day Gainer", df.loc[df["Day %"].idxmax(), "Ticker"], f'{df["Day %"].max():.2f}%')
c2.metric("Top Month Gainer", df.loc[df["Month %"].fillna(-9999).idxmax(), "Ticker"], f'{df["Month %"].max():.2f}%')
c3.metric("Top Year Gainer", df.loc[df["Year %"].idxmax(), "Ticker"], f'{df["Year %"].max():.2f}%')

# ---------------- Table ----------------- #

def color_signal(val):
    if val in ["Overbought", "Bearish", "Death Cross"]:
        return "color:red;font-weight:bold"
    elif val in ["Underbought", "Bullish", "Golden Cross", "Oversold", "Positive"]:
        return "color:green;font-weight:bold"
    return "color:darkgrey;font-weight:bold"

display_df = df[
    [
        "Ticker",
        "Price",
        "Day %",
        "Month %",
        "Year %",
        "RSI",
        "Bollinger Bands",
        "MA Cross",
        "Momentum Score"
    ]
]

styled = display_df.style.format({
    "Price": "{:.2f}",
    "Day %": "{:.2f}",
    "Month %": "{:.2f}",
    "Year %": "{:.2f}"
}).map(
    color_signal,
    subset=["RSI", "Bollinger Bands", "MA Cross", "Momentum Score"]
)

st.subheader("Portfolio Table")
st.dataframe(styled, use_container_width=True, hide_index=True)

# ---------------- Charts ----------------- #

left, right = st.columns(2)

with left:
    st.subheader("Sector Concentration")
    sector_df = df.groupby("Sector").size().reset_index(name="Count")
    fig_pie = px.pie(sector_df, names="Sector", values="Count", hole=0.45)
    st.plotly_chart(fig_pie, use_container_width=True)

with right:
    st.subheader("Correlation Heatmap")

    if len(price_map) > 1:
        price_df = pd.DataFrame(price_map)
        corr = price_df.pct_change().dropna().corr()

        fig_heat = px.imshow(
            corr,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="GnYlRd",
            zmin=-1,
            zmax=1
        )

        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Need at least 2 valid stocks for heatmap.")
