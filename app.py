import streamlit as st
import pandas as pd
import time
from nsepython import nse_eq, fnolist

# --- 1. SETTINGS & BYPASS ---
st.set_page_config(page_title="Alpha Execution", layout="wide")

# This header makes the NSE think you are a real person on Chrome
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

st.title("⚡ Alpha Live Execution (9:45 AM Session)")
st.info("Direct Data Mode Active. If this shows empty, run the code LOCALLY via VS Code.")

# --- 2. THE TABS ---
tab_scan, tab_del, tab_risk = st.tabs(["🎯 Live Scanner", "💎 Delivery", "🧮 Risk"])

# ---------------------------------------------------------
# TAB 1: LIVE SCANNER (NO AUTO-REFRESH TO AVOID BLOCKS)
# ---------------------------------------------------------
with tab_scan:
    col_ctrl, col_feed = st.columns([1, 2])
    
    with col_ctrl:
        st.subheader("Scanner Controls")
        # Manual scanning is MUCH safer on the cloud than auto-pilot
        if st.button("▶ SCAN TOP 20 BREAKOUTS", type="primary"):
            st.session_state.hits = []
            with st.spinner("Hunting..."):
                # Scanning small batches prevents the NSE from 'Ghosting' your IP
                watchlist = fnolist()[10:30] 
                for symbol in watchlist:
                    try:
                        data = nse_eq(symbol)
                        price = data['priceInfo']['lastPrice']
                        vol = data['marketDeptOrderBook']['tradeInfo']['totalTradedVolume']
                        prev_vol = data['priceInfo']['previousCloseVolume']
                        
                        # 10% Volume Trigger
                        if price > 50 and vol > (prev_vol * 0.10):
                            st.session_state.hits.append(symbol)
                    except:
                        continue
                    time.sleep(0.6) # Wait to look human
            st.success("Scan Complete")

    with col_feed:
        if 'hits' in st.session_state and st.session_state.hits:
            for sym in st.session_state.hits:
                st.markdown(f"### 🔥 {sym}")
                # LINK BUTTONS ARE CRASH-PROOF
                st.link_button(f"📈 View {sym} Chart", f"https://www.tradingview.com/chart/?symbol=NSE:{sym}")
                st.markdown("---")
        else:
            st.write("No breakouts found in this batch. Click Scan to refresh.")

# ---------------------------------------------------------
# TAB 2: DELIVERY SCANNER
# ---------------------------------------------------------
with tab_del:
    st.subheader("Institutional Hoarding")
    if st.button("▶ Get High Delivery Stocks"):
        res = []
        # Target a specific safe range
        for sym in fnolist()[30:50]:
            try:
                d = nse_eq(sym)
                t = d.get('marketDeptOrderBook', {}).get('tradeInfo', {})
                # Try all known NSE delivery keys
                p = t.get('deliveryPercentage', t.get('deliveryToTradedQuantity', 0))
                if p and str(p) != '-' and float(str(p).replace('%','')) > 60:
                    res.append({"Symbol": sym, "Delivery": f"{p}%", "LTP": d['priceInfo']['lastPrice']})
            except: pass
            time.sleep(0.5)
        
        if res: st.dataframe(pd.DataFrame(res), use_container_width=True)
        else: st.warning("NSE Server returned empty. They have blocked this Cloud IP. Run locally.")
