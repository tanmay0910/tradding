import streamlit as st
import pandas as pd
import time
from nsepython import nse_eq, fnolist

# --- 1. SYSTEM LOGGING ---
def log(msg, type="info"):
    if type == "error": st.sidebar.error(msg)
    elif type == "success": st.sidebar.success(msg)
    else: st.sidebar.write(msg)

st.set_page_config(page_title="Alpha Hunter V3", layout="wide")
st.title("⚡ Alpha Hunter: Stability Edition")

# --- 2. THE ULTIMATE DATA FETCH ---
def get_delivery_data(symbol):
    try:
        data = nse_eq(symbol)
        if not data: return None
        
        # We search every possible location for delivery data
        trade_info = data.get('marketDeptOrderBook', {}).get('tradeInfo', {})
        sec_wise = data.get('securityWiseDP', {}) # Alternative key used in 2026
        
        # Try Live Key -> Try SecurityWise Key -> Try Prev Day Key
        pct = trade_info.get('deliveryPercentage', 
                sec_wise.get('deliveryPercentage', 
                trade_info.get('deliveryToTradedQuantity', 0)))
        
        # Debugging: Log what we found
        if pct and str(pct) != '-':
            return {"symbol": symbol, "pct": float(str(pct).replace('%','')), "price": data['priceInfo']['lastPrice']}
        else:
            log(f"{symbol}: No live delivery data yet. NSE updates this after 4:30 PM.", "error")
            return None
    except:
        return None

# --- 3. EXECUTION TABS ---
tab_del, tab_risk = st.tabs(["💎 Smart Money", "🧮 Risk Manager"])

with tab_del:
    if st.button("▶ Start Full Equity Scan", type="primary"):
        results = []
        progress = st.progress(0)
        
        # Scan a focused batch of top F&O movers
        watch = fnolist()[:50] 
        
        for i, sym in enumerate(watch):
            progress.progress((i + 1) / len(watch))
            if sym in ['NIFTY', 'BANKNIFTY']: continue
            
            log(f"Hunting {sym}...")
            res = get_delivery_data(sym)
            
            if res and res['pct'] > 60:
                log(f"🎯 MATCH: {sym} at {res['pct']}%", "success")
                results.append(res)
            
            time.sleep(0.8) # Prevent IP Blocking
            
        if results:
            st.success(f"Scan complete. {len(results)} institutional hoarding setups found.")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.warning("No stocks passed the 60% threshold. Try scanning after 4:30 PM for final data.")
