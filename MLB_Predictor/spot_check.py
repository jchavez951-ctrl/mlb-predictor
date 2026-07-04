import streamlit as st
import requests
import random
import pandas as pd

st.set_page_config(page_title="Live MLB Predictor", page_icon="⚾", layout="wide")
st.title("⚾ Live MLB Matchup & Playoff Series Predictor")
st.write("Fetching live team standings and individual player metrics directly from the official MLB API.")

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
# NEW DATA FUNCTION: Fetch Individual Player Stats
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def get_individual_player_stats(team_id):
    """Fetches full team active roster and hydrates seasonal hitting stats for each player"""
    players_list = []
    try:
        # Request roster hydrated with active seasonal hitting stats
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=Active&hydrate=person(stats(group=[hitting],type=season,season=2026))"
        res = requests.get(url).json()
        
        for member in res.get('roster', []):
            person = member.get('person', {})
            name = person.get('fullName', 'Unknown Player')
            position = member.get('position', {}).get('abbreviation', 'N/A')
            
            # Navigate nested stat splits
            stats_group = person.get('stats', [{}])[0].get('splits', [{}])
            if stats_group and 'stat' in stats_group[0]:
                stat = stats_group[0]['stat']
                players_list.append({
                    "Player": name,
                    "Pos": position,
                    "AVG": float(stat.get("avg", ".000")),
                    "OPS": float(stat.get("ops", ".000")),
                    "HR": int(stat.get("homeRuns", 0)),
                    "RBI": int(stat.get("rbi", 0))
                })
    except:
        pass
    
    # If API fails or returns blank array, fallback to dummy data container
    if not players_list:
        return pd.DataFrame(columns=["Player", "Pos", "AVG", "OPS", "HR", "RBI"])
        
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
# SIDEBAR SETUP (MATCHUP + SERIES FORMAT)
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

# Calculate automated modifiers based on live team OPS performance
away_stat_modifier = (away_stats["ops"] - 0.700) * 50
home_stat_modifier = ((home_stats["ops"] - 0.700) * 50) + 2.0  # +2 home field advantage bonus

st.sidebar.markdown("---")
st.sidebar.header("Automated Stat Modifiers")
st.sidebar.caption("Calculated dynamically from real-time team performance metrics (OPS Baseline).")
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
# INTERFACE DISPLAY LAYOUT
# ----------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Live Data Analysis Breakdown")
    st.metric(label=f"{away_team} Base Strength Index", value=f"{away_strength:.1f}", delta=f"Base Pct: {away_base_pct:.3f}")
    st.metric(label=f"{home_team} Base Strength Index", value=f"{home_strength:.1f}", delta=f"Base Pct: {home_base_pct:.3f}")
    
    st.markdown("### Team Season Stat Metrics")
    stat_df = pd.DataFrame({
        "Metric": ["Batting Avg (.AVG)", "On-Base + Slugging (.OPS)", "Total Home Runs (HR)"],
        away_team: [f"{away_stats['avg']:.3f}", f"{away_stats['ops']:.3f}", away_stats['hr']],
        home_team: [f"{home_stats['avg']:.3f}", f"{home_stats['ops']:.3f}", home_stats['hr']]
    })
    st.table(stat_df)

    st.markdown("### Calculated Live Win Expectancy")
    st.write(f"**{away_team}:** {away_prob:.1f}%")
    st.progress(int(away_prob))
    
    st.write(f"**{home_team}:** {home_prob:.1f}%")
    st.progress(int(home_prob))

with col2:
    st.subheader("🎲 Real-Time Simulator Engine")
    st.write(f"Simulating under configuration: **Best of {series_length} Series**" if series_length > 1 else "Simulating a Single Regular Season Game Matchup.")
    
    if st.button("Simulate Matchup Outcome"):
        if series_length == 1:
            roll = random.uniform(0, 100)
            winner = home_team if roll <= home_prob else away_team
            win_runs = random.randint(3, 8)
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
        else:
            away_wins = 0
            home_wins = 0
            needed_to_win = (series_length // 2) + 1
            game_history = []
            
            while away_wins < needed_to_win and home_wins < needed_to_win:
                game_num = away_wins + home_wins + 1
                roll = random.uniform(0, 100)
                
                g_winner = home_team if roll <= home_prob else away_team
                if g_winner == home_team:
                    home_wins += 1
                else:
                    away_wins += 1
                game_history.append(f"Game {game_num}: Winner is {g_winner} (Series Score: {away_team} {away_wins} - {home_wins} {home_team})")
            
            st.balloons()
            st.markdown("### 🏆 Series Championship Report")
            series_winner = home_team if home_wins == needed_to_win else away_team
            
            if series_winner == home_team:
                st.success(f"**{home_team} wins the series {home_wins} games to {away_wins}!**")
            else:
                st.info(f"**{away_team} wins the series {away_wins} games to {home_wins}!**")
                
            st.markdown("#### Game-By-Game Breakdown:")
            for log in game_history:
                st.write(f"⚾ {log}")

# ----------------------------------------------------
# NEW INDIVIDUAL PLAYER STAT MATRIX TRACKER
# ----------------------------------------------------
st.markdown("---")
st.subheader("👤 Active Rosters & Individual Player Analytics")
st.write("Reviewing live seasonal player stats derived via real-time roster serialization.")

p_col1, p_col2 = st.columns(2)

with p_col1:
    st.markdown(f"#### {away_team} Roster Leaderboard")
    away_player_df = get_individual_player_stats(away_id) if away_id else pd.DataFrame()
    if not away_player_df.empty:
        st.dataframe(away_player_df.set_index("Player"), use_container_width=True)
    else:
        st.write("No individual hitting data logged for this team roster.")

with p_col2:
    st.markdown(f"#### {home_team} Roster Leaderboard")
    home_player_df = get_individual_player_stats(home_id) if home_id else pd.DataFrame()
    if not home_player_df.empty:
        st.dataframe(home_player_df.set_index("Player"), use_container_width=True)
    else:
        st.write("No individual hitting data logged for this team roster.")

# ----------------------------------------------------
# RE-ENGINEERED GRAPH VISUALIZATION SECTION
# ----------------------------------------------------
st.markdown("---")
st.subheader("📈 Divisional Context Chart Tracker")
st.write("See how your selected teams compare against rival win percentages inside their respective divisions.")

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
else:
    st.write("Gathering divisional peer data points...")
