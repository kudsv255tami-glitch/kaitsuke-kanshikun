import streamlit as st
import yfinance as yf
import pandas as pd
import json
import time
import os
import re
from datetime import datetime
from PIL import Image

# --- Constants & Configuration ---
# Use relative paths for deployment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_storage.json")
ICON_FILE = os.path.join(BASE_DIR, "assets", "icon.png")
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

# --- JS Helpers ---
def inject_js():
    js = f"""
    <script>
    if (!window.notificationLib) {{
        window.notificationLib = {{
            requestPermission: function() {{
                if (!("Notification" in window)) return;
                Notification.requestPermission();
            }},
            send: function(title, body) {{
                if (window.Notification && Notification.permission === "granted") {{
                    new Notification(title, {{ body: body }});
                }}
            }}
        }};
        setInterval(function() {{
            const btn = window.parent.document.querySelector('button[kind="secondary"]');
            if (btn && btn.innerText.includes("一括更新")) btn.click();
        }}, {UPDATE_INTERVAL * 1000});
    }}
    </script>
    """
    st.components.v1.html(js, height=0)

def trigger_notification(title, body):
    js = f"<script>if(window.notificationLib) window.notificationLib.send('{title}', '{body}');</script>"
    st.components.v1.html(js, height=0)

# --- Streamlit UI Setup ---
app_icon = Image.open(ICON_FILE) if os.path.exists(ICON_FILE) else "🏹"
st.set_page_config(page_title="買付監視くん", page_icon=app_icon, layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #ffffff; }
    .search-area { background-color: #f8f9fa; padding: 25px; border-radius: 10px; margin-bottom: 30px; }
    .stock-row { padding: 15px 0; border-bottom: 2px solid #f1f3f5; }
    .stock-name { font-size: 1.5rem !important; font-weight: 800; color: #111; }
    .metric-val { font-size: 2.2rem; font-weight: 900; color: #0066cc; text-align: right; }
    .unit-label { font-size:1rem; color:#444; margin-left:8px; }
    .status-tag { padding: 4px 10px; border-radius: 5px; font-size: 0.8rem; font-weight: bold; }
    .status-reached { background-color: #e6fced; color: #1a7f37; }
    .status-pending { background-color: #f1f3f5; color: #5f6368; }
</style>
""", unsafe_allow_html=True)

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if "notified_targets" not in st.session_state:
    st.session_state.notified_targets = set()

# Header with App Icon
c_h1, c_h2 = st.columns([1, 5])
with c_h1:
    if os.path.exists(ICON_FILE):
        st.image(ICON_FILE, width=60)
    else:
        st.title("🏹")
with c_h2:
    st.title("買付監視くん")

# --- Search & Add ---
with st.container():
    st.markdown('<div class="search-area">', unsafe_allow_html=True)
    st.write("**🔍 銘柄を追加**")
    c_s1, c_s2 = st.columns([4, 1])
    search_ticker = c_s1.text_input("証券コード", label_visibility="collapsed", placeholder="例: 7203, AAPL", key="search_box").upper()
    msg_container = st.empty()
    if c_s2.button("追加", use_container_width=True, type="primary") and search_ticker:
        with st.spinner("情報を取得中..."):
            price, name, div, final_ticker, unit = fetch_price(search_ticker)
            if price:
                data = load_data()
                if not any(s['ticker'] == final_ticker for s in data['stocks']):
                    data['stocks'].append({"ticker": final_ticker, "name": name, "last_price": price, "last_div": div, "unit": unit, "odd_lot_target": 0.0, "one_lot_target": 0.0})
                    save_data(data)
                    st.rerun()
                else: msg_container.warning("追加済みです。")
            else: msg_container.error("見つかりませんでした。")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Watchlist ---
inject_js()
data = load_data()
data['stocks'].sort(key=lambda x: x['ticker'])

if not data['stocks']:
    st.info("監視リストが空です。")
else:
    st.markdown(f"### 👀 監視リスト（{len(data['stocks'])}銘柄）")
    pending_alerts = []
    for idx, stock in enumerate(data['stocks']):
        st.markdown(f'<div class="stock-row">', unsafe_allow_html=True)
        col_main, col_btn = st.columns([3, 1])
        with col_main:
            st.markdown(f'<div class="stock-name">{stock["name"]} <small style="color:#888">{stock["ticker"]}</small></div>', unsafe_allow_html=True)
        with col_btn:
            edit_key = f"edit_{stock['ticker']}"
            if st.button("設定", key=f"btn_{stock['ticker']}", use_container_width=True):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
        
        price_unit = stock.get("unit", "円")
        st.columns([1, 1])[1].markdown(f'<div class="metric-val">{stock["last_price"]:.2f}<span class="unit-label">{price_unit}</span></div>', unsafe_allow_html=True)

        if st.session_state.get(edit_key, False):
            with st.container():
                st.markdown('<div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border:1px solid #ddd; margin-top:10px;">', unsafe_allow_html=True)
                with st.form(f"f_{stock['ticker']}"):
                    new_name = st.text_input("表示名", value=stock['name'])
                    new_unit = st.selectbox("通貨単位", options=["円", "ドル"], index=0 if price_unit == "円" else 1)
                    ce1, ce2 = st.columns(2)
                    new_odd = ce1.number_input(f"単元未満ライン ({new_unit})", value=float(stock.get('odd_lot_target', 0)), step=0.1)
                    new_one = ce2.number_input(f"単元ライン ({new_unit})", value=float(stock.get('one_lot_target', 0)), step=0.1)
                    if st.form_submit_button("保存"):
                        stock['name'], stock['unit'], stock['odd_lot_target'], stock['one_lot_target'] = new_name, new_unit, new_odd, new_one
                        save_data(data)
                        st.session_state[edit_key] = False
                        st.rerun()
                    if st.form_submit_button("削除"):
                        data['stocks'].pop(idx)
                        save_data(data)
                        st.session_state[edit_key] = False
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        t_col1, t_col2 = st.columns(2)
        for i, (label, val) in enumerate([("単元未満", stock.get('odd_lot_target', 0)), ("単元", stock.get('one_lot_target', 0))]):
            area = t_col1 if i == 0 else t_col2
            if val > 0:
                reached = stock['last_price'] <= val
                t_cls, t_txt = ("status-reached", "✅ 到達") if reached else ("status-pending", "監視中")
                area.markdown(f'{label}: <b>{val:.2f}{price_unit}</b> <span class="status-tag {t_cls}">{t_txt}</span>', unsafe_allow_html=True)
                if reached:
                    aid = f"{stock['ticker']}_{label}_{val}"
                    if aid not in st.session_state.notified_targets:
                        pending_alerts.append((stock['name'], label, f"{val:.2f}{price_unit}"))
                        st.session_state.notified_targets.add(aid)
            else: area.markdown(f'<span style="color:#bbb;">{label}: 未設定</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    for n, l, p in pending_alerts: trigger_notification(f"【{l}】到達", f"{n} が {p} に到達しました！")

st.divider()
c_f1, c_f2 = st.columns([3, 1])
c_f1.caption(f"最終更新: {st.session_state.last_refresh.strftime('%H:%M:%S')} (自動更新中)")
if c_f2.button("🔄 一括更新", use_container_width=True):
    with st.spinner("株価を更新中..."):
        u_data = load_data()
        for s in u_data['stocks']:
            p, _, d, _, u = fetch_price(s['ticker'])
            if p: s['last_price'], s['last_div'] = p, d
        save_data(u_data)
        st.session_state.last_refresh = datetime.now()
    st.rerun()

if st.sidebar.button("🔔 通知許可"):
    st.components.v1.html("<script>window.notificationLib.requestPermission()</script>", height=0)
