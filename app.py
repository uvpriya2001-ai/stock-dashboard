import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import plotly.express as px

st.set_page_config(page_title="Stock Dashboard", layout="wide")

# ---------------- Global CSS ----------------- #
st.markdown("""
<style>
div[data-testid="stDataFrame"] thead th{
    font-weight:700 !important;
    font-size:15px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- Loading Tickers ----------------- #
WATCHLIST_FILE = "stocks.json"

DEFAULT_TICKERS = [
    "IREDA.NS","BEL.NS","TCS.NS","ICICIGI.NS","CDSL.NS",
    "POLYCAB.NS","INFY.NS","HAL.NS","HAVELLS.NS",
    "BAJAJ-AUTO.NS","HDFCBANK.NS"
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
        json.dump({"tickers": tickers,}, f, indent=4)

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
    if value < 30:
        return "Underbought"
    if value > 70:
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
    if last <= lower:
        return "Oversold"
    if last <= lower + zone:
        return "Underbought"
    return "Neutral"

def ma_cross(close):
    if len(close) < 200:
        return "NA"
    return "Golden Cross" if close.tail(50).mean() > close.tail(200).mean() else "Death Cross"

def momentum_label(close):
    if len(close) < 126:
        return "NA"

    r1 = (close.iloc[-1] / close.iloc[-21] - 1) * 100
    r3 = (close.iloc[-1] / close.iloc[-63] - 1) * 100
    r6 = (close.iloc[-1] / close.iloc[-126] - 1) * 100
    score = 0.5*r1 + 0.3*r3 + 0.2*r6

    if score >= 20: return "Overbought"
    if score >= 10: return "Bullish"
    if score >= 3: return "Positive"
    if score > -3: return "Neutral"
    if score > -10: return "Underbought"
    return "Bearish"

# ---------------- Market Data ----------------- #
@st.cache_data(ttl=600)
def market_data():
    try:
        nifty = yf.Ticker("^NSEI").history(period="5d")["Close"]
        vix = yf.Ticker("^INDIAVIX").history(period="5d")["Close"]

        nifty_val = nifty.iloc[-1]
        nifty_ret = (nifty.iloc[-1] / nifty.iloc[-2] - 1) * 100

        vix_val = vix.iloc[-1]
        vix_ret = (vix.iloc[-1] / vix.iloc[-2] - 1) * 100

        return round(nifty_val,2), round(nifty_ret,2), round(vix_val,2), round(vix_ret,2)
    except Exception:
        return 0,0,0,0

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

            current = close.iloc[-1]
            high = close.max()
            low = close.min()

            rows.append({
                "Ticker": ticker,
                "Sector": info.get("sector", "Unknown"),
                "Price": round(current, 2),
                "Day %": round((current / close.iloc[-2] - 1) * 100, 2),
                "Month %": round((current / close.iloc[-21] - 1) * 100, 2) if len(close) >= 21 else None,
                "Year %": round((current / close.iloc[0] - 1) * 100, 2),
                "RSI": rsi(close),
                "Bollinger Bands": bollinger_label(close),
                "MA Cross": ma_cross(close),
                "Momentum Score": momentum_label(close),
                "Drawdown %": round((current / high - 1) * 100, 2),
                "52W High": round(high, 2),
                "52W Low": round(low, 2)
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

    remove_ticker = st.selectbox("Remove Stock", [""] + st.session_state.tickers)

    if st.button("Remove"):
        if remove_ticker:
            st.session_state.tickers.remove(remove_ticker)
            save_tickers(st.session_state.tickers)
            st.cache_data.clear()
            st.rerun()

    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---------------- Main ----------------- #
st.title("Stock Dashboard")
st.caption("This dashboard monitors all your favourite stocks at one place.")

df, price_map = load_data(tuple(st.session_state.tickers))
nifty_val, nifty_ret, vix_val, vix_ret = market_data()

if df.empty:
    st.warning("No valid data found.")
    st.stop()

# ---------------- Top Metrics ----------------- #
top_day = df.loc[df["Day %"].idxmax()]
top_month = df.loc[df["Month %"].fillna(-9999).idxmax()]
top_year = df.loc[df["Year %"].idxmax()]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Top Day Gainer", top_day["Ticker"], f'{top_day["Day %"]:.2f}%')
c2.metric("Top Month Gainer", top_month["Ticker"], f'{top_month["Month %"]:.2f}%')
c3.metric("Top Year Gainer", top_year["Ticker"], f'{top_year["Year %"]:.2f}%')
c4.metric("Nifty 50", f"{nifty_val:.2f}", f"{nifty_ret:.2f}%")
c5.metric("India VIX", f"{vix_val:.2f}", f"{vix_ret:.2f}%")

# ---------------- Ranking ----------------- #
df["Buy Score"] = (
    (-df["Drawdown %"]) * 0.4 +
    df["Month %"].fillna(0) * 0.2 +
    df["Year %"].fillna(0) * 0.2 +
    (df["MA Cross"].eq("Golden Cross")).astype(int) * 10 +
    (df["Momentum Score"].isin(["Bullish","Positive"])).astype(int) * 8
)

df = df.sort_values("Buy Score", ascending=False)

# ---------------- Table ----------------- #
def color_signal(val):
    if val in ["Overbought","Bearish","Death Cross"]:
        return "color:red;font-weight:bold"
    if val in ["Underbought","Bullish","Golden Cross","Oversold","Positive"]:
        return "color:green;font-weight:bold"
    return "color:darkgrey;font-weight:bold"

display_df = df[
    ["Ticker","Price","Day %","Month %","Year %","RSI",
     "Bollinger Bands","MA Cross","Momentum Score","Drawdown %"]
]

styled = (
    display_df.style
    .format({
        "Price":"{:.2f}",
        "Day %":"{:.2f}",
        "Month %":"{:.2f}",
        "Year %":"{:.2f}",
        "Drawdown %":"{:.2f}"
    })
    .map(color_signal, subset=["RSI","Bollinger Bands","MA Cross","Momentum Score"])
)

st.subheader("Watchlist Table")
st.dataframe(styled, use_container_width=True, hide_index=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, "stock_dashboard.csv", "text/csv")

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
            color_continuous_scale="RdYlGn_r",
            zmin=-1,
            zmax=1
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Need at least 2 valid stocks for heatmap.")
