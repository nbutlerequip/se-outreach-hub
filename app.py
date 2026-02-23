"""
Southeastern Equipment - Customer Outreach Hub
2026

Login → Campaign Cards → Call Lists
Admin Dashboard for leadership visibility
Call log persists to Google Sheets
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
from collections import Counter

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

st.set_page_config(page_title="SE Customer Outreach", page_icon="SE", layout="wide", initial_sidebar_state="collapsed")

APP_DIR = Path(__file__).parent
SE_MAROON = "#A41E35"
SE_DARK = "#7a1528"

BRANCHES = {
    1:"Cambridge",2:"North Canton",3:"Gallipolis",4:"Dublin",5:"Monroe",6:"Burlington",
    7:"Perrysburg",9:"Brunswick",11:"Mentor",12:"Fort Wayne",13:"Indianapolis",14:"Mansfield",
    15:"Heath",16:"Marietta",17:"Evansville",18:"Brilliant",19:"Holt",20:"Novi",24:"South Charleston"
}
MONTH_NAMES = {1:'January',2:'February',3:'March',4:'April',5:'May',6:'June',
               7:'July',8:'August',9:'September',10:'October',11:'November',12:'December'}

# =============================================================================
# GOOGLE SHEETS CONNECTION
# =============================================================================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=300)
def get_gsheet_connection():
    """Create authenticated gspread client. Cached 5 min."""
    if not GSHEETS_AVAILABLE:
        return None, None
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet_url = st.secrets.get("sheet_url", "")
        if sheet_url:
            sh = client.open_by_url(sheet_url)
        else:
            sheet_name = st.secrets.get("sheet_name", "SE Outreach Call Log")
            try:
                sh = client.open(sheet_name)
            except gspread.SpreadsheetNotFound:
                sh = client.create(sheet_name)
                sh.share(None, perm_type='anyone', role='writer')
        # Ensure call_log worksheet exists with headers
        try:
            ws = sh.worksheet("call_log")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="call_log", rows=5000, cols=9)
            ws.append_row(["log_key", "customer_name", "branch_name", "called",
                           "followup", "notes", "user", "date_updated", "campaign"])
        return client, sh
    except Exception as e:
        st.sidebar.warning(f"Google Sheets connection failed: {e}")
        return None, None

def load_call_log_gsheets(sh):
    """Load all call log entries from Google Sheets into a dict."""
    try:
        ws = sh.worksheet("call_log")
        records = ws.get_all_records()
        log = {}
        for r in records:
            key = r.get("log_key", "")
            if not key:
                continue
            log[key] = {
                "customer_name": r.get("customer_name", ""),
                "branch_name": r.get("branch_name", ""),
                "called": str(r.get("called", "")).lower() == "true",
                "followup": str(r.get("followup", "")).lower() == "true",
                "notes": r.get("notes", ""),
                "user": r.get("user", ""),
                "date_updated": r.get("date_updated", ""),
            }
        return log
    except Exception:
        return {}

def save_entry_gsheets(sh, log_key, entry):
    """Save or update a single call log entry in Google Sheets."""
    try:
        ws = sh.worksheet("call_log")
        campaign = log_key.split("_")[0]
        if "conquest" in log_key:
            campaign = "conquest"
        row_data = [
            log_key,
            entry.get("customer_name", ""),
            entry.get("branch_name", ""),
            str(entry.get("called", False)),
            str(entry.get("followup", False)),
            entry.get("notes", ""),
            entry.get("user", ""),
            entry.get("date_updated", ""),
            campaign
        ]
        # Try to find existing row
        try:
            cell = ws.find(log_key, in_column=1)
            if cell:
                ws.update(f"A{cell.row}:I{cell.row}", [row_data])
                return
        except gspread.exceptions.CellNotFound:
            pass
        # Append new row
        ws.append_row(row_data, value_input_option="RAW")
    except Exception as e:
        st.toast(f"Save error: {e}", icon="warning")

def delete_entry_gsheets(sh, log_key):
    """Delete a call log entry from Google Sheets."""
    try:
        ws = sh.worksheet("call_log")
        cell = ws.find(log_key, in_column=1)
        if cell:
            ws.delete_rows(cell.row)
    except Exception:
        pass

# =============================================================================
# FALLBACK: LOCAL JSON (if no Google Sheets)
# =============================================================================

CALL_LOG_FILE = APP_DIR / "call_log.json"

def load_call_log_local():
    if CALL_LOG_FILE.exists():
        try:
            with open(CALL_LOG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_call_log_local(log):
    with open(CALL_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2, default=str)

# =============================================================================
# UNIFIED CALL LOG INTERFACE
# =============================================================================

def init_call_log():
    """Initialize call log - from Google Sheets if available, else local JSON."""
    if "call_log" not in st.session_state or st.session_state.call_log is None:
        _, sh = get_gsheet_connection()
        if sh:
            st.session_state.call_log = load_call_log_gsheets(sh)
            st.session_state.gsheets_active = True
        else:
            st.session_state.call_log = load_call_log_local()
            st.session_state.gsheets_active = False

def save_entry(log_key, entry):
    """Save a single entry to the active backend."""
    st.session_state.call_log[log_key] = entry
    if st.session_state.get("gsheets_active"):
        _, sh = get_gsheet_connection()
        if sh:
            save_entry_gsheets(sh, log_key, entry)
    else:
        save_call_log_local(st.session_state.call_log)

def delete_entry(log_key):
    """Delete an entry from the active backend."""
    if log_key in st.session_state.call_log:
        del st.session_state.call_log[log_key]
    if st.session_state.get("gsheets_active"):
        _, sh = get_gsheet_connection()
        if sh:
            delete_entry_gsheets(sh, log_key)
    else:
        save_call_log_local(st.session_state.call_log)

def refresh_log():
    """Force refresh from Google Sheets."""
    _, sh = get_gsheet_connection()
    if sh:
        st.session_state.call_log = load_call_log_gsheets(sh)

# =============================================================================
# STYLES
# =============================================================================

st.markdown(f"""
<style>
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
    .stDeployButton {{display: none;}} header {{visibility: hidden;}}
    div[data-testid="stFooter"] {{ display: none; }}
    .main .block-container {{ padding-top: 0; padding-bottom: 2rem; max-width: 1400px; }}
    .login-container {{ text-align: center; padding: 50px 20px 30px; }}
    .login-title {{ color: {SE_MAROON}; font-size: 32px; font-weight: 600; margin-bottom: 4px; }}
    .login-subtitle {{ color: #666; font-size: 16px; margin-bottom: 4px; }}
    .login-detail {{ color: #999; font-size: 13px; margin-bottom: 36px; }}
    .header-bar {{ background: {SE_MAROON}; color: white; padding: 14px 24px; margin: -1rem -1rem 1.2rem -1rem; display: flex; justify-content: space-between; align-items: center; font-size: 14px; }}
    .header-bar .page-title {{ font-weight: 600; font-size: 16px; }}
    .header-bar .page-info {{ font-size: 13px; opacity: 0.9; }}
    .cards-title {{ font-size: 22px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }}
    .cards-sub {{ color: #64748b; font-size: 13px; margin-bottom: 20px; }}
    .kpi-card {{ border-radius: 8px; padding: 18px 20px; margin-bottom: 8px; cursor: pointer; transition: box-shadow 0.15s; }}
    .kpi-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.12); }}
    .kpi-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; opacity: 0.85; margin-bottom: 8px; }}
    .kpi-row {{ display: flex; justify-content: space-between; align-items: flex-end; }}
    .kpi-big {{ font-size: 28px; font-weight: 700; line-height: 1; }}
    .kpi-right {{ text-align: right; }}
    .kpi-called {{ font-size: 13px; font-weight: 500; opacity: 0.85; }}
    .kpi-pct {{ font-size: 18px; font-weight: 700; }}
    .kpi-bar {{ height: 3px; border-radius: 2px; margin-top: 10px; overflow: hidden; }}
    .kpi-bar-fill {{ height: 100%; border-radius: 2px; }}
    .info-banner {{ padding: 10px 16px; border-radius: 6px; font-size: 13px; margin-bottom: 12px; }}
    .tip-banner {{ background: #fff3cd; color: #856404; padding: 8px 14px; border-radius: 4px; font-size: 12px; margin-bottom: 14px; }}
    .col-header {{ font-weight: 600; font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; margin-bottom: 8px; }}
    .customer-name {{ font-weight: 600; font-size: 14px; color: #1e293b; }}
    .customer-sub {{ font-size: 12px; color: #94a3b8; }}
    .cell-text {{ font-size: 13px; color: #475569; }}
    .empty-cell {{ color: #cbd5e1; font-style: italic; }}
    .row-divider {{ border-bottom: 1px solid #f1f5f9; margin: 6px 0; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
    .badge-hot {{ background: #FEE2E2; color: #991B1B; }}
    .badge-warm {{ background: #FEF3C7; color: #92400E; }}
    .badge-cool {{ background: #DBEAFE; color: #1E40AF; }}
    .badge-urgent {{ background: #FEE2E2; color: #991B1B; }}
    .badge-early {{ background: #FEF3C7; color: #92400E; }}
    .badge-internal {{ background: #E0E7FF; color: #3730A3; }}
    .badge-checkin {{ background: #ECFDF5; color: #065F46; }}
    .badge-reactivate {{ background: #F3E8FF; color: #6B21A8; }}
    .admin-metric {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; text-align: center; }}
    .admin-num {{ font-size: 28px; font-weight: 700; color: #1e293b; }}
    .admin-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
    .stButton > button {{ background: {SE_MAROON}; color: white; border: none; font-weight: 500; }}
    .stButton > button:hover {{ background: {SE_DARK}; color: white; }}
    .gs-status {{ font-size: 11px; padding: 4px 10px; border-radius: 12px; display: inline-block; }}
    .gs-on {{ background: #ECFDF5; color: #065F46; }}
    .gs-off {{ background: #FEF2F2; color: #991B1B; }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA LOADERS
# =============================================================================

@st.cache_data
def load_recovery():
    try: return pd.read_csv(APP_DIR / "data_recovery.csv")
    except: return pd.DataFrame()
@st.cache_data
def load_conquest_sn():
    try: return pd.read_csv(APP_DIR / "data_conquest_sn.csv")
    except: return pd.DataFrame()
@st.cache_data
def load_conquest_eda():
    try: return pd.read_csv(APP_DIR / "data_conquest_eda.csv")
    except: return pd.DataFrame()
@st.cache_data
def load_parts():
    try: return pd.read_csv(APP_DIR / "data_parts_campaign.csv")
    except: return pd.DataFrame()
@st.cache_data
def load_service():
    try: return pd.read_csv(APP_DIR / "data_service_seasonality.csv")
    except: return pd.DataFrame()
@st.cache_data
def load_consignment():
    try: return pd.read_csv(APP_DIR / "data_consignment.csv")
    except: return pd.DataFrame()

def gbn(): return BRANCHES.get(st.session_state.get('branch'), 'Unknown')
def gun(): return st.session_state.get('user_name', '')

# =============================================================================
# SESSION STATE
# =============================================================================

for key, default in [('page','login'),('branch',None),('user_name',''),
                     ('campaign_month',datetime.now().month),('call_log',None),
                     ('gsheets_active',False)]:
    if key not in st.session_state:
        st.session_state[key] = default

init_call_log()

def go(p): st.session_state.page = p

# =============================================================================
# HELPERS
# =============================================================================

def count_called(df, id_col, prefix):
    t=len(df); c=f=0
    log = st.session_state.call_log
    for _,r in df.iterrows():
        e=log.get(f"{prefix}_{r[id_col]}",{})
        if e.get('called'): c+=1
        if e.get('followup'): f+=1
    return t,c,f

def render_row(cid, cname, col_data, prefix, br=None, extra_badge=''):
    lk=f"{prefix}_{cid}"
    log = st.session_state.call_log
    e=log.get(lk,{})
    ic=e.get('called',False); ifu=e.get('followup',False); sn=e.get('notes','')
    cols=st.columns([0.5,0.5,2.8,1.3,1.2,2.5])
    with cols[0]: nc=st.checkbox("",value=ic,key=f"c_{lk}",label_visibility="collapsed")
    with cols[1]: nf=st.checkbox("",value=ifu,key=f"f_{lk}",label_visibility="collapsed")
    for i,(_,v) in enumerate(col_data[:3]):
        with cols[2+i]:
            if i==0:
                st.markdown(f'<div class="customer-name">{cname}{extra_badge}</div>',unsafe_allow_html=True)
                if v: st.markdown(f'<div class="customer-sub">{v}</div>',unsafe_allow_html=True)
            else:
                if v: st.markdown(f'<div class="cell-text">{v}</div>',unsafe_allow_html=True)
                else: st.markdown('<div class="empty-cell">—</div>',unsafe_allow_html=True)
    with cols[5]: nn=st.text_input("",value=sn,key=f"n_{lk}",label_visibility="collapsed",placeholder="Add notes...")
    if nc!=ic or nf!=ifu or nn!=sn:
        if nc or nf or nn:
            entry = {'customer_name':cname,'branch_name':br or gbn(),'called':nc,
                     'followup':nf,'notes':nn,'user':gun(),
                     'date_updated':datetime.now().strftime('%Y-%m-%d %H:%M')}
            save_entry(lk, entry)
        else:
            delete_entry(lk)
        if nc!=ic: st.rerun()
    st.markdown('<div class="row-divider"></div>',unsafe_allow_html=True)

def cbar(title,branch,total,called,fu):
    gs = '<span class="gs-status gs-on">Sheets Connected</span>' if st.session_state.gsheets_active else '<span class="gs-status gs-off">Local Mode</span>'
    st.markdown(f'<div class="header-bar"><span class="page-title">{title} — {branch}</span><span class="page-info">{called} of {total} Called | {fu} Follow-ups | {gun()} {gs}</span></div>',unsafe_allow_html=True)

def cheaders(labels):
    cols=st.columns([0.5,0.5,2.8,1.3,1.2,2.5])
    for i,l in enumerate(labels): cols[i].markdown(f'<div class="col-header">{l}</div>',unsafe_allow_html=True)

def fbar(key, blist, show_month=False):
    if show_month: c1,c2,c3,c4,c5=st.columns([2,1.5,2,1.5,1])
    else: c1,c2,c3,c4=st.columns([2.5,2.5,1.5,1])
    with c1:
        opts=["All Branches"]+sorted(set(blist)); ubr=gbn()
        idx=opts.index(ubr) if ubr in opts else 0
        br=st.selectbox("Branch",opts,index=idx,key=f"br_{key}",label_visibility="collapsed")
        br=None if br=="All Branches" else br
    mo=None
    if show_month:
        with c2:
            mopts=list(MONTH_NAMES.values())
            sel=st.selectbox("Month",mopts,index=st.session_state.campaign_month-1,key=f"mo_{key}",label_visibility="collapsed")
            mo=mopts.index(sel)+1
    sc=c3 if show_month else c2; hc=c4 if show_month else c3; bc=c5 if show_month else c4
    with sc: s=st.text_input("Search",placeholder="Search customer...",label_visibility="collapsed",key=f"s_{key}")
    with hc: h=st.checkbox("Hide called",value=True,key=f"h_{key}")
    with bc:
        if st.button("← Back",key=f"back_{key}"): go('cards'); st.rerun()
    return br,s,h,mo

# =============================================================================
# LOGIN
# =============================================================================

def show_login():
    st.markdown('<div class="login-container"><div class="login-title">Customer Outreach</div><div class="login-subtitle">Q1 2026</div><div class="login-detail">Recovery | Conquest | Parts | Service | Consignment</div></div>',unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1.5,1])
    with c2:
        name=st.text_input("Your Name",placeholder="Enter your name...",key="login_name")
        opts=["Select your branch..."]; bmap={}
        for n,b in sorted(BRANCHES.items()): l=f"{n} - {b}"; opts.append(l); bmap[l]=n
        sel=st.selectbox("Branch",opts,key="login_branch",label_visibility="collapsed")
        mopts=list(MONTH_NAMES.values()); cm=datetime.now().month
        sm=st.selectbox("Campaign Month",mopts,index=cm-1,key="login_month")
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button("Start Outreach",use_container_width=True,type="primary"):
            if sel!="Select your branch..." and name.strip():
                st.session_state.branch=bmap[sel]; st.session_state.user_name=name.strip()
                st.session_state.campaign_month=mopts.index(sm)+1; go('cards'); st.rerun()
            else: st.warning("Please enter your name and select a branch")
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button("Admin Dashboard",use_container_width=True): go('admin'); st.rerun()
        # Connection status
        gs_label = "Google Sheets Connected" if st.session_state.gsheets_active else "Local Mode (no Google Sheets)"
        gs_class = "gs-on" if st.session_state.gsheets_active else "gs-off"
        st.markdown(f'<div style="text-align:center;margin-top:20px;"><span class="gs-status {gs_class}">{gs_label}</span></div>',unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;color:#999;font-size:11px;margin-top:40px;">Created by Nick Butler | Southeastern Equipment</div>',unsafe_allow_html=True)

# =============================================================================
# CARDS
# =============================================================================

def show_cards():
    branch_name=gbn(); user=gun(); month_name=MONTH_NAMES.get(st.session_state.campaign_month,'')
    gs = ' | Sheets Connected' if st.session_state.gsheets_active else ''
    st.markdown(f'<div class="header-bar"><span class="page-title">Customer Outreach Hub</span><span class="page-info">{branch_name}  |  {month_name}  |  {user}{gs}</span></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="cards-title">Welcome, {user}</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="cards-sub">Showing targets for {branch_name}. Select a campaign below.</div>',unsafe_allow_html=True)

    rec=load_recovery(); sn=load_conquest_sn(); eda=load_conquest_eda()
    pts=load_parts(); svc=load_service(); con=load_consignment()
    log=st.session_state.call_log

    def lc(prefix,df,id_col):
        return sum(1 for _,r in df.iterrows() if log.get(f"{prefix}_{r[id_col]}",{}).get('called'))

    rb=rec[rec['branch']==branch_name]; snb=sn[sn['branch']==branch_name]; eb=eda[eda['branch']==branch_name]
    pb=pts[pts['BranchName']==branch_name]; sb=svc[(svc['branch_name']==branch_name)&(svc['target_month']==st.session_state.campaign_month)]
    cb=con[con['Branch']==branch_name]

    camps=[
        {'key':'recovery','title':'RECOVERY','color':'#DC2626','bg':'#FEF2F2','bar_bg':'#FECACA','total':len(rb),'called':lc('recovery',rb,'customer')},
        {'key':'conquest','title':'CONQUEST','color':'#7C3AED','bg':'#F5F3FF','bar_bg':'#DDD6FE','total':len(snb)+len(eb),'called':lc('conquest_sn',snb,'company')+lc('conquest_eda',eb,'company')},
        {'key':'parts','title':'PARTS CAMPAIGN','color':'#2563EB','bg':'#EFF6FF','bar_bg':'#BFDBFE','total':len(pb),'called':lc('parts',pb,'Customer')},
        {'key':'service','title':'SERVICE','color':'#059669','bg':'#ECFDF5','bar_bg':'#A7F3D0','total':len(sb),'called':lc('service',sb,'cust_acct')},
        {'key':'consignment','title':'CONSIGNMENT','color':'#D97706','bg':'#FFFBEB','bar_bg':'#FDE68A','total':len(cb),'called':lc('consignment',cb,'Account')},
    ]

    cols=st.columns(5)
    for i,c in enumerate(camps):
        with cols[i]:
            pct=int(c['called']/c['total']*100) if c['total']>0 else 0
            remaining=c['total']-c['called']
            if st.button(c['title'],key=f"card_{c['key']}",use_container_width=True):
                go(c['key']); st.rerun()
            st.markdown(f"""<div class="kpi-card" style="background:{c['bg']};">
                <div class="kpi-label" style="color:{c['color']};">{c['title']}</div>
                <div class="kpi-row">
                    <div class="kpi-big" style="color:{c['color']};">{c['total']}</div>
                    <div class="kpi-right">
                        <div class="kpi-pct" style="color:{c['color']};">{pct}%</div>
                        <div class="kpi-called" style="color:{c['color']};">{c['called']} called / {remaining} left</div>
                    </div>
                </div>
                <div class="kpi-bar" style="background:{c['bar_bg']};"><div class="kpi-bar-fill" style="width:{pct}%;background:{c['color']};"></div></div>
            </div>""",unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1,1])
    with c2:
        if st.button("Change Branch / User",use_container_width=True): go('login'); st.rerun()
    st.markdown('<div style="text-align:center;color:#94a3b8;font-size:11px;margin-top:30px;padding-top:12px;border-top:1px solid #e2e8f0;">Created by Nick Butler  |  Southeastern Equipment  |  2026</div>',unsafe_allow_html=True)

# =============================================================================
# RECOVERY
# =============================================================================

def show_recovery():
    df=load_recovery(); br,s,h,_=fbar("rec",df['branch'].unique().tolist())
    dbr=br or gbn(); f=df[df['branch']==dbr].copy()
    if s: f=f[f['customer'].str.contains(s,case=False,na=False)]
    t,c,fu=count_called(f,'customer','recovery'); cbar('Recovery',dbr,t,c,fu)
    st.markdown('<div class="info-banner" style="background:#FEF2F2;color:#991B1B;border-left:4px solid #DC2626;">Declining customers ranked by dollar opportunity. Action type guides your conversation.</div>',unsafe_allow_html=True)
    f['_c']=f['customer'].apply(lambda x:st.session_state.call_log.get(f"recovery_{x}",{}).get('called',False))
    if h: f=f[~f['_c']]
    f=f.sort_values(['_c','decline_amount'],ascending=[True,False])
    st.caption(f"{len(f)} customers"); cheaders(['Called','F/U','Customer','Action','Decline','Notes'])
    bm={'Urgent':'badge-urgent','Early Warning':'badge-early','Internal Review':'badge-internal','Check-In':'badge-checkin','Reactivate':'badge-reactivate'}
    for _,r in f.head(100).iterrows():
        cid=str(r['customer']).strip(); a=r.get('action','') or ''; bc=bm.get(a,'')
        ah=f'<span class="badge {bc}">{a}</span>' if a else '—'
        d=r.get('decline_amount',0); ds=f"${abs(d):,.0f}" if pd.notna(d) and d!=0 else "—"
        render_row(cid,cid,[("",r['branch']),("",ah),("",ds)],"recovery",dbr)

# =============================================================================
# CONQUEST
# =============================================================================

def show_conquest():
    sn=load_conquest_sn(); eda=load_conquest_eda()
    abr=sorted(set(sn['branch'].dropna().tolist()+eda['branch'].dropna().tolist()))
    c1,c2,c3,c4,c5=st.columns([1.8,1.5,2,1.5,1])
    with c1:
        opts=["All Branches"]+abr; ubr=gbn(); idx=opts.index(ubr) if ubr in opts else 0
        br=st.selectbox("Branch",opts,index=idx,key="br_conq",label_visibility="collapsed")
        br=None if br=="All Branches" else br
    with c2: view=st.selectbox("View",["All","SN Match (Warm)","EDA Tier A (Cold)"],key="conq_view",label_visibility="collapsed")
    with c3: search=st.text_input("Search",placeholder="Search...",key="s_conq",label_visibility="collapsed")
    with c4: hide=st.checkbox("Hide called",value=True,key="h_conq")
    with c5:
        if st.button("← Back",key="back_conq"): go('cards'); st.rerun()
    dbr=br or gbn(); snf=sn[sn['branch']==dbr]; ef=eda[eda['branch']==dbr]
    if search: snf=snf[snf['company'].str.contains(search,case=False,na=False)]; ef=ef[ef['company'].str.contains(search,case=False,na=False)]
    st2,sc2,sf2=count_called(snf,'company','conquest_sn'); et2,ec2,ef2=count_called(ef,'company','conquest_eda')
    cbar('Conquest',dbr,st2+et2,sc2+ec2,sf2+ef2)
    st.markdown(f'<div style="display:flex;gap:12px;margin-bottom:16px;"><div class="admin-metric" style="flex:1;"><div class="admin-num" style="color:#7C3AED;">{st2}</div><div class="admin-label">SN Match (Warm)</div></div><div class="admin-metric" style="flex:1;"><div class="admin-num" style="color:#059669;">{et2}</div><div class="admin-label">EDA Tier A (Cold)</div></div><div class="admin-metric" style="flex:1;"><div class="admin-num">{sc2+ec2}</div><div class="admin-label">Called</div></div></div>',unsafe_allow_html=True)

    if view in ["All","SN Match (Warm)"]:
        st.markdown('<div class="info-banner" style="background:#F5F3FF;color:#5B21B6;border-left:4px solid #7C3AED;"><strong>SN Match — Warm Leads.</strong> We serviced their machine under a prior owner. Opener: "We see you have a [machine]. We have actually worked on that unit before."</div>',unsafe_allow_html=True)
        cheaders(['Called','F/U','Company','Heat / Fleet','Revenue','Notes'])
        sns=snf.sort_values('heat_score',ascending=False)
        if hide: sns=sns[~sns['company'].apply(lambda x:st.session_state.call_log.get(f"conquest_sn_{x}",{}).get('called',False))]
        for _,r in sns.head(75).iterrows():
            hs=int(r['heat_score']) if pd.notna(r.get('heat_score')) else 0
            bc='badge-hot' if hs>=70 else ('badge-warm' if hs>=50 else 'badge-cool')
            bl='HOT' if hs>=70 else ('WARM' if hs>=50 else 'COOL')
            fl=f"{int(r['sec_fleet'])}" if pd.notna(r.get('sec_fleet')) else "?"
            rv=f"${r['historical_revenue']:,.0f}" if pd.notna(r.get('historical_revenue')) else "—"
            ph=str(r.get('phone','')).strip(); ph=ph if len(ph)>=7 and ph not in ('nan','0','0.0') else ''
            ct=str(r.get('contact','')).strip()
            sub=" | ".join([x for x in [ct,ph,str(r.get('city','')),str(r.get('state',''))] if x and x!='nan'][:3])
            render_row(str(r['company']),str(r['company']),[("",sub),("",f'<span class="badge {bc}">{bl}</span> {fl} units'),("",rv)],"conquest_sn",dbr)

    if view in ["All","EDA Tier A (Cold)"]:
        if view=="All": st.markdown("---")
        st.markdown('<div class="info-banner" style="background:#F0FDF4;color:#166534;border-left:4px solid #059669;"><strong>EDA Tier A — Cold Conquest.</strong> 3+ SEC machines, score 70+, equipment from 2015+. They own our brands but have never been our customer.</div>',unsafe_allow_html=True)
        cheaders(['Called','F/U','Company','Score / Fleet','Equip Value','Notes'])
        eds=ef.sort_values('score',ascending=False)
        if hide: eds=eds[~eds['company'].apply(lambda x:st.session_state.call_log.get(f"conquest_eda_{x}",{}).get('called',False))]
        for _,r in eds.head(75).iterrows():
            sc=int(r['score']) if pd.notna(r['score']) else 0; un2=int(r['sec_units']) if pd.notna(r['sec_units']) else 0
            vl=f"${r['sec_value']:,.0f}" if pd.notna(r.get('sec_value')) else "—"
            ph=str(r.get('phone','')).strip(); ph=ph if len(ph)>=7 and ph not in ('nan','0','0.0') else ''
            ct=str(r.get('contact','')).strip()
            sub=" | ".join([x for x in [ct,ph,str(r.get('city','')),str(r.get('state',''))] if x and x!='nan'][:3])
            render_row(str(r['company']),str(r['company']),[("",sub),("",f"Score {sc} | {un2} units"),("",vl)],"conquest_eda",dbr)

# =============================================================================
# PARTS
# =============================================================================

def show_parts():
    df=load_parts(); br,s,h,_=fbar("parts",df['BranchName'].dropna().unique().tolist())
    dbr=br or gbn(); f=df[df['BranchName']==dbr].copy()
    if s: f=f[f['CustomerName'].str.contains(s,case=False,na=False)]
    t,c,fu=count_called(f,'Customer','parts'); cbar('Parts Campaign',dbr,t,c,fu)
    st.markdown('<div class="info-banner" style="background:#EFF6FF;color:#1E40AF;border-left:4px solid #2563EB;">Existing customers targeted by seasonal buying patterns. Verify customer profile on NDS before calling.</div>',unsafe_allow_html=True)
    st.markdown('<div class="tip-banner"><strong>Before Calling:</strong> Check NDS for recent orders. Use the Bundle Tool to identify complementary parts.</div>',unsafe_allow_html=True)
    f['_c']=f['Customer'].astype(str).apply(lambda x:st.session_state.call_log.get(f"parts_{x}",{}).get('called',False))
    if h: f=f[~f['_c']]
    st.caption(f"{len(f)} customers"); cheaders(['Called','F/U','Customer','Equipment','Categories','Notes'])
    for _,r in f.head(100).iterrows():
        cid=str(r['Customer']); nm=r.get('CustomerName','') or cid
        eq=str(r.get('Equipment',''))[:55] if pd.notna(r.get('Equipment')) else ''
        ca=str(r.get('Categories',''))[:40] if pd.notna(r.get('Categories')) else ''
        render_row(cid,nm,[("",f"Acct: {cid}"),("",eq),("",ca)],"parts",dbr)

# =============================================================================
# SERVICE
# =============================================================================

def show_service():
    df=load_service(); br,s,h,mo=fbar("svc",df['branch_name'].dropna().unique().tolist(),show_month=True)
    dbr=br or gbn(); mo=mo or st.session_state.campaign_month
    f=df[(df['branch_name']==dbr)&(df['target_month']==mo)].copy()
    if s:
        sq=s.lower()
        f=f[f['cust_name'].str.lower().str.contains(sq,na=False)|f['equipment'].fillna('').str.lower().str.contains(sq,na=False)]
    t,c,fu=count_called(f,'cust_acct','service')
    # Header matches existing app style
    cbar(f'{MONTH_NAMES[mo]} Campaign',dbr,t,c,fu)
    # Campaign info banner
    total_rev=f['month_revenue'].sum(); strong_ct=len(f[f['tier']=='STRONG'])
    st.markdown(f'<div class="info-banner" style="background:#E0F2FE;color:#0C4A6E;border-left:4px solid #0369A1;"><strong>{MONTH_NAMES[mo]} Campaign: Spring Service Push</strong> | ${total_rev:,.0f} historical {MONTH_NAMES[mo]} revenue | {strong_ct} proven multi-year buyers<br>These customers historically service equipment in {MONTH_NAMES[mo]}. Concentrated buyers have narrow windows - don\'t miss them.<br>"History" shows what each customer spends in {MONTH_NAMES[mo]} and how reliable the pattern is.</div>',unsafe_allow_html=True)
    # Before calling tip
    st.markdown('<div class="info-banner" style="background:#FFFBEB;color:#92400E;border-left:4px solid #D97706;"><strong>Before Calling:</strong> Verify customer service history and open work orders on NDS. Use the equipment info to offer specific maintenance recommendations.</div>',unsafe_allow_html=True)
    f['_c']=f['cust_acct'].astype(str).apply(lambda x:st.session_state.call_log.get(f"service_{x}",{}).get('called',False))
    if h: f=f[~f['_c']]
    # Sort: STRONG first, then GOOD, then TARGET, then by revenue
    tier_sort={'STRONG':0,'GOOD':1,'TARGET':2}
    f['_ts']=f['tier'].map(tier_sort).fillna(3)
    f=f.sort_values(['_ts','month_revenue'],ascending=[True,False])
    st.caption(f"{len(f)} customers shown"); cheaders(['Called','Follow-Up','Customer','Equipment','History','Notes'])
    for _,r in f.head(100).iterrows():
        cid=str(r['cust_acct']); nm=str(r['cust_name']).strip()
        # Tier badge
        tier=str(r.get('tier',''))
        if tier=='STRONG': badge='<span style="background:#1E3A5F;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-left:6px;">STRONG</span>'
        elif tier=='GOOD': badge='<span style="background:#059669;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-left:6px;">GOOD</span>'
        elif tier=='TARGET': badge='<span style="background:#D97706;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-left:6px;">TARGET</span>'
        else: badge=''
        # Equipment
        eq=str(r.get('equipment','')) if pd.notna(r.get('equipment')) else ''
        eq=eq if eq and eq!='nan' else ''
        # History with GL desc and year pattern
        hist=str(r.get('history','')) if pd.notna(r.get('history')) else ''
        gl=str(r.get('gl_desc','')) if pd.notna(r.get('gl_desc')) else ''
        yp=str(r.get('year_pattern','')) if pd.notna(r.get('year_pattern')) else ''
        gl_short=gl.replace('SALES ','').replace('CUSTOMER ','').title() if gl else ''
        hist_line2=f"{gl_short} | {yp}" if gl_short and yp else (gl_short or yp)
        render_row(cid,nm,[("",f"Acct: {cid}"),("",eq),("",f"{hist}<br><span style='color:#666;font-size:12px;'>{hist_line2}</span>" if hist_line2 else hist)],"service",dbr,extra_badge=badge)

# =============================================================================
# CONSIGNMENT
# =============================================================================

def show_consignment():
    df=load_consignment(); br,s,h,_=fbar("con",df['Branch'].dropna().unique().tolist())
    dbr=br or gbn(); f=df[df['Branch']==dbr].copy()
    if s:
        sq=s.lower()
        f=f[f['Customer'].str.lower().str.contains(sq,na=False)|f['Equipment'].fillna('').str.lower().str.contains(sq,na=False)|f['Top_Parts'].fillna('').str.lower().str.contains(sq,na=False)]
    t,c,fu=count_called(f,'Account','consignment'); cbar('Consignment',dbr,t,c,fu)
    # Info banner
    total_inv=f['Stock Cost'].sum(); total_sell=f['Sell Value'].sum()
    avg_gm=f['GM%'].mean()*100 if len(f)>0 else 0
    st.markdown(f'<div class="info-banner" style="background:#FFFBEB;color:#92400E;border-left:4px solid #D97706;"><strong>Consignment Bin Candidates</strong> | {len(f)} customers | Est. inventory: ${total_inv:,.0f} cost / ${total_sell:,.0f} sell ({avg_gm:.0f}% GM)<br>Ranked by readiness score. Each customer shows their top repeat parts (bought in 2+ of 4 half-year periods) and estimated bin investment.</div>',unsafe_allow_html=True)
    st.markdown('<div class="info-banner" style="background:#E0F2FE;color:#0C4A6E;border-left:4px solid #0369A1;"><strong>Before Calling:</strong> Review the customer\'s top parts below. Lead with: "We noticed you order [part] regularly. Would a consignment bin save you downtime?"</div>',unsafe_allow_html=True)
    f['_c']=f['Account'].astype(str).apply(lambda x:st.session_state.call_log.get(f"consignment_{x}",{}).get('called',False))
    if h: f=f[~f['_c']]
    f=f.sort_values('Readiness',ascending=False)
    st.caption(f"{len(f)} customers shown")
    # Custom wider layout for consignment
    hcols=st.columns([0.4,0.4,2.2,2.5,1.2,2.0])
    for i,l in enumerate(['Called','F/U','Customer','Top Repeat Parts','Bin Investment','Notes']):
        hcols[i].markdown(f'<div class="col-header">{l}</div>',unsafe_allow_html=True)
    for _,r in f.head(100).iterrows():
        ac=str(r['Account']); nm=str(r['Customer']).strip()
        lk=f"consignment_{ac}"
        log=st.session_state.call_log; e=log.get(lk,{})
        ic=e.get('called',False); ifu=e.get('followup',False); sn=e.get('notes','')
        cols=st.columns([0.4,0.4,2.2,2.5,1.2,2.0])
        with cols[0]: nc=st.checkbox("",value=ic,key=f"c_{lk}",label_visibility="collapsed")
        with cols[1]: nf=st.checkbox("",value=ifu,key=f"f_{lk}",label_visibility="collapsed")
        with cols[2]:
            # Customer info: name, tier badge, equipment, season
            phase=int(r['Phase']) if pd.notna(r.get('Phase')) else 0
            score=int(r['Readiness']) if pd.notna(r.get('Readiness')) else 0
            if score>=90: pbadge='<span style="background:#1E3A5F;color:white;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;margin-left:6px;">PHASE 1</span>'
            elif score>=70: pbadge='<span style="background:#059669;color:white;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;margin-left:6px;">PHASE 2</span>'
            else: pbadge='<span style="background:#D97706;color:white;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;margin-left:6px;">PHASE 3</span>'
            eq=str(r.get('Equipment','')) if pd.notna(r.get('Equipment')) else ''
            season=str(r.get('Peak Season','')) if pd.notna(r.get('Peak Season')) else ''
            rv25=f"${r['Rev 2025']:,.0f}" if pd.notna(r.get('Rev 2025')) else ''
            tr=str(r.get('Trend','')) if pd.notna(r.get('Trend')) else ''
            rep=int(r.get('Repeat_Parts',0)) if pd.notna(r.get('Repeat_Parts')) else 0
            sub_parts = [f"Acct: {ac} | Score {score}"]
            if eq: sub_parts.append(f"Equip: {eq}")
            if season or rv25: sub_parts.append(f"Peak: {season} | {rv25} ({tr})" if season else f"{rv25} ({tr})")
            sub_line = '<br>'.join(sub_parts)
            st.markdown(f'<div class="customer-name">{nm}{pbadge}</div><div class="customer-sub">{sub_line}</div>',unsafe_allow_html=True)
        with cols[3]:
            # Top repeat parts - formatted as compact list
            tp=str(r.get('Top_Parts','')) if pd.notna(r.get('Top_Parts')) else ''
            if tp:
                parts_html = []
                for p in tp.split(' | ')[:4]:
                    parts_html.append(f"<div style='font-size:12px;color:#475569;line-height:1.5;'>{p}</div>")
                rep_total = int(r.get('Repeat_Parts',0))
                if rep_total > 4:
                    parts_html.append(f"<div style='font-size:11px;color:#94a3b8;'>+{rep_total-4} more repeat parts</div>")
                st.markdown(''.join(parts_html),unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty-cell">No repeat parts found</div>',unsafe_allow_html=True)
        with cols[4]:
            # Bin investment summary
            sc=r.get('Stock Cost',0) if pd.notna(r.get('Stock Cost')) else 0
            sv=r.get('Sell Value',0) if pd.notna(r.get('Sell Value')) else 0
            gm=r.get('GM%',0) if pd.notna(r.get('GM%')) else 0
            roi=r.get('Bin ROI',0) if pd.notna(r.get('Bin ROI')) else 0
            st.markdown(f'<div style="font-size:13px;color:#475569;"><strong>${sc:,.0f}</strong> cost<br>${sv:,.0f} sell<br>{gm*100:.0f}% GM | {roi:.1f}x ROI</div>',unsafe_allow_html=True)
        with cols[5]: nn=st.text_input("",value=sn,key=f"n_{lk}",label_visibility="collapsed",placeholder="Add notes...")
        if nc!=ic or nf!=ifu or nn!=sn:
            if nc or nf or nn:
                entry={'customer_name':nm,'branch_name':dbr,'called':nc,'followup':nf,'notes':nn,'user':gun(),'date_updated':datetime.now().strftime('%Y-%m-%d %H:%M')}
                save_entry(lk,entry)
            else: delete_entry(lk)
            if nc!=ic: st.rerun()
        st.markdown('<div class="row-divider"></div>',unsafe_allow_html=True)

# =============================================================================
# ADMIN
# =============================================================================

def show_admin():
    st.markdown('<div class="header-bar"><span class="page-title">Admin Dashboard — Leadership View</span><span class="page-info">All Branches | All Campaigns</span></div>',unsafe_allow_html=True)

    # Refresh button
    c1,c2,c3=st.columns([1,1,1])
    with c1:
        if st.session_state.gsheets_active:
            if st.button("Refresh from Sheets"): refresh_log(); st.rerun()
    with c3:
        if st.button("← Back to Login",key="admin_back_top"): go('login'); st.rerun()

    log=st.session_state.call_log
    tc=sum(1 for v in log.values() if v.get('called'))
    tfu=sum(1 for v in log.values() if v.get('followup'))
    tn=sum(1 for v in log.values() if v.get('notes','').strip())
    uu=len(set(v.get('user','') for v in log.values() if v.get('user')))
    today=datetime.now().strftime('%Y-%m-%d')
    ct=sum(1 for v in log.values() if v.get('called') and v.get('date_updated','').startswith(today))

    cols=st.columns(5)
    for i,(n,l) in enumerate([(tc,"Total Calls"),(ct,"Called Today"),(tfu,"Follow-Ups"),(tn,"Notes Logged"),(uu,"Active Users")]):
        with cols[i]: st.markdown(f'<div class="admin-metric"><div class="admin-num">{n}</div><div class="admin-label">{l}</div></div>',unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### Campaign Progress")
    rec=load_recovery(); sn=load_conquest_sn(); eda=load_conquest_eda(); pts=load_parts(); svc=load_service(); con=load_consignment()
    cstats=[]
    for nm,px,d,ic in [("Recovery","recovery",rec,"customer"),("Conquest SN","conquest_sn",sn,"company"),("Conquest EDA","conquest_eda",eda,"company"),("Parts Campaign","parts",pts,"Customer"),("Consignment","consignment",con,"Account")]:
        tt=len(d); cc=sum(1 for _,r in d.iterrows() if log.get(f"{px}_{r[ic]}",{}).get('called'))
        pp=int(cc/tt*100) if tt>0 else 0
        cstats.append({'Campaign':nm,'Total':tt,'Called':cc,'Remaining':tt-cc,'Progress':f"{pp}%"})
    sm=st.session_state.get('campaign_month',datetime.now().month)
    svm=svc[svc['target_month']==sm]; svt=len(svm)
    svc2=sum(1 for _,r in svm.iterrows() if log.get(f"service_{r['cust_acct']}",{}).get('called'))
    svp=int(svc2/svt*100) if svt>0 else 0
    cstats.append({'Campaign':f'Service ({MONTH_NAMES[sm]})','Total':svt,'Called':svc2,'Remaining':svt-svc2,'Progress':f"{svp}%"})
    st.dataframe(pd.DataFrame(cstats),use_container_width=True,hide_index=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### Branch Activity")
    bdata=[]
    for brn in sorted(BRANCHES.values()):
        bc=sum(1 for v in log.values() if v.get('called') and v.get('branch_name')==brn)
        bf=sum(1 for v in log.values() if v.get('followup') and v.get('branch_name')==brn)
        bnn=sum(1 for v in log.values() if v.get('notes','').strip() and v.get('branch_name')==brn)
        bu=len(set(v.get('user','') for v in log.values() if v.get('branch_name')==brn and v.get('user')))
        rt=len(rec[rec['branch']==brn]); st2=len(sn[sn['branch']==brn]); et=len(eda[eda['branch']==brn])
        pt=len(pts[pts['BranchName']==brn]); ct2=len(con[con['Branch']==brn])
        tt=rt+st2+et+pt+ct2; pp=int(bc/tt*100) if tt>0 else 0
        bdata.append({'Branch':brn,'Targets':tt,'Calls':bc,'Follow-Ups':bf,'Notes':bnn,'Users':bu,'Progress':f"{pp}%",'Recovery':rt,'Conquest':st2+et,'Parts':pt,'Consign':ct2})
    bdf=pd.DataFrame(bdata).sort_values('Calls',ascending=False)
    st.dataframe(bdf,use_container_width=True,hide_index=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### Recent Activity")
    recent=[]
    for k,v in log.items():
        if v.get('called'):
            cpx=k.split('_')[0]; cpx='Conquest' if 'conquest' in k else cpx.title()
            recent.append({'Customer':v.get('customer_name',k),'Branch':v.get('branch_name',''),'User':v.get('user',''),'Follow-Up':'Yes' if v.get('followup') else '','Notes':(v.get('notes','')[:60]+'...' if len(v.get('notes',''))>60 else v.get('notes','')),'Date':v.get('date_updated',''),'Campaign':cpx})
    if recent:
        rdf=pd.DataFrame(recent).sort_values('Date',ascending=False).head(50)
        st.dataframe(rdf,use_container_width=True,hide_index=True)
    else: st.info("No calls logged yet. Activity will appear here as branches make outreach calls.")

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### User Leaderboard")
    uc=Counter(v.get('user','Unknown') for v in log.values() if v.get('called'))
    if uc: st.dataframe(pd.DataFrame([{'Name':n,'Calls':c} for n,c in uc.most_common(20)]),use_container_width=True,hide_index=True)
    else: st.info("No calls logged yet.")

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("### Export")
    c1,c2,c3=st.columns([1,1,1])
    with c1:
        if st.button("Export Full Call Log",use_container_width=True):
            if log:
                exp=[{'Key':k,'Customer':v.get('customer_name',''),'Branch':v.get('branch_name',''),'User':v.get('user',''),'Called':v.get('called',False),'Follow-Up':v.get('followup',False),'Notes':v.get('notes',''),'Date':v.get('date_updated',''),'Campaign':k.split('_')[0]} for k,v in log.items()]
                csv=pd.DataFrame(exp).to_csv(index=False)
                st.download_button("Download CSV",csv,f"outreach_log_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
            else: st.info("No data to export yet.")
    with c3:
        if st.button("← Back to Login",use_container_width=True,key="admin_back_bottom"): go('login'); st.rerun()
    st.markdown('<div style="text-align:center;color:#94a3b8;font-size:11px;margin-top:30px;padding-top:12px;border-top:1px solid #e2e8f0;">Created by Nick Butler | Southeastern Equipment | 2026</div>',unsafe_allow_html=True)

# =============================================================================
# ROUTER
# =============================================================================

{'login':show_login,'cards':show_cards,'recovery':show_recovery,'conquest':show_conquest,'parts':show_parts,'service':show_service,'consignment':show_consignment,'admin':show_admin}.get(st.session_state.page,show_login)()
