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

# ---- FIXED LINE 179-180 TYPO ----
away_sp_row = away_pitcher_df[away_pitcher_df["Player"] == away_starter_sel]
home_sp_row = home_pitcher_df[home_pitcher_df["Player"] == home_starter_sel]

away_sp_era = float(away_sp_row.iloc[0]["ERA"]) if not away_sp_row.empty else 4.20
home_sp_era = float(home_sp_row.iloc[0]["ERA"]) if not home_sp_row.empty else 4.20
away_sp_hand = str(away_sp_row.iloc[0]["Throws"]) if not away_sp_row.empty else "R"
home_sp_hand = str(home_sp_row.iloc[0]["Throws"]) if not home_sp_row.empty else "R"

# Calculate Live Multi-Variable Weight Modifiers
park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)
away_lineup_ops = away_selected_hitters["OPS"].mean() if not away_selected_hitters.empty else 0.720
home_lineup_ops = home_selected_hitters["OPS"].mean() if not home_selected_hitters.empty else 0.720

away_modifier = ((away_lineup_ops - 0.700) * 60) + (4.30 - home_sp_era) * 4
home_modifier = ((home_lineup_ops - 0.700) * 60) + (4.30 - away_sp_era) * 4 + 2.2

# Probability Balance Logic
away_prob = max(10, min(90, 50 + away_modifier - home_modifier))
home_prob = 100 - away_prob

# ----------------------------------------------------
# VISUAL MAIN DASHBOARD LAYOUT
# ----------------------------------------------------
st.markdown("---")
m_col1, m_col2 = st.columns(2)

with m_col1:
    st.subheader("📊 Matchup Analytics & Venue Profile")
    st.info(f"🏟️ **Ballpark Context:** {park_data['desc']}")
    
    st.write(f"💨 **{away_team} SP:** {away_starter_sel} (ERA: `{away_sp_era:.2f}`, Throws: `{away_sp_hand}`)")
    st.write(f"🏠 **{home_team} SP:** {home_starter_sel} (ERA: `{home_sp_era:.2f}`, Throws: `{home_sp_hand}`)")
    
    st.markdown("### Match Win Expectancy Engine")
    st.write(f"**{away_team}:** {away_prob:.1f}%")
    st.progress(int(away_prob))
    st.write(f"**{home_team}:** {home_prob:.1f}%")
    st.progress(int(home_prob))

with m_col2:
    st.subheader("🎲 Game Simulation Engine")
    
    if st.button("Simulate Matchup Outcome"):
        def sim_hr_logs(hitters_df, opp_pitcher_hand):
            logs = []
            if hitters_df.empty: return logs
            for _, player in hitters_df.iterrows():
                for _ in range(random.choice([4, 5])):
                    plat_bonus = 1.05 if player["Bats"] != opp_pitcher_hand else 0.95
                    if random.uniform(0, 1) <= (player["AVG"] * park_data["run_mult"] * plat_bonus):
                        hr_chance = (player["HR"] / max(1, player["AB"])) * park_data["hr_mult"] * plat_bonus
                        if random.uniform(0, 1) <= min(0.25, hr_chance):
                            logs.append(player["Player"])
            return logs

        if series_length == 1:
            winner = home_team if random.uniform(0, 100) <= home_prob else away_team
            w_score = random.randint(max(1, int(3*park_data["run_mult"])), max(4, int(8*park_data["run_mult"])))
            l_score = random.randint(0, max(0, w_score - 1))
            if w_score == l_score: w_score += 1
            
            st.balloons()
            st.markdown(f"### 🏆 Result: {winner} wins!")
            if winner == home_team: st.success(f"Final: {home_team} **{w_score}** - {l_score} {away_team}")
            else: st.info(f"Final: {away_team} **{w_score}** - {l_score} {home_team}")
            
            st.markdown("#### 💥 Home Run Highlights")
            a_hrs = sim_hr_logs(away_selected_hitters, home_sp_hand)
            with_team_a = [f"🚀 **{p}** ({away_team})" for p in a_hrs]
            h_hrs = sim_hr_logs(home_selected_hitters, away_sp_hand)
            with_team_h = [f"🚀 **{p}** ({home_team})" for p in h_hrs]
            
            total_hr_list = with_team_a + with_team_h
            if total_hr_list:
                for line in total_hr_list: st.write(line)
            else: st.write("No longballs recorded in this simulation.")
        else:
            away_wins, home_wins, game_num = 0, 0, 1
            series_hrs = []
            while away_wins < (series_length//2+1) and home_wins < (series_length//2+1):
                g_win = home_team if random.uniform(0, 100) <= home_prob else away_team
                if g_win == home_team: home_wins += 1
                else: away_wins += 1
                
                a_hrs = sim_hr_logs(away_selected_hitters, home_sp_hand)
                h_hrs = sim_hr_logs(home_selected_hitters, away_sp_hand)
                for p in a_hrs: series_hrs.append(f"Game {game_num}: 🚀 **{p}** ({away_team})")
                for p in h_hrs: series_hrs.append(f"Game {game_num}: 🚀 **{p}** ({home_team})")
                game_num += 1
                
            st.balloons()
            if home_wins > away_wins: st.success(f"🏆 **{home_team} wins series {home_wins} to {away_wins}!**")
            else: st.info(f"🏆 **{away_team} wins series {away_wins} to {home_wins}!**")
            
            st.markdown("#### 💥 Series Home Run Log (Top 8 entries)")
            if series_hrs:
                for log in series_hrs[:8]: st.write(log)
            else: st.write("No longballs launched across the series stretch.")

# ----------------------------------------------------
# LIVE DAILY MLB SCHEDULE COMPONENT
# ----------------------------------------------------
st.markdown("---")
st.subheader("📅 Real-World MLB Schedule Lookup Tracker")
schedule_data = get_todays_schedule()
if schedule_data:
    sched_df = pd.DataFrame(schedule_data)
    st.dataframe(sched_df.set_index("away"), use_container_width=True)
else:
    st.write("No active games or scheduling logs currently returned from the MLB server data grids today.")

# ----------------------------------------------------
# ACTIVE TEAM ROSTER METRIC MATRIX VIEWPORTS
# ----------------------------------------------------
st.markdown("---")
st.subheader("👤 Active Selected Squad Statistics")
stat_view = st.radio("Toggle Metric Layout Grid View:", ["Hitting Performance Columns", "Pitching Performance Columns"], horizontal=True)

p_col1, p_col2 = st.columns(2)
with p_col1:
    st.markdown(f"#### {away_team} Strategy Ledger")
    if "Hitting" in stat_view: st.dataframe(away_selected_hitters.set_index("Player"), use_container_width=True)
    else: st.dataframe(away_pitcher_df.set_index("Player"), use_container_width=True)
with p_col2:
    st.markdown(f"#### {home_team} Strategy Ledger")
    if "Hitting" in stat_view: st.dataframe(home_selected_hitters.set_index("Player"), use_container_width=True)
    else: st.dataframe(home_pitcher_df.set_index("Player"), use_container_width=True)
