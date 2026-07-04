import streamlit as st
import requests
import random
import pandas as pd

st.set_page_config(page_title="Live MLB Predictor", page_icon="⚾", layout="wide")
st.title("⚾ Live MLB Matchup Predictor & Divisional Analytics")
st.write("Fetching live team standings and analytics directly from the official MLB API.")

# ----------------------------------------------------
# DATA SOURCE: Fetch active MLB teams from API
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
# SIDEBAR MATCHUP SETUP
# ----------------------------------------------------
st.sidebar.header("Matchup Setup")
away_team = st.sidebar.selectbox("Away Team (Visitor)", team_names, index=team_names.index("New York Mets") if "New York Mets" in team_names else 0)
home_team = st.sidebar.selectbox("Home Team (Host)", team_names, index=team_names.index("Los Angeles Angels") if "Los Angeles Angels" in team_names else 0)

st.sidebar.markdown("---")
st.sidebar.header("Advanced Analytics Overrides")
away_modifier = st.sidebar.slider(f"{away_team} Rest/Form Modifier", -10, 10, 0)
home_modifier = st.sidebar.slider(f"{home_team} Rest/Form Modifier", -10, 10, 2)

# ----------------------------------------------------
# LIVE STATS CALCULATION LOGIC
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def get_all_standings_data():
    """Fetches win percentages and division names for all teams."""
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
away_id = team_dict.get(away_team)
home_id = team_dict.get(home_team)

away_base_pct = all_records.get(away_id, {}).get("pct", 0.500) if away_id else 0.500
home_base_pct = all_records.get(home_id, {}).get("pct", 0.500) if home_id else 0.500

away_strength = (away_base_pct * 100) + away_modifier
home_strength = (home_base_pct * 100) + home_modifier

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
    
    st.markdown("### Calculated Live Win Expectancy")
    st.write(f"**{away_team}:** {away_prob:.1f}%")
    st.progress(int(away_prob))
    
    st.write(f"**{home_team}:** {home_prob:.1f}%")
    st.progress(int(home_prob))

with col2:
    st.subheader("🎲 Real-Time Simulator Engine")
    st.write("Run a custom algorithmic scenario simulation based on the calculated live data metrics.")
    
    if st.button("Simulate Matchup Outcome"):
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

# ----------------------------------------------------
# NEW VISUALIZATION SECTION: Divisional Comparison Chart
# ----------------------------------------------------
st.markdown("---")
st.subheader("📈 Divisional Context Tracker")
st.write("See how your selected teams compare against rival win percentages inside their respective divisions.")

# Gather division peers for the chart
away_div = all_records.get(away_id, {}).get("division")
home_div = all_records.get(home_id, {}).get("division")

chart_data = []
for t_data in all_records.values():
    if t_data["division"] in [away_div, home_div]:
        chart_data.append({"Team": t_data["name"], "Win Pct": t_data["pct"], "Division": t_data["division"]})

if chart_data:
    df = pd.DataFrame(chart_data).sort_values(by="Win Pct", ascending=False)
    # Pivot for clean Streamlit rendering
    chart_df = df.set_index("Team")[["Win Pct"]]
    st.bar_chart(chart_df)
else:
    st.write("No divisional peer data found.")
