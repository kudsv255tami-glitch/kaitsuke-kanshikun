import streamlit as st
import yfinance as yf
import json
import os
import re
from datetime import datetime
from PIL import Image

# --- Constants & Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_storage.json")
LOCAL_ICON = os.path.join(BASE_DIR, "assets", "icon.png")
ICON_URL = "https://raw.githubusercontent.com/kudsv255tami-glitch/kaitsuke-kanshikun/main/assets/icon.png"
UPDATE_INTERVAL = 300 

# --- MUST BE FIRST ---
st.set_page_config(page_title="買付監視くん", page_icon=Image.open(LOCAL_ICON) if os.path.exists(LOCAL_ICON) else "🏹", layout="centered")

# Session State
if "notified_targets" not in st.session_state: st.session_state.notified_targets = set()
if "last_refresh" not in st.session_state: st.session_state.last_refresh = datetime.now()

# Common Japanese Stock Names
COMMON_JP_NAMES = {
    "7203.T": "トヨタ自動車", "2914.T": "JT", "9432.T": "NTT", "9984.T": "ソフトバンクグループ",
    "6758.T": "ソニーグループ", "8306.T": "三菱UFJフィナンシャルG", "8411.T": "みずほフィナンシャルG",
    "8316.T": "三井住友フィナンシャルG", "7267.T": "本田技研工業", "6954.T": "ファナック",
    "6098.T": "リクルートHD", "4502.T": "武田薬品工業", "7974.T": "任天堂", "9020.T": "JR東日本",
    "9022.T": "JR東海", "9201.T": "日本航空", "9202.T": "ANAホールディングス", "4063.T": "信越化学工業",
    "8031.T": "三井物産", "8058.T": "三菱商事", "8001.T": "伊藤忠商事", "435A.T": "iFreeETF 日本株 配当 ローテーション 戦略"
}

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
            name = COMMON_JP_NAMES.get(final_ticker)
            if not name:
                raw = info.get('longName') or info.get('shortName') or final_ticker
                name = re.sub(r'\b(CORP|INC|LTD|HOLDINGS|GROUP|JAPAN)\b', '', raw.upper()).strip() if final_ticker.endswith(".T") else raw
            u = "円" if info.get('currency', 'JPY') == "JPY" else "ドル"
            d = info.get('dividendYield', 0) * p if info.get('dividendYield') else info.get('trailingAnnualDividendRate', 0)
            return round(p, 2), name, d, final_ticker, u
        return None, None, 0, final_ticker, "円"
    except: return None, None, 0, final_ticker, "円"

# --- UI Styling (Native App Look) ---
st.markdown(f"""
<style>
    header, footer, #MainMenu {{ visibility: hidden; display: none !important; }}
    [data-testid="stHeader"] {{ height: 0px !important; display: none !important; }}
    [data-testid="stMainBlockContainer"] {{ padding: 1.2rem !important; padding-top: 1rem !important; max-width: 100% !important; }}
    .stApp {{ background-color: #f2f2f7; }}
    div[data-testid="stExpander"] {{ background-color: white; border-radius: 12px; border: 1px solid #e5e5ea; }}
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {{ background-color: white; border-radius: 16px; padding: 10px; border: 1px solid #e5e5ea; }}
    h1 {{ font-size: 1.6rem !important; margin: 0 !important; }}
    .price-text {{ font-size: 2.2rem; font-weight: 900; color: #007aff; text-align: right; margin: 5px 0; line-height: 1; }}
    .price-unit {{ font-size: 1rem; color: #3a3a3c; margin-left: 5px; }}
    .label-text {{ font-size: 0.8rem; color: #8e8e93; font-weight: 600; }}
    .val-text {{ font-size: 1rem; font-weight: 800; color: #1c1c1e; }}
    .pill {{ font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

st.components.v1.html(f"""
<script>
if (!window.kInjected) {{
    window.kInjected = true;
    setInterval(() => {{
        const btn = window.parent.document.querySelector('button[kind="secondary"]');
        if (btn && btn.innerText.includes("更新")) btn.click();
    }}, {UPDATE_INTERVAL * 1000});
    const link = window.parent.document.createElement('link'); link.rel = 'apple-touch-icon'; link.href = '{ICON_URL}';
    window.parent.document.head.appendChild(link);
}}
</script>
""", height=0)

# --- Header ---
c1, c2 = st.columns([1, 4])
with c1:
    if os.path.exists(LOCAL_ICON): st.image(LOCAL_ICON, width=54)
    else: st.markdown("### 🏹")
with c2: st.markdown("<h1 style='padding-top:10px;'>買付監視くん</h1>", unsafe_allow_html=True)

# --- Add ---
with st.expander("➕ 銘柄を追加"):
    cs1, cs2 = st.columns([3, 1])
    tin = cs1.text_input("コード", placeholder="例: 7203", label_visibility="collapsed").upper()
    if cs2.button("追加", use_container_width=True, type="primary") and tin:
        p, n, d, t, u = fetch_price(tin)
        if p:
            db = load_data()
            if not any(s['ticker'] == t for s in db['stocks']):
                db['stocks'].append({"ticker":t, "name":n, "last_price":p, "unit":u, "odd_lot_target":0.0, "one_lot_target":0.0})
                save_data(db); st.rerun()
            else: st.warning("追加済み")
        else: st.error("取得失敗")

# --- List ---
db = load_data()
if not db['stocks']:
    st.info("銘柄を追加してください")
else:
    for idx, s in enumerate(db['stocks']):
        unit = s.get("unit", "円")
        pnow = s['last_price']
        t1 = float(s.get('odd_lot_target', 0))
        t2 = float(s.get('one_lot_target', 0))
        
        # --- Native Container Card ---
        with st.container(border=True):
            # Row 1: Title
            st.markdown(f"**{s['name']}** <small style='color:#8e8e93'>{s['ticker']}</small>", unsafe_allow_html=True)
            
            # Row 2: Price
            st.markdown(f'<div class="price-text">{pnow:.2f}<span class="price-unit">{unit}</span></div>', unsafe_allow_html=True)
            
            # Row 3: Targets
            tc1, tc2 = st.columns(2)
            # Target 1
            tc1.markdown(f'<div class="label-text">単元未満</div>', unsafe_allow_html=True)
            tc1.markdown(f'<div class="val-text">{t1:.2f}{unit if t1 > 0 else ""}</div>' if t1 > 0 else '<div class="val-text">未設定</div>', unsafe_allow_html=True)
            if t1 > 0:
                if pnow <= t1: tc1.success("✅ 到達", icon="🎯")
                else: tc1.markdown('<span class="pill" style="background-color:#f2f2f7; color:#8e8e93;">監視中</span>', unsafe_allow_html=True)
                
            # Target 2
            tc2.markdown(f'<div class="label-text">単元</div>', unsafe_allow_html=True)
            tc2.markdown(f'<div class="val-text">{t2:.2f}{unit if t2 > 0 else ""}</div>' if t2 > 0 else '<div class="val-text">未設定</div>', unsafe_allow_html=True)
            if t2 > 0:
                if pnow <= t2: tc2.success("✅ 到達", icon="🎯")
                else: tc2.markdown('<span class="pill" style="background-color:#f2f2f7; color:#8e8e93;">監視中</span>', unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            
            # Settings Button (Integrated at bottom of card)
            if st.button(f"⚙️ 設定 ({s['ticker']})", key=f"btn_{s['ticker']}", use_container_width=True):
                st.session_state[f"ed_{s['ticker']}"] = not st.session_state.get(f"ed_{s['ticker']}", False)
            
            if st.session_state.get(f"ed_{s['ticker']}", False):
                with st.form(f"form_{s['ticker']}"):
                    nn = st.text_input("表示名", value=s['name'])
                    nu = st.selectbox("通貨", options=["円", "ドル"], index=0 if unit=="円" else 1)
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
ff1, ff2 = st.columns([3, 1])
ff1.caption(f"最終更新: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
if ff2.button("🔄 更新", use_container_width=True):
    ndb = load_data()
    for item in ndb['stocks']:
        px, _, _, _, _ = fetch_price(item['ticker'])
        if px: item['last_price'] = px
    save_data(ndb)
    st.session_state.last_refresh = datetime.now(); st.rerun()
