import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import re
from datetime import datetime
from PIL import Image

# --- Constants & Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_storage.json")
LOCAL_ICON = os.path.join(BASE_DIR, "assets", "icon.png")
UPDATE_INTERVAL = 300 

# Common Japanese Stock Names Mapping
COMMON_JP_NAMES = {
    "7203.T": "トヨタ自動車", "2914.T": "JT", "9432.T": "NTT", "9984.T": "ソフトバンクグループ",
    "6758.T": "ソニーグループ", "8306.T": "三菱UFJフィナンシャルG", "8411.T": "みずほフィナンシャルG",
    "8316.T": "三井住友フィナンシャルG", "7267.T": "本田技研工業", "6954.T": "ファナック",
    "6098.T": "リクルートHD", "4502.T": "武田薬品工業", "7974.T": "任天堂", "9020.T": "JR東日本",
    "9022.T": "JR東海", "9201.T": "日本航空", "9202.T": "ANAホールディングス", "4063.T": "信越化学工業",
    "8031.T": "三井物産", "8058.T": "三菱商事", "8001.T": "伊藤忠商事", "435A.T": "iFreeETF 日本株 配当 ローテーション 戦略"
}

# --- Utility Functions ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"stocks": []}

def save_data(data):
    data['stocks'].sort(key=lambda x: x['ticker'])
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def normalize_ticker(ticker):
    t = ticker.strip().upper()
    if t.endswith(".T") or "." in t: return t
    if len(t) == 4: return t + ".T"
    return t

def translate_name_aggressive(name):
    translations = {
        "CORPORATION": "", "CORP": "", "LTD": "", "INC": "", "CO": "", 
        "HOLDINGS": "HD", "GROUP": "G",
        "JAPAN": "日本", "EQUITY": "株", "DIVIDEND": "配当", "ROTATION": "ローテーション", "STRATEGY": "戦略",
        "NIPPON": "日本", "TOYOTA": "トヨタ", "MOTOR": "自動車", "STEEL": "製鉄", "TOBACCO": "たばこ",
        "AIRLINES": "航空", "RAILWAY": "鉄道", "ELECTRIC": "電気", "CHEMICAL": "化学"
    }
    res = name.upper()
    for eng, jp in translations.items():
        res = re.sub(rf'\b{eng}\b', jp, res)
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
            currency_code = info.get('currency', 'JPY')
            unit = "円" if currency_code == "JPY" else "ドル"
            name = COMMON_JP_NAMES.get(final_ticker)
            if not name:
                if final_ticker.endswith(".T") and any(c.isalpha() for c in raw_name):
                    name = translate_name_aggressive(raw_name)
                else:
                    name = raw_name
            dividend = info.get('dividendYield', 0) * price if info.get('dividendYield') else info.get('trailingAnnualDividendRate', 0)
            return round(price, 2), name, dividend, final_ticker, unit
        return None, None, 0, final_ticker, "円"
    except Exception:
        return None, None, 0, final_ticker, "円"

# --- JS & CSS Styling ---
def apply_ios_styling():
    # Hide Streamlit junk and adjust for mobile
    st.markdown("""
    <style>
        /* Hide Header, Footer, Menu */
        header, footer, #MainMenu, .stAppDeployButton {
            visibility: hidden;
            display: none !important;
        }
        [data-testid="stHeader"] { height: 0px !important; display: none !important; }
        
        /* Eliminate top/bottom blank space */
        [data-testid="stMainBlockContainer"] {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
        
        /* Prevent iOS zoom on input */
        input, select, textarea, button { font-size: 16px !important; }
        
        /* Card Style for Stocks */
        .stock-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #f0f0f0;
        }
        .stock-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
        .stock-title { font-size: 1.2rem; font-weight: 800; color: #1a1a1a; display: flex; align-items: center; gap: 6px; }
        .ticker-badge { color: #8e8e93; font-size: 0.8rem; font-weight: 400; }
        .price-display { font-size: 2rem; font-weight: 900; color: #007aff; text-align: right; line-height: 1; margin: 10px 0; }
        .price-unit { font-size: 0.9rem; color: #444; margin-left: 4px; font-weight: 600; }
        .target-row { display: flex; justify-content: space-between; border-top: 1px solid #f5f5f5; padding-top: 10px; margin-top: 5px; }
        .target-item { text-align: left; }
        .target-label { font-size: 0.75rem; color: #8e8e93; margin-bottom: 2px; }
        .target-price { font-size: 0.95rem; font-weight: 700; color: #3a3a3c; }
        .status-pill { font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 20px; text-transform: uppercase; }
        .pill-reached { background-color: #e1f5fe; color: #0288d1; border: 1px solid #b3e5fc; }
        .pill-pending { background-color: #f2f2f7; color: #8e8e93; }
        
        /* App Background */
        .stApp { background-color: #f2f2f7; }
    </style>
    """, unsafe_allow_html=True)

    # JS for automatic triggers
    js = f"""
    <script>
    if (!window.kanshikunInjected) {{
        window.kanshikunInjected = true;
        // Auto-refresh timer
        setInterval(function() {{
            const btn = window.parent.document.querySelector('button[kind="secondary"]');
            if (btn && btn.innerText.includes("一括更新")) btn.click();
        }}, {UPDATE_INTERVAL * 1000});
        
        window.notificationLib = {{
            requestPermission: function() {{ if (Notification) Notification.requestPermission(); }},
            send: function(title, body) {{ if (Notification && Notification.permission === "granted") new Notification(title, {{ body: body }}); }}
        }};
    }}
    </script>
    """
    st.components.v1.html(js, height=0)

def trigger_notification(title, body):
    js = f"<script>if(window.notificationLib) window.notificationLib.send('{title}', '{body}');</script>"
    st.components.v1.html(js, height=0)

# --- App Execution ---
apply_ios_styling()
app_icon = Image.open(LOCAL_ICON) if os.path.exists(LOCAL_ICON) else "🏹"
st.set_page_config(page_title="買付監視くん", page_icon=app_icon, layout="centered")

# Custom App Header
col_h1, col_h2 = st.columns([1, 4])
with col_h1:
    if os.path.exists(LOCAL_ICON): st.image(LOCAL_ICON, width=54)
    else: st.markdown("### 🏹")
with col_h2:
    st.markdown("<h1 style='margin:0; padding:0; font-size:1.8rem;'>買付監視くん</h1>", unsafe_allow_html=True)

# Add Stock - Minimalist
with st.expander("➕ 銘柄を追加", expanded=False):
    c_s1, c_s2 = st.columns([3, 1])
    search_ticker = c_s1.text_input("証券コード", placeholder="7203, AAPL", label_visibility="collapsed").upper()
    if c_s2.button("追加", use_container_width=True, type="primary") and search_ticker:
        with st.spinner("取得中..."):
            price, name, div, final_ticker, unit = fetch_price(search_ticker)
            if price:
                data = load_data()
                if not any(s['ticker'] == final_ticker for s in data['stocks']):
                    data['stocks'].append({"ticker": final_ticker, "name": name, "last_price": price, "last_div": div, "unit": unit, "odd_lot_target": 0.0, "one_lot_target": 0.0})
                    save_data(data)
                    st.rerun()
                else: st.warning("追加済みです。")
            else: st.error("不明なコード")

# Watchlist
data = load_data()
data['stocks'].sort(key=lambda x: x['ticker'])

if not data['stocks']:
    st.info("リストが空です。銘柄を追加してください。")
else:
    pending_alerts = []
    for idx, stock in enumerate(data['stocks']):
        # Using a card containers approach
        price_unit = stock.get("unit", "円")
        
        # Check targets
        odd_reached = stock.get('odd_lot_target', 0) > 0 and stock['last_price'] <= stock['odd_lot_target']
        one_reached = stock.get('one_lot_target', 0) > 0 and stock['last_price'] <= stock['one_lot_target']
        
        st.markdown(f"""
        <div class="stock-card">
            <div class="stock-header">
                <div class="stock-title">{stock['name']} <span class="ticker-badge">{stock['ticker']}</span></div>
            </div>
            <div class="price-display">
                {stock['last_price']:.2f}<span class="price-unit">{price_unit}</span>
            </div>
            <div class="target-row">
                <div class="target-item">
                    <div class="target-label">単元未満</div>
                    <div class="target-price">{f"{stock['odd_lot_target']:.2f}{price_unit}" if stock['odd_lot_target'] > 0 else "未設定"}</div>
                    {"<span class='status-pill pill-reached'>✅ 到達</span>" if odd_reached else "<span class='status-pill pill-pending'>監視中</span>" if stock['odd_lot_target'] > 0 else ""}
                </div>
                <div class="target-item">
                    <div class="target-label">単元</div>
                    <div class="target-price">{f"{stock['one_lot_target']:.2f}{price_unit}" if stock['one_lot_target'] > 0 else "未設定"}</div>
                    {"<span class='status-pill pill-reached'>✅ 到達</span>" if one_reached else "<span class='status-pill pill-pending'>監視中</span>" if stock['one_lot_target'] > 0 else ""}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Action Button (Minimal)
        if st.button(f"⚙️ 設定 ({stock['ticker']})", key=f"set_{stock['ticker']}", type="secondary", use_container_width=True):
            st.session_state[f"edit_{stock['ticker']}"] = not st.session_state.get(f"edit_{stock['ticker']}", False)

        if st.session_state.get(f"edit_{stock['ticker']}", False):
            with st.form(f"f_{stock['ticker']}"):
                new_name = st.text_input("表示名", value=stock['name'])
                new_unit = st.selectbox("通貨単位", options=["円", "ドル"], index=0 if price_unit == "円" else 1)
                ce1, ce2 = st.columns(2)
                new_odd = ce1.number_input(f"単元未満ライン", value=float(stock.get('odd_lot_target', 0)), step=0.1)
                new_one = ce2.number_input(f"単元ライン", value=float(stock.get('one_lot_target', 0)), step=0.1)
                b1, b2 = st.columns(2)
                if b1.form_submit_button("保存"):
                    stock['name'], stock['unit'], stock['odd_lot_target'], stock['one_lot_target'] = new_name, new_unit, new_odd, new_one
                    save_data(data)
                    st.session_state[f"edit_{stock['ticker']}"] = False
                    st.rerun()
                if b2.form_submit_button("削除"):
                    data['stocks'].pop(idx)
                    save_data(data)
                    st.session_state[f"edit_{stock['ticker']}"] = False
                    st.rerun()

        # Notifications logic
        if odd_reached:
            aid = f"{stock['ticker']}_odd_{stock['odd_lot_target']}"
            if aid not in st.session_state.notified_targets:
                pending_alerts.append((stock['name'], "単元未満", f"{stock['odd_lot_target']:.2f}{price_unit}"))
                st.session_state.notified_targets.add(aid)
        if one_reached:
            aid = f"{stock['ticker']}_one_{stock['one_lot_target']}"
            if aid not in st.session_state.notified_targets:
                pending_alerts.append((stock['name'], "単元", f"{stock['one_lot_target']:.2f}{price_unit}"))
                st.session_state.notified_targets.add(aid)

    for n, l, p in pending_alerts: trigger_notification(f"【{l}】到達", f"{n} が {p} に到達しました！")

# Footer Area
st.markdown("<br><br>", unsafe_allow_html=True)
c_f1, c_f2 = st.columns([3, 1])
c_f1.caption(f"最終更新: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
if c_f2.button("🔄 更新", use_container_width=True):
    with st.spinner():
        u_data = load_data()
        for s in u_data['stocks']:
            p, _, d, _, u = fetch_price(s['ticker'])
            if p: s['last_price'], s['last_div'] = p, d
        save_data(u_data)
        st.session_state.last_refresh = datetime.now()
    st.rerun()

if st.sidebar.button("🔔 通知許可"):
    st.components.v1.html("<script>window.notificationLib.requestPermission()</script>", height=0)
