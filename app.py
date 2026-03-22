import streamlit as st
import yfinance as yf
import pandas as pd
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

if "notified_targets" not in st.session_state: st.session_state.notified_targets = set()
if "last_refresh" not in st.session_state: st.session_state.last_refresh = datetime.now()

# --- Logic ---
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

def translate_name_aggressive(name):
    translations = {"CORPORATION":"","CORP":"","LTD":"","INC":"","CO":"","HOLDINGS":"HD","GROUP":"G","JAPAN":"日本","EQUITY":"株","DIVIDEND":"配当","ROTATION":"ローテーション","STRATEGY":"戦略"}
    res = name.upper()
    for eng, jp in translations.items(): res = re.sub(rf'\b{eng}\b', jp, res)
    return res.replace("  ", " ").strip()

def fetch_price(ticker):
    final_ticker = normalize_ticker(ticker)
    try:
        stock = yf.Ticker(final_ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            info = stock.info
            raw_name = info.get('longName') or info.get('shortName') or final_ticker
            currency = "円" if info.get('currency', 'JPY') == "JPY" else "ドル"
            name = translate_name_aggressive(raw_name) if final_ticker.endswith(".T") else raw_name
            dividend = info.get('dividendYield', 0) * price if info.get('dividendYield') else info.get('trailingAnnualDividendRate', 0)
            return round(price, 2), name, dividend, final_ticker, currency
        return None, None, 0, final_ticker, "円"
    except Exception: return None, None, 0, final_ticker, "円"

# --- UI Styling ---
st.markdown(f"""
<style>
    header, footer, #MainMenu {{ visibility: hidden; display: none !important; }}
    [data-testid="stHeader"] {{ height: 0px !important; display: none !important; }}
    [data-testid="stMainBlockContainer"] {{ padding: 1rem !important; padding-top: 1.5rem !important; max-width: 100% !important; }}
    input, select, button {{ font-size: 16px !important; }}
    .stApp {{ background-color: #f2f2f7; }}
    .stock-card {{ background-color: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 12px; shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e5e5ea; }}
    .stock-title {{ font-size: 1.3rem; font-weight: 800; color: #1c1c1e; display: flex; align-items: center; justify-content: space-between; }}
    .ticker-badge {{ color: #8e8e93; font-size: 0.8rem; font-weight: 400; }}
    .price-large {{ font-size: 2.3rem; font-weight: 900; color: #007aff; text-align: right; margin: 8px 0; letter-spacing: -1px; }}
    .price-unit {{ font-size: 1rem; color: #3a3a3c; margin-left: 4px; }}
    .target-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; border-top: 1px solid #f2f2f7; padding-top: 12px; margin-top: 4px; }}
    .target-col {{ display: flex; flex-direction: column; gap: 2px; }}
    .label-tiny {{ font-size: 0.75rem; color: #8e8e93; font-weight: 500; }}
    .val-bold {{ font-size: 1rem; font-weight: 700; color: #1c1c1e; }}
    .pill {{ font-size: 0.7rem; font-weight: 800; padding: 3px 8px; border-radius: 10px; width: fit-content; margin-top: 4px; }}
    .pill-ok {{ background-color: #34c759; color: white; }}
    .pill-wait {{ background-color: #f2f2f7; color: #8e8e93; }}
</style>
""", unsafe_allow_html=True)

st.components.v1.html(f"""
<script>
if (!window.kInjected) {{
    window.kInjected = true;
    setInterval(() => {{
        const btn = window.parent.document.querySelector('button[kind="secondary"]');
        if (btn && (btn.innerText.includes("更新") || btn.innerText.includes("Refresh"))) btn.click();
    }}, {UPDATE_INTERVAL * 1000});
    const link = window.parent.document.createElement('link');
    link.rel = 'apple-touch-icon'; link.href = '{ICON_URL}';
    window.parent.document.head.appendChild(link);
}}
</script>
""", height=0)

# --- Main UI ---
ch1, ch2 = st.columns([1, 5])
with ch1:
    if os.path.exists(LOCAL_ICON): st.image(LOCAL_ICON, width=54)
    else: st.markdown("### 🏹")
with ch2: st.markdown("<h1 style='margin:0; font-size:1.8rem;'>買付監視くん</h1>", unsafe_allow_html=True)

with st.expander("➕ 銘柄を追加", expanded=False):
    cs1, cs2 = st.columns([3, 1])
    ticker_in = cs1.text_input("コード", placeholder="7203", label_visibility="collapsed").upper()
    if cs2.button("追加", use_container_width=True, type="primary") and ticker_in:
        p, n, d, t, u = fetch_price(ticker_in)
        if p:
            db = load_data()
            if not any(s['ticker'] == t for s in db['stocks']):
                db['stocks'].append({"ticker":t, "name":n, "last_price":p, "unit":u, "odd_lot_target":0.0, "one_lot_target":0.0})
                save_data(db); st.rerun()
            else: st.warning("追加済み")
        else: st.error("取得失敗")

db = load_data()
if not db['stocks']:
    st.info("リストが空です")
else:
    for idx, s in enumerate(db['stocks']):
        unit = s.get("unit", "円")
        p_now = s['last_price']
        t1 = float(s.get('odd_lot_target', 0))
        t2 = float(s.get('one_lot_target', 0))
        
        # Build HTML components separately to avoid parsing errors
        pill1 = f'<div class="pill pill-ok">✅ 到達</div>' if (t1 > 0 and p_now <= t1) else f'<div class="pill pill-wait">監視中</div>' if t1 > 0 else ""
        pill2 = f'<div class="pill pill-ok">✅ 到達</div>' if (t2 > 0 and p_now <= t2) else f'<div class="pill pill-wait">監視中</div>' if t2 > 0 else ""
        
        val1 = f"{t1:.2f}{unit}" if t1 > 0 else "未設定"
        val2 = f"{t2:.2f}{unit}" if t2 > 0 else "未設定"
        
        card_html = f"""
        <div class="stock-card">
            <div class="stock-title">
                {s['name']} <span class="ticker-badge">{s['ticker']}</span>
            </div>
            <div class="price-large">
                {p_now:.2f}<span class="price-unit">{unit}</span>
            </div>
            <div class="target-grid">
                <div class="target-col">
                    <div class="label-tiny">単元未満</div>
                    <div class="val-bold">{val1}</div>
                    {pill1}
                </div>
                <div class="target-col">
                    <div class="label-tiny">単元</div>
                    <div class="val-bold">{val2}</div>
                    {pill2}
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
        
        if st.button(f"⚙️ 設定 ({s['ticker']})", key=f"btn_{s['ticker']}", use_container_width=True):
            st.session_state[f"ed_{s['ticker']}"] = not st.session_state.get(f"ed_{s['ticker']}", False)

        if st.session_state.get(f"ed_{s['ticker']}", False):
            with st.form(f"form_{s['ticker']}"):
                n_name = st.text_input("表示名", value=s['name'])
                n_unit = st.selectbox("通貨", options=["円", "ドル"], index=0 if unit=="円" else 1)
                c1, c2 = st.columns(2)
                v1 = c1.number_input("単元未満目標", value=float(t1), step=0.1)
                v2 = c2.number_input("単元目標", value=float(t2), step=0.1)
                b1, b2 = st.columns(2)
                if b1.form_submit_button("保存"):
                    s['name'], s['unit'], s['odd_lot_target'], s['one_lot_target'] = n_name, n_unit, v1, v2
                    save_data(db); st.session_state[f"ed_{s['ticker']}"] = False; st.rerun()
                if b2.form_submit_button("削除"):
                    db['stocks'].pop(idx); save_data(db); st.rerun()

st.divider()
cf1, cf2 = st.columns([3, 1])
cf1.caption(f"最終更新: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
if cf2.button("🔄 更新", use_container_width=True):
    new_db = load_data()
    for item in new_db['stocks']:
        price, _, _, _, _ = fetch_price(item['ticker'])
        if price: item['last_price'] = price
    save_data(new_db)
    st.session_state.last_refresh = datetime.now(); st.rerun()
