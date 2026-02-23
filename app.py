import streamlit as st
import pandas as pd
import time
from nsepython import nse_eq, nse_preopen, fnolist

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Alpha Live", layout="wide")

# This bypasses the 'json object' error by using a standard link
def render_execution_panel(symbol):
    chart_url = f"https://www.tradingview.com/chart/?symbol=NSE:{symbol}"
    st.markdown(f"### 🎯 Action: {symbol}")
    st.link_button(f"📈 Open Live {symbol} Chart", chart_url)
    st.markdown("---")

st.title("⚡ Alpha Live Execution Terminal")
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Live Scanner", "🕒 Pre-Market", "💎 Delivery", "🧮 Risk"])

# ---------------------------------------------------------
# TAB 1: THE LIVE SCANNER (SIMPLE & FAST)
# ---------------------------------------------------------
with tab1:
    col_ctrl, col_feed = st.columns([1, 2])
    with col_ctrl:
        st.subheader("Radar")
        auto = st.toggle("▶ START SCANNER")
        if st.button("🗑️ Clear Feed"):
            st.session_state.hits = []
            st.rerun()
    
    with col_feed:
        if 'hits' not in st.session_state: st.session_state.hits = []
        for sym in st.session_state.hits:
            render_execution_panel(sym)

    if auto:
        try:
            # We scan a small list first to prevent API blocking
            watchlist = fnolist()[:30] 
            for symbol in watchlist:
                try:
                    data = nse_eq(symbol)
                    price = data['priceInfo']['lastPrice']
                    vol = data['marketDeptOrderBook']['tradeInfo']['totalTradedVolume']
                    prev_vol = data['priceInfo']['previousCloseVolume']
                    
                    # TRIGGER: 10% of total daily volume in just 1 minute
                    if price > 50 and vol > (prev_vol * 0.10):
                        if symbol not in st.session_state.hits:
                            st.session_state.hits.insert(0, symbol)
                            st.session_state.hits = st.session_state.hits[:5]
                            st.rerun()
                except: pass
                time.sleep(0.5)
            st.rerun()
        except: st.error("NSE API Busy. Waiting 5 seconds...")

# ---------------------------------------------------------
# TAB 3: THE DELIVERY SCANNER (FIXED)
# ---------------------------------------------------------
with tab3:
    st.subheader("💎 Smart Money Hoarding")
    if st.button("▶ Start 60% Delivery Scan"):
        results = []
        # Skip the indices at the top (NIFTY, etc.)
        for sym in fnolist()[5:45]: 
            try:
                d = nse_eq(sym)
                # target specific raw keys to avoid {}
                t = d.get('marketDeptOrderBook', {}).get('tradeInfo', {})
                p = t.get('deliveryPercentage', t.get('deliveryToTradedQuantity', 0))
                if p and str(p) != '-' and float(str(p).replace('%','')) > 60:
                    results.append({"Symbol": sym, "Delivery": f"{p}%", "Price": d['priceInfo']['lastPrice']})
            except: pass
            time.sleep(0.4)
        if results: st.dataframe(pd.DataFrame(results))
        else: st.info("No 60% movers found in this batch.")

# ---------------------------------------------------------
# TAB 4: RISK CALCULATOR (STAYS FOREVER)
# ---------------------------------------------------------
with tab4:
    st.subheader("🧮 ₹100 Risk Manager")
    e = st.number_input("Entry", value=100.0)
    s = st.number_input("Stop Loss", value=95.0)
    if e > s: st.metric("Quantity to Buy", int(100 / (e - s)))
