import streamlit as st
import requests
import random
import time
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

# Filter rosters by user configurations
away_selected_hitters = away_hitter_raw[away_hitter_raw["Player"].isin(away_lineup)].copy() if away_lineup else away_hitter_raw.head(9).copy()
home_selected_hitters = home_hitter_raw[home_hitter_raw["Player"].isin(home_lineup)].copy() if home_lineup else home_hitter_raw.head(9).copy()

# Fallback checking if rosters are too empty
if away_selected_hitters.empty: away_selected_hitters = pd.DataFrame([{"Player": "Away Batter", "AVG": 0.250, "OPS": 0.750, "HR": 15, "AB": 400, "Bats": "R"}])
if home_selected_hitters.empty: home_selected_hitters = pd.DataFrame([{"Player": "Home Batter", "AVG": 0.250, "OPS": 0.750, "HR": 15, "AB": 400, "Bats": "R"}])

away_sp_row = away_pitcher_df[away_pitcher_df["Player"] == away_starter_sel]
home_sp_row = home_pitcher_df[home_pitcher_df["Player"] == home_starter_sel]

away_sp_era = float(away_sp_row.iloc[0]["ERA"]) if not away_sp_row.empty else 4.20
home_sp_era = float(home_sp_row.iloc[0]["ERA"]) if not home_sp_row.empty else 4.20
away_sp_hand = str(away_sp_row.iloc[0]["Throws"]) if not away_sp_row.empty else "R"
home_sp_hand = str(home_sp_row.iloc[0]["Throws"]) if not home_sp_row.empty else "R"

park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)

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

with m_col2:
    st.subheader("🎲 Play-by-Play Simulation Engine")
    sim_button = st.button("Launch Inning-by-Inning Simulation")

if sim_button:
    # Tracking logs and structures
    away_score, home_score = 0, 0
    away_lineup_index, home_lineup_index = 0, 0
    away_batters_faced, home_batters_faced = 0, 0
    
    current_away_pitcher = f"{away_starter_sel} (SP)"
    current_away_era = away_sp_era
    current_away_hand = away_sp_hand
    
    current_home_pitcher = f"{home_starter_sel} (SP)"
    current_home_era = home_sp_era
    current_home_hand = home_sp_hand

    # Clean display views
    status_box = st.status("⚾ Preparing Stadium and Field Infrastructure...", expanded=True)
    score_board_display = st.empty()
    ticker_display = st.empty()
    
    play_by_play_logs = []
    
    def render_scoreboard(inn, top_half, runs_a, runs_h, runners):
        arrow = "🔺 Top" if top_half else "🔻 Bot"
        base_emojis = ["⬜", "⬜", "⬜"]
        if runners[0]: base_emojis[0] = "🟨"
        if runners[1]: base_emojis[1] = "🟨"
        if runners[2]: base_emojis[2] = "🟨"
        bases_str = f"1st: {base_emojis[0]} | 2nd: {base_emojis[1]} | 3rd: {base_emojis[2]}"
        
        score_board_display.markdown(f"""
        ### 🏟️ LIVE SCOREBOARD
        **Inning:** {arrow} {inn} | {bases_str}
        * **{away_team}:** `{runs_a}`
        * **{home_team}:** `{runs_h}`
        ---
        """)

    inning = 1
    # Full Game Inning Engine Loop
    while inning <= 9 or (away_score == home_score):
        # ----------------------------------------------------
        # TOP HALF: AWAY TEAM BATTING
        # ----------------------------------------------------
        play_by_play_logs.append(f"### 🔺 Top of Inning {inning}")
        outs = 0
        bases = [None, None, None] # 1st, 2nd, 3rd base runner track
        
        # Bullpen hook fatigue logic
        if home_batters_faced >= 18 and "Reliever" not in current_home_pitcher and not home_pitcher_df.empty:
            reliever = home_pitcher_df.iloc[min(len(home_pitcher_df)-1, random.randint(1, 4))]
            current_home_pitcher = f"{reliever['Player']} (RP)"
            current_home_era = float(reliever['ERA'])
            current_home_hand = str(reliever['Throws'])
            play_by_play_logs.append(f"🔄 *Manager Pull:* {home_team} brings in reliever **{current_home_pitcher}** (ERA: {current_home_era:.2f})")

        while outs < 3:
            # Handle walk-offs / premature endings in extra innings
            if inning >= 9 and home_score > away_score and outs == 0:
                break # Home team holds lead in top or bottom
                
            batter = away_selected_hitters.iloc[away_lineup_index % len(away_selected_hitters)]
            away_lineup_index += 1
            home_batters_faced += 1
            
            # Platoon Splitting Calculus
            platoon_mult = 1.06 if batter["Bats"] != current_home_hand else 0.94
            hit_prob = batter["AVG"] * park_data["run_mult"] * platoon_mult * (current_home_era / 4.0)
            
            roll = random.uniform(0, 1.1)
            if roll <= hit_prob:
                # HIT! Determine what type
                hr_chance = (batter["HR"] / max(1, batter["AB"])) * park_data["hr_mult"] * platoon_mult
                hit_roll = random.uniform(0, 1)
                
                if hit_roll <= hr_chance:
                    # HOME RUN
                    rbis = 1 + sum([1 for r in bases if r is not None])
                    away_score += rbis
                    play_by_play_logs.append(f"💥 **CRACK! HOME RUN!** {batter['Player']} launches a massive longball! `{rbis}` Run(s) score!")
                    bases = [None, None, None]
                elif hit_roll <= hr_chance + 0.15:
                    # DOUBLE
                    rbis = 0
                    for b_idx in [2, 1]: # 3rd and 2nd scores
                        if bases[b_idx]: rbis += 1; bases[b_idx] = None
                    if bases[0]: bases[2] = bases[0]; bases[0] = None
                    bases[1] = batter["Player"]
                    away_score += rbis
                    play_by_play_logs.append(f"⚾ **Double!** {batter['Player']} rips an extra-base hit into the gap! {f'`{rbis}` run(s) cross plate!' if rbis > 0 else ''}")
                else:
                    # SINGLE
                    rbis = 0
                    if bases[2]: rbis += 1; bases[2] = None
                    if bases[1]: bases[2] = bases[1]; bases[1] = None
                    if bases[0]: bases[1] = bases[0]; bases[0] = None
                    bases[0] = batter["Player"]
                    away_score += rbis
                    play_by_play_logs.append(f"🏃 **Single!** {batter['Player']} lines a base hit past shortstop! {f'`{rbis}` run(s) score!' if rbis > 0 else ''}")
            else:
                # OUT
                outs += 1
                if random.uniform(0, 1) <= 0.30:
                    play_by_play_logs.append(f"💨 *Strikeout!* {batter['Player']} swings and misses at a breaking pitch. ({outs} Out)")
                else:
                    play_by_play_logs.append(f"🥎 *Flyout/Groundout!* {batter['Player']} hits a routine ball into play for an out. ({outs} Out)")
                    
            render_scoreboard(inning, True, away_score, home_score, bases)
            ticker_display.markdown("\n".join(play_by_play_logs[-6:]))
            time.sleep(0.35)

        # ----------------------------------------------------
        # BOTTOM HALF: HOME TEAM BATTING
        # ----------------------------------------------------
        # Check if game is already won in bottom of 9th
        if inning == 9 and home_score > away_score:
            break
            
        play_by_play_logs.append(f"### 🔻 Bottom of Inning {inning}")
        outs = 0
        bases = [None, None, None]
        
        if away_batters_faced >= 18 and "Reliever" not in current_away_pitcher and not away_pitcher_df.empty:
            reliever = away_pitcher_df.iloc[min(len(away_pitcher_df)-1, random.randint(1, 4))]
            current_away_pitcher = f"{reliever['Player']} (RP)"
            current_away_era = float(reliever['ERA'])
            current_away_hand = str(reliever['Throws'])
            play_by_play_logs.append(f"🔄 *Manager Pull:* {away_team} brings in reliever **{current_away_pitcher}** (ERA: {current_away_era:.2f})")

        while outs < 3:
            # Walk-off scenario check
            if inning >= 9 and home_score > away_score:
                play_by_play_logs.append(f"🎉 **WALK-OFF!** {home_team} scores the winning run in the final frames!")
                break
                
            batter = home_selected_hitters.iloc[home_lineup_index % len(home_selected_hitters)]
            home_lineup_index += 1
            away_batters_faced += 1
            
            platoon_mult = 1.06 if batter["Bats"] != current_away_hand else 0.94
            hit_prob = batter["AVG"] * park_data["run_mult"] * platoon_mult * (current_away_era / 4.0)
            
            roll = random.uniform(0, 1.1)
            if roll <= hit_prob:
                hr_chance = (batter["HR"] / max(1, batter["AB"])) * park_data["hr_mult"] * platoon_mult
                hit_roll = random.uniform(0, 1)
                
                if hit_roll <= hr_chance:
                    rbis = 1 + sum([1 for r in bases if r is not None])
                    home_score += rbis
                    play_by_play_logs.append(f"💥 **CRACK! HOME RUN!** {batter['Player']} hits a majestic shot to deep field! `{rbis}` Run(s) score!")
                    bases = [None, None, None]
                elif hit_roll <= hr_chance + 0.15:
                    rbis = 0
                    for b_idx in [2, 1]:
                        if bases[b_idx]: rbis += 1; bases[b_idx] = None
                    if bases[0]: bases[2] = bases[0]; bases[0] = None
                    bases[1] = batter["Player"]
                    home_score += rbis
                    play_by_play_logs.append(f"⚾ **Double!** {batter['Player']} drops a hit along the baseline line! {f'`{rbis}` run(s) score!' if rbis > 0 else ''}")
                else:
                    rbis = 0
                    if bases[2]: rbis += 1; bases[2] = None
                    if bases[1]: bases[2] = bases[1]; bases[1] = None
                    if bases[0]: bases[1] = bases[0]; bases[0] = None
                    bases[0] = batter["Player"]
                    home_score += rbis
                    play_by_play_logs.append(f"🏃 **Single!** {batter['Player']} sneaks an infield base hit! {f'`{rbis}` run(s) score!' if rbis > 0 else ''}")
            else:
                outs += 1
                if random.uniform(0, 1) <= 0.30:
                    play_by_play_logs.append(f"💨 *Strikeout!* {batter['Player']} strikes out swinging. ({outs} Out)")
                else:
                    play_by_play_logs.append(f"🥎 *Groundout!* {batter['Player']} hits it directly into a defensive field out. ({outs} Out)")
                    
            render_scoreboard(inning, False, away_score, home_score, bases)
            ticker_display.markdown("\n".join(play_by_play_logs[-6:]))
            time.sleep(0.35)
            
        inning += 1

    # End simulation display outputs
    status_box.update(label="🏆 Simulation Complete!", state="complete", expanded=False)
    st.balloons()
    
    st.markdown("## 🏁 Final Game Report")
    if home_score > away_score:
        st.success(f"### 🏆 {home_team} Wins! Final Score: `{home_score}` - `{away_score}`")
    else:
        st.info(f"### 🏆 {away_team} Wins! Final Score: `{away_score}` - `{home_score}`")

    with st.expander("👁️ View Full Detailed Play-By-Play Broadcast Log"):
        for track_line in play_by_play_logs:
            st.markdown(track_line)

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
    st.write("No active games returned from the MLB server data grids today.")

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
