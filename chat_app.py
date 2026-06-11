import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv
import base64
import pandas as pd
import re

st.set_page_config(page_title="BDC AI Assistant", layout="centered", initial_sidebar_state="collapsed")
load_dotenv()

# ════════════════════════════════════════════════════════════════
# CREDENTIALS
# ════════════════════════════════════════════════════════════════
try:
    DATASPHERE_CLIENT_ID     = st.secrets.get("DATASPHERE_CLIENT_ID")     or os.getenv("DATASPHERE_CLIENT_ID")
    DATASPHERE_CLIENT_SECRET = st.secrets.get("DATASPHERE_CLIENT_SECRET") or os.getenv("DATASPHERE_CLIENT_SECRET")
    AICORE_AUTH_URL          = st.secrets.get("AICORE_AUTH_URL")          or os.getenv("AICORE_AUTH_URL")
    AICORE_CLIENT_ID         = st.secrets.get("AICORE_CLIENT_ID")         or os.getenv("AICORE_CLIENT_ID")
    AICORE_CLIENT_SECRET     = st.secrets.get("AICORE_CLIENT_SECRET")     or os.getenv("AICORE_CLIENT_SECRET")
    AICORE_BASE_URL          = st.secrets.get("AICORE_BASE_URL")          or os.getenv("AICORE_BASE_URL", "")
    AICORE_RESOURCE_GROUP    = st.secrets.get("AICORE_RESOURCE_GROUP")    or os.getenv("AICORE_RESOURCE_GROUP", "default")
except Exception:
    DATASPHERE_CLIENT_ID     = os.getenv("DATASPHERE_CLIENT_ID")
    DATASPHERE_CLIENT_SECRET = os.getenv("DATASPHERE_CLIENT_SECRET")
    AICORE_AUTH_URL          = os.getenv("AICORE_AUTH_URL")
    AICORE_CLIENT_ID         = os.getenv("AICORE_CLIENT_ID")
    AICORE_CLIENT_SECRET     = os.getenv("AICORE_CLIENT_SECRET")
    AICORE_BASE_URL          = os.getenv("AICORE_BASE_URL", "")
    AICORE_RESOURCE_GROUP    = os.getenv("AICORE_RESOURCE_GROUP", "default")

CLIENT_ID     = DATASPHERE_CLIENT_ID
CLIENT_SECRET = DATASPHERE_CLIENT_SECRET
TOKEN_URL     = "https://bpt-bdc-dataspherev2.authentication.eu10.hana.ondemand.com/oauth/token"
ODATA_URL     = "https://bpt-bdc-dataspherev2.eu10.hcs.cloud.sap/api/v1/datasphere/consumption/relational/EXP_DISK_STORE/GL_Cashflow_monthly/GL_Cashflow_monthly"
BASE          = "https://api.ai.prod-eu20.westeurope.azure.ml.hana.ondemand.com/v2/inference/deployments"

# ════════════════════════════════════════════════════════════════
# CONFIRMED WORKING ENDPOINTS (from debug)
# GPT:    {BASE}/{dep_id}/v1/chat/completions  — OpenAI format
# Claude: {BASE}/{dep_id}/invoke               — Anthropic format, NO model field
# ════════════════════════════════════════════════════════════════
MODELS = {
    "gpt-4o-mini": {
        "dep_id":   "d3d7fcb52df868d5",
        "endpoint": f"{BASE}/d3d7fcb52df868d5/v1/chat/completions",
        "type":     "openai",
        "label":    "GPT-4o Mini"
    },
    "gpt-4.1-nano": {
        "dep_id":   "d78261897cff6fde",
        "endpoint": f"{BASE}/d78261897cff6fde/v1/chat/completions",
        "type":     "openai",
        "label":    "GPT-4.1 Nano"
    },
    "anthropic--claude-4.5-haiku": {
        "dep_id":   "d104e9bb210192c1",
        "endpoint": f"{BASE}/d104e9bb210192c1/invoke",
        "type":     "claude",   # Anthropic native format
        "label":    "Claude 4.5 Haiku"
    },
}

# ════════════════════════════════════════════════════════════════
# LOGO
# ════════════════════════════════════════════════════════════════
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_B64 = None
for name in ["Logo.png", "logo.png"]:
    p = os.path.join(SCRIPT_DIR, name)
    if os.path.exists(p):
        with open(p, "rb") as f:
            LOGO_B64 = base64.b64encode(f.read()).decode()
        break

# ════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════
defaults = {
    "messages": [], "tokens": 0, "model": "gpt-4o-mini",
    "models": list(MODELS.keys()),
    "all_data": None, "dark": False, "chat_history": [],
    "aicore_token": None, "aicore_token_expiry": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

dark = st.session_state.dark
if dark:
    BG="#1e1e2e"; BORDER="#3a3a4c"; TEXT="#cdd6f4"; MUTED="#6c7086"
    USER_BG="#313244"; ASST_BG="#1e3a2a"; HEADER_BG="#181825"; TOOLBAR_BG="#181825"
else:
    BG="#ffffff"; BORDER="#e1e4e8"; TEXT="#24292f"; MUTED="#656d76"
    USER_BG="#e8f0fe"; ASST_BG="#e6f4ea"; HEADER_BG="#1a1a2e"; TOOLBAR_BG="#f0f2f6"

logo_html = f'<img src="data:image/png;base64,{LOGO_B64}" style="height:32px;"/>' if LOGO_B64 else ''

# ════════════════════════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
  #MainMenu, footer, header {{display:none !important;}}
  .stApp {{background:{BG}; color:{TEXT};}}
  .stDeprecationWarning {{display:none !important;}}
  .block-container {{padding:125px 1rem 90px 1rem !important; max-width:850px !important;}}

  .header-bar {{
    background:{HEADER_BG}; border-radius:0 0 8px 8px; padding:10px 16px;
    display:flex; align-items:center; gap:14px;
    position:fixed; top:0; left:50%; transform:translateX(-50%);
    width:100%; max-width:850px; z-index:1001;
    box-shadow:0 2px 8px rgba(0,0,0,0.2);
  }}
  .header-title {{color:#fff; font-size:15px; font-weight:600;}}
  .header-sub   {{color:#9ca3af; font-size:11px;}}

  .toolbar-wrap {{
    position:fixed; top:54px; left:50%; transform:translateX(-50%);
    width:100%; max-width:850px; z-index:1000;
    background:{TOOLBAR_BG}; border-bottom:1px solid {BORDER};
    padding:4px 12px;
  }}

  .stChatFloatingInputContainer {{
    position:fixed !important; bottom:0 !important;
    left:50% !important; transform:translateX(-50%) !important;
    width:100% !important; max-width:850px !important;
    background:{BG} !important; border-top:1px solid {BORDER} !important;
    padding:6px 12px 8px !important; z-index:1000 !important;
  }}

  .msg-u {{
    background:{USER_BG}; color:{TEXT}; padding:10px 14px;
    border-radius:14px 4px 14px 14px; margin:6px 0 6px auto;
    max-width:75%; font-size:13px; text-align:right;
  }}
  .msg-a {{
    background:{ASST_BG}; color:{TEXT}; padding:10px 14px;
    border-radius:4px 14px 14px 14px; margin:6px auto 6px 0;
    max-width:82%; font-size:13px; line-height:1.7;
  }}
  .msg-e {{background:#ffebe9;color:#cf222e;padding:10px 14px;border-radius:8px;margin:6px 0;font-size:12px;}}

  [data-testid="stSidebar"] {{background:{HEADER_BG} !important;}}
  [data-testid="stSidebar"] * {{color:#e6edf3 !important;}}
  [data-testid="stSidebar"] .stButton > button {{
    background:transparent !important; color:#cdd6f4 !important;
    border:1px solid #3a3a4c !important; text-align:left !important; font-size:12px !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover {{background:#313244 !important;}}
  .stSelectbox label {{display:none !important;}}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def get_datasphere_token():
    r = requests.post(TOKEN_URL,
        data={"grant_type":"client_credentials","client_id":CLIENT_ID,"client_secret":CLIENT_SECRET},
        timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def get_aicore_token():
    import time
    now = time.time()
    if st.session_state.aicore_token and now < st.session_state.aicore_token_expiry:
        return st.session_state.aicore_token
    auth_base = AICORE_AUTH_URL.rstrip("/").replace("/oauth/token","")
    r = requests.post(f"{auth_base}/oauth/token",
        data={"grant_type":"client_credentials","client_id":AICORE_CLIENT_ID,"client_secret":AICORE_CLIENT_SECRET},
        timeout=15)
    r.raise_for_status()
    data = r.json()
    st.session_state.aicore_token        = data["access_token"]
    st.session_state.aicore_token_expiry = now + data.get("expires_in", 3600) - 60
    return st.session_state.aicore_token

def llm_call(model, messages):
    """
    GPT  → OpenAI format: /v1/chat/completions
    Claude → Anthropic format: /invoke  (no model field, anthropic_version required)
    """
    try:
        token  = get_aicore_token()
        cfg    = MODELS.get(model, MODELS["gpt-4o-mini"])
        hdrs   = {
            "Authorization":     f"Bearer {token}",
            "AI-Resource-Group": AICORE_RESOURCE_GROUP,
            "Content-Type":      "application/json"
        }

        if cfg["type"] == "claude":
            # ── Anthropic native format ──
            # Extract system prompt (if any) and user messages
            system_text = ""
            user_msgs   = []
            for m in messages:
                if m["role"] == "system":
                    system_text = m["content"]
                else:
                    user_msgs.append(m)

            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": user_msgs
            }
            if system_text:
                payload["system"] = system_text

            resp = requests.post(cfg["endpoint"], headers=hdrs, json=payload, timeout=40)
            if resp.status_code == 200:
                data = resp.json()
                content = data["content"][0]["text"].strip()
                # Claude doesn't return token usage in same format
                st.session_state.tokens += data.get("usage", {}).get("input_tokens", 0) + \
                                           data.get("usage", {}).get("output_tokens", 0)
                return content
            else:
                return f"⚠️ Claude error {resp.status_code}: {resp.text[:200]}"

        else:
            # ── OpenAI format ──
            payload = {
                "model":       model,
                "messages":    messages,
                "temperature": 0.5,
                "max_tokens":  1000
            }
            resp = requests.post(cfg["endpoint"], headers=hdrs, json=payload, timeout=40)
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.tokens += data.get("usage", {}).get("total_tokens", 10)
                return data["choices"][0]["message"]["content"].strip()
            else:
                return f"⚠️ LLM error {resp.status_code}: {resp.text[:200]}"

    except Exception as e:
        return f"⚠️ Error: {str(e)[:150]}"

def fetch_all_data():
    if st.session_state.all_data is not None:
        return st.session_state.all_data
    token = get_datasphere_token()
    r = requests.get(ODATA_URL+"?$format=json&$top=10000",
        headers={"Authorization":f"Bearer {token}"}, timeout=30)
    if r.status_code < 400:
        data = r.json().get("value", [])
        st.session_state.all_data = data
        return data
    return []

def is_data_related(q):
    keywords = [
        "company","cashflow","cash flow","inflow","outflow","forecast","cumulative",
        "record","column","field","schema","chart","graph","plot","total","sum",
        "highest","lowest","top","bottom","average","trend","improve","increase",
        "decrease","better","worse","compare","perform","analysis","analyze",
        "1001","1003","1004","1005","1006","1007","1008","1009","1010",
        "1016","1017","1021","1022","2006","2007","2008","2009","2010","4002",
        "bdc","datasphere","net","baseline","p80","month","financial","finance","sales"
    ]
    return any(kw in q.lower() for kw in keywords)

def build_data_summary(df):
    num_cols = [c for c in df.columns if df[c].dtype in ['float64','int64','float32','int32']]
    codes    = sorted(df["CompanyCode"].dropna().unique().tolist()) if "CompanyCode" in df.columns else []
    company_summary = ""
    if "CompanyCode" in df.columns and num_cols:
        agg = df[~df["CompanyCode"].isin(["ALL","OTHER"])].groupby("CompanyCode")[num_cols[:6]].sum().reset_index()
        company_summary = agg.to_string(index=False)
    return f"""DATASET: GL Cashflow Monthly | Rows: {len(df)} | Columns: {', '.join(df.columns)}
Company codes ({len(codes)}): {', '.join(str(c) for c in codes)}
Per-company totals:
{company_summary}"""

def get_conversation_history():
    """
    Build conversation history from session messages for LLM context.
    Only includes user/assistant text messages (not tables/charts).
    Keeps last 10 turns to avoid token overflow.
    """
    history = []
    for role, content in st.session_state.messages[:-1]:  # exclude current message
        if role == "user":
            history.append({"role": "user", "content": str(content)})
        elif role == "asst":
            history.append({"role": "assistant", "content": str(content)})
    # Keep last 10 exchanges (20 messages) to stay within token limits
    return history[-20:]

def process(q, model):
    st.session_state.messages.append(("user", q))
    ql = q.lower().strip()

    if any(w in ql for w in ["show chart","plot","visualize","bar chart","line chart","show graph","make chart"]):
        st.session_state.messages.append(("chart", None)); return
    if any(w in ql for w in ["show table","show data","display table","show records"]):
        try:
            all_data = fetch_all_data()
            if all_data:
                df   = pd.DataFrame(all_data)
                cols = [c for c in df.columns if df[c].notna().any()]
                st.session_state.messages.append(("table", df[cols].head(30))); return
        except Exception: pass

    # Get prior conversation history for context
    history = get_conversation_history()

    if is_data_related(q):
        try:
            all_data = fetch_all_data()
            if not all_data:
                st.session_state.messages.append(("asst","❌ Could not fetch data.")); return
            df      = pd.DataFrame(all_data)
            summary = build_data_summary(df)
            # System prompt + history + current question
            msgs = [
                {"role":"system","content":f"You are a financial data analyst for BDC Datasphere.\nUse this GL Cashflow data:\n{summary}\nAnswer with specific numbers and actionable insights. Remember the full conversation context."},
                *history,
                {"role":"user","content":q}
            ]
        except Exception as e:
            st.session_state.messages.append(("err",f"Data error: {str(e)[:80]}")); return
    else:
        # System prompt + history + current question
        msgs = [
            {"role":"system","content":"You are a helpful AI assistant. Answer clearly and concisely. Remember the full conversation context."},
            *history,
            {"role":"user","content":q}
        ]

    ans = llm_call(model, msgs)
    st.session_state.messages.append(("asst", ans))

# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 💬 Chats")
    if st.button("➕ New Chat", use_container_width=True):
        if st.session_state.messages:
            first_q = next((c for r,c in st.session_state.messages if r=="user"),"Empty")
            st.session_state.chat_history.append({"name":first_q[:35],"messages":st.session_state.messages.copy(),"tokens":st.session_state.tokens})
        st.session_state.messages=[]; st.session_state.tokens=0; st.rerun()

    for i, chat in enumerate(reversed(st.session_state.chat_history)):
        if st.button(f"💬 {chat['name']}",key=f"ch_{i}",use_container_width=True):
            if st.session_state.messages:
                first_q = next((c for r,c in st.session_state.messages if r=="user"),"Empty")
                st.session_state.chat_history.append({"name":first_q[:35],"messages":st.session_state.messages.copy(),"tokens":st.session_state.tokens})
            st.session_state.messages=chat["messages"]; st.session_state.tokens=chat["tokens"]
            st.session_state.chat_history.pop(len(st.session_state.chat_history)-1-i); st.rerun()

    st.divider()
    if st.button("🔗 Test Datasphere", use_container_width=True):
        try: get_datasphere_token(); st.success("✓ Connected")
        except Exception as e: st.error(f"✗ {str(e)[:50]}")
    if st.button("🤖 Test AI Core", use_container_width=True):
        try: get_aicore_token(); st.success("✓ Token OK")
        except Exception as e: st.error(f"✗ {str(e)[:50]}")
    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.messages=[]; st.session_state.tokens=0; st.session_state.all_data=None; st.rerun()
    st.divider()
    st.caption("**Models:**")
    for m,cfg in MODELS.items():
        st.caption(f"• {cfg['label']} ({cfg['type']})")

# ════════════════════════════════════════════════════════════════
# HEADER + TOOLBAR
# ════════════════════════════════════════════════════════════════
st.markdown(f"""<div class='header-bar'>
  {logo_html}
  <div><div class='header-title'>BDC AI Assistant</div>
  <div class='header-sub'>Blueprint Technologies · Gen AI Hub</div></div>
</div>""", unsafe_allow_html=True)

st.markdown("<div class='toolbar-wrap'>", unsafe_allow_html=True)
tb1,tb2,tb3,tb4 = st.columns([3,1.8,0.7,0.7])
with tb1:
    st.selectbox("model", st.session_state.models, key="m_main",
        label_visibility="collapsed",
        on_change=lambda: st.session_state.update({"model": st.session_state.m_main}))
with tb2: st.caption(f"📊 {st.session_state.tokens} tokens")
with tb3:
    if st.button("🌙" if not dark else "☀️", key="dark_btn", use_container_width=True):
        st.session_state.dark = not dark; st.rerun()
with tb4:
    if st.button("🗑", key="clear_btn", use_container_width=True):
        st.session_state.messages=[]; st.session_state.tokens=0; st.session_state.all_data=None; st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# CHAT MESSAGES
# ════════════════════════════════════════════════════════════════
if not st.session_state.messages:
    st.markdown(f"""<div style='text-align:center;padding:40px 20px;'>
      <div style='font-size:32px;'>💬</div>
      <div style='font-size:15px;color:{TEXT};margin-top:12px;font-weight:600;'>Ask anything — BDC data or general questions</div>
      <div style='font-size:11px;margin-top:12px;line-height:2.6;color:{MUTED};'>
        "How to improve net cashflow?" · "Which company is performing best?"<br/>
        "Compare company 1005 vs 1021" · "Show chart of net cashflow"<br/>
        "Explain P80 forecast range"
      </div></div>""", unsafe_allow_html=True)

for idx,(role,content) in enumerate(st.session_state.messages):
    if role=="user":
        st.markdown(f"<div class='msg-u'>{content}</div>", unsafe_allow_html=True)
    elif role=="asst":
        st.markdown(f"<div class='msg-a'>{content}</div>", unsafe_allow_html=True)
    elif role=="table":
        if isinstance(content, pd.DataFrame):
            all_cols     = content.columns.tolist()
            default_cols = [c for c in all_cols if content[c].notna().any()][:6]
            sel = st.multiselect("Columns", all_cols, default=default_cols, key=f"t_{idx}")
            if sel: st.dataframe(content[sel], use_container_width=True, height=300)
    elif role=="chart":
        data_c = fetch_all_data()
        if data_c:
            df_c = pd.DataFrame(data_c)
            nc   = [c for c in df_c.columns if df_c[c].dtype in ['float64','int64','float32','int32']]
            ca,cb,cc = st.columns(3)
            with ca: x_col = st.selectbox("X-axis",["CompanyCode","ForecastType","Month"],key=f"x_{idx}")
            with cb: y_col = st.selectbox("Y-axis",nc,key=f"y_{idx}")
            with cc: ct    = st.radio("Type",["Bar","Line"],horizontal=True,key=f"ct_{idx}")
            agg = df_c.groupby(x_col)[y_col].sum().reset_index()
            st.bar_chart(agg.set_index(x_col)) if ct=="Bar" else st.line_chart(agg.set_index(x_col))
    elif role=="err":
        st.markdown(f"<div class='msg-e'>⚠ {content}</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# CHAT INPUT
# ════════════════════════════════════════════════════════════════
user_input = st.chat_input("Ask about BDC data or anything else...")
if user_input:
    with st.spinner("🔍 Thinking..."):
        process(user_input.strip(), st.session_state.model)
    st.rerun()
