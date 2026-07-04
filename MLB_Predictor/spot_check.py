import streamlit as st
import requests
import random
import time
import pandas as pd

st.set_page_config(page_title="Live MLB Analytics Platform", page_icon="⚾", layout="wide")

# ----------------------------------------------------
# STANDINGS DATA PERSISTENCE LAYER (Season Tracking)
# ----------------------------------------------------
if "standings" not in st.session_state:
    st.session_state["standings"] = {}

def record_game_result(winner, loser):
    if winner not in st.session_state["standings"]:
        st.session_state["standings"][winner] = {"W": 0, "L": 0}
    if loser not in st.session_state["standings"]:
        st.session_state["standings"][loser] = {"W": 0, "L": 0}
    st.session_state["standings"][winner]["W"] += 1
    st.session_state["standings"][loser]["L"] += 1

# ----------------------------------------------------
# RETRO HISTORICAL SQUAD ENGINE
# ----------------------------------------------------
RETRO_TEAMS = {
    "1927 New York Yankees": {
        "primary": "#0C2340", "secondary": "#C4CED4", "runs_scored": 975, "runs_allowed": 599,
        "hitting": [
            {"Player": "Earle Combs", "Pos": "CF", "Bats": "L", "AVG": 0.356, "OPS": 0.925, "HR": 6, "AB": 648},
            {"Player": "Mark Koenig", "Pos": "SS", "Bats": "B", "AVG": 0.285, "OPS": 0.701, "HR": 3, "AB": 626},
            {"Player": "Babe Ruth", "Pos": "RF", "Bats": "L", "AVG": 0.356, "OPS": 1.258, "HR": 60, "AB": 540},
            {"Player": "Lou Gehrig", "Pos": "1B", "Bats": "L", "AVG": 0.373, "OPS": 1.240, "HR": 47, "AB": 584},
            {"Player": "Bob Meusel", "Pos": "LF", "Bats": "R", "AVG": 0.337, "OPS": 0.895, "HR": 8, "AB": 513},
            {"Player": "Tony Lazzeri", "Pos": "2B", "Bats": "R", "AVG": 0.309, "OPS": 0.841, "HR": 18, "AB": 570},
            {"Player": "Joe Dugan", "Pos": "3B", "Bats": "R", "AVG": 0.269, "OPS": 0.672, "HR": 2, "AB": 387},
            {"Player": "Pat Collins", "Pos": "C", "Bats": "R", "AVG": 0.275, "OPS": 0.825, "HR": 7, "AB": 251},
            {"Player": "Ray Morehart", "Pos": "IF", "Bats": "L", "AVG": 0.256, "OPS": 0.630, "HR": 1, "AB": 195}
        ],
        "pitching": [
            {"Player": "Waite Hoyt", "Pos": "SP", "Throws": "R", "ERA": 2.63, "WHIP": 1.15, "SO (K)": 86, "IP": "256.2"},
            {"Player": "Herb Pennock", "Pos": "SP", "Throws": "L", "ERA": 3.00, "WHIP": 1.21, "SO (K)": 51, "IP": "209.2"},
            {"Player": "Urban Shocker", "Pos": "SP", "Throws": "R", "ERA": 2.84, "WHIP": 1.16, "SO (K)": 35, "IP": "200.0"},
            {"Player": "Wilcy Moore", "Pos": "RP", "Throws": "R", "ERA": 2.28, "WHIP": 1.14, "SO (K)": 75, "IP": "213.0"}
        ]
    },
    "2004 Boston Red Sox": {
        "primary": "#BD3039", "secondary": "#0C2340", "runs_scored": 949, "runs_allowed": 768,
        "hitting": [
            {"Player": "Johnny Damon", "Pos": "CF", "Bats": "L", "AVG": 0.304, "OPS": 0.877, "HR": 20, "AB": 621},
            {"Player": "Mark Bellhorn", "Pos": "2B", "Bats": "B", "AVG": 0.264, "OPS": 0.801, "HR": 17, "AB": 500},
            {"Player": "Manny Ramirez", "Pos": "LF", "Bats": "R", "AVG": 0.308, "OPS": 1.009, "HR": 43, "AB": 568},
            {"Player": "David Ortiz", "Pos": "DH", "Bats": "L", "AVG": 0.301, "OPS": 0.983, "HR": 41, "AB": 582},
            {"Player": "Kevin Millar", "Pos": "1B", "Bats": "R", "AVG": 0.297, "OPS": 0.874, "HR": 18, "AB": 508},
            {"Player": "Jason Varitek", "Pos": "C", "Bats": "B", "AVG": 0.296, "OPS": 0.890, "HR": 18, "AB": 463},
            {"Player": "Orlando Cabrera", "Pos": "SS", "Bats": "R", "AVG": 0.294, "OPS": 0.785, "HR": 6, "AB": 245},
            {"Player": "Bill Mueller", "Pos": "3B", "Bats": "B", "AVG": 0.283, "OPS": 0.795, "HR": 12, "AB": 399},
            {"Player": "Trot Nixon", "Pos": "RF", "Bats": "L", "AVG": 0.293, "OPS": 0.871, "HR": 6, "AB": 140}
        ],
        "pitching": [
            {"Player": "Curt Schilling", "Pos": "SP", "Throws": "R", "ERA": 3.26, "WHIP": 1.06, "SO (K)": 203, "IP": "226.2"},
            {"Player": "Pedro Martinez", "Pos": "SP", "Throws": "R", "ERA": 3.90, "WHIP": 1.21, "SO (K)": 227, "IP": "217.0"},
            {"Player": "Tim Wakefield", "Pos": "SP", "Throws": "R", "ERA": 4.87, "WHIP": 1.34, "SO (K)": 116, "IP": "188.1"},
            {"Player": "Keith Foulke", "Pos": "RP", "Throws": "R", "ERA": 2.17, "WHIP": 0.94, "SO (K)": 79, "IP": "83.0"}
        ]
    }
}

# Live Franchise Brand Design Options
TEAM_COLORS = {
    "New York Mets": {"primary": "#002D72", "secondary": "#FF5910", "runs_scored": 725, "runs_allowed": 710},
    "Los Angeles Angels": {"primary": "#BA0021", "secondary": "#003263", "runs_scored": 690, "runs_allowed": 760},
    "New York Yankees": {"primary": "#0C2340", "secondary": "#C4CED4", "runs_scored": 815, "runs_allowed": 705},
    "Boston Red Sox": {"primary": "#BD3039", "secondary": "#0C2340", "runs_scored": 780, "runs_allowed": 740},
    "Los Angeles Dodgers": {"primary": "#005A9C", "secondary": "#A5ACAF", "runs_scored": 840, "runs_allowed": 680},
    "Chicago Cubs": {"primary": "#0E3386", "secondary": "#CC3433", "runs_scored": 730, "runs_allowed": 720},
    "San Francisco Giants": {"primary": "#FD5A1E", "secondary": "#27251F", "runs_scored": 695, "runs_allowed": 735},
    "San Diego Padres": {"primary": "#2F241D", "secondary": "#FFC425", "runs_scored": 770, "runs_allowed": 700}
}

BALLPARK_MODIFIERS = {
    "San Diego Padres": {"run_mult": 0.93, "hr_mult": 0.85, "desc": "Petco Park - Coastal deep dimensions limit scoring"},
    "Los Angeles Dodgers": {"run_mult": 1.02, "hr_mult": 1.08, "desc": "Dodger Stadium - Neutral setup favoring power carries"},
    "1927 New York Yankees": {"run_mult": 1.05, "hr_mult": 1.02, "desc": "Yankee Stadium I - Short right-field porch limits"},
    "2004 Boston Red Sox": {"run_mult": 1.08, "hr_mult": 1.02, "desc": "Fenway Park - Green Monster wall factors"}
}
DEFAULT_BALLPARK = {"run_mult": 1.00, "hr_mult": 1.00, "desc": "Standard neutral environment environment variables active"}

# ----------------------------------------------------
# DATA SOURCE CONTEXT LOGIC
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def get_mlb_teams():
    url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    response = requests.get(url).json()
    teams = {}
    for team in response.get('teams', []):
        if team.get('active', False) and team['name'] in TEAM_COLORS:
            teams[team['name']] = team['id']
    return dict(sorted(teams.items()))

try:
    live_teams = get_mlb_teams()
except:
    live_teams = {}

# Merged Team Lists (Live API + Custom Historic Databases)
all_selectable_teams = sorted(list(live_teams.keys()) + list(RETRO_TEAMS.keys()))

@st.cache_data(ttl=3600)
def get_detailed_roster_stats(team_id, team_name, stat_group="hitting"):
    if team_name in RETRO_TEAMS:
        return pd.DataFrame(RETRO_TEAMS[team_name][stat_group])
    
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
    return pd.DataFrame(players_list)

# ----------------------------------------------------
# MATCHUP LAYOUT ARRAYS
# ----------------------------------------------------
st.sidebar.header("Matchup Setup Panel")
away_team = st.sidebar.selectbox("Away Team (Visitor)", all_selectable_teams, index=0)
home_team = st.sidebar.selectbox("Home Team (Host)", all_selectable_teams, index=min(1, len(all_selectable_teams)-1))

# CSS Injector
theme_host = RETRO_TEAMS.get(home_team, TEAM_COLORS.get(home_team, {"primary": "#1E1E1E", "secondary": "#777777"}))
st.markdown(f"<style>h1, h2, h3, h4 {{ color: {theme_host['primary']}; }} .stButton>button {{ background-color: {theme_host['primary']} !important; color: white !important; }}</style>", unsafe_allow_html=True)

# Pull Roster Layout Contexts
away_hitter_raw = get_detailed_roster_stats(live_teams.get(away_team), away_team, "hitting")
home_hitter_raw = get_detailed_roster_stats(live_teams.get(home_team), home_team, "hitting")
away_pitcher_df = get_detailed_roster_stats(live_teams.get(away_team), away_team, "pitching")
home_pitcher_df = get_detailed_roster_stats(live_teams.get(home_team), home_team, "pitching")

# ----------------------------------------------------
# LINEUP CONTROL INTERFACES
# ----------------------------------------------------
st.subheader("📋 Team Lineup Card Management")
l_col1, l_col2 = st.columns(2)

with l_col1:
    st.markdown(f"#### {away_team} Config")
    away_p_names = list(away_pitcher_df["Player"]) if not away_pitcher_df.empty else ["Unknown Starter"]
    away_starter_sel = st.selectbox("Select Starting Pitcher", away_p_names, key="a_sp")
    away_h_names = list(away_hitter_raw["Player"]) if not away_hitter_raw.empty else ["Generic Hitter"]
    away_lineup = st.multiselect("Batting Roster Lineup (9)", away_h_names, default=away_h_names[:9] if len(away_h_names) >= 9 else away_h_names)

with l_col2:
    st.markdown(f"#### {home_team} Config")
    home_p_names = list(home_pitcher_df["Player"]) if not home_pitcher_df.empty else ["Unknown Starter"]
    home_starter_sel = st.selectbox("Select Starting Pitcher", home_p_names, key="h_sp")
    home_h_names = list(home_hitter_raw["Player"]) if not home_hitter_raw.empty else ["Generic Hitter"]
    home_lineup = st.multiselect("Batting Roster Lineup (9)", home_h_names, default=home_h_names[:9] if len(home_h_names) >= 9 else home_h_names)

# Filtering Context blocks
away_selected_hitters = away_hitter_raw[away_hitter_raw["Player"].isin(away_lineup)].copy() if away_lineup else away_hitter_raw.head(9).copy()
home_selected_hitters = home_hitter_raw[home_hitter_raw["Player"].isin(home_lineup)].copy() if home_lineup else home_hitter_raw.head(9).copy()

if away_selected_hitters.empty: away_selected_hitters = pd.DataFrame([{"Player": "Player A", "AVG": 0.260, "OPS": 0.760, "HR": 10, "AB": 300, "Bats": "R"}])
if home_selected_hitters.empty: home_selected_hitters = pd.DataFrame([{"Player": "Player H", "AVG": 0.260, "OPS": 0.760, "HR": 10, "AB": 300, "Bats": "R"}])

away_sp_row = away_pitcher_df[away_pitcher_df["Player"] == away_starter_sel]
home_sp_row = home_pitcher_df[home_pitcher_df["Player"] == home_starter_sel]

away_sp_era = float(away_sp_row.iloc[0]["ERA"]) if not away_sp_row.empty else 4.20
home_sp_era = float(home_sp_row.iloc[0]["ERA"]) if not home_sp_row.empty else 4.20
away_sp_hand = str(away_sp_row.iloc[0]["Throws"]) if not away_sp_row.empty else "R"
home_sp_hand = str(home_sp_row.iloc[0]["Throws"]) if not home_sp_row.empty else "R"

park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)

# ----------------------------------------------------
# ADVANCED MATHEMATICAL MODELS (Pythagorean Formula Engine)
# ----------------------------------------------------
st.markdown("---")
m_col1, m_col2 = st.columns(2)

with m_col1:
    st.subheader("📊 Pythagorean Mathematical Baseline")
    
    # Extract historical metrics
    data_away_profile = RETRO_TEAMS.get(away_team, TEAM_COLORS.get(away_team, {"runs_scored": 720, "runs_allowed": 720}))
    data_home_profile = RETRO_TEAMS.get(home_team, TEAM_COLORS.get(home_team, {"runs_scored": 720, "runs_allowed": 720}))
    
    rs_a, ra_a = data_away_profile["runs_scored"], data_away_profile["runs_allowed"]
    rs_h, ra_h = data_home_profile["runs_scored"], data_home_profile["runs_allowed"]
    
    # Bill James Sabermetric Formula calculations
    pyth_away = (rs_a ** 1.83) / ((rs_a ** 1.83) + (ra_a ** 1.83))
    pyth_home = (rs_h ** 1.83) / ((rs_h ** 1.83) + (ra_h ** 1.83))
    
    sum_expectancy = pyth_away + pyth_home
    calc_away_pct = (pyth_away / sum_expectancy) * 100
    calc_home_pct = (pyth_home / sum_expectancy) * 100
    
    st.caption("Calculated via Exponent $\gamma = 1.83$ based on baseline historical run-differentials.")
    st.write(f"**{away_team} Baseline Odds:** {calc_away_pct:.1f}%")
    st.progress(int(calc_away_pct))
    st.write(f"**{home_team} Baseline Odds:** {calc_home_pct:.1f}%")
    st.progress(int(calc_home_pct))
    st.info(f"🏟️ **Park Modifier Matrix:** {park_data['desc']}")

with m_col2:
    st.subheader("🎲 Live Engine Playback")
    sim_button = st.button("Simulate Interactive Framework Matchup")

if sim_button:
    away_score, home_score = 0, 0
    away_lineup_index, home_lineup_index = 0, 0
    away_batters_faced, home_batters_faced = 0, 0
    
    current_away_p, current_away_era, current_away_hand = f"{away_starter_sel} (SP)", away_sp_era, away_sp_hand
    current_home_p, current_home_era, current_home_hand = f"{home_starter_sel} (SP)", home_sp_era, home_sp_hand
    
    status_box = st.status("⚾ Inning State Sync Loading...", expanded=True)
    score_board_display = st.empty()
    ticker_display = st.empty()
    play_by_play_logs = []
    
    def update_live_render(inn, top_half, runs_a, runs_h, runners):
        arrow = "🔺 Top" if top_half else "🔻 Bot"
        bases_emojis = ["⬜", "⬜", "⬜"]
        for i in range(3):
            if runners[i]: bases_emojis[i] = "🟨"
        score_board_display.markdown(f"**Inning:** {arrow} {inn} | 1st: {bases_emojis[0]} 2nd: {bases_emojis[1]} 3rd: {bases_emojis[2]} | **Score:** {away_team} `{runs_a}` - {home_team} `{runs_h}`")

    inning = 1
    while inning <= 9 or (away_score == home_score):
        # --- TOP HALF: AWAY ---
        play_by_play_logs.append(f"**Top {inning}**")
        outs, bases = 0, [None, None, None]
        
        if home_batters_faced >= 18 and "Reliever" not in current_home_p and not home_pitcher_df.empty:
            rel = home_pitcher_df.iloc[random.randint(0, min(3, len(home_pitcher_df)-1))]
            current_home_p, current_home_era, current_home_hand = f"{rel['Player']} (RP)", float(rel['ERA']), str(rel['Throws'])
            play_by_play_logs.append(f"🔄 Bullpen call: **{current_home_p}** enters mound.")

        while outs < 3:
            if inning >= 9 and home_score > away_score and outs == 0: break
            batter = away_selected_hitters.iloc[away_lineup_index % len(away_selected_hitters)]
            away_lineup_index += 1; home_batters_faced += 1
            
            p_mult = 1.05 if batter["Bats"] != current_home_hand else 0.95
            h_prob = batter["AVG"] * park_data["run_mult"] * p_mult * (current_home_era / 4.1)
            
            if random.uniform(0, 1) <= h_prob:
                hr_c = (batter["HR"] / max(1, batter["AB"])) * park_data["hr_mult"]
                h_roll = random.uniform(0, 1)
                if h_roll <= hr_c:
                    rbis = 1 + sum([1 for r in bases if r is not None])
                    away_score += rbis; bases = [None, None, None]
                    play_by_play_logs.append(f"💥 **HR!** {batter['Player']} launches a `{rbis}-run` blast!")
                elif h_roll <= hr_c + 0.18:
                    rbis = sum([1 for r in bases[1:] if r is not None])
                    bases[2] = bases[0]; bases[1] = batter["Player"]; bases[0] = None
                    away_score += rbis; play_by_play_logs.append(f"⚾ **Double!** {batter['Player']} hits the gap.")
                else:
                    rbis = 1 if bases[2] else 0
                    bases[2] = bases[1]; bases[1] = bases[0]; bases[0] = batter["Player"]
                    away_score += rbis; play_by_play_logs.append(f"🏃 **Single!** {batter['Player']} hits a base knock.")
            else:
                outs += 1
                if random.uniform(0, 1) <= 0.3: play_by_play_logs.append(f"💨 *Strikeout!* {batter['Player']} down swinging.")
                else: play_by_play_logs.append(f"🥎 *Out!* {batter['Player']} grounds out.")
            
            update_live_render(inning, True, away_score, home_score, bases)
            ticker_display.markdown("\n\n".join(play_by_play_logs[-4:]))
            time.sleep(0.15)
            
        # --- BOTTOM HALF: HOME ---
        if inning == 9 and home_score > away_score: break
        play_by_play_logs.append(f"**Bottom {inning}**")
        outs, bases = 0, [None, None, None]
        
        if away_batters_faced >= 18 and "Reliever" not in current_away_p and not away_pitcher_df.empty:
            rel = away_pitcher_df.iloc[random.randint(0, min(3, len(away_pitcher_df)-1))]
            current_away_p, current_away_era, current_away_hand = f"{rel['Player']} (RP)", float(rel['ERA']), str(rel['Throws'])
            play_by_play_logs.append(f"🔄 Bullpen call: **{current_away_p}** enters mound.")

        while outs < 3:
            if inning >= 9 and home_score > away_score: break
            batter = home_selected_hitters.iloc[home_lineup_index % len(home_selected_hitters)]
            home_lineup_index += 1; away_batters_faced += 1
            
            p_mult = 1.05 if batter["Bats"] != current_away_hand else 0.95
            h_prob = batter["AVG"] * park_data["run_mult"] * p_mult * (current_away_era / 4.1)
            
            if random.uniform(0, 1) <= h_prob:
                hr_c = (batter["HR"] / max(1, batter["AB"])) * park_data["hr_mult"]
                h_roll = random.uniform(0, 1)
                if h_roll <= hr_c:
                    rbis = 1 + sum([1 for r in bases if r is not None])
                    home_score += rbis; bases = [None, None, None]
                    play_by_play_logs.append(f"💥 **HR!** {batter['Player']} cracks a `{rbis}-run` blast!")
                elif h_roll <= hr_c + 0.18:
                    rbis = sum([1 for r in bases[1:] if r is not None])
                    bases[2] = bases[0]; bases[1] = batter["Player"]; bases[0] = None
                    home_score += rbis; play_by_play_logs.append(f"⚾ **Double!** {batter['Player']} hits the gap.")
                else:
                    rbis = 1 if bases[2] else 0
                    bases[2] = bases[1]; bases[1] = bases[0]; bases[0] = batter["Player"]
                    home_score += rbis; play_by_play_logs.append(f"🏃 **Single!** {batter['Player']} hits a base knock.")
            else:
                outs += 1
                if random.uniform(0, 1) <= 0.3: play_by_play_logs.append(f"💨 *Strikeout!* {batter['Player']} down swinging.")
                else: play_by_play_logs.append(f"🥎 *Out!* {batter['Player']} hits a fly ball out.")
                
            update_live_render(inning, False, away_score, home_score, bases)
            ticker_display.markdown("\n\n".join(play_by_play_logs[-4:]))
            time.sleep(0.15)
            
        inning += 1

    status_box.update(label="🏆 Game Concluded!", state="complete", expanded=False)
    
    # Save results directly to session state engine tracking data structures
    if home_score > away_score:
        record_game_result(home_team, away_team)
        st.success(f"🏁 **{home_team} Wins!** Final: `{home_score}` - `{away_score}`")
    else:
        record_game_result(away_team, home_team)
        st.info(f"🏁 **{away_team} Wins!** Final: `{away_score}` - `{home_score}`")

# ----------------------------------------------------
# LEAGUE STANDINGS DISPLAY CARD (Persistent Data View)
# ----------------------------------------------------
st.markdown("---")
st.subheader("🏆 Persistent Campaign Standings Leaderboard")
if st.session_state["standings"]:
    standings_list = []
    for team, stats in st.session_state["standings"].items():
        total = stats["W"] + stats["L"]
        pct = stats["W"] / total if total > 0 else 0.0
        standings_list.append({"Franchise Team Name": team, "Wins": stats["W"], "Losses": stats["L"], "Win Pct": f"{pct:.3f}"})
    
    st.dataframe(pd.DataFrame(standings_list).sort_values(by="Wins", ascending=False).set_index("Franchise Team Name"), use_container_width=True)
else:
    st.caption("No historical season matches simulated in this current framework runtime session yet.")
