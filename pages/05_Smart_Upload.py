"""Smart Upload & AI Analysis — SoccerLens."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from utils.styles import dedent_html, MAIN_CSS, SIDEBAR_BRAND
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import anthropic
import json
import io
import time
import warnings
warnings.filterwarnings("ignore")

# ── Theme constants ────────────────────────────────────────────
DARK   = "#0A0E1A"
CARD   = "#111827"
BORDER = "#1f2d45"
GREEN  = "#00C97B"
GOLD   = "#FFD700"
BLUE   = "#3B82F6"
RED    = "#EF4444"
PURPLE = "#8B5CF6"
AMBER  = "#F59E0B"

PLOT = dict(paper_bgcolor=CARD, plot_bgcolor=CARD,
            font=dict(color="#9CA3AF", size=11),
            margin=dict(l=10, r=10, t=35, b=10))

# ─────────────────────────────────────────────────────────────
# STEP 1 — DATA TYPE DETECTION
# ─────────────────────────────────────────────────────────────
DATA_TYPES = {
    "events":      "⚽ Match Event Data",
    "performance": "📊 Player Performance Stats",
    "attributes":  "🎮 FIFA / Player Attributes",
    "matches":     "🏟️ Match Results",
    "transfers":   "💰 Transfer Data",
    "generic":     "📋 General Football Data",
}

VISUAL_MENU = {
    "events": [
        ("🗺️ Shot Map",          "shot_map"),
        ("🔀 Pass Map",           "pass_map"),
        ("🔥 Activity Heatmap",   "heatmap"),
        ("📈 xG Timeline",        "xg_timeline"),
        ("🎯 Shot Zone Breakdown","shot_zones"),
        ("🏅 Top Players Table",  "top_players"),
    ],
    "performance": [
        ("🏅 Goal Scorers Leaderboard", "leaderboard"),
        ("📊 Goals vs Assists Scatter", "scatter_ga"),
        ("📈 Season Trend Line",        "trend"),
        ("🥧 Position Breakdown",       "position_pie"),
        ("⚡ Per-90 Comparison Bar",    "per90_bar"),
        ("🌍 Goals by Nationality",     "nationality_bar"),
    ],
    "attributes": [
        ("🕸️ Player Radar Chart",       "radar"),
        ("📊 Attribute Distribution",   "attr_dist"),
        ("🏅 Top Rated Players",        "top_rated"),
        ("🔵 Rating vs Market Value",   "rating_scatter"),
        ("📦 Position Comparison Box",  "position_box"),
        ("🌍 Top Nations Bar",          "nation_bar"),
    ],
    "matches": [
        ("📊 Results Grid",             "results_grid"),
        ("⚽ Goals Per Match Timeline", "goals_timeline"),
        ("🏠 Home vs Away Bar",         "home_away"),
        ("📋 League Table",             "league_table"),
        ("📈 Cumulative Points",        "cumulative_pts"),
        ("🥅 Goals For vs Against",     "gf_ga_scatter"),
    ],
    "transfers": [
        ("💰 Top Transfer Fees Bar",    "top_fees"),
        ("📈 Spend by Season",          "spend_season"),
        ("🔵 Fee vs Value Scatter",     "fee_value"),
        ("🌍 Spending by Country",      "country_spend"),
        ("📊 Transfer Type Breakdown",  "type_breakdown"),
        ("🏅 Top Clubs (Net Spend)",    "club_spend"),
    ],
    "generic": [
        ("📊 Column Distribution",      "col_dist"),
        ("🔵 Numeric Scatter",          "num_scatter"),
        ("📋 Data Summary Table",       "summary_table"),
        ("🏅 Top Rows Leaderboard",     "generic_lead"),
    ],
}

def normalise_cols(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ","_").str.replace(r"[^\w]","_",regex=True)
    return df

def detect_type(df):
    cols = set(df.columns.str.lower())
    # Events (StatsBomb / custom event data)
    if any(c in cols for c in ["shot_statsbomb_xg","xg","expected_goals"]) and \
       any(c in cols for c in ["x","location_x","start_x"]):
        return "events"
    if "type" in cols and any(c in cols for c in ["x","location_x"]) and \
       any(c in cols for c in ["player","player_name"]):
        return "events"
    # Match results
    if any(c in cols for c in ["home_team","home_score","home_goals"]) and \
       any(c in cols for c in ["away_team","away_score","away_goals"]):
        return "matches"
    # FIFA/attribute data
    if any(c in cols for c in ["finishing","overall_rating","overall"]) and \
       any(c in cols for c in ["dribbling","vision","positioning","passing"]):
        return "attributes"
    # Transfer data
    if any(c in cols for c in ["transfer_fee","fee","transfer_amount"]):
        return "transfers"
    # Performance data
    if any(c in cols for c in ["goals","goal"]) and \
       any(c in cols for c in ["assists","assist","minutes_played","minutes","appearances"]):
        return "performance"
    return "generic"

def friendly_col(col):
    return col.replace("_"," ").title()

def find_col(df, candidates):
    """Return first matching column name from candidates list."""
    cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None

# ─────────────────────────────────────────────────────────────
# STEP 2 — VISUAL GENERATORS
# ─────────────────────────────────────────────────────────────

def gen_shot_map(df):
    x_col = find_col(df, ["x","location_x","start_x","pos_x"])
    y_col = find_col(df, ["y","location_y","start_y","pos_y"])
    xg_col= find_col(df, ["shot_statsbomb_xg","xg","expected_goals","xG"])
    oc_col= find_col(df, ["shot_outcome","outcome","result","shot_outcome_clean"])
    pl_col= find_col(df, ["player","player_name","name"])
    type_col = find_col(df, ["type","event_type","event","action"])

    if not x_col or not y_col:
        st.warning("Shot map needs x and y coordinate columns.")
        return

    df_work = df.copy()

    # If this is a mixed events file (passes, crosses, dribbles, carries, shots all
    # sharing the same x/y columns), filter down to shot-type rows only — otherwise
    # every pass and carry on the pitch gets plotted as if it were a shot, scattering
    # dots everywhere instead of clustering them near goal where shots actually happen.
    shot_type_values = {"shot", "shots", "attempt", "attempt on goal"}
    if type_col:
        type_series = df_work[type_col].astype(str).str.lower().str.strip()
        is_shot_type = type_series.isin(shot_type_values)
        if is_shot_type.any():
            df_work = df_work[is_shot_type].copy()
        elif oc_col:
            # No rows literally tagged "Shot", but if outcome values look shot-specific
            # (Goal/Saved/Blocked/Off Target), use those as a fallback shot filter.
            oc_series = df_work[oc_col].astype(str).str.lower().str.strip()
            shot_outcomes = {"goal","saved","blocked","off target","off t","post","wayward"}
            is_shot_outcome = oc_series.isin(shot_outcomes)
            if is_shot_outcome.any():
                df_work = df_work[is_shot_outcome].copy()

    sub = df_work.dropna(subset=[x_col, y_col]).copy()
    sub["_x"] = pd.to_numeric(sub[x_col], errors="coerce")
    sub["_y"] = pd.to_numeric(sub[y_col], errors="coerce")
    sub = sub.dropna(subset=["_x", "_y"])

    if sub.empty:
        st.warning("No shot events found — this dataset may only contain non-shot events "
                   "(passes, dribbles, carries) for the current filters.")
        return

    if type_col:
        st.caption(f"Filtered to {len(sub):,} shot event(s) out of {len(df):,} total rows "
                   f"in this dataset (other event types like passes and dribbles excluded).")

    # Flag a real, separate issue from coordinate scaling: even after correctly filtering to
    # shot-type rows, randomly-generated dummy data can still place "shots" anywhere on the
    # pitch (e.g. x=9 in the defensive third) rather than clustering them near the goal the
    # way real shot data does. This isn't a charting bug — it's worth telling the user their
    # source data doesn't model realistic shot locations.
    far_side_frac = (sub["_x"] < sub["_x"].max() * 0.5).mean() if len(sub) else 0
    if type_col and far_side_frac > 0.25:
        st.caption(f"⚠️ {far_side_frac*100:.0f}% of shot events in this dataset have x-coordinates "
                   f"in the defensive half of the pitch, which is unusual for real shot data "
                   f"(shots normally cluster near goal). This may indicate randomly-generated "
                   f"or test data rather than real match coordinates.")

    # Auto-detect the coordinate system instead of assuming a fixed StatsBomb 120×80 pitch.
    # Uploaded data might be 0-100 normalized, 0-1 normalized, or a totally different scale —
    # plotting those directly onto a hardcoded 120×80 outline crushes every point against
    # the edges, which is exactly the bug this fixes.
    x_max_data, x_min_data = sub["_x"].max(), sub["_x"].min()
    y_max_data, y_min_data = sub["_y"].max(), sub["_y"].min()

    if x_max_data <= 1.05 and y_max_data <= 1.05:
        # 0-1 normalized coordinates — rescale onto a 120x80 pitch
        pitch_x, pitch_y = 120, 80
        sub["_x"] = sub["_x"] * pitch_x
        sub["_y"] = sub["_y"] * pitch_y
        coord_note = "Coordinates detected as 0–1 normalized and rescaled to a 120×80 pitch."
    elif x_max_data <= 121 and y_max_data <= 81 and x_max_data > 50:
        # Already StatsBomb-style 120x80 pitch (or a subset/half of it) — use as-is
        pitch_x, pitch_y = 120, 80
        coord_note = None
    else:
        # Unknown scale — build a pitch outline that matches the data's own bounding box
        # instead of forcing it onto a StatsBomb pitch it was never drawn for.
        pitch_x = max(x_max_data, 1)
        pitch_y = max(y_max_data, 1)
        coord_note = (f"Coordinates detected outside the standard 120×80 pitch range "
                      f"(x: {x_min_data:.1f}–{x_max_data:.1f}, y: {y_min_data:.1f}–{y_max_data:.1f}) "
                      f"— pitch outline scaled to match this dataset's own coordinate range.")

    # If shots are recorded at BOTH ends of the pitch (common in raw match-event data
    # where each team attacks a different direction at different points), normalize
    # everything onto a single attacking-direction pitch by flipping any shot whose x
    # is in the defensive half — otherwise half the shots plot on the wrong side
    # of the goal entirely.
    if x_min_data < pitch_x * 0.4:
        flip_mask = sub["_x"] < (pitch_x / 2)
        if flip_mask.any() and flip_mask.mean() < 1.0:
            sub.loc[flip_mask, "_x"] = pitch_x - sub.loc[flip_mask, "_x"]
            sub.loc[flip_mask, "_y"] = pitch_y - sub.loc[flip_mask, "_y"]
            if coord_note is None:
                coord_note = ""
            coord_note += (" Shots recorded at both ends of the pitch were mirrored onto a "
                           "single attacking direction for a cleaner shot map.")

    colour_col = oc_col or pl_col

    # Marker size: normalise whatever scale the uploaded xG column uses to a
    # safe 8-26 pixel range, instead of assuming a fixed 0-1 StatsBomb scale.
    def safe_marker_sizes(values):
        v = pd.to_numeric(values, errors="coerce").fillna(0)
        if v.max() > v.min():
            norm = (v - v.min()) / (v.max() - v.min())
        else:
            norm = pd.Series([0.3] * len(v), index=v.index)
        return (norm * 18 + 8).clip(8, 26)

    fig = go.Figure()
    box_w, box_h   = pitch_x * 0.15, pitch_y * 0.55   # 18-yd box proportional to pitch size
    six_w, six_h   = pitch_x * 0.05, pitch_y * 0.25   # 6-yd box
    goal_h         = pitch_y * 0.10
    for shape in [
        dict(type="rect", x0=0,y0=0,x1=pitch_x,y1=pitch_y, line=dict(color="#4B5563",width=2), fillcolor="#1a3a1a"),
        dict(type="rect", x0=pitch_x-box_w,y0=(pitch_y-box_h)/2,x1=pitch_x,y1=(pitch_y+box_h)/2,
             line=dict(color="#6B7280",width=1.5), fillcolor="rgba(0,0,0,0)"),
        dict(type="rect", x0=pitch_x-six_w,y0=(pitch_y-six_h)/2,x1=pitch_x,y1=(pitch_y+six_h)/2,
             line=dict(color="#6B7280",width=1), fillcolor="rgba(0,0,0,0)"),
        dict(type="rect", x0=pitch_x,y0=(pitch_y-goal_h)/2,x1=pitch_x+pitch_x*0.008,y1=(pitch_y+goal_h)/2,
             line=dict(color=GOLD,width=2), fillcolor=GOLD),
        dict(type="rect", x0=0,y0=(pitch_y-box_h)/2,x1=box_w,y1=(pitch_y+box_h)/2,
             line=dict(color="#6B7280",width=1.5), fillcolor="rgba(0,0,0,0)"),
        dict(type="line", x0=pitch_x/2,y0=0,x1=pitch_x/2,y1=pitch_y, line=dict(color="#4B5563",width=1.5)),
    ]:
        # CRITICAL: layer="below" forces these pitch shapes to render underneath the
        # scatter markers added later. Without this, Plotly draws shapes in their own
        # layer ABOVE traces by default, so the solid-filled pitch rectangle was painting
        # over every shot marker — only the slivers that fell outside the pitch's bounding
        # box were ever visible. This was the actual bug behind "markers behind the pitch".
        shape["layer"] = "below"
        fig.add_shape(**shape)

    if coord_note:
        st.caption(f"ℹ️ {coord_note}")

    # Canonical colors for known StatsBomb-style shot outcomes. Any outcome value that
    # ISN'T one of these (e.g. a user's own dataset using "Success"/"Fail", or a typo'd
    # variant) gets assigned a distinct color from a fallback palette instead of all
    # collapsing into the same gray — that was the bug: unmatched outcomes used to share
    # one flat fallback color, making the legend categories visually indistinguishable.
    outcome_color_map = {
        "goal": RED, "saved": BLUE, "off t": "#6B7280", "off target": "#6B7280",
        "blocked": PURPLE, "wayward": "#4B5563", "post": AMBER,
        "saved to post": "#0EA5E9", "saved off target": "#64748B",
        "success": GREEN, "fail": RED, "failed": RED, "successful": GREEN,
        "complete": GREEN, "incomplete": RED, "won": GREEN, "lost": RED,
    }
    fallback_palette = [GREEN, BLUE, AMBER, PURPLE, RED, "#06B6D4", "#F472B6", "#A3E635", "#FB923C"]

    if colour_col and colour_col == oc_col:
        seen_outcomes = set()
        outcome_series = sub[oc_col].astype(str).str.lower().str.strip()
        unmatched_idx = 0
        for outcome in outcome_series.unique():
            if outcome in seen_outcomes or outcome == "nan":
                continue
            seen_outcomes.add(outcome)
            if outcome in outcome_color_map:
                colour = outcome_color_map[outcome]
            else:
                colour = fallback_palette[unmatched_idx % len(fallback_palette)]
                unmatched_idx += 1
            mask = outcome_series == outcome
            grp = sub[mask]
            if grp.empty: continue
            sizes = safe_marker_sizes(grp[xg_col]) if xg_col else [12]*len(grp)
            fig.add_trace(go.Scatter(
                x=grp["_x"], y=grp["_y"], mode="markers",
                name=outcome.title(),
                marker=dict(size=sizes, color=colour, opacity=0.85,
                            line=dict(color="white",width=0.8)),
                hovertemplate=f"<b>{outcome.title()}</b><br>x:%{{x}}, y:%{{y}}<extra></extra>"
            ))
    else:
        sizes = safe_marker_sizes(sub[xg_col]) if xg_col else [12]*len(sub)
        fig.add_trace(go.Scatter(
            x=sub["_x"], y=sub["_y"], mode="markers", name="Shots",
            marker=dict(size=sizes, color=GREEN, opacity=0.8, line=dict(color="white",width=0.7)),
            hovertemplate="x:%{x}, y:%{y}<extra></extra>"
        ))

    pad_x, pad_y = pitch_x * 0.02, pitch_y * 0.03
    fig.update_layout(**PLOT, height=420,
        xaxis=dict(range=[-pad_x, pitch_x+pad_x*5],showgrid=False,zeroline=False,showticklabels=False,scaleanchor="y",scaleratio=1),
        yaxis=dict(range=[-pad_y, pitch_y+pad_y],showgrid=False,zeroline=False,showticklabels=False),
        legend=dict(bgcolor=CARD,bordercolor=BORDER,orientation="h",x=0.5,xanchor="center",y=-0.05),
        title=dict(text="Shot Map",font=dict(color="#e8eaf0",size=14))
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Dot size = relative xG within this dataset  ·  Colour = shot outcome")

def gen_heatmap(df):
    from mplsoccer import Pitch
    x_col = find_col(df, ["x","location_x","start_x","pos_x"])
    y_col = find_col(df, ["y","location_y","start_y","pos_y"])
    if not x_col or not y_col:
        st.warning("Heatmap needs x and y coordinate columns.")
        return
    sub = df.dropna(subset=[x_col, y_col]).copy()
    sub["_x"] = pd.to_numeric(sub[x_col], errors="coerce")
    sub["_y"] = pd.to_numeric(sub[y_col], errors="coerce")
    sub = sub.dropna(subset=["_x","_y"])
    fig, ax = plt.subplots(figsize=(10,6))
    fig.patch.set_facecolor(CARD); ax.set_facecolor("#1a3a1a")
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#1a3a1a", line_color="#4B5563")
    pitch.draw(ax=ax)
    if len(sub) >= 3:
        pitch.kdeplot(sub["_x"], sub["_y"], ax=ax, cmap="YlOrRd", fill=True, alpha=0.75, levels=10)
    ax.set_title("Activity Heatmap", color="#e8eaf0", fontsize=13, pad=8)
    st.pyplot(fig, use_container_width=True); plt.close()

def gen_pass_map(df):
    from mplsoccer import Pitch
    x_col  = find_col(df, ["x","start_x","location_x"])
    y_col  = find_col(df, ["y","start_y","location_y"])
    ex_col = find_col(df, ["end_x","pass_end_x","end_location_x"])
    ey_col = find_col(df, ["end_y","pass_end_y","end_location_y"])
    oc_col = find_col(df, ["outcome","pass_outcome","result"])

    if not all([x_col, y_col, ex_col, ey_col]):
        st.warning("Pass map needs x, y, end_x, end_y columns.")
        return

    fig, ax = plt.subplots(figsize=(10,6))
    fig.patch.set_facecolor(CARD); ax.set_facecolor("#1a3a1a")
    pitch = Pitch(pitch_type="statsbomb", pitch_color="#1a3a1a", line_color="#4B5563")
    pitch.draw(ax=ax)

    passes = df.dropna(subset=[x_col,y_col,ex_col,ey_col]).copy()
    passes["_sx"] = pd.to_numeric(passes[x_col],errors="coerce")
    passes["_sy"] = pd.to_numeric(passes[y_col],errors="coerce")
    passes["_ex"] = pd.to_numeric(passes[ex_col],errors="coerce")
    passes["_ey"] = pd.to_numeric(passes[ey_col],errors="coerce")
    passes = passes.dropna(subset=["_sx","_sy","_ex","_ey"])

    if oc_col:
        passes["_success"] = passes[oc_col].apply(
            lambda v: pd.isna(v) or str(v).lower() in ["success","complete","nan",""])
    else:
        passes["_success"] = True

    for _, row in passes.head(300).iterrows():
        c = GREEN if row["_success"] else RED
        ax.annotate("", xy=(row["_ex"],row["_ey"]), xytext=(row["_sx"],row["_sy"]),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=0.7, mutation_scale=8),
                    alpha=0.6 if row["_success"] else 0.35)

    ax.legend(handles=[mpatches.Patch(facecolor=GREEN,label="Successful"),
                        mpatches.Patch(facecolor=RED,label="Unsuccessful")],
              loc="upper right", facecolor=CARD, edgecolor=BORDER, labelcolor="#e8eaf0", fontsize=9)
    ax.set_title("Pass Map", color="#e8eaf0", fontsize=13, pad=8)
    st.pyplot(fig, use_container_width=True); plt.close()
    if len(passes) > 300:
        st.caption(f"Showing first 300 of {len(passes):,} passes for readability.")

def gen_xg_timeline(df):
    xg_col = find_col(df, ["shot_statsbomb_xg","xg","expected_goals","xG"])
    mn_col = find_col(df, ["minute","min","time_min","match_minute"])
    oc_col = find_col(df, ["shot_outcome","outcome","result"])
    pl_col = find_col(df, ["player","player_name","name"])
    if not xg_col or not mn_col:
        st.warning("xG timeline needs xg and minute columns."); return

    sub = df[[c for c in [xg_col,mn_col,oc_col,pl_col] if c]].copy()
    sub["_xg"] = pd.to_numeric(sub[xg_col], errors="coerce").fillna(0)
    sub["_min"]= pd.to_numeric(sub[mn_col], errors="coerce").fillna(0)
    sub = sub.sort_values("_min")
    sub["_cumxg"] = sub["_xg"].cumsum()
    is_goal = sub[oc_col].str.lower().str.contains("goal",na=False) if oc_col else pd.Series([False]*len(sub))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["_min"], y=sub["_cumxg"], mode="lines+markers",
        line=dict(color=GREEN, width=2.5),
        marker=dict(size=[13 if g else 7 for g in is_goal],
                    color=[RED if g else GREEN for g in is_goal],
                    symbol=["star" if g else "circle" for g in is_goal],
                    line=dict(width=1,color=DARK)),
        hovertemplate="Minute: %{x}<br>Cumulative xG: %{y:.3f}<extra></extra>"
    ))
    fig.update_layout(**PLOT, height=300,
        xaxis=dict(title="Minute", gridcolor=BORDER),
        yaxis=dict(title="Cumulative xG", gridcolor=BORDER),
        title=dict(text="xG Timeline  (⭐ = Goal)", font=dict(color="#e8eaf0",size=13))
    )
    st.plotly_chart(fig, use_container_width=True)

def gen_shot_zones(df):
    zone_col = find_col(df, ["shot_zone","zone","area"])
    xg_col   = find_col(df, ["shot_statsbomb_xg","xg","expected_goals"])
    oc_col   = find_col(df, ["shot_outcome","outcome","result"])

    # If no zone col, compute from x/y
    if not zone_col:
        x_col = find_col(df, ["x","start_x","location_x"])
        y_col = find_col(df, ["y","start_y","location_y"])
        if x_col and y_col:
            def zone(x, y):
                try:
                    d = np.sqrt((120-float(x))**2 + (40-float(y))**2)
                    if d < 6:  return "Six-Yard Box"
                    if d < 12: return "Central (12m)"
                    if d < 20: return "Penalty Area"
                    if d < 30: return "Edge of Box"
                    return "Long Range"
                except: return "Unknown"
            df = df.copy()
            df["_zone"] = df.apply(lambda r: zone(r[x_col], r[y_col]), axis=1)
            zone_col = "_zone"
        else:
            st.warning("Shot zone breakdown needs x/y or zone column."); return

    agg = {"shots": (zone_col,"count")}
    if xg_col: agg["avg_xg"] = (xg_col, lambda x: pd.to_numeric(x,errors="coerce").mean())
    if oc_col:
        df = df.copy()
        df["_is_goal"] = df[oc_col].astype(str).str.lower().str.contains("goal")
        agg["goals"] = ("_is_goal","sum")

    zone_df = df.groupby(zone_col).agg(**agg).reset_index()
    zone_df.columns = ["Zone"] + list(agg.keys())
    if "goals" in zone_df: zone_df["conv_%"] = (zone_df["goals"]/zone_df["shots"]*100).round(1)

    fig = px.bar(zone_df, x="Zone", y="shots",
                 color="avg_xg" if "avg_xg" in zone_df else "shots",
                 color_continuous_scale=[BORDER, GREEN],
                 hover_data=[c for c in ["avg_xg","goals","conv_%"] if c in zone_df],
                 labels={"shots":"Shots","avg_xg":"Avg xG"})
    fig.update_layout(**PLOT, height=300,
        title=dict(text="Shot Zones", font=dict(color="#e8eaf0",size=13)),
        coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

def gen_leaderboard(df):
    pl_col = find_col(df, ["player","player_name","name","athlete"])
    g_col  = find_col(df, ["goals","goal","total_goals","goals_scored"])
    a_col  = find_col(df, ["assists","assist","total_assists"])
    m_col  = find_col(df, ["minutes_played","minutes","mins"])
    t_col  = find_col(df, ["team","team_name","club"])
    pos_col= find_col(df, ["position","pos","role","main_position"])

    if not pl_col:
        st.warning("Leaderboard needs a player/name column."); return

    agg_dict = {}
    if g_col: agg_dict["Goals"]   = (g_col,  lambda x: pd.to_numeric(x,errors="coerce").sum())
    if a_col: agg_dict["Assists"]  = (a_col,  lambda x: pd.to_numeric(x,errors="coerce").sum())
    if m_col: agg_dict["Minutes"]  = (m_col,  lambda x: pd.to_numeric(x,errors="coerce").sum())
    if t_col: agg_dict["Team"]     = (t_col,  "first")
    if pos_col: agg_dict["Position"]=(pos_col,"first")

    if agg_dict:
        board = df.groupby(pl_col).agg(**agg_dict).reset_index()
    else:
        board = df[[pl_col]].drop_duplicates().rename(columns={pl_col:"Player"})

    board = board.rename(columns={pl_col:"Player"})
    if "Goals" in board: board = board.sort_values("Goals", ascending=False)
    if "Goals" in board and "Minutes" in board:
        board["Goals/90"] = (board["Goals"] / board["Minutes"].replace(0,np.nan) * 90).round(2)

    st.dataframe(board.reset_index(drop=True), use_container_width=True, height=420)

    if "Goals" in board:
        top = board.head(15)
        fig = px.bar(top, x="Goals", y="Player", orientation="h",
                     color="Goals", color_continuous_scale=[BORDER, GREEN])
        fig.update_layout(**PLOT, height=360, coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            title=dict(text="Top Goal Scorers",font=dict(color="#e8eaf0",size=13)))
        st.plotly_chart(fig, use_container_width=True)

def gen_scatter_ga(df):
    g_col = find_col(df, ["goals","total_goals"])
    a_col = find_col(df, ["assists","total_assists"])
    pl_col= find_col(df, ["player","player_name","name"])
    t_col = find_col(df, ["team","team_name","club"])
    if not g_col or not a_col:
        st.warning("Scatter needs goals and assists columns."); return
    plot_df = df.copy()
    plot_df["_g"] = pd.to_numeric(plot_df[g_col], errors="coerce")
    plot_df["_a"] = pd.to_numeric(plot_df[a_col], errors="coerce")
    plot_df = plot_df.dropna(subset=["_g","_a"])
    hover = pl_col or t_col
    fig = px.scatter(plot_df, x="_g", y="_a", color=t_col,
                     hover_data=[hover] if hover else None,
                     labels={"_g":"Goals","_a":"Assists"},
                     color_discrete_sequence=[GREEN,BLUE,AMBER,RED,PURPLE])
    fig.add_shape(type="line",x0=0,y0=0,x1=plot_df["_g"].max(),y1=plot_df["_a"].max(),
                  line=dict(color=BORDER,dash="dash"))
    fig.update_layout(**PLOT, height=360,
        title=dict(text="Goals vs Assists",font=dict(color="#e8eaf0",size=13)),
        xaxis=dict(title="Goals",gridcolor=BORDER),
        yaxis=dict(title="Assists",gridcolor=BORDER))
    st.plotly_chart(fig, use_container_width=True)

def gen_per90_bar(df):
    pl_col = find_col(df, ["player","player_name","name"])
    g_col  = find_col(df, ["goals","total_goals"])
    m_col  = find_col(df, ["minutes_played","minutes","mins"])
    if not pl_col or not g_col or not m_col:
        st.warning("Per-90 chart needs player, goals, and minutes columns."); return
    df2 = df.copy()
    df2["_g"] = pd.to_numeric(df2[g_col],errors="coerce")
    df2["_m"] = pd.to_numeric(df2[m_col],errors="coerce")
    df2 = df2.dropna(subset=["_g","_m"])
    df2["Goals/90"] = (df2["_g"] / df2["_m"] * 90).round(3)
    df2 = df2[df2["_m"] >= 90].nlargest(15,"Goals/90")
    fig = px.bar(df2, x="Goals/90", y=pl_col, orientation="h",
                 color="Goals/90", color_continuous_scale=[BORDER,GREEN])
    fig.update_layout(**PLOT, height=380, coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        title=dict(text="Goals per 90 Minutes (min. 90 mins played)",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig, use_container_width=True)

def gen_radar(df):
    pl_col = find_col(df, ["player","player_name","name"])
    attr_candidates = ["pace","shooting","passing","dribbling","defending","physical",
                       "finishing","positioning","vision","composure","acceleration",
                       "sprint_speed","overall_rating","stamina","strength"]
    attrs = [find_col(df, [a]) for a in attr_candidates if find_col(df, [a])]
    if not pl_col or len(attrs) < 3:
        st.warning("Radar needs a player column and at least 3 numeric attribute columns."); return

    players = sorted(df[pl_col].dropna().unique().tolist())
    c1, c2 = st.columns(2)
    p_a = c1.selectbox("Player A", players, index=0, key="radar_a")
    p_b = c2.selectbox("Player B", [p for p in players if p != p_a], index=0, key="radar_b")

    def get_vals(player):
        row = df[df[pl_col] == player].iloc[0] if not df[df[pl_col]==player].empty else None
        if row is None: return [50]*len(attrs)
        return [float(pd.to_numeric(row.get(a,50),errors="coerce") or 50) for a in attrs]

    va, vb = get_vals(p_a), get_vals(p_b)
    mx = [max(a,b,1) for a,b in zip(va,vb)]
    na = [v/m for v,m in zip(va,mx)]
    nb = [v/m for v,m in zip(vb,mx)]
    labels = [friendly_col(a) for a in attrs]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=na+[na[0]], theta=labels+[labels[0]],
        fill="toself", name=p_a, line=dict(color=GREEN,width=2), fillcolor=GREEN+"22"))
    fig.add_trace(go.Scatterpolar(r=nb+[nb[0]], theta=labels+[labels[0]],
        fill="toself", name=p_b, line=dict(color=RED,width=2), fillcolor=RED+"22"))
    fig.update_layout(
        polar=dict(bgcolor=CARD,
                   radialaxis=dict(visible=True,range=[0,1],gridcolor=BORDER,tickfont=dict(color="#6B7280",size=8)),
                   angularaxis=dict(gridcolor=BORDER,tickfont=dict(color="#9CA3AF",size=10))),
        paper_bgcolor=DARK, font=dict(color="#e8eaf0"),
        legend=dict(bgcolor=CARD,bordercolor=BORDER),
        height=400, margin=dict(l=50,r=50,t=30,b=30),
        title=dict(text="Player Attribute Radar",font=dict(color="#e8eaf0",size=13))
    )
    st.plotly_chart(fig, use_container_width=True)

def gen_attr_dist(df):
    num_cols = df.select_dtypes(include="number").columns.tolist()[:8]
    if not num_cols:
        st.warning("No numeric columns found for distribution."); return
    chosen = st.selectbox("Select attribute", num_cols, key="attr_dist_sel")
    pos_col = find_col(df, ["position","position_group","pos","role"])
    colour = pos_col if pos_col else None
    fig = px.histogram(df, x=chosen, color=colour, nbins=30,
                       color_discrete_sequence=[GREEN,BLUE,AMBER,RED])
    fig.update_layout(**PLOT, height=320,
        title=dict(text=f"Distribution: {friendly_col(chosen)}",font=dict(color="#e8eaf0",size=13)),
        xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig, use_container_width=True)

def gen_top_rated(df):
    r_col  = find_col(df, ["overall_rating","overall","rating","overall_score"])
    pl_col = find_col(df, ["player","player_name","name","full_name"])
    t_col  = find_col(df, ["team","team_name","club","current_club_name"])
    if not r_col:
        st.warning("Top rated needs an overall_rating / rating column."); return
    df2 = df.copy()
    df2["_r"] = pd.to_numeric(df2[r_col], errors="coerce")
    label = pl_col or df.columns[0]
    top = df2.nlargest(15,"_r")
    fig = px.bar(top, x="_r", y=label, orientation="h",
                 color="_r", color_continuous_scale=[BORDER,GOLD],
                 hover_data=[t_col] if t_col else None,
                 labels={"_r":"Overall Rating"})
    fig.update_layout(**PLOT, height=380, coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        title=dict(text="Top Rated Players",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig, use_container_width=True)

def gen_rating_scatter(df):
    r_col = find_col(df, ["overall_rating","overall","rating"])
    v_col = find_col(df, ["value_euro","market_value","value","wage_euro"])
    p_col = find_col(df, ["position","position_group","pos","role"])
    n_col = find_col(df, ["player","player_name","name"])
    if not r_col or not v_col:
        st.warning("Rating scatter needs rating and market value columns."); return
    df2 = df.copy()
    df2["_r"] = pd.to_numeric(df2[r_col], errors="coerce")
    df2["_v"] = pd.to_numeric(df2[v_col], errors="coerce")
    df2 = df2.dropna(subset=["_r","_v"])
    fig = px.scatter(df2.sample(min(2000,len(df2)),random_state=42),
                     x="_r", y="_v", color=p_col,
                     hover_data=[n_col] if n_col else None,
                     color_discrete_sequence=[GREEN,BLUE,AMBER,RED],
                     labels={"_r":"Overall Rating","_v":friendly_col(v_col)})
    fig.update_layout(**PLOT, height=360,
        title=dict(text="Rating vs Market Value",font=dict(color="#e8eaf0",size=13)),
        xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig, use_container_width=True)

def gen_league_table(df):
    t_col = find_col(df, ["team","team_name","club","home_team"])
    p_col = find_col(df, ["points","pts","total_points"])
    g_col = find_col(df, ["goals_for","gf","goals_scored"])
    ga_col= find_col(df, ["goals_against","ga"])
    w_col = find_col(df, ["wins","won","w"])
    if not t_col:
        st.warning("League table needs a team column."); return

    if p_col:
        tbl = df[[c for c in [t_col,p_col,g_col,ga_col,w_col] if c]].copy()
        tbl = tbl.sort_values(p_col, ascending=False).reset_index(drop=True)
        tbl.index += 1
        st.dataframe(tbl, use_container_width=True)
    elif find_col(df,["home_team"]) and find_col(df,["away_team"]):
        ht = find_col(df,["home_team"]); at = find_col(df,["away_team"])
        hs = find_col(df,["home_score","home_goals"]); as_ = find_col(df,["away_score","away_goals"])
        if hs and as_:
            rows = []
            for t in pd.concat([df[ht],df[at]]).unique():
                hm = df[df[ht]==t]; aw = df[df[at]==t]
                hpts = ((pd.to_numeric(hm[hs],errors="coerce")>pd.to_numeric(hm[as_],errors="coerce"))*3 +
                        (pd.to_numeric(hm[hs],errors="coerce")==pd.to_numeric(hm[as_],errors="coerce"))*1).sum()
                apts = ((pd.to_numeric(aw[as_],errors="coerce")>pd.to_numeric(aw[hs],errors="coerce"))*3 +
                        (pd.to_numeric(aw[as_],errors="coerce")==pd.to_numeric(aw[hs],errors="coerce"))*1).sum()
                rows.append({"Team":t,"P":len(hm)+len(aw),"Pts":int(hpts+apts),
                             "GF":int(pd.to_numeric(hm[hs],errors="coerce").sum()+pd.to_numeric(aw[as_],errors="coerce").sum()),
                             "GA":int(pd.to_numeric(hm[as_],errors="coerce").sum()+pd.to_numeric(aw[hs],errors="coerce").sum())})
            tbl = pd.DataFrame(rows).sort_values("Pts",ascending=False).reset_index(drop=True)
            tbl.index += 1; tbl["GD"] = tbl["GF"]-tbl["GA"]
            st.dataframe(tbl, use_container_width=True)

def gen_top_fees(df):
    f_col  = find_col(df, ["transfer_fee","fee","transfer_amount"])
    pl_col = find_col(df, ["player","player_name","name"])
    t_col  = find_col(df, ["to_team_name","to_team","to_club"])
    s_col  = find_col(df, ["season_name","season","year"])
    if not f_col:
        st.warning("Transfer fee chart needs a transfer_fee column."); return
    df2 = df.copy()
    df2["_fee"] = pd.to_numeric(df2[f_col], errors="coerce")
    df2 = df2[df2["_fee"] > 0].nlargest(20,"_fee")
    label = pl_col or df.columns[0]
    if s_col: df2["_label"] = df2[label].astype(str)+" ("+df2[s_col].astype(str)+")"
    else:     df2["_label"] = df2[label].astype(str)
    df2["_fee_M"] = (df2["_fee"]/1e6).round(1)
    fig = px.bar(df2, x="_fee_M", y="_label", orientation="h",
                 color="_fee_M", color_continuous_scale=[BORDER,PURPLE],
                 labels={"_fee_M":"Fee (€M)","_label":"Player"})
    fig.update_layout(**PLOT, height=420, coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        title=dict(text="Top Transfer Fees (€M)",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig, use_container_width=True)

def gen_spend_season(df):
    f_col = find_col(df, ["transfer_fee","fee"])
    s_col = find_col(df, ["season_name","season","year"])
    if not f_col or not s_col:
        st.warning("Season spend needs transfer_fee and season columns."); return
    df2 = df.copy()
    df2["_fee"] = pd.to_numeric(df2[f_col],errors="coerce")
    agg = df2[df2["_fee"]>0].groupby(s_col)["_fee"].sum().reset_index()
    agg.columns = ["Season","Total (€)"]
    agg["Total (€M)"] = (agg["Total (€)"]/1e6).round(1)
    fig = px.bar(agg, x="Season", y="Total (€M)",
                 color="Total (€M)", color_continuous_scale=[BORDER,BLUE])
    fig.update_layout(**PLOT, height=300, coloraxis_showscale=False,
        xaxis=dict(tickangle=-35,gridcolor=BORDER),
        yaxis=dict(title="Transfer Spend (€M)",gridcolor=BORDER),
        title=dict(text="Transfer Spend by Season",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig, use_container_width=True)

def gen_col_dist(df):
    num_cols = df.select_dtypes(include="number").columns.tolist()
    if not num_cols:
        st.warning("No numeric columns found."); return
    chosen = st.selectbox("Select column", num_cols, key="col_dist_sel")
    fig = px.histogram(df, x=chosen, nbins=30, color_discrete_sequence=[GREEN])
    fig.update_layout(**PLOT, height=300,
        title=dict(text=f"Distribution: {friendly_col(chosen)}",font=dict(color="#e8eaf0",size=13)),
        xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig, use_container_width=True)

def gen_summary_table(df):
    num_df = df.describe().round(3)
    st.dataframe(num_df, use_container_width=True)

def gen_position_pie(df):
    p_col = find_col(df, ["position","position_group","pos","role","main_position"])
    if not p_col:
        st.warning("Position chart needs a position column."); return
    vc = df[p_col].value_counts().reset_index()
    vc.columns = ["Position","Count"]
    fig = px.pie(vc, values="Count", names="Position", hole=0.4,
                 color_discrete_sequence=[GREEN,BLUE,AMBER,RED,PURPLE])
    fig.update_layout(**PLOT, height=320,
        title=dict(text="Position Breakdown",font=dict(color="#e8eaf0",size=13)))
    fig.update_traces(textinfo="label+percent")
    st.plotly_chart(fig, use_container_width=True)

def gen_nationality_bar(df):
    n_col = find_col(df, ["nationality","citizenship","country","nation"])
    g_col = find_col(df, ["goals","total_goals"])
    if not n_col:
        st.warning("Nationality chart needs a nationality/country column."); return
    if g_col:
        df2 = df.copy(); df2["_g"]=pd.to_numeric(df2[g_col],errors="coerce")
        agg = df2.groupby(n_col)["_g"].sum().nlargest(15).reset_index()
        agg.columns = ["Nation","Goals"]
        fig = px.bar(agg, x="Goals", y="Nation", orientation="h",
                     color="Goals", color_continuous_scale=[BORDER,GREEN])
    else:
        vc = df[n_col].value_counts().head(15).reset_index()
        vc.columns = ["Nation","Players"]
        fig = px.bar(vc, x="Players", y="Nation", orientation="h",
                     color="Players", color_continuous_scale=[BORDER,GREEN])
    fig.update_layout(**PLOT, height=380, coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        title=dict(text="Goals / Players by Nationality",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig, use_container_width=True)

def gen_position_box(df):
    p_col  = find_col(df, ["position","position_group","pos"])
    r_col  = find_col(df, ["overall_rating","overall","rating"])
    if not p_col or not r_col:
        st.warning("Position box needs position and rating columns."); return
    df2 = df.copy(); df2["_r"]=pd.to_numeric(df2[r_col],errors="coerce")
    fig = px.box(df2.dropna(subset=["_r"]), x=p_col, y="_r", color=p_col,
                 color_discrete_sequence=[GREEN,BLUE,AMBER,RED], points=False,
                 labels={"_r":"Rating",p_col:"Position"})
    fig.update_layout(**PLOT, height=320, showlegend=False,
        title=dict(text="Rating Distribution by Position",font=dict(color="#e8eaf0",size=13)),
        yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig, use_container_width=True)

def gen_home_away(df):
    ht=find_col(df,["home_team"]); at=find_col(df,["away_team"])
    hs=find_col(df,["home_score","home_goals"]); as_=find_col(df,["away_score","away_goals"])
    if not all([ht,at,hs,as_]):
        st.warning("Home/Away chart needs home_team, away_team, home_score, away_score."); return
    df2=df.copy()
    df2["_hs"]=pd.to_numeric(df2[hs],errors="coerce"); df2["_as"]=pd.to_numeric(df2[as_],errors="coerce")
    df2["result"]=df2.apply(lambda r:"Home Win" if r["_hs"]>r["_as"] else "Away Win" if r["_as"]>r["_hs"] else "Draw",axis=1)
    vc=df2["result"].value_counts().reset_index(); vc.columns=["Result","Count"]
    fig=px.bar(vc,x="Result",y="Count",color="Result",
               color_discrete_map={"Home Win":GREEN,"Away Win":RED,"Draw":AMBER})
    fig.update_layout(**PLOT,height=280,showlegend=False,
        title=dict(text="Home vs Away Results",font=dict(color="#e8eaf0",size=13)),
        yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig,use_container_width=True)

def gen_cumulative_pts(df):
    t_col=find_col(df,["team","home_team"]); at=find_col(df,["away_team"])
    hs=find_col(df,["home_score","home_goals"]); as_=find_col(df,["away_score","away_goals"])
    if not all([t_col,hs,as_]): st.warning("Needs team, home_score, away_score."); return
    st.info("Cumulative points chart best with match-level data — showing goals over time instead.")
    gen_goals_timeline(df)

def gen_goals_timeline(df):
    mn_col=find_col(df,["minute","min","date","match_date","round"])
    g_col=find_col(df,["goals","home_score","total_goals"])
    if not mn_col or not g_col: st.warning("Timeline needs a time/date column and goals."); return
    df2=df.copy(); df2["_g"]=pd.to_numeric(df2[g_col],errors="coerce")
    df2=df2.sort_values(mn_col)
    df2["_cum"]=df2["_g"].cumsum()
    fig=px.area(df2,x=mn_col,y="_cum",labels={"_cum":"Cumulative Goals",mn_col:friendly_col(mn_col)})
    fig.update_traces(line_color=GREEN,fillcolor=GREEN+"33")
    fig.update_layout(**PLOT,height=300,
        title=dict(text="Goals Over Time",font=dict(color="#e8eaf0",size=13)),
        xaxis=dict(gridcolor=BORDER),yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig,use_container_width=True)

def gen_gf_ga_scatter(df):
    t_col=find_col(df,["team","team_name"]); gf=find_col(df,["goals_for","gf","goals_scored"])
    ga=find_col(df,["goals_against","ga"])
    if not gf or not ga: st.warning("GF/GA scatter needs goals_for and goals_against."); return
    df2=df.copy(); df2["_gf"]=pd.to_numeric(df2[gf],errors="coerce"); df2["_ga"]=pd.to_numeric(df2[ga],errors="coerce")
    fig=px.scatter(df2.dropna(subset=["_gf","_ga"]),x="_gf",y="_ga",
                   text=t_col,color="_gf",color_continuous_scale=[RED,GREEN],
                   labels={"_gf":"Goals For","_ga":"Goals Against"})
    fig.update_layout(**PLOT,height=360,coloraxis_showscale=False,
        title=dict(text="Goals For vs Goals Against",font=dict(color="#e8eaf0",size=13)),
        xaxis=dict(gridcolor=BORDER),yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig,use_container_width=True)

def gen_fee_value(df):
    f_col=find_col(df,["transfer_fee","fee"]); v_col=find_col(df,["value_at_transfer","market_value","value"])
    p_col=find_col(df,["player","player_name","name"])
    if not f_col or not v_col: st.warning("Fee vs value scatter needs transfer_fee and value columns."); return
    df2=df.copy(); df2["_f"]=pd.to_numeric(df2[f_col],errors="coerce")/1e6; df2["_v"]=pd.to_numeric(df2[v_col],errors="coerce")/1e6
    df2=df2[(df2["_f"]>0)&(df2["_v"]>0)]
    fig=px.scatter(df2.sample(min(500,len(df2)),random_state=42),x="_v",y="_f",
                   hover_data=[p_col] if p_col else None,
                   labels={"_v":"Market Value (€M)","_f":"Transfer Fee (€M)"},
                   color_discrete_sequence=[PURPLE])
    fig.add_shape(type="line",x0=0,y0=0,x1=df2["_v"].max(),y1=df2["_v"].max(),
                  line=dict(color=AMBER,dash="dash"))
    fig.update_layout(**PLOT,height=360,
        title=dict(text="Transfer Fee vs Market Value (dashed = fair value)",font=dict(color="#e8eaf0",size=13)),
        xaxis=dict(gridcolor=BORDER),yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig,use_container_width=True)

def gen_country_spend(df):
    c_col=find_col(df,["citizenship","nationality","country"]); f_col=find_col(df,["transfer_fee","fee"])
    if not c_col or not f_col: st.warning("Country spend needs country and fee columns."); return
    df2=df.copy(); df2["_f"]=pd.to_numeric(df2[f_col],errors="coerce")
    agg=df2[df2["_f"]>0].groupby(c_col)["_f"].sum().nlargest(15).reset_index()
    agg.columns=["Country","Total (€)"]
    agg["Total (€M)"]=(agg["Total (€)"]/1e6).round(1)
    fig=px.bar(agg,x="Total (€M)",y="Country",orientation="h",
               color="Total (€M)",color_continuous_scale=[BORDER,PURPLE])
    fig.update_layout(**PLOT,height=380,coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        title=dict(text="Transfer Spend by Country",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig,use_container_width=True)

def gen_type_breakdown(df):
    t_col=find_col(df,["transfer_type","type"])
    if not t_col: st.warning("Type breakdown needs a transfer_type column."); return
    vc=df[t_col].value_counts().reset_index(); vc.columns=["Type","Count"]
    fig=px.pie(vc,values="Count",names="Type",hole=0.4,
               color_discrete_sequence=[GREEN,BLUE,AMBER,RED,PURPLE])
    fig.update_layout(**PLOT,height=300,
        title=dict(text="Transfer Type Breakdown",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig,use_container_width=True)

def gen_club_spend(df):
    t_col=find_col(df,["to_team_name","to_team","to_club","club"]); f_col=find_col(df,["transfer_fee","fee"])
    if not t_col or not f_col: st.warning("Club spend needs team and fee columns."); return
    df2=df.copy(); df2["_f"]=pd.to_numeric(df2[f_col],errors="coerce")
    agg=df2[df2["_f"]>0].groupby(t_col)["_f"].sum().nlargest(12).reset_index()
    agg.columns=["Club","Spend (€)"]; agg["Spend (€M)"]=(agg["Spend (€)"]/1e6).round(1)
    fig=px.bar(agg,x="Spend (€M)",y="Club",orientation="h",
               color="Spend (€M)",color_continuous_scale=[BORDER,PURPLE])
    fig.update_layout(**PLOT,height=360,coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        title=dict(text="Top Clubs by Transfer Spend",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig,use_container_width=True)

def gen_nation_bar(df):
    n_col=find_col(df,["nationality","citizenship","country"])
    if not n_col: st.warning("Nationality bar needs a nationality column."); return
    vc=df[n_col].value_counts().head(20).reset_index(); vc.columns=["Nation","Players"]
    fig=px.bar(vc,x="Players",y="Nation",orientation="h",
               color="Players",color_continuous_scale=[BORDER,GREEN])
    fig.update_layout(**PLOT,height=420,coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        title=dict(text="Top 20 Nations by Player Count",font=dict(color="#e8eaf0",size=13)))
    st.plotly_chart(fig,use_container_width=True)

def gen_top_players(df):
    """Generic top players for events data"""
    pl_col=find_col(df,["player","player_name","name"])
    xg_col=find_col(df,["shot_statsbomb_xg","xg","expected_goals"])
    if not pl_col: st.warning("Top players needs a player column."); return
    if xg_col:
        agg=df.groupby(pl_col).agg(shots=(pl_col,"count"),total_xg=(xg_col,lambda x:pd.to_numeric(x,errors="coerce").sum())).reset_index()
        agg.columns=["Player","Shots","Total xG"]
        agg=agg.nlargest(15,"Total xG")
        fig=px.bar(agg,x="Total xG",y="Player",orientation="h",
                   color="Total xG",color_continuous_scale=[BORDER,GREEN])
        fig.update_layout(**PLOT,height=380,coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
            title=dict(text="Top Players by xG",font=dict(color="#e8eaf0",size=13)))
        st.plotly_chart(fig,use_container_width=True)

def gen_results_grid(df):
    ht=find_col(df,["home_team"]); at=find_col(df,["away_team"])
    hs=find_col(df,["home_score","home_goals"]); as_=find_col(df,["away_score","away_goals"])
    if not all([ht,at,hs,as_]): st.warning("Results grid needs home_team, away_team, home_score, away_score."); return
    df2=df.copy()
    df2["Score"]=df2[hs].astype(str)+"–"+df2[as_].astype(str)
    df2["Result"]=df2.apply(lambda r:"🟢" if str(r[hs])>str(r[as_]) else "🔴" if str(r[as_])>str(r[hs]) else "🟡",axis=1)
    tbl=df2[[ht,at,"Score","Result"]].rename(columns={ht:"Home",at:"Away"})
    st.dataframe(tbl,use_container_width=True,height=400)

def gen_num_scatter(df):
    num_cols=df.select_dtypes(include="number").columns.tolist()
    if len(num_cols)<2: st.warning("Scatter needs at least 2 numeric columns."); return
    c1,c2=st.columns(2)
    x=c1.selectbox("X axis",num_cols,index=0,key="ns_x")
    y=c2.selectbox("Y axis",num_cols,index=min(1,len(num_cols)-1),key="ns_y")
    fig=px.scatter(df.sample(min(2000,len(df)),random_state=42),x=x,y=y,
                   color_discrete_sequence=[GREEN],opacity=0.7)
    fig.update_layout(**PLOT,height=360,
        title=dict(text=f"{friendly_col(x)} vs {friendly_col(y)}",font=dict(color="#e8eaf0",size=13)),
        xaxis=dict(gridcolor=BORDER),yaxis=dict(gridcolor=BORDER))
    st.plotly_chart(fig,use_container_width=True)

def gen_generic_lead(df):
    num_cols=df.select_dtypes(include="number").columns.tolist()
    if not num_cols: st.warning("No numeric columns for leaderboard."); return
    sort_col=st.selectbox("Sort by",num_cols,key="gl_sort")
    st.dataframe(df.sort_values(sort_col,ascending=False).head(30).reset_index(drop=True),
                 use_container_width=True)

# Map visual IDs to generator functions
VISUAL_FN = {
    "shot_map":       gen_shot_map,
    "pass_map":       gen_pass_map,
    "heatmap":        gen_heatmap,
    "xg_timeline":    gen_xg_timeline,
    "shot_zones":     gen_shot_zones,
    "top_players":    gen_top_players,
    "leaderboard":    gen_leaderboard,
    "scatter_ga":     gen_scatter_ga,
    "trend":          gen_goals_timeline,
    "position_pie":   gen_position_pie,
    "per90_bar":      gen_per90_bar,
    "nationality_bar":gen_nationality_bar,
    "radar":          gen_radar,
    "attr_dist":      gen_attr_dist,
    "top_rated":      gen_top_rated,
    "rating_scatter": gen_rating_scatter,
    "position_box":   gen_position_box,
    "nation_bar":     gen_nation_bar,
    "results_grid":   gen_results_grid,
    "goals_timeline": gen_goals_timeline,
    "home_away":      gen_home_away,
    "league_table":   gen_league_table,
    "cumulative_pts": gen_cumulative_pts,
    "gf_ga_scatter":  gen_gf_ga_scatter,
    "top_fees":       gen_top_fees,
    "spend_season":   gen_spend_season,
    "fee_value":      gen_fee_value,
    "country_spend":  gen_country_spend,
    "type_breakdown": gen_type_breakdown,
    "club_spend":     gen_club_spend,
    "col_dist":       gen_col_dist,
    "summary_table":  gen_summary_table,
    "num_scatter":    gen_num_scatter,
    "generic_lead":   gen_generic_lead,
}

# ─────────────────────────────────────────────────────────────
# STEP 3 — AI ANALYSIS VIA CLAUDE
# ─────────────────────────────────────────────────────────────
def build_ai_prompt(df, data_type):
    num_df = df.select_dtypes(include="number")
    stats  = num_df.describe().round(2).to_string() if not num_df.empty else "No numeric columns"
    sample = df.head(5).to_string(max_cols=12)
    text_cols = df.select_dtypes(include="object").columns.tolist()[:6]
    text_summary = ""
    for col in text_cols:
        vc = df[col].value_counts().head(5)
        text_summary += f"\n{col}: {vc.to_dict()}"

    return f"""You are an expert football/soccer analyst. A user has uploaded a dataset and you need to provide clear, insightful analysis.

DATA TYPE DETECTED: {DATA_TYPES.get(data_type,'General Football Data')}
ROWS: {len(df):,} | COLUMNS: {len(df.columns)}
COLUMN NAMES: {', '.join(df.columns.tolist())}

NUMERIC STATISTICS:
{stats}

CATEGORICAL DISTRIBUTIONS:
{text_summary}

SAMPLE DATA (first 5 rows):
{sample}

Please provide analysis in the following JSON format (return ONLY valid JSON, no markdown):
{{
  "data_quality": "2-3 sentences about data completeness, size, and any notable issues",
  "key_insights": [
    "Insight 1: specific factual finding with numbers",
    "Insight 2: specific factual finding with numbers",
    "Insight 3: specific factual finding with numbers",
    "Insight 4: specific factual finding with numbers"
  ],
  "standout_finding": "The single most interesting or surprising thing in this data",
  "coach_recommendation": "One specific tactical or training recommendation for the head coach based on this data",
  "director_recommendation": "One specific recruitment or strategic recommendation for the sporting director",
  "what_to_watch": "What metric or trend should stakeholders monitor going forward"
}}"""

def get_ai_analysis(df, data_type, api_key):
    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = build_ai_prompt(df, data_type)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role":"user","content": prompt}]
        )
        raw = msg.content[0].text.strip()
        raw = raw.replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"error": f"Could not parse AI response: {e}"}
    except Exception as e:
        return {"error": str(e)}

def render_ai_insights(analysis):
    if "error" in analysis:
        st.error(f"AI analysis error: {analysis['error']}")
        return

    st.markdown(dedent_html(f"""
    <div style="background:#111827;border:1px solid #1f2d45;border-radius:12px;padding:1.2rem;margin-bottom:1rem;">
      <div style="font-size:.7rem;color:#6B7280;letter-spacing:2px;text-transform:uppercase;margin-bottom:.5rem;">📋 DATA QUALITY</div>
      <div style="font-size:.9rem;color:#d1d5db;line-height:1.6;">{analysis.get("data_quality","—")}</div>
    </div>"""), unsafe_allow_html=True)

    st.markdown('<div style="font-family:\'Inter\',sans-serif;font-size:.7rem;color:#6B7280;letter-spacing:2px;text-transform:uppercase;margin-bottom:.6rem;">🔍 KEY INSIGHTS</div>', unsafe_allow_html=True)
    for i, insight in enumerate(analysis.get("key_insights", []), 1):
        st.markdown(dedent_html(f"""
        <div style="background:#111827;border-left:3px solid {[GREEN,BLUE,AMBER,RED][i%4]};
                    border-radius:0 8px 8px 0;padding:.7rem 1rem;margin-bottom:.5rem;
                    font-size:.88rem;color:#d1d5db;line-height:1.5;">
          <span style="color:{[GREEN,BLUE,AMBER,RED][i%4]};font-weight:600;">{i}.</span> {insight}
        </div>"""), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(dedent_html(f"""
        <div style="background:#1a2235;border:1px solid #2d4d6a;border-radius:10px;padding:1rem;height:100%;">
          <div style="font-size:.7rem;color:#7dd3fc;letter-spacing:2px;font-weight:600;">⚽ FOR THE HEAD COACH</div>
          <div style="font-size:.88rem;color:#d1d5db;margin-top:.5rem;line-height:1.6;">{analysis.get("coach_recommendation","—")}</div>
        </div>"""), unsafe_allow_html=True)
    with c2:
        st.markdown(dedent_html(f"""
        <div style="background:#2d1a3a;border:1px solid #4a2d6a;border-radius:10px;padding:1rem;height:100%;">
          <div style="font-size:.7rem;color:#c4b5fd;letter-spacing:2px;font-weight:600;">🏟️ FOR THE SPORTING DIRECTOR</div>
          <div style="font-size:.88rem;color:#d1d5db;margin-top:.5rem;line-height:1.6;">{analysis.get("director_recommendation","—")}</div>
        </div>"""), unsafe_allow_html=True)

    st.markdown(dedent_html(f"""
    <div style="background:#2d200a;border:1px solid #6a4d17;border-radius:10px;padding:1rem;margin-top:.8rem;">
      <div style="font-size:.7rem;color:#fcd34d;letter-spacing:2px;font-weight:600;">⭐ STANDOUT FINDING</div>
      <div style="font-size:.95rem;color:#fde68a;margin-top:.4rem;line-height:1.6;">{analysis.get("standout_finding","—")}</div>
    </div>
    <div style="background:#111827;border:1px solid #1f2d45;border-radius:8px;padding:.8rem 1rem;margin-top:.6rem;">
      <div style="font-size:.7rem;color:#6B7280;letter-spacing:2px;">📡 WHAT TO MONITOR</div>
      <div style="font-size:.85rem;color:#9CA3AF;margin-top:.3rem;">{analysis.get("what_to_watch","—")}</div>
    </div>"""), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MAIN PAGE RENDER FUNCTION — call this from app.py
# ─────────────────────────────────────────────────────────────
def render_smart_upload_page():
    st.markdown(dedent_html("""
    <style>
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
    .upload-hero{font-family:'Outfit',sans-serif;font-size:2.2rem;color:#00C97B;letter-spacing:3px;}
    .upload-sub{font-size:.82rem;color:#6B7280;letter-spacing:2px;text-transform:uppercase;}
    .type-badge{display:inline-block;padding:4px 14px;border-radius:20px;font-size:.78rem;
                font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:.8rem;}
    .vis-card{background:#111827;border:1px solid #1f2d45;border-radius:8px;padding:.6rem .8rem;
              font-size:.82rem;color:#9CA3AF;cursor:pointer;}
    .sec-hdr{font-family:'Outfit',sans-serif;font-size:1.1rem;color:#e8eaf0;
             letter-spacing:3px;border-left:3px solid #00C97B;padding-left:10px;margin:1rem 0 .6rem;}
    </style>
    """), unsafe_allow_html=True)

    st.markdown('<div class="upload-hero">📤 INSIGHT ENGINE</div>', unsafe_allow_html=True)
    st.markdown('<div class="upload-sub">Upload any football data · Auto-detect type · Choose visuals · Get AI insights</div>', unsafe_allow_html=True)
    st.markdown("---")

    # ── API Key (sidebar) ──────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("**🤖 AI Analysis**")
        api_key = st.text_input("Anthropic API Key", type="password",
                                placeholder="sk-ant-...",
                                help="Get your free key at console.anthropic.com")
        if api_key:
            st.success("✅ API key set")
        else:
            st.caption("Add key above to enable AI insights")

    # ── Upload Zone ────────────────────────────────────────────
    col_up, col_tmpl = st.columns([3,1])
    with col_up:
        uploaded = st.file_uploader(
            "Drop your football data file here",
            type=["csv","xlsx","xls"],
            help="Supports: match events, player stats, FIFA attributes, match results, transfers"
        )
    with col_tmpl:
        st.markdown("<br>", unsafe_allow_html=True)
        tmpl_df = pd.DataFrame([
            {"player":"K. Mbappé","team":"France","type":"Shot","minute":23,"x":108,"y":38,"outcome":"Goal","xg":0.45},
            {"player":"K. Mbappé","team":"France","type":"Pass","minute":15,"x":60,"y":40,"end_x":90,"end_y":35,"outcome":"success","xg":None},
            {"player":"A. Griezmann","team":"France","type":"Shot","minute":67,"x":105,"y":40,"outcome":"Saved","xg":0.18},
            {"player":"H. Kane","team":"England","type":"Shot","minute":88,"x":110,"y":39,"outcome":"Goal","xg":0.55},
        ])
        csv_bytes = tmpl_df.to_csv(index=False).encode()
        st.download_button("⬇️ Sample Template", csv_bytes, "football_data_template.csv", "text/csv", use_container_width=True)

    if not uploaded:
        # Show guide
        st.markdown('<div class="sec-hdr">WHAT DATA CAN I UPLOAD?</div>', unsafe_allow_html=True)
        types = [
            ("⚽", "Match Event Data", "Shots, passes, tackles with x/y coordinates and outcomes", "StatsBomb, Wyscout exports, custom tracking"),
            ("📊", "Player Performance", "Goals, assists, minutes per season or match", "FBref exports, club databases"),
            ("🎮", "Player Attributes", "FIFA-style ratings, finishing, dribbling, pace", "FIFA datasets, EA Sports data"),
            ("🏟️", "Match Results",    "Home/away teams, scores, match dates", "League results CSVs, transfermarkt"),
            ("💰", "Transfer Data",    "Transfer fees, clubs, players, seasons", "Transfermarkt exports"),
        ]
        cols = st.columns(len(types))
        for col, (icon, title, desc, source) in zip(cols, types):
            col.markdown(f"""
            <div style="background:#111827;border:1px solid #1f2d45;border-radius:10px;padding:1rem;text-align:center;">
              <div style="font-size:1.8rem;margin-bottom:.4rem;">{icon}</div>
              <div style="font-weight:700;font-size:.88rem;color:#e8eaf0;margin-bottom:.3rem;">{title}</div>
              <div style="font-size:.78rem;color:#6B7280;margin-bottom:.3rem;">{desc}</div>
              <div style="font-size:.72rem;color:#374151;font-style:italic;">{source}</div>
            </div>""", unsafe_allow_html=True)
        return

    # ── Read file ──────────────────────────────────────────────
    try:
        if uploaded.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded)
        else:
            df_raw = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read file: {e}"); return

    df = normalise_cols(df_raw.copy())

    # ── Auto-detect ────────────────────────────────────────────
    dtype = detect_type(df)
    dtype_label = DATA_TYPES.get(dtype,"📋 General Data")
    badge_colors = {"events":("#1a3d2a","#6ee7b7"), "performance":("#0f2d3a","#7dd3fc"),
                    "attributes":("#2d1f0a","#fcd34d"), "matches":("#2d0f1a","#fca5a5"),
                    "transfers":("#1a0f2d","#c4b5fd"), "generic":("#111827","#9CA3AF")}
    bg, fg = badge_colors.get(dtype, ("#111827","#9CA3AF"))

    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.markdown(f'<span class="type-badge" style="background:{bg};color:{fg};border:1px solid {fg}44;">{dtype_label}</span>', unsafe_allow_html=True)
    col_info2.metric("Rows", f"{len(df):,}")
    col_info3.metric("Columns", str(len(df.columns)))

    # ── Data preview ───────────────────────────────────────────
    with st.expander("👁️ Preview data", expanded=False):
        st.dataframe(df_raw.head(10), use_container_width=True)
        st.caption(f"Columns detected: {', '.join(df.columns.tolist())}")

    team_col   = find_col(df, ["team","club","team_name","squad"])
    player_col = find_col(df, ["player","player_name","name"])

    st.markdown("---")

    # ── Visual selector ────────────────────────────────────────
    st.markdown('<div class="sec-hdr">CHOOSE YOUR VISUALS</div>', unsafe_allow_html=True)
    available = VISUAL_MENU.get(dtype, VISUAL_MENU["generic"])

    st.markdown("**Select which visuals to generate:**")
    cols = st.columns(3)
    selected_visuals = []
    for i, (label, vid) in enumerate(available):
        with cols[i % 3]:
            if st.checkbox(label, key=f"vis_{vid}", value=(i < 3)):
                selected_visuals.append((label, vid))

    st.markdown("---")

    # ── Generate button ────────────────────────────────────────
    run_ai = bool(api_key)
    btn_label = "🚀 Generate Visuals + AI Analysis" if run_ai else "🚀 Generate Visuals"

    # Use a session-state flag instead of `if st.button(...)` directly, so the generated
    # visuals (and the filter controls below them) persist across reruns triggered by
    # interacting with the filter — a plain `if st.button(...)` block only evaluates True
    # on the single rerun where the click happened, so any widget inside it that triggers
    # its own rerun (like a multiselect) would cause the whole visuals section to vanish.
    gen_key = f"su_generated_{uploaded.name}_{dtype}"
    if st.button(btn_label, type="primary", use_container_width=True):
        if not selected_visuals:
            st.warning("Please select at least one visual above."); st.stop()
        st.session_state[gen_key] = True
        st.session_state[f"{gen_key}_visuals"] = selected_visuals

    if st.session_state.get(gen_key):
        active_visuals = st.session_state.get(f"{gen_key}_visuals", selected_visuals)

        # ── Team / Player filter — applied AFTER generation, to the visuals themselves ──
        df_for_visuals = df
        if team_col or player_col:
            st.markdown("---")
            st.markdown('<div class="sec-hdr">🔎 FILTER VISUALS</div>', unsafe_allow_html=True)
            st.caption("Narrow the visuals above down to specific teams or players without regenerating.")
            fcol1, fcol2 = st.columns(2)

            team_sel, player_sel_filter = [], []
            with fcol1:
                if team_col:
                    team_opts = sorted(df[team_col].dropna().astype(str).unique().tolist())
                    team_sel = st.multiselect("Team(s)", team_opts, default=[], key="su_team_filter",
                                              placeholder="All teams")
            with fcol2:
                if player_col:
                    player_pool = df
                    if team_col and team_sel:
                        player_pool = df[df[team_col].astype(str).isin(team_sel)]
                    player_opts = sorted(player_pool[player_col].dropna().astype(str).unique().tolist())
                    player_sel_filter = st.multiselect("Player(s)", player_opts, default=[], key="su_player_filter",
                                                       placeholder="All players")

            df_for_visuals = df.copy()
            if team_col and team_sel:
                df_for_visuals = df_for_visuals[df_for_visuals[team_col].astype(str).isin(team_sel)]
            if player_col and player_sel_filter:
                df_for_visuals = df_for_visuals[df_for_visuals[player_col].astype(str).isin(player_sel_filter)]

            if team_sel or player_sel_filter:
                st.caption(f"Showing {len(df_for_visuals):,} of {len(df):,} rows after filtering.")

        # ── Render visuals (using the filtered data) ────────────
        st.markdown("---")
        st.markdown('<div class="sec-hdr">GENERATED VISUALS</div>', unsafe_allow_html=True)

        if df_for_visuals.empty:
            st.warning("No rows match the current Team/Player filter. Adjust the filter above.")
        else:
            # Group into pairs for 2-column layout
            i = 0
            while i < len(active_visuals):
                label1, vid1 = active_visuals[i]
                if i+1 < len(active_visuals):
                    label2, vid2 = active_visuals[i+1]
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f'<div style="font-weight:600;color:#e8eaf0;margin-bottom:.3rem;">{label1}</div>', unsafe_allow_html=True)
                        with st.spinner(f"Generating {label1}..."):
                            try: VISUAL_FN[vid1](df_for_visuals)
                            except Exception as e: st.error(f"Error: {e}")
                    with c2:
                        st.markdown(f'<div style="font-weight:600;color:#e8eaf0;margin-bottom:.3rem;">{label2}</div>', unsafe_allow_html=True)
                        with st.spinner(f"Generating {label2}..."):
                            try: VISUAL_FN[vid2](df_for_visuals)
                            except Exception as e: st.error(f"Error: {e}")
                    i += 2
                else:
                    st.markdown(f'<div style="font-weight:600;color:#e8eaf0;margin-bottom:.3rem;">{label1}</div>', unsafe_allow_html=True)
                    with st.spinner(f"Generating {label1}..."):
                        try: VISUAL_FN[vid1](df_for_visuals)
                        except Exception as e: st.error(f"Error: {e}")
                    i += 1

        # ── AI Analysis ────────────────────────────────────────
        if run_ai:
            st.markdown("---")
            st.markdown('<div class="sec-hdr">🤖 AI-POWERED INSIGHTS</div>', unsafe_allow_html=True)
            with st.spinner("Claude is analysing your data..."):
                analysis = get_ai_analysis(df_for_visuals, dtype, api_key)
            render_ai_insights(analysis)
        else:
            st.markdown("---")
            st.info("💡 Add your Anthropic API key in the sidebar to unlock AI-powered plain-English insights for this data.")

        # ── Download processed data ────────────────────────────
        st.markdown("---")
        csv_out = df.to_csv(index=False).encode()
        st.download_button("⬇️ Download processed data as CSV",
                           csv_out, f"processed_{uploaded.name.replace('.xlsx','.csv')}",
                           "text/csv", use_container_width=False)


st.set_page_config(page_title="Scout IQ", page_icon="📤", layout="wide", initial_sidebar_state="expanded")
st.markdown(MAIN_CSS, unsafe_allow_html=True)
st.sidebar.markdown(SIDEBAR_BRAND, unsafe_allow_html=True)
render_smart_upload_page()
