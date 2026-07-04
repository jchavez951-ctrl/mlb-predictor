import streamlit as st
import requests
import random
import pandas as pd

st.set_page_config(page_title="Live MLB Analytics Platform", page_icon="⚾", layout="wide")

# ----------------------------------------------------
# FRANCHISE BRAND DESIGN SYSTEM (Dynamic CSS Theme)
# ----------------------------------------------------
TEAM_COLORS = {
    "New York Mets": {"primary": "#002D72", "secondary": "#FF5910"},
    "Los Angeles Angels": {"primary": "#BA0021", "secondary": "#003263"},
    "New York Yankees": {"primary": "#0C2340", "secondary": "#C4CED4"},
    "Boston Red Sox": {"primary": "#BD3039", "secondary": "#0C2340"},
    "Los Angeles Dodgers": {"primary": "#005A9C", "secondary": "#A5ACAF"},
    "Chicago Cubs": {"primary": "#0E3386", "secondary": "#CC3433"},
    "San Francisco Giants": {"primary": "#FD5A1E", "secondary": "#27251F"},
    "Colorado Rockies": {"primary": "#333366", "secondary": "#C4CED4"},
    "Houston Astros": {"primary": "#EB6E1F", "secondary": "#002D62"},
    "Atlanta Braves": {"primary": "#CE1141", "secondary": "#13274F"},
    "Philadelphia Phillies": {"primary": "#E81828", "secondary": "#293A80"},
    "San Diego Padres": {"primary": "#2F241D", "secondary": "#FFC425"}
}

# ----------------------------------------------------
# STADIUM STATCAST DICTIONARY
# ----------------------------------------------------
BALLPARK_MODIFIERS = {
    "Colorado Rockies": {"run_mult": 1.15, "hr_mult": 1.20, "desc": "Coors Field - High altitude hitters paradise"},
    "Cincinnati Reds": {"run_mult": 1.05, "hr_mult": 1.18, "desc": "Great American Ball Park - Tiny dimensions favor power"},
    "Boston Red Sox": {"run_mult": 1.08, "hr_mult": 1.02, "desc": "Fenway Park - Green Monster inflates extra-base hits"},
    "San Francisco Giants": {"run_mult": 0.92, "hr_mult": 0.82, "desc": "Oracle Park - Heavy marine layer deadens flyballs"},
    "Seattle Mariners": {"run_mult": 0.91, "hr_mult": 0.88, "desc": "T-Mobile Park - Pitcher favored marine atmosphere"},
    "San Diego Padres": {"run_mult": 0.93, "hr_mult": 0.85, "desc": "Petco Park - Coastal deep dimensions limit scoring"}
}
DEFAULT_BALLPARK = {"run_mult": 1.00, "hr_mult": 1.00, "desc": "Standard neutral environment settings applied"}

# ----------------------------------------------------
# MLB API DATA FETCH FUNCTIONS
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

@st.cache_data(ttl=1800)
def get_todays_schedule():
    """Fetches real-world games scheduled for today's calendar date via MLB API"""
    try:
        url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
        res = requests.get(url).json()
        games_list = []
        for date_obj in res.get("dates", []):
            for game in date_obj.get("games", []):
                games_list.append({
                    "away": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                    "home": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                    "status": game.get("status", {}).get("detailedState", "Scheduled")
                })
        return games_list
    except:
        return []

@st.cache_data(ttl=3600)
def get_detailed_roster_stats(team_id, stat_group="hitting"):
    players_list = []
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=Active&hydrate=person(stats(group=[{stat_group}],type=season,season=2026))"
        res = requests.get(url).json()
        
        for member in res.get('roster', []):
            person = member.get('person', {})
            name = person.get('fullName', 'Unknown Player')
            position = member.get('position', {}).get('abbreviation', 'N/A')
            throws = person.get('pitchHand', {}).get('code', 'R')
            bats = person.get('batSide', {}).get('code', 'R')
            
            stats_group = person.get('stats', [{}])[0].get('splits', [{}])
            if stats_group and 'stat' in stats_group[0]:
                stat = stats_group[0]['stat']
                
                if stat_group == "hitting":
                    players_list.append({
                        "Player": name, "Pos": position, "Bats": bats,
                        "AVG": float(stat.get("avg", ".000")), "OPS": float(stat.get("ops", ".000")),
                        "H": int(stat.get("hits", 0)), "HR": int(stat.get("homeRuns", 0)),
                        "RBI": int(stat.get("rbi", 0)), "BB": int(stat.get("baseOnBalls", 0)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "AB": int(stat.get("atBats", 1))
                    })
                elif stat_group == "pitching":
                    players_list.append({
                        "Player": name, "Pos": position, "Throws": throws,
                        "ERA": float(stat.get("era", 4.50)), "WHIP": float(stat.get("whip", 1.30)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "IP": stat.get("inningsPitched", "0.0")
                    })
    except: pass
    if not players_list: return pd.DataFrame()
    df = pd.DataFrame(players_list)
    return df.sort_values(by="OPS" if stat_group == "hitting" else "SO (K)", ascending=False)

@st.cache_data(ttl=3600)
def get_team_season_stats(team_id):
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=season&group=hitting&season=2026"
        res = requests.get(url).json()
        splits = res.get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
        return {"avg": float(splits.get("avg", ".250")), "ops": float(splits.get("ops", ".720"))}
    except:
        return {"avg": 0.250, "ops": 0.720}

# ----------------------------------------------------
# MATCHUP INPUT SETUP (SIDEBAR)
# ----------------------------------------------------
st.sidebar.header("Matchup Setup")
away_team = st.sidebar.selectbox("Away Team (Visitor)", team_names, index=team_names.index("New York Mets") if "New York Mets" in team_names else 0)
home_team = st.sidebar.selectbox("Home Team (Host)", team_names, index=team_names.index("Los Angeles Angels") if "Los Angeles Angels" in team_names else 0)

# Inject CSS Colors dynamically matching the Home Team choice
theme = TEAM_COLORS.get(home_team, {"primary": "#1E1E1E", "secondary": "#777777"})
st.markdown(f"""
    <style>
        .stButton>button {{ background-color: {theme['primary']} !important; color: white !important; border-radius: 6px; font-weight: bold; border: 2px solid {theme['secondary']}; }}
        h1, h2, h3, h4 {{ color: {theme['primary']}; }}
        .css-1kyx60a {{ background-color: {theme['primary']}; }}
    </style>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
series_length = st.sidebar.selectbox("Choose Simulation Mode", [1, 3, 5, 7], format_func=lambda x: "Single Game" if x == 1 else f"Best of {x} Series")

away_id = team_dict.get(away_team)
home_id = team_dict.get(home_team)

# Fetch Rosters and Pitchers
away_hitter_raw = get_detailed_roster_stats(away_id, "hitting") if away_id else pd.DataFrame()
home_hitter_raw = get_detailed_roster_stats(home_id, "hitting") if home_id else pd.DataFrame()
away_pitcher_df = get_detailed_roster_stats(away_id, "pitching") if away_id else pd.DataFrame()
home_pitcher_df = get_detailed_roster_stats(home_id, "pitching") if home_id else pd.DataFrame()

# ----------------------------------------------------
# INTERACTIVE LINEUP & PITCHER SELECTOR CARDS
# ----------------------------------------------------
st.subheader("📋 Team Lineup Card Management")
l_col1, l_col2 = st.columns(2)

with l_col1:
    st.markdown(f"#### {away_team} Lineup Strategy")
    away_p_names = list(away_pitcher_df["Player"]) if not away_pitcher_df.empty else ["Unknown Pitcher"]
    away_starter_sel = st.selectbox("Select Starting Pitcher", away_p_names, key="away_sp")
    
    away_h_names = list(away_hitter_raw["Player"]) if not away_hitter_raw.empty else []
    away_lineup = st.multiselect("Set 9-Man Batting Order Lineup", away_h_names, default=away_h_names[:9] if len(away_h_names)>=9 else away_h_names)

with l_col2:
    st.markdown(f"#### {home_team} Lineup Strategy")
    home_p_names = list(home_pitcher_df["Player"]) if not home_pitcher_df.empty else ["Unknown Pitcher"]
    home_starter_sel = st.selectbox("Select Starting Pitcher", home_p_names, key="home_sp")
    
    home_h_names = list(home_hitter_raw["Player"]) if not home_hitter_raw.empty else []
    home_lineup = st.multiselect("Set 9-Man Batting Order Lineup", home_h_names, default=home_h_names[:9] if len(home_h_names)>=9 else home_h_names)

# Filter dataframes by selections
away_selected_hitters = away_hitter_raw[away_hitter_raw["Player"].isin(away_lineup)] if away_lineup else away_hitter_raw.head(9)
home_selected_hitters = home_hitter_raw[home_hitter_raw["Player"].isin(home_lineup)] if home_lineup else home_hitter_raw.head(9)

away_sp_row = away_pitcher_df[away_pitcher_df["Player"] == away_starter_sel]
home_sp_row = home
