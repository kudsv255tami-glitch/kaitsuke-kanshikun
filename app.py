import streamlit as st
import yfinance as yf
import json
import os
import re
from datetime import datetime
from PIL import Image

# --- Constants ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_storage.json")
LOCAL_ICON = os.path.join(BASE_DIR, "assets", "icon.png")
ICON_URL = "https://raw.githubusercontent.com/kudsv255tami-glitch/kaitsuke-kanshikun/main/assets/icon.png"
UPDATE_INTERVAL = 300 

# --- Streamlit Setup ---
st.set_page_config(page_title="買付監視くん", page_icon=Image.open(LOCAL_ICON) if os.path.exists(LOCAL_ICON) else "🏹", layout="centered")

# Session State Initialization
if "notified_targets" not in st.session_state: st.session_state.notified_targets = set()
if "last_refresh" not in st.session_state: st.session_state.last_refresh = datetime.now()

# Common Japanese Stock Names
COMMON_JP_NAMES = {
    "7203.T": "トヨタ自動車", "2914.T": "JT", "9432.T": "NTT", "9984.T": "ソフトバンクグループ",
    "6758.T": "ソニーグループ", "8306.T": "三菱UFJフィナンシャルG", "8411.T": "みずほフィナンシャルG",
    "8316.T": "三井住友フィナンシャルG", "7267.T": "本田技研工業", "6954.T": "ファナック",
    "6098.T": "リクルートHD", "4502.T": "武田薬品工業", "7974.T": "任天堂", "435A.T": "iFreeETF 日本株 配当 ローテーション"
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
            return round(p, 2), name, final_ticker, u
        return None, None, final_ticker, "円"
    except: return None, None, final_ticker, "円"

# --- CSS & JS ---
st.markdown(f"""
<style>
    header, footer, #MainMenu {{ visibility: hidden; display: none !important; }}
    [data-testid="stHeader"] {{ height: 0px !important; display: none !important; }}
    [data-testid="stMainBlockContainer"] {{ padding: 1rem !important; padding-top: 1rem !important; max-width: 100% !important; }}
    .stApp {{ background-color: #f2f2f7; }}
    [data-testid="stExpander"] {{ background-color: white; border-radius: 12px; border: 1px solid #e5e5ea; }}
    [data-testid="stVerticalBlockBorderWrapper"] > div {{ background-color: white; border-radius: 16px; padding: 12px; border: 1px solid #e5e5ea; margin-bottom: 10px; }}
    .price-text {{ font-size: 2.3rem; font-weight: 900; color: #007aff; text-align: right; margin: 4px 0; line-height: 1; }}
    .p-unit {{ font-size: 1rem; color: #3a3a3c; margin-left: 5px; }}
    .lbl {{ font-size: 0.8rem; color: #8e8e93; font-weight: 600; }}
    .val {{ font-size: 1.1rem; font-weight: 800; color: #1c1c1e; }}
</style>
""", unsafe_allow_html=True)

st.components.v1.html(f"""
<script>
if (!window.kInjected) {{
    window.kInjected = true;
    setInterval(() => {{
        const b = window.parent.document.querySelector('button[kind="secondary"]');
        if (b && b.innerText.includes("更新")) b.click();
    }}, {UPDATE_INTERVAL * 1000});
    const link = window.parent.document.createElement('link'); link.rel = 'apple-touch-icon'; link.href = '{ICON_URL}';
    window.parent.document.head.appendChild(link);
    window.notif = {{
        ask: () => {{ Notification.requestPermission().then(p => {{ if(p==='granted') alert('通知が許可されました！'); }}); }},
        send: (t, b) => {{ if(Notification.permission === 'granted') new Notification(t, {{body: b, icon: '{ICON_URL}'}}); }}
    }};
}}
</script>
""", height=0)

def trigger_notification(title, body):
    st.components.v1.html(f"<script>window.notif.send('{title}', '{body}');</script>", height=0)

# --- Header ---
h1, h2 = st.columns([1, 4])
with h1:
    if os.path.exists(LOCAL_ICON): st.image(LOCAL_ICON, width=54)
    else: st.markdown("### 🏹")
with h2: st.markdown("<h1 style='padding-top:10px;'>買付監視くん</h1>", unsafe_allow_html=True)

# --- Notification Config ---
c_notif, c_test = st.columns(2)
with c_notif:
    if st.button("🔔 スマホ通知を有効にする", use_container_width=True):
        st.components.v1.html("<script>window.notif.ask();</script>", height=0)
with c_test:
    if st.button("🧪 テスト通知を送る", use_container_width=True):
        trigger_notification("テスト通知", "監視くんが正常に動作しています！")

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

# --- List ---
db = load_data()
if not db['stocks']:
    st.info("銘柄を追加してください")
else:
    pending_alerts = []
    for idx, s in enumerate(db['stocks']):
        unit = s.get("unit", "円")
        pnow = s['last_price']
        t1, t2 = float(s.get('odd_lot_target', 0)), float(s.get('one_lot_target', 0))
        
        with st.container(border=True):
            st.markdown(f"**{s['name']}** <small style='color:#8e8e93'>{s['ticker']}</small>", unsafe_allow_html=True)
            st.markdown(f'<div class="price-text">{pnow:.2f}<span class="p-unit">{unit}</span></div>', unsafe_allow_html=True)
            
            tc1, tc2 = st.columns(2)
            for i, (label, val, reached) in enumerate([("単元未満", t1, t1 > 0 and pnow <= t1), ("単元", t2, t2 > 0 and pnow <= t2)]):
                col = tc1 if i == 0 else tc2
                col.markdown(f'<div class="lbl">{label}</div>', unsafe_allow_html=True)
                col.markdown(f'<div class="val">{val:.2f}{unit if val > 0 else ""}</div>' if val > 0 else '<div class="val">未設定</div>', unsafe_allow_html=True)
                if val > 0:
                    if reached:
                        col.success("✅ 到達", icon="🎯")
                        aid = f"{s['ticker']}_{label}_{val}"
                        if aid not in st.session_state.notified_targets:
                            pending_alerts.append((s['name'], label, f"{val:.2f}{unit}"))
                            st.session_state.notified_targets.add(aid)
                    else: col.markdown('<small style="color:#8e8e93">● 監視中</small>', unsafe_allow_html=True)
            
            # Integrated Settings
            if st.button(f"⚙️ 設定 ({s['ticker']})", key=f"btn_{s['ticker']}", use_container_width=True):
                st.session_state[f"ed_{s['ticker']}"] = not st.session_state.get(f"ed_{s['ticker']}", False)
            if st.session_state.get(f"ed_{s['ticker']}", False):
                with st.form(f"form_{s['ticker']}"):
                    nn, nu = st.text_input("表示名", value=s['name']), st.selectbox("通貨", ["円", "ドル"], 0 if unit=="円" else 1)
                    ec1, ec2 = st.columns(2)
                    v1, v2 = ec1.number_input("単元未満目標", value=t1, step=0.1), ec2.number_input("単元目標", value=t2, step=0.1)
                    eb1, eb2 = st.columns(2)
                    if eb1.form_submit_button("保存"):
                        s['name'], s['unit'], s['odd_lot_target'], s['one_lot_target'] = nn, nu, v1, v2
                        save_data(db); st.session_state[f"ed_{s['ticker']}"] = False; st.rerun()
                    if eb2.form_submit_button("削除"): db['stocks'].pop(idx); save_data(db); st.rerun()

    for n, l, p in pending_alerts: trigger_notification(f"【{l}】到達", f"{n} が {p} に到達しました！")

# --- Footer ---
st.divider()
ff1, ff2 = st.columns([3, 1])
ff1.caption(f"最終更新: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
if ff2.button("🔄 更新", use_container_width=True):
    ndb = load_data()
    for item in ndb['stocks']:
        px, _, _, _ = fetch_price(item['ticker'])
        if px: item['last_price'] = px
    save_data(ndb); st.session_state.last_refresh = datetime.now(); st.rerun()
