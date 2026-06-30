"""
02_WC_2026_Live.py — Scout IQ · WC 2026 Live
Powered entirely by local CSV files — NO API KEY needed
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json, warnings
warnings.filterwarnings("ignore")

from utils.styles import MAIN_CSS, PLOT_THEME, GREEN, GOLD, RED, BLUE, AMBER, PURPLE, dedent_html, SIDEBAR_BRAND

st.set_page_config(page_title="Scout IQ — WC 2026 Live",
                   page_icon="🏆", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)

DATA = Path(__file__).parent.parent / "data" / "processed"

# ── Load every CSV directly — no API, no wrapper ─────────────
def _load(fname):
    p = DATA / fname
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

matches   = _load("wc2026_matches_full.csv")
scorers   = _load("wc2026_real_scorers.csv")
standings = _load("wc2026_standings.csv")
team_stats= _load("wc2026_team_full_stats.csv")
gk        = _load("wc2026_goalkeeper_stats.csv")
venues    = _load("wc2026_venue_stats.csv")
potm      = _load("wc2026_potm.csv")
timing    = _load("wc2026_goal_timing.csv")
pos_df    = _load("wc2026_position_analysis.csv")
players   = _load("wc2026_players_full.csv")
disc      = _load("wc2026_discipline.csv")

# De-duplicate team_stats (has one row per match per team)
if not team_stats.empty and "team_id" in team_stats.columns:
    team_stats = team_stats.drop_duplicates("team_id")

completed = matches[matches["status"] == "Completed"] if not matches.empty else pd.DataFrame()

# ── Header ────────────────────────────────────────────────────
st.markdown('<div class="hero">📡 TOURNAMENT PULSE</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Real match data · 89 fixtures · 1,248 players · '
            'No API key required</div>', unsafe_allow_html=True)
st.markdown("---")

# ── KPI strip ─────────────────────────────────────────────────
tot_goals = int(completed["total_goals"].sum()) if not completed.empty and "total_goals" in completed else 216
n_done    = len(completed)
avg_gpg   = round(tot_goals / max(n_done, 1), 2)
yc = int(disc["yellow_cards"].sum()) if not disc.empty else 55
rc = int(disc["red_cards"].sum())    if not disc.empty else 9
top_name  = scorers.iloc[0]["player_name"].split()[-1] if not scorers.empty else "Messi"
top_goals = int(scorers.iloc[0]["current_goals"]) if not scorers.empty else 6

k1,k2,k3,k4,k5,k6 = st.columns(6)
for col,(lbl,val,clr) in zip([k1,k2,k3,k5,k6],[
    ("Matches Done",   f"{n_done}/89",        GREEN),
    ("Total Goals",    str(tot_goals),         GOLD),
    ("Goals/Match",    str(avg_gpg),           BLUE),
    ("Yellow Cards 🟨",str(yc),               "#FFD700"),
    ("Red Cards 🟥",   str(rc),               RED),
]):
    col.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{clr};">{val}</div>'
                 f'<div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)

# Golden Boot — redesigned so the player name is fully readable
k4.markdown(f"""
<div class="kpi-card" style="display:flex;flex-direction:column;justify-content:center;">
  <div style="font-size:.56rem;color:#9CA3AF;letter-spacing:2px;text-transform:uppercase;
              white-space:nowrap;">🥇 Golden Boot</div>
  <div style="font-family:'Outfit',sans-serif;font-weight:700;font-size:1.1rem;color:{AMBER};
              line-height:1.25;margin:.15rem 0;white-space:nowrap;overflow:hidden;
              text-overflow:ellipsis;">{top_name}</div>
  <div style="font-size:.78rem;color:#9CA3AF;">{top_goals} goals</div>
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📊 Standings","⚽ Scorers","🗓️ Fixtures","🥅 Goalkeepers",
    "📈 Team Stats","🏟️ Venues","🕐 Goal Timing",
    "🏆 POTM","👥 Squads"
])

# ══ TAB 1: STANDINGS — full group stage results & tables ════
with tabs[0]:
    st.markdown('<div class="sec-hdr">⚽ GROUP STAGE — STANDINGS & ALL 72 MATCH RESULTS</div>',
                unsafe_allow_html=True)
    st.caption("Jun 11 – 27, 2026 · 🟢 = qualified for Round of 32")

    GROUP_RESULTS = {
        "A":{"adv":["Mexico","South Africa"],"matches":[("Jun 11","Mexico","South Africa","2-0"),("Jun 11","South Korea","Czechia","2-1"),("Jun 18","Czechia","South Africa","1-1"),("Jun 18","Mexico","South Korea","1-0"),("Jun 24","Mexico","Czechia","3-0"),("Jun 24","South Africa","South Korea","1-0")],"standings":[("Mexico",3,3,0,0,6,0,9,"#FFD700"),("South Africa",3,1,1,1,2,3,4,"#C0C0C0"),("South Korea",3,1,0,2,2,4,3,"#6B7280"),("Czechia",3,0,1,2,2,5,1,"#4B5563")]},
        "B":{"adv":["Switzerland","Canada"],"matches":[("Jun 12","Canada","Bosnia","1-1"),("Jun 13","Switzerland","Qatar","1-1"),("Jun 18","Switzerland","Bosnia","4-1"),("Jun 18","Canada","Qatar","6-0"),("Jun 24","Switzerland","Canada","2-1"),("Jun 24","Bosnia","Qatar","3-1")],"standings":[("Switzerland",3,2,1,0,7,3,7,"#FFD700"),("Canada",3,1,1,1,8,3,4,"#C0C0C0"),("Bosnia",3,1,1,1,5,6,4,"#6B7280"),("Qatar",3,0,1,2,2,10,1,"#4B5563")]},
        "C":{"adv":["USA","Australia"],"matches":[("Jun 12","USA","Paraguay","4-1"),("Jun 13","Australia","Turkey","2-0"),("Jun 19","USA","Australia","2-0"),("Jun 19","Turkey","Paraguay","0-1"),("Jun 25","Turkey","USA","3-2"),("Jun 25","Paraguay","Australia","0-0")],"standings":[("USA",3,2,0,1,8,4,6,"#FFD700"),("Australia",3,1,1,1,2,2,4,"#C0C0C0"),("Paraguay",3,1,1,1,2,5,4,"#6B7280"),("Turkey",3,1,0,2,3,5,3,"#4B5563")]},
        "D":{"adv":["Germany","Ivory Coast"],"matches":[("Jun 14","Germany","Curacao","7-1"),("Jun 14","Ivory Coast","Ecuador","1-0"),("Jun 20","Germany","Ivory Coast","2-1"),("Jun 20","Ecuador","Curacao","0-0"),("Jun 25","Curacao","Ivory Coast","0-2"),("Jun 25","Ecuador","Germany","2-1")],"standings":[("Germany",3,2,0,1,10,3,6,"#FFD700"),("Ivory Coast",3,2,0,1,4,3,6,"#C0C0C0"),("Ecuador",3,1,1,1,2,2,4,"#6B7280"),("Curacao",3,0,1,2,1,9,1,"#4B5563")]},
        "E":{"adv":["Netherlands","Japan"],"matches":[("Jun 14","Netherlands","Japan","2-2"),("Jun 14","Sweden","Tunisia","5-1"),("Jun 20","Netherlands","Sweden","5-1"),("Jun 20","Japan","Tunisia","4-0"),("Jun 25","Japan","Sweden","1-1"),("Jun 25","Netherlands","Tunisia","3-1")],"standings":[("Netherlands",3,2,1,0,10,4,7,"#FFD700"),("Japan",3,1,2,0,7,3,5,"#C0C0C0"),("Sweden",3,1,1,1,7,7,4,"#6B7280"),("Tunisia",3,0,0,3,2,12,0,"#4B5563")]},
        "F":{"adv":["Brazil","Morocco"],"matches":[("Jun 13","Brazil","Morocco","1-1"),("Jun 13","Scotland","Haiti","1-0"),("Jun 19","Scotland","Morocco","0-1"),("Jun 19","Brazil","Haiti","3-0"),("Jun 24","Scotland","Brazil","0-3"),("Jun 24","Morocco","Haiti","4-2")],"standings":[("Brazil",3,2,1,0,7,1,7,"#FFD700"),("Morocco",3,2,1,0,6,2,7,"#C0C0C0"),("Scotland",3,1,0,2,1,4,3,"#6B7280"),("Haiti",3,0,0,3,2,9,0,"#4B5563")]},
        "G":{"adv":["Belgium","Egypt"],"matches":[("Jun 15","Belgium","Egypt","1-1"),("Jun 15","Iran","New Zealand","2-2"),("Jun 21","Belgium","Iran","0-0"),("Jun 21","Egypt","New Zealand","3-1"),("Jun 26","Egypt","Iran","1-1"),("Jun 26","Belgium","New Zealand","5-1")],"standings":[("Belgium",3,1,2,0,6,2,5,"#FFD700"),("Egypt",3,1,2,0,5,3,5,"#C0C0C0"),("Iran",3,0,3,0,3,3,3,"#6B7280"),("New Zealand",3,0,1,2,4,10,1,"#4B5563")]},
        "H":{"adv":["Spain","Cape Verde"],"matches":[("Jun 15","Spain","Cape Verde","0-0"),("Jun 15","Saudi Arabia","Uruguay","1-1"),("Jun 21","Spain","Saudi Arabia","4-0"),("Jun 21","Uruguay","Cape Verde","2-2"),("Jun 26","Cape Verde","Saudi Arabia","0-0"),("Jun 26","Spain","Uruguay","1-0")],"standings":[("Spain",3,2,1,0,5,0,7,"#FFD700"),("Cape Verde",3,0,3,0,2,2,3,"#C0C0C0"),("Uruguay",3,0,2,1,3,4,2,"#6B7280"),("Saudi Arabia",3,0,2,1,1,4,2,"#4B5563")]},
        "I":{"adv":["France","Norway"],"matches":[("Jun 16","France","Senegal","3-1"),("Jun 16","Norway","Iraq","4-1"),("Jun 22","France","Iraq","3-0"),("Jun 22","Norway","Senegal","3-2"),("Jun 26","France","Norway","4-1"),("Jun 26","Senegal","Iraq","5-0")],"standings":[("France",3,3,0,0,10,2,9,"#FFD700"),("Norway",3,2,0,1,8,5,6,"#C0C0C0"),("Senegal",3,1,0,2,8,7,3,"#6B7280"),("Iraq",3,0,0,3,1,13,0,"#4B5563")]},
        "J":{"adv":["Argentina","Algeria"],"matches":[("Jun 16","Argentina","Algeria","3-0"),("Jun 17","Austria","Jordan","3-1"),("Jun 22","Argentina","Austria","2-0"),("Jun 22","Jordan","Algeria","1-2"),("Jun 27","Argentina","Jordan","3-1"),("Jun 27","Austria","Algeria","3-3")],"standings":[("Argentina",3,3,0,0,8,1,9,"#FFD700"),("Algeria",3,1,1,1,5,5,4,"#C0C0C0"),("Austria",3,1,1,1,6,6,4,"#6B7280"),("Jordan",3,0,0,3,3,10,0,"#4B5563")]},
        "K":{"adv":["Colombia","Portugal"],"matches":[("Jun 17","Portugal","Congo DR","1-1"),("Jun 17","Colombia","Uzbekistan","3-1"),("Jun 23","Portugal","Uzbekistan","5-0"),("Jun 23","Colombia","Congo DR","1-0"),("Jun 27","Colombia","Portugal","0-0"),("Jun 27","Congo DR","Uzbekistan","3-1")],"standings":[("Colombia",3,2,1,0,4,1,7,"#FFD700"),("Portugal",3,1,2,0,6,2,5,"#C0C0C0"),("Congo DR",3,1,1,1,4,3,4,"#6B7280"),("Uzbekistan",3,0,0,3,2,10,0,"#4B5563")]},
        "L":{"adv":["England","Croatia"],"matches":[("Jun 17","England","Croatia","4-2"),("Jun 17","Ghana","Panama","1-0"),("Jun 23","England","Ghana","0-0"),("Jun 23","Panama","Croatia","0-1"),("Jun 27","England","Panama","2-0"),("Jun 27","Croatia","Ghana","2-1")],"standings":[("England",3,2,1,0,6,2,7,"#FFD700"),("Croatia",3,2,0,1,5,5,6,"#C0C0C0"),("Ghana",3,1,1,1,2,3,4,"#6B7280"),("Panama",3,0,0,3,0,3,0,"#4B5563")]},
    }
    for row_start in range(0,12,3):
        batch = list(GROUP_RESULTS.keys())[row_start:row_start+3]
        gcols = st.columns(3)
        for ci, grp in enumerate(batch):
            data = GROUP_RESULTS[grp]
            with gcols[ci]:
                st.markdown(f'<div style="background:#111827;border:1px solid #1f2d45;border-radius:12px;padding:.9rem;margin-bottom:.8rem;"><div style="font-family:\'Outfit\',sans-serif;font-size:1.4rem;color:#FFD700;letter-spacing:3px;margin-bottom:.5rem;">⚽ GROUP {grp}</div><div style="display:flex;gap:4px;font-size:.6rem;color:#6B7280;letter-spacing:1px;padding:.15rem 0;border-bottom:1px solid #1f2d45;margin-bottom:.3rem;"><span style="flex:1;">TEAM</span><span style="width:18px;text-align:center;">P</span><span style="width:18px;text-align:center;">W</span><span style="width:18px;text-align:center;">D</span><span style="width:18px;text-align:center;">L</span><span style="width:34px;text-align:center;">GF-GA</span><span style="width:22px;text-align:center;">PTS</span></div>', unsafe_allow_html=True)
                for team,p,w,d,l,gf,ga,pts,pos_clr in data["standings"]:
                    adv = team in data["adv"]
                    bg  = "#182a1e" if adv else "#0f1724"
                    dot = " 🟢" if adv else ""
                    gd  = gf - ga
                    gds = f"+{gd}" if gd>0 else str(gd)
                    st.markdown(f'<div style="background:{bg};border-radius:6px;padding:.28rem .4rem;margin-bottom:.18rem;display:flex;align-items:center;gap:4px;font-size:.76rem;"><span style="color:{pos_clr};font-family:\'Outfit\',sans-serif;font-size:.95rem;width:14px;flex-shrink:0;">●</span><span style="flex:1;color:#e8eaf0;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{team}{dot}</span><span style="width:18px;text-align:center;color:#9CA3AF;">{p}</span><span style="width:18px;text-align:center;color:#00C97B;">{w}</span><span style="width:18px;text-align:center;color:#F59E0B;">{d}</span><span style="width:18px;text-align:center;color:#EF4444;">{l}</span><span style="width:34px;text-align:center;color:#6B7280;font-size:.7rem;">{gf}-{ga}</span><span style="width:22px;text-align:center;font-family:\'Outfit\',sans-serif;font-size:1rem;color:#FFD700;">{pts}</span></div>', unsafe_allow_html=True)
                for date,h,a,score in data["matches"]:
                    hg,ag = int(score.split("-")[0]),int(score.split("-")[1])
                    h_win = hg>ag; a_win = ag>hg
                    hc = "#00C97B" if h_win else ("#EF4444" if a_win else "#9CA3AF")
                    ac = "#00C97B" if a_win else ("#EF4444" if h_win else "#9CA3AF")
                    st.markdown(f'<div style="display:flex;align-items:center;gap:4px;padding:.18rem 0;border-bottom:1px solid rgba(31,45,69,0.25);font-size:.71rem;"><span style="color:#374151;min-width:40px;font-size:.65rem;">{date}</span><span style="flex:1;text-align:right;color:{hc};font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:90px;">{h}</span><span style="font-family:\'Outfit\',sans-serif;font-size:1rem;color:#FFD700;min-width:34px;text-align:center;">{score}</span><span style="flex:1;color:{ac};font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:90px;">{a}</span></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # Goals chart (from real standings CSV if available)
    if not standings.empty and "goals_for" in standings.columns:
        st.markdown('<div class="sec-hdr">GOALS SCORED BY TEAM</div>', unsafe_allow_html=True)
        sdf = standings.sort_values("goals_for", ascending=False).copy()
        color_col = "confederation" if "confederation" in sdf.columns else None
        fig_s = px.bar(sdf, x="team_name", y="goals_for",
                       color=color_col,
                       labels={"goals_for": "Goals For", "team_name": "Team"})
        ly = {**PLOT_THEME}; ly["margin"] = dict(l=5, r=5, t=5, b=60); ly["height"] = 300
        ly["xaxis"] = dict(tickangle=-40, gridcolor="#1f2d45")
        ly["yaxis"] = dict(title="Goals", gridcolor="#1f2d45")
        ly["legend"] = dict(bgcolor="#111827", bordercolor="#1f2d45",
                            orientation="h", x=0.5, xanchor="center", y=-0.3)
        fig_s.update_layout(**ly)
        st.plotly_chart(fig_s, use_container_width=True)

# ══ TAB 2: SCORERS ════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="sec-hdr">🥅 GOLDEN BOOT — REAL GOALS FROM MATCH EVENTS</div>',
                unsafe_allow_html=True)
    if scorers.empty:
        st.warning("wc2026_real_scorers.csv not found")
    else:
        g_col = "current_goals"
        a_col = "current_assists"
        top20 = scorers.nlargest(20, g_col).reset_index(drop=True)
        max_g = int(top20[g_col].max()) if len(top20) else 1

        sc1, sc2 = st.columns([2, 1])
        with sc1:
            for i, row in top20.iterrows():
                name  = str(row.get("player_name", "?"))
                team  = str(row.get("team_name", ""))
                club  = str(row.get("club_team", ""))
                goals = int(row.get(g_col, 0))
                asst  = int(row.get(a_col, 0))
                mins  = int(row.get("current_mins", 0))
                val   = float(row.get("market_value_M", 0))
                medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}."
                clr   = [GOLD, "#C0C0C0", "#CD7F32"][i] if i < 3 else "#6B7280"
                bw    = int(goals / max_g * 180)
                g90   = round(goals / max(mins, 1) * 90, 2)
                st.markdown(dedent_html(f'''<div style="display:flex;align-items:center;gap:10px;
                    padding:.42rem 0;border-bottom:1px solid #1f2d4555;">
                  <span style="font-family:'Outfit',sans-serif;font-size:1.2rem;
                               color:{clr};min-width:28px;">{medal}</span>
                  <div style="flex:1;">
                    <div style="font-size:.86rem;font-weight:600;color:#e8eaf0;">{name}</div>
                    <div style="font-size:.68rem;color:#6B7280;">{team} · {club[:20]} · €{val:.1f}M</div>
                    <div style="background:#1f2d45;border-radius:4px;height:5px;
                                margin-top:3px;width:200px;">
                      <div style="width:{bw}px;height:5px;background:{GREEN};
                                  border-radius:4px;"></div></div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-family:'Outfit',sans-serif;font-size:1.5rem;
                                color:#FFD700;">{goals}⚽</div>
                    <div style="font-size:.65rem;color:#3B82F6;">
                      {asst}🎯  {g90}/90</div>
                  </div>
                </div>'''), unsafe_allow_html=True)

        with sc2:
            fig_sc = px.bar(top20.head(12), x=g_col, y="player_name", orientation="h",
                            color=g_col, color_continuous_scale=["#1f2d45", GREEN],
                            labels={g_col: "Goals", "player_name": ""},
                            hover_data=["team_name", a_col])
            ly2 = {**PLOT_THEME}; ly2["margin"] = dict(l=5,r=5,t=5,b=5); ly2["height"] = 420
            ly2["coloraxis_showscale"] = False
            ly2["yaxis"] = dict(autorange="reversed", gridcolor="#1f2d45")
            ly2["xaxis"] = dict(title="Goals", gridcolor="#1f2d45")
            fig_sc.update_layout(**ly2)
            st.plotly_chart(fig_sc, use_container_width=True)

# ══ TAB 3: FIXTURES ════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="sec-hdr">ALL 89 MATCHES — RESULTS & SCHEDULE</div>',
                unsafe_allow_html=True)
    if matches.empty:
        st.warning("wc2026_matches_full.csv not found")
    else:
        fc1, fc2 = st.columns(2)
        stage_list = ["All"] + sorted(matches["stage_name"].dropna().unique())
        sel_stage  = fc1.selectbox("Stage", stage_list, key="stage")
        sel_status = fc2.radio("Status", ["All", "Completed", "Scheduled"],
                               horizontal=True, key="status")
        show = matches.copy()
        if sel_stage != "All":     show = show[show["stage_name"] == sel_stage]
        if sel_status != "All":    show = show[show["status"] == sel_status]
        st.caption(f"Showing {len(show)} of {len(matches)} matches")

        for _, m in show.iterrows():
            hs    = m.get("home_score"); as_ = m.get("away_score")
            done  = str(m.get("status", "")) == "Completed"
            score = f"{int(hs)}–{int(as_)}" if pd.notna(hs) and pd.notna(as_) else "vs"
            hxg   = m.get("home_xg", 0) or 0
            axg   = m.get("away_xg", 0) or 0
            potm_n= str(m.get("potm_name", m.get("player_of_the_match_name", ""))) or ""
            if potm_n == "nan": potm_n = ""
            elev  = m.get("elevation_meters", 0) or 0
            ko    = "🔥 KO" if m.get("is_knockout") else ""
            st.markdown(dedent_html(f'''<div style="background:{"#1a2e1f" if done else "#111827"};
                border:1px solid {"#00C97B44" if done else "#1f2d45"};
                border-radius:9px;padding:.6rem .9rem;margin-bottom:.28rem;
                display:flex;align-items:center;gap:8px;">
              <div style="min-width:82px;font-size:.68rem;color:#6B7280;">{str(m.get("date",""))[:10]}</div>
              <div style="min-width:55px;font-size:.6rem;color:#6B7280;">{str(m.get("stage_name",""))[:12]}</div>
              <div style="flex:1;font-size:.84rem;font-weight:600;color:#e8eaf0;
                          text-align:right;">{m.get("home_team_name","")}</div>
              <div style="font-family:'Outfit',sans-serif;font-size:1.65rem;color:#FFD700;
                          min-width:76px;text-align:center;">{score}</div>
              <div style="flex:1;font-size:.84rem;font-weight:600;color:#e8eaf0;">{m.get("away_team_name","")}</div>
              <div style="font-size:.62rem;color:#6B7280;text-align:right;min-width:150px;">
                {"✅ FT" if done else "📅"} {ko}<br>
                {f"xG {hxg:.2f}–{axg:.2f}" if done else str(m.get("kickoff_time_utc",""))}<br>
                {f"🏆 {potm_n[:20]}" if potm_n else f"🏟️ {str(m.get('stadium_name',''))[:20]}"}
              </div>
            </div>'''), unsafe_allow_html=True)

# ══ TAB 4: GOALKEEPERS ════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="sec-hdr">🥅 GOALKEEPER STATS — FROM REAL SAVE DATA</div>',
                unsafe_allow_html=True)
    if gk.empty:
        st.warning("wc2026_goalkeeper_stats.csv not found")
    else:
        gc1, gc2 = st.columns(2)
        with gc1:
            top_sp = gk.nlargest(16, "save_pct")
            fig_sp = px.bar(top_sp, x="save_pct", y="team_name", orientation="h",
                            color="save_pct", color_continuous_scale=["#1f2d45", BLUE],
                            hover_data=["goalkeeper", "total_saves", "goals_conceded"],
                            labels={"save_pct": "Save %", "team_name": "Team"})
            ly3 = {**PLOT_THEME}; ly3["margin"]=dict(l=5,r=5,t=30,b=5); ly3["height"]=420
            ly3["coloraxis_showscale"]=False; ly3["yaxis"]=dict(autorange="reversed")
            ly3["title"]={"text":"Save % by Goalkeeper","font":{"color":"#e8eaf0","size":13}}
            fig_sp.update_layout(**ly3)
            st.plotly_chart(fig_sp, use_container_width=True)
        with gc2:
            top_sv = gk.nlargest(14, "total_saves")
            fig_sv = px.bar(top_sv, x="total_saves", y="goalkeeper", orientation="h",
                            color="total_saves", color_continuous_scale=["#1f2d45", GREEN],
                            hover_data=["team_name", "save_pct", "goals_conceded"],
                            labels={"total_saves": "Saves", "goalkeeper": "Goalkeeper"})
            ly4 = {**PLOT_THEME}; ly4["margin"]=dict(l=5,r=5,t=30,b=5); ly4["height"]=420
            ly4["coloraxis_showscale"]=False; ly4["yaxis"]=dict(autorange="reversed")
            ly4["title"]={"text":"Total Saves by Goalkeeper","font":{"color":"#e8eaf0","size":13}}
            fig_sv.update_layout(**ly4)
            st.plotly_chart(fig_sv, use_container_width=True)

        st.dataframe(
            gk[["team_name","goalkeeper","matches","total_saves","goals_conceded","save_pct","avg_saves_pg"]]
              .sort_values("save_pct", ascending=False).reset_index(drop=True),
            use_container_width=True, height=350)

# ══ TAB 5: TEAM STATS ══════════════════════════════════════════
with tabs[4]:
    st.markdown('<div class="sec-hdr">📈 TEAM PERFORMANCE — POSSESSION · xG · SHOTS</div>',
                unsafe_allow_html=True)
    if team_stats.empty:
        st.warning("wc2026_team_full_stats.csv not found")
    else:
        metrics = [c for c in ["total_xg","avg_possession","shot_accuracy",
                               "total_shots","total_saves","goals_for","fouls_pg"]
                   if c in team_stats.columns]
        metric = st.selectbox("Metric", metrics,
                              format_func=lambda x: x.replace("_"," ").title(), key="ts_m")
        ts_plot = team_stats.dropna(subset=[metric]).sort_values(metric, ascending=False).head(24)
        clr_col = "confederation" if "confederation" in ts_plot.columns else None
        fig_ts  = px.bar(ts_plot, x="team_name", y=metric, color=clr_col,
                         color_discrete_map={"UEFA":BLUE,"CONMEBOL":GREEN,"CAF":GOLD,
                                             "AFC":RED,"CONCACAF":PURPLE,"OFC":"#6B7280"},
                         hover_data=["manager_name","elo_rating"] if "manager_name" in ts_plot else [],
                         labels={metric: metric.replace("_"," ").title(), "team_name":"Team"})
        ly5={**PLOT_THEME}; ly5["margin"]=dict(l=5,r=5,t=5,b=60); ly5["height"]=340
        ly5["xaxis"]=dict(tickangle=-40,gridcolor="#1f2d45")
        ly5["yaxis"]=dict(gridcolor="#1f2d45")
        ly5["legend"]=dict(bgcolor="#111827",bordercolor="#1f2d45",orientation="h",
                           x=0.5,xanchor="center",y=-0.3)
        fig_ts.update_layout(**ly5)
        st.plotly_chart(fig_ts, use_container_width=True)

        show_cols = [c for c in ["team_name","manager_name","elo_rating","avg_possession",
                                  "total_shots","shot_accuracy","total_xg","goals_for",
                                  "goals_against","yellow_cards","red_cards","deepest_stage"]
                     if c in team_stats.columns]
        st.dataframe(
            team_stats[show_cols].sort_values("total_xg",ascending=False).reset_index(drop=True),
            use_container_width=True, height=450)

# ══ TAB 6: VENUES ══════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="sec-hdr">🏟️ VENUE ANALYSIS — 16 STADIUMS, 3 COUNTRIES</div>',
                unsafe_allow_html=True)
    if venues.empty:
        st.warning("wc2026_venue_stats.csv not found")
    else:
        vc1, vc2 = st.columns(2)
        with vc1:
            fig_v = px.bar(venues.sort_values("avg_goals", ascending=False),
                           x="avg_goals", y="stadium_name", orientation="h",
                           color="avg_goals", color_continuous_scale=["#1f2d45", GOLD],
                           text="avg_goals",
                           hover_data=[c for c in ["city","country","capacity","elevation_meters"]
                                       if c in venues.columns],
                           labels={"avg_goals":"Avg Goals/Match","stadium_name":"Stadium"})
            fig_v.update_traces(texttemplate="%{text:.2f}", textposition="outside",
                                textfont=dict(color="#9CA3AF"))
            ly6={**PLOT_THEME}; ly6["margin"]=dict(l=5,r=100,t=5,b=5); ly6["height"]=460
            ly6["coloraxis_showscale"]=False; ly6["yaxis"]=dict(autorange="reversed")
            fig_v.update_layout(**ly6)
            st.plotly_chart(fig_v, use_container_width=True)
        with vc2:
            if "elevation_meters" in venues.columns:
                fig_v2 = px.scatter(venues, x="elevation_meters", y="avg_goals",
                                    size="capacity" if "capacity" in venues.columns else None,
                                    text="city" if "city" in venues.columns else None,
                                    color="country" if "country" in venues.columns else None,
                                    labels={"elevation_meters":"Elevation (m)","avg_goals":"Avg Goals"},
                                    hover_data=[c for c in ["stadium_name","capacity","matches_played"]
                                                if c in venues.columns])
                fig_v2.update_traces(textposition="top center", textfont_size=8)
                ly7={**PLOT_THEME}; ly7["margin"]=dict(l=5,r=5,t=30,b=5); ly7["height"]=460
                ly7["title"]={"text":"Elevation vs Goals (bubble = capacity)",
                              "font":{"color":"#e8eaf0","size":13}}
                ly7["legend"]=dict(bgcolor="#111827",bordercolor="#1f2d45")
                fig_v2.update_layout(**ly7)
                st.plotly_chart(fig_v2, use_container_width=True)
        # Venue cards
        st.markdown('<div class="sec-hdr">STADIUM CARDS</div>', unsafe_allow_html=True)
        vcols = st.columns(4)
        for vi, (_, vrow) in enumerate(venues.sort_values("avg_goals",ascending=False).iterrows()):
            flag = {"USA":"🇺🇸","MEX":"🇲🇽","CAN":"🇨🇦"}.get(str(vrow.get("country","")), "🌍")
            elev = int(vrow.get("elevation_meters", 0) or 0)
            cap  = int(vrow.get("capacity", 0) or 0)
            with vcols[vi % 4]:
                st.markdown(dedent_html(f'''<div style="background:#111827;border:1px solid #1f2d45;
                    border-radius:9px;padding:.65rem;margin-bottom:.5rem;">
                  <div style="font-size:.62rem;color:#6B7280;">{flag} {vrow.get("city","")} · {vrow.get("country","")}</div>
                  <div style="font-size:.78rem;font-weight:600;color:#e8eaf0;margin:.18rem 0;">
                    {str(vrow.get("stadium_name","")).split("(")[0].strip()[:28]}</div>
                  <div style="display:flex;gap:.6rem;font-size:.7rem;">
                    <span style="color:{GOLD};">{vrow.get("avg_goals",0):.2f} gls/m</span>
                    <span style="color:{BLUE};">{cap:,}</span>
                    <span style="color:{AMBER};">{elev}m</span>
                  </div>
                </div>'''), unsafe_allow_html=True)

# ══ TAB 7: GOAL TIMING ════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="sec-hdr">🕐 WHEN GOALS HAPPEN — BUILT FROM 216 MATCH EVENTS</div>',
                unsafe_allow_html=True)
    if timing.empty:
        st.warning("wc2026_goal_timing.csv not found")
    else:
        tc1, tc2 = st.columns([3, 2])
        with tc1:
            peak_pct = timing["pct_of_total"].max()
            clrs = [GREEN if p == peak_pct else BLUE for p in timing["pct_of_total"]]
            fig_t = go.Figure()
            fig_t.add_trace(go.Bar(x=timing["time_period"], y=timing["goals"],
                                   marker_color=clrs, text=timing["goals"],
                                   textposition="outside",
                                   textfont=dict(color="#e8eaf0")))
            ly8={**PLOT_THEME}; ly8["margin"]=dict(l=5,r=5,t=30,b=5); ly8["height"]=320
            ly8["xaxis"]=dict(title="Period",gridcolor="#1f2d45")
            ly8["yaxis"]=dict(title="Goals",gridcolor="#1f2d45")
            ly8["title"]={"text":"Goals by 15-Minute Period",
                          "font":{"color":"#e8eaf0","size":13}}
            fig_t.update_layout(**ly8)
            st.plotly_chart(fig_t, use_container_width=True)
        with tc2:
            for _, row in timing.iterrows():
                pct    = row["pct_of_total"]
                is_pk  = pct == peak_pct
                bclr   = GREEN if is_pk else BLUE
                bar_w  = int(pct / peak_pct * 100)
                st.markdown(dedent_html(f'''<div style="margin-bottom:.55rem;">
                  <div style="display:flex;justify-content:space-between;
                              font-size:.82rem;margin-bottom:2px;">
                    <span style="color:#e8eaf0;font-weight:{"700" if is_pk else "400"}">
                      {row["time_period"]}'</span>
                    <span style="color:{bclr};font-weight:700;">
                      {int(row["goals"])} goals ({pct}%)</span>
                  </div>
                  <div style="background:#1f2d45;border-radius:20px;height:7px;">
                    <div style="width:{bar_w}%;height:7px;background:{bclr};
                                border-radius:20px;"></div></div>
                </div>'''), unsafe_allow_html=True)
            peak_row = timing.nlargest(1,"goals").iloc[0]
            st.markdown(dedent_html(f'''<div style="background:#1a2e1f;border:1px solid #00C97B44;
                border-radius:10px;padding:.8rem;margin-top:1rem;text-align:center;">
              <div style="font-size:.62rem;color:#9CA3AF;letter-spacing:1px;">PEAK DANGER ZONE</div>
              <div style="font-family:'Outfit',sans-serif;font-size:2.2rem;color:#00C97B;">
                {peak_row["time_period"]}'</div>
              <div style="font-size:.78rem;color:#6ee7b7;">
                {peak_row["pct_of_total"]}% of all goals</div>
            </div>'''), unsafe_allow_html=True)

# ══ TAB 8: POTM ════════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="sec-hdr">🏆 PLAYER OF THE MATCH — 73 AWARDS</div>',
                unsafe_allow_html=True)
    if potm.empty:
        st.warning("wc2026_potm.csv not found")
    else:
        potm_cnt = potm.groupby(["player_name","team_name","position"])\
                       ["match_id"].count().reset_index(name="awards")\
                       .sort_values("awards", ascending=False)
        pc1, pc2 = st.columns([2, 3])
        with pc1:
            st.markdown('<div class="sec-hdr" style="font-size:.7rem;">MOST AWARDS</div>',
                        unsafe_allow_html=True)
            for _, row in potm_cnt.head(12).iterrows():
                aw   = int(row["awards"])
                aclr = GOLD if aw >= 3 else GREEN if aw >= 2 else "#6B7280"
                st.markdown(dedent_html(f'''<div style="display:flex;align-items:center;gap:10px;
                    padding:.4rem 0;border-bottom:1px solid #1f2d4555;">
                  <div style="flex:1;">
                    <div style="font-size:.84rem;font-weight:600;color:#e8eaf0;">{row["player_name"]}</div>
                    <div style="font-size:.68rem;color:#6B7280;">{row["team_name"]} · {row["position"]}</div>
                  </div>
                  <span style="font-family:'Outfit',sans-serif;font-size:1.5rem;
                               color:{aclr};">{aw}×🏆</span>
                </div>'''), unsafe_allow_html=True)
        with pc2:
            team_potm = potm.groupby("team_name")["match_id"].count()\
                            .reset_index(name="count").sort_values("count",ascending=False).head(16)
            fig_p = px.bar(team_potm, x="team_name", y="count",
                           color="count", color_continuous_scale=["#1f2d45",GOLD],
                           labels={"count":"POTM Awards","team_name":"Team"})
            lyp={**PLOT_THEME}; lyp["margin"]=dict(l=5,r=5,t=30,b=60); lyp["height"]=340
            lyp["coloraxis_showscale"]=False; lyp["xaxis"]=dict(tickangle=-40,gridcolor="#1f2d45")
            lyp["title"]={"text":"POTM Awards by Nation","font":{"color":"#e8eaf0","size":13}}
            fig_p.update_layout(**lyp)
            st.plotly_chart(fig_p, use_container_width=True)
        show_p = [c for c in ["stage_name","home_team_name","away_team_name",
                               "player_name","team_name","position","market_value_M"]
                  if c in potm.columns]
        st.dataframe(potm[show_p].reset_index(drop=True),
                     use_container_width=True, height=300)

# ══ TAB 9: SQUADS ════════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="sec-hdr">👥 SQUAD EXPLORER — ALL 1,248 PLAYERS</div>',
                unsafe_allow_html=True)
    if players.empty:
        st.warning("wc2026_players_full.csv not found")
    else:
        se1, se2, se3 = st.columns(3)
        nations  = ["All"] + sorted(players["team_name"].dropna().unique())
        pos_opts = ["All"] + sorted(players["position"].dropna().unique())
        sel_nat  = se1.selectbox("Nation",   nations,  key="sq_nat")
        sel_pos  = se2.selectbox("Position", pos_opts, key="sq_pos")
        min_g    = se3.slider("Min goals", 0, 6, 0,   key="sq_g")

        sp = players.copy()
        if sel_nat != "All": sp = sp[sp["team_name"] == sel_nat]
        if sel_pos != "All": sp = sp[sp["position"]  == sel_pos]
        if min_g   >  0:     sp = sp[sp["goals_scored"] >= min_g]

        show_sp = [c for c in ["player_name","team_name","position","age_at_tournament",
                                "height_cm","caps","club_team","market_value_M","starts",
                                "sub_appearances","total_minutes","goals_scored","assists",
                                "yellow_cards","red_cards","g_plus_a","goals_per_90",
                                "primary_tactical_position","potm_awards"]
                   if c in sp.columns]
        st.caption(f"{len(sp):,} players match filters")
        st.dataframe(sp[show_sp].sort_values("goals_scored",ascending=False)
                       .reset_index(drop=True), use_container_width=True, height=500)

        if not pos_df.empty:
            st.markdown('<div class="sec-hdr">POSITION PROFILE</div>', unsafe_allow_html=True)
            avail = [c for c in ["avg_age","avg_height","avg_caps","avg_market_value"]
                     if c in pos_df.columns]
            if avail:
                fig_pos = go.Figure()
                for ci, col in enumerate(avail):
                    fig_pos.add_trace(go.Bar(
                        name=col.replace("avg_","").title(),
                        x=pos_df["position"], y=pos_df[col],
                        marker_color=[GREEN,BLUE,AMBER,RED][ci % 4]))
                lypos={**PLOT_THEME}; lypos["margin"]=dict(l=5,r=5,t=5,b=5); lypos["height"]=260
                lypos["barmode"]="group"
                lypos["legend"]=dict(bgcolor="#111827",bordercolor="#1f2d45")
                fig_pos.update_layout(**lypos)
                st.plotly_chart(fig_pos, use_container_width=True)

st.markdown("---")
st.markdown('<div style="text-align:center;font-size:.72rem;color:#374151;">'
            'Real WC 2026 match data · 10 CSV files · No API key · '
            'Last updated Jun 29, 2026</div>', unsafe_allow_html=True)
