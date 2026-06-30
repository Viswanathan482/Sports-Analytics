"""
utils/worldcupapi.py
Dedicated WC 2026 API — worldcupapi.com
All endpoints extracted from the official Postman collection.

Base URL : https://api.worldcupapi.com
Auth     : query param  ?key=YOUR_KEY   (NOT a header)
Get key  : worldcupapi.com

Add to .streamlit/secrets.toml:
    WORLDCUP_API_KEY = "your_key_here"

Endpoints covered:
  /livescores                         Live match scores
  /fixtures                           All 104 fixtures
  /fixtures?group=A..L                Fixtures by group
  /fixtures?team_id=X                 Fixtures by team
  /fixtures?date=YYYY-MM-DD           Fixtures by date
  /standings?group=A..L               Group standings
  /standings?group=A&form=1           Standings with form
  /livestandings?group=A..L           Real-time live standings
  /goalscorers                        Top scorers (Golden Boot)
  /cards                              Top yellow/red card holders
  /squads?team_id=X                   Full squad list per team
  /head2head?team1_id=X&team2_id=Y    Head-to-head history
  /history?team_id=X                  Team match history
  /history?date_from=&date_to=        History by date range
  /events?match_id=X                  Match events (goals, cards)
  /lineups?match_id=X                 Match lineups
  /statistics?match_id=X             Match statistics
  /commentary?match_id=X             Live match commentary
"""
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

BASE = "https://api.worldcupapi.com"

# ── All 48 Team IDs (from official Postman collection) ─────────────────────────
TEAM_IDS = {
    "Argentina":    1443, "Australia":   1440, "Algeria":     1528,
    "Austria":      2684, "Belgium":     1453, "Bosnia":      None,
    "Brazil":       1448, "Canada":      1674, "Cabo Verde":  1608,
    "Colombia":     1457, "Croatia":      211, "Czechia":     None,
    "Curaçao":      2732, "DR Congo":    None, "Ecuador":     1847,
    "Egypt":         215, "England":     1456, "France":      1439,
    "Germany":      1449, "Ghana":        214, "Haiti":       2777,
    "Iran":         1436, "Iraq":         None, "Ivory Coast": 1628,
    "Japan":        1458, "Jordan":      1790, "Mexico":      1450,
    "Morocco":      1435, "Netherlands": 1649, "New Zealand": 5345,
    "Norway":       2677, "Panama":      1454, "Paraguay":    4040,
    "Portugal":     1437, "Qatar":       1427, "Saudi Arabia":1432,
    "Scotland":     1741, "Senegal":     1460, "South Africa":2767,
    "South Korea":  1452, "Spain":       1438, "Sweden":      None,
    "Switzerland":   208, "Tunisia":     1455, "Türkiye":     None,
    "Uruguay":      1434, "USA":         1849, "Uzbekistan":  1776,
}

# Head-to-head pairs defined in the collection
H2H_PAIRS = [
    (1439, 1456),  # France vs England
    (1440, 5345),  # Australia vs New Zealand
    (1448, 1443),  # Brazil vs Argentina
    (1450, 1849),  # Mexico vs USA
    (1452, 1458),  # South Korea vs Japan
    (1628, 1460),  # Ivory Coast vs Senegal
    ( 208,  211),  # Switzerland vs Croatia
]


def _get(endpoint: str, params: dict, api_key: str) -> dict:
    """GET request with key as query param."""
    try:
        params = {"key": api_key, **params}
        r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        return {}
    except Exception:
        return {}


# ── Live data (short cache) ───────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def fetch_livescores(api_key: str) -> list:
    """All currently live matches."""
    data = _get("livescores", {}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("matches", []))


@st.cache_data(ttl=30, show_spinner=False)
def fetch_livestandings(api_key: str, group: str) -> list:
    """Live standings for a single group (A-L). Updates in real-time."""
    data = _get("livestandings", {"group": group}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("standings", []))


# ── Fixtures ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def fetch_all_fixtures(api_key: str) -> list:
    """All 104 WC 2026 fixtures."""
    data = _get("fixtures", {}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("matches", []))


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fixtures_by_group(api_key: str, group: str) -> list:
    """Fixtures for a single group (A-L)."""
    data = _get("fixtures", {"group": group}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("matches", []))


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fixtures_by_team(api_key: str, team_id: int) -> list:
    """All fixtures for a specific team."""
    data = _get("fixtures", {"team_id": team_id}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("matches", []))


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fixtures_by_date(api_key: str, date: str) -> list:
    """Fixtures on a specific date (YYYY-MM-DD)."""
    data = _get("fixtures", {"date": date}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("matches", []))


# ── Standings ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_standings(api_key: str, group: str, with_form: bool = False) -> list:
    """Group table standings. with_form=True adds recent form."""
    params = {"group": group}
    if with_form:
        params["form"] = "1"
    data = _get("standings", params, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("standings", []))


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_standings(api_key: str) -> dict:
    """Returns dict {group_letter: [standings list]} for all 12 groups."""
    result = {}
    for g in "ABCDEFGHIJKL":
        rows = fetch_standings(api_key, g, with_form=True)
        if rows:
            result[g] = rows
    return result


# ── Player stats ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_goalscorers(api_key: str) -> list:
    """Top scorers (Golden Boot race)."""
    data = _get("goalscorers", {}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("players", []))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_cards(api_key: str) -> list:
    """Players with most yellow/red cards."""
    data = _get("cards", {}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("players", []))


# ── Team data ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def fetch_squad(api_key: str, team_id: int) -> list:
    """Full squad list for a team."""
    data = _get("squads", {"team_id": team_id}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("players", []))


@st.cache_data(ttl=600, show_spinner=False)
def fetch_history(api_key: str, team_id: int) -> list:
    """Historical match results for a team."""
    data = _get("history", {"team_id": team_id}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("matches", []))


@st.cache_data(ttl=600, show_spinner=False)
def fetch_head2head(api_key: str, team1_id: int, team2_id: int) -> list:
    """Head-to-head history between two teams."""
    data = _get("head2head", {"team1_id": team1_id, "team2_id": team2_id}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("matches", []))


# ── Match detail ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def fetch_events(api_key: str, match_id: int) -> list:
    """Goals, cards, substitutions for a match."""
    data = _get("events", {"match_id": match_id}, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("events", []))


@st.cache_data(ttl=60, show_spinner=False)
def fetch_lineups(api_key: str, match_id: int) -> dict:
    """Starting lineups and formations for a match."""
    data = _get("lineups", {"match_id": match_id}, api_key)
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=30, show_spinner=False)
def fetch_statistics(api_key: str, match_id: int) -> dict:
    """Match statistics (shots, possession, corners, etc.)."""
    data = _get("statistics", {"match_id": match_id}, api_key)
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=20, show_spinner=False)
def fetch_commentary(api_key: str, match_id: int,
                     from_min: int = None, to_min: int = None) -> list:
    """Live commentary for a match."""
    params = {"match_id": match_id}
    if from_min: params["from"] = from_min
    if to_min:   params["to"]   = to_min
    data = _get("commentary", params, api_key)
    return data if isinstance(data, list) else data.get("data", data.get("commentary", []))


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_team_id(team_name: str) -> int | None:
    """Look up team_id by name."""
    return TEAM_IDS.get(team_name)


def match_status_emoji(status: str) -> str:
    status = str(status).upper()
    if any(x in status for x in ["LIVE","1H","2H","HT","ET","PENS","IN PROGRESS"]):
        return "🔴 LIVE"
    if any(x in status for x in ["FT","FINISHED","FULL TIME","AET","PEN"]):
        return "✅ FT"
    if any(x in status for x in ["TBD","SCHED","NS","NOT STARTED"]):
        return "📅"
    return status


def safe_str(val) -> str:
    return str(val) if val is not None else "—"


def flatten_fixture(m: dict) -> dict:
    """Normalize a fixture dict regardless of API response structure."""
    # Try common field names used by worldcupapi
    home = (m.get("home_team") or m.get("team_home") or
            m.get("homeTeam") or {})
    away = (m.get("away_team") or m.get("team_away") or
            m.get("awayTeam") or {})
    if isinstance(home, str): home = {"name": home}
    if isinstance(away, str): away = {"name": away}

    home_score = (m.get("home_score") or m.get("score_home") or
                  m.get("homeScore") or m.get("goals_home"))
    away_score = (m.get("away_score") or m.get("score_away") or
                  m.get("awayScore") or m.get("goals_away"))

    return {
        "id":         m.get("id") or m.get("match_id") or m.get("fixture_id"),
        "home_name":  home.get("name","") if isinstance(home,dict) else str(home),
        "away_name":  away.get("name","") if isinstance(away,dict) else str(away),
        "home_score": home_score,
        "away_score": away_score,
        "status":     (m.get("status") or m.get("match_status") or ""),
        "date":       (m.get("date") or m.get("match_date") or
                       m.get("kickoff") or m.get("datetime") or ""),
        "venue":      (m.get("venue") or m.get("stadium") or
                       m.get("location") or ""),
        "group":      (m.get("group") or m.get("stage") or ""),
        "round":      (m.get("round") or m.get("matchday") or ""),
    }
