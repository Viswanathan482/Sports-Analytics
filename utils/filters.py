"""
Shared hierarchical filter sidebar:
Club → Country → Player Name → Season
Used identically across all pages.
"""
import streamlit as st
import pandas as pd
from utils.data_loader import load_player_lookup, load_performances

POPULAR_CLUBS = [
    "Arsenal FC","Manchester City FC","FC Barcelona","Real Madrid CF",
    "Bayern Munich","Paris Saint-Germain","Liverpool FC","Chelsea FC",
    "Manchester United","Juventus FC","Inter Milan","AC Milan",
    "Borussia Dortmund","Atletico Madrid","Tottenham Hotspur",
    "Ajax","Porto","Benfica","Napoli","AS Roma",
]

def render_sidebar_filters() -> dict:
    """
    Renders the 4-level filter sidebar and returns a dict:
    {player_row, player_id, player_perf, is_on_loan, loan_club,
     image_url, year_choice, club_choice, country_choice, player_choice}
    """
    lookup  = load_player_lookup()
    perf_df = load_performances()

    with st.sidebar:
        st.markdown(
            '<div style="font-family:\'Outfit\',sans-serif;font-size:2.2rem;'
            'color:#00C97B;letter-spacing:4px;line-height:1;">⚽ SOCCER<br>LENS</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div style="font-size:.75rem;color:#6B7280;letter-spacing:2px;'
            'text-transform:uppercase;margin-bottom:.8rem;">Sporting Director Suite</div>',
            unsafe_allow_html=True
        )
        st.markdown("---")

        # ── FILTER 1: CLUB ────────────────────────────────────
        st.markdown("**🏟️ Club**")
        all_clubs = sorted(lookup['current_club_name'].dropna().unique().tolist())
        popular_in_data = [c for c in POPULAR_CLUBS if c in all_clubs]
        other_clubs     = [c for c in all_clubs if c not in popular_in_data]
        clubs_display   = ["All Clubs"] + popular_in_data + ["──────────"] + other_clubs

        club_choice = st.selectbox(
            "Select club", clubs_display,
            help="Filter players by current club"
        )
        if club_choice in ["All Clubs", "──────────"]:
            club_filter = lookup
            club_selected = None
        else:
            club_filter   = lookup[lookup['current_club_name'] == club_choice]
            club_selected = club_choice

        # ── FILTER 2: COUNTRY ─────────────────────────────────
        st.markdown("**🌍 Nationality**")
        country_options = sorted(club_filter['citizenship'].dropna().unique().tolist())
        country_choice  = st.selectbox(
            "Select nationality", ["All Countries"] + country_options,
            help="Filter by player nationality"
        )
        country_filter = (
            club_filter[club_filter['citizenship'] == country_choice]
            if country_choice != "All Countries"
            else club_filter
        )

        # ── FILTER 3: PLAYER ──────────────────────────────────
        st.markdown("**👤 Player**")
        player_options = sorted(country_filter['clean_name'].dropna().unique().tolist())
        if not player_options:
            st.warning("No players match filters — resetting.")
            player_options = sorted(lookup['clean_name'].dropna().unique().tolist()[:200])

        player_choice = st.selectbox("Select player", player_options,
                                     help="Choose player to analyse")

        # Resolve player row
        match = country_filter[country_filter['clean_name'] == player_choice]
        if match.empty:
            match = lookup[lookup['clean_name'] == player_choice]
        player_row = match.iloc[0] if not match.empty else lookup.iloc[0]
        player_id  = int(player_row['player_id'])

        is_on_loan  = bool(player_row.get('on_loan', False))
        loan_club   = str(player_row.get('on_loan_from_club_name', ''))
        image_url   = str(player_row.get('player_image_url', ''))

        # Loan warning
        if is_on_loan and loan_club:
            st.markdown(
                f'<div class="loan-badge">📋 On loan from<br><b>{loan_club}</b></div>',
                unsafe_allow_html=True
            )

        # ── FILTER 4: SEASON ──────────────────────────────────
        player_perf = perf_df[perf_df['player_id'] == player_id].copy()
        year_choice = "All Seasons"
        if not player_perf.empty:
            st.markdown("**📅 Season**")
            seasons = sorted(player_perf['season_name'].dropna().unique().tolist(), reverse=True)
            year_choice = st.selectbox(
                "Select season", ["All Seasons"] + seasons,
                help="Filter to a specific season"
            )

        st.markdown("---")
        st.caption(
            f"**{len(lookup):,}** active players\n\n"
            f"**{lookup['current_club_name'].nunique():,}** clubs\n\n"
            f"**{lookup['citizenship'].nunique():,}** nationalities"
        )

    return dict(
        player_row    = player_row,
        player_id     = player_id,
        player_perf   = player_perf,
        is_on_loan    = is_on_loan,
        loan_club     = loan_club,
        image_url     = image_url,
        year_choice   = year_choice,
        club_choice   = club_choice,
        country_choice= country_choice,
        player_choice = player_choice,
    )
