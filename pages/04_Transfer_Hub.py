"""Transfer Market Hub — recruitment intelligence."""
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

st.set_page_config(page_title="Scout IQ", page_icon="💰",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
st.markdown('<div class="hero">🔍 SCOUT IQ</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Player lookup · Value for money · Career projections · Market trends</div>', unsafe_allow_html=True)
st.markdown("---")

with st.spinner("Loading full player universe..."):
    players = build_player_universe()
    mv      = load_market_values()

st.caption(f"📚 Searching {len(players):,} players — every player in the Transfermarkt database, "
           f"not just the {int(players['has_fifa_data'].sum()):,} with FIFA attribute data.")

# ════════════════════════════════════════════════════════════════
# TOP FILTER BAR — Player / Club / Nationality (drives whole page)
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-hdr">🔎 PLAYER LOOKUP</div>', unsafe_allow_html=True)
fc1, fc2, fc3 = st.columns(3)

club_opts   = ["All Clubs"]   + sorted(players["club_display"].dropna().unique().tolist())
nation_opts = ["All Nations"] + sorted(players["nation_display"].dropna().unique().tolist())

club_sel = fc1.selectbox("🏟️ Club", club_opts, key="th_club")

filtered_for_player = players.copy()
if club_sel != "All Clubs":
    filtered_for_player = filtered_for_player[filtered_for_player["club_display"] == club_sel]

nation_sel = fc2.selectbox("🌍 Nationality", nation_opts, key="th_nation")
if nation_sel != "All Nations":
    filtered_for_player = filtered_for_player[filtered_for_player["nation_display"] == nation_sel]

player_opts = ["— Select a player —"] + sorted(
    filtered_for_player["display_name"].dropna().unique().tolist())
player_sel = fc3.selectbox("👤 Player Name", player_opts, key="th_player")

# ── Selected player profile card ────────────────────────────────
if player_sel != "— Select a player —":
    prow = filtered_for_player[filtered_for_player["display_name"] == player_sel]
    if prow.empty:
        prow = players[players["display_name"] == player_sel]
    prow = prow.iloc[0]
    has_fifa = bool(prow.get("has_fifa_data", False))

    img_url = prow.get("player_image_url", "")
    pos     = prow.get("position_group", "")
    age     = prow.get("age_2026", prow.get("age", ""))
    foot    = prow.get("preferred_foot", "")
    on_loan = bool(prow.get("on_loan", False))

    pcol1, pcol2 = st.columns([1, 3])
    with pcol1:
        st.markdown(get_player_image_html(img_url, player_sel, size=140), unsafe_allow_html=True)
    with pcol2:
        loan_badge = (' <span style="background:#F59E0B22;color:#F59E0B;border-radius:6px;'
                      'padding:2px 8px;font-size:.7rem;font-weight:600;">ON LOAN</span>') if on_loan else ''
        no_fifa_badge = ('' if has_fifa else
            ' <span style="background:#8B5CF622;color:#8B5CF6;border-radius:6px;'
            'padding:2px 8px;font-size:.68rem;font-weight:600;">NO FIFA ATTRIBUTE DATA</span>')
        st.markdown(dedent_html(f"""
        <div style="background:#111827;border:1px solid #1f2d45;border-radius:12px;padding:1rem 1.2rem;">
          <div style="font-family:'Outfit',sans-serif;font-size:1.8rem;color:#e8eaf0;
                      letter-spacing:1px;">{player_sel}{loan_badge}{no_fifa_badge}</div>
          <div style="font-size:.85rem;color:#9CA3AF;margin-bottom:.6rem;">
            🏟️ {prow.get('club_display','Unknown')} &nbsp;·&nbsp; 🌍 {prow.get('nation_display','Unknown')}
            &nbsp;·&nbsp; 📍 {pos} {f"&nbsp;·&nbsp; 🎂 Age {int(age)}" if pd.notna(age) and age != "" else ""}
            {f"&nbsp;·&nbsp; 🦶 {foot}" if foot and pd.notna(foot) else ""}
          </div>"""), unsafe_allow_html=True)
        if has_fifa:
            rating    = prow.get("overall_rating", 0)
            potential = prow.get("potential", rating)
            value_M   = round((prow.get("value_euro", 0) or 0) / 1e6, 1)
            wage      = prow.get("wage_euro", 0) or 0
            st.markdown(dedent_html(f"""
              <div style="display:flex;gap:1.8rem;flex-wrap:wrap;">
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.6rem;color:{GREEN};">{rating:.0f}</div>
                     <div style="font-size:.68rem;color:#6B7280;">OVERALL</div></div>
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.6rem;color:{BLUE};">{potential:.0f}</div>
                     <div style="font-size:.68rem;color:#6B7280;">POTENTIAL</div></div>
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.6rem;color:{GOLD};">€{value_M:.1f}M</div>
                     <div style="font-size:.68rem;color:#6B7280;">MARKET VALUE</div></div>
                <div><div style="font-family:'Outfit',sans-serif;font-size:1.6rem;color:{AMBER};">€{wage:,.0f}</div>
                     <div style="font-size:.68rem;color:#6B7280;">WEEKLY WAGE</div></div>
              </div></div>"""), unsafe_allow_html=True)
        else:
            st.markdown(dedent_html(f"""
              <div style="font-size:.8rem;color:#8B5CF6;background:#8B5CF611;
                          border-radius:8px;padding:.5rem .8rem;">
                ⚠️ This player isn't in the FIFA attribute dataset (likely a recent breakout or
                very young player). Club, nationality, and photo are sourced from Transfermarkt —
                rating, value, wage, and the attribute radar aren't available for them.
              </div></div>"""), unsafe_allow_html=True)

    if has_fifa:
        attr_cols = ['pace_score','shooting_score','passing_score','defending_score','physical_score']
        attr_cols = [c for c in attr_cols if c in players.columns]
        if attr_cols:
            st.markdown("<br>", unsafe_allow_html=True)
            rc1, rc2 = st.columns([1,1])
            with rc1:
                pos_avg = players[(players['position_group']==pos) & (players['has_fifa_data'])][attr_cols].mean()
                labels  = [c.replace('_score','').title() for c in attr_cols]
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(r=[prow.get(c,0) for c in attr_cols], theta=labels,
                    fill='toself', name=player_sel, line_color=GREEN, fillcolor="rgba(0,201,123,0.25)"))
                fig_r.add_trace(go.Scatterpolar(r=pos_avg.values.tolist(), theta=labels,
                    fill='toself', name=f"{pos} Avg", line_color=BLUE, fillcolor="rgba(59,130,246,0.12)"))
                layout_r = {**PLOT_THEME}
                layout_r["height"] = 320
                layout_r["polar"] = dict(bgcolor="#0d1117",
                    radialaxis=dict(visible=True, range=[0,100], gridcolor="#1f2d45", color="#6B7280"),
                    angularaxis=dict(gridcolor="#1f2d45", color="#9CA3AF"))
                layout_r["legend"] = dict(bgcolor="#111827",bordercolor="#1f2d45",orientation="h",y=-0.1)
                fig_r.update_layout(**layout_r)
                st.plotly_chart(fig_r, use_container_width=True)
            with rc2:
                rating  = prow.get("overall_rating", 0)
                value_M = round((prow.get("value_euro", 0) or 0) / 1e6, 1)
                if 'shooting_score' in players.columns:
                    vfm_val = round(prow.get('shooting_score',rating) / (value_M + 0.1), 2)
                else:
                    vfm_val = round(rating / (value_M + 0.1), 2)
                pos_pool = players[(players['position_group']==pos) & (players['has_fifa_data'])]
                pos_rank = (pos_pool['overall_rating'] < rating).mean()*100 if len(pos_pool) else 50
                st.markdown(dedent_html(f"""
                <div style="background:#111827;border:1px solid #1f2d45;border-radius:12px;
                            padding:1rem;height:300px;display:flex;flex-direction:column;
                            justify-content:center;gap:1rem;">
                  <div>
                    <div style="font-size:.7rem;color:#9CA3AF;letter-spacing:1px;">VALUE FOR MONEY SCORE</div>
                    <div style="font-family:'Outfit',sans-serif;font-size:2.2rem;color:{GOLD};">{vfm_val}</div>
                    <div style="font-size:.7rem;color:#6B7280;">Quality ÷ Market Value (€M)</div>
                  </div>
                  <div>
                    <div style="font-size:.7rem;color:#9CA3AF;letter-spacing:1px;">RATING PERCENTILE — {pos}</div>
                    <div style="background:#1f2d45;border-radius:20px;height:10px;margin-top:.3rem;">
                      <div style="width:{pos_rank:.0f}%;height:10px;background:{GREEN};border-radius:20px;"></div>
                    </div>
                    <div style="font-size:.7rem;color:#00C97B;margin-top:.2rem;">Top {100-pos_rank:.0f}% of {pos}s</div>
                  </div>
                  <div>
                    <div style="font-size:.7rem;color:#9CA3AF;letter-spacing:1px;">RELEASE CLAUSE</div>
                    <div style="font-size:1.1rem;color:#e8eaf0;font-weight:600;">
                      €{(prow.get('release_clause_euro',0) or 0)/1e6:.1f}M</div>
                  </div>
                </div>"""), unsafe_allow_html=True)
else:
    st.caption("Pick a club, nationality, or player above to see a full profile card.")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(
    ["🔍 Scout Tool", "⚖️ Compare Players", "📈 Career Value Projector", "💹 Market Trends"])

# ── TAB 1: SCOUT TOOL (FIFA-attribute players only) ───────────
with tab1:
    st.markdown('<div class="sec-hdr">PLAYER RECRUITMENT SCOUT</div>', unsafe_allow_html=True)
    st.caption("Uses FIFA attribute data — only players with rating/value/wage scores are rankable here.")

    c1,c2,c3,c4,c5 = st.columns(5)
    pos_opts  = ["All"] + sorted(players[players["has_fifa_data"]]["position_group"].dropna().unique().tolist())
    pos_s     = c1.selectbox("Position", pos_opts, key="sc_pos")
    age_s     = c2.slider("Age (2026)", 17, 50, (20,28), key="sc_age")
    rat_s     = c3.slider("Min Rating",  65, 95, 78, key="sc_rat")
    val_s     = c4.slider("Max Value (€M)", 1, 200, 50, key="sc_val")
    nat_s     = c5.selectbox("Nationality", nation_opts, key="sc_nat")

    scout = players[players["has_fifa_data"]].copy()
    if pos_s != "All" and 'position_group' in scout.columns:
        scout = scout[scout['position_group'] == pos_s]
    if nat_s != "All Nations":
        scout = scout[scout['nation_display'] == nat_s]
    age_col = 'age_2026' if 'age_2026' in scout.columns else 'age'
    if age_col in scout.columns:
        scout = scout[(scout[age_col] >= age_s[0]) & (scout[age_col] <= age_s[1])]
    if 'overall_rating' in scout.columns:
        scout = scout[scout['overall_rating'] >= rat_s]
    if 'value_euro' in scout.columns:
        scout = scout[(scout['value_euro'] > 0) & (scout['value_euro'] <= val_s*1e6)]

    if 'shooting_score' in scout.columns and 'value_euro' in scout.columns:
        scout['vfm'] = (scout['shooting_score'] / (scout['value_euro']/1e6 + 0.1)).round(3)
    else:
        scout['vfm'] = scout.get('overall_rating', 75)

    scout['Value (€M)'] = (scout['value_euro']/1e6).round(1) if 'value_euro' in scout.columns else 0

    show_cols = ['display_name','club_display','nation_display','position_group',
                 age_col, 'overall_rating','Value (€M)','vfm']
    show_cols = [c for c in show_cols if c in scout.columns]
    rename_map = {'display_name':'Player','club_display':'Club','nation_display':'Nation',
                  'position_group':'Position','age_2026':'Age 2026','age':'Age',
                  'overall_rating':'Rating','vfm':'Value for Money'}
    display = scout[show_cols].rename(columns=rename_map)

    # ── Result count + sort/pagination controls ───────────────
    total_matches = len(display)
    rc1, rc2, rc3 = st.columns([2,1,1])
    with rc1:
        st.markdown(f'<div style="font-size:.95rem;color:#e8eaf0;padding-top:.4rem;">'
                     f'<span style="color:{GREEN};font-weight:700;">{total_matches:,}</span> players match '
                     f'your filters</div>', unsafe_allow_html=True)
    with rc2:
        sort_options = [c for c in display.columns if c != 'Player']
        sort_col = st.selectbox("Sort by", sort_options,
                                index=(sort_options.index('Value for Money')
                                       if 'Value for Money' in sort_options else 0),
                                key="sc_sort")
    with rc3:
        page_size = st.selectbox("Rows per page", [25, 50, 100, 250, "All"], index=1, key="sc_pagesize")

    display = display.sort_values(sort_col, ascending=False).reset_index(drop=True)

    if page_size == "All":
        page_df = display
        st.caption(f"Showing all {total_matches:,} players")
    else:
        n_pages = max(1, -(-total_matches // page_size))  # ceil
        pg = st.number_input(f"Page (1–{n_pages})", min_value=1, max_value=n_pages, value=1, key="sc_page")
        start = (pg-1)*page_size
        end   = start + page_size
        page_df = display.iloc[start:end]
        st.caption(f"Showing {start+1:,}–{min(end,total_matches):,} of {total_matches:,} players")

    st.dataframe(page_df.reset_index(drop=True), use_container_width=True, height=440)

    csv_bytes = display.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download full filtered list (CSV)", csv_bytes,
                       file_name="scout_results.csv", mime="text/csv", key="sc_dl")

    st.markdown('<div class="sec-hdr">VALUE FOR MONEY SCATTER</div>', unsafe_allow_html=True)
    st.caption("Bubble size = Value for Money score · hover for player name and club · click-drag to zoom")
    if 'value_euro' in scout.columns and 'overall_rating' in scout.columns:
        top_vfm = scout.nlargest(min(50, len(scout)), 'vfm')
        c_col = 'position_group' if 'position_group' in top_vfm.columns else None
        fig = px.scatter(top_vfm, x='value_euro', y='overall_rating',
                         size='vfm', color=c_col,
                         hover_data=['display_name','club_display'],
                         color_discrete_sequence=[GREEN,BLUE,AMBER,RED],
                         labels={'value_euro':'Market Value (€)','overall_rating':'Rating'})
        layout_vfm = {**PLOT_THEME}; layout_vfm["height"]=340
        layout_vfm["xaxis"]=dict(gridcolor="#1f2d45"); layout_vfm["yaxis"]=dict(gridcolor="#1f2d45")
        layout_vfm["legend"]=dict(bgcolor="#111827",bordercolor="#1f2d45")
        fig.update_layout(**layout_vfm)
        st.plotly_chart(fig, use_container_width=True)

    # ── Position breakdown of filtered pool ────────────────────
    if 'Position' in display.columns and total_matches > 0:
        st.markdown('<div class="sec-hdr">FILTERED POOL — POSITION BREAKDOWN</div>', unsafe_allow_html=True)
        pos_counts = display['Position'].value_counts().reset_index()
        pos_counts.columns = ['Position','Count']
        bd1, bd2 = st.columns([2,1])
        with bd1:
            fig_pos = px.bar(pos_counts, x='Position', y='Count', color='Position',
                             color_discrete_sequence=[GREEN,BLUE,AMBER,RED,PURPLE])
            layout_pos = {**PLOT_THEME}; layout_pos["height"]=240; layout_pos["showlegend"]=False
            layout_pos["xaxis"]=dict(gridcolor="#1f2d45"); layout_pos["yaxis"]=dict(gridcolor="#1f2d45")
            fig_pos.update_layout(**layout_pos)
            st.plotly_chart(fig_pos, use_container_width=True)
        with bd2:
            avg_rating = display['Rating'].mean() if 'Rating' in display.columns else 0
            avg_value  = display['Value (€M)'].mean() if 'Value (€M)' in display.columns else 0
            best_vfm   = display.iloc[0]['Player'] if total_matches > 0 else "—"
            st.markdown(dedent_html(f"""
            <div style="display:flex;flex-direction:column;gap:.6rem;padding-top:.5rem;">
              <div class="kpi-card"><div class="kpi-val" style="color:{GREEN};font-size:1.4rem;">{avg_rating:.1f}</div>
                   <div class="kpi-lbl">Avg Rating</div></div>
              <div class="kpi-card"><div class="kpi-val" style="color:{GOLD};font-size:1.4rem;">€{avg_value:.1f}M</div>
                   <div class="kpi-lbl">Avg Value</div></div>
              <div class="kpi-card"><div class="kpi-val" style="color:{BLUE};font-size:1rem;">{best_vfm}</div>
                   <div class="kpi-lbl">Top Value Pick</div></div>
            </div>"""), unsafe_allow_html=True)

# ── TAB 2: COMPARE PLAYERS (full universe) ────────────────────
with tab2:
    st.markdown('<div class="sec-hdr">⚖️ HEAD-TO-HEAD PLAYER COMPARISON</div>', unsafe_allow_html=True)
    st.caption("Every player is searchable. Players without FIFA attribute data will show bio info only — no radar.")
    all_names = sorted(players['display_name'].dropna().unique().tolist())
    cmp1, cmp2 = st.columns(2)
    pa_name = cmp1.selectbox("Player A", all_names,
        index=all_names.index("Lionel Messi") if "Lionel Messi" in all_names else 0, key="cmp_a")
    pb_name = cmp2.selectbox("Player B", all_names,
        index=all_names.index("Kylian Mbappé") if "Kylian Mbappé" in all_names else 1, key="cmp_b")

    pa = players[players['display_name']==pa_name].iloc[0]
    pb = players[players['display_name']==pb_name].iloc[0]
    pa_has = bool(pa.get("has_fifa_data", False))
    pb_has = bool(pb.get("has_fifa_data", False))

    attr_cols = [c for c in ['pace_score','shooting_score','passing_score',
                              'defending_score','physical_score'] if c in players.columns]
    hc1, hc2 = st.columns(2)
    for col, p, clr, has_fifa_p in [(hc1, pa, GREEN, pa_has), (hc2, pb, RED, pb_has)]:
        img_url = p.get('player_image_url','')
        with col:
            st.markdown(get_player_image_html(img_url, p['display_name'], size=110), unsafe_allow_html=True)
            rating_str = f"{p.get('overall_rating',0):.0f}" if has_fifa_p else "N/A"
            value_str  = f"€{(p.get('value_euro',0) or 0)/1e6:.1f}M" if has_fifa_p else "No FIFA data"
            st.markdown(dedent_html(f"""
            <div style="text-align:center;margin-top:.4rem;">
              <div style="font-weight:700;color:#e8eaf0;font-size:1rem;">{p['display_name']}</div>
              <div style="font-size:.75rem;color:#6B7280;">{p.get('club_display','')} · {p.get('nation_display','')}</div>
              <div style="font-family:'Outfit',sans-serif;font-size:1.8rem;color:{clr};">{rating_str}</div>
              <div style="font-size:.68rem;color:#6B7280;">OVERALL · {value_str}</div>
            </div>"""), unsafe_allow_html=True)

    if attr_cols and pa_has and pb_has:
        labels = [c.replace('_score','').title() for c in attr_cols]
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatterpolar(r=[pa.get(c,0) for c in attr_cols], theta=labels,
            fill='toself', name=pa_name, line_color=GREEN, fillcolor="rgba(0,201,123,0.22)"))
        fig_cmp.add_trace(go.Scatterpolar(r=[pb.get(c,0) for c in attr_cols], theta=labels,
            fill='toself', name=pb_name, line_color=RED, fillcolor="rgba(239,68,68,0.18)"))
        layout_c = {**PLOT_THEME}; layout_c["height"]=420
        layout_c["polar"]=dict(bgcolor="#0d1117",
            radialaxis=dict(visible=True, range=[0,100], gridcolor="#1f2d45", color="#6B7280"),
            angularaxis=dict(gridcolor="#1f2d45", color="#9CA3AF"))
        layout_c["legend"]=dict(bgcolor="#111827",bordercolor="#1f2d45",orientation="h",y=-0.05)
        fig_cmp.update_layout(**layout_c)
        st.plotly_chart(fig_cmp, use_container_width=True)
    elif not pa_has or not pb_has:
        missing = []
        if not pa_has: missing.append(pa_name)
        if not pb_has: missing.append(pb_name)
        st.info(f"⚠️ No FIFA attribute radar available for: {', '.join(missing)}. "
                f"Bio info shown above is from Transfermarkt.")

    compare_metrics = [c for c in ['overall_rating','potential','value_euro','wage_euro'] if c in players.columns]
    if compare_metrics and pa_has and pb_has:
        st.markdown('<div class="sec-hdr">KEY METRICS SIDE BY SIDE</div>', unsafe_allow_html=True)
        mcols = st.columns(len(compare_metrics))
        labels_map = {'overall_rating':'Rating','potential':'Potential',
                      'value_euro':'Value (€M)','wage_euro':'Wage (€/wk)'}
        for col, m in zip(mcols, compare_metrics):
            av = pa.get(m,0) or 0; bv = pb.get(m,0) or 0
            if m in ('value_euro',):
                av, bv = av/1e6, bv/1e6
            with col:
                st.markdown(f'<div style="text-align:center;font-size:.72rem;color:#9CA3AF;">{labels_map.get(m,m)}</div>', unsafe_allow_html=True)
                fig_b = go.Figure()
                fig_b.add_trace(go.Bar(x=[pa_name[:10],pb_name[:10]], y=[av,bv],
                                       marker_color=[GREEN,RED]))
                layout_b={**PLOT_THEME}; layout_b["height"]=180
                layout_b["margin"]=dict(l=5,r=5,t=5,b=30)
                layout_b["showlegend"]=False
                layout_b["yaxis"]=dict(gridcolor="#1f2d45"); layout_b["xaxis"]=dict(tickfont=dict(size=9))
                fig_b.update_layout(**layout_b)
                st.plotly_chart(fig_b, use_container_width=True)

# ── TAB 3: CAREER VALUE PROJECTOR ─────────────────────────────
with tab3:
    st.markdown('<div class="sec-hdr">CAREER VALUE TRAJECTORY</div>', unsafe_allow_html=True)
    st.caption("Projects future market value using age curve, potential gap, and a typical peak-at-27 development/decline model. "
               "If the selected player has real historical value data, it's overlaid as solid markers.")
    prefill = None
    if player_sel != "— Select a player —":
        prefill = players[players['display_name']==player_sel]
        prefill = prefill.iloc[0] if not prefill.empty and bool(prefill.iloc[0].get("has_fifa_data", False)) else None

    ci1,ci2 = st.columns([1,2])
    with ci1:
        if prefill is not None:
            st.caption(f"Pre-filled from {player_sel} — adjust as needed")
        elif player_sel != "— Select a player —":
            st.caption(f"{player_sel} has no FIFA data to pre-fill from — using defaults")
        cv_age = st.slider("Current Age",  16, 37,
            int(prefill.get('age_2026', prefill.get('age',22))) if prefill is not None else 22, key="cv_age")
        cv_rat = st.slider("Overall Rating", 60, 99,
            int(prefill.get('overall_rating',80)) if prefill is not None else 80, key="cv_rat")
        cv_pot = st.slider("Potential",     60, 99,
            int(prefill.get('potential',87)) if prefill is not None else 87, key="cv_pot")
        default_val = int(prefill.get('value_euro',10000000)) if prefill is not None and prefill.get('value_euro',0) else 10000000
        cv_val = st.number_input("Current Market Value (€)", 100000, 300000000,
                                 min(max(default_val,100000),300000000), step=500000)
        cv_pos = st.selectbox("Position (for peer comparison)",
                              sorted(players[players["has_fifa_data"]]["position_group"].dropna().unique().tolist()),
                              index=0, key="cv_pos")

    def age_factor(a):
        if a<18: return 0.65
        if a<22: return 0.82
        if a<26: return 0.97
        if a<29: return 1.00
        if a<32: return 0.93
        if a<35: return 0.82
        if a<38: return 0.65
        return 0.48

    ages  = list(range(cv_age, 39))
    pot_b = (cv_pot - cv_rat) / 100.0
    traj  = []
    for a in ages:
        af  = age_factor(a)
        dev = 1 + max(0, (min(a,27)-cv_age) / max(1,27-cv_age)) * pot_b
        dec = max(0.05, 1 - max(0,(a-27))*0.07)
        traj.append(cv_val/1e6 * af * dev * dec)

    peak_age = ages[int(np.argmax(traj))]
    peak_val = max(traj)
    growth   = (peak_val - cv_val/1e6) / (cv_val/1e6) * 100
    val_at_30 = traj[ages.index(30)] if 30 in ages else traj[-1]
    val_at_35 = traj[ages.index(35)] if 35 in ages else traj[-1]

    # Real historical trajectory overlay, if available — convert calendar years to the
    # player's age-at-that-year so it shares the same x-axis as the projection (both "Age").
    real_hist = pd.DataFrame()
    if player_sel != "— Select a player —" and not mv.empty and 'player_name' in mv.columns:
        real_hist = mv[mv['player_name'].astype(str).str.contains(
            player_sel.split('(')[0].strip(), case=False, na=False, regex=False)]
        real_hist = real_hist[['year','value_M']].dropna().sort_values('year')
        if not real_hist.empty:
            # birth_year ≈ (2026 - cv_age) using the same age basis as the projection's current age
            birth_year = 2026 - cv_age
            real_hist = real_hist.copy()
            real_hist['hist_age'] = real_hist['year'] - birth_year
            # Drop any nonsensical ages outside a sane career window
            real_hist = real_hist[(real_hist['hist_age'] >= 14) & (real_hist['hist_age'] <= 42)]

    with ci2:
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(
            x=ages, y=traj, mode="lines+markers", name="Projected",
            line=dict(color=GREEN,width=3), fill='tozeroy', fillcolor="rgba(0,201,123,0.13)",
            marker=dict(size=[14 if a==peak_age else 6 for a in ages],
                        color=[GOLD if a==peak_age else GREEN for a in ages],
                        symbol=['star' if a==peak_age else 'circle' for a in ages]),
            hovertemplate="Age %{x}: €%{y:.1f}M<extra></extra>"))
        if not real_hist.empty:
            fig_t.add_trace(go.Scatter(
                x=real_hist['hist_age'], y=real_hist['value_M'], mode="markers+lines", name="Actual history",
                line=dict(color=BLUE, width=2, dash="dot"), marker=dict(size=8, color=BLUE, symbol="diamond"),
                customdata=real_hist['year'],
                hovertemplate="Age %{x} (Year %{customdata}): €%{y:.1f}M actual<extra></extra>"))
        layout_t = {**PLOT_THEME}; layout_t["height"]=340
        layout_t["xaxis"]=dict(title="Age",gridcolor="#1f2d45")
        layout_t["yaxis"]=dict(title="Value (€M)",gridcolor="#1f2d45")
        layout_t["title"]=dict(text="Market Value Trajectory",font=dict(color="#e8eaf0",size=13))
        layout_t["legend"]=dict(bgcolor="#111827",bordercolor="#1f2d45",orientation="h",y=-0.18)
        fig_t.update_layout(**layout_t)
        st.plotly_chart(fig_t, use_container_width=True)

        k1,k2,k3,k4 = st.columns(4)
        peak_val_str = f"€{peak_val:.0f}M" if peak_val >= 100 else f"€{peak_val:.1f}M"
        k1.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{GOLD};font-size:1.5rem;">{peak_val_str}</div>'
                    f'<div class="kpi-lbl">Peak Value</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{GREEN};">{peak_age}</div>'
                    f'<div class="kpi-lbl">Peak Age</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{BLUE};">+{growth:.0f}%</div>'
                    f'<div class="kpi-lbl">Growth to Peak</div></div>', unsafe_allow_html=True)
        decline_30_35 = ((val_at_35 - val_at_30) / val_at_30 * 100) if val_at_30 else 0
        k4.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{RED if decline_30_35<0 else GREEN};">{decline_30_35:+.0f}%</div>'
                    f'<div class="kpi-lbl">Value Change Age 30→35</div></div>', unsafe_allow_html=True)

    # ── Year-by-year table ──────────────────────────────────────
    st.markdown('<div class="sec-hdr">YEAR-BY-YEAR PROJECTION</div>', unsafe_allow_html=True)
    proj_table = pd.DataFrame({
        "Age": ages,
        "Projected Value (€M)": [round(v,1) for v in traj],
        "vs Current": [f"{((v/(cv_val/1e6))-1)*100:+.0f}%" for v in traj],
        "Phase": ["Development" if a < 27 else ("Peak" if a == peak_age else
                  ("Plateau" if 27 <= a < 30 else "Decline")) for a in ages]
    })
    st.dataframe(proj_table, use_container_width=True, height=260)

    # ── Peer comparison: similar-age, similar-position players ─
    st.markdown('<div class="sec-hdr">COMPARABLE PLAYERS</div>', unsafe_allow_html=True)
    st.caption(f"Other {cv_pos}s within ±2 years of age {cv_age} and ±5 rating points of {cv_rat}, for sanity-checking this projection")
    peer_pool = players[players["has_fifa_data"]].copy()
    age_col_p = 'age_2026' if 'age_2026' in peer_pool.columns else 'age'
    peers = peer_pool[
        (peer_pool['position_group'] == cv_pos) &
        (peer_pool[age_col_p].between(cv_age-2, cv_age+2)) &
        (peer_pool['overall_rating'].between(cv_rat-5, cv_rat+5))
    ].copy()
    if not peers.empty:
        peers['Value (€M)'] = (peers['value_euro']/1e6).round(1)
        peer_cols = ['display_name','club_display', age_col_p, 'overall_rating','potential','Value (€M)']
        peer_cols = [c for c in peer_cols if c in peers.columns]
        peer_show = peers[peer_cols].rename(columns={
            'display_name':'Player','club_display':'Club', age_col_p:'Age',
            'overall_rating':'Rating','potential':'Potential'})
        peer_show = peer_show.sort_values('Value (€M)', ascending=False).head(15).reset_index(drop=True)
        st.dataframe(peer_show, use_container_width=True, height=300)
    else:
        st.info("No close comparables found for this age/rating/position combination.")

# ── TAB 4: MARKET TRENDS ──────────────────────────────────────
with tab4:
    st.markdown('<div class="sec-hdr">MARKET VALUE TRENDS</div>', unsafe_allow_html=True)
    st.caption("Average market value across the full Transfermarkt history, broken down by position. Use the controls to focus on a position or year range.")

    if not mv.empty and 'value_M' in mv.columns and 'year' in mv.columns:
        pos_col = 'main_position' if 'main_position' in mv.columns else mv.columns[2] if len(mv.columns) > 2 else None

        mt1, mt2 = st.columns([1,3])
        with mt1:
            yr_min, yr_max = int(mv['year'].min()), int(mv['year'].max())
            yr_range = st.slider("Year range", yr_min, yr_max, (yr_min, yr_max), key="mv_yr")
            pos_filter_opts = ["All Positions"] + sorted(mv[pos_col].dropna().unique().tolist()) if pos_col else ["All Positions"]
            pos_filter = st.selectbox("Focus position", pos_filter_opts, key="mv_pos")

        mv_f = mv[(mv['year'] >= yr_range[0]) & (mv['year'] <= yr_range[1])].copy()
        if pos_col and pos_filter != "All Positions":
            mv_f = mv_f[mv_f[pos_col] == pos_filter]

        with mt2:
            if pos_col:
                mv_t = mv_f.groupby(['year', pos_col])['value_M'].mean().reset_index()

                # Distinct dash pattern per position so overlapping lines remain distinguishable.
                dash_map = {"Attack": "solid", "Midfield": "dash", "Defender": "dot", "Goalkeeper": "dashdot"}
                fig_m = px.line(mv_t, x='year', y='value_M', color=pos_col, markers=True,
                                line_dash=pos_col, line_dash_map=dash_map,
                                color_discrete_sequence=[GREEN,RED,BLUE,AMBER,PURPLE])
                fig_m.update_traces(line=dict(width=3), marker=dict(size=7))
                layout_m={**PLOT_THEME}; layout_m["height"]=320
                layout_m["xaxis"]=dict(title="Year",gridcolor="#1f2d45")
                layout_m["yaxis"]=dict(title="Average Value (€M)",gridcolor="#1f2d45")
                layout_m["legend"]=dict(bgcolor="#111827",bordercolor="#1f2d45")
                fig_m.update_layout(**layout_m)
                st.plotly_chart(fig_m, use_container_width=True)

        # ── Headline KPIs for filtered range ───────────────────
        mk1, mk2, mk3, mk4 = st.columns(4)
        start_avg = mv_f[mv_f['year']==yr_range[0]]['value_M'].mean()
        end_avg   = mv_f[mv_f['year']==yr_range[1]]['value_M'].mean()
        total_chg = ((end_avg - start_avg) / start_avg * 100) if start_avg else 0
        mk1.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{GREEN};">€{end_avg:.2f}M</div>'
                     f'<div class="kpi-lbl">Average Value ({yr_range[1]})</div></div>', unsafe_allow_html=True)
        mk2.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{GOLD};">€{mv_f["value_M"].max():.1f}M</div>'
                     f'<div class="kpi-lbl">Highest Value in Range</div></div>', unsafe_allow_html=True)
        mk3.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{BLUE if total_chg>=0 else RED};">{total_chg:+.0f}%</div>'
                     f'<div class="kpi-lbl">Average Change {yr_range[0]}→{yr_range[1]}</div></div>', unsafe_allow_html=True)
        mk4.markdown(f'<div class="kpi-card"><div class="kpi-val" style="color:{AMBER};">{mv_f["player_id"].nunique() if "player_id" in mv_f.columns else mv_f.shape[0]:,}</div>'
                     f'<div class="kpi-lbl">Players in Range</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Year-on-year growth ─────────────────────────────────
        yc1, yc2 = st.columns(2)
        with yc1:
            yoy = mv_f.groupby('year')['value_M'].mean().pct_change()*100
            yoy_df = yoy.reset_index(); yoy_df.columns = ['Year','YoY %']
            fig_y = px.bar(yoy_df.dropna(), x='Year', y='YoY %',
                           color='YoY %', color_continuous_scale=[RED,"#6B7280",GREEN],
                           color_continuous_midpoint=0)
            layout_y={**PLOT_THEME}; layout_y["height"]=260; layout_y["coloraxis_showscale"]=False
            layout_y["title"]=dict(text="Average Market Year-on-Year Growth %",font=dict(color="#e8eaf0",size=13))
            layout_y["xaxis"]=dict(gridcolor="#1f2d45"); layout_y["yaxis"]=dict(gridcolor="#1f2d45")
            fig_y.update_layout(**layout_y)
            st.plotly_chart(fig_y, use_container_width=True)

        with yc2:
            # Value distribution histogram for the latest year in range
            latest_yr_data = mv_f[mv_f['year']==yr_range[1]]
            if not latest_yr_data.empty:
                fig_h = px.histogram(latest_yr_data, x='value_M', nbins=40,
                                     color_discrete_sequence=[GREEN])
                layout_h={**PLOT_THEME}; layout_h["height"]=260
                layout_h["title"]=dict(text=f"Value Distribution — {yr_range[1]}",font=dict(color="#e8eaf0",size=13))
                layout_h["xaxis"]=dict(title="Value (€M)",gridcolor="#1f2d45")
                layout_h["yaxis"]=dict(title="Players",gridcolor="#1f2d45")
                fig_h.update_layout(**layout_h)
                st.plotly_chart(fig_h, use_container_width=True)

        # ── Top risers / fallers between first and last year in range ─
        if 'player_name' in mv_f.columns:
            st.markdown('<div class="sec-hdr">BIGGEST MOVERS IN SELECTED RANGE</div>', unsafe_allow_html=True)
            start_vals = mv_f[mv_f['year']==yr_range[0]][['player_name','value_M']].rename(columns={'value_M':'start_val'})
            end_vals   = mv_f[mv_f['year']==yr_range[1]][['player_name','value_M']].rename(columns={'value_M':'end_val'})
            moves = start_vals.merge(end_vals, on='player_name', how='inner')
            moves = moves[moves['start_val'] > 0.05]  # avoid div-by-near-zero noise
            moves['change_M'] = moves['end_val'] - moves['start_val']
            moves['change_pct'] = (moves['change_M'] / moves['start_val'] * 100).round(0)

            mv_c1, mv_c2 = st.columns(2)
            with mv_c1:
                st.markdown(f'<div style="font-size:.78rem;color:{GREEN};letter-spacing:1px;margin-bottom:.4rem;">📈 TOP 10 RISERS</div>', unsafe_allow_html=True)
                risers = moves.nlargest(10, 'change_M')[['player_name','start_val','end_val','change_pct']]
                risers.columns = ['Player', f'{yr_range[0]} (€M)', f'{yr_range[1]} (€M)', 'Change %']
                st.dataframe(risers.reset_index(drop=True), use_container_width=True, height=320)
            with mv_c2:
                st.markdown(f'<div style="font-size:.78rem;color:{RED};letter-spacing:1px;margin-bottom:.4rem;">📉 TOP 10 FALLERS</div>', unsafe_allow_html=True)
                fallers = moves.nsmallest(10, 'change_M')[['player_name','start_val','end_val','change_pct']]
                fallers.columns = ['Player', f'{yr_range[0]} (€M)', f'{yr_range[1]} (€M)', 'Change %']
                st.dataframe(fallers.reset_index(drop=True), use_container_width=True, height=320)
    else:
        st.info("Market value trend data loading...")
