import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np
import json
import os

st.set_page_config(page_title="Stock Dashboard", layout="wide")

# ---------------- SETTINGS ---------------- #
WATCHLIST_FILE = "stocks.json"
DEFAULT_TICKERS = ["IREDA.NS", "BEL.NS"]

# ---------------- WATCHLIST ---------------- #
def load_tickers():
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict) and "tickers" in data:
                return [str(x).upper().strip() for x in data["tickers"] if str(x).strip()]

            if isinstance(data, list):
                return [str(x).upper().strip() for x in data if str(x).strip()]
    except:
        pass
    return DEFAULT_TICKERS.copy()

def save_tickers(tickers):
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump({"tickers": tickers}, f, indent=4)
    except:
        pass

if "tickers" not in st.session_state:
    st.session_state.tickers = load_tickers()

# ---------------- INDICATORS ---------------- #
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

# ---------------- DATA LOAD ---------------- #
@st.cache_data(ttl=900)
def load_data(tickers):
    rows = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            info = stock.info

            if hist.empty or len(hist) < 2:
                raise ValueError("No data")

            close = hist["Close"]

            day_ret = ((close.iloc[-1] / close.iloc[-2]) - 1) * 100
            month_ret = ((close.iloc[-1] / close.iloc[-21]) - 1) * 100 if len(close) >= 21 else np.nan
            year_ret = ((close.iloc[-1] / close.iloc[0]) - 1) * 100

            rows.append({
                "Ticker": ticker,
                "Company Name": info.get("longName", ticker),
                "Sector": info.get("sector", "N/A"),
                "Price": round(close.iloc[-1], 2),
                "52W High": round(close.max(), 2),
                "52W Low": round(close.min(), 2),
                "RSI": round(rsi(close).iloc[-1], 2),
                "Bollinger Bands": bollinger_label(close),
                "MA Cross": ma_cross(close),
                "Momentum Score": momentum_label(close),
                "Day %": round(day_ret, 2),
                "Month %": round(month_ret, 2) if pd.notna(month_ret) else np.nan,
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

# ---------------- SIDEBAR ---------------- #
with st.sidebar:
    st.header("Watchlist")

    new_ticker = st.text_input("Add Ticker")

    if st.button("Add"):
        value = new_ticker.strip().upper()
        if value and value not in st.session_state.tickers:
            st.session_state.tickers.append(value)
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

# ---------------- STYLES ---------------- #
st.markdown("""
<style>
.leader-card{
background:white;
border:1px solid #e5e7eb;
border-radius:16px;
padding:20px;
min-height:150px;
box-shadow:0 2px 8px rgba(0,0,0,0.06);
margin-bottom:16px;
}
.leader-label{font-size:16px;color:#64748b;margin-bottom:8px}
.leader-ticker{font-size:34px;font-weight:700;color:#111827}
.leader-green{font-size:20px;font-weight:700;color:green}
.leader-red{font-size:20px;font-weight:700;color:red}
</style>
""", unsafe_allow_html=True)

# ---------------- PAGE ---------------- #
st.title("Stock Dashboard")

df = load_data(tuple(st.session_state.tickers))

def color_signal(val):
    if val in ["Bearish", "Death Cross", "Overbought"]:
        return "color:red;font-weight:bold"
    elif val in ["Bullish", "Golden Cross", "Oversold", "Underbought", "Positive"]:
        return "color:green;font-weight:bold"
    elif val == "Neutral":
        return "color:gray;font-weight:bold"
    return ""

def color_pct(val):
    try:
        return "color:green;font-weight:bold" if float(val) >= 0 else "color:red;font-weight:bold"
    except:
        return ""

if not df.empty:

    valid_d = df[df["Day %"].notna()]
    valid_m = df[df["Month %"].notna()]
    valid_y = df[df["Year %"].notna()]

    if valid_d.empty:
        st.warning("No valid market data available.")
    else:
        dg = valid_d.loc[valid_d["Day %"].idxmax()]
        dl = valid_d.loc[valid_d["Day %"].idxmin()]
        mg = valid_m.loc[valid_m["Month %"].idxmax()] if not valid_m.empty else dg
        ml = valid_m.loc[valid_m["Month %"].idxmin()] if not valid_m.empty else dl
        yg = valid_y.loc[valid_y["Year %"].idxmax()] if not valid_y.empty else dg
        yl = valid_y.loc[valid_y["Year %"].idxmin()] if not valid_y.empty else dl

        st.subheader("Performance Leaders")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(f"<div class='leader-card'><div class='leader-label'>Day Gainer</div><div class='leader-ticker'>{dg['Ticker']}</div><div class='leader-green'>{dg['Day %']:+.2f}%</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='leader-card'><div class='leader-label'>Day Loser</div><div class='leader-ticker'>{dl['Ticker']}</div><div class='leader-red'>{dl['Day %']:+.2f}%</div></div>", unsafe_allow_html=True)

        with c2:
            st.markdown(f"<div class='leader-card'><div class='leader-label'>Month Gainer</div><div class='leader-ticker'>{mg['Ticker']}</div><div class='leader-green'>{mg['Month %']:+.2f}%</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='leader-card'><div class='leader-label'>Month Loser</div><div class='leader-ticker'>{ml['Ticker']}</div><div class='leader-red'>{ml['Month %']:+.2f}%</div></div>", unsafe_allow_html=True)

        with c3:
            st.markdown(f"<div class='leader-card'><div class='leader-label'>Year Gainer</div><div class='leader-ticker'>{yg['Ticker']}</div><div class='leader-green'>{yg['Year %']:+.2f}%</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='leader-card'><div class='leader-label'>Year Loser</div><div class='leader-ticker'>{yl['Ticker']}</div><div class='leader-red'>{yl['Year %']:+.2f}%</div></div>", unsafe_allow_html=True)

        st.subheader("Portfolio Table")

        tab1, tab2, tab3 = st.tabs(["Overview", "Technicals", "Performance"])

        with tab1:
            st.dataframe(
                df[["Ticker", "Company Name", "Sector", "Price", "52W High", "52W Low"]],
                use_container_width=True,
                hide_index=True
            )

        with tab2:
            tech = df[["Ticker", "RSI", "Bollinger Bands", "MA Cross", "Momentum Score"]]
            st.dataframe(
                tech.style.map(color_signal, subset=["Bollinger Bands", "MA Cross", "Momentum Score"]),
                use_container_width=True,
                hide_index=True,
                height=500
            )

        with tab3:
            perf = df[["Ticker", "Day %", "Month %", "Year %"]]
            st.dataframe(
                perf.style.map(color_pct, subset=["Day %", "Month %", "Year %"]),
                use_container_width=True,
                hide_index=True,
                height=500
            )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Sector Allocation")
            sector_df = df.groupby("Sector").size().reset_index(name="Count")
            fig = px.pie(sector_df, names="Sector", values="Count")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Returns Comparison")
            chart_df = df[["Ticker", "Day %", "Month %", "Year %"]].set_index("Ticker")
            st.bar_chart(chart_df)

else:
    st.warning("No data available.")
