import streamlit as st
import yfinance as yf
import json
import os
import re
from datetime import datetime
from PIL import Image

# --- Configuration & State ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_storage.json")
LOCAL_ICON = os.path.join(BASE_DIR, "assets", "icon.png")
ICON_URL = "https://raw.githubusercontent.com/kudsv255tami-glitch/kaitsuke-kanshikun/main/assets/icon.png"
UPDATE_INTERVAL = 300 

st.set_page_config(page_title="買付監視くん", page_icon=Image.open(LOCAL_ICON) if os.path.exists(LOCAL_ICON) else "🏹", layout="centered")

if "last_refresh" not in st.session_state: st.session_state.last_refresh = datetime.now()

# --- Functions ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"stocks": []}

def save_data(data):
    data['stocks'].sort(key=lambda x: x['ticker'])
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

def normalize_ticker(ticker):
    t = ticker.strip().upper()
    if t.endswith(".T") or "." in t: return t
    return t + ".T" if len(t) == 4 else t

def fetch_price(ticker):
    final_ticker = normalize_ticker(ticker)
    try:
        stock = yf.Ticker(final_ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            p = hist['Close'].iloc[-1]
            info = stock.info
            name = info.get('longName') or info.get('shortName') or final_ticker
            if final_ticker.endswith(".T"):
                name = re.sub(r'\b(CORP|INC|LTD|HOLDINGS|GROUP|JAPAN)\b', '', name.upper()).strip()
            u = "円" if info.get('currency', 'JPY') == "JPY" else "ドル"
            return round(p, 2), name, final_ticker, u
        return None, None, final_ticker, "円"
    except: return None, None, final_ticker, "円"

# --- UI Styling (Ultra Compact) ---
st.markdown(f"""
<style>
    header, footer, #MainMenu {{ visibility: hidden; display: none !important; }}
    [data-testid="stHeader"] {{ height: 0px !important; display: none !important; }}
    [data-testid="stMainBlockContainer"] {{ padding: 0.8rem !important; padding-top: 1rem !important; max-width: 100% !important; }}
    .stApp {{ background-color: #f2f2f7; }}
    
    /* Compact Containers */
    [data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: white; border-radius: 12px; padding: 12px; border: 1px solid #e5e5ea; margin-bottom: 8px;
    }}
    
    /* Metric Override */
    [data-testid="stMetricValue"] {{ font-size: 2rem !important; font-weight: 800 !important; color: #007aff !important; }}
    [data-testid="stMetricLabel"] {{ font-size: 1rem !important; font-weight: 700 !important; color: #1c1c1e !important; }}
    [data-testid="stMetric"] {{ margin-bottom: -10px !important; }}
    
    /* Horizontal Targets */
    .target-grid {{ display: flex; justify-content: space-between; gap: 10px; border-top: 1px solid #f2f2f7; padding-top: 8px; margin-top: 2px; }}
    .target-box {{ flex: 1; }}
    .t-lbl {{ font-size: 0.75rem; color: #8e8e93; font-weight: 600; margin-bottom: 2px; }}
    .t-val {{ font-size: 0.95rem; font-weight: 700; color: #1c1c1e; }}
    .t-status {{ font-size: 0.7rem; font-weight: 800; color: #34c759; margin-top: 2px; }}
    .t-wait {{ font-size: 0.7rem; color: #aeaeb2; margin-top: 2px; }}

    input {{ font-size: 16px !important; }}
</style>
""", unsafe_allow_html=True)

# JS for Auto-Refresh only
st.components.v1.html(f"""
<script>
if (!window.kInjected) {{
    window.kInjected = true;
    setInterval(() => {{
        const b = window.parent.document.querySelector('button[kind="secondary"]');
        if (b && (b.innerText.includes("更新") || b.innerText.includes("Refresh"))) b.click();
    }}, {UPDATE_INTERVAL * 1000});
}}
</script>
""", height=0)

# --- Header ---
st.markdown(f"<div style='display:flex; align-items:center; gap:8px; margin-bottom:10px;'><img src='{ICON_URL}' width='40'><h1 style='margin:0; font-size:1.5rem;'>買付監視くん</h1></div>", unsafe_allow_html=True)

# --- Add ---
with st.expander("➕ 銘柄を追加"):
    cs1, cs2 = st.columns([3, 1])
    tin = cs1.text_input("コード", placeholder="例: 7203", label_visibility="collapsed").upper()
    if cs2.button("追加", use_container_width=True, type="primary") and tin:
        p, n, t, u = fetch_price(tin)
        if p:
            db = load_data()
            if not any(s['ticker'] == t for s in db['stocks']):
                db['stocks'].append({"ticker":t, "name":n, "last_price":p, "unit":u, "odd_lot_target":0.0, "one_lot_target":0.0})
                save_data(db); st.rerun()
            else: st.warning("追加済み")
        else: st.error("取得失敗")

# --- Stock Watchlist ---
db = load_data()
if not db['stocks']:
    st.info("銘柄を追加してください")
else:
    for idx, s in enumerate(db['stocks']):
        unit = s.get("unit", "円")
        pnow = s['last_price']
        t1, t2 = float(s.get('odd_lot_target', 0)), float(s.get('one_lot_target', 0))
        
        with st.container(border=True):
            # Price Section
            st.metric(label=f"{s['name']}", value=f"{pnow:,.2f} {unit}")
            st.caption(f"コード: {s['ticker']}")
            
            # Targets Section (Forced Horizontal via HTML)
            t1_html = f"<div class='t-val'>{t1:,.2f}{unit}</div><div class='t-status'>✅ 到達</div>" if (t1 > 0 and pnow <= t1) else f"<div class='t-val'>{t1:,.2f}{unit}</div><div class='t-wait'>監視中</div>" if t1 > 0 else "<div class='t-val'>未設定</div>"
            t2_html = f"<div class='t-val'>{t2:,.2f}{unit}</div><div class='t-status'>✅ 到達</div>" if (t2 > 0 and pnow <= t2) else f"<div class='t-val'>{t2:,.2f}{unit}</div><div class='t-wait'>監視中</div>" if t2 > 0 else "<div class='t-val'>未設定</div>"
            
            st.markdown(f"""
            <div class="target-grid">
                <div class="target-box">
                    <div class="t-lbl">単元未満</div>
                    {t1_html}
                </div>
                <div class="target-box">
                    <div class="t-lbl">単元</div>
                    {t2_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Integrated Settings
            if st.button(f"⚙️ 設定/削除 ({s['ticker']})", key=f"btn_{s['ticker']}", use_container_width=True):
                st.session_state[f"ed_{s['ticker']}"] = not st.session_state.get(f"ed_{s['ticker']}", False)
            
            if st.session_state.get(f"ed_{s['ticker']}", False):
                with st.form(f"form_{s['ticker']}"):
                    nn = st.text_input("表示名", value=s['name'])
                    nu = st.selectbox("通貨", ["円", "ドル"], 0 if unit=="円" else 1)
                    ec1, ec2 = st.columns(2)
                    v1 = ec1.number_input("単元未満目標", value=t1, step=0.1)
                    v2 = ec2.number_input("単元目標", value=t2, step=0.1)
                    eb1, eb2 = st.columns(2)
                    if eb1.form_submit_button("保存"):
                        s['name'], s['unit'], s['odd_lot_target'], s['one_lot_target'] = nn, nu, v1, v2
                        save_data(db); st.session_state[f"ed_{s['ticker']}"] = False; st.rerun()
                    if eb2.form_submit_button("削除"):
                        db['stocks'].pop(idx); save_data(db); st.rerun()

# --- Footer ---
st.divider()
fl1, fl2 = st.columns([3, 1])
fl1.caption(f"最終更新: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
if fl2.button("🔄 更新", use_container_width=True):
    ndb = load_data()
    for item in ndb['stocks']:
        px, _, _, _ = fetch_price(item['ticker'])
        if px: item['last_price'] = px
    save_data(ndb); st.session_state.last_refresh = datetime.now(); st.rerun()
