import streamlit as st
import requests
import random
import pandas as pd

st.set_page_config(page_title="Live MLB Predictor", page_icon="⚾", layout="wide")
st.title("⚾ Live MLB Matchup & Stat Projection Engine")
st.write("Using live team standing data and historical player statistics to generate game outcomes and box score predictions.")

# ----------------------------------------------------
# DATA SOURCE: Fetch active MLB teams
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def get_mlb_teams():
    url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    response = requests.get(url).json()
    teams = {}
    for team in response.get('teams', []):
        if team.get('active', False):
            teams[team['name']] = team['id']
    return dict(sorted(teams.items()))

try:
    team_dict = get_mlb_teams()
    team_names = list(team_dict.keys())
except Exception as e:
    st.error(f"Error fetching live MLB teams: {e}")
    team_names = ["New York Mets", "Los Angeles Angels"]

# ----------------------------------------------------
# DATA FUNCTION: Fetch Individual Player Stats
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def get_individual_player_stats(team_id):
    players_list = []
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=Active&hydrate=person(stats(group=[hitting],type=season,season=2026))"
        res = requests.get(url).json()
        
        for member in res.get('roster', []):
            person = member.get('person', {})
            name = person.get('fullName', 'Unknown Player')
            position = member.get('position', {}).get('abbreviation', 'N/A')
            
            stats_group = person.get('stats', [{}])[0].get('splits', [{}])
            if stats_group and 'stat' in stats_group[0]:
                stat = stats_group[0]['stat']
                players_list.append({
                    "Player": name,
                    "Pos": position,
                    "AVG": float(stat.get("avg", ".000")),
                    "OPS": float(stat.get("ops", ".000")),
                    "HR": int(stat.get("homeRuns", 0)),
                    "RBI": int(stat.get("rbi", 0)),
                    "AB": int(stat.get("atBats", 1))
                })
    except:
        pass
    
    if not players_list:
        return pd.DataFrame(columns=["Player", "Pos", "AVG", "OPS", "HR", "RBI", "AB"])
        
    return pd.DataFrame(players_list).sort_values(by="OPS", ascending=False)

@st.cache_data(ttl=3600)
def get_team_season_stats(team_id):
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=season&group=hitting&season=2026"
        res = requests.get(url).json()
        splits = res.get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
        return {
            "avg": float(splits.get("avg", ".250")),
            "ops": float(splits.get("ops", ".720")),
            "hr": int(splits.get("homeRuns", 0))
        }
    except:
        return {"avg": 0.250, "ops": 0.720, "hr": 20}

# ----------------------------------------------------
# SIDEBAR SETUP
# ----------------------------------------------------
st.sidebar.header("Matchup Setup")
away_team = st.sidebar.selectbox("Away Team (Visitor)", team_names, index=team_names.index("New York Mets") if "New York Mets" in team_names else 0)
home_team = st.sidebar.selectbox("Home Team (Host)", team_names, index=team_names.index("Los Angeles Angels") if "Los Angeles Angels" in team_names else 0)

st.sidebar.markdown("---")
st.sidebar.header("Playoff Simulation Settings")
series_length = st.sidebar.selectbox("Choose Simulation Mode", [1, 3, 5, 7], format_func=lambda x: "Single Regular Season Game" if x == 1 else f"Best of {x} Postseason Series")

away_id = team_dict.get(away_team)
home_id = team_dict.get(home_team)

away_stats = get_team_season_stats(away_id) if away_id else {"avg": 0.250, "ops": 0.720, "hr": 20}
home_stats = get_team_season_stats(home_id) if home_id else {"avg": 0.250, "ops": 0.720, "hr": 20}

# Fetch rosters for predictions
away_player_df = get_individual_player_stats(away_id) if away_id else pd.DataFrame()
home_player_df = get_individual_player_stats(home_id) if home_id else pd.DataFrame()

# Calculate modifiers
away_stat_modifier = (away_stats["ops"] - 0.700) * 50
home_stat_modifier = ((home_stats["ops"] - 0.700) * 50) + 2.0

st.sidebar.markdown("---")
st.sidebar.header("Automated Stat Modifiers")
st.sidebar.caption("Calculated from team performance metrics.")
st.sidebar.text(f"{away_team} Modifier: {away_stat_modifier:+.2f}")
st.sidebar.text(f"{home_team} Modifier: {home_stat_modifier:+.2f}")

# ----------------------------------------------------
# LIVE STANDINGS & PROBABILITY CALCULATION LOGIC
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def get_all_standings_data():
    url = "https://statsapi.mlb.com/api/v1/standings?id=regularSeason&leagueId=103,104&season=2026"
    records_mapped = {}
    try:
        res = requests.get(url).json()
        for record_group in res.get('records', []):
            div_name = record_group.get('division', {}).get('name', 'Unknown Division')
            for team_record in record_group.get('teamRecords', []):
                t_id = team_record['team']['id']
                t_name = team_record['team']['name']
                pct = float(team_record.get('leagueRecord', {}).get('pct', '0.500'))
                records_mapped[t_id] = {"pct": pct, "division": div_name, "name": t_name}
    except:
        pass
    return records_mapped

all_records = get_all_standings_data()

away_base_pct = all_records.get(away_id, {}).get("pct", 0.500) if away_id else 0.500
home_base_pct = all_records.get(home_id, {}).get("pct", 0.500) if home_id else 0.500

away_strength = (away_base_pct * 100) + away_stat_modifier
home_strength = (home_base_pct * 100) + home_stat_modifier

total_strength = away_strength + home_strength
away_prob = (away_strength / total_strength) * 100
home_prob = (home_strength / total_strength) * 100

# ----------------------------------------------------
# INDIVIDUAL STAT PROJECTION LOGIC ENGINE
# ----------------------------------------------------
def project_player_box_score(roster_df):
    """Simulates realistic individual single-game stat projections based on their season profile"""
    projections = []
    if roster_df.empty:
        return pd.DataFrame()
        
    # Pick the top 5 hitters on the roster to make a mini-box score
    top_hitters = roster_df.head(5)
    
    for _, player in top_hitters.iterrows():
        at_bats = random.choice([4, 4, 5, 3])
        hits = 0
        hrs = 0
        rbis = 0
        
        # Simple Monte-Carlo roll per at-bat based on their real batting average
        for _ in range(at_bats):
            roll = random.uniform(0, 1)
            if roll <= player["AVG"]:
                hits += 1
                # Check if hit is a home run based on season HR density
                hr_chance = min(0.15, (player["HR"] / max(1, player["AB"])))
                if random.uniform(0, 1) <= hr_chance:
                    hrs += 1
                    rbis += random.choice([1, 2, 3])
                elif random.uniform(0, 1) < 0.3:
                    rbis += random.choice([1, 2])
                    
        projections.append({
            "Player": player["Player"],
            "Pos": player["Pos"],
            "Projected AB": at_bats,
            "Projected Hits": hits,
            "Projected HR": hrs,
            "Projected RBI": rbis
        })
    return pd.DataFrame(projections)

# ----------------------------------------------------
# INTERFACE DISPLAY LAYOUT
# ----------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Live Data Analysis Breakdown")
    st.metric(label=f"{away_team} Base Strength Index", value=f"{away_strength:.1f}", delta=f"Base Pct: {away_base_pct:.3f}")
    st.metric(label=f"{home_team} Base Strength Index", value=f"{home_strength:.1f}", delta=f"Base Pct: {home_base_pct:.3f}")
