import streamlit as st
import pandas as pd
import time
from nsepython import nse_eq, fnolist

# --- 1. DEBUGGING ENGINE ---
def debug_log(msg, type="info"):
    """Helper to show what's happening behind the scenes"""
    if type == "error":
        st.sidebar.error(f"❌ {msg}")
    elif type == "success":
        st.sidebar.success(f"✅ {msg}")
    else:
        st.sidebar.write(f"🔍 {msg}")

st.set_page_config(page_title="Alpha Debug Mode", layout="wide")
st.sidebar.title("🛠️ System Logs")

# --- 2. STABILIZED FETCH WITH LOGS ---
def fetch_with_debug(symbol):
    try:
        debug_log(f"Requesting {symbol}...")
        data = nse_eq(symbol)
        
        if not data:
            debug_log(f"{symbol}: Server returned EMPTY object.", "error")
            return None
        
        if 'priceInfo' not in data:
            debug_log(f"{symbol}: 'priceInfo' missing. (Market closed/Blocked?)", "error")
            return None
            
        debug_log(f"{symbol}: Data received successfully.", "success")
        return data
    except Exception as e:
        debug_log(f"{symbol}: Crash -> {str(e)}", "error")
        return None

# --- 3. THE DELIVERY SCANNER (WITH FULL TRACING) ---
st.title("⚡ Alpha Hunter (Debug Mode)")
tab_del, tab_risk = st.tabs(["💎 Smart Money Scan", "🧮 Risk"])

with tab_del:
    st.markdown("Monitor the **Sidebar Logs** to see why stocks are being skipped.")
    
    if st.button("▶ Run Full Trace Scan"):
        results = []
        progress = st.progress(0)
        
        # Step 1: Fetch List
        try:
            watch = fnolist()
            debug_log(f"F&O List Loaded: {len(watch)} symbols.")
        except:
            st.error("Could not load F&O list. Check Internet.")
            st.stop()
            
        # Step 2: Loop with Debugging
        target_list = watch[10:40] # Scan a batch of 30
        
        for i, sym in enumerate(target_list):
            progress.progress((i + 1) / len(target_list))
            
            # Skip Indices
            if any(idx in sym for idx in ['NIFTY', 'BANKNIFTY']):
                debug_log(f"Skipping Index: {sym}")
                continue
                
            d = fetch_with_debug(sym)
            if d:
                # TRACING THE DELIVERY KEY
                trade_info = d.get('marketDeptOrderBook', {}).get('tradeInfo', {})
                
                # Check Key A
                pct = trade_info.get('deliveryPercentage')
                if pct is not None:
                    debug_log(f"{sym}: Found 'deliveryPercentage' = {pct}")
                else:
                    # Check Key B
                    pct = trade_info.get('deliveryToTradedQuantity')
                    if pct is not None:
                        debug_log(f"{sym}: Found 'deliveryToTradedQuantity' = {pct}")
                    else:
                        debug_log(f"{sym}: NO DELIVERY KEY FOUND.", "error")
                
                # Filter Logic
                if pct and str(pct) != '-':
                    clean_val = float(str(pct).replace('%', '').strip())
                    if clean_val > 60:
                        debug_log(f"🎯 MATCH FOUND: {sym} ({clean_val}%)", "success")
                        results.append({"Symbol": sym, "Delivery": f"{clean_val}%", "Price": d['priceInfo']['lastPrice']})
            
            time.sleep(1.0) # Be very gentle to avoid IP block
            
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.warning("Scan finished. Check logs to see if you were blocked or if no matches exist.")
