"""Centralised, cached data loading for all SoccerLens pages."""
from pathlib import Path
import pandas as pd
import streamlit as st
import numpy as np

DATA = Path(__file__).parent.parent / "data" / "processed"

@st.cache_data(show_spinner=False)
def load_player_lookup():
    df = pd.read_csv(DATA / "player_lookup.csv")
    df['on_loan'] = df['on_loan'].fillna(False).astype(bool)
    df['clean_name'] = df['clean_name'].fillna('Unknown')
    df['current_club_name'] = df['current_club_name'].fillna('Unknown')
    df['citizenship'] = df['citizenship'].fillna('Unknown')
    return df

@st.cache_data(show_spinner=False)
def load_performances():
    df = pd.read_csv(DATA / "perf_by_season.csv")
    df['season_year'] = df['season_name'].str[:2].apply(
        lambda x: 2000+int(x) if str(x).isdigit() else None)
    return df

@st.cache_data(show_spinner=False)
def load_market_values():
    df = pd.read_csv(DATA / "market_value_trends.csv")
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    if 'value' in df.columns:
        df['value_M'] = (pd.to_numeric(df['value'], errors='coerce') / 1e6).round(2)
    elif 'value_M' not in df.columns:
        df['value_M'] = 0
    return df

@st.cache_data(show_spinner=False)
def load_injuries():
    return pd.read_csv(DATA / "clean_injuries.csv")

@st.cache_data(show_spinner=False)
def load_fifa():
    return pd.read_csv(DATA / "clean_fifa_players.csv")

@st.cache_data(show_spinner=False)
def load_shots():
    return pd.read_csv(DATA / "clean_wc2022_shots.csv")

@st.cache_data(show_spinner=False)
def load_wc_top50():
    return pd.read_csv(DATA / "wc2026_top50_real.csv")

@st.cache_data(show_spinner=False)
def load_wc_simulation():
    return pd.read_csv(DATA / "wc2026_winner_prediction_real.csv")

@st.cache_data(show_spinner=False)
def load_wc_discipline():
    return pd.read_csv(DATA / "wc2026_discipline.csv")

@st.cache_data(show_spinner=False)
def load_wc_groups():
    return pd.read_csv(DATA / "wc2026_groups.csv")

# Convenience: get single player's data across all datasets
def get_player_data(player_id: int):
    pid = int(player_id)
    return {
        "performances": load_performances()[load_performances()['player_id'] == pid],
        "market_value": load_market_values()[load_market_values()['player_id'] == pid],
        "injuries":     load_injuries()[load_injuries()['player_id'] == pid],
    }

# ── New WC 2026 real-data loaders ────────────────────────────
@st.cache_data(show_spinner=False)
def load_wc_matches():
    return pd.read_csv(DATA / "wc2026_matches_full.csv")

@st.cache_data(show_spinner=False)
def load_wc_scorers():
    return pd.read_csv(DATA / "wc2026_real_scorers.csv")

@st.cache_data(show_spinner=False)
def load_wc_standings():
    return pd.read_csv(DATA / "wc2026_standings.csv")

@st.cache_data(show_spinner=False)
def load_wc_team_stats():
    return pd.read_csv(DATA / "wc2026_team_full_stats.csv")

@st.cache_data(show_spinner=False)
def load_wc_gk_stats():
    return pd.read_csv(DATA / "wc2026_goalkeeper_stats.csv")

@st.cache_data(show_spinner=False)
def load_wc_venue_stats():
    return pd.read_csv(DATA / "wc2026_venue_stats.csv")

@st.cache_data(show_spinner=False)
def load_wc_referee_stats():
    return pd.read_csv(DATA / "wc2026_referee_stats.csv")

@st.cache_data(show_spinner=False)
def load_wc_potm():
    return pd.read_csv(DATA / "wc2026_potm.csv")

@st.cache_data(show_spinner=False)
def load_wc_goal_timing():
    return pd.read_csv(DATA / "wc2026_goal_timing.csv")

@st.cache_data(show_spinner=False)
def load_wc_position_analysis():
    return pd.read_csv(DATA / "wc2026_position_analysis.csv")

@st.cache_data(show_spinner=False)
def load_wc_players_full():
    return pd.read_csv(DATA / "wc2026_players_full.csv")

# ── Shared full player universe (FIFA ∪ Transfermarkt-only) ──────
# Used by Transfer Hub and Executive so EVERY player in the
# Transfermarkt lookup (58k+) is searchable, not just the 17,898
# in the older FIFA attribute dataset. Players found only in the
# lookup table (e.g. very recent breakout stars) appear with their
# club/nation/photo but no FIFA attribute scores.
@st.cache_data(show_spinner=False)
def build_player_universe():
    fifa   = load_fifa()
    lookup = load_player_lookup()
    perf   = load_performances()

    POS_MAP = {"Attack": "Attacker", "Midfield": "Midfielder",
               "Defender": "Defender", "Goalkeeper": "Goalkeeper"}

    # Career goals/assists/minutes per player, joined via Transfermarkt id
    g = perf.groupby("player_id").agg(
        total_goals=("goals", "sum"),
        total_assists=("assists", "sum"),
        total_minutes=("minutes_played", "sum"),
    ).reset_index()

    name_col = "clean_name" if "clean_name" in fifa.columns else "name"
    f = fifa.copy()
    f["_mn"] = f[name_col].astype(str).str.strip().str.lower()
    f["has_fifa_data"] = True
    f["display_name"]  = f[name_col]

    lk = lookup.copy()
    lk["_mn"] = lk["clean_name"].astype(str).str.strip().str.lower()
    lk = lk.merge(g, on="player_id", how="left")
    lk[["total_goals", "total_assists", "total_minutes"]] = \
        lk[["total_goals", "total_assists", "total_minutes"]].fillna(0)

    # Attach club/nation/photo/goals to every FIFA player
    lk_dedup = lk.drop_duplicates("_mn")
    fifa_full = f.merge(
        lk_dedup[["_mn", "current_club_name", "citizenship", "player_image_url",
                  "on_loan", "total_goals", "total_assists", "total_minutes"]],
        on="_mn", how="left")
    fifa_full["club_display"]   = fifa_full["current_club_name"].fillna("Unknown Club")
    fifa_full["nation_display"] = fifa_full["nationality"].fillna(fifa_full["citizenship"])
    fifa_full["total_goals"]    = fifa_full["total_goals"].fillna(0)
    fifa_full["total_assists"]  = fifa_full["total_assists"].fillna(0)
    fifa_full["total_minutes"]  = fifa_full["total_minutes"].fillna(0)

    # Players that exist ONLY in the Transfermarkt lookup (not in FIFA)
    fifa_names = set(f["_mn"])
    extra = lk[~lk["_mn"].isin(fifa_names)].drop_duplicates("_mn").copy()
    extra["has_fifa_data"]  = False
    extra["display_name"]   = extra["clean_name"]
    extra["club_display"]   = extra["current_club_name"].fillna("Unknown Club")
    extra["nation_display"] = extra["citizenship"]
    extra["position_group"] = extra["main_position"].map(POS_MAP).fillna(extra["main_position"])
    for col in ["overall_rating", "potential", "value_euro", "wage_euro",
                "release_clause_euro", "age", "age_2026",
                "pace_score", "shooting_score", "passing_score",
                "defending_score", "physical_score", "preferred_foot"]:
        if col not in extra.columns:
            extra[col] = np.nan

    keep_cols = list(fifa_full.columns)
    for col in keep_cols:
        if col not in extra.columns:
            extra[col] = np.nan
    extra = extra[keep_cols]

    universe = pd.concat([fifa_full, extra], ignore_index=True, sort=False)
    universe["wage_euro"]  = pd.to_numeric(universe["wage_euro"], errors="coerce").fillna(0)
    universe["value_euro"] = pd.to_numeric(universe["value_euro"], errors="coerce").fillna(0)
    universe["annual_wage_M"] = (universe["wage_euro"] * 52 / 1e6).round(3)
    return universe
