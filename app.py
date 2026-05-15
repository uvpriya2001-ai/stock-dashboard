import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import plotly.express as px
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Stock Dashboard", layout="wide")

st.markdown("""<style>
div[data-testid="stDataFrame"] thead th{font-weight:700 !important;font-size:15px !important;}
.positive {color:#10b981;}
.negative {color:#ef4444;}
</style>""", unsafe_allow_html=True)

# ============= HELPERS =============
def get_current_quarter():
    today = datetime.now()
    month = today.month
    return (month - 1) // 3 + 1

def get_quarter_dates(quarter):
    today = datetime.now()
    year = today.year
    quarters = {
        1: (datetime(year, 1, 1), datetime(year, 3, 31)),
        2: (datetime(year, 4, 1), datetime(year, 6, 30)),
        3: (datetime(year, 7, 1), datetime(year, 9, 30)),
        4: (datetime(year, 10, 1), datetime(year, 12, 31))
    }
    return quarters[quarter]

# ============= TICKERS =============
WATCHLIST_FILE = "stocks.json"
DEFAULT_TICKERS = [
    "IREDA.NS","BEL.NS","TCS.NS","ICICIGI.NS","CDSL.NS",
    "POLYCAB.NS","INFY.NS","HAL.NS","HAVELLS.NS",
    "BAJAJ-AUTO.NS","HDFCBANK.NS"
]

SECTOR_INDICES = {
    "Nifty 50": ("^NSEI",),
    "Sensex": ("^BSESN",),
    "India VIX": ("^INDIAVIX",),
    "Nifty Smallcap 50": ("NIFTYSMLCAP50.NS", "^NIFTYSMALLCAP50"),
    "Nifty Midcap 50": ("^NSEMDCP50", "^NIFTYMID50"),
    "Nifty Bank": ("^NSEBANK", "^NIFTYBANK"),
    "Nifty IT": ("^CNXIT", "^NIFTYIT"),
    "Nifty Auto": ("^CNXAUTO", "^NIFTYAUTO"),
    "Nifty Energy": ("^CNXENERGY", "^NIFTYENERGY"),
    "Nifty FMCG": ("^CNXFMCG", "^NIFTYFMCG"),
    "Nifty Pharma": ("^CNXPHARMA", "^NIFTYPHARMA"),
    "Nifty Realty": ("^CNXREALTY", "^NIFTYREALTY")
}

def load_tickers():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("tickers", DEFAULT_TICKERS)
        except:
            pass
    return DEFAULT_TICKERS.copy()

def save_tickers(tickers):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump({"tickers": tickers}, f, indent=4)

if "tickers" not in st.session_state:
    st.session_state.tickers = load_tickers()

# ============= INDICATORS =============
def rsi(series, period=14):
    if len(series) < period + 1:
        return "NA"
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

def momentum_score_numeric(close):
    if len(close) < 126:
        return 0
    r1 = (close.iloc[-1] / close.iloc[-21] - 1) * 100
    r3 = (close.iloc[-1] / close.iloc[-63] - 1) * 100
    r6 = (close.iloc[-1] / close.iloc[-126] - 1) * 100
    return 0.5*r1 + 0.3*r3 + 0.2*r6

# ============= DATA FETCH =============
@st.cache_data(ttl=600)
def load_data(tickers):
    rows = []
    price_map = {}
    for ticker in tickers:
        try:
            hist = yf.download(ticker, period="3y", auto_adjust=True, progress=False, group_by="column", threads=False)
            if hist.empty:
                continue
            if isinstance(hist.columns, pd.MultiIndex):
                close = hist["Close"].iloc[:, 0]
            else:
                close = hist["Close"]
            close = pd.Series(close).dropna()
            if len(close) < 2:
                continue
            current = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            start = float(close.iloc[0])
            high = float(close.max())
            low = float(close.min())
            month_ret = round((current / float(close.iloc[-21]) - 1) * 100, 2) if len(close) >= 21 else None
            sector = "Unknown"
            try:
                info = yf.Ticker(ticker).info
                sector = info.get("sector", "Unknown")
            except:
                pass
            price_map[ticker] = close
            momentum = momentum_score_numeric(close)
            rows.append({
                "Ticker": ticker,
                "Sector": sector,
                "Price": round(current, 2),
                "Day %": round((current / prev - 1) * 100, 2),
                "Month %": month_ret,
                "Year %": round((current / start - 1) * 100, 2),
                "RSI": rsi(close),
                "Bollinger Bands": bollinger_label(close),
                "MA Cross": ma_cross(close),
                "Momentum": momentum_label(close),
                "Momentum_Score": momentum,
                "Drawdown %": round((current / high - 1) * 100, 2),
                "52W High": round(high, 2),
                "52W Low": round(low, 2),
                "Close_Series": close
            })
        except:
            continue
    return pd.DataFrame(rows), price_map

@st.cache_data(ttl=600)
def load_sector_indices_data():
    rows = []
    for name, symbol in SECTOR_INDICES.items():
        try:
            hist = yf.download(symbol, period="1y", auto_adjust=True, progress=False, group_by="column", threads=False)
            if hist.empty:
                continue
            if isinstance(hist.columns, pd.MultiIndex):
                close = hist["Close"].iloc[:, 0]
            else:
                close = hist["Close"]
            close = pd.Series(close).dropna()
            if len(close) < 2:
                continue
            current = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            start = float(close.iloc[0])
            high = float(close.max())
            low = float(close.min())
            day_ret = round((current / prev - 1) * 100, 2)
            month_ret = round((current / float(close.iloc[-21]) - 1) * 100, 2) if len(close) >= 21 else None
            year_ret = round((current / start - 1) * 100, 2)
            rows.append({
                "Index": name,
                "Price": round(current, 2),
                "Day %": day_ret,
                "Month %": month_ret,
                "Year %": year_ret,
                "52W High": round(high, 2),
                "52W Low": round(low, 2)
            })
        except:
            continue
    return pd.DataFrame(rows)

@st.cache_data(ttl=600)
def find_best_pairs(price_map, top_n=5):
    if len(price_map) < 2:
        return None
    price_df = pd.DataFrame(price_map).dropna(axis=1, how="all")
    returns = price_df.pct_change().dropna(how="all").dropna(axis=1, how="all")
    if returns.shape[1] < 2:
        return None
    corr = returns.corr()
    pairs = []
    tickers = list(price_map.keys())
    for i in range(len(tickers)):
        for j in range(i+1, len(tickers)):
            ticker1, ticker2 = tickers[i], tickers[j]
            correlation = corr.loc[ticker1, ticker2]
            momentum1 = momentum_score_numeric(price_map[ticker1])
            momentum2 = momentum_score_numeric(price_map[ticker2])
            expected_return = (momentum1 + momentum2) / 2
            vol1 = returns[ticker1].std() * np.sqrt(252)
            vol2 = returns[ticker2].std() * np.sqrt(252)
            portfolio_vol = np.sqrt((0.5*vol1)**2 + (0.5*vol2)**2 + 2*0.5*0.5*correlation*vol1*vol2)
            pairs.append({
                "Bundle": f"{ticker1} + {ticker2}",
                "Correlation": round(correlation, 3),
                "Expected_Quarterly_Return": round(expected_return, 2),
                "Portfolio_Volatility": round(portfolio_vol, 4)
            })
    pairs_df = pd.DataFrame(pairs)
    pairs_df = pairs_df.sort_values(["Correlation", "Expected_Quarterly_Return"], ascending=[True, False])
    return pairs_df.head(top_n)

# ============= SIDEBAR =============
with st.sidebar:
    st.header("Manage Stocks")
    new_ticker = st.text_input("Add Stock", placeholder="SBIN.NS", key="add_ticker")
    if st.button("Add"):
        val = new_ticker.strip().upper()
        if val and val not in st.session_state.tickers:
            st.session_state.tickers.append(val)
            save_tickers(st.session_state.tickers)
            st.cache_data.clear()
            st.rerun()
    remove_ticker = st.selectbox("Remove Stock", [""] + st.session_state.tickers)
    if st.button("Remove"):
        if remove_ticker and remove_ticker in st.session_state.tickers:
            st.session_state.tickers.remove(remove_ticker)
            save_tickers(st.session_state.tickers)
            st.cache_data.clear()
            st.rerun()
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============= MAIN =============
st.title("Stock Dashboard")
current_quarter = get_current_quarter()
quarter_start, quarter_end = get_quarter_dates(current_quarter)
st.caption(f"Q{current_quarter} Analysis | {quarter_start.strftime('%B %d')} - {quarter_end.strftime('%B %d, %Y')} | Target: 5-6%")

tab1, tab2, tab3 = st.tabs(["Watchlist", "Market Indices", "Sector Deep Dive"])

# ============= TAB 1 =============
with tab1:
    df, price_map = load_data(tuple(st.session_state.tickers))
    if df.empty:
        st.warning("No valid data found.")
        st.stop()
    
    st.subheader("Market Overview")
    top_day = df.loc[df["Day %"].fillna(-9999).idxmax()]
    bottom_day = df.loc[df["Day %"].fillna(9999).idxmin()]
    top_month = df.loc[df["Month %"].fillna(-9999).idxmax()]
    bottom_month = df.loc[df["Month %"].fillna(9999).idxmin()]
    top_year = df.loc[df["Year %"].fillna(-9999).idxmax()]
    bottom_year = df.loc[df["Year %"].fillna(9999).idxmin()]
    top_momentum = df.loc[df["Momentum_Score"].idxmax()]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Top Day Gainer", top_day["Ticker"], f'{top_day["Day %"]:.2f}%')
        st.metric("Worst Day Loser", bottom_day["Ticker"], f'{bottom_day["Day %"]:.2f}%')
    with c2:
        st.metric("Top Month Gainer", top_month["Ticker"], f'{top_month["Month %"]:.2f}%')
        st.metric("Worst Month Loser", bottom_month["Ticker"], f'{bottom_month["Month %"]:.2f}%')
    with c3:
        st.metric("Top Year Gainer", top_year["Ticker"], f'{top_year["Year %"]:.2f}%')
        st.metric("Worst Year Loser", bottom_year["Ticker"], f'{bottom_year["Year %"]:.2f}%')
    
    st.metric("Top Momentum Stock this quarter".format(current_quarter), top_momentum["Ticker"], f'{top_momentum["Momentum_Score"]:.2f}')
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        sort_order = st.selectbox("Sort By", ["Momentum_Score", "Month %", "Year %", "Drawdown %", "Day %"])
    with col2:
        ascending = st.checkbox("Ascending Order", value=False)
    
    display_df = df.sort_values(sort_order, ascending=ascending)
    
    def color_signal(val):
        if val in ["Overbought","Bearish","Death Cross"]:
            return "color:red;font-weight:bold"
        if val in ["Underbought","Bullish","Golden Cross","Oversold","Positive"]:
            return "color:green;font-weight:bold"
        return "color:grey;font-weight:bold"
    
    table_cols = ["Ticker","Price","Day %","Month %","Year %","RSI","Bollinger Bands","MA Cross","Momentum","Momentum_Score","Drawdown %","52W High", "52W Low"]
    table_display = display_df[table_cols].copy()
    styled = (
        table_display.style
        .format({"Price":"{:.2f}","Day %":"{:.2f}","Month %":"{:.2f}","Year %":"{:.2f}","Momentum_Score":"{:.2f}","Drawdown %":"{:.2f}","52W High":"{:.2f}","52W Low":"{:.2f}" })
        .map(color_signal, subset=["RSI","Bollinger Bands","MA Cross","Momentum"])
    )
    st.subheader("Watchlist Table")
    st.dataframe(styled, use_container_width=True, hide_index=True)
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "stock_dashboard.csv", "text/csv")
    st.divider()
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Sector Concentration")
        sector_df = df.groupby("Sector").size().reset_index(name="Count")
        fig_pie = px.pie(sector_df, names="Sector", values="Count", hole=0.4)
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_right:
        st.subheader("Momentum Distribution")
        momentum_counts = df["Momentum"].value_counts().reset_index()
        momentum_counts.columns = ["Momentum", "Count"]
        fig_momentum = px.bar(momentum_counts, x="Momentum", y="Count", color="Momentum")
        fig_momentum.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_momentum, use_container_width=True)
    
    st.subheader("Correlation Heatmap")
    if len(price_map) > 1:
        price_df = pd.DataFrame(price_map).dropna(axis=1, how="all")
        returns = price_df.pct_change().dropna(how="all").dropna(axis=1, how="all")
        if not returns.empty and returns.shape[1] > 1:
            corr = returns.corr()
            fig_heat = px.imshow(corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdYlGn_r", zmin=-1, zmax=1)
            fig_heat.update_layout(height=600)
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Not enough valid stocks for heatmap.")
    else:
        st.info("Need at least 2 valid stocks for heatmap.")
    
    st.divider()
    st.subheader("Best Diversification Bundles (Q{})".format(current_quarter))
    pairs_df = find_best_pairs(price_map, top_n=5)
    if pairs_df is not None and not pairs_df.empty:
        display_pairs = pairs_df[["Bundle", "Correlation", "Expected_Quarterly_Return", "Portfolio_Volatility"]]
        styled_pairs = (
            display_pairs.style
            .format({"Correlation": "{:.3f}","Expected_Quarterly_Return": "{:.2f}%","Portfolio_Volatility": "{:.4f}"})
        )
        st.dataframe(styled_pairs, use_container_width=True, hide_index=True)
        st.info("Lower correlation indicates better diversification. Expected return assumes equal-weight allocation. Target: 5-6% quarterly.")
    else:
        st.warning("Need at least 2 stocks for diversification analysis.")

# ============= TAB 2 =============
with tab2:
    st.subheader("Indian Market Indices Overview")
    
    indices_df = load_sector_indices_data()
    if indices_df.empty:
        st.error("Unable to fetch sector indices data.")
    else:
        cols = st.columns(3)
        for idx, row in indices_df.iterrows():
            col = cols[idx % 3]
            with col:
                change_color = "green" if row["Day %"] > 0 else "red"
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:15px;border-radius:8px;color:white;text-align:center;margin:5px;">
                    <div style="font-size:12px;opacity:0.9;">{row['Index']}</div>
                    <div style="font-size:20px;font-weight:bold;">{row['Price']:.2f}</div>
                    <div style="font-size:14px;color:{change_color};font-weight:bold;">{row['Day %']:+.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        st.subheader("Detailed Sector Index Performance")
        styled_sector = (
            indices_df.style
            .format({"Price": "{:.2f}","Day %": "{:.2f}","Month %": "{:.2f}","Year %": "{:.2f}","52W High": "{:.2f}","52W Low": "{:.2f}"})
            .map(lambda x: 'color: green; font-weight: bold' if (isinstance(x, (int, float)) and x > 0) else 'color: red; font-weight: bold' if (isinstance(x, (int, float)) and x < 0) else '', subset=["Day %", "Month %", "Year %"])
        )
        st.dataframe(styled_sector, use_container_width=True, hide_index=True)
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Day Performance")
            fig_day = px.bar(indices_df, x="Index", y="Day %", color="Day %", color_continuous_scale="RdYlGn")
            fig_day.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_day, use_container_width=True)
        with col_right:
            st.subheader("Year Performance")
            fig_year = px.bar(indices_df, x="Index", y="Year %", color="Year %", color_continuous_scale="RdYlGn")
            fig_year.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_year, use_container_width=True)

# ============= TAB 3 =============
with tab3:
    df, price_map = load_data(tuple(st.session_state.tickers))
    if df.empty:
        st.warning("No valid data found.")
    else:
        sectors = sorted(df["Sector"].unique())
        selected_sector = st.selectbox("Select Sector", sectors)
        sector_stocks = df[df["Sector"] == selected_sector].sort_values("Momentum_Score", ascending=False)
        st.subheader(f"Sector: {selected_sector} ({len(sector_stocks)} Stocks)")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_momentum = sector_stocks["Momentum_Score"].mean()
            st.metric("Average Momentum", f"{avg_momentum:.2f}")
        with col2:
            top_performer = sector_stocks.iloc[0]
            st.metric("Top Performer", top_performer["Ticker"], f"{top_performer['Momentum_Score']:.2f}")
        with col3:
            avg_year_return = sector_stocks["Year %"].mean()
            st.metric("Average Year Return", f"{avg_year_return:.2f}%")
        with col4:
            positive_momentum = len(sector_stocks[sector_stocks["Momentum"].isin(["Bullish", "Positive"])])
            st.metric("Bullish Stocks", f"{positive_momentum}/{len(sector_stocks)}")
        
        st.divider()
        sector_table = sector_stocks[["Ticker", "Price", "Day %", "Month %", "Year %", "Momentum", "Momentum_Score", "Drawdown %"]].copy()
        styled_sector = (
            sector_table.style
            .format({"Price": "{:.2f}","Day %": "{:.2f}","Month %": "{:.2f}","Year %": "{:.2f}","Momentum_Score": "{:.2f}","Drawdown %": "{:.2f}"})
            .map(color_signal, subset=["Momentum"])
            .map(lambda x: 'color: green; font-weight: bold' if (isinstance(x, (int, float)) and x > 0) else 'color: red; font-weight: bold' if (isinstance(x, (int, float)) and x < 0) else '', subset=["Day %", "Month %", "Year %", "Drawdown %"])
        )
        st.dataframe(styled_sector, use_container_width=True, hide_index=True)
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Momentum Scores")
            fig_momentum = px.bar(sector_stocks, x="Ticker", y="Momentum_Score", color="Momentum_Score", color_continuous_scale="RdYlGn")
            st.plotly_chart(fig_momentum, use_container_width=True)
        with col_right:
            st.subheader("Year Return Distribution")
            fig_return = px.bar(sector_stocks, x="Ticker", y="Year %", color="Year %", color_continuous_scale="RdYlGn")
            st.plotly_chart(fig_return, use_container_width=True)
