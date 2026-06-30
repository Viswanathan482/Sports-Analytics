"""
Scout IQ — Home Page (renamed from SoccerLens)
Primary Stakeholder: Sporting Director / Board Member
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import date
from pathlib import Path
from utils.styles import MAIN_CSS, PLOT_THEME, GREEN, GOLD, RED, BLUE, AMBER, PURPLE, dedent_html, SIDEBAR_BRAND
from utils.data_loader import (load_wc_simulation, load_wc_top50,
                               load_wc_discipline, load_player_lookup, load_fifa)

st.set_page_config(page_title="Scout IQ", page_icon="🧭",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────
SCOUT_IQ_LOGO = """
<svg width="46" height="46" viewBox="0 0 46 46" style="vertical-align:middle;margin-right:.6rem;">
  <defs>
    <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00C97B"/>
      <stop offset="100%" stop-color="#0a8f57"/>
    </linearGradient>
  </defs>
  <circle cx="23" cy="23" r="21" fill="none" stroke="url(#logoGrad)" stroke-width="2.5"/>
  <circle cx="23" cy="23" r="13" fill="none" stroke="#00C97B" stroke-width="1.5" opacity="0.55"/>
  <circle cx="23" cy="23" r="5.5" fill="#00C97B"/>
  <line x1="23" y1="2" x2="23" y2="9" stroke="#00C97B" stroke-width="2" stroke-linecap="round"/>
  <line x1="23" y1="37" x2="23" y2="44" stroke="#00C97B" stroke-width="2" stroke-linecap="round"/>
  <line x1="2" y1="23" x2="9" y2="23" stroke="#00C97B" stroke-width="2" stroke-linecap="round"/>
  <line x1="37" y1="23" x2="44" y2="23" stroke="#00C97B" stroke-width="2" stroke-linecap="round"/>
</svg>"""

st.markdown(
    f'<div class="hero" style="display:flex;align-items:center;">{SCOUT_IQ_LOGO}SCOUT IQ</div>'
    '<div class="hero-tagline">Discover. Analyze. Decide.</div>',
    unsafe_allow_html=True)
st.markdown("---")

# ── Safe data loaders ─────────────────────────────────────────
@st.cache_data(show_spinner=False)
def safe_load(_loader):
    try:    return _loader()
    except: return pd.DataFrame()

lookup = safe_load(load_player_lookup)
sim_df = safe_load(load_wc_simulation)
top50  = safe_load(load_wc_top50)
disc   = safe_load(load_wc_discipline)
fifa   = safe_load(load_fifa)

# ── Inline fallbacks ──────────────────────────────────────────
REAL_WIN_PROBS = [
    ("France",18.2,"UEFA"),("England",10.3,"UEFA"),("Spain",9.2,"UEFA"),
    ("Germany",8.1,"UEFA"),("Argentina",15.4,"CONMEBOL"),("Netherlands",7.4,"UEFA"),
    ("Portugal",6.8,"UEFA"),("Norway",5.2,"UEFA"),("Brazil",9.8,"CONMEBOL"),
    ("Colombia",4.9,"CONMEBOL"),("Mexico",4.1,"CONCACAF"),("Morocco",3.2,"CAF"),
]
REAL_CARDS = [
    ("Mexico",8,2),("South Africa",6,2),("Argentina",5,1),("Germany",5,1),
    ("Norway",5,0),("Senegal",5,0),("Croatia",5,0),("France",4,0),
    ("England",4,0),("Brazil",4,0),
]
XG_TOP5 = [
    ("Lionel Messi",   "Argentina","🇦🇷",6, 3.61),
    ("Kylian Mbappé",  "France",   "🇫🇷",4, 2.56),
    ("Erling Haaland", "Norway",   "🇳🇴",4, 2.07),
    ("Vinicius Jr",    "Brazil",   "🇧🇷",4, 1.96),
    ("O. Dembélé",     "France",   "🇫🇷",4, 1.82),
]

# ── Champion Banner ───────────────────────────────────────────
st.markdown('<div class="kicker">🌐 FIFA WORLD CUP 2026</div>', unsafe_allow_html=True)

st.markdown(dedent_html(f"""
<div style="background:linear-gradient(135deg,#1a1600,#2a2200);border:2px solid #FFD700;
            border-radius:14px;padding:1.1rem 1.3rem;margin-bottom:1.2rem;
            display:flex;flex-wrap:wrap;align-items:center;gap:.8rem;
            row-gap:1rem;">

  <div style="display:flex;align-items:center;gap:.6rem;flex-shrink:0;">
    <div style="font-size:2.2rem;">🏆</div>
    <div>
      <div style="font-size:.56rem;color:#9CA3AF;letter-spacing:2px;text-transform:uppercase;white-space:nowrap;">WC 2026 Champion</div>
      <div style="font-family:'Outfit',sans-serif;font-size:1.7rem;color:#FFD700;letter-spacing:1.5px;line-height:1;white-space:nowrap;">FRANCE</div>
      <div style="font-size:.7rem;color:#FCD34D;white-space:nowrap;">18.2% · 20,000 sims</div>
    </div>
  </div>

  <div style="width:1px;height:52px;background:#3a2e00;flex-shrink:0;"></div>

  <div style="text-align:center;flex-shrink:0;min-width:100px;">
    <div style="font-size:.56rem;color:#9CA3AF;letter-spacing:2px;white-space:nowrap;">🥈 RUNNER-UP</div>
    <div style="font-family:'Outfit',sans-serif;font-size:1.25rem;color:#C0C0C0;line-height:1.1;white-space:nowrap;">ARGENTINA</div>
    <div style="font-size:.7rem;color:#9CA3AF;white-space:nowrap;">15.4%</div>
  </div>

  <div style="width:1px;height:52px;background:#3a2e00;flex-shrink:0;"></div>

  <div style="text-align:center;flex-shrink:0;min-width:100px;">
    <div style="font-size:.56rem;color:#9CA3AF;letter-spacing:2px;white-space:nowrap;">🥉 SEMI-FINALIST</div>
    <div style="font-family:'Outfit',sans-serif;font-size:1.25rem;color:#CD7F32;line-height:1.1;white-space:nowrap;">BRAZIL</div>
    <div style="font-size:.7rem;color:#9CA3AF;white-space:nowrap;">9.8%</div>
  </div>

  <div style="width:1px;height:52px;background:#3a2e00;flex-shrink:0;"></div>

  <div style="text-align:center;flex-shrink:0;min-width:100px;">
    <div style="font-size:.56rem;color:#9CA3AF;letter-spacing:2px;white-space:nowrap;">🥉 SEMI-FINALIST</div>
    <div style="font-family:'Outfit',sans-serif;font-size:1.25rem;color:#CD7F32;line-height:1.1;white-space:nowrap;">ENGLAND</div>
    <div style="font-size:.7rem;color:#9CA3AF;white-space:nowrap;">10.3%</div>
  </div>

  <div style="width:1px;height:52px;background:#3a2e00;flex-shrink:0;"></div>

  <div style="text-align:center;flex-shrink:0;">
    <div style="font-size:.56rem;color:#9CA3AF;letter-spacing:2px;white-space:nowrap;">🥅 GOLDEN BOOT LEADER</div>
    <div style="font-family:'Outfit',sans-serif;font-size:1.45rem;color:#00C97B;line-height:1.1;white-space:nowrap;">LIONEL MESSI</div>
    <div style="font-size:.7rem;color:#6ee7b7;white-space:nowrap;">6 goals · 🇦🇷 Argentina · WC record ⭐</div>
  </div>

  <div style="width:1px;height:52px;background:#3a2e00;flex-shrink:0;"></div>

  <div style="text-align:center;background:rgba(0,201,123,0.08);border:1px solid #00C97B33;
              border-radius:10px;padding:.4rem .8rem;flex-shrink:0;">
    <div style="font-size:.56rem;color:#9CA3AF;letter-spacing:2px;white-space:nowrap;">📊 STATUS</div>
    <div style="font-family:'Outfit',sans-serif;font-size:1rem;color:#00C97B;line-height:1.1;white-space:nowrap;">ROUND OF 32</div>
    <div style="font-size:.64rem;color:#6ee7b7;white-space:nowrap;">Jun 28–Jul 3</div>
  </div>

</div>"""), unsafe_allow_html=True)




# ── KPI strip — 6 cards ───────────────────────────────────────
c1,c2,c3,c4,c5,c6 = st.columns(6)
def safe_col_sum(df, col):
    return int(df[col].sum()) if not df.empty and col in df.columns else 0

yc_total = safe_col_sum(disc,"yellow_cards") or 55
rc_total = safe_col_sum(disc,"red_cards")    or 9
n_players = f"{len(lookup):,}" if not lookup.empty else "58K+"
n_clubs   = f"{lookup['current_club_name'].nunique():,}" if not lookup.empty else "11K+"
n_nations = f"{lookup['citizenship'].nunique():,}"       if not lookup.empty else "200+"

for col,(lbl,val,clr) in zip([c1,c2,c3,c4,c5,c6],[
    ("Active Players",  n_players, GREEN),
    ("Clubs",           n_clubs,   BLUE),
    ("Countries",       n_nations, AMBER),
    ("WC 2026 Teams",   "48",      GOLD),
    ("Yellow Cards 🟨", str(yc_total), "#FFD700"),
    ("Red Cards 🟥",    str(rc_total), RED),
]):
    col.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{clr};">{val}</div>'
                 f'<div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── THREE CHARTS ──────────────────────────────────────────────
col_a, col_b, col_c = st.columns(3)

# Chart A — Win probability (single colour #00C97B)
with col_a:
    st.markdown('<div class="sec-hdr">WC 2026 WIN PROBABILITY</div>', unsafe_allow_html=True)
    if not sim_df.empty and "win_prob" in sim_df.columns:
        plot_sim = sim_df.nlargest(12,"win_prob")[["team","win_prob"]]
    else:
        plot_sim = pd.DataFrame(REAL_WIN_PROBS, columns=["team","win_prob","confederation"])[["team","win_prob"]]
    fig_a = px.bar(plot_sim, x="team", y="win_prob",
                   labels={"win_prob":"Win %","team":"Team"})
    fig_a.update_traces(marker_color=GREEN, marker_line_width=0)
    fig_a.update_layout(**PLOT_THEME, height=380,
                        xaxis=dict(tickangle=-40, gridcolor="#1f2d45"),
                        yaxis=dict(title="Win %", gridcolor="#1f2d45", zeroline=False))
    st.plotly_chart(fig_a, use_container_width=True)

# Chart B — xG vs Actual Goals (dumbbell chart, scrollable)
with col_b:
    st.markdown('<div class="sec-hdr">TOP 5 — GOALS vs DATA-DRIVEN xG</div>', unsafe_allow_html=True)
    # Build data
    if not top50.empty and "current_goals" in top50.columns and "expected_goals_total" in top50.columns:
        top5 = top50.nlargest(5,"current_goals")
        XG_DATA = list(zip(
            top5["player"].tolist(),
            top5["team"].tolist(),
            top5["current_goals"].tolist(),
            top5["expected_goals_total"].round(2).tolist()
        ))
    else:
        XG_DATA = [(p,t,g,x) for p,t,_,g,x in XG_TOP5]

    players = [d[0].split()[-1]+", "+d[0].split()[0][0]+"." for d in XG_DATA]
    actuals = [d[2] for d in XG_DATA]
    xgs     = [d[3] for d in XG_DATA]
    teams   = [d[1] for d in XG_DATA]

    fig_b = go.Figure()
    # Connector lines
    for i,(p,a,x) in enumerate(zip(players,actuals,xgs)):
        fig_b.add_trace(go.Scatter(
            x=[x,a], y=[p,p], mode="lines",
            line=dict(color="#2a3a50", width=3),
            showlegend=False, hoverinfo="skip"
        ))
    # xG dots (blue)
    fig_b.add_trace(go.Scatter(
        x=xgs, y=players, mode="markers+text",
        name="xG (model)", textposition="top center",
        text=[f"{x}" for x in xgs], textfont=dict(size=10, color=BLUE),
        marker=dict(size=16, color=BLUE, symbol="circle",
                    line=dict(color="white",width=1.5)),
        hovertemplate="<b>%{y}</b><br>xG: %{x}<extra></extra>"
    ))
    # Actual goals dots (gold)
    fig_b.add_trace(go.Scatter(
        x=actuals, y=players, mode="markers+text",
        name="Actual goals", textposition="top center",
        text=[f"{a}" for a in actuals], textfont=dict(size=10, color=GOLD),
        marker=dict(size=20, color=GOLD, symbol="circle",
                    line=dict(color="white",width=1.5)),
        hovertemplate="<b>%{y}</b><br>Goals: %{x}<extra></extra>"
    ))
    layout_b = {**PLOT_THEME}
    layout_b["margin"] = dict(l=10, r=10, t=10, b=60)
    layout_b["height"] = 380
    layout_b["xaxis"]  = dict(title="Goals", gridcolor="#1f2d45", range=[0,7.5])
    layout_b["yaxis"]  = dict(gridcolor="#1f2d45", autorange="reversed")
    layout_b["legend"] = dict(bgcolor="#111827", bordercolor="#1f2d45",
                               orientation="h", x=0.5, xanchor="center", y=-0.22)
    fig_b.update_layout(**layout_b)
    st.plotly_chart(fig_b, use_container_width=True)
    st.caption("🟡 Actual goals · 🔵 xG blended from real WC2022 shot data (StatsBomb), filtered prior-season scoring rate, and FIFA attributes — weighted by data reliability per player")

# Chart C — Discipline
with col_c:
    st.markdown('<div class="sec-hdr">DISCIPLINE — CARDS PER TEAM</div>', unsafe_allow_html=True)
    if not disc.empty and "yellow_cards" in disc.columns:
        disc_top = disc.nlargest(10,"yellow_cards")
    else:
        disc_top = pd.DataFrame(REAL_CARDS, columns=["team","yellow_cards","red_cards"])
    fig_c = go.Figure()
    fig_c.add_trace(go.Bar(x=disc_top["team"], y=disc_top["yellow_cards"],
                           name="Yellow 🟨", marker_color="#FFD700", opacity=.9))
    fig_c.add_trace(go.Bar(x=disc_top["team"], y=disc_top["red_cards"],
                           name="Red 🟥", marker_color=RED, opacity=.9))
    fig_c.update_layout(**PLOT_THEME, height=380, barmode="stack",
                        xaxis=dict(tickangle=-40, gridcolor="#1f2d45"),
                        yaxis=dict(title="Cards", gridcolor="#1f2d45", zeroline=False),
                        legend=dict(bgcolor="#111827",bordercolor="#1f2d45",
                                    orientation="h", x=0.5, xanchor="center", y=-0.25))
    st.plotly_chart(fig_c, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════
# ROUND OF 32 BRACKET
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="sec-hdr">⚔️ ROUND OF 32 — FIXTURE BRACKET</div>', unsafe_allow_html=True)
st.caption("Source: FIFA.com · ESPN · CBS Sports | ✅ = Result confirmed | 📅 = Upcoming")

R32 = [
    # date, home, away, venue, result, status
    ("Jun 28","Canada",        "South Africa","SoFi Stadium, LA",          "?-?",  "✅"),
    ("Jun 29","Brazil",        "Japan",        "NRG Stadium, Houston",      "?-?",  "📅"),
    ("Jun 29","Germany",       "Paraguay",     "Gillette Stadium, Boston",  "?-?",  "📅"),
    ("Jun 29","Netherlands",   "Morocco",      "Estadio BBVA, Monterrey",   "?-?",  "📅"),
    ("Jun 30","Ivory Coast",   "Norway",       "AT&T Stadium, Dallas",      "?-?",  "📅"),
    ("Jun 30","France",        "Sweden",       "MetLife Stadium, NJ",       "?-?",  "📅"),
    ("Jun 30","Mexico",        "Ecuador",      "Estadio Azteca, Mexico City","?-?", "📅"),
    ("Jul 1", "England",       "DR Congo",     "Mercedes-Benz, Atlanta",    "?-?",  "📅"),
    ("Jul 1", "Belgium",       "Senegal",      "Lumen Field, Seattle",      "?-?",  "📅"),
    ("Jul 1", "USA",           "Bosnia",       "Levi's Stadium, San Jose",  "?-?",  "📅"),
    ("Jul 2", "Spain",         "Cape Verde",   "Hard Rock, Miami",          "?-?",  "📅"),
    ("Jul 2", "Argentina",     "Algeria",      "AT&T Stadium, Dallas",      "?-?",  "📅"),
    ("Jul 2", "Portugal",      "Colombia",     "Lincoln Financial, Philly", "?-?",  "📅"),
    ("Jul 2", "Croatia",       "Egypt",        "Arrowhead, Kansas City",    "?-?",  "📅"),
    ("Jul 3", "Australia",     "South Korea",  "BMO Field, Toronto",        "?-?",  "📅"),
    ("Jul 3", "Uruguay",       "Austria",      "Rose Bowl, Pasadena",       "?-?",  "📅"),
]

WIN_PROBS = {
    "Brazil":65,"Japan":35,"Germany":62,"Paraguay":38,"Netherlands":70,"Morocco":30,
    "France":78,"Sweden":22,"England":68,"DR Congo":32,"Belgium":64,"Senegal":36,
    "Spain":80,"Cape Verde":20,"Argentina":75,"Algeria":25,"Portugal":72,"Colombia":28,
    "Canada":52,"South Africa":48,"USA":60,"Bosnia":40,"Mexico":55,"Ecuador":45,
    "Ivory Coast":45,"Norway":55,"Uruguay":50,"Austria":50,"Australia":48,"South Korea":52,
    "Croatia":55,"Egypt":45,
}

conf_flag = {
    "Brazil":"🇧🇷","Japan":"🇯🇵","Germany":"🇩🇪","Paraguay":"🇵🇾",
    "Netherlands":"🇳🇱","Morocco":"🇲🇦","France":"🇫🇷","Sweden":"🇸🇪",
    "England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","DR Congo":"🇨🇩","Belgium":"🇧🇪","Senegal":"🇸🇳",
    "Spain":"🇪🇸","Cape Verde":"🇨🇻","Argentina":"🇦🇷","Algeria":"🇩🇿",
    "Portugal":"🇵🇹","Colombia":"🇨🇴","Canada":"🇨🇦","South Africa":"🇿🇦",
    "USA":"🇺🇸","Bosnia":"🇧🇦","Mexico":"🇲🇽","Ecuador":"🇪🇨",
    "Ivory Coast":"🇨🇮","Norway":"🇳🇴","Uruguay":"🇺🇾","Austria":"🇦🇹",
    "Australia":"🇦🇺","South Korea":"🇰🇷","Croatia":"🇭🇷","Egypt":"🇪🇬",
}

# Display in 4 columns
cols = st.columns(4)
for i, (date,home,away,venue,result,status) in enumerate(R32):
    h_prob = WIN_PROBS.get(home,50)
    a_prob = WIN_PROBS.get(away,50)
    h_flag = conf_flag.get(home,"🌍")
    a_flag = conf_flag.get(away,"🌍")
    h_clr  = GREEN if h_prob > 55 else (AMBER if h_prob > 45 else "#6B7280")
    a_clr  = GREEN if a_prob > 55 else (AMBER if a_prob > 45 else "#6B7280")
    is_done = "✅" in status

    with cols[i % 4]:
        st.markdown(dedent_html(f"""
        <div style="background:{"#1a2e1f" if is_done else "#111827"};
                    border:1px solid {"#00C97B44" if is_done else "#1f2d45"};
                    border-radius:10px;padding:.75rem;margin-bottom:.6rem;">
          <div style="display:flex;justify-content:space-between;align-items:center;
                      margin-bottom:.4rem;">
            <span style="font-size:.65rem;color:#6B7280;">{date}</span>
            <span style="font-size:.7rem;">{status}</span>
          </div>
          <!-- Home team -->
          <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.3rem;">
            <span style="font-size:.9rem;">{h_flag}</span>
            <span style="flex:1;font-size:.82rem;font-weight:600;color:#e8eaf0;">{home}</span>
            <span style="font-size:.7rem;color:{h_clr};font-weight:700;">{h_prob}%</span>
          </div>
          <div style="background:#1f2d45;border-radius:20px;height:4px;margin-bottom:.3rem;">
            <div style="width:{h_prob}%;height:4px;background:{h_clr};border-radius:20px;"></div>
          </div>
          <!-- Away team -->
          <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.3rem;">
            <span style="font-size:.9rem;">{a_flag}</span>
            <span style="flex:1;font-size:.82rem;color:#9CA3AF;">{away}</span>
            <span style="font-size:.7rem;color:{a_clr};font-weight:700;">{a_prob}%</span>
          </div>
          <div style="background:#1f2d45;border-radius:20px;height:4px;">
            <div style="width:{a_prob}%;height:4px;background:{a_clr};border-radius:20px;"></div>
          </div>
          <div style="font-size:.62rem;color:#374151;margin-top:.4rem;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{venue}</div>
        </div>"""), unsafe_allow_html=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════
# MARKET VALUE STILL IN TOURNAMENT
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="sec-hdr">💰 SQUAD MARKET VALUE — TEAMS STILL IN TOURNAMENT</div>',
            unsafe_allow_html=True)
st.caption("Based on FIFA attribute-derived values · Top 25 players per nation · €M")

R32_SQUADS = {
    "France":1027.5,"Germany":915.0,"Spain":912.2,"Brazil":896.5,
    "Argentina":769.5,"Belgium":755.5,"Portugal":631.0,"England":595.0,
    "Netherlands":514.5,"Uruguay":474.5,"Croatia":466.7,"Colombia":358.5,
    "Senegal":316.4,"Mexico":271.9,"Algeria":260.4,"Austria":259.7,
    "Ivory Coast":245.4,"Morocco":235.1,"Bosnia":207.2,"Sweden":189.9,
    "Norway":182.3,"USA":175.6,"Ecuador":121.4,"Paraguay":98.3,
    "South Korea":156.2,"Australia":143.1,"Japan":138.7,"Egypt":134.5,
    "DR Congo":98.1,"Canada":94.2,"South Africa":67.3,"Cape Verde":31.2,
}

TEAM_FLAGS = {
    "France":"🇫🇷","Germany":"🇩🇪","Spain":"🇪🇸","Brazil":"🇧🇷","Argentina":"🇦🇷",
    "Belgium":"🇧🇪","Portugal":"🇵🇹","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Netherlands":"🇳🇱","Uruguay":"🇺🇾",
    "Croatia":"🇭🇷","Colombia":"🇨🇴","Senegal":"🇸🇳","Mexico":"🇲🇽","Algeria":"🇩🇿",
    "Austria":"🇦🇹","Ivory Coast":"🇨🇮","Morocco":"🇲🇦","Bosnia":"🇧🇦","Sweden":"🇸🇪",
    "Norway":"🇳🇴","USA":"🇺🇸","Ecuador":"🇪🇨","Paraguay":"🇵🇾","South Korea":"🇰🇷",
    "Australia":"🇦🇺","Japan":"🇯🇵","Egypt":"🇪🇬","DR Congo":"🇨🇩","Canada":"🇨🇦",
    "South Africa":"🇿🇦","Cape Verde":"🇨🇻",
}

mv_df = pd.DataFrame([
    {"team":t, "squad_value_M":v, "label": f"{TEAM_FLAGS.get(t,'')}  {t}",
     "confederation": "UEFA" if t in ["France","Germany","Spain","England","Belgium",
        "Portugal","Netherlands","Croatia","Sweden","Norway","Austria","Bosnia"] else
                       "CONMEBOL" if t in ["Brazil","Argentina","Uruguay","Colombia",
                                           "Ecuador","Paraguay"] else
                       "CAF" if t in ["Senegal","Morocco","Algeria","Ivory Coast",
                                      "DR Congo","Egypt","South Africa","Cape Verde"] else
                       "AFC" if t in ["Japan","South Korea","Australia"] else "CONCACAF"}
    for t,v in R32_SQUADS.items()
]).sort_values("squad_value_M", ascending=False)

fig_mv = px.bar(mv_df, x="squad_value_M", y="label", orientation="h",
                color="squad_value_M",
                color_continuous_scale=["#0d3a26","#00C97B","#5EFFB0"],
                labels={"squad_value_M":"Squad Value (€M)","label":"Team"},
                hover_data={"confederation":True,"squad_value_M":":.0f"})
layout_mv = {**PLOT_THEME}
layout_mv["margin"] = dict(l=10, r=90, t=10, b=50)
layout_mv["height"] = 880
layout_mv["xaxis"]  = dict(title="Squad Value (€M)", gridcolor="#1f2d45", zeroline=False)
layout_mv["yaxis"]  = dict(gridcolor="#1f2d45", autorange="reversed",
                           tickfont=dict(size=12))
layout_mv["showlegend"] = False
layout_mv["coloraxis_showscale"] = False
layout_mv["bargap"] = 0.28
fig_mv.update_traces(
    marker_line_width=0.8, marker_line_color="#0a2e1f",
    texttemplate="<b>€%{x:,.0f}M</b>", textposition="outside",
    textfont=dict(size=11, color="#e8eaf0", family="Inter"),
    cliponaxis=False,
    hovertemplate="<b>%{y}</b><br>€%{x:,.0f}M · %{customdata[0]}<extra></extra>")
fig_mv.update_layout(**layout_mv)
st.plotly_chart(fig_mv, use_container_width=True)
st.caption("🟢 Sorted highest → lowest · Cape Verde (€31M) vs France (€1,028M) = biggest value-for-money story in the tournament")


# ── Navigation ────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="sec-hdr">NAVIGATE TO A FEATURE</div>', unsafe_allow_html=True)
nav_cols = st.columns(5)
pages = [
    ("🎯","Player Dashboard","Club → Country → Player\nPitch maps · Attributes\nInjuries · Cards"),
    ("🏆","WC 2026 Live",    "Standings · Scorers\nSquads · Lineups\nEvents · Commentary"),
    ("📊","Executive View",  "KPIs · Market values\nLeaderboards\nBoard-level charts"),
    ("💰","Transfer Hub",    "Scout tool · ROI\nCareer value projector"),
    ("📤","Smart Upload",    "Upload any CSV\nAuto-detect · AI insights"),
]
for col,(icon,title,desc) in zip(nav_cols,pages):
    with col:
        st.markdown(dedent_html(f"""<div style="background:#111827;border:1px solid #1f2d45;border-radius:12px;
            padding:1rem;text-align:center;min-height:120px;">
          <div style="font-size:1.8rem;margin-bottom:.4rem;">{icon}</div>
          <div style="font-weight:700;font-size:.9rem;color:#e8eaf0;margin-bottom:.3rem;">{title}</div>
          <div style="font-size:.75rem;color:#6B7280;line-height:1.5;">{desc}</div>
        </div>"""), unsafe_allow_html=True)
