import streamlit as st
import yfinance as yf
import json
import os
import re
from datetime import datetime
from PIL import Image

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data_storage.json")
LOCAL_ICON = os.path.join(BASE_DIR, "assets", "icon.png")
ICON_URL = "https://raw.githubusercontent.com/kudsv255tami-glitch/kaitsuke-kanshikun/main/assets/icon.png"
UPDATE_INTERVAL = 300 

st.set_page_config(page_title="買付監視くん", page_icon=Image.open(LOCAL_ICON) if os.path.exists(LOCAL_ICON) else "🏹", layout="centered")

if "last_refresh" not in st.session_state: st.session_state.last_refresh = datetime.now()

# Japanese Name Mapping
COMMON_JP_NAMES = {
    "7203.T": "トヨタ自動車", "2914.T": "JT", "9432.T": "NTT", "9984.T": "ソフトバンクグループ",
    "6758.T": "ソニーグループ", "8306.T": "三菱UFJフィナンシャルG", "8411.T": "みずほフィナンシャルG",
    "8316.T": "三井住友フィナンシャルG", "7267.T": "本田技研工業", "6954.T": "ファナック",
    "6098.T": "リクルートHD", "4502.T": "武田薬品工業", "7974.T": "任天堂", "9020.T": "JR東日本",
    "9022.T": "JR東海", "9201.T": "日本航空", "9202.T": "ANAホールディングス", "4063.T": "信越化学工業",
    "8031.T": "三井物産", "8058.T": "三菱商事", "8001.T": "伊藤忠商事", "435A.T": "iFreeETF 日本株 配当 ローテーション"
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

def translate_name_aggressive(name):
    translations = {
        "CORPORATION":"", "CORP":"", "LTD":"", "INC":"", "CO":"", 
        "HOLDINGS":"HD", "GROUP":"G", "MOTOR":"自動車", "STEEL":"製鉄", "TOBACCO":"たばこ",
        "JAPAN":"日本", "NIPPON":"日本", "EQUITY":"株", "DIVIDEND":"配当", "ROTATION":"ローテーション", "STRATEGY":"戦略"
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
            p = hist['Close'].iloc[-1]
            info = stock.info
            name = COMMON_JP_NAMES.get(final_ticker)
            if not name:
                raw = info.get('longName') or info.get('shortName') or final_ticker
                name = translate_name_aggressive(raw) if final_ticker.endswith(".T") else raw
            u = "円" if info.get('currency', 'JPY') == "JPY" else "ドル"
            return round(p, 2), name, final_ticker, u
        return None, None, final_ticker, "円"
    except: return None, None, final_ticker, "円"

# --- UI Styling ---
st.markdown(f"""
<style>
    header, footer, #MainMenu {{ visibility: hidden; display: none !important; }}
    [data-testid="stHeader"] {{ height: 0px !important; display: none !important; }}
    [data-testid="stMainBlockContainer"] {{ padding: 0.8rem !important; padding-top: 1rem !important; max-width: 100% !important; }}
    .stApp {{ background-color: #f2f2f7; }}
    [data-testid="stVerticalBlockBorderWrapper"] > div {{ background-color: white; border-radius: 12px; padding: 12px; border: 1px solid #e5e5ea; margin-bottom: 8px; }}
    [data-testid="stMetricValue"] {{ font-size: 2.1rem !important; font-weight: 800 !important; color: #007aff !important; }}
    [data-testid="stMetricLabel"] {{ font-size: 1.05rem !important; font-weight: 700 !important; color: #1c1c1e !important; }}
    .target-grid {{ display: flex; justify-content: space-between; gap: 8px; border-top: 1px solid #f2f2f7; padding-top: 8px; margin-top: 2px; }}
    .target-box {{ flex: 1; }}
    .t-lbl {{ font-size: 0.75rem; color: #8e8e93; font-weight: 600; margin-bottom: 1px; }}
    .t-val {{ font-size: 0.95rem; font-weight: 700; color: #1c1c1e; }}
    .t-status {{ font-size: 0.75rem; font-weight: 800; color: #34c759; margin-top: 2px; }}
    .t-wait {{ font-size: 0.7rem; color: #aeaeb2; margin-top: 2px; }}
    input {{ font-size: 16px !important; }}
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
}}
</script>
""", height=0)

# --- App UI ---
st.markdown(f"<div style='display:flex; align-items:center; gap:8px; margin-bottom:10px;'><img src='{ICON_URL}' width='40'><h1 style='margin:0; font-size:1.5rem;'>買付監視くん</h1></div>", unsafe_allow_html=True)

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

db = load_data()
if not db['stocks']:
    st.info("銘柄を追加してください")
else:
    for idx, s in enumerate(db['stocks']):
        # Sync name with Japanese mapping if available
        if s['ticker'] in COMMON_JP_NAMES:
            s['name'] = COMMON_JP_NAMES[s['ticker']]
            
        unit = s.get("unit", "円")
        pnow = s['last_price']
        t1, t2 = float(s.get('odd_lot_target', 0)), float(s.get('one_lot_target', 0))
        
        with st.container(border=True):
            st.metric(label=f"{s['name']}", value=f"{pnow:,.2f} {unit}")
            st.caption(f"コード: {s['ticker']}")
            
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
            
            if st.button(f"⚙️ 設定/削除 ({s['ticker']})", key=f"btn_{s['ticker']}", use_container_width=True):
                st.session_state[f"ed_{s['ticker']}"] = not st.session_state.get(f"ed_{s['ticker']}", False)
            if st.session_state.get(f"ed_{s['ticker']}", False):
                with st.form(f"form_{s['ticker']}"):
                    nn = st.text_input("表示名", value=s['name'])
                    nu = st.selectbox("通貨", ["円", "ドル"], 0 if unit=="円" else 1)
                    ec1, ec2 = st.columns(2)
                    v1 = ec1.number_input("単元未満目標", value=t1, step=0.1)
                    v2 = ec2.number_input("単元目標", value=t2, step=0.1)
                    if st.form_submit_button("保存"):
                        s['name'], s['unit'], s['odd_lot_target'], s['one_lot_target'] = nn, nu, v1, v2
                        save_data(db); st.session_state[f"ed_{s['ticker']}"] = False; st.rerun()
                    if st.form_submit_button("削除"): db['stocks'].pop(idx); save_data(db); st.rerun()

st.divider()
ff1, ff2 = st.columns([3, 1])
ff1.caption(f"最終更新: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
if ff2.button("🔄 更新", use_container_width=True):
    for item in db['stocks']:
        px, _, _, _ = fetch_price(item['ticker'])
        if px: item['last_price'] = px
    save_data(db); st.session_state.last_refresh = datetime.now(); st.rerun()
