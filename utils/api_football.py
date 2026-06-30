"""
utils/api_football.py
Live WC 2026 data from API-Football (api-sports.io)
league=1  season=2026  →  free plan, 100 req/day

Get your FREE key at: https://dashboard.api-football.com/register
Add it to .streamlit/secrets.toml:
    API_FOOTBALL_KEY = "your_key_here"
"""
import requests
import streamlit as st
from datetime import datetime, timezone
import pandas as pd

BASE = "https://v3.football.api-sports.io"
LEAGUE = 1
SEASON = 2026


def _headers(api_key: str) -> dict:
    return {"x-apisports-key": api_key}


def _get(endpoint: str, params: dict, api_key: str) -> dict:
    """Single GET call — returns response list or empty list on error."""
    try:
        r = requests.get(
            f"{BASE}/{endpoint}",
            params=params,
            headers=_headers(api_key),
            timeout=10,
        )
        data = r.json()
        if data.get("errors"):
            return {}
        return data
    except Exception:
        return {}


# ── Cached fetchers (TTL tuned to avoid wasting free-plan quota) ──────────────

@st.cache_data(ttl=300, show_spinner=False)   # 5-minute cache
def fetch_standings(api_key: str) -> list:
    """Returns list of groups, each a list of team standing dicts."""
    data = _get("standings", {"league": LEAGUE, "season": SEASON}, api_key)
    try:
        return data["response"][0]["league"]["standings"]
    except (KeyError, IndexError):
        return []


@st.cache_data(ttl=60, show_spinner=False)    # 1-minute cache
def fetch_top_scorers(api_key: str) -> list:
    data = _get("players/topscorers",
                {"league": LEAGUE, "season": SEASON}, api_key)
    return data.get("response", [])


@st.cache_data(ttl=60, show_spinner=False)
def fetch_top_yellow(api_key: str) -> list:
    data = _get("players/topyellowcards",
                {"league": LEAGUE, "season": SEASON}, api_key)
    return data.get("response", [])


@st.cache_data(ttl=60, show_spinner=False)
def fetch_top_red(api_key: str) -> list:
    data = _get("players/topredcards",
                {"league": LEAGUE, "season": SEASON}, api_key)
    return data.get("response", [])


@st.cache_data(ttl=30, show_spinner=False)    # 30-second cache for live
def fetch_live_matches(api_key: str) -> list:
    data = _get("fixtures",
                {"live": "all", "league": LEAGUE, "season": SEASON}, api_key)
    return data.get("response", [])


@st.cache_data(ttl=120, show_spinner=False)   # 2-minute cache
def fetch_fixtures(api_key: str, round_name: str = None) -> list:
    params = {"league": LEAGUE, "season": SEASON}
    if round_name:
        params["round"] = round_name
    data = _get("fixtures", params, api_key)
    return data.get("response", [])


@st.cache_data(ttl=300, show_spinner=False)
def fetch_rounds(api_key: str) -> list:
    data = _get("fixtures/rounds",
                {"league": LEAGUE, "season": SEASON}, api_key)
    return data.get("response", [])


@st.cache_data(ttl=300, show_spinner=False)
def fetch_current_round(api_key: str) -> str:
    data = _get("fixtures/rounds",
                {"league": LEAGUE, "season": SEASON, "current": "true"}, api_key)
    rounds = data.get("response", [])
    return rounds[0] if rounds else "Group Stage - 1"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_teams(api_key: str) -> list:
    data = _get("teams", {"league": LEAGUE, "season": SEASON}, api_key)
    return data.get("response", [])


@st.cache_data(ttl=300, show_spinner=False)
def fetch_injuries(api_key: str) -> list:
    data = _get("injuries", {"league": LEAGUE, "season": SEASON}, api_key)
    return data.get("response", [])


@st.cache_data(ttl=120, show_spinner=False)
def fetch_prediction(fixture_id: int, api_key: str) -> dict:
    data = _get("predictions", {"fixture": fixture_id}, api_key)
    resp = data.get("response", [])
    return resp[0] if resp else {}


@st.cache_data(ttl=60, show_spinner=False)
def fetch_fixture_detail(fixture_id: int, api_key: str) -> dict:
    data = _get("fixtures", {"id": fixture_id}, api_key)
    resp = data.get("response", [])
    return resp[0] if resp else {}


# ── Helper: check requests remaining ─────────────────────────────────────────
def get_requests_remaining(api_key: str) -> dict:
    """Returns quota info from API response headers."""
    try:
        r = requests.get(
            f"{BASE}/fixtures/rounds",
            params={"league": LEAGUE, "season": SEASON},
            headers=_headers(api_key),
            timeout=8,
        )
        return {
            "remaining": r.headers.get("x-ratelimit-requests-remaining", "?"),
            "limit":     r.headers.get("x-ratelimit-requests-limit", "100"),
        }
    except Exception:
        return {"remaining": "?", "limit": "100"}


# ── Data parsers / helpers ─────────────────────────────────────────────────────

def parse_standings_df(groups: list) -> dict[str, pd.DataFrame]:
    """Returns dict of {group_name: DataFrame}."""
    result = {}
    for grp in groups:
        rows = []
        for t in grp:
            rows.append({
                "Pos":    t["rank"],
                "Team":   t["team"]["name"],
                "Logo":   t["team"]["logo"],
                "P":      t["all"]["played"],
                "W":      t["all"]["win"],
                "D":      t["all"]["draw"],
                "L":      t["all"]["lose"],
                "GF":     t["all"]["goals"]["for"],
                "GA":     t["all"]["goals"]["against"],
                "GD":     t["goalsDiff"],
                "Pts":    t["points"],
                "Form":   t.get("form") or "—",
                "Group":  t.get("group", ""),
            })
        df = pd.DataFrame(rows)
        grp_name = rows[0]["Group"] if rows else f"Group {len(result)+1}"
        result[grp_name] = df
    return result


def parse_scorers_df(scorers: list) -> pd.DataFrame:
    rows = []
    for i, s in enumerate(scorers, 1):
        p = s.get("player", {})
        st_= s.get("statistics", [{}])[0]
        g  = st_.get("goals", {})
        rows.append({
            "Rank":       i,
            "Player":     p.get("name", "Unknown"),
            "Photo":      p.get("photo", ""),
            "Age":        p.get("age", ""),
            "Nationality":p.get("nationality", ""),
            "Team":       st_.get("team", {}).get("name", ""),
            "Team Logo":  st_.get("team", {}).get("logo", ""),
            "Goals":      g.get("total", 0) or 0,
            "Assists":    g.get("assists", 0) or 0,
            "Penalties":  g.get("penalties", 0) or 0,
            "Shots":      st_.get("shots", {}).get("on", 0) or 0,
            "G+A":        (g.get("total") or 0) + (g.get("assists") or 0),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def parse_cards_df(players: list, card_type: str = "yellow") -> pd.DataFrame:
    rows = []
    for i, s in enumerate(players, 1):
        p  = s.get("player", {})
        st_= s.get("statistics", [{}])[0]
        c  = st_.get("cards", {})
        rows.append({
            "Rank":    i,
            "Player":  p.get("name", "Unknown"),
            "Photo":   p.get("photo", ""),
            "Nation":  p.get("nationality", ""),
            "Team":    st_.get("team", {}).get("name", ""),
            "Yellow":  c.get("yellow", 0) or 0,
            "Red":     c.get("red", 0) or 0,
            "Yellow+Red": (c.get("yellow") or 0) + (c.get("red") or 0),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def fixture_status_label(status_short: str, elapsed: int | None) -> str:
    labels = {
        "TBD": "🕐 TBD",   "NS":  "📅 Not Started",
        "1H":  f"⚽ LIVE {elapsed}'", "HT": "🔁 Half Time",
        "2H":  f"⚽ LIVE {elapsed}'", "ET": f"⏱️ ET {elapsed}'",
        "P":   "🥅 Penalties", "FT": "✅ Full Time",
        "AET": "✅ After ET", "PEN": "✅ Penalties",
        "BT":  "⏸ Break",    "SUSP":"⚠️ Suspended",
        "INT": "⏸ Interrupted", "PST": "📌 Postponed",
        "CANC":"❌ Cancelled", "ABD": "🚫 Abandoned",
        "AWD": "🏆 Awarded", "WO":  "🏆 Walk Over",
        "LIVE": f"⚽ LIVE {elapsed}'",
    }
    return labels.get(status_short, status_short)
