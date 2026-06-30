"""
utils/kickoffapi.py
KickoffAPI — Live WC 2026 data fetcher
Docs   : https://docs.kickoffapi.com/
Sign up: https://kickoffapi.com/signup.html  (free, 100 req/day)

Base URL : https://api.kickoffapi.com/api/v1/
Auth     : Header  x-api-key: YOUR_KEY
WC 2026  : league=1, season=2026

Add to .streamlit/secrets.toml:
    KICKOFF_API_KEY = "your_key_here"
"""
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

BASE   = "https://api.kickoffapi.com/api/v1"
LEAGUE = 1       # FIFA World Cup
SEASON = 2026


# ── Core request ──────────────────────────────────────────────────────────────
def _get(endpoint: str, params: dict, api_key: str) -> dict:
    try:
        r = requests.get(
            f"{BASE}/{endpoint}",
            params=params,
            headers={"x-api-key": api_key},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
        return {"error": r.status_code, "message": r.text}
    except Exception as e:
        return {"error": str(e)}


def _response(data: dict) -> list:
    """Extract the response list, handling KickoffAPI envelope."""
    if isinstance(data, list):
        return data
    return data.get("response", [])


# ── Live & fixtures ───────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def fetch_live(api_key: str) -> list:
    """All currently in-play WC 2026 matches."""
    return _response(_get("fixtures", {"live": "all", "league": LEAGUE, "season": SEASON}, api_key))


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fixtures_all(api_key: str) -> list:
    """All 104 WC 2026 fixtures (past + upcoming)."""
    return _response(_get("fixtures", {"league": LEAGUE, "season": SEASON}, api_key))


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fixtures_date(api_key: str, date: str) -> list:
    """Fixtures on a specific date (YYYY-MM-DD)."""
    return _response(_get("fixtures", {"league": LEAGUE, "season": SEASON, "date": date}, api_key))


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fixtures_team(api_key: str, team_id: int) -> list:
    """All fixtures for a specific team."""
    return _response(_get("fixtures", {"league": LEAGUE, "season": SEASON, "team": team_id}, api_key))


@st.cache_data(ttl=120, show_spinner=False)
def fetch_upcoming(api_key: str) -> list:
    """Fixtures not yet started."""
    return _response(_get("fixtures", {"league": LEAGUE, "season": SEASON, "status": "NS"}, api_key))


# ── Standings ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_standings(api_key: str) -> list:
    """
    Group standings for all 12 groups.
    Returns list of groups; each group is a list of team dicts.
    """
    data = _get("standings", {"league": LEAGUE, "season": SEASON}, api_key)
    try:
        return data["response"][0]["league"]["standings"]
    except (KeyError, IndexError, TypeError):
        return []


# ── Top scorers / assists ─────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def fetch_topscorers(api_key: str) -> list:
    return _response(_get("topscorers", {"league": LEAGUE, "season": SEASON}, api_key))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_topassists(api_key: str) -> list:
    return _response(_get("topassists", {"league": LEAGUE, "season": SEASON}, api_key))


# ── Match detail ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def fetch_events(api_key: str, fixture_id: int) -> list:
    """Goals, cards, subs for a match."""
    return _response(_get("fixtures/events", {"fixture": fixture_id}, api_key))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_lineups(api_key: str, fixture_id: int) -> list:
    """Starting XI and bench for both teams."""
    return _response(_get("fixtures/lineups", {"fixture": fixture_id}, api_key))


@st.cache_data(ttl=30, show_spinner=False)
def fetch_fixture_stats(api_key: str, fixture_id: int) -> list:
    """Match statistics (shots, possession, corners ...)."""
    return _response(_get("fixtures/statistics", {"fixture": fixture_id}, api_key))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_player_stats(api_key: str, fixture_id: int) -> list:
    """Per-player stats for a match."""
    return _response(_get("fixtures/players", {"fixture": fixture_id}, api_key))


# ── H2H, predictions, injuries ────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def fetch_h2h(api_key: str, team1_id: int, team2_id: int) -> list:
    """Head-to-head history. Format: 'team1-team2'."""
    return _response(_get("headtohead", {"h2h": f"{team1_id}-{team2_id}"}, api_key))


@st.cache_data(ttl=120, show_spinner=False)
def fetch_predictions(api_key: str, fixture_id: int) -> dict:
    """Pre-match prediction for a fixture."""
    items = _response(_get("predictions", {"fixture": fixture_id}, api_key))
    return items[0] if items else {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_injuries(api_key: str) -> list:
    return _response(_get("injuries", {"league": LEAGUE, "season": SEASON}, api_key))


# ── Squads ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def fetch_squad(api_key: str, team_id: int) -> list:
    items = _response(_get("squads", {"team": team_id}, api_key))
    if items:
        return items[0].get("players", [])
    return []


# ── Teams list ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_teams(api_key: str) -> list:
    return _response(_get("teams", {"league": LEAGUE, "season": SEASON}, api_key))


# ── Quota check ───────────────────────────────────────────────────────────────
def fetch_quota(api_key: str) -> dict:
    try:
        r = requests.get(f"{BASE}/status",
                         headers={"x-api-key": api_key}, timeout=8)
        headers = r.headers
        return {
            "remaining": headers.get("X-RateLimit-Remaining", "?"),
            "limit":     headers.get("X-RateLimit-Limit", "100"),
        }
    except Exception:
        return {"remaining": "?", "limit": "100"}


# ── Parsers ───────────────────────────────────────────────────────────────────
def parse_fixture(m: dict) -> dict:
    """Normalise a fixture dict from KickoffAPI response."""
    # KickoffAPI uses two slightly different formats depending on endpoint
    fix   = m.get("fixture") or {}
    teams = m.get("teams") or {}
    goals = m.get("goals") or {}
    home  = teams.get("home") or {}
    away  = teams.get("away") or {}
    stat  = fix.get("status") or {}

    # Fallback to flat fields (older response shape)
    home_name  = home.get("name")  or m.get("homeTeam", {}).get("name", "Home")
    away_name  = away.get("name")  or m.get("awayTeam", {}).get("name", "Away")
    home_logo  = home.get("logo")  or m.get("homeTeam", {}).get("logo", "")
    away_logo  = away.get("logo")  or m.get("awayTeam", {}).get("logo", "")
    home_goals = goals.get("home") if goals.get("home") is not None else m.get("homeTeam", {}).get("goals")
    away_goals = goals.get("away") if goals.get("away") is not None else m.get("awayTeam", {}).get("goals")

    status_short = stat.get("short") or m.get("statusShort", "NS")
    elapsed      = stat.get("elapsed") or ""

    league = m.get("league") or {}

    return {
        "id":          fix.get("id") or m.get("id"),
        "date":        (fix.get("date") or m.get("date") or "")[:16].replace("T", " "),
        "home_name":   home_name,
        "away_name":   away_name,
        "home_logo":   home_logo,
        "away_logo":   away_logo,
        "home_goals":  home_goals,
        "away_goals":  away_goals,
        "status":      status_short,
        "elapsed":     elapsed,
        "venue":       (fix.get("venue") or {}).get("name", ""),
        "round":       league.get("round", ""),
        "group":       league.get("round", ""),
    }


def parse_standings(groups: list) -> dict:
    """
    Input : raw standings list from API (list of groups)
    Output: {group_name: pd.DataFrame}
    """
    result = {}
    for group in groups:
        rows = []
        for t in group:
            all_ = t.get("all", {})
            rows.append({
                "Pos":  t.get("rank", 0),
                "Team": t.get("team", {}).get("name", ""),
                "Logo": t.get("team", {}).get("logo", ""),
                "P":    all_.get("played", 0),
                "W":    all_.get("win", 0),
                "D":    all_.get("draw", 0),
                "L":    all_.get("lose", 0),
                "GF":   (all_.get("goals") or {}).get("for", 0),
                "GA":   (all_.get("goals") or {}).get("against", 0),
                "GD":   t.get("goalsDiff", 0),
                "Pts":  t.get("points", 0),
                "Form": t.get("form") or "",
                "Group":t.get("group", ""),
            })
        if rows:
            grp_name = rows[0]["Group"] or f"Group {len(result)+1}"
            result[grp_name] = pd.DataFrame(rows)
    return result


def status_badge(status: str, elapsed) -> tuple[str, str]:
    """Returns (label, colour)."""
    s = str(status).upper()
    if s in ("1H", "2H", "HT", "ET", "P", "BT", "LIVE"):
        return f"● LIVE {elapsed}'" if elapsed else "● LIVE", "#EF4444"
    if s in ("FT", "AET", "PEN", "AWD", "WO"):
        return "✅ FT", "#00C97B"
    if s in ("NS", "TBD", "SCHED"):
        return "📅 Upcoming", "#6B7280"
    return status, "#6B7280"
