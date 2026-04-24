import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import plotly.express as px

st.set_page_config(page_title="Stock Dashboard", layout="wide")

WATCHLIST_FILE = "stocks.json"
DEFAULT_TICKERS = ["IREDA.NS", "BEL.NS", "TCS.NS"]

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
                "52W High": round(close.max(), 2),
                "52W Low": round(close.min(), 2),
            })
        except:
            continue

    return pd.DataFrame(rows)

with st.sidebar:
    st.header("Watchlist")

    new_ticker = st.text_input("Add Ticker")

    if st.button("Add"):
        t = new_ticker.strip().upper()
        if t and t not in st.session_state.tickers:
            st.session_state.tickers.append(t)
            save_tickers(st.session_state.tickers)
            st.cache_data.clear()
            st.rerun()

    remove_ticker = st.selectbox("Remove Ticker", [""] + st.session_state.tickers)

    if st.button("Remove"):
        if remove_ticker:
            st.session_state.tickers.remove(remove_ticker)
            save_tickers(st.session_state.tickers)
            st.cache_data.clear()
            st.rerun()

st.title("Stock Dashboard")

df = load_data(tuple(st.session_state.tickers))

if df.empty:
    st.warning("No valid data found.")
    st.stop()

c1, c2, c3 = st.columns(3)

c1.metric("Top Day Gainer", df.loc[df["Day %"].idxmax(), "Ticker"], f'{df["Day %"].max():.2f}%')
c2.metric("Top Month Gainer", df["Ticker"][df["Month %"].fillna(-9999).idxmax()], f'{df["Month %"].max():.2f}%')
c3.metric("Top Year Gainer", df.loc[df["Year %"].idxmax(), "Ticker"], f'{df["Year %"].max():.2f}%')

st.subheader("Portfolio")
st.dataframe(df, use_container_width=True, hide_index=True)

col1, col2 = st.columns(2)

with col1:
    sector = pd.DataFrame({"Type": ["Watchlist"], "Count": [len(df)]})
    fig = px.pie(sector, names="Type", values="Count")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    chart_df = df[["Ticker", "Day %", "Month %", "Year %"]].set_index("Ticker")
    st.bar_chart(chart_df)
