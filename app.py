# ----------------- Setting up the libraries ----------------- #

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import json
import os

"""
This is a simple dashboard for watching over selected stocks. 
The stocks are saved in stocks.json, which is stored in a public repository.
The website is hosted on streamlit. 
"""


# ----------------- Loading the watchlist ----------------- #

WATCHLIST_FILE = "stocks.json"
DEFAULT_TICKERS = ["IREDA.NS", "BEL.NS"]
   
def load_tickers():
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict) and "tickers" in data:
                if isinstance(data["tickers"], list):
                    return [str(x).upper().strip() for x in data["tickers"] if str(x).strip()]

            if isinstance(data, list):
                return [str(x).upper().strip() for x in data if str(x).strip()]
    except:
        pass

    return DEFAULT_TICKERS.copy()

if "tickers" not in st.session_state:
    st.session_state.tickers = load_tickers()

def save_tickers(tickers):
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump({"tickers": tickers}, f, indent=4)
    except:
        pass

# ----------------- Cache Data ----------------- #

@st.cache_data(ttl=900)
def load_data(tickers):
    rows = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1y')
            info = stock.info
            close = hist['Close']
            rows.append({
                'Ticker': ticker,
                'Company': info.get('longName', ticker),
                'Sector': info.get('sector', 'N/A'),
                'Price': round(close.iloc[-1], 2),
                'Day %': round((close.iloc[-1]/close.iloc[-2]-1)*100, 2),
                'Month %': round((close.iloc[-1]/close.iloc[-21]-1)*100, 2),
                'Year %': round((close.iloc[-1]/close.iloc[0]-1)*100, 2),
                '52W High': round(close.max(), 2),
                '52W Low': round(close.min(), 2)
            })
        except:
            pass
    return pd.DataFrame(rows)

# ----------------- Sidebar Edits ----------------- #

with st.sidebar:
    st.header("Watchlist")

    new_ticker = st.text_input("Add Ticker")

    if st.button("Add"):
        value = new_ticker.strip().upper()

        if value:
            if value not in st.session_state.tickers:
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
# ----------------- Main Page ----------------- #

st.title('Stock Dashboard')

st.markdown("""
<style>
.leader-card{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:20px;min-height:150px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:16px}
.leader-label{font-size:16px;color:#64748b;margin-bottom:8px}
.leader-ticker{font-size:34px;font-weight:700;color:#111827;line-height:1.2}
.leader-green{font-size:20px;font-weight:700;color:#16a34a;margin-top:8px}
.leader-red{font-size:20px;font-weight:700;color:#dc2626;margin-top:8px}
</style>
""", unsafe_allow_html=True)

df = load_data(tuple(st.session_state.tickers))

# ----------------- Performance Dashboard ----------------- #

if not df.empty:
    c1, c2, c3 = st.columns(3)
    st.subheader('Performance Leaders')

    dg = df.loc[df['Day %'].idxmax()]
    dl = df.loc[df['Day %'].idxmin()]
    mg = df.loc[df['Month %'].idxmax()]
    ml = df.loc[df['Month %'].idxmin()]
    yg = df.loc[df['Year %'].idxmax()]
    yl = df.loc[df['Year %'].idxmin()]

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
    
    st.subheader('Portfolio Table')
    st.dataframe(df, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader('Sector Allocation')
        sector_df = df.groupby('Sector').size().reset_index(name='Count')
        fig = px.pie(sector_df, names='Sector', values='Count')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader('Returns Comparison')
        chart_df = df[['Ticker','Day %','Month %','Year %']].set_index('Ticker')
        st.bar_chart(chart_df)
else:
    st.warning('No data available.')
