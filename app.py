"""
Southeastern Equipment — Customer Outreach Hub
At Risk | Recovery | Conquest
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

st.set_page_config(page_title="SE Outreach Hub", page_icon="SE", layout="wide",
                   initial_sidebar_state="collapsed")

APP_DIR = Path(__file__).parent
SE_MAROON = "#A41E35"
SE_DARK   = "#7a1528"

BRANCHES = {
    1:"Cambridge", 2:"North Canton", 3:"Gallipolis", 4:"Dublin", 5:"Monroe",
    6:"Burlington", 7:"Perrysburg", 9:"Brunswick", 11:"Mentor", 12:"Fort Wayne",
    13:"Indianapolis", 14:"Mansfield", 15:"Heath", 16:"Marietta", 17:"Evansville",
    19:"Holt", 20:"Novi"
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# =============================================================================
# GOOGLE SHEETS BACKEND
# =============================================================================

@st.cache_resource(ttl=300)
def get_gsheet_connection():
    if not GSHEETS_AVAILABLE: return None, None
    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet_url = st.secrets.get("sheet_url", "")
        if sheet_url:
            sh = client.open_by_url(sheet_url)
        else:
            sname = st.secrets.get("sheet_name", "SE Outreach Call Log")
            try:
                sh = client.open(sname)
            except gspread.SpreadsheetNotFound:
                sh = client.create(sname)
                sh.share(None, perm_type='anyone', role='writer')
        try:
            ws = sh.worksheet("call_log")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="call_log", rows=5000, cols=10)
            ws.append_row(["log_key","customer_name","branch_name","called",
                           "followup","notes","user","date_updated","module","targeted"])
        return client, sh
    except Exception as e:
        st.sidebar.warning(f"Sheets: {e}")
        return None, None

def load_call_log_gsheets(sh):
    try:
        records = sh.worksheet("call_log").get_all_records()
        log = {}
        for r in records:
            key = r.get("log_key", "")
            if not key: continue
            log[key] = {
                "customer_name": r.get("customer_name", ""),
                "branch_name":   r.get("branch_name", ""),
                "called":   str(r.get("called",   "")).lower() == "true",
                "followup": str(r.get("followup", "")).lower() == "true",
                "targeted": str(r.get("targeted", "")).lower() == "true",
                "notes": r.get("notes", ""),
                "user":  r.get("user", ""),
                "date_updated": r.get("date_updated", ""),
            }
        return log
    except Exception:
        return {}

def save_entry_gsheets(sh, log_key, entry):
    try:
        ws = sh.worksheet("call_log")
        module = log_key.split("_")[0]
        row_data = [log_key,
                    entry.get("customer_name",""), entry.get("branch_name",""),
                    str(entry.get("called", False)), str(entry.get("followup", False)),
                    entry.get("notes",""), entry.get("user",""),
                    entry.get("date_updated",""), module,
                    str(entry.get("targeted", False))]
        try:
            cell = ws.find(log_key, in_column=1)
            if cell:
                ws.update(f"A{cell.row}:J{cell.row}", [row_data]); return
        except gspread.exceptions.CellNotFound:
            pass
        ws.append_row(row_data, value_input_option="RAW")
    except Exception as e:
        st.toast(f"Save error: {e}", icon="warning")

def delete_entry_gsheets(sh, log_key):
    try:
        ws = sh.worksheet("call_log")
        cell = ws.find(log_key, in_column=1)
        if cell: ws.delete_rows(cell.row)
    except Exception:
        pass

CALL_LOG_FILE = APP_DIR / "call_log.json"

def load_call_log_local():
    if CALL_LOG_FILE.exists():
        try:
            with open(CALL_LOG_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_call_log_local(log):
    with open(CALL_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2, default=str)

def init_call_log():
    if "call_log" not in st.session_state or st.session_state.call_log is None:
        _, sh = get_gsheet_connection()
        if sh:
            st.session_state.call_log = load_call_log_gsheets(sh)
            st.session_state.gsheets_active = True
        else:
            st.session_state.call_log = load_call_log_local()
            st.session_state.gsheets_active = False

def save_entry(log_key, entry):
    st.session_state.call_log[log_key] = entry
    if st.session_state.get("gsheets_active"):
        _, sh = get_gsheet_connection()
        if sh: save_entry_gsheets(sh, log_key, entry)
    else:
        save_call_log_local(st.session_state.call_log)

def delete_entry(log_key):
    if log_key in st.session_state.call_log:
        del st.session_state.call_log[log_key]
    if st.session_state.get("gsheets_active"):
        _, sh = get_gsheet_connection()
        if sh: delete_entry_gsheets(sh, log_key)
    else:
        save_call_log_local(st.session_state.call_log)

# =============================================================================
# CSS
# =============================================================================

st.markdown(f"""
<style>
    #MainMenu {{visibility:hidden;}} footer {{visibility:hidden;}}
    .stDeployButton {{display:none;}} header {{visibility:hidden;}}
    .main .block-container {{padding-top:0;padding-bottom:2rem;max-width:1400px;}}
    .login-wrap {{text-align:center;padding:60px 20px 30px;}}
    .login-title {{color:{SE_MAROON};font-size:30px;font-weight:700;margin-bottom:6px;}}
    .login-sub {{color:#64748b;font-size:14px;margin-bottom:40px;}}
    .hbar {{background:{SE_MAROON};color:white;padding:12px 24px;margin:-1rem -1rem 1rem -1rem;
            display:flex;justify-content:space-between;align-items:center;}}
    .hbar-title {{font-weight:600;font-size:15px;}}
    .hbar-info  {{font-size:12px;opacity:0.9;}}
    .card-wrap {{border-radius:8px;padding:16px 18px;margin-bottom:6px;}}
    .card-label {{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;opacity:0.8;margin-bottom:6px;}}
    .card-big   {{font-size:26px;font-weight:700;line-height:1;}}
    .card-sub   {{font-size:11px;color:#94a3b8;margin-top:6px;}}
    .card-bar   {{height:3px;border-radius:2px;margin-top:10px;overflow:hidden;}}
    .card-fill  {{height:100%;border-radius:2px;}}
    .banner {{padding:10px 16px;border-radius:6px;font-size:13px;margin-bottom:12px;}}
    .col-hdr {{font-weight:600;font-size:10px;color:#64748b;text-transform:uppercase;
               letter-spacing:0.5px;padding-bottom:5px;border-bottom:2px solid #e2e8f0;margin-bottom:8px;}}
    .cname {{font-weight:600;font-size:13px;color:#1e293b;}}
    .csub  {{font-size:11px;color:#94a3b8;}}
    .cval  {{font-size:12px;color:#475569;}}
    .divider {{border-bottom:1px solid #f1f5f9;margin:4px 0;}}
    .tgt-bg {{background:#FFFBEB;border-left:3px solid #D97706;padding-left:6px;border-radius:2px;}}
    .badge {{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:600;}}
    .b-hot  {{background:#FEE2E2;color:#991B1B;}}
    .b-warm {{background:#FEF3C7;color:#92400E;}}
    .b-cool {{background:#DBEAFE;color:#1E40AF;}}
    .b-gray {{background:#F3F4F6;color:#374151;}}
    .gs-on  {{font-size:11px;background:#ECFDF5;color:#065F46;padding:2px 8px;border-radius:10px;}}
    .gs-off {{font-size:11px;background:#FEF2F2;color:#991B1B;padding:2px 8px;border-radius:10px;}}
    .stButton>button {{background:{SE_MAROON};color:white;border:none;font-weight:500;}}
    .stButton>button:hover {{background:{SE_DARK};color:white;}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA LOADERS
# =============================================================================

@st.cache_data
def load_at_risk():
    try: return pd.read_csv(APP_DIR / "data_at_risk.csv")
    except: return pd.DataFrame()

@st.cache_data
def load_recovery():
    try: return pd.read_csv(APP_DIR / "data_recovery_lost.csv")
    except: return pd.DataFrame()

@st.cache_data
def load_conquest():
    try: return pd.read_csv(APP_DIR / "data_conquest.csv")
    except: return pd.DataFrame()

# =============================================================================
# HELPERS
# =============================================================================

def gbn(): return BRANCHES.get(st.session_state.get('branch'), 'Unknown')
def gun(): return st.session_state.get('user_name', '')
def go(p): st.session_state.page = p

def gs_badge():
    if st.session_state.get('gsheets_active'):
        return '<span class="gs-on">Sheets</span>'
    return '<span class="gs-off">Local</span>'

def hbar(title, right=''):
    st.markdown(
        f'<div class="hbar"><span class="hbar-title">{title}</span>'
        f'<span class="hbar-info">{right} {gun()} {gs_badge()}</span></div>',
        unsafe_allow_html=True)

def col_heads(ws, labels):
    cols = st.columns(ws)
    for i, l in enumerate(labels):
        cols[i].markdown(f'<div class="col-hdr">{l}</div>', unsafe_allow_html=True)

def fmt_rev(v):
    try:
        f = float(v)
        return f"${f:,.0f}" if f and f != 0 else "—"
    except:
        return "—"

def fmt_mo(v):
    try: return f"{float(v):.1f}"
    except: return "—"

def n_targeted(df, id_col, prefix, log):
    if df.empty or id_col not in df.columns: return 0
    return sum(1 for _, r in df.iterrows()
               if log.get(f"{prefix}_{r[id_col]}", {}).get('targeted'))

def n_called(df, id_col, prefix, log):
    if df.empty or id_col not in df.columns: return 0
    return sum(1 for _, r in df.iterrows()
               if log.get(f"{prefix}_{r[id_col]}", {}).get('called'))

def target_toggle(lk, currently, cname, dbr):
    if currently:
        e = st.session_state.call_log.get(lk, {})
        e.update({'targeted': True, 'customer_name': cname, 'branch_name': dbr,
                  'user': gun(), 'date_updated': datetime.now().strftime('%Y-%m-%d %H:%M')})
        save_entry(lk, e)
    else:
        e = st.session_state.call_log.get(lk, {})
        if not e.get('called') and not e.get('notes'):
            delete_entry(lk)
        else:
            e['targeted'] = False
            save_entry(lk, e)

def back_btn(dest, key):
    if st.button("Back", key=key): go(dest); st.rerun()

# =============================================================================
# STATE INIT
# =============================================================================

for key, default in [('page','login'), ('branch', None), ('user_name', ''),
                     ('call_log', None), ('gsheets_active', False)]:
    if key not in st.session_state:
        st.session_state[key] = default

init_call_log()

# =============================================================================
# LOGIN
# =============================================================================

def show_login():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Southeastern Equipment</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Customer Outreach Hub</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        name = st.text_input("Your name", placeholder="First Last",
                              value=st.session_state.user_name)
        branch_opts = ["Select branch..."] + list(BRANCHES.values())
        branch_sel  = st.selectbox("Branch", branch_opts)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Get Started", use_container_width=True):
            if not name.strip():
                st.error("Enter your name.")
            elif branch_sel == "Select branch...":
                st.error("Select your branch.")
            else:
                st.session_state.user_name = name.strip()
                br_id = next((k for k, v in BRANCHES.items() if v == branch_sel), None)
                st.session_state.branch = br_id
                go('cards')
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# CARDS
# =============================================================================

def show_cards():
    branch = gbn()
    log    = st.session_state.call_log

    ar  = load_at_risk()
    rec = load_recovery()
    cq  = load_conquest()

    def bf(df, col, val):
        return df[df[col] == val].copy() if col in df.columns and not df.empty else pd.DataFrame()

    arb  = bf(ar,  'branch', branch)
    recb = bf(rec, 'branch', branch)
    cqb  = bf(cq,  'branch', branch)

    ar_tg  = n_targeted(arb,  'customer', 'atrisk',   log)
    ar_cd  = n_called(arb,    'customer', 'atrisk',   log)
    rec_tg = n_targeted(recb, 'customer', 'recovery', log)
    rec_cd = n_called(recb,   'customer', 'recovery', log)
    cq_tg  = n_targeted(cqb,  'company',  'conquest', log)
    cq_cd  = n_called(cqb,    'company',  'conquest', log)

    hbar("Customer Outreach Hub", f"{branch} |")

    st.markdown(
        f'<p style="color:#64748b;font-size:13px;margin-bottom:18px;">'
        f'Welcome, {gun()}. Select a list to get started.</p>',
        unsafe_allow_html=True)

    urgent_ct = len(arb[arb['months_gone'] < 7]) if not arb.empty and 'months_gone' in arb.columns else 0
    t12_ct    = len(cqb[cqb['tier'] <= 2]) if not cqb.empty and 'tier' in cqb.columns else 0

    modules = [
        dict(key='atrisk',   title='At Risk',  color='#D97706', bg='#FFFBEB', bar='#FDE68A',
             total=len(arb),  tg=ar_tg,  cd=ar_cd,
             sub=f"{urgent_ct} urgent (under 7 mo)" if urgent_ct else "6–12 months inactive",
             browse='atrisk', lst='atrisk_list'),
        dict(key='recovery', title='Recovery', color='#DC2626', bg='#FEF2F2', bar='#FECACA',
             total=len(recb), tg=rec_tg, cd=rec_cd,
             sub="Lost 13–30 months",
             browse='recovery', lst='recovery_list'),
        dict(key='conquest', title='Conquest', color='#7C3AED', bg='#F5F3FF', bar='#DDD6FE',
             total=len(cqb),  tg=cq_tg,  cd=cq_cd,
             sub=f"{t12_ct} priority leads (Tier 1 & 2)" if t12_ct else "New prospects",
             browse='conquest', lst='conquest_list'),
    ]

    cols = st.columns(3)
    for i, m in enumerate(modules):
        with cols[i]:
            pct = int(m['cd'] / m['total'] * 100) if m['total'] > 0 else 0

            b1, b2 = st.columns([1.6, 1])
            with b1:
                if st.button(m['title'], key=f"card_{m['key']}", use_container_width=True):
                    go(m['browse']); st.rerun()
            with b2:
                lbl = f"List ({m['tg']})" if m['tg'] > 0 else "My List"
                if st.button(lbl, key=f"list_{m['key']}", use_container_width=True):
                    go(m['lst']); st.rerun()

            tg_line = (f'<div style="font-size:11px;color:#D97706;font-weight:600;margin-top:2px;">'
                       f'{m["tg"]} targeted</div>') if m['tg'] > 0 else \
                      '<div style="font-size:11px;color:#94a3b8;margin-top:2px;">select targets first</div>'

            st.markdown(f"""<div class="card-wrap" style="background:{m['bg']};">
                <div class="card-label" style="color:{m['color']};">{m['title']}</div>
                <div style="display:flex;justify-content:space-between;align-items:flex-end;">
                    <div class="card-big" style="color:{m['color']};">{m['total']}</div>
                    <div style="text-align:right;">
                        <div style="font-size:15px;font-weight:700;color:{m['color']};">{pct}%</div>
                        <div style="font-size:11px;color:{m['color']};">{m['cd']} called</div>
                        {tg_line}
                    </div>
                </div>
                <div class="card-sub">{m['sub']}</div>
                <div class="card-bar" style="background:{m['bar']};"><div class="card-fill"
                    style="width:{pct}%;background:{m['color']};"></div></div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 1, 1])
    with c2:
        if st.button("Change Branch / User", use_container_width=True):
            go('login'); st.rerun()

    st.markdown(
        '<div style="text-align:center;color:#94a3b8;font-size:11px;margin-top:28px;'
        'padding-top:12px;border-top:1px solid #e2e8f0;">'
        'Southeastern Equipment | Customer Outreach Hub | 2026</div>',
        unsafe_allow_html=True)

# =============================================================================
# TIER LABELS (Conquest)
# =============================================================================

TIER_LABELS = {
    1: ('Tier 1', 'b-hot'),
    2: ('Tier 2', 'b-warm'),
    3: ('Tier 3', 'b-cool'),
    4: ('Tier 4', 'b-gray'),
}

# =============================================================================
# AT RISK — BROWSE
# =============================================================================

def show_atrisk_browse():
    df = load_at_risk()
    if df.empty:
        st.error("No at risk data."); back_btn('cards', 'back_ar_empty'); return

    dbr = gbn(); log = st.session_state.call_log

    c1, c2, c3, c4 = st.columns([2, 2, 2.5, 0.8])
    with c1:
        opts = ["All Branches"] + sorted(df['branch'].dropna().unique().tolist())
        sel  = st.selectbox("Branch", opts, index=opts.index(dbr) if dbr in opts else 0,
                             key="br_ar", label_visibility="collapsed")
        if sel != "All Branches": dbr = sel
    with c2:
        filt = st.selectbox("Filter", ["All", "Urgent (<7 mo)", "7–12 months"],
                             key="filt_ar", label_visibility="collapsed")
    with c3:
        search = st.text_input("Search", placeholder="Search customer...",
                                key="s_ar", label_visibility="collapsed")
    with c4:
        back_btn('cards', 'back_ar')

    f = df[df['branch'] == dbr].copy()
    if filt == "Urgent (<7 mo)":  f = f[f['months_gone'] < 7]
    elif filt == "7–12 months":   f = f[f['months_gone'] >= 7]
    if search: f = f[f['customer'].str.contains(search, case=False, na=False)]

    f['_tg'] = f['customer'].apply(lambda x: log.get(f"atrisk_{x}", {}).get('targeted', False))
    f = f.sort_values(['_tg', 'months_gone'], ascending=[False, True])

    tg_ct   = int(f['_tg'].sum())
    br_all  = df[df['branch'] == dbr]
    urgent  = len(br_all[br_all['months_gone'] < 7])

    hbar("At Risk — Browse", f"{dbr} |")

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown(
            f'<div class="banner" style="background:#FFFBEB;color:#92400E;border-left:4px solid #D97706;">'
            f'<strong>{len(br_all)} customers</strong> have not purchased in 6–12 months. '
            f'<strong>{urgent} urgent</strong> (under 7 months). '
            f'Select who you plan to contact, then open your target list.</div>',
            unsafe_allow_html=True)
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        lbl = f"My Target List ({tg_ct})" if tg_ct > 0 else "My Target List"
        if st.button(lbl, use_container_width=True,
                     type="primary" if tg_ct > 0 else "secondary", key="goto_ar_list"):
            go('atrisk_list'); st.rerun()

    st.caption(f"{len(f)} shown")
    WS = [0.4, 2.8, 1.3, 1.1, 1.3]
    col_heads(WS, ['SELECT', 'CUSTOMER', '3-YR REVENUE', 'MONTHS INACTIVE', 'LAST PURCHASE'])

    for _, r in f.head(150).iterrows():
        cid  = str(r['customer']).strip()
        lk   = f"atrisk_{cid}"
        e    = log.get(lk, {}); it = e.get('targeted', False)
        acct = str(r.get('acct', '')).split('.')[0] if pd.notna(r.get('acct','')) else ''
        lp   = str(r.get('last_purchase',''))[:10] if pd.notna(r.get('last_purchase','')) else ''

        if it: st.markdown('<div class="tgt-bg">', unsafe_allow_html=True)
        cols = st.columns(WS)
        with cols[0]:
            nt = st.checkbox("", value=it, key=f"t_{lk}", label_visibility="collapsed")
        with cols[1]:
            st.markdown(f'<div class="cname">{cid}</div>', unsafe_allow_html=True)
            if acct: st.markdown(f'<div class="csub">Acct {acct}</div>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f'<div class="cval">{fmt_rev(r.get("decline_amount",0))}</div>', unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f'<div class="cval">{fmt_mo(r.get("months_gone",0))} mo</div>', unsafe_allow_html=True)
        with cols[4]:
            st.markdown(f'<div class="cval">{lp}</div>', unsafe_allow_html=True)
        if it: st.markdown('</div>', unsafe_allow_html=True)

        if nt != it:
            target_toggle(lk, nt, cid, dbr); st.rerun()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =============================================================================
# AT RISK — TARGET LIST
# =============================================================================

def show_atrisk_list():
    df = load_at_risk(); dbr = gbn(); log = st.session_state.call_log

    f = df[df['branch'] == dbr].copy() if not df.empty else pd.DataFrame()
    f['_tg'] = f['customer'].apply(lambda x: log.get(f"atrisk_{x}", {}).get('targeted', False))
    f['_cd'] = f['customer'].apply(lambda x: log.get(f"atrisk_{x}", {}).get('called',   False))
    targets  = f[f['_tg']].sort_values(['_cd','months_gone'], ascending=[False, True])

    tg_ct = len(targets); cd_ct = int(targets['_cd'].sum()) if tg_ct > 0 else 0
    hbar("At Risk — My Target List", f"{dbr} | {cd_ct}/{tg_ct} called |")

    c1, _, c2 = st.columns([1.2, 3, 1])
    with c1: back_btn('atrisk', 'back_ar_list')
    with c2:
        if st.button("+ Add More", key="ar_add"): go('atrisk'); st.rerun()

    if targets.empty:
        st.markdown(
            '<div class="banner" style="background:#FEF9C3;color:#854D0E;border-left:4px solid #EAB308;">'
            'No targets selected. Go back to browse and check the box next to customers you plan to call.</div>',
            unsafe_allow_html=True); return

    c1, c2 = st.columns([1.5, 3])
    with c1: hide_cd = st.checkbox("Hide called", key="hc_ar")
    with c2: search  = st.text_input("", placeholder="Search...", key="s_ar_list",
                                      label_visibility="collapsed")
    if search:  targets = targets[targets['customer'].str.contains(search, case=False, na=False)]
    if hide_cd: targets = targets[~targets['_cd']]
    st.caption(f"{len(targets)} targeted | {cd_ct} called")

    WS = [0.45, 0.45, 2.8, 1.2, 1.0, 1.0, 2.2]
    col_heads(WS, ['CALLED', 'F/U', 'CUSTOMER', '3-YR REV', '2024 REV', 'MONTHS', 'NOTES'])

    for _, r in targets.iterrows():
        cid  = str(r['customer']).strip(); lk = f"atrisk_{cid}"
        e    = log.get(lk, {})
        ic   = e.get('called', False); ifu = e.get('followup', False); sn = e.get('notes', '')
        acct = str(r.get('acct','')).split('.')[0] if pd.notna(r.get('acct','')) else ''
        lp   = str(r.get('last_purchase',''))[:10] if pd.notna(r.get('last_purchase','')) else ''

        cols = st.columns(WS)
        with cols[0]: nc  = st.checkbox("", value=ic,  key=f"c_{lk}", label_visibility="collapsed")
        with cols[1]: nfu = st.checkbox("", value=ifu, key=f"f_{lk}", label_visibility="collapsed")
        with cols[2]:
            st.markdown(f'<div class="cname">{cid}</div>', unsafe_allow_html=True)
            if acct: st.markdown(f'<div class="csub">Acct {acct} · Last: {lp}</div>', unsafe_allow_html=True)
        with cols[3]: st.markdown(f'<div class="cval">{fmt_rev(r.get("decline_amount",0))}</div>', unsafe_allow_html=True)
        with cols[4]: st.markdown(f'<div class="cval">{fmt_rev(r.get("rev_2024",0))}</div>', unsafe_allow_html=True)
        with cols[5]: st.markdown(f'<div class="cval">{fmt_mo(r.get("months_gone",0))} mo</div>', unsafe_allow_html=True)
        with cols[6]: nn = st.text_input("", value=sn, key=f"n_{lk}",
                                          label_visibility="collapsed", placeholder="Notes...")

        if nc != ic or nfu != ifu or nn != sn:
            e.update({'called': nc, 'followup': nfu, 'notes': nn, 'targeted': True,
                      'customer_name': cid, 'branch_name': dbr,
                      'user': gun(), 'date_updated': datetime.now().strftime('%Y-%m-%d %H:%M')})
            save_entry(lk, e)
            if nc != ic: st.rerun()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =============================================================================
# RECOVERY — BROWSE
# =============================================================================

def show_recovery_browse():
    df = load_recovery()
    if df.empty:
        st.error("No recovery data."); back_btn('cards', 'back_rec_empty'); return

    dbr = gbn(); log = st.session_state.call_log

    c1, c2, c3, c4 = st.columns([2, 2, 2.5, 0.8])
    with c1:
        opts = ["All Branches"] + sorted(df['branch'].dropna().unique().tolist())
        sel  = st.selectbox("Branch", opts, index=opts.index(dbr) if dbr in opts else 0,
                             key="br_rec", label_visibility="collapsed")
        if sel != "All Branches": dbr = sel
    with c2:
        filt = st.selectbox("Filter", ["All", "13–18 months", "19–30 months"],
                             key="filt_rec", label_visibility="collapsed")
    with c3:
        search = st.text_input("Search", placeholder="Search customer...",
                                key="s_rec", label_visibility="collapsed")
    with c4:
        back_btn('cards', 'back_rec')

    f = df[df['branch'] == dbr].copy()
    if filt == "13–18 months": f = f[f['months_gone'] <= 18]
    elif filt == "19–30 months": f = f[f['months_gone'] > 18]
    if search: f = f[f['customer'].str.contains(search, case=False, na=False)]

    f['_tg'] = f['customer'].apply(lambda x: log.get(f"recovery_{x}", {}).get('targeted', False))
    f = f.sort_values(['_tg','decline_amount'], ascending=[False, False])

    tg_ct   = int(f['_tg'].sum())
    br_all  = df[df['branch'] == dbr]
    recent  = len(br_all[br_all['months_gone'] <= 18])

    hbar("Recovery — Browse", f"{dbr} |")

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown(
            f'<div class="banner" style="background:#FEF2F2;color:#991B1B;border-left:4px solid #DC2626;">'
            f'<strong>{len(br_all)} customers</strong> lost 13–30 months ago — '
            f'<strong>{recent}</strong> within the last 18 months. '
            f'Select who you plan to call, then open your target list.</div>',
            unsafe_allow_html=True)
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        lbl = f"My Target List ({tg_ct})" if tg_ct > 0 else "My Target List"
        if st.button(lbl, use_container_width=True,
                     type="primary" if tg_ct > 0 else "secondary", key="goto_rec_list"):
            go('recovery_list'); st.rerun()

    st.caption(f"{len(f)} shown")
    WS = [0.4, 2.8, 1.3, 1.1, 1.3]
    col_heads(WS, ['SELECT', 'CUSTOMER', '3-YR REVENUE', 'MONTHS GONE', 'LAST PURCHASE'])

    for _, r in f.head(150).iterrows():
        cid  = str(r['customer']).strip(); lk = f"recovery_{cid}"
        e    = log.get(lk, {}); it = e.get('targeted', False)
        acct = str(r.get('acct','')).split('.')[0] if pd.notna(r.get('acct','')) else ''
        lp   = str(r.get('last_purchase',''))[:10] if pd.notna(r.get('last_purchase','')) else ''

        if it: st.markdown('<div class="tgt-bg">', unsafe_allow_html=True)
        cols = st.columns(WS)
        with cols[0]:
            nt = st.checkbox("", value=it, key=f"t_{lk}", label_visibility="collapsed")
        with cols[1]:
            st.markdown(f'<div class="cname">{cid}</div>', unsafe_allow_html=True)
            if acct: st.markdown(f'<div class="csub">Acct {acct}</div>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f'<div class="cval">{fmt_rev(r.get("decline_amount",0))}</div>', unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f'<div class="cval">{fmt_mo(r.get("months_gone",0))} mo</div>', unsafe_allow_html=True)
        with cols[4]:
            st.markdown(f'<div class="cval">{lp}</div>', unsafe_allow_html=True)
        if it: st.markdown('</div>', unsafe_allow_html=True)

        if nt != it:
            target_toggle(lk, nt, cid, dbr); st.rerun()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =============================================================================
# RECOVERY — TARGET LIST
# =============================================================================

def show_recovery_list():
    df = load_recovery(); dbr = gbn(); log = st.session_state.call_log

    f = df[df['branch'] == dbr].copy() if not df.empty else pd.DataFrame()
    f['_tg'] = f['customer'].apply(lambda x: log.get(f"recovery_{x}", {}).get('targeted', False))
    f['_cd'] = f['customer'].apply(lambda x: log.get(f"recovery_{x}", {}).get('called',   False))
    targets  = f[f['_tg']].sort_values(['_cd','decline_amount'], ascending=[False, False])

    tg_ct = len(targets); cd_ct = int(targets['_cd'].sum()) if tg_ct > 0 else 0
    hbar("Recovery — My Target List", f"{dbr} | {cd_ct}/{tg_ct} called |")

    c1, _, c2 = st.columns([1.2, 3, 1])
    with c1: back_btn('recovery', 'back_rec_list')
    with c2:
        if st.button("+ Add More", key="rec_add"): go('recovery'); st.rerun()

    if targets.empty:
        st.markdown(
            '<div class="banner" style="background:#FEF9C3;color:#854D0E;border-left:4px solid #EAB308;">'
            'No targets selected. Go back to browse and check the box next to customers you plan to call.</div>',
            unsafe_allow_html=True); return

    c1, c2 = st.columns([1.5, 3])
    with c1: hide_cd = st.checkbox("Hide called", key="hc_rec")
    with c2: search  = st.text_input("", placeholder="Search...", key="s_rec_list",
                                      label_visibility="collapsed")
    if search:  targets = targets[targets['customer'].str.contains(search, case=False, na=False)]
    if hide_cd: targets = targets[~targets['_cd']]
    st.caption(f"{len(targets)} targeted | {cd_ct} called")

    WS = [0.45, 0.45, 2.8, 1.2, 1.0, 1.0, 2.2]
    col_heads(WS, ['CALLED', 'F/U', 'CUSTOMER', '3-YR REV', '2024 REV', 'MONTHS', 'NOTES'])

    for _, r in targets.iterrows():
        cid  = str(r['customer']).strip(); lk = f"recovery_{cid}"
        e    = log.get(lk, {})
        ic   = e.get('called', False); ifu = e.get('followup', False); sn = e.get('notes', '')
        acct = str(r.get('acct','')).split('.')[0] if pd.notna(r.get('acct','')) else ''
        lp   = str(r.get('last_purchase',''))[:10] if pd.notna(r.get('last_purchase','')) else ''

        cols = st.columns(WS)
        with cols[0]: nc  = st.checkbox("", value=ic,  key=f"c_{lk}", label_visibility="collapsed")
        with cols[1]: nfu = st.checkbox("", value=ifu, key=f"f_{lk}", label_visibility="collapsed")
        with cols[2]:
            st.markdown(f'<div class="cname">{cid}</div>', unsafe_allow_html=True)
            if acct: st.markdown(f'<div class="csub">Acct {acct} · Last: {lp}</div>', unsafe_allow_html=True)
        with cols[3]: st.markdown(f'<div class="cval">{fmt_rev(r.get("decline_amount",0))}</div>', unsafe_allow_html=True)
        with cols[4]: st.markdown(f'<div class="cval">{fmt_rev(r.get("rev_2024",0))}</div>', unsafe_allow_html=True)
        with cols[5]: st.markdown(f'<div class="cval">{fmt_mo(r.get("months_gone",0))} mo</div>', unsafe_allow_html=True)
        with cols[6]: nn = st.text_input("", value=sn, key=f"n_{lk}",
                                          label_visibility="collapsed", placeholder="Notes...")

        if nc != ic or nfu != ifu or nn != sn:
            e.update({'called': nc, 'followup': nfu, 'notes': nn, 'targeted': True,
                      'customer_name': cid, 'branch_name': dbr,
                      'user': gun(), 'date_updated': datetime.now().strftime('%Y-%m-%d %H:%M')})
            save_entry(lk, e)
            if nc != ic: st.rerun()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =============================================================================
# CONQUEST — BROWSE
# =============================================================================

def show_conquest_browse():
    df = load_conquest()
    if df.empty:
        st.error("No conquest data."); back_btn('cards', 'back_cq_empty'); return

    dbr = gbn(); log = st.session_state.call_log

    c1, c2, c3, c4 = st.columns([2, 2, 2.5, 0.8])
    with c1:
        opts = ["All Branches"] + sorted(df['branch'].dropna().unique().tolist())
        sel  = st.selectbox("Branch", opts, index=opts.index(dbr) if dbr in opts else 0,
                             key="br_cq", label_visibility="collapsed")
        if sel != "All Branches": dbr = sel
    with c2:
        filt = st.selectbox("Filter", ["All", "Tier 1 & 2", "SE History", "Tier 3 & 4"],
                             key="filt_cq", label_visibility="collapsed")
    with c3:
        search = st.text_input("Search", placeholder="Search company...",
                                key="s_cq", label_visibility="collapsed")
    with c4:
        back_btn('cards', 'back_cq')

    f = df[df['branch'] == dbr].copy()
    if filt == "Tier 1 & 2":  f = f[f['tier'] <= 2]
    elif filt == "SE History": f = f[f['sn_match'] == True]
    elif filt == "Tier 3 & 4": f = f[f['tier'] >= 3]
    if search: f = f[f['company'].str.contains(search, case=False, na=False)]

    f['_tg'] = f['company'].apply(lambda x: log.get(f"conquest_{x}", {}).get('targeted', False))
    f = f.sort_values(['_tg','tier','score'], ascending=[False, True, False])

    tg_ct = int(f['_tg'].sum())
    br_all = df[df['branch'] == dbr]
    t12    = len(br_all[br_all['tier'] <= 2])

    hbar("Conquest — Browse", f"{dbr} |")

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown(
            f'<div class="banner" style="background:#F5F3FF;color:#5B21B6;border-left:4px solid #7C3AED;">'
            f'<strong>{len(br_all)} prospects</strong> — <strong>{t12} priority</strong> (Tier 1 & 2). '
            f'Tier 1 leads are companies SE has previously serviced equipment for. '
            f'Select who you plan to call, then open your target list.</div>',
            unsafe_allow_html=True)
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        lbl = f"My Target List ({tg_ct})" if tg_ct > 0 else "My Target List"
        if st.button(lbl, use_container_width=True,
                     type="primary" if tg_ct > 0 else "secondary", key="goto_cq_list"):
            go('conquest_list'); st.rerun()

    st.caption(f"{len(f)} shown")
    WS = [0.4, 0.55, 2.8, 1.9, 0.75, 1.1]
    col_heads(WS, ['SELECT', 'TIER', 'COMPANY', 'MAKES / UNITS', 'SCORE', 'SE HISTORY'])

    for _, r in f.head(150).iterrows():
        cid   = str(r['company']).strip(); lk = f"conquest_{cid}"
        e     = log.get(lk, {}); it = e.get('targeted', False)
        tier  = int(r.get('tier', 4))
        score = int(r.get('score', 0)) if pd.notna(r.get('score')) else 0
        makes = str(r.get('makes','')).strip(); makes = makes if makes and makes != 'nan' else ''
        units = int(r['units']) if pd.notna(r.get('units')) else 0
        equip = f"{makes} · {units} units" if makes else f"{units} units"
        city  = str(r.get('city','')).strip(); state = str(r.get('state','')).strip()
        loc   = f"{city}, {state}" if city and city!='nan' and state and state!='nan' else ''
        hr    = r.get('hist_revenue', 0)
        se_h  = fmt_rev(hr) if pd.notna(hr) and float(hr) > 0 else '—'
        tlbl, tcls = TIER_LABELS.get(tier, ('T4','b-gray'))

        if it: st.markdown('<div class="tgt-bg">', unsafe_allow_html=True)
        cols = st.columns(WS)
        with cols[0]:
            nt = st.checkbox("", value=it, key=f"t_{lk}", label_visibility="collapsed")
        with cols[1]:
            st.markdown(f'<span class="badge {tcls}">{tlbl}</span>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f'<div class="cname">{cid}</div>', unsafe_allow_html=True)
            if loc: st.markdown(f'<div class="csub">{loc}</div>', unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f'<div class="cval">{equip}</div>', unsafe_allow_html=True)
        with cols[4]:
            st.markdown(f'<div class="cval">{score}</div>', unsafe_allow_html=True)
        with cols[5]:
            st.markdown(f'<div class="cval">{se_h}</div>', unsafe_allow_html=True)
        if it: st.markdown('</div>', unsafe_allow_html=True)

        if nt != it:
            target_toggle(lk, nt, cid, dbr); st.rerun()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =============================================================================
# CONQUEST — TARGET LIST
# =============================================================================

def show_conquest_list():
    df = load_conquest(); dbr = gbn(); log = st.session_state.call_log

    f = df[df['branch'] == dbr].copy() if not df.empty else pd.DataFrame()
    f['_tg'] = f['company'].apply(lambda x: log.get(f"conquest_{x}", {}).get('targeted', False))
    f['_cd'] = f['company'].apply(lambda x: log.get(f"conquest_{x}", {}).get('called',   False))
    targets  = f[f['_tg']].sort_values(['_cd','tier','score'], ascending=[False, True, False])

    tg_ct = len(targets); cd_ct = int(targets['_cd'].sum()) if tg_ct > 0 else 0
    hbar("Conquest — My Target List", f"{dbr} | {cd_ct}/{tg_ct} called |")

    c1, _, c2 = st.columns([1.2, 3, 1])
    with c1: back_btn('conquest', 'back_cq_list')
    with c2:
        if st.button("+ Add More", key="cq_add"): go('conquest'); st.rerun()

    if targets.empty:
        st.markdown(
            '<div class="banner" style="background:#FEF9C3;color:#854D0E;border-left:4px solid #EAB308;">'
            'No targets selected. Go back to browse and check the box next to prospects you plan to call.</div>',
            unsafe_allow_html=True); return

    c1, c2 = st.columns([1.5, 3])
    with c1: hide_cd = st.checkbox("Hide called", key="hc_cq")
    with c2: search  = st.text_input("", placeholder="Search...", key="s_cq_list",
                                      label_visibility="collapsed")
    if search:  targets = targets[targets['company'].str.contains(search, case=False, na=False)]
    if hide_cd: targets = targets[~targets['_cd']]
    st.caption(f"{len(targets)} targeted | {cd_ct} called")

    WS = [0.45, 0.45, 0.55, 2.8, 1.6, 1.0, 2.2]
    col_heads(WS, ['CALLED', 'F/U', 'TIER', 'COMPANY', 'MAKES / UNITS', 'SE HISTORY', 'NOTES'])

    for _, r in targets.iterrows():
        cid   = str(r['company']).strip(); lk = f"conquest_{cid}"
        e     = log.get(lk, {})
        ic    = e.get('called', False); ifu = e.get('followup', False); sn = e.get('notes', '')
        tier  = int(r.get('tier', 4))
        makes = str(r.get('makes','')).strip(); makes = makes if makes and makes != 'nan' else ''
        units = int(r['units']) if pd.notna(r.get('units')) else 0
        equip = f"{makes} · {units} units" if makes else f"{units} units"
        ph    = str(r.get('phone','')).strip()
        ph    = ph if len(ph) >= 7 and ph not in ('nan','0','0.0') else ''
        ct    = str(r.get('contact','')).strip()
        ct    = ct if ct and ct not in ('nan nan','nan','') else ''
        city  = str(r.get('city','')).strip(); state = str(r.get('state','')).strip()
        loc   = f"{city}, {state}" if city and city!='nan' and state and state!='nan' else ''
        sub   = " | ".join([s for s in [ct, ph, loc] if s][:2])
        hr    = r.get('hist_revenue', 0)
        se_h  = fmt_rev(hr) if pd.notna(hr) and float(hr) > 0 else '—'
        tlbl, tcls = TIER_LABELS.get(tier, ('T4','b-gray'))

        cols = st.columns(WS)
        with cols[0]: nc  = st.checkbox("", value=ic,  key=f"c_{lk}", label_visibility="collapsed")
        with cols[1]: nfu = st.checkbox("", value=ifu, key=f"f_{lk}", label_visibility="collapsed")
        with cols[2]: st.markdown(f'<span class="badge {tcls}">{tlbl}</span>', unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f'<div class="cname">{cid}</div>', unsafe_allow_html=True)
            if sub: st.markdown(f'<div class="csub">{sub}</div>', unsafe_allow_html=True)
        with cols[4]: st.markdown(f'<div class="cval">{equip}</div>', unsafe_allow_html=True)
        with cols[5]: st.markdown(f'<div class="cval">{se_h}</div>', unsafe_allow_html=True)
        with cols[6]: nn = st.text_input("", value=sn, key=f"n_{lk}",
                                          label_visibility="collapsed", placeholder="Notes...")

        if nc != ic or nfu != ifu or nn != sn:
            e.update({'called': nc, 'followup': nfu, 'notes': nn, 'targeted': True,
                      'customer_name': cid, 'branch_name': dbr,
                      'user': gun(), 'date_updated': datetime.now().strftime('%Y-%m-%d %H:%M')})
            save_entry(lk, e)
            if nc != ic: st.rerun()
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =============================================================================
# ADMIN
# =============================================================================

def show_admin():
    hbar("Admin — Call Log")
    back_btn('cards', 'back_admin')
    log = st.session_state.call_log
    if not log:
        st.info("No entries yet."); return
    rows = [{'key': k, 'customer': e.get('customer_name',''), 'branch': e.get('branch_name',''),
             'targeted': e.get('targeted',False), 'called': e.get('called',False),
             'followup': e.get('followup',False), 'notes': e.get('notes',''),
             'user': e.get('user',''), 'date': e.get('date_updated','')}
            for k, e in log.items()]
    adf = pd.DataFrame(rows)
    st.dataframe(adf, use_container_width=True)
    st.download_button("Download", adf.to_csv(index=False),
                        f"outreach_log_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

# =============================================================================
# ROUTER
# =============================================================================

page = st.session_state.page

if   page == 'login':         show_login()
elif page == 'cards':         show_cards()
elif page == 'atrisk':        show_atrisk_browse()
elif page == 'atrisk_list':   show_atrisk_list()
elif page == 'recovery':      show_recovery_browse()
elif page == 'recovery_list': show_recovery_list()
elif page == 'conquest':      show_conquest_browse()
elif page == 'conquest_list': show_conquest_list()
elif page == 'admin':         show_admin()
else:
    go('login'); st.rerun()
