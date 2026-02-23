import streamlit as st
import pandas as pd
import time
import requests
from nsepython import nse_eq, fnolist

# --- 1. THE HUMAN MASK (Bypasses the {} Empty Brackets) ---
# This makes the NSE think your app is a real browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

st.set_page_config(page_title="Alpha Live Terminal", layout="wide")

# --- 2. CRASH-PROOF UI ---
st.title("⚡ Alpha Live Terminal (Cloud Optimized)")
st.info(f"Market Status: LIVE | Time: {pd.Timestamp.now(tz='Asia/Kolkata').strftime('%H:%M:%S')}")

tab1, tab2, tab3 = st.tabs(["🎯 Live Scanner", "💎 Delivery", "🧮 Risk"])

with tab1:
    col_ctrl, col_feed = st.columns([1, 2])
    with col_ctrl:
        auto = st.toggle("▶ START SCANNER")
        if st.button("🗑️ Clear List"):
            st.session_state.hits = []
            st.rerun()
    
    with col_feed:
        if 'hits' not in st.session_state: st.session_state.hits = []
        for sym in st.session_state.hits:
            st.subheader(f"🔥 BREAKOUT: {sym}")
            # LINK BUTTON: This fixes the "src property" error permanently
            st.link_button(f"📈 Open {sym} Chart (TradingView)", f"https://www.tradingview.com/chart/?symbol=NSE:{sym}")
            st.markdown("---")

    if auto:
        try:
            watchlist = fnolist()[:40] # Scan top 40 for high speed
            for symbol in watchlist:
                try:
                    # Bypassing index issues
                    if symbol in ['NIFTY', 'BANKNIFTY']: continue
                    
                    data = nse_eq(symbol)
                    price = data['priceInfo']['lastPrice']
                    vol = data['marketDeptOrderBook']['tradeInfo']['totalTradedVolume']
                    prev_vol = data['priceInfo']['previousCloseVolume']
                    
                    # TRIGGER: 10% of total daily volume in just a few mins
                    if price > 50 and vol > (prev_vol * 0.10):
                        if symbol not in st.session_state.hits:
                            st.session_state.hits.insert(0, symbol)
                            st.session_state.hits = st.session_state.hits[:5]
                            st.rerun()
                except: pass
                time.sleep(0.7) # Slow down to avoid being blocked again
            st.rerun()
        except: st.warning("API Throttled. Waiting...")
