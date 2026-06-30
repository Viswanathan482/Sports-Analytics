"""
SoccerLens — Local Data Preparation Script
Run this ONCE on your local machine before deploying.
This script processes the raw Transfermarkt data into the
smaller processed files used by the dashboard.

Usage:
  1. Place raw Transfermarkt CSV files in data/raw/
  2. Run: python scripts/prepare_data.py
  3. Processed files appear in data/processed/
"""
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

ROOT      = Path(__file__).parent.parent
RAW       = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(exist_ok=True)

print("SoccerLens — Data Preparation")
print("=" * 50)

# ── 1. FIFA PLAYERS ─────────────────────────────────────────
print("[1/6] Processing FIFA players...")
try:
    fifa = pd.read_csv(RAW / "fifa_players.csv")
    fifa.columns = fifa.columns.str.strip()

    def pos_group(p):
        p = str(p).split(",")[0].upper()
        if p in ["ST","CF","LW","RW","SS"]: return "Attacker"
        if p in ["CAM","LM","RM","CM","CDM"]: return "Midfielder"
        if p in ["CB","LB","RB","LWB","RWB"]: return "Defender"
        if p == "GK": return "Goalkeeper"
        return "Other"

    fifa["position_group"] = fifa["positions"].apply(pos_group)
    fifa["age_2026"]       = fifa["age"] + 7
    fifa["pace_score"]     = (fifa.get("acceleration",50) + fifa.get("sprint_speed",50)) / 2
    fifa["shooting_score"] = (fifa.get("finishing",50)*0.4 + fifa.get("positioning",50)*0.3 +
                              fifa.get("shot_power",50)*0.2 + fifa.get("long_shots",50)*0.1)
    fifa["passing_score"]  = (fifa.get("short_passing",50)*0.4 + fifa.get("long_passing",50)*0.3 +
                              fifa.get("vision",50)*0.2 + fifa.get("crossing",50)*0.1)
    fifa = fifa.dropna(subset=["name","overall_rating"])
    fifa = fifa.sort_values("overall_rating",ascending=False).drop_duplicates(subset="full_name")
    fifa.to_csv(PROCESSED / "clean_fifa_players.csv", index=False)
    print(f"  clean_fifa_players.csv: {len(fifa):,} players")
except FileNotFoundError:
    print("  SKIP: fifa_players.csv not found in data/raw/")

# ── 2. PLAYER LOOKUP ─────────────────────────────────────────
print("[2/6] Building player lookup...")
try:
    profiles = pd.read_csv(RAW / "player_profiles.csv",
        usecols=['player_id','player_name','player_image_url','current_club_name',
                 'citizenship','main_position','date_of_birth','height','foot',
                 'on_loan_from_club_name','contract_expires'])
    profiles['clean_name'] = profiles['player_name'].str.replace(r'\s*\(\d+\)$','',regex=True).str.strip()
    EXCLUDE = ['Retired','Without Club','Unknown','---','Career break','']
    profiles = profiles[~profiles['current_club_name'].isin(EXCLUDE)].copy()
    profiles['on_loan'] = profiles['on_loan_from_club_name'].notna() & (profiles['on_loan_from_club_name'] != '')
    profiles[['player_id','clean_name','player_image_url','current_club_name',
              'citizenship','main_position','date_of_birth','height','foot',
              'on_loan','on_loan_from_club_name','contract_expires']].to_csv(
        PROCESSED / "player_lookup.csv", index=False)
    print(f"  player_lookup.csv: {len(profiles):,} active players")
except FileNotFoundError:
    print("  SKIP: player_profiles.csv not found")

# ── 3. SEASON PERFORMANCES ───────────────────────────────────
print("[3/6] Aggregating season performances (recent 5 seasons)...")
try:
    perf = pd.read_csv(RAW / "player_performances.csv",
        usecols=['player_id','season_name','team_name','goals','assists',
                 'yellow_cards','second_yellow_cards','direct_red_cards',
                 'minutes_played','clean_sheets'])
    recent = ['20/21','21/22','22/23','23/24','24/25','25/26']
    perf = perf[perf['season_name'].isin(recent)]
    perf_agg = perf.groupby(['player_id','season_name']).agg(
        goals=('goals','sum'), assists=('assists','sum'),
        yellow_cards=('yellow_cards','sum'), red_cards=('direct_red_cards','sum'),
        second_yellow=('second_yellow_cards','sum'),
        minutes_played=('minutes_played','sum'), clean_sheets=('clean_sheets','sum'),
        main_team=('team_name', lambda x: x.value_counts().index[0] if len(x)>0 else 'Unknown')
    ).reset_index()
    perf_agg['g_plus_a']    = perf_agg['goals'] + perf_agg['assists']
    perf_agg['total_cards'] = perf_agg['yellow_cards'] + perf_agg['red_cards'] + perf_agg['second_yellow']
    perf_agg['goals_per90'] = (perf_agg['goals'] / perf_agg['minutes_played'].replace(0,1) * 90).round(3)
    perf_agg.to_csv(PROCESSED / "perf_by_season.csv", index=False)
    print(f"  perf_by_season.csv: {len(perf_agg):,} records")
except FileNotFoundError:
    print("  SKIP: player_performances.csv not found")

# ── 4. INJURIES ──────────────────────────────────────────────
print("[4/6] Cleaning injuries...")
try:
    inj = pd.read_csv(RAW / "player_injuries.csv")
    inj = inj[(inj['days_missed'] >= 0) & (inj['days_missed'] < 1000)]
    def inj_cat(r):
        r = str(r).lower()
        if any(k in r for k in ['cruciate','acl','knee']): return 'Cruciate/Knee'
        if any(k in r for k in ['hamstring','thigh','quad']): return 'Hamstring/Thigh'
        if any(k in r for k in ['ankle','foot','achilles']): return 'Ankle/Foot'
        if any(k in r for k in ['muscle','tear','strain']): return 'Muscle/Tear'
        if any(k in r for k in ['back','hip','groin']): return 'Back/Hip'
        if any(k in r for k in ['head','concussion']): return 'Head/Concussion'
        return 'Other'
    inj['injury_category'] = inj['injury_reason'].apply(inj_cat)
    import pandas as pd2
    inj['severity'] = pd.cut(inj['days_missed'], bins=[-1,7,21,90,365,9999],
        labels=["Minor","Moderate","Serious","Severe","Season-ending"])
    inj.to_csv(PROCESSED / "clean_injuries.csv", index=False)
    print(f"  clean_injuries.csv: {len(inj):,} records")
except FileNotFoundError:
    print("  SKIP: player_injuries.csv not found")

# ── 5. MARKET VALUES ─────────────────────────────────────────
print("[5/6] Processing market values...")
try:
    mv = pd.read_csv(RAW / "player_market_value.csv")
    mv['date']  = pd.to_datetime(mv['date_unix'], errors='coerce')
    mv['year']  = mv['date'].dt.year
    mv = mv[(mv['value'] > 100000) & (mv['year'] >= 2015)]
    prof_pos = pd.read_csv(RAW / "player_profiles.csv",
        usecols=['player_id','main_position','citizenship'])
    mv = mv.merge(prof_pos, on='player_id', how='left')
    mv_agg = mv.groupby(['player_id','main_position','citizenship','year'])['value'].max().reset_index()
    mv_agg.to_csv(PROCESSED / "market_value_trends.csv", index=False)
    print(f"  market_value_trends.csv: {len(mv_agg):,} records")
except FileNotFoundError:
    print("  SKIP: player_market_value.csv not found")

# ── 6. WC 2026 SHOTS ─────────────────────────────────────────
print("[6/6] Downloading StatsBomb WC 2022 shots...")
try:
    from statsbombpy import sb
    import warnings; warnings.filterwarnings("ignore")
    matches = sb.matches(competition_id=43, season_id=106)
    all_shots = []
    for _, m in matches.iterrows():
        try:
            ev = sb.events(match_id=int(m['match_id']))
            shots = ev[ev['type']=='Shot'].copy()
            shots['x'] = shots['location'].apply(lambda l: l[0] if isinstance(l,list) else None)
            shots['y'] = shots['location'].apply(lambda l: l[1] if isinstance(l,list) else None)
            all_shots.append(shots)
        except: pass
    wc_shots = pd.concat(all_shots, ignore_index=True)
    wc_shots = wc_shots.dropna(subset=['x','y'])
    wc_shots['dist_to_goal'] = np.sqrt((120-wc_shots['x'])**2+(40-wc_shots['y'])**2).round(2)
    wc_shots['shot_angle']   = np.degrees(np.arctan2(np.abs(wc_shots['y']-40),120-wc_shots['x'])).round(2)
    wc_shots['is_goal'] = (wc_shots['shot_outcome']=='Goal').astype(int)
    wc_shots['is_on_target'] = wc_shots['shot_outcome'].isin(['Goal','Saved']).astype(int)
    wc_shots.to_csv(PROCESSED / "clean_wc2022_shots.csv", index=False)
    print(f"  clean_wc2022_shots.csv: {len(wc_shots):,} shots")
except Exception as e:
    print(f"  StatsBomb error: {e}")

print("\n✅ Data preparation complete!")
print(f"Files in {PROCESSED}:")
for f in sorted(PROCESSED.iterdir()):
    size = f.stat().st_size // 1024
    print(f"  {f.name}: {size} KB")
