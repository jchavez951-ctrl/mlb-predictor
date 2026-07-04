import streamlit as st
import requests
import random
import pandas as pd

st.set_page_config(page_title="Live MLB Advanced Predictor", page_icon="⚾", layout="wide")
st.title("⚾ Live MLB Ultimate Matchup, Pitching & Ballpark Engine")
st.write("Streaming team rosters, dynamic pitcher ERA matchweights, and Statcast stadium environmental factors.")

# ----------------------------------------------------
# STATIC LOOKUP: Statcast Stadium Factors Dictionary
# ----------------------------------------------------
BALLPARK_MODIFIERS = {
    "Colorado Rockies": {"run_mult": 1.15, "hr_mult": 1.20, "desc": "Coors Field - High altitude extreme hitters paradise"},
    "Cincinnati Reds": {"run_mult": 1.05, "hr_mult": 1.18, "desc": "Great American Ball Park - Tiny dimensions favor power hitters"},
    "Boston Red Sox": {"run_mult": 1.08, "hr_mult": 1.02, "desc": "Fenway Park - Green Monster inflates doubles and runs"},
    "San Francisco Giants": {"run_mult": 0.92, "hr_mult": 0.82, "desc": "Oracle Park - Heavy marine layer deadens long-balls"},
    "Seattle Mariners": {"run_mult": 0.91, "hr_mult": 0.88, "desc": "T-Mobile Park - Heavy pitcher favor atmospheric pressure"},
    "San Diego Padres": {"run_mult": 0.93, "hr_mult": 0.85, "desc": "Petco Park - Coastal deep dimensions heavily limit scoring"}
}
DEFAULT_BALLPARK = {"run_mult": 1.00, "hr_mult": 1.00, "desc": "Standard neutral environment settings applied"}

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
# ADVANCED DATA LOOKUPS: Roster & Pitching Matchups
# ----------------------------------------------------
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
            
            stats_group = person.get('stats', [{}])[0].get('splits', [{}])
            if stats_group and 'stat' in stats_group[0]:
                stat = stats_group[0]['stat']
                
                if stat_group == "hitting":
                    players_list.append({
                        "Player": name, "Pos": position,
                        "AVG": float(stat.get("avg", ".000")), "OPS": float(stat.get("ops", ".000")),
                        "H": int(stat.get("hits", 0)), "HR": int(stat.get("homeRuns", 0)),
                        "RBI": int(stat.get("rbi", 0)), "BB": int(stat.get("baseOnBalls", 0)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "SB": int(stat.get("stolenBases", 0)),
                        "AB": int(stat.get("atBats", 1))
                    })
                elif stat_group == "pitching":
                    players_list.append({
                        "Player": name, "Pos": position,
                        "ERA": float(stat.get("era", 4.50)), "WHIP": float(stat.get("whip", 1.30)),
                        "W": int(stat.get("wins", 0)), "L": int(stat.get("losses", 0)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "BB": int(stat.get("baseOnBalls", 0)),
                        "SV": int(stat.get("saves", 0)), "IP": stat.get("inningsPitched", "0.0")
                    })
    except:
        pass
    if not players_list: return pd.DataFrame()
    df = pd.DataFrame(players_list)
    return df.sort_values(by="OPS" if stat_group == "hitting" else "SO (K)", ascending=False)

@st.cache_data(ttl=3600)
def get_team_season_stats(team_id):
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=season&group=hitting&season=2026"
        res = requests.get(url).json()
        splits = res.get('stats', [{}])[0].get('splits', [{}])[0].get('stat', {})
        return {"avg": float(splits.get("avg", ".250")), "ops": float(splits.get("ops", ".720")), "hr": int(splits.get("homeRuns", 0))}
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

# Fetch Rosters and Pitchers
away_hitter_df = get_detailed_roster_stats(away_id, "hitting") if away_id else pd.DataFrame()
home_hitter_df = get_detailed_roster_stats(home_id, "hitting") if home_id else pd.DataFrame()
away_pitcher_df = get_detailed_roster_stats(away_id, "pitching") if away_id else pd.DataFrame()
home_pitcher_df = get_detailed_roster_stats(home_id, "pitching") if home_id else pd.DataFrame()

# Select top starting pitcher by strikeouts/innings density as default ace matchup
away_starter_name = away_pitcher_df.iloc[0]["Player"] if not away_pitcher_df.empty else "Unknown Ace"
away_starter_era = away_pitcher_df.iloc[0]["ERA"] if not away_pitcher_df.empty else 4.00
home_starter_name = home_pitcher_df.iloc[0]["Player"] if not home_pitcher_df.empty else "Unknown Ace"
home_starter_era = home_pitcher_df.iloc[0]["ERA"] if not home_pitcher_df.empty else 4.00

# Set Up Environment Weights
park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)

# Calculate Base Modifiers (Weigh team offensive baseline against starting pitcher's defensive ERA strength)
away_stat_modifier = ((get_team_season_stats(away_id)["ops"] - 0.700) * 50) + (4.50 - home_starter_era) * 3
home_stat_modifier = ((get_team_season_stats(home_id)["ops"] - 0.700) * 50) + (4.50 - away_starter_era) * 3 + 2.0

st.sidebar.markdown("---")
st.sidebar.header("Live Tactical Modifiers")
st.sidebar.caption("Derived from Team Offense, SP Season ERA & Venue Proximity metrics.")
st.sidebar.text(f"{away_team} Match Modifier: {away_stat_modifier:+.2f}")
st.sidebar.text(f"{home_team} Match Modifier: {home_stat_modifier:+.2f}")

# ----------------------------------------------------
# LIVE STANDINGS & PROBABILITY CALCULATION
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def get_all_standings_data():
    url = "https://statsapi.mlb.com/api/v1/standings?id=regularSeason&leagueId=103,104&season=2026"
    records_mapped = {}
    try:
        res = requests.get(url).json()
        for record_group in res.get('records', []):
            for team_record in record_group.get('teamRecords', []):
                records_mapped[team_record['team']['id']] = {
                    "pct": float(team_record.get('leagueRecord', {}).get('pct', '0.500')),
                    "division": record_group.get('division', {}).get('name', 'Unknown Division'),
                    "name": team_record['team']['name']
                }
    except: pass
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
# DYNAMIC SIMULATION LOGIC WITH PARK FACTORS
# ----------------------------------------------------
def simulate_game_with_park_factors(away_df, home_df, park):
    """Simulates performance while magnifying output via home stadium multipliers."""
    hr_hitters = []
    # Loop away team hitting array
    if not away_df.empty:
        for _, player in away_df.head(9).iterrows():
            for _ in range(random.choice([4, 5])):
                if random.uniform(0, 1) <= (player["AVG"] * park["run_mult"]):
                    hr_chance = min(0.22, (player["HR"] / max(1, player["AB"])) * park["hr_mult"])
                    if random.uniform(0, 1) <= hr_chance:
                        hr_hitters.append(f"🚀 **{player['Player']}** ({away_team})")
    # Loop home team hitting array
    if not home_df.empty:
        for _, player in home_df.head(9).iterrows():
            for _ in range(random.choice([4, 5])):
                if random.uniform(0, 1) <= (player["AVG"] * park["run_mult"]):
                    hr_chance = min(0.22, (player["HR"] / max(1, player["AB"])) * park["hr_mult"])
                    if random.uniform(0, 1) <= hr_chance:
                        hr_hitters.append(f"🚀 **{player['Player']}** ({home_team})")
    return hr_hitters

# ----------------------------------------------------
# INTERFACE DISPLAY LAYOUT
# ----------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Live Data Analysis Breakdown")
    st.metric(label=f"{away_team} Base Strength Index", value=f"{away_strength:.1f}", delta=f"Base Pct: {away_base_pct:.3f}")
    st.metric(label=f"{home_team} Base Strength Index", value=f"{home_strength:.1f}", delta=f"Base Pct: {home_base_pct:.3f}")
    
    st.markdown("### 🏟️ Active Pitching Matchup & Venue Impact")
    st.info(f"📍 **Stadium Profile:** {park_data['desc']}")
    st.write(f"💨 **{away_team} Starter:** {away_starter_name} (Season ERA: `{away_starter_era:.2f}`)")
    st.write(f"🏠 **{home_team} Starter:** {home_starter_name} (Season ERA: `{home_starter_era:.2f}`)")

    st.markdown("### Calculated Live Win Expectancy")
    st.write(f"**{away_team}:** {away_prob:.1f}%")
    st.progress(int(away_prob))
    st.write(f"**{home_team}:** {home_prob:.1f}%")
    st.progress(int(home_prob))

with col2:
    st.subheader("🎲 Real-Time Simulator Engine")
    
    if st.button("Simulate Matchup Outcome"):
        # Apply ballpark adjustments to random score ranges
        base_low = int(3 * park_data["run_mult"])
        base_high = int(8 * park_data["run_mult"])
        
        if series_length == 1:
            roll = random.uniform(0, 100)
            winner = home_team if roll <= home_prob else away_team
            win_runs = random.randint(max(1, base_low), max(4, base_high))
            lose_runs = random.randint(0, max(0, win_runs - 1))
            if win_runs == lose_runs: win_runs += 1
                
            st.balloons()
            st.markdown("### 🏆 Simulated Boxscore Winner")
            if winner == home_team:
                st.success(f"**{home_team} take the victory at home!**")
                st.subheader(f"Final Score: {home_team} **{win_runs}** - {lose_runs} {away_team}")
            else:
                st.info(f"**{away_team} secure the away upset!**")
                st.subheader(f"Final Score: {away_team} **{win_runs}** - {lose_runs} {home_team}")
                
            hrs_logged = simulate_game_with_park_factors(away_hitter_df, home_hitter_df, park_data)
            st.markdown("#### 💥 Simulated Home Run Highlights")
            if hrs_logged:
                for log in hrs_logged: st.write(log)
            else:
                st.write("Pitcher's duel! No home runs simulated under these environmental factors.")
        else:
            away_wins, home_wins = 0, 0
            needed_to_win = (series_length // 2) + 1
            game_history = []
            all_series_hrs = []
            
            while away_wins < needed_to_win and home_wins < needed_to_win:
                game_num = away_wins + home_wins + 1
                winner_name = home_team if random.uniform(0, 100) <= home_prob else away_team
                if winner_name == home_team: home_wins += 1
                else: away_wins += 1
                game_history.append(f"Game {game_num}: Winner is {winner_name} (Series: {away_team} {away_wins} - {home_wins} {home_team})")
                
                game_hrs = simulate_game_with_park_factors(away_hitter_df, home_hitter_df, park_data)
                for h in game_hrs: all_series_hrs.append(f"Game {game_num}: {h}")
            
            st.balloons()
            st.markdown("### 🏆 Series Championship Report")
            if home_wins == needed_to_win: st.success(f"**{home_team} wins the series {home_wins} to {away_wins}!**")
            else: st.info(f"**{away_team} wins the series {away_wins} to {home_wins}!**")
            
            for log in game_history: st.write(f"⚾ {log}")
            st.markdown("#### 💥 Series Home Run Logs")
            if all_series_hrs:
                for entry in all_series_hrs[:10]: st.write(entry)
            else: st.write("No home runs were logged across this series infrastructure.")

# ----------------------------------------------------
# LIVE ROSTER STAT TRACKER (WITH GROUP TOGGLE)
# ----------------------------------------------------
st.markdown("---")
st.subheader("👤 Live Active Roster Stat Analytics")
stat_view = st.radio("Select View Metric Group:", ["Hitting Performance Columns", "Pitching Performance Columns"], horizontal=True)

group_key = "hitting" if "Hitting" in stat_view else "pitching"
away_player_df = get_detailed_roster_stats(away_id, group_key) if away_id else pd.DataFrame()
home_player_df = get_detailed_roster_stats(home_id, group_key) if home_id else pd.DataFrame()

p_col1, p_col2 = st.columns(2)
with p_col1:
    st.markdown(f"#### {away_team} Roster Leaderboard")
    if not away_player_df.empty: st.dataframe(away_player_df.set_index("Player"), use_container_width=True)
with p_col2:
    st.markdown(f"#### {home_team} Roster Leaderboard")
    if not home_player_df.empty: st.dataframe(home_player_df.set_index("Player"), use_container_width=True)

# ----------------------------------------------------
# GRAPH VISUALIZATION SECTION
# ----------------------------------------------------
st.markdown("---")
st.subheader("📈 Divisional Context Chart Tracker")
away_div = all_records.get(away_id, {}).get("division")
home_div = all_records.get(home_id, {}).get("division")

chart_data = []
for t_data in all_records.values():
    if t_data["division"] in [away_div, home_div]:
        chart_data.append({"Team": t_data["name"], "Win Pct": t_data["pct"]})

if chart_data:
    df = pd.DataFrame(chart_data)
    chart_ready_df = df.pivot_table(index="Team", values="Win Pct")
    st.bar_chart(chart_ready_df)
