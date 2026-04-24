import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

st.set_page_config(page_title='Family Stock Dashboard', layout='wide', page_icon='📈')

PASSWORD='family2025'
DEFAULT_TICKERS=['IREDA.NS','BEL.NS','AFFLE.NS','HAVELLS.NS','POLYCAB.NS','BAJAJ-AUTO.NS']

if 'authenticated' not in st.session_state:
    st.session_state.authenticated=False
if 'tickers' not in st.session_state:
    st.session_state.tickers=DEFAULT_TICKERS.copy()

# Login
if not st.session_state.authenticated:
    st.markdown("""
    <style>
    .stApp{background:#070d1a;color:#e2e8f0}
    .login{max-width:420px;margin:12vh auto;padding:2rem;background:#0f172a;border:1px solid #1e293b;border-radius:16px}
    </style>
    <div class='login'><h1>📈 Stock Dashboard</h1><p>Enter password</p></div>
    """, unsafe_allow_html=True)
    pwd=st.text_input('Password', type='password')
    if st.button('Login', use_container_width=True):
        if pwd==PASSWORD:
            st.session_state.authenticated=True
            st.rerun()
        else:
            st.error('Incorrect password')
    st.stop()

# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
html,body,.stApp{font-family:'DM Sans',sans-serif;background:#070d1a;color:#e2e8f0}
h1,h2,h3{color:#e2e8f0 !important}
section[data-testid='stSidebar']{background:#0f172a}
.metric-card{background:#0d1829;border:1px solid #1a2744;border-radius:12px;padding:1rem;margin-bottom:.75rem}
.small{color:#94a3b8;font-size:.8rem}
.green{color:#22c55e;font-weight:700}.red{color:#ef4444;font-weight:700}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=900)
def load_data(tickers):
    rows=[]
    for t in tickers:
        try:
            h=yf.Ticker(t).history(period='1y')
            info=yf.Ticker(t).info
            c=h['Close']
            rows.append({
                'Ticker':t,
                'Company':info.get('longName',t),
                'Sector':info.get('sector','N/A'),
                'Price':round(c.iloc[-1],2),
                'Day %':round((c.iloc[-1]/c.iloc[-2]-1)*100,2),
                'Month %':round((c.iloc[-1]/c.iloc[-21]-1)*100,2),
                'Year %':round((c.iloc[-1]/c.iloc[0]-1)*100,2),
                '52W High':round(c.max(),2),
                '52W Low':round(c.min(),2),
            })
        except:
            pass
    return pd.DataFrame(rows)

with st.sidebar:
    page=st.radio('Navigation',['Technical'])
    new_ticker=st.text_input('Add Ticker')
    if st.button('Add', use_container_width=True):
        v=new_ticker.strip().upper()
        if v and v not in st.session_state.tickers:
            st.session_state.tickers.append(v)
            st.cache_data.clear(); st.rerun()
    rem=st.selectbox('Remove Ticker',['']+st.session_state.tickers)
    if st.button('Remove', use_container_width=True):
        if rem:
            st.session_state.tickers.remove(rem)
            st.cache_data.clear(); st.rerun()
    if st.button('Refresh Data', use_container_width=True):
        st.cache_data.clear(); st.rerun()
    if st.button('Reset Defaults', use_container_width=True):
        st.session_state.tickers=DEFAULT_TICKERS.copy(); st.cache_data.clear(); st.rerun()
    if st.button('Logout', use_container_width=True):
        st.session_state.authenticated=False; st.rerun()

st.title('📈 Technical Dashboard')
df=load_data(tuple(st.session_state.tickers))

if not df.empty:
    st.subheader('Performance Leaders')
    c1,c2,c3=st.columns(3)
    metrics=[('Day %','Day'),('Month %','Month'),('Year %','Year')]
    for col_obj,(metric,label) in zip([c1,c2,c3],metrics):
        g=df.loc[df[metric].idxmax()]
        l=df.loc[df[metric].idxmin()]
        with col_obj:
            st.markdown(f"<div class='metric-card'><div class='small'>{label} Gainer</div><b>{g['Ticker']}</b><div class='green'>{g[metric]:+.2f}%</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-card'><div class='small'>{label} Loser</div><b>{l['Ticker']}</b><div class='red'>{l[metric]:+.2f}%</div></div>", unsafe_allow_html=True)

    st.subheader('Portfolio Table')
    st.dataframe(df, use_container_width=True, hide_index=True, height=420)

    a,b=st.columns(2)
    with a:
        st.subheader('Sector Concentration')
        s=df.groupby('Sector').size().reset_index(name='Count')
        fig=px.pie(s, names='Sector', values='Count', hole=.45)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0')
        st.plotly_chart(fig, use_container_width=True)
    with b:
        st.subheader('Returns Snapshot')
        chart=df[['Ticker','Day %','Month %','Year %']].set_index('Ticker')
        st.bar_chart(chart)
else:
    st.warning('No valid tickers loaded.')
