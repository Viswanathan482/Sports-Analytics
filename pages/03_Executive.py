"""Executive Dashboard — board-level KPIs & financial intelligence."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import warnings; warnings.filterwarnings("ignore")

from utils.styles import MAIN_CSS, PLOT_THEME, GREEN, GOLD, RED, BLUE, AMBER, PURPLE, dedent_html, SIDEBAR_BRAND
from utils.data_loader import load_market_values, build_player_universe
from utils.image_helper import get_player_image_html

st.set_page_config(page_title="Scout IQ — Executive View", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
st.markdown('<div class="hero">📊 BOARDROOM INTELLIGENCE</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Board-level KPIs · Financial efficiency · Recruitment intelligence</div>',
            unsafe_allow_html=True)
st.markdown("---")

with st.spinner("Loading data..."):
    players = build_player_universe()
    mv      = load_market_values()

# ════════════════════════════════════════════════════════════════
# 🔎 TOP FILTER BAR — Club / Nationality / Player + existing filters
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-hdr">🔎 FILTER & PLAYER LOOKUP</div>', unsafe_allow_html=True)
st.caption(f"📚 Searching {len(players):,} players from the full Transfermarkt database")

fc1, fc2, fc3 = st.columns(3)
club_opts   = ["All Clubs"]   + sorted(players["club_display"].dropna().unique().tolist())
nation_opts = ["All Nations"] + sorted(players["nation_display"].dropna().unique().tolist())
club_sel    = fc1.selectbox("🏟️ Club", club_opts, key="ex_club")

filtered_for_player = players.copy()
if club_sel != "All Clubs":
    filtered_for_player = filtered_for_player[filtered_for_player["club_display"] == club_sel]

nation_sel = fc2.selectbox("🌍 Nationality", nation_opts, key="ex_nation")
if nation_sel != "All Nations":
    filtered_for_player = filtered_for_player[filtered_for_player["nation_display"] == nation_sel]

player_opts = ["— Select a player —"] + sorted(
    filtered_for_player["display_name"].dropna().unique().tolist())
player_sel = fc3.selectbox("👤 Player", player_opts, key="ex_player")

cf1, cf2, cf3 = st.columns(3)
pos_options = sorted(players[players["has_fifa_data"]]["position_group"].dropna().unique().tolist())
pos_filter  = cf1.multiselect("Position Group", pos_options, default=[], key="ex_pos")
rat_range   = cf2.slider("Overall Rating", 47, 95, (75, 95), key="ex_rating")
min_goals   = cf3.slider("Min Goals (recorded seasons)", 0, 30, 0, key="ex_goals")

df = players[players["has_fifa_data"]].copy()
if club_sel  != "All Clubs":   df = df[df["club_display"]   == club_sel]
if nation_sel!= "All Nations": df = df[df["nation_display"] == nation_sel]
if pos_filter and "position_group" in df.columns:
    df = df[df["position_group"].isin(pos_filter)]
if "overall_rating" in df.columns:
    df = df[(df["overall_rating"] >= rat_range[0]) & (df["overall_rating"] <= rat_range[1])]
if min_goals > 0:
    df = df[df["total_goals"] >= min_goals]
st.caption(f"Showing {len(df):,} players (with FIFA attribute data) after filters")

# ── Selected player financial card ───────────────────────────────
if player_sel != "— Select a player —":
    prow = filtered_for_player[filtered_for_player["display_name"] == player_sel]
    if prow.empty:
        prow = players[players["display_name"] == player_sel]
    prow = prow.iloc[0]
    has_fifa = bool(prow.get("has_fifa_data", False))

    img_url = prow.get("player_image_url", "")
    goals    = int(prow.get("total_goals", 0))
    assists  = int(prow.get("total_assists", 0))

    pcol1, pcol2 = st.columns([1, 3])
    with pcol1:
        st.markdown(get_player_image_html(img_url, player_sel, size=130), unsafe_allow_html=True)
    with pcol2:
        if has_fifa:
            ann_wage = prow.get("annual_wage_M", 0) or 0
            cpg      = round(ann_wage / goals, 3) if goals > 0 else None
            value_M  = round((prow.get("value_euro", 0) or 0) / 1e6, 1)
            cpg_html = f"€{cpg*1000:.0f}K / goal" if cpg is not None else "No goals on record"
            cpg_clr  = GREEN if (cpg is not None and cpg < 0.5) else AMBER if (cpg is not None and cpg < 2) else RED
            st.markdown(dedent_html(f"""
            <div style="background:#111827;border:1px solid #1f2d45;border-radius:12px;padding:1rem 1.2rem;">
              <div style="font-family:'Outfit',sans-serif;font-size:1.7rem;color:#e8eaf0;">{player_sel}</div>
              <div style="font-size:.82rem;color:#9CA3AF;margin-bottom:.6rem;">
                🏟️ {prow.get('club_display','Unknown')} &nbsp;·&nbsp; 🌍 {prow.get('nation_display','Unknown')}
                &nbsp;·&nbsp; 📍 {prow.get('position_group','')}
              </div>
              <div style="display:flex;gap:1.6rem;flex-wrap:wrap;">
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.5rem;color:{GREEN};">{goals}</div>
                     <div style="font-size:.66rem;color:#6B7280;">GOALS (RECORDED)</div></div>
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.5rem;color:{BLUE};">{assists}</div>
                     <div style="font-size:.66rem;color:#6B7280;">ASSISTS</div></div>
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.5rem;color:{GOLD};">€{value_M:.1f}M</div>
                     <div style="font-size:.66rem;color:#6B7280;">MARKET VALUE</div></div>
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.5rem;color:{AMBER};">€{ann_wage:.2f}M</div>
                     <div style="font-size:.66rem;color:#6B7280;">ANNUAL WAGE (×52)</div></div>
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.5rem;color:{cpg_clr};">{cpg_html}</div>
                     <div style="font-size:.66rem;color:#6B7280;">COST PER GOAL</div></div>
              </div>
            </div>"""), unsafe_allow_html=True)
        else:
            st.markdown(dedent_html(f"""
            <div style="background:#111827;border:1px solid #1f2d45;border-radius:12px;padding:1rem 1.2rem;">
              <div style="font-family:'Outfit',sans-serif;font-size:1.7rem;color:#e8eaf0;">{player_sel}</div>
              <div style="font-size:.82rem;color:#9CA3AF;margin-bottom:.6rem;">
                🏟️ {prow.get('club_display','Unknown')} &nbsp;·&nbsp; 🌍 {prow.get('nation_display','Unknown')}
                &nbsp;·&nbsp; 📍 {prow.get('position_group','')} &nbsp;·&nbsp; {goals} goals (recorded seasons)
              </div>
              <div style="font-size:.8rem;color:#8B5CF6;background:#8B5CF611;border-radius:8px;
                          padding:.5rem .8rem;">
                ⚠️ No FIFA wage/value data for this player — financial efficiency metrics
                (annual wage, cost per goal) aren't available for them.
              </div>
            </div>"""), unsafe_allow_html=True)
else:
    st.caption("Pick a club, nationality, or player above to see their financial efficiency card "
               "(goals, wage, and cost-per-goal).")

st.markdown("---")

# ════════════════════════════════════════════════════════════════
# KPI strip
# ════════════════════════════════════════════════════════════════
c1, c2, c3, c4, c5, c6 = st.columns(6)
avg_rat   = df["overall_rating"].mean() if "overall_rating" in df.columns else 0
avg_wage  = df["wage_euro"].mean()      if "wage_euro"      in df.columns else 0
avg_val   = df["value_euro"].mean()/1e6 if "value_euro"     in df.columns else 0
n_nat     = df["nation_display"].nunique() if "nation_display" in df.columns else 0
total_bill= (df["wage_euro"] * 52).sum() / 1e6 if "wage_euro" in df.columns else 0
bill_label = f"€{total_bill/1000:.1f}B" if total_bill >= 1000 else f"€{total_bill:.0f}M"
scorers_n = (df["total_goals"] > 0).sum()

for col, (lbl, val, clr) in zip([c1,c2,c3,c4,c5,c6], [
    ("Players in filter",   f"{len(df):,}",        GREEN),
    ("Avg Rating",          f"{avg_rat:.1f}",       BLUE),
    ("Avg Wage/Week",       f"€{avg_wage:,.0f}",    AMBER),
    ("Avg Market Value",    f"€{avg_val:.1f}M",     GOLD),
    ("Total Annual Wage Bill", bill_label, RED),
    ("Players w/ Goals",    str(scorers_n),         PURPLE),
]):
    col.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{clr};">{val}</div>'
                 f'<div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# Row 1 — Top rated + Rating vs Value
# ════════════════════════════════════════════════════════════════
ca, cb = st.columns(2)
with ca:
    st.markdown('<div class="sec-hdr">TOP 15 BY OVERALL RATING</div>', unsafe_allow_html=True)
    if "overall_rating" in df.columns and "display_name" in df.columns:
        top15 = df.nlargest(15, "overall_rating")
        fig = px.bar(top15, x="overall_rating", y="display_name", orientation="h",
                     color="overall_rating", color_continuous_scale=["#1f2d45", GREEN],
                     hover_data=["nation_display", "position_group"] if "position_group" in top15.columns else ["nation_display"],
                     labels={"display_name": "Player"})
        layout1 = {**PLOT_THEME}
        layout1["height"] = 380; layout1["coloraxis_showscale"] = False
        layout1["yaxis"] = dict(autorange="reversed", gridcolor="#1f2d45")
        fig.update_layout(**layout1)
        st.plotly_chart(fig, use_container_width=True)

with cb:
    st.markdown('<div class="sec-hdr">RATING vs MARKET VALUE</div>', unsafe_allow_html=True)
    if "overall_rating" in df.columns and "value_euro" in df.columns:
        sdf = df[df["value_euro"] > 0]
        sdf = sdf.sample(min(2000, len(sdf)), random_state=42) if len(sdf) > 0 else sdf
        clr_col = "position_group" if "position_group" in sdf.columns else None
        fig2 = px.scatter(sdf, x="overall_rating", y="value_euro",
                          color=clr_col,
                          hover_data=["display_name", "nation_display"],
                          color_discrete_sequence=[GREEN, BLUE, AMBER, RED],
                          labels={"value_euro": "Market Value (€)", "overall_rating": "Overall Rating"})
        layout2 = {**PLOT_THEME}; layout2["height"] = 380
        layout2["xaxis"] = dict(title="Overall Rating", gridcolor="#1f2d45")
        layout2["yaxis"] = dict(title="Market Value (€)", gridcolor="#1f2d45")
        layout2["legend"] = dict(bgcolor="#111827", bordercolor="#1f2d45")
        fig2.update_layout(**layout2)
        st.plotly_chart(fig2, use_container_width=True)

# ════════════════════════════════════════════════════════════════
# Row 2 — Goals vs Salary (financial efficiency)
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-hdr">💰 GOALS vs SALARY — FINANCIAL EFFICIENCY</div>', unsafe_allow_html=True)
st.caption("Bubble size = market value · Players above the line score more goals per € spent than average")

gv_df = df[(df["total_goals"] > 0) & (df["wage_euro"] > 0)].copy()
if len(gv_df) > 0:
    gv1, gv2 = st.columns([2.2, 1])
    with gv1:
        st.markdown('<div class="sec-hdr" style="font-size:.78rem;">📈 WAGE vs GOALS SCATTER</div>',
                    unsafe_allow_html=True)
        st.caption("Bubble size = market value · hover for player details")
        fig_gv = px.scatter(
            gv_df, x="annual_wage_M", y="total_goals",
            size="value_euro", color="position_group" if "position_group" in gv_df.columns else None,
            hover_data=["display_name", "club_display"],
            color_discrete_sequence=[GREEN, BLUE, AMBER, RED],
            labels={"annual_wage_M": "Annual Wage (€M)", "total_goals": "Goals (recorded seasons)"})
        if player_sel != "— Select a player —":
            sel_row = gv_df[gv_df["display_name"] == player_sel]
            if not sel_row.empty:
                fig_gv.add_trace(go.Scatter(
                    x=sel_row["annual_wage_M"], y=sel_row["total_goals"],
                    mode="markers+text", text=[player_sel], textposition="top center",
                    marker=dict(size=22, color=GOLD, symbol="star",
                               line=dict(color="white", width=1.5)),
                    name=player_sel, showlegend=True))
        layout_gv = {**PLOT_THEME}; layout_gv["height"] = 420
        layout_gv["xaxis"] = dict(title="Annual Wage (€M)", gridcolor="#1f2d45")
        layout_gv["yaxis"] = dict(title="Total Goals", gridcolor="#1f2d45")
        layout_gv["legend"] = dict(bgcolor="#111827", bordercolor="#1f2d45", orientation="h", y=-0.18)
        fig_gv.update_layout(**layout_gv)
        st.plotly_chart(fig_gv, use_container_width=True)

    with gv2:
        st.markdown('<div class="sec-hdr" style="font-size:.78rem;">🏆 BEST VALUE SCORERS</div>',
                    unsafe_allow_html=True)
        st.caption("Major players only · min. 5 goals · €5M+ value")
        # Filter to MAJOR players: exclude the €1,000/week data-floor noise,
        # require a real market value, and enough goals to be meaningful.
        major_pool = gv_df[(gv_df["total_goals"] >= 5) &
                           (gv_df["wage_euro"] > 1000) &
                           (gv_df["value_euro"] >= 5_000_000)].copy()
        major_pool["cost_per_goal_K"] = (major_pool["annual_wage_M"] * 1000 /
                                         major_pool["total_goals"]).round(0)
        best_val = major_pool.nsmallest(8, "cost_per_goal_K")

        rows_html = ""
        if best_val.empty:
            rows_html = '<div style="color:#6B7280;font-size:.8rem;padding:1rem 0;">No major players match the current filters.</div>'
        else:
            for _, row in best_val.iterrows():
                rows_html += f"""
                <div style="display:flex;align-items:center;gap:8px;padding:.4rem 0;
                            border-bottom:1px solid #1f2d4555;">
                  <div style="flex:1;min-width:0;">
                    <div style="font-size:.82rem;font-weight:600;color:#e8eaf0;white-space:nowrap;
                                overflow:hidden;text-overflow:ellipsis;">{row['display_name']}</div>
                    <div style="font-size:.68rem;color:#6B7280;white-space:nowrap;overflow:hidden;
                                text-overflow:ellipsis;">{row['club_display']} · {int(row['total_goals'])} goals</div>
                  </div>
                  <span style="background:#00C97B22;color:{GREEN};border-radius:6px;padding:2px 8px;
                              font-size:.74rem;font-weight:700;white-space:nowrap;">€{row['cost_per_goal_K']:.0f}K</span>
                </div>"""

        st.markdown(dedent_html(f"""
        <div style="background:#0d1117;border:1px solid #1f2d45;border-radius:10px;
                    padding:.6rem .8rem;height:420px;overflow-y:auto;">
          {rows_html}
        </div>"""), unsafe_allow_html=True)
else:
    st.info("No players with both recorded goals and wage data match the current filters.")

# ════════════════════════════════════════════════════════════════
# Row 3 — Cost Per Goal leaderboard (FIXED: major players only)
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-hdr">⚖️ COST PER GOAL — MOST vs LEAST EFFICIENT FORWARDS/MIDFIELDERS</div>',
            unsafe_allow_html=True)
st.caption("Filtered to attacking players with real wage data (excludes the dataset's €1,000/wk "
           "placeholder floor), 5+ goals, and €5M+ market value — so this shows recognisable players, "
           "not statistical noise from journeymen.")

cpg_pool = df[
    (df["total_goals"] >= 5) &
    (df["wage_euro"] > 1000) &
    (df["value_euro"] >= 5_000_000) &
    (df["position_group"].isin(["Attacker", "Midfielder"]))
].copy()
cpg_pool["cost_per_goal_K"] = (cpg_pool["annual_wage_M"] * 1000 / cpg_pool["total_goals"]).round(0)

if len(cpg_pool) > 0:
    cpg1, cpg2 = st.columns(2)
    with cpg1:
        best = cpg_pool.nsmallest(12, "cost_per_goal_K")
        fig_best = px.bar(best, x="cost_per_goal_K", y="display_name", orientation="h",
                          color="cost_per_goal_K", color_continuous_scale=[GREEN, "#1f2d45"],
                          hover_data=["club_display", "total_goals"],
                          labels={"cost_per_goal_K": "€K per Goal", "display_name": "Player"})
        layout_b1 = {**PLOT_THEME}; layout_b1["height"] = 380
        layout_b1["coloraxis_showscale"] = False
        layout_b1["yaxis"] = dict(autorange="reversed", gridcolor="#1f2d45")
        layout_b1["xaxis"] = dict(title="€K per Goal", gridcolor="#1f2d45")
        layout_b1["title"] = dict(text="✅ Best Value (lowest €K/goal)", font=dict(color=GREEN, size=12))
        fig_best.update_layout(**layout_b1)
        st.plotly_chart(fig_best, use_container_width=True)
    with cpg2:
        worst = cpg_pool.nlargest(12, "cost_per_goal_K")
        fig_worst = px.bar(worst, x="cost_per_goal_K", y="display_name", orientation="h",
                           color="cost_per_goal_K", color_continuous_scale=["#1f2d45", RED],
                           hover_data=["club_display", "total_goals"],
                           labels={"cost_per_goal_K": "€K per Goal", "display_name": "Player"})
        layout_b2 = {**PLOT_THEME}; layout_b2["height"] = 380
        layout_b2["coloraxis_showscale"] = False
        layout_b2["yaxis"] = dict(autorange="reversed", gridcolor="#1f2d45")
        layout_b2["xaxis"] = dict(title="€K per Goal", gridcolor="#1f2d45")
        layout_b2["title"] = dict(text="⚠️ Most Expensive (highest €K/goal)", font=dict(color=RED, size=12))
        fig_worst.update_layout(**layout_b2)
        st.plotly_chart(fig_worst, use_container_width=True)
else:
    st.info("Not enough major attacking players match the current filters to rank. "
            "Try widening the Position/Rating filters above.")

st.markdown("<br>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# Row 4 — Wage brackets + Market value trends
# ════════════════════════════════════════════════════════════════
cc, cd = st.columns(2)
with cc:
    st.markdown('<div class="sec-hdr">💵 WAGE BRACKETS BY POSITION</div>', unsafe_allow_html=True)
    st.caption("How many players fall into each weekly wage band")
    if "wage_euro" in df.columns and "position_group" in df.columns:
        wdf = df[df["wage_euro"] > 0].copy()
        bins   = [0, 10_000, 25_000, 50_000, 100_000, 200_000, np.inf]
        labels = ["<€10K", "€10–25K", "€25–50K", "€50–100K", "€100–200K", "€200K+"]
        wdf["wage_bracket"] = pd.cut(wdf["wage_euro"], bins=bins, labels=labels, right=False)
        bracket_counts = wdf.groupby(["wage_bracket", "position_group"], observed=True).size().reset_index(name="count")
        fig3 = px.bar(bracket_counts, x="wage_bracket", y="count", color="position_group",
                      category_orders={"wage_bracket": labels},
                      color_discrete_sequence=[GREEN, BLUE, AMBER, RED],
                      labels={"wage_bracket": "Weekly Wage", "count": "Number of Players"})
        layout3 = {**PLOT_THEME}; layout3["height"] = 380; layout3["barmode"] = "stack"
        layout3["margin"] = dict(l=10, r=10, t=10, b=90)
        layout3["xaxis"] = dict(gridcolor="#1f2d45")
        layout3["yaxis"] = dict(title="Players", gridcolor="#1f2d45")
        layout3["legend"] = dict(bgcolor="#111827", bordercolor="#1f2d45",
                                 orientation="h", x=0.5, xanchor="center", y=-0.32)
        fig3.update_layout(**layout3)
        st.plotly_chart(fig3, use_container_width=True)

with cd:
    st.markdown('<div class="sec-hdr">MARKET VALUE TRENDS (2015-2025)</div>', unsafe_allow_html=True)
    st.caption(" ")
    if not mv.empty and "value_M" in mv.columns and "year" in mv.columns:
        pos_col = "main_position" if "main_position" in mv.columns else (mv.columns[2] if len(mv.columns) > 2 else None)
        if pos_col:
            mv_trend = mv.groupby(["year", pos_col])["value_M"].median().reset_index()
            fig4 = px.line(mv_trend, x="year", y="value_M", color=pos_col,
                           color_discrete_sequence=[GREEN, BLUE, AMBER, RED])
            layout4 = {**PLOT_THEME}; layout4["height"] = 380
            layout4["margin"] = dict(l=10, r=10, t=10, b=90)
            layout4["xaxis"] = dict(title="Year", gridcolor="#1f2d45")
            layout4["yaxis"] = dict(title="Median Value (€M)", gridcolor="#1f2d45")
            layout4["legend"] = dict(bgcolor="#111827", bordercolor="#1f2d45",
                                     orientation="h", x=0.5, xanchor="center", y=-0.32)
            fig4.update_layout(**layout4)
            st.plotly_chart(fig4, use_container_width=True)

st.caption("Wage brackets read like: '12 forwards earn over €200K/week' — easier to brief a board with than a box plot.")

# ════════════════════════════════════════════════════════════════
# Row 5 — Total wage bill share by position
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-hdr">📌 SHARE OF TOTAL WAGE BILL BY POSITION</div>', unsafe_allow_html=True)
if "wage_euro" in df.columns and "position_group" in df.columns:
    bill_by_pos = df.groupby("position_group")["wage_euro"].apply(lambda x: (x * 52).sum() / 1e6).reset_index()
    bill_by_pos.columns = ["Position", "Annual Wage Bill (€M)"]
    fig_pie = px.pie(bill_by_pos, values="Annual Wage Bill (€M)", names="Position",
                     color_discrete_sequence=[GREEN, BLUE, AMBER, RED], hole=0.45)
    layout_pie = {**PLOT_THEME}; layout_pie["height"] = 320
    layout_pie["legend"] = dict(bgcolor="#111827", bordercolor="#1f2d45")
    fig_pie.update_traces(textinfo="label+percent", textfont=dict(color="#e8eaf0"))
    fig_pie.update_layout(**layout_pie)
    st.plotly_chart(fig_pie, use_container_width=True)
