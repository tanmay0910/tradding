import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import feedparser
import urllib.parse
import time
from nsepython import nse_eq, nse_events, nse_preopen, nse_eq_symbols, fnolist
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# --- 1. SETUP & MEMORY ---
st.set_page_config(page_title="Alpha Feed Terminal", layout="wide")
analyzer = SentimentIntensityAnalyzer()

# Memory: Now stores a LIST of up to 5 stocks instead of just 1
if 'triggered_stocks' not in st.session_state:
    st.session_state.triggered_stocks = []
if 'scan_index' not in st.session_state:
    st.session_state.scan_index = 0
if 'news_cache' not in st.session_state:
    st.session_state.news_cache = {}

st.markdown("""
<style>
    .flash { background-color: #ff3333; padding: 10px; border-radius: 5px; color: white; text-align: center; font-weight: bold; animation: blinker 1s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    div[data-testid="stMetric"] { background-color: #121212; border: 1px solid #333; padding: 15px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- 2. ENGINE FUNCTIONS ---
def fetch_and_score_catalysts(symbol):
    """Fetches and scores news. Uses a dictionary cache so it doesn't fetch the same news twice."""
    if symbol in st.session_state.news_cache:
        return st.session_state.news_cache[symbol]
        
    catalysts = []
    try:
        events = nse_events(symbol)
        if events:
            for ev in events[:3]:
                score = analyzer.polarity_scores(ev.get('desc', ''))['compound']
                catalysts.append({"Source": "NSE", "Headline": ev.get('desc', ''), "Score": score})
    except: pass
    
    try:
        safe_q = urllib.parse.quote(f"{symbol} stock news india")
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={safe_q}&hl=en-IN&gl=IN")
        for e in feed.entries[:4]:
            score = analyzer.polarity_scores(e.title)['compound']
            catalysts.append({"Source": "News", "Headline": e.title, "Score": score})
    except: pass
    
    st.session_state.news_cache[symbol] = catalysts
    return catalysts

def color_sentiment(val):
    try:
        score = float(val)
        if score >= 0.05: return 'color: #00ffcc; font-weight: bold;'
        elif score <= -0.05: return 'color: #ff3333; font-weight: bold;'
        else: return 'color: #aaaaaa;'
    except: return ''

def render_chart(symbol):
    """Note: container_id must be unique (tv_chart_{symbol}) so 5 charts can exist together."""
    html = f"""
    <div class="tradingview-widget-container"><div id="tv_chart_{symbol}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{"autosize": true, "symbol": "NSE:{symbol}", "interval": "1", "theme": "dark", "style": "1", "container_id": "tv_chart_{symbol}"}});
      </script></div>
    """
    components.html(html, height=450)

st.title("⚡ Autonomous Multi-Feed Terminal")
st.markdown("---")

# --- 3. THE TABS ---
tab_hub, tab_pmo, tab_del, tab_earn, tab_risk = st.tabs([
    "🎯 Live Breakout Feed", "🕒 PMO Sniper", "💎 Smart Money (>60%)", "📅 Earnings", "🧮 Risk Calculator"
])

# ---------------------------------------------------------
# TAB 1: THE LIVE FEED (Up to 5 Stocks Stacked)
# ---------------------------------------------------------
with tab_hub:
    col_scan, col_feed = st.columns([1, 2.5])

    # LEFT COLUMN: THE SCANNER ENGINE
    with col_scan:
        st.subheader("Radar Controls")
        auto_pilot = st.toggle("▶ ACTIVATE AUTO-PILOT")
        status = st.empty()
        flash_area = st.empty()
        
        if st.button("🗑️ Clear Feed"):
            st.session_state.triggered_stocks = []
            st.rerun()

    # RIGHT COLUMN: THE 5-STOCK STACK
    with col_feed:
        st.subheader("🔥 Live Breakout Stack")
        if not st.session_state.triggered_stocks:
            st.info("📡 Radar sweeping... Breakouts will stack here automatically.")
        
        # Loop through our saved stocks and render their Chart + News
        for sym in st.session_state.triggered_stocks:
            st.markdown(f"### 🎯 {sym} | Live 1-Minute Action")
            render_chart(sym)
            
            cat_data = fetch_and_score_catalysts(sym)
            if cat_data:
                df_cat = pd.DataFrame(cat_data).sort_values(by="Score", ascending=False)
                styled_df = df_cat.style.map(color_sentiment, subset=['Score'])
                st.dataframe(styled_df, width='stretch', hide_index=True)
            else:
                st.write("No catalyst found.")
            st.markdown("---") # Visual divider between the 5 stocks

    # THE BACKGROUND AUTONOMOUS LOOP
    if auto_pilot:
        try: watchlist = nse_eq_symbols()
        except: watchlist = fnolist()
            
        start = st.session_state.scan_index
        end = start + 5
        if end >= len(watchlist): 
            end = len(watchlist)
            st.session_state.scan_index = 0
        else: st.session_state.scan_index = end
            
        for symbol in watchlist[start:end]:
            status.text(f"Scanning: {symbol}")
            try:
                data = nse_eq(symbol)
                price = data['priceInfo']['lastPrice']
                
                if price > 50: # Anti-Penny Filter
                    vwap = data['priceInfo']['vwap']
                    today_vol = data['marketDeptOrderBook']['tradeInfo']['totalTradedVolume']
                    prev_vol = data['priceInfo']['previousCloseVolume']
                    
                    # The Breakout Logic
                    if price > vwap and today_vol > (prev_vol * 0.10):
                        if symbol not in st.session_state.triggered_stocks:
                            # Add to the top of the list
                            st.session_state.triggered_stocks.insert(0, symbol)
                            # Keep only the newest 5 to prevent browser crashing
                            st.session_state.triggered_stocks = st.session_state.triggered_stocks[:5]
                            # REPLACE 'winsound.Beep(1000, 500)' WITH THIS:
                            if HAS_WINSOUND:
                                winsound.Beep(1000, 500)
                            else:
                                print("Beep: Volume Breakout Detected!")
                            flash_area.markdown('<div class="flash">⚠️ NEW BREAKOUT ADDED TO FEED ⚠️</div>', unsafe_allow_html=True)
                            st.rerun() # Refresh the UI to show the new stock in the right column
            except: pass
            
        time.sleep(1)
        st.rerun()

# ---------------------------------------------------------
# TABS 2-5: YOUR OTHER TOOLS
# ---------------------------------------------------------
with tab_pmo:
    st.subheader("Early Identification: Pre-Open Leaders")
    if st.button("▶ Run Pre-Market Scan"):
        try:
            pmo_data = nse_preopen("NIFTY")
            df_p = pd.DataFrame(pmo_data['data'])
            st.dataframe(df_p[df_p['quantity'] > 5000].sort_values(by='quantity', ascending=False)[['symbol', 'lastPrice', 'pChange', 'quantity']], width='stretch', hide_index=True)
        except: st.warning("Pre-open unavailable.")

# ---------------------------------------------------------
# TAB 3: SMART MONEY ABSORPTION (60% DELIVERY)
# ---------------------------------------------------------
# ---------------------------------------------------------
# TAB 3: SMART MONEY ABSORPTION (60% DELIVERY)
# ---------------------------------------------------------
with tab_del:
    st.subheader("💎 Institutional Hoarding (> 60% Delivery)")
    st.markdown("Scanning ALL 200+ F&O equities for massive delivery absorption.")
    
    # --- REAL SCANNER ---
    if st.button("▶ Scan Entire F&O List", type="primary"):
        del_list = []
        progress = st.progress(0)
        status_text = st.empty()
        
        watch = fnolist() 
        for i, sym in enumerate(watch):
            # FIX: Skip non-tradable indices!
            if sym in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTYIT']:
                continue
                
            progress.progress((i + 1) / len(watch))
            status_text.text(f"Analyzing {sym}... ({i+1}/{len(watch)})")
            
            try:
                d = nse_eq(sym)
                trade_info = d.get('marketDeptOrderBook', {}).get('tradeInfo', {})
                pct_raw = trade_info.get('deliveryToTradedQuantity', trade_info.get('deliveryPercentage', 0))
                
                if pct_raw and str(pct_raw) != '-':
                    clean_pct = str(pct_raw).replace('%', '').replace(',', '').strip()
                    pct = float(clean_pct)
                    if pct > 60.0: 
                        del_list.append({"Symbol": sym, "Delivery %": f"{pct}%", "LTP": f"₹{d.get('priceInfo', {}).get('lastPrice', 0)}"})
            except Exception: pass
            time.sleep(0.3)
            
        progress.empty()
        status_text.empty()
        
        if del_list:
            df = pd.DataFrame(del_list)
            df['Sort_Val'] = df['Delivery %'].str.replace('%', '').astype(float)
            df = df.sort_values(by='Sort_Val', ascending=False).drop('Sort_Val', axis=1)
            st.success(f"✅ Hunt complete. Found {len(df)} stocks being hoarded.")
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.warning("Scan complete. No equities passed the strict 60% threshold.")

    st.markdown("---")
    
    # --- X-RAY DIAGNOSTIC TOOL ---
    st.subheader("🛠️ API X-Ray Diagnostic Mode")
    if st.button("▶ Run X-Ray on Top 3 Equities"):
        watch = fnolist()
        count = 0
        
        for sym in watch:
            # FIX: Skip non-tradable indices so we only X-Ray real stocks!
            if sym in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTYIT']:
                continue
                
            try:
                d = nse_eq(sym)
                trade_info = d.get('marketDeptOrderBook', {}).get('tradeInfo', {})
                
                st.markdown(f"### Raw NSE Data for {sym}:")
                st.json(trade_info) 
                count += 1
            except Exception as e:
                st.error(f"Connection blocked or failed for {sym}. Error: {e}")
            
            if count >= 3:
                break # Stop after showing 3 real stocks
            time.sleep(1)
with tab_earn:
    st.subheader("📅 Live Earnings & Board Meetings")
    earn_sym = st.text_input("Symbol:").upper()
    if st.button("Fetch Events") and earn_sym:
        try:
            evs = nse_events(earn_sym)
            if evs: 
                for ev in evs[:5]: st.markdown(f"🗓️ **{ev.get('date')}**: {ev.get('desc')}")
        except: st.error("Connection error.")

with tab_risk:
    st.subheader("🧮 Fixed ₹100 Risk Calculator")
    e_p, s_l = st.number_input("Entry Price", value=100.0), st.number_input("Stop Loss", value=98.0)

    if e_p > s_l: st.metric("Shares to Buy", int(100 / (e_p - s_l)))
