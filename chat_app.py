import streamlit as st
import requests
import json
import re
import os
from dotenv import load_dotenv
import base64
import pandas as pd

st.set_page_config(page_title="BDC AI Assistant", layout="centered", initial_sidebar_state="collapsed")
# Load from .env file (local development only)
load_dotenv()

# For Streamlit Cloud, use st.secrets instead
try:
    # Try Streamlit secrets first (production)
    import streamlit as st
    DATASPHERE_CLIENT_ID = st.secrets.get("DATASPHERE_CLIENT_ID") or os.getenv("DATASPHERE_CLIENT_ID")
    DATASPHERE_CLIENT_SECRET = st.secrets.get("DATASPHERE_CLIENT_SECRET") or os.getenv("DATASPHERE_CLIENT_SECRET")
    DATASPHERE_TENANT_URL = st.secrets.get("DATASPHERE_TENANT_URL") or os.getenv("DATASPHERE_TENANT_URL", "https://bpt-bdc-dataspherev2.eu10.hcs.cloud.sap")
    TOKEN_URL = "https://bpt-bdc-dataspherev2.authentication.eu10.hana.ondemand.com/oauth/token"
    ODATA_URL = "https://bpt-bdc-dataspherev2.eu10.hcs.cloud.sap/api/v1/datasphere/consumption/relational/EXP_DISK_STORE/GL_Cashflow_monthly/GL_Cashflow_monthly"

    AICORE_AUTH_URL = st.secrets.get("AICORE_AUTH_URL") or os.getenv("AICORE_AUTH_URL")
    AICORE_CLIENT_ID = st.secrets.get("AICORE_CLIENT_ID") or os.getenv("AICORE_CLIENT_ID")
    AICORE_CLIENT_SECRET = st.secrets.get("AICORE_CLIENT_SECRET") or os.getenv("AICORE_CLIENT_SECRET")
    AICORE_BASE_URL = st.secrets.get("AICORE_BASE_URL") or os.getenv("AICORE_BASE_URL")
    AICORE_RESOURCE_GROUP = st.secrets.get("AICORE_RESOURCE_GROUP") or os.getenv("AICORE_RESOURCE_GROUP", "default")
except Exception as e:
    # Fallback to environment variables only
    DATASPHERE_CLIENT_ID = os.getenv("DATASPHERE_CLIENT_ID")
    DATASPHERE_CLIENT_SECRET = os.getenv("DATASPHERE_CLIENT_SECRET")
    DATASPHERE_TENANT_URL = os.getenv("DATASPHERE_TENANT_URL", "https://bpt-bdc-dataspherev2.eu10.hcs.cloud.sap")
    TOKEN_URL = "https://bpt-bdc-dataspherev2.authentication.eu10.hana.ondemand.com/oauth/token"
    ODATA_URL = "https://bpt-bdc-dataspherev2.eu10.hcs.cloud.sap/api/v1/datasphere/consumption/relational/EXP_DISK_STORE/GL_Cashflow_monthly/GL_Cashflow_monthly"
    
    AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL")
    AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID")
    AICORE_CLIENT_SECRET = os.getenv("AICORE_CLIENT_SECRET")
    AICORE_BASE_URL = os.getenv("AICORE_BASE_URL")
    AICORE_RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP", "default")

# ════════════════════════════════════════════════════════════════
# MAP DATASPHERE CREDENTIALS TO CLIENT VARS (FOR get_token() FUNCTION)
# ════════════════════════════════════════════════════════════════
CLIENT_ID = DATASPHERE_CLIENT_ID
CLIENT_SECRET = DATASPHERE_CLIENT_SECRET
    
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_B64 = None
for name in ["Logo.png", "logo.png"]:
    p = os.path.join(SCRIPT_DIR, name)
    if os.path.exists(p):
        with open(p, "rb") as f:
            LOGO_B64 = base64.b64encode(f.read()).decode()
        break

defaults = {
    "messages": [], "tokens": 0, "model": "gpt-4o-mini", "models": [],
    "all_data": None, "dark": False, "chat_history": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

dark = st.session_state.dark
if dark:
    BG="#1e1e2e"; CARD="#2a2a3c"; BORDER="#3a3a4c"; TEXT="#cdd6f4"; MUTED="#6c7086"
    USER_BG="#313244"; ASST_BG="#1e3a2a"; ACCENT="#89b4fa"; HEADER_BG="#181825"
else:
    BG="#ffffff"; CARD="#f8f9fa"; BORDER="#e1e4e8"; TEXT="#24292f"; MUTED="#656d76"
    USER_BG="#e8f0fe"; ASST_BG="#e6f4ea"; ACCENT="#0969da"; HEADER_BG="#1a1a2e"

logo_html = f'<img src="data:image/png;base64,{LOGO_B64}" style="height:32px;"/>' if LOGO_B64 else ''

st.markdown(f"""
<style>
  #MainMenu, footer, header {{display: none !important;}}
  .stApp {{background: {BG}; color: {TEXT};}}
  .stDeprecationWarning {{display: none !important;}}
  .block-container {{padding: 110px 1rem 80px 1rem !important; max-width: 850px !important;}}
  
  .header-bar {{
    background: {HEADER_BG}; border-radius: 0 0 10px 10px; padding: 12px 16px;
    display: flex; align-items: center; gap: 14px;
    position: fixed; top: 0; left: 50%; transform: translateX(-50%);
    width: 100%; max-width: 850px; z-index: 998;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }}
  .header-bar img {{ height: 32px; }}
  .header-title {{ color: #fff; font-size: 15px; font-weight: 600; }}
  .header-sub {{ color: #9ca3af; font-size: 11px; }}
  
  .msg-u {{
    background: {USER_BG}; color: {TEXT}; padding: 10px 14px;
    border-radius: 14px 4px 14px 14px; margin: 6px 0 6px auto;
    max-width: 75%; font-size: 13px; text-align: right;
  }}
  .msg-a {{
    background: {ASST_BG}; color: {TEXT}; padding: 10px 14px;
    border-radius: 4px 14px 14px 14px; margin: 6px auto 6px 0;
    max-width: 80%; font-size: 13px; line-height: 1.6;
  }}
  .msg-e {{
    background: #ffebe9; color: #cf222e; padding: 10px 14px;
    border-radius: 8px; margin: 6px 0; font-size: 12px;
  }}
  
  [data-testid="stChatInput"] {{
    background: {CARD} !important;
    border-top: 1px solid {BORDER} !important;
  }}
  
  [data-testid="stSidebar"] {{ background: {HEADER_BG} !important; }}
  [data-testid="stSidebar"] * {{ color: #e6edf3 !important; }}
  [data-testid="stSidebar"] .stButton > button {{
    background: transparent !important; color: #cdd6f4 !important;
    border: 1px solid #3a3a4c !important; text-align: left !important; font-size: 12px !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover {{ background: #313244 !important; }}
  [data-testid="stSidebar"] .stSelectbox > div[data-baseweb="select"] > div {{
    background: #313244 !important; border-color: #3a3a4c !important;
  }}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def get_token():
    r = requests.post(TOKEN_URL, data={"grant_type":"client_credentials","client_id":CLIENT_ID,"client_secret":CLIENT_SECRET}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def get_models():
    """Lazy load models from Gen AI Hub (called on demand, not at startup)"""
    try:
        from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
        seen, out = set(), []
        for d in get_proxy_client().deployments:
            s = str(d).lower()
            name = 'gpt-4o-mini' if 'gpt-4o-mini' in s else ('anthropic--claude-4.5-haiku' if 'claude' in s else None)
            if name and name not in seen:
                seen.add(name)
                out.append(name)
        return out if out else ["gpt-4o-mini"]
    except Exception as e:
        return ["gpt-4o-mini"]

def fetch_all_data():
    if st.session_state.all_data is not None:
        return st.session_state.all_data
    token = get_token()
    r = requests.get(ODATA_URL+"?$format=json&$top=10000", headers={"Authorization":f"Bearer {token}"}, timeout=30)
    if r.status_code < 400:
        data = r.json().get("value", [])
        st.session_state.all_data = data
        return data
    return []

def llm_call(model, prompt):
    from gen_ai_hub.proxy.native.openai import chat
    r = chat.completions.create(model_name=model, temperature=0.3, messages=[{"role":"user","content":prompt}])
    try:
        st.session_state.tokens += r.usage.total_tokens
    except:
        st.session_state.tokens += 10
    return r.choices[0].message.content.strip()

def detect_column(ql, df):
    for kw, col in {
        "net_cashflow":"Net_Cashflow", "net cash":"Net_Cashflow", "cashflow":"Net_Cashflow", "cash flow":"Net_Cashflow",
        "cumulative":"Cumulative_Net", "inflow_baseline":"Inflow_Baseline", "inflow":"Inflow_Baseline",
        "outflow_baseline":"Outflow_Baseline", "outflow":"Outflow_Baseline",
        "inflow_forecast":"Inflow_Forecast", "outflow_forecast":"Outflow_Forecast",
    }.items():
        if kw in ql and col in df.columns:
            return col
    return "Net_Cashflow" if "Net_Cashflow" in df.columns else None

def process(q, model):
    st.session_state.messages.append(("user", q))
    try:
        all_data = fetch_all_data()
        if not all_data:
            st.session_state.messages.append(("asst", "Could not fetch data."))
            return
        
        df = pd.DataFrame(all_data)
        ql = q.lower().strip()
        num_cols = [c for c in df.columns if df[c].dtype in ['float64','int64','float32','int32']]
        target_col = detect_column(ql, df)
        
        # ── CONTEXT: resolve "it", "same", "this", "previous" ──
        prev_code = None
        prev_col = None
        if any(w in ql for w in ["it ","same","this","previous","above","that"]):
            # Find last mentioned company code from previous messages
            for role, content in reversed(st.session_state.messages[:-1]):
                if role in ("user", "asst"):
                    code_found = re.search(r'\b(\d{4})\b', str(content))
                    if code_found:
                        prev_code = code_found.group(1)
                        break
            # Find last mentioned column
            for role, content in reversed(st.session_state.messages[:-1]):
                if role in ("user", "asst"):
                    prev_col = detect_column(str(content).lower(), df)
                    if prev_col:
                        break
        
        code_match = re.search(r'\b(\d{4})\b', ql)
        target_code = code_match.group(1) if code_match else prev_code
        if not target_col and prev_col:
            target_col = prev_col
        if not target_col:
            target_col = "Net_Cashflow" if "Net_Cashflow" in df.columns else None
        
        # ── PRIORITY 1: highest/lowest/most/top (BEFORE company codes) ──
        if any(w in ql for w in ["highest","most","largest","biggest","lowest","least","smallest","top"]):
            if target_col and "CompanyCode" in df.columns:
                # Exclude ALL and OTHER from rankings
                df_clean = df[~df["CompanyCode"].isin(["ALL","OTHER"])]
                agg = df_clean.groupby("CompanyCode")[target_col].sum().reset_index()
                agg.columns = ["CompanyCode", f"Total_{target_col}"]
                
                # Top N
                top_match = re.search(r'top\s*(\d+)', ql)
                if top_match:
                    n = int(top_match.group(1))
                    top_df = agg.nlargest(n, f"Total_{target_col}")
                    st.session_state.messages.append(("table", top_df))
                    return
                
                # Second highest/lowest
                if "second" in ql:
                    if any(w in ql for w in ["lowest","least"]):
                        sorted_df = agg.nsmallest(2, f"Total_{target_col}")
                    else:
                        sorted_df = agg.nlargest(2, f"Total_{target_col}")
                    if len(sorted_df) >= 2:
                        row = sorted_df.iloc[1]
                        st.session_state.messages.append(("asst", f"Second {'lowest' if 'lowest' in ql else 'highest'}: Company **{row['CompanyCode']}** with {target_col}: **{row[f'Total_{target_col}']:,.2f}**"))
                        return
                
                # Single highest/lowest
                is_lowest = any(w in ql for w in ["lowest","least","smallest"])
                row = agg.loc[agg[f"Total_{target_col}"].idxmin()] if is_lowest else agg.loc[agg[f"Total_{target_col}"].idxmax()]
                st.session_state.messages.append(("asst", f"Company **{row['CompanyCode']}** has the {'lowest' if is_lowest else 'highest'} {target_col}: **{row[f'Total_{target_col}']:,.2f}**"))
                return
        
        # ── PRIORITY 2: Specific company total ──
        if target_code and any(w in ql for w in ["total","sum","net","cash","inflow","outflow","for"]):
            subset = df[df["CompanyCode"].astype(str) == target_code]
            if not subset.empty:
                lines = [f"**Company {target_code}** ({len(subset)} records):"]
                for col in ["Net_Cashflow","Inflow_Baseline","Outflow_Baseline","Cumulative_Net","Inflow_Forecast","Outflow_Forecast"]:
                    if col in subset.columns:
                        lines.append(f"- {col}: **{subset[col].sum():,.2f}**")
                st.session_state.messages.append(("asst", "\n".join(lines)))
                return
        
        # ── PRIORITY 3: Group by company ──
        if any(w in ql for w in ["against each","each company","company wise","code wise","wise total","summing up"]):
            # Aggregate ALL numeric columns, not just one
            agg = df.groupby("CompanyCode")[num_cols].sum().reset_index()
            st.session_state.messages.append(("table", agg.sort_values("CompanyCode")))
            return
        
        # ── PRIORITY 4: Chart ──
        if any(w in ql for w in ["chart","graph","plot","visualize"]):
            st.session_state.messages.append(("chart", None))
            return
        
        # ── PRIORITY 5: Record count ──
        if "how many" in ql and "record" in ql:
            st.session_state.messages.append(("asst", f"Total records: **{len(df)}**"))
            return
        
        # ── PRIORITY 6: Columns ──
        if any(w in ql for w in ["column","field","schema"]):
            cols_with_data = [c for c in df.columns if df[c].notna().any()]
            st.session_state.messages.append(("asst", f"**{len(cols_with_data)} columns:**\n{', '.join(cols_with_data)}"))
            return
        
        # ── PRIORITY 7: Grand total ──
        if "total" in ql and target_col:
            st.session_state.messages.append(("asst", f"Total {target_col}: **{df[target_col].sum():,.2f}**"))
            return
        
        # ── PRIORITY 8: Table ──
        if any(w in ql for w in ["table","show data","records","show record"]):
            n_match = re.search(r'(\d+)', ql)
            if "all" in ql:
                n = len(df)
            elif n_match:
                n = int(n_match.group(1))
            else:
                n = 20
            
            # If context refers to a specific company, filter for it
            if target_code:
                subset = df[df["CompanyCode"].astype(str) == target_code]
                if not subset.empty:
                    cols_with_data = [c for c in subset.columns if subset[c].notna().any()]
                    st.session_state.messages.append(("table", subset[cols_with_data].head(n)))
                    return
            
            cols_with_data = [c for c in df.columns if df[c].notna().any()]
            st.session_state.messages.append(("table", df[cols_with_data].head(n)))
            return
        
        # ── PRIORITY 9: Company codes (LAST among specific patterns) ──
        if "company" in ql and ("code" in ql or "codes" in ql):
            codes = sorted(set(str(x) for x in df["CompanyCode"].dropna().unique()))
            st.session_state.messages.append(("asst", f"**{len(codes)} unique company codes:**\n{', '.join(codes)}"))
            return
        
        # ── PRIORITY 10: Specific company fallback ──
        if target_code:
            subset = df[df["CompanyCode"].astype(str) == target_code]
            if not subset.empty:
                lines = [f"**Company {target_code}** ({len(subset)} records):"]
                for col in num_cols[:5]:
                    lines.append(f"- {col}: **{subset[col].sum():,.2f}**")
                st.session_state.messages.append(("asst", "\n".join(lines)))
                return
        
        # ── PRIORITY 11: LLM ──
        try:
            ans = llm_call(model, f"Q: {q}\nData: {len(df)} rows, cols: {','.join(df.columns[:10])}\nSample: {json.dumps(all_data[:3])[:300]}\nAnswer with specific numbers.")
            st.session_state.messages.append(("asst", ans))
        except Exception as e:
            st.session_state.messages.append(("err", f"LLM: {str(e)[:60]}"))
    except Exception as e:
        st.session_state.messages.append(("err", str(e)[:80]))

# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 💬 Chats")
    
    if st.button("➕ New Chat", use_container_width=True):
        if st.session_state.messages:
            first_q = next((c for r, c in st.session_state.messages if r == "user"), "Empty")
            st.session_state.chat_history.append({"name": first_q[:35], "messages": st.session_state.messages.copy(), "tokens": st.session_state.tokens})
        st.session_state.messages = []
        st.session_state.tokens = 0
        st.rerun()
    
    for i, chat in enumerate(reversed(st.session_state.chat_history)):
        if st.button(f"💬 {chat['name']}", key=f"ch_{i}", use_container_width=True):
            if st.session_state.messages:
                first_q = next((c for r, c in st.session_state.messages if r == "user"), "Empty")
                st.session_state.chat_history.append({"name": first_q[:35], "messages": st.session_state.messages.copy(), "tokens": st.session_state.tokens})
            st.session_state.messages = chat["messages"]
            st.session_state.tokens = chat["tokens"]
            idx = len(st.session_state.chat_history) - 1 - i
            st.session_state.chat_history.pop(idx)
            st.rerun()
    
    st.divider()
    
    # Model selector - use default models (don't call get_models at startup)
    if not st.session_state.models:
        st.session_state.models = ["gpt-4o-mini", "anthropic--claude-4.5-haiku"]
    st.selectbox("Model", st.session_state.models, key="m", on_change=lambda: st.session_state.update({"model": st.session_state.m}))
    
    # Lazy load Gen AI Hub models on demand
    if st.button("🔄 Load Gen AI Hub Models", use_container_width=True):
        with st.spinner("Loading models..."):
            models = get_models()
            st.session_state.models = models
            st.success(f"✓ Loaded {len(models)} models")
            st.rerun()
    
    st.caption(f"📊 Tokens: {st.session_state.tokens}")
    
    st.divider()
    
    if st.button("🌙 Dark" if not dark else "☀️ Light", use_container_width=True):
        st.session_state.dark = not dark
        st.rerun()
    
    if st.button("🔗 Test Connection", use_container_width=True):
        try:
            get_token()
            st.success("✓ Connected")
        except Exception as e:
            st.error(f"✗ Failed: {str(e)[:50]}")
    
    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tokens = 0
        st.session_state.all_data = None
        st.rerun()

# ════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════

st.markdown(f"""<div class='header-bar'>
    {logo_html}
    <div><div class='header-title'>BDC AI Assistant</div><div class='header-sub'>Blueprint Technologies · Gen AI Hub</div></div>
</div>""", unsafe_allow_html=True)

# Controls bar (always visible)
c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
with c1:
    # Default models (don't call get_models at startup)
    if not st.session_state.models:
        st.session_state.models = ["gpt-4o-mini", "anthropic--claude-4.5-haiku"]
    st.selectbox("Model", st.session_state.models, key="m_main", label_visibility="collapsed",
                 on_change=lambda: st.session_state.update({"model": st.session_state.m_main}))
with c2:
    st.caption(f"📊 {st.session_state.tokens} tokens")
with c3:
    if st.button("🌙" if not dark else "☀️"):
        st.session_state.dark = not dark
        st.rerun()
with c4:
    if st.button("🗑 Clear"):
        st.session_state.messages = []
        st.session_state.tokens = 0
        st.session_state.all_data = None
        st.rerun()

# ════════════════════════════════════════════════════════════════
# CHAT MESSAGES
# ════════════════════════════════════════════════════════════════

if not st.session_state.messages:
    st.markdown(f"""<div style='text-align:center; padding:50px 20px; color:{MUTED};'>
        <div style='font-size:28px;'>💬</div>
        <div style='font-size:14px; color:{TEXT}; margin-top:12px;'>Ask about your BDC data</div>
        <div style='font-size:11px; margin-top:10px; line-height:2.2;'>
            "Show all company codes" · "Total net cashflow for 1006"<br/>
            "Which company has highest net cashflow" · "Top 5 companies"
        </div>
    </div>""", unsafe_allow_html=True)

for idx, (role, content) in enumerate(st.session_state.messages):
    if role == "user":
        st.markdown(f"<div class='msg-u'>{content}</div>", unsafe_allow_html=True)
    elif role == "asst":
        st.markdown(f"<div class='msg-a'>{content}</div>", unsafe_allow_html=True)
    elif role == "table":
        if isinstance(content, pd.DataFrame):
            all_cols = content.columns.tolist()
            default_cols = [c for c in all_cols if content[c].notna().any()][:6]
            sel = st.multiselect("Columns", all_cols, default=default_cols, key=f"t_{idx}")
            if sel:
                st.dataframe(content[sel], use_container_width=True, height=300)
        else:
            try:
                st.dataframe(pd.read_json(content), use_container_width=True, height=300)
            except:
                pass
    elif role == "chart":
        all_data = fetch_all_data()
        if all_data:
            df_c = pd.DataFrame(all_data)
            nc = [c for c in df_c.columns if df_c[c].dtype in ['float64','int64','float32','int32']]
            c1, c2, c3 = st.columns(3)
            with c1:
                x_col = st.selectbox("X-axis", ["CompanyCode","ForecastType","Month"], key=f"x_{idx}")
            with c2:
                y_col = st.selectbox("Y-axis", nc, key=f"y_{idx}")
            with c3:
                ct = st.radio("Type", ["Bar","Line"], horizontal=True, key=f"ct_{idx}")
            agg = df_c.groupby(x_col)[y_col].sum().reset_index()
            if ct == "Bar":
                st.bar_chart(agg.set_index(x_col))
            else:
                st.line_chart(agg.set_index(x_col))
    elif role == "err":
        st.markdown(f"<div class='msg-e'>⚠ {content}</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# FIXED INPUT AT BOTTOM (st.chat_input - truly pinned)
# ════════════════════════════════════════════════════════════════

user_input = st.chat_input("Ask about your BDC data...")

if user_input:
    with st.spinner("🔍 Analyzing..."):
        process(user_input.strip(), st.session_state.model)
    st.rerun()