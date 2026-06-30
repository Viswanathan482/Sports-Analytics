"""
SoccerLens — Complete Player Analytics Dashboard
Stakeholder: Sporting Director / Board Member
Features:
  • Hierarchical filters: Club → Country → Player → Year
  • Real player images (Transfermarkt CDN)
  • On-loan indicator
  • Animated year-wise performance charts
  • Football pitch shot map (mplsoccer)
  • Market value trajectory
  • Injury history
  • Radar attributes
"""

import streamlit as st
from utils.styles import dedent_html, MAIN_CSS, SIDEBAR_BRAND
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mplsoccer import Pitch, VerticalPitch
import requests
from PIL import Image
import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import warnings
warnings.filterwarnings("ignore")

# ── Page config ───────────────────────────────────────────────
st.set_page_config(page_title="Scout IQ", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
st.markdown(MAIN_CSS, unsafe_allow_html=True)

# ── CSS ───────────────────────────────────────────────────────
st.markdown(dedent_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.main{background:#0A0E1A;}
header[data-testid="stHeader"]{background:transparent !important;box-shadow:none !important;}
[data-testid="stToolbar"]{visibility:hidden !important;}
[data-testid="stDecoration"]{display:none !important;}
[data-testid="stSidebarCollapsedControl"]{display:none !important;}
[data-testid="stSidebarCollapseButton"]{display:none !important;}
[data-testid="collapsedControl"]{display:none !important;}
[data-testid="baseButton-headerNoPadding"]{display:none !important;}
[data-testid="stSidebarHeader"] button{display:none !important;}
[data-testid="stSidebarUserContent"] + div button{display:none !important;}
button[kind="headerNoPadding"]{display:none !important;}
button[title*="sidebar" i]{display:none !important;}
button[aria-label*="sidebar" i]{display:none !important;}
header[data-testid="stHeader"] button{display:none !important;}
section[data-testid="stSidebar"] > div:first-child button{display:none !important;}
button[kind="header"]{display:none !important;}
[data-testid="stSidebar"]{min-width:21rem !important;max-width:21rem !important;
                          transform:none !important;visibility:visible !important;}
[data-testid="stSidebar"][aria-expanded="false"]{margin-left:0 !important;}
.block-container{padding:1rem 1.5rem 2rem !important;}

/* Player card */
.player-card{
  background:linear-gradient(160deg,#111827,#1a2235);
  border:1px solid #1f2d45;border-radius:16px;
  padding:1.4rem;text-align:center;
}
.player-name{
  font-family:'Outfit',sans-serif;font-size:1.9rem;
  color:#fff;letter-spacing:2px;margin:.6rem 0 .2rem;
  line-height:1.1;
}
.player-pos{font-size:.75rem;color:#00C97B;font-weight:600;
            letter-spacing:2px;text-transform:uppercase;}
.bio-row{
  display:flex;justify-content:space-between;align-items:center;
  padding:.4rem .5rem;border-bottom:1px solid #1f2d455;
  font-size:.82rem;
}
.bio-label{color:#6B7280;}
.bio-val{color:#e8eaf0;font-weight:500;}
.loan-badge{
  background:#2d1a0a;border:1px solid #f59e0b;
  border-radius:6px;padding:3px 10px;
  font-size:.72rem;color:#fcd34d;font-weight:600;
  display:inline-block;margin-top:.5rem;
}
.avatar-ring{
  width:130px;height:130px;border-radius:50%;
  border:3px solid #00C97B;
  overflow:hidden;display:flex;align-items:center;
  justify-content:center;background:#1f2d45;
  margin:0 auto .8rem;font-size:2.8rem;
}
.avatar-ring img{width:100%;height:100%;object-fit:cover;}

/* KPI cards */
.kpi-row{display:flex;gap:8px;margin:1rem 0;}
.kpi{
  flex:1;background:#111827;border:1px solid #1f2d45;
  border-radius:10px;padding:.8rem;text-align:center;
}
.kpi-val{font-family:'Outfit',sans-serif;font-size:1.9rem;
          color:#00C97B;line-height:1;}
.kpi-lbl{font-size:.68rem;color:#6B7280;letter-spacing:2px;
          text-transform:uppercase;margin-top:.2rem;}

/* Section headers */
.sec-hdr{
  font-family:'Outfit',sans-serif;font-size:1.1rem;
  color:#e8eaf0;letter-spacing:3px;
  border-left:3px solid #00C97B;padding-left:10px;
  margin:1rem 0 .6rem;
}
/* Tabs */
.stTabs [data-baseweb="tab-list"]{background:#111827;border-radius:8px;padding:3px;gap:3px;}
.stTabs [data-baseweb="tab"]{color:#6B7280;border-radius:6px;padding:7px 18px;
                              font-size:.78rem;letter-spacing:1.5px;text-transform:uppercase;}
.stTabs [aria-selected="true"]{background:#00C97B!important;color:#0A0E1A!important;font-weight:700;}

/* Sidebar */
[data-testid="stSidebar"]{background:#0d1220;border-right:1px solid #1f2d45;}

hr{border-color:#1f2d45;}
</style>
"""), unsafe_allow_html=True)

PLOT = dict(paper_bgcolor="#111827", plot_bgcolor="#111827",
            font=dict(color="#9CA3AF",size=11), margin=dict(l=10,r=10,t=30,b=10))
GREEN, GOLD, RED, BLUE, AMBER, PURPLE = "#00C97B","#FFD700","#EF4444","#3B82F6","#F59E0B","#8B5CF6"

BASE = str(Path(__file__).parent.parent / "data" / "processed")
DATA = str(Path(__file__).parent.parent / "data" / "processed")

# ─────────────────────────────────────────────────────────────
# DATA LOADING (cached)
# ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_lookup():
    df = pd.read_csv(f"{BASE}/player_lookup.csv")
    df['on_loan'] = df['on_loan'].fillna(False).astype(bool)
    df['clean_name'] = df['clean_name'].fillna('Unknown')
    df['current_club_name'] = df['current_club_name'].fillna('Unknown')
    df['citizenship'] = df['citizenship'].fillna('Unknown')
    return df

@st.cache_data(show_spinner=False)
def load_perf():
    return pd.read_csv(f"{BASE}/perf_by_season.csv")

@st.cache_data(show_spinner=False)
def load_market():
    mv = pd.read_csv(f"{BASE}/market_value_trends.csv")
    mv['year'] = pd.to_numeric(mv['year'], errors='coerce')
    return mv

@st.cache_data(show_spinner=False)
def load_injuries():
    return pd.read_csv(f"{BASE}/clean_injuries.csv")

@st.cache_data(show_spinner=False)
def load_fifa():
    return pd.read_csv(f"{BASE}/clean_fifa_players.csv")

@st.cache_data(show_spinner=False)
def load_shots():
    return pd.read_csv(f"{BASE}/clean_wc2022_shots.csv")

# ─────────────────────────────────────────────────────────────
# IMAGE HELPER
# ─────────────────────────────────────────────────────────────
def fetch_player_image(image_url: str, name: str) -> str:
    """Returns HTML for player image or styled avatar fallback."""
    if image_url and pd.notna(image_url) and 'default' not in str(image_url):
        try:
            r = requests.get(image_url, timeout=4, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; SoccerLens/1.0)'
            })
            if r.status_code == 200 and len(r.content) > 1000:
                import base64
                ext = 'png' if image_url.endswith('.png') else 'jpeg'
                b64 = base64.b64encode(r.content).decode()
                return f'<img src="data:image/{ext};base64,{b64}" style="width:130px;height:130px;border-radius:50%;object-fit:cover;border:3px solid #00C97B;">'
        except Exception:
            pass
    # Fallback: styled avatar with initials
    initials = ''.join([p[0].upper() for p in name.split()[:2] if p])[:2] or '?'
    return (f'<div style="width:130px;height:130px;border-radius:50%;border:3px solid #00C97B;'
            f'background:linear-gradient(135deg,#1f4d3a,#0a2040);display:flex;align-items:center;'
            f'justify-content:center;font-size:2.8rem;font-weight:700;color:#00C97B;margin:0 auto;">'
            f'{initials}</div>')

# ─────────────────────────────────────────────────────────────
# SIDEBAR — HIERARCHICAL FILTERS
# ─────────────────────────────────────────────────────────────
lookup = load_lookup()
perf_df = load_perf()

with st.sidebar:
    st.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
    st.markdown(
        '<div style="font-family:\'Outfit\',sans-serif;font-size:.92rem;font-weight:700;'
        'color:#00C97B;letter-spacing:2px;text-transform:uppercase;margin:0 1rem .15rem;">'
        '🎯 Player Intelligence</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="font-size:.7rem;color:#6B7280;letter-spacing:1px;'
        'text-transform:uppercase;margin:0 1rem 1rem;">Player Analytics</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── FILTER 1: CLUB ────────────────────────────────────────
    st.markdown("**🏟️ Club**")
    all_clubs = sorted(lookup['current_club_name'].dropna().unique().tolist())
    # Popular clubs at top
    popular = ["Arsenal FC","Manchester City FC","FC Barcelona","Real Madrid CF",
               "Bayern Munich","Paris Saint-Germain","Liverpool FC","Chelsea FC",
               "Manchester United","Juventus FC","Inter Milan","AC Milan"]
    popular_in_data = [c for c in popular if c in all_clubs]
    other_clubs = [c for c in all_clubs if c not in popular_in_data]
    clubs_ordered = popular_in_data + ["─── All clubs ───"] + other_clubs
    clubs_clean = [c for c in clubs_ordered if c != "─── All clubs ───"]

    club_choice = st.selectbox(
        "Select club", ["All Clubs"] + clubs_ordered,
        help="Filter players by the club they currently play for"
    )
    if club_choice in ["All Clubs","─── All clubs ───"]:
        club_filter = lookup
        club_selected = None
    else:
        club_filter = lookup[lookup['current_club_name'] == club_choice]
        club_selected = club_choice

    # ── FILTER 2: COUNTRY ─────────────────────────────────────
    st.markdown("**🌍 Country / Nationality**")
    country_options = sorted(club_filter['citizenship'].dropna().unique().tolist())
    country_choice = st.selectbox(
        "Select nationality", ["All Countries"] + country_options,
        help="Filter by player nationality"
    )
    if country_choice != "All Countries":
        country_filter = club_filter[club_filter['citizenship'] == country_choice]
    else:
        country_filter = club_filter

    # ── FILTER 3: PLAYER NAME ─────────────────────────────────
    st.markdown("**👤 Player Name**")
    player_options = sorted(country_filter['clean_name'].dropna().unique().tolist())
    if not player_options:
        st.warning("No players match these filters.")
        st.stop()

    player_choice = st.selectbox(
        "Select player", player_options,
        help="Choose a specific player to analyse"
    )

    # Get player row
    player_row = country_filter[country_filter['clean_name'] == player_choice].iloc[0]
    player_id   = int(player_row['player_id'])
    is_on_loan  = bool(player_row.get('on_loan', False))
    loan_club   = player_row.get('on_loan_from_club_name', '')
    image_url   = str(player_row.get('player_image_url', ''))

    # ── FILTER 4: YEAR (if performance data available) ────────
    player_perf = perf_df[perf_df['player_id'] == player_id].copy()
    has_perf    = len(player_perf) > 0

    if has_perf:
        st.markdown("**📅 Season**")
        seasons_avail = sorted(player_perf['season_name'].dropna().unique().tolist(), reverse=True)
        year_choice = st.selectbox(
            "Select season", ["All Seasons"] + seasons_avail,
            help="Filter to a specific season's performance"
        )
    else:
        year_choice = "All Seasons"

    st.markdown("---")
    st.caption(f"**Dataset:** {len(lookup):,} active players across {lookup['current_club_name'].nunique():,} clubs")

# ─────────────────────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────────────────────
if is_on_loan:
    col_header1, col_header2 = st.columns([3,1])
else:
    col_header1 = st.container()
    col_header2 = None

with col_header1:
    st.markdown(
        f'<div style="font-family:\'Outfit\',sans-serif;font-size:1.8rem;'
        f'color:#e8eaf0;letter-spacing:3px;">PLAYER ANALYSIS DASHBOARD</div>',
        unsafe_allow_html=True
    )
    crumb_parts = []
    if club_selected:   crumb_parts.append(f"🏟️ {club_selected}")
    if country_choice != "All Countries": crumb_parts.append(f"🌍 {country_choice}")
    crumb_parts.append(f"👤 {player_choice}")
    st.caption("  ›  ".join(crumb_parts))

if col_header2 is not None:
    with col_header2:
        st.markdown(
            f'<div class="loan-badge">⚠️ ON LOAN FROM {loan_club}</div>',
            unsafe_allow_html=True
        )

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# LAYOUT: PLAYER CARD + TABS
# ─────────────────────────────────────────────────────────────
col_card, col_content = st.columns([1, 3])

# ── LEFT: PLAYER CARD ─────────────────────────────────────────
with col_card:
    # Player image (returns its own <img> or avatar HTML)
    with st.spinner("Loading image..."):
        img_html = fetch_player_image(image_url, player_choice)

    position = str(player_row.get('main_position', '—'))

    loan_html = (
        f'<div class="loan-badge">📋 On loan from<br>{loan_club}</div>'
        if is_on_loan else ''
    )

    def dob_to_age(dob):
        try:
            from datetime import datetime
            return datetime.now().year - pd.to_datetime(dob).year
        except: return "—"

    bio_items = [
        ("Club",        str(player_row.get('current_club_name','—'))),
        ("Nationality", str(player_row.get('citizenship','—'))),
        ("Age",         str(dob_to_age(player_row.get('date_of_birth','')))),
        ("DOB",         str(player_row.get('date_of_birth','—'))[:10]),
        ("Height",      f"{player_row.get('height','—')} cm"),
        ("Foot",        str(player_row.get('foot','—')).title()),
        ("Contract",    str(player_row.get('contract_expires','—'))[:10]),
    ]
    bio_html = "".join(
        f'<div class="bio-row"><span class="bio-label">{label}</span>'
        f'<span class="bio-val">{val}</span></div>'
        for label, val in bio_items
    )

    totals_html = ""
    if has_perf:
        total_g  = int(player_perf['goals'].sum())
        total_a  = int(player_perf['assists'].sum())
        total_yc = int(player_perf['yellow_cards'].sum())
        total_rc = int(player_perf['red_cards'].sum())
        total_m  = int(player_perf['minutes_played'].sum())
        kpi_data = [
            ("Goals",   total_g,            GREEN),
            ("Assists", total_a,            BLUE),
            ("Mins",    f"{total_m//1000}K", AMBER),
            ("YC",      total_yc,           "#FFD700"),
            ("RC",      total_rc,           RED),
        ]
        kpi_cells = "".join(
            f'<div class="kpi" style="border-color:{clr}22;">'
            f'<div class="kpi-val" style="color:{clr};">{val}</div>'
            f'<div class="kpi-lbl">{lbl}</div></div>'
            for lbl, val, clr in kpi_data
        )
        totals_html = f"""
        <div style="font-size:.68rem;color:#6B7280;letter-spacing:2px;
                    text-transform:uppercase;margin:1rem 0 .5rem;">CAREER TOTALS</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;">
          {kpi_cells}
        </div>"""

    st.markdown(dedent_html(f"""
    <div class="player-card">
      {img_html}
      <div class="player-name">{player_choice}</div>
      <div class="player-pos">{position}</div>
      {loan_html}
      <div style="margin-top:1rem;">{bio_html}</div>
      {totals_html}
    </div>"""), unsafe_allow_html=True)

# ── RIGHT: CONTENT TABS ───────────────────────────────────────
with col_content:
    tab_perf, tab_pitch, tab_market, tab_radar, tab_injury, tab_cards = st.tabs([
        "📊 Performance",
        "⚽ Pitch Analysis",
        "📈 Market Value",
        "🕸️ Attributes",
        "⚕️ Injury History",
        "🟨 Cards & Discipline",
    ])

    # ══════════════════════════════════════════════════════════
    # TAB 1: PERFORMANCE (animated year-wise)
    # ══════════════════════════════════════════════════════════
    with tab_perf:
        if not has_perf:
            st.info("No season performance data found for this player.")
        else:
            # Apply year filter
            if year_choice != "All Seasons":
                perf_show = player_perf[player_perf['season_name'] == year_choice]
            else:
                perf_show = player_perf.copy()

            # KPI strip for selected period
            st.markdown('<div class="sec-hdr">SEASON SUMMARY</div>', unsafe_allow_html=True)
            k1,k2,k3,k4,k5,k6 = st.columns(6)
            for col,(lbl,val,clr) in zip([k1,k2,k3,k4,k5,k6],[
                ("Goals",    int(perf_show['goals'].sum()), GREEN),
                ("Assists",  int(perf_show['assists'].sum()), BLUE),
                ("G+A",      int(perf_show['g_plus_a'].sum()), AMBER),
                ("Minutes",  f"{int(perf_show['minutes_played'].sum()):,}", "#9CA3AF"),
                ("Yellow",   int(perf_show['yellow_cards'].sum()), "#FFD700"),
                ("Red",      int(perf_show['red_cards'].sum()), RED),
            ]):
                col.markdown(
                    f'<div class="kpi"><div class="kpi-val" style="color:{clr};">{val}</div>'
                    f'<div class="kpi-lbl">{lbl}</div></div>',
                    unsafe_allow_html=True
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # ── ANIMATED CAREER TIMELINE ──
            st.markdown('<div class="sec-hdr">CAREER PERFORMANCE TIMELINE (ANIMATED)</div>', unsafe_allow_html=True)
            career = player_perf.sort_values('season_name')
            career['cumulative_goals']   = career['goals'].cumsum()
            career['cumulative_assists'] = career['assists'].cumsum()

            fig_anim = go.Figure()

            # Animated goals bar
            fig_anim.add_trace(go.Bar(
                x=career['season_name'], y=career['goals'],
                name="Goals", marker_color=GREEN, opacity=0.85,
                hovertemplate="Season: %{x}<br>Goals: %{y}<extra></extra>"
            ))
            fig_anim.add_trace(go.Bar(
                x=career['season_name'], y=career['assists'],
                name="Assists", marker_color=BLUE, opacity=0.7,
                hovertemplate="Season: %{x}<br>Assists: %{y}<extra></extra>"
            ))
            fig_anim.update_layout(
                **PLOT, height=310, barmode="group",
                xaxis=dict(title="Season", gridcolor="#1f2d45", tickangle=-45),
                yaxis=dict(title="Count",  gridcolor="#1f2d45"),
                legend=dict(bgcolor="#111827",bordercolor="#1f2d45",orientation="h",y=1.1),
                title=dict(text="Goals & Assists by Season", font=dict(color="#e8eaf0",size=13))
            )

            # Highlight selected year (use add_shape — works on category axes, add_vline does not)
            if year_choice != "All Seasons" and year_choice in career['season_name'].values:
                fig_anim.add_shape(
                    type="line", xref="x", yref="paper",
                    x0=year_choice, x1=year_choice, y0=0, y1=1,
                    line=dict(color=GOLD, width=2, dash="dash"),
                )
                fig_anim.add_annotation(
                    x=year_choice, y=1.04, xref="x", yref="paper",
                    text=f"Selected: {year_choice}", showarrow=False,
                    font=dict(color=GOLD, size=11),
                )

            st.plotly_chart(fig_anim, use_container_width=True)

            # ── GOALS PER 90 TREND (animated line) ──
            st.markdown('<div class="sec-hdr">GOALS PER 90 — ANIMATED TREND</div>', unsafe_allow_html=True)
            gp90 = career[career['minutes_played'] > 0].copy()
            gp90['season_idx'] = range(len(gp90))

            # Build animation frames
            frames = []
            for i in range(1, len(gp90)+1):
                sub = gp90.iloc[:i]
                frames.append(go.Frame(
                    data=[
                        go.Scatter(x=sub['season_name'], y=sub['goals_per90'],
                                   mode='lines+markers',
                                   line=dict(color=GREEN,width=2.5),
                                   marker=dict(size=8,color=GREEN)),
                    ],
                    name=str(i)
                ))

            fig_gp90 = go.Figure(
                data=[go.Scatter(x=gp90['season_name'].iloc[:1],
                                 y=gp90['goals_per90'].iloc[:1],
                                 mode='lines+markers',
                                 line=dict(color=GREEN,width=2.5),
                                 marker=dict(size=8,color=GREEN),
                                 name="G/90")],
                layout=go.Layout(
                    **PLOT, height=260,
                    xaxis=dict(title="Season",gridcolor="#1f2d45",tickangle=-45,
                               range=[gp90['season_name'].iloc[0], gp90['season_name'].iloc[-1]]),
                    yaxis=dict(title="Goals per 90",gridcolor="#1f2d45",
                               range=[0, max(0.01, gp90['goals_per90'].max()*1.2)]),
                    title=dict(text="Goals per 90 Min — Career Evolution",
                               font=dict(color="#e8eaf0",size=13)),
                    updatemenus=[dict(
                        type="buttons", showactive=False,
                        y=1.15, x=0.01, xanchor="left",
                        buttons=[
                            dict(label="▶ Play",
                                 method="animate",
                                 args=[None, dict(frame=dict(duration=300,redraw=True),
                                                  fromcurrent=True, mode="immediate")]),
                            dict(label="⏸ Pause",
                                 method="animate",
                                 args=[[None], dict(frame=dict(duration=0,redraw=False),
                                                    mode="immediate")]),
                        ]
                    )],
                ),
                frames=frames
            )
            st.plotly_chart(fig_gp90, use_container_width=True)
            st.caption("▶ Press Play to animate the career progression")

            # ── SEASON BREAKDOWN TABLE ──
            if year_choice != "All Seasons":
                st.markdown('<div class="sec-hdr">SEASON DETAIL</div>', unsafe_allow_html=True)
                detail = perf_show[['season_name','main_team','goals','assists','yellow_cards',
                                    'red_cards','minutes_played','goals_per90']].copy()
                detail.columns = ['Season','Team','Goals','Assists','YC','RC','Minutes','G/90']
                st.dataframe(detail, use_container_width=True)
            else:
                st.markdown('<div class="sec-hdr">FULL CAREER STATS</div>', unsafe_allow_html=True)
                all_detail = player_perf[['season_name','main_team','goals','assists','yellow_cards',
                                          'red_cards','minutes_played','goals_per90']].copy()
                all_detail.columns = ['Season','Team','Goals','Assists','YC','RC','Minutes','G/90']
                all_detail = all_detail.sort_values('Season',ascending=False)
                st.dataframe(all_detail, use_container_width=True, height=300)

    # ══════════════════════════════════════════════════════════
    # TAB 2: PITCH ANALYSIS (football field visuals)
    # ══════════════════════════════════════════════════════════
    with tab_pitch:
        shots_df = load_shots()
        # Try to find player in WC 2022 shot data
        # Match on last name or first part of name
        name_parts = player_choice.lower().split()
        player_shots = pd.DataFrame()
        for part in name_parts[:2]:
            if len(part) >= 4:
                matches = shots_df[shots_df['player'].str.lower().str.contains(part, na=False)]
                if len(matches) > 0:
                    player_shots = matches
                    break

        st.markdown('<div class="sec-hdr">⚽ PITCH ANALYSIS — WC 2022 DATA</div>', unsafe_allow_html=True)
        pitch_mode = st.radio("Visualisation type",
                              ["🎯 Shot Map","🔥 Shot Heatmap","📊 Shot Zone Breakdown"],
                              horizontal=True, key="pitch_mode")

        if len(player_shots) == 0:
            st.info(f"No WC 2022 shot data found for '{player_choice}'. "
                    f"Showing squad-level team data instead.")
            # Show team-level pitch visual
            team_name = str(player_row.get('current_club_name',''))
            team_shots = shots_df.head(200)  # Show all WC shots as overview
            title_str = "WC 2022 — All Shots Overview"
        else:
            team_shots = player_shots
            title_str = f"WC 2022 — {player_choice} Shots"
            st.success(f"Found {len(player_shots)} shots for {player_choice} in WC 2022")

        if "Shot Map" in pitch_mode:
            # ── COLOURFUL VERTICAL HALF-PITCH SHOT MAP ────────
            import matplotlib.patches as mpatch
            from mplsoccer import VerticalPitch

            x_col = 'x' if 'x' in team_shots.columns else 'location_x'
            y_col = 'y' if 'y' in team_shots.columns else 'location_y'

            xs       = pd.to_numeric(team_shots[x_col], errors='coerce')
            ys       = pd.to_numeric(team_shots[y_col], errors='coerce')
            outcomes = team_shots.get('shot_outcome',
                       pd.Series(['Off T']*len(team_shots), dtype=str))

            # Attacking half only (x >= 60 StatsBomb)
            valid = xs.notna() & ys.notna() & (xs >= 60)
            xs_a = xs[valid].values
            ys_a = ys[valid].values
            oc_a = np.array([str(o) for o in outcomes[valid].values])

            # Outcome → colour, size, zorder, edge
            OUTCOME_STYLE = {
                'Goal':     ('#FF3333', 220, 6, '#FFaaaa', 1.5),
                'Saved':    ('#3B82F6', 100, 4, '#93C5FD', 0.8),
                'Blocked':  ('#8B5CF6',  80, 3, '#C4B5FD', 0.8),
                'Post':     ('#F59E0B', 100, 5, '#FCD34D', 1.0),
                'Off Target':('#6B7280', 60, 2, '#9CA3AF', 0.5),
            }
            OUTCOME_MAP = {
                'Goal':'Goal','Saved':'Saved','Off T':'Off Target',
                'Blocked':'Blocked','Wayward':'Off Target',
                'Post':'Post','Saved to Post':'Saved',
                'Saved Off Target':'Saved','Woodwork':'Post',
            }
            mapped_oc = np.array([OUTCOME_MAP.get(o,'Off Target') for o in oc_a])

            # Stats
            n_goals    = int((mapped_oc == 'Goal').sum())
            n_on_tgt   = int((np.isin(mapped_oc, ['Goal','Saved'])).sum())
            n_shots    = len(xs_a)
            on_tgt_pct = round(n_on_tgt / max(n_shots,1) * 100)

            # Draw pitch — realistic striped grass instead of flat black
            pitch_sm = VerticalPitch(
                pitch_type='statsbomb', half=True,
                pitch_color='#1e5c2e', line_color='#e8f5e9',
                stripe=True, stripe_color='#247838',
                goal_type='box', goal_alpha=0.9,
                linewidth=2, spot_scale=0.005,
            )
            fig_sm, ax_sm = pitch_sm.draw(figsize=(6.5, 8.5))
            fig_sm.patch.set_facecolor('#0d1117')
            fig_sm.subplots_adjust(top=0.90, bottom=0.18, left=0.05, right=0.95)
            ax_sm.set_title(title_str, color='#ffffff',
                            fontsize=13, pad=12, fontweight='bold')

            # Draw each outcome group (low-priority first)
            for outcome in ['Off Target','Blocked','Post','Saved','Goal']:
                mask = (mapped_oc == outcome)
                if not mask.any(): continue
                clr, sz, zo, edge, lw = OUTCOME_STYLE[outcome]
                pitch_sm.scatter(
                    xs_a[mask], ys_a[mask],
                    s=sz, color=clr, ax=ax_sm,
                    alpha=0.95 if outcome=='Goal' else 0.80,
                    edgecolors=edge, linewidth=lw, zorder=zo
                )

            # Legend
            legend_handles = [
                mpatch.Patch(color='#FF3333', label=f"Goal ({n_goals})"),
                mpatch.Patch(color='#3B82F6', label='Saved'),
                mpatch.Patch(color='#8B5CF6', label='Blocked'),
                mpatch.Patch(color='#F59E0B', label='Post'),
                mpatch.Patch(color='#6B7280', label='Off Target'),
            ]
            ax_sm.legend(handles=legend_handles,
                         loc='lower center', bbox_to_anchor=(0.5, -0.04),
                         ncol=5, frameon=False, labelcolor='#e8eaf0',
                         fontsize=8.5, columnspacing=0.8)

            # Stats bar
            stat_items = [
                (str(n_goals),        'Goals',        '#FF3333'),
                (str(n_shots),        'Total Shots',  '#e8eaf0'),
                (f"{on_tgt_pct}%",    'On Target',    '#3B82F6'),
            ]
            bar_y0, bar_y1 = 0.0, 0.13
            # Background for stats bar
            from matplotlib.patches import FancyBboxPatch
            fig_sm.patches.append(FancyBboxPatch(
                (0.0, bar_y0), 1.0, bar_y1,
                boxstyle="square,pad=0", transform=fig_sm.transFigure,
                facecolor='#0d1117', zorder=0, clip_on=False))
            for si, (val, lbl, clr) in enumerate(stat_items):
                xp = (si + 0.5) / len(stat_items)
                fig_sm.text(xp, 0.09, val, ha='center', va='center',
                            fontsize=22, fontweight='bold', color=clr,
                            transform=fig_sm.transFigure, zorder=5)
                fig_sm.text(xp, 0.035, lbl, ha='center', va='center',
                            fontsize=9, color='#888888',
                            transform=fig_sm.transFigure, zorder=5)
            for di in range(1, len(stat_items)):
                xd = di / len(stat_items)
                fig_sm.add_artist(plt.Line2D([xd,xd],[bar_y0,bar_y1],
                    color='#333333', linewidth=1.0,
                    transform=fig_sm.transFigure, clip_on=False, zorder=4))

            st.pyplot(fig_sm, use_container_width=True)
            plt.close(fig_sm)
            st.caption("Data: StatsBomb WC 2022 (WC 2026 shot coordinates not yet in free tier)")

        elif "Heatmap" in pitch_mode:
            # ── BEAUTIFUL SHOT HEATMAP ─────────────────────────
            from mplsoccer import VerticalPitch
            import matplotlib.patches as mpatch

            x_col = 'x' if 'x' in team_shots.columns else 'location_x'
            y_col = 'y' if 'y' in team_shots.columns else 'location_y'

            xs = pd.to_numeric(team_shots[x_col], errors='coerce')
            ys = pd.to_numeric(team_shots[y_col], errors='coerce')
            valid = xs.notna() & ys.notna()
            xs_v = xs[valid].values
            ys_v = ys[valid].values

            pitch_hm = VerticalPitch(
                pitch_type='statsbomb', half=True,
                pitch_color='#1e5c2e', line_color='#e8f5e9',
                stripe=True, stripe_color='#247838',
                goal_type='box', linewidth=2,
            )
            fig_hm, ax_hm = pitch_hm.draw(figsize=(6.5, 8.5))
            fig_hm.patch.set_facecolor('#0d1117')
            fig_hm.subplots_adjust(top=0.91, bottom=0.05)
            ax_hm.set_title(f"Shot Density — {title_str}",
                            color='#ffffff', fontsize=13,
                            pad=12, fontweight='bold')

            if len(xs_v) >= 3:
                # KDE heatmap with a vivid colourmap that reads clearly over grass
                pitch_hm.kdeplot(
                    xs_v, ys_v, ax=ax_hm,
                    cmap='inferno', fill=True, alpha=0.75,
                    levels=15, thresh=0.05,
                )
                # Scatter shots on top (small, white semi-transparent)
                outcomes_v = team_shots.get('shot_outcome',
                    pd.Series(['Off T']*len(team_shots), dtype=str))[valid].values
                is_g = np.array([str(o).lower()=='goal' for o in outcomes_v])

                # non-goals: small white dots
                if (~is_g).any():
                    pitch_hm.scatter(xs_v[~is_g], ys_v[~is_g],
                        s=20, color='white', ax=ax_hm,
                        alpha=0.30, edgecolors='none', zorder=3)
                # goals: bright red
                if is_g.any():
                    pitch_hm.scatter(xs_v[is_g], ys_v[is_g],
                        s=80, color='#FF3333', ax=ax_hm,
                        alpha=0.95, edgecolors='#FFaaaa',
                        linewidth=1.0, zorder=5)

                # Colourbar
                from matplotlib.cm import ScalarMappable
                from matplotlib.colors import Normalize
                sm = ScalarMappable(cmap='inferno', norm=Normalize(0,1))
                sm.set_array([])
                cbar = fig_hm.colorbar(sm, ax=ax_hm,
                    orientation='horizontal', fraction=0.035,
                    pad=0.01, aspect=30)
                cbar.set_label('Shot Density', color='#cccccc', fontsize=9)
                cbar.ax.xaxis.set_tick_params(color='#888888')
                plt.setp(cbar.ax.xaxis.get_ticklabels(), color='#cccccc')
                cbar.outline.set_edgecolor('#555555')
            else:
                ax_hm.text(40, 90, 'Not enough shots', ha='center',
                           color='#ffffff', fontsize=12, fontweight='bold')

            st.pyplot(fig_hm, use_container_width=True)
            plt.close(fig_hm)
            st.caption("🔴 Goal  ·  ⚪ Shot  ·  Hotter = more shots from that zone")

        else:
            # ── SHOT ZONE BREAKDOWN ───────────────────────────
            def calc_zone(x, y):
                try:
                    d = np.sqrt((120-float(x))**2+(40-float(y))**2)
                    if d<6: return "Six-Yard Box"
                    if d<12: return "Central (12m)"
                    if d<20: return "Penalty Area"
                    if d<30: return "Edge of Box"
                    return "Long Range"
                except: return "Unknown"

            zs = team_shots.copy()
            zs['zone'] = zs.apply(lambda r: calc_zone(r.get('x',r.get('location_x',60)),
                                                       r.get('y',r.get('location_y',40))), axis=1)
            zs['is_goal'] = zs.get('shot_outcome','').str.lower().str.contains('goal').fillna(False)
            zs['xg'] = pd.to_numeric(zs.get('shot_statsbomb_xg', 0.1), errors='coerce').fillna(0.1)
            zone_agg = zs.groupby('zone').agg(shots=('zone','count'),
                goals=('is_goal','sum'), avg_xg=('xg','mean')).reset_index()
            zone_agg['conv_pct'] = (zone_agg['goals']/zone_agg['shots']*100).round(1)
            fig_zone = px.bar(zone_agg, x='zone', y='shots',
                              color='avg_xg', color_continuous_scale=["#1f2d45",GREEN],
                              text='goals',
                              labels={'shots':'Total Shots','zone':'Zone','avg_xg':'Avg xG'})
            fig_zone.update_traces(texttemplate='%{text}⚽', textposition='outside')
            fig_zone.update_layout(**PLOT, height=320,
                title=dict(text="Shots by Zone (number = goals scored)",
                           font=dict(color="#e8eaf0",size=13)),
                xaxis=dict(gridcolor="#1f2d45"),yaxis=dict(gridcolor="#1f2d45"))
            st.plotly_chart(fig_zone, use_container_width=True)

    # ══════════════════════════════════════════════════════════
    # TAB 3: MARKET VALUE
    # ══════════════════════════════════════════════════════════
    with tab_market:
        mv_df = load_market()
        player_mv = mv_df[mv_df['player_id'] == player_id].copy()

        st.markdown('<div class="sec-hdr">MARKET VALUE TRAJECTORY (€)</div>', unsafe_allow_html=True)

        if len(player_mv) == 0:
            st.info("No market value history found for this player in the Transfermarkt dataset.")
        else:
            player_mv = player_mv.sort_values('year')
            player_mv['value_M'] = (player_mv['value']/1e6).round(2)
            peak_val  = player_mv['value_M'].max()
            peak_year = player_mv.loc[player_mv['value_M'].idxmax(), 'year']
            curr_val  = player_mv['value_M'].iloc[-1]

            k1,k2,k3 = st.columns(3)
            for col,(lbl,val,clr) in zip([k1,k2,k3],[
                ("Current Value (€M)",  f"€{curr_val:.1f}M", GREEN),
                ("Peak Value (€M)",     f"€{peak_val:.1f}M", GOLD),
                ("Peak Year",           str(int(peak_year)),  BLUE),
            ]):
                col.markdown(
                    f'<div class="kpi"><div class="kpi-val" style="color:{clr};">{val}</div>'
                    f'<div class="kpi-lbl">{lbl}</div></div>',
                    unsafe_allow_html=True
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Animated market value chart
            fig_mv = go.Figure()
            fig_mv.add_trace(go.Scatter(
                x=player_mv['year'], y=player_mv['value_M'],
                mode='lines+markers',
                line=dict(color=GREEN, width=3),
                marker=dict(size=[12 if yr==peak_year else 6 for yr in player_mv['year']],
                            color=[GOLD if yr==peak_year else GREEN for yr in player_mv['year']],
                            symbol=['star' if yr==peak_year else 'circle' for yr in player_mv['year']]),
                fill='tozeroy', fillcolor="rgba(0,201,123,0.13)",
                hovertemplate="Year: %{x}<br>Value: €%{y:.1f}M<extra></extra>",
                name="Market Value"
            ))
            fig_mv.add_hline(y=curr_val, line_dash="dot", line_color="#6B7280",
                             annotation_text=f"Current: €{curr_val:.1f}M",
                             annotation_font_color="#9CA3AF")
            fig_mv.update_layout(**PLOT, height=340,
                xaxis=dict(title="Year",gridcolor="#1f2d45"),
                yaxis=dict(title="Market Value (€M)",gridcolor="#1f2d45"),
                title=dict(text=f"Market Value History — {player_choice}",
                           font=dict(color="#e8eaf0",size=13)))
            st.plotly_chart(fig_mv, use_container_width=True)
            st.caption("⭐ Gold star = peak market value  ·  Dashed line = current value")

            # Value change year-on-year
            player_mv['yoy_change'] = player_mv['value_M'].pct_change()*100
            fig_yoy = px.bar(player_mv.dropna(subset=['yoy_change']),
                             x='year', y='yoy_change',
                             color='yoy_change',
                             color_continuous_scale=[RED,"#6B7280",GREEN],
                             color_continuous_midpoint=0,
                             labels={'yoy_change':'Year-on-Year Change (%)'})
            fig_yoy.update_layout(**PLOT, height=240, coloraxis_showscale=False,
                title=dict(text="Year-on-Year Value Change %",font=dict(color="#e8eaf0",size=13)),
                xaxis=dict(gridcolor="#1f2d45"),yaxis=dict(gridcolor="#1f2d45"))
            st.plotly_chart(fig_yoy, use_container_width=True)

    # ══════════════════════════════════════════════════════════
    # TAB 4: ATTRIBUTE RADAR (FIFA data)
    # ══════════════════════════════════════════════════════════
    with tab_radar:
        fifa_df = load_fifa()
        # Match by clean name
        name_lower = player_choice.lower()
        match = fifa_df[fifa_df['name'].str.lower().str.contains(
            name_lower.split()[0] if name_lower.split() else name_lower, na=False)]
        if len(match) == 0 and len(name_lower.split()) > 1:
            match = fifa_df[fifa_df['name'].str.lower().str.contains(
                name_lower.split()[-1], na=False)]

        st.markdown('<div class="sec-hdr">ATTRIBUTE RADAR (FIFA DATA)</div>', unsafe_allow_html=True)

        if len(match) == 0:
            st.info(f"No FIFA attribute data found for '{player_choice}'. Try searching by last name in the FIFA dataset.")
            # Show generic radar for position group
            pos_group = str(player_row.get('main_position','Attack')).lower()
            avg = fifa_df[fifa_df['position_group'] == ('Attacker' if 'attack' in pos_group
                          else 'Midfielder' if 'midfield' in pos_group
                          else 'Defender' if 'defend' in pos_group else 'Goalkeeper')]
            if len(avg) > 0:
                cats = ["Finishing","Positioning","Dribbling","Vision","Composure","Pace"]
                vals = [avg['finishing'].mean(), avg['positioning'].mean(),
                        avg['dribbling'].mean(), avg['vision'].mean(),
                        avg['composure'].mean(),
                        (avg['acceleration'].mean()+avg['sprint_speed'].mean())/2]
                fig_r = go.Figure(go.Scatterpolar(
                    r=[v/99 for v in vals]+[vals[0]/99], theta=cats+[cats[0]],
                    fill="toself", name=f"Avg {pos_group.title()}",
                    line=dict(color=BLUE,width=2), fillcolor="rgba(59,130,246,0.13)"
                ))
                fig_r.update_layout(polar=dict(bgcolor=CARD if False else "#111827",
                    radialaxis=dict(visible=True,range=[0,1],gridcolor="#1f2d45",
                                   tickfont=dict(color="#6B7280",size=8)),
                    angularaxis=dict(gridcolor="#1f2d45",tickfont=dict(color="#9CA3AF",size=10))),
                    paper_bgcolor="#0A0E1A",font=dict(color="#e8eaf0"),
                    height=380,margin=dict(l=50,r=50,t=30,b=30),showlegend=True,
                    legend=dict(bgcolor="#111827",bordercolor="#1f2d45"))
                st.plotly_chart(fig_r, use_container_width=True)
                st.caption(f"Showing average attributes for {pos_group} position group")
        else:
            p = match.iloc[0]
            cats = ["Finishing","Positioning","Dribbling","Vision","Composure",
                    "Pace","Passing","Physical","Defending","Shooting"]
            attr_map = {
                "Finishing":   p.get('finishing',50),
                "Positioning": p.get('positioning',50),
                "Dribbling":   p.get('dribbling',50),
                "Vision":      p.get('vision',50),
                "Composure":   p.get('composure',50),
                "Pace":        (p.get('acceleration',50)+p.get('sprint_speed',50))/2,
                "Passing":     (p.get('short_passing',50)+p.get('long_passing',50))/2,
                "Physical":    p.get('stamina',50),
                "Defending":   (p.get('standing_tackle',50)+p.get('interceptions',50))/2,
                "Shooting":    p.get('shot_power',50),
            }
            vals = [float(attr_map.get(c,50) or 50) for c in cats]
            norm_v = [v/99 for v in vals]

            # Compare to position average
            pos_grp = str(p.get('position_group','Attacker'))
            avg_grp = fifa_df[fifa_df['position_group'] == pos_grp]
            avg_v   = [float(avg_grp[{
                "Finishing":"finishing","Positioning":"positioning","Dribbling":"dribbling",
                "Vision":"vision","Composure":"composure","Pace":"acceleration",
                "Passing":"short_passing","Physical":"stamina","Defending":"standing_tackle",
                "Shooting":"shot_power"
            }.get(c,'finishing')].mean() or 50) for c in cats]
            norm_avg = [v/99 for v in avg_v]

            c1, c2 = st.columns([2,1])
            with c1:
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(
                    r=norm_v+[norm_v[0]], theta=cats+[cats[0]],
                    fill="toself", name=player_choice,
                    line=dict(color=GREEN,width=2.5), fillcolor="rgba(0,201,123,0.13)"
                ))
                fig_r.add_trace(go.Scatterpolar(
                    r=norm_avg+[norm_avg[0]], theta=cats+[cats[0]],
                    fill="toself", name=f"Avg {pos_grp}",
                    line=dict(color=BLUE,width=1.5,dash="dash"), fillcolor="rgba(59,130,246,0.07)"
                ))
                fig_r.update_layout(
                    polar=dict(bgcolor="#111827",
                        radialaxis=dict(visible=True,range=[0,1],gridcolor="#1f2d45",
                                       tickfont=dict(color="#6B7280",size=8)),
                        angularaxis=dict(gridcolor="#1f2d45",tickfont=dict(color="#9CA3AF",size=10))),
                    paper_bgcolor="#0A0E1A", font=dict(color="#e8eaf0"),
                    legend=dict(bgcolor="#111827",bordercolor="#1f2d45"),
                    height=400, margin=dict(l=50,r=50,t=30,b=30),
                    title=dict(text=f"Attribute Radar — {player_choice} vs {pos_grp} Average",
                               font=dict(color="#e8eaf0",size=13))
                )
                st.plotly_chart(fig_r, use_container_width=True)
            with c2:
                st.markdown('<div class="sec-hdr">RATINGS</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div style="background:#111827;border:1px solid #1f2d45;border-radius:8px;padding:.8rem;">'
                    f'<div style="font-size:.7rem;color:#6B7280;letter-spacing:2px;margin-bottom:.5rem;">OVERALL</div>'
                    f'<div style="font-family:\'Outfit\',sans-serif;font-size:3rem;color:{GOLD};">{int(p.get("overall_rating",0))}</div>'
                    f'<div style="font-size:.7rem;color:#6B7280;margin-top:.3rem;">POTENTIAL</div>'
                    f'<div style="font-family:\'Outfit\',sans-serif;font-size:2rem;color:{GREEN};">{int(p.get("potential",0))}</div>'
                    f'</div>', unsafe_allow_html=True
                )
                for cat, val, avg in zip(cats, vals, avg_v):
                    diff = val - avg
                    clr = GREEN if diff >= 0 else RED
                    bar_w = int(val/99*100)
                    st.markdown(
                        f'<div style="margin:.3rem 0;">'
                        f'<div style="display:flex;justify-content:space-between;font-size:.75rem;margin-bottom:2px;">'
                        f'<span style="color:#9CA3AF;">{cat}</span>'
                        f'<span style="color:{clr};font-weight:600;">{int(val)} ({"+"+str(int(diff)) if diff>=0 else str(int(diff))})</span></div>'
                        f'<div style="background:#1f2d45;border-radius:4px;height:6px;">'
                        f'<div style="width:{bar_w}%;height:6px;background:{clr};border-radius:4px;"></div></div>'
                        f'</div>', unsafe_allow_html=True
                    )

    # ══════════════════════════════════════════════════════════
    # TAB 5: INJURY HISTORY
    # ══════════════════════════════════════════════════════════
    with tab_injury:
        inj_df = load_injuries()
        player_inj = inj_df[inj_df['player_id'] == player_id].copy()

        st.markdown('<div class="sec-hdr">INJURY HISTORY & RISK PROFILE</div>', unsafe_allow_html=True)

        if len(player_inj) == 0:
            st.success(f"✅ No injury records found for {player_choice} — clean bill of health in the dataset.")
        else:
            # Injury KPIs
            k1,k2,k3,k4 = st.columns(4)
            for col,(lbl,val,clr) in zip([k1,k2,k3,k4],[
                ("Total Injuries", len(player_inj), RED),
                ("Total Days Missed", int(player_inj['days_missed'].sum()), AMBER),
                ("Avg Days/Injury", round(player_inj['days_missed'].mean(),1), AMBER),
                ("Games Missed", int(player_inj['games_missed'].sum()), "#9CA3AF"),
            ]):
                col.markdown(
                    f'<div class="kpi"><div class="kpi-val" style="color:{clr};">{val}</div>'
                    f'<div class="kpi-lbl">{lbl}</div></div>',
                    unsafe_allow_html=True
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Injury timeline
            if 'season_name' in player_inj.columns:
                inj_season = player_inj.groupby('season_name').agg(
                    injuries=('injury_reason','count'),
                    days_missed=('days_missed','sum')
                ).reset_index()
                fig_inj = go.Figure()
                fig_inj.add_trace(go.Bar(x=inj_season['season_name'],
                                         y=inj_season['days_missed'],
                                         name="Days Missed",
                                         marker_color=AMBER, opacity=0.8))
                fig_inj.add_trace(go.Scatter(x=inj_season['season_name'],
                                             y=inj_season['injuries'],
                                             name="Injuries", mode='lines+markers',
                                             line=dict(color=RED,width=2),
                                             marker=dict(size=8,color=RED),
                                             yaxis='y2'))
                fig_inj.update_layout(**PLOT, height=280,
                    xaxis=dict(title="Season",gridcolor="#1f2d45",tickangle=-45),
                    yaxis=dict(title="Days Missed",gridcolor="#1f2d45"),
                    yaxis2=dict(title="Injuries",overlaying='y',side='right',
                               gridcolor="#1f2d45"),
                    legend=dict(bgcolor="#111827",bordercolor="#1f2d45"),
                    title=dict(text="Injury History by Season",font=dict(color="#e8eaf0",size=13)))
                st.plotly_chart(fig_inj, use_container_width=True)

            # Injury types
            inj_types = player_inj['injury_category'].value_counts().reset_index()
            inj_types.columns = ['Type','Count']
            fig_itype = px.pie(inj_types, values='Count', names='Type', hole=0.4,
                               color_discrete_sequence=[RED,AMBER,BLUE,PURPLE,GREEN])
            fig_itype.update_layout(**PLOT, height=260,
                title=dict(text="Injury Types",font=dict(color="#e8eaf0",size=13)))
            st.plotly_chart(fig_itype, use_container_width=True)

            # Injury table
            show_inj = player_inj[['season_name','injury_reason','injury_category',
                                   'days_missed','games_missed','severity']].copy()
            show_inj.columns = ['Season','Injury','Category','Days','Games','Severity']
            show_inj = show_inj.sort_values('Days',ascending=False)
            st.dataframe(show_inj, use_container_width=True, height=260)

    # ══════════════════════════════════════════════════════════
    # TAB 6: CARDS & DISCIPLINE
    # ══════════════════════════════════════════════════════════
    with tab_cards:
        st.markdown('<div class="sec-hdr">DISCIPLINE RECORD</div>', unsafe_allow_html=True)

        if not has_perf:
            st.info("No performance data available for discipline analysis.")
        else:
            # Card totals
            total_yc  = int(player_perf['yellow_cards'].sum())
            total_rc  = int(player_perf['red_cards'].sum())
            total_sy  = int(player_perf['second_yellow'].sum())
            total_all = total_yc + total_rc + total_sy

            k1,k2,k3,k4 = st.columns(4)
            for col,(lbl,val,clr) in zip([k1,k2,k3,k4],[
                ("Yellow Cards", total_yc,  "#FFD700"),
                ("Red Cards",    total_rc,  RED),
                ("2nd Yellows",  total_sy,  AMBER),
                ("Total Cards",  total_all, "#9CA3AF"),
            ]):
                col.markdown(
                    f'<div class="kpi"><div class="kpi-val" style="color:{clr};">{val}</div>'
                    f'<div class="kpi-lbl">{lbl}</div></div>',
                    unsafe_allow_html=True
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Cards per season chart
            card_df = player_perf[['season_name','yellow_cards','red_cards','second_yellow']].copy()
            card_df = card_df.sort_values('season_name')
            fig_cards = go.Figure()
            fig_cards.add_trace(go.Bar(x=card_df['season_name'], y=card_df['yellow_cards'],
                                       name="Yellow", marker_color="#FFD700", opacity=0.85))
            fig_cards.add_trace(go.Bar(x=card_df['season_name'], y=card_df['second_yellow'],
                                       name="2nd Yellow", marker_color=AMBER, opacity=0.85))
            fig_cards.add_trace(go.Bar(x=card_df['season_name'], y=card_df['red_cards'],
                                       name="Red", marker_color=RED, opacity=0.85))
            fig_cards.update_layout(**PLOT, height=300, barmode='stack',
                xaxis=dict(title="Season",gridcolor="#1f2d45",tickangle=-45),
                yaxis=dict(title="Cards",gridcolor="#1f2d45"),
                legend=dict(bgcolor="#111827",bordercolor="#1f2d45"),
                title=dict(text="Cards by Season",font=dict(color="#e8eaf0",size=13)))
            st.plotly_chart(fig_cards, use_container_width=True)

            # Discipline risk rating
            seasons_played = max(1, player_perf['season_name'].nunique())
            yc_per_season  = total_yc / seasons_played
            risk_score = min(100, int(yc_per_season * 20 + total_rc * 25))
            risk_label = "🔴 HIGH" if risk_score > 60 else "🟡 MEDIUM" if risk_score > 30 else "🟢 LOW"
            risk_color = RED if risk_score > 60 else AMBER if risk_score > 30 else GREEN

            st.markdown(dedent_html(f"""
            <div style="background:#111827;border:1px solid #1f2d45;border-radius:10px;
                        padding:1rem;text-align:center;margin-top:.5rem;">
              <div style="font-size:.7rem;color:#6B7280;letter-spacing:2px;text-transform:uppercase;">DISCIPLINE RISK</div>
              <div style="font-family:'Outfit',sans-serif;font-size:2.5rem;color:{risk_color};">{risk_label}</div>
              <div style="font-size:.85rem;color:#9CA3AF;">{yc_per_season:.1f} yellow cards per season average</div>
            </div>"""), unsafe_allow_html=True)
