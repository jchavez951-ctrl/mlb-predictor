import streamlit as st
import requests
import random
import time
import pandas as pd
import numpy as np

st.set_page_config(page_title="Ultimate MLB Analytics Platform", page_icon="⚾", layout="wide")

# ----------------------------------------------------
# STATE PERSISTENCE LAYER
# ----------------------------------------------------
if "standings" not in st.session_state:
    st.session_state["standings"] = {}
if "lineups_locked" not in st.session_state:
    st.session_state["lineups_locked"] = False
if "leveraged_game_state" not in st.session_state:
    st.session_state["leveraged_game_state"] = None
if "game_active" not in st.session_state:
    st.session_state["game_active"] = False
if "away_bullpen" not in st.session_state:
    st.session_state["away_bullpen"] = []
if "home_bullpen" not in st.session_state:
    st.session_state["home_bullpen"] = []

# ----------------------------------------------------
# ADVANCED MODULE 1: HISTORICAL DATA & ROLE ASSIGNMENT
# ----------------------------------------------------
RETRO_TEAMS = {
    "1927 New York Yankees": {
        "primary": "#0C2340", "secondary": "#C4CED4", "runs_scored": 975, "runs_allowed": 599,
        "hitting": [
            {"Player": "Earle Combs", "Pos": "CF", "Bats": "L", "AVG": 0.356, "OPS": 0.925, "HR": 6, "AB": 648, "SPD": 88, "AVG_v_LHP": 0.330, "AVG_v_RHP": 0.365},
            {"Player": "Mark Koenig", "Pos": "SS", "Bats": "B", "AVG": 0.285, "OPS": 0.701, "HR": 3, "AB": 626, "SPD": 75, "AVG_v_LHP": 0.290, "AVG_v_RHP": 0.282},
            {"Player": "Babe Ruth", "Pos": "RF", "Bats": "L", "AVG": 0.356, "OPS": 1.258, "HR": 60, "AB": 540, "SPD": 65, "AVG_v_LHP": 0.315, "AVG_v_RHP": 0.372},
            {"Player": "Lou Gehrig", "Pos": "1B", "Bats": "L", "AVG": 0.373, "OPS": 1.240, "HR": 47, "AB": 584, "SPD": 60, "AVG_v_LHP": 0.340, "AVG_v_RHP": 0.385},
            {"Player": "Bob Meusel", "Pos": "LF", "Bats": "R", "AVG": 0.337, "OPS": 0.895, "HR": 8, "AB": 513, "SPD": 78, "AVG_v_LHP": 0.350, "AVG_v_RHP": 0.331},
            {"Player": "Tony Lazzeri", "Pos": "2B", "Bats": "R", "AVG": 0.309, "OPS": 0.841, "HR": 18, "AB": 570, "SPD": 72, "AVG_v_LHP": 0.325, "AVG_v_RHP": 0.302},
            {"Player": "Joe Dugan", "Pos": "3B", "Bats": "R", "AVG": 0.269, "OPS": 0.672, "HR": 2, "AB": 387, "SPD": 55, "AVG_v_LHP": 0.280, "AVG_v_RHP": 0.264},
            {"Player": "Pat Collins", "Pos": "C", "Bats": "R", "AVG": 0.275, "OPS": 0.825, "HR": 7, "AB": 251, "SPD": 40, "AVG_v_LHP": 0.290, "AVG_v_RHP": 0.268},
            {"Player": "Ray Morehart", "Pos": "IF", "Bats": "L", "AVG": 0.256, "OPS": 0.630, "HR": 1, "AB": 195, "SPD": 68, "AVG_v_LHP": 0.220, "AVG_v_RHP": 0.270}
        ],
        "pitching": [
            {"Player": "Waite Hoyt", "Pos": "SP", "Role": "SP", "Throws": "R", "ERA": 2.63, "WHIP": 1.15, "SO (K)": 86, "IP": "256.2", "ERA_v_LHB": 2.80, "ERA_v_RHB": 2.50},
            {"Player": "Herb Pennock", "Pos": "SP", "Role": "SP", "Throws": "L", "ERA": 3.00, "WHIP": 1.21, "SO (K)": 51, "IP": "209.2", "ERA_v_LHB": 2.60, "ERA_v_RHB": 3.15},
            {"Player": "Urban Shocker", "Pos": "SP", "Role": "SP", "Throws": "R", "ERA": 2.84, "WHIP": 1.16, "SO (K)": 35, "IP": "200.0", "ERA_v_LHB": 3.05, "ERA_v_RHB": 2.70},
            {"Player": "Wilcy Moore", "Pos": "RP", "Role": "Closer", "Throws": "R", "ERA": 2.28, "WHIP": 1.14, "SO (K)": 75, "IP": "213.0", "ERA_v_LHB": 2.40, "ERA_v_RHB": 2.15}
        ]
    },
    "2004 Boston Red Sox": {
        "primary": "#BD3039", "secondary": "#0C2340", "runs_scored": 949, "runs_allowed": 768,
        "hitting": [
            {"Player": "Johnny Damon", "Pos": "CF", "Bats": "L", "AVG": 0.304, "OPS": 0.877, "HR": 20, "AB": 621, "SPD": 90, "AVG_v_LHP": 0.275, "AVG_v_RHP": 0.316},
            {"Player": "Mark Bellhorn", "Pos": "2B", "Bats": "B", "AVG": 0.264, "OPS": 0.801, "HR": 17, "AB": 500, "SPD": 62, "AVG_v_LHP": 0.250, "AVG_v_RHP": 0.270},
            {"Player": "Manny Ramirez", "Pos": "LF", "Bats": "R", "AVG": 0.308, "OPS": 1.009, "HR": 43, "AB": 568, "SPD": 50, "AVG_v_LHP": 0.325, "AVG_v_RHP": 0.300},
            {"Player": "David Ortiz", "Pos": "DH", "Bats": "L", "AVG": 0.301, "OPS": 0.983, "HR": 41, "AB": 582, "SPD": 45, "AVG_v_LHP": 0.265, "AVG_v_RHP": 0.318},
            {"Player": "Kevin Millar", "Pos": "1B", "Bats": "R", "AVG": 0.297, "OPS": 0.874, "HR": 18, "AB": 508, "SPD": 42, "AVG_v_LHP": 0.310, "AVG_v_RHP": 0.290},
            {"Player": "Jason Varitek", "Pos": "C", "Bats": "B", "AVG": 0.296, "OPS": 0.890, "HR": 18, "AB": 463, "SPD": 48, "AVG_v_LHP": 0.280, "AVG_v_RHP": 0.302},
            {"Player": "Orlando Cabrera", "Pos": "SS", "Bats": "R", "AVG": 0.294, "OPS": 0.785, "HR": 6, "AB": 245, "SPD": 78, "AVG_v_LHP": 0.305, "AVG_v_RHP": 0.288},
            {"Player": "Bill Mueller", "Pos": "3B", "Bats": "B", "AVG": 0.283, "OPS": 0.795, "HR": 12, "AB": 399, "SPD": 58, "AVG_v_LHB": 0.270, "AVG_v_RHP": 0.289},
            {"Player": "Trot Nixon", "Pos": "RF", "Bats": "L", "AVG": 0.293, "OPS": 0.871, "HR": 6, "AB": 140, "SPD": 70, "AVG_v_LHP": 0.235, "AVG_v_RHP": 0.305}
        ],
        "pitching": [
            {"Player": "Curt Schilling", "Pos": "SP", "Role": "SP", "Throws": "R", "ERA": 3.26, "WHIP": 1.06, "SO (K)": 203, "IP": "226.2", "ERA_v_LHB": 3.45, "ERA_v_RHB": 3.10},
            {"Player": "Pedro Martinez", "Pos": "SP", "Role": "SP", "Throws": "R", "ERA": 3.90, "WHIP": 1.21, "SO (K)": 227, "IP": "217.0", "ERA_v_LHB": 4.10, "ERA_v_RHB": 3.70},
            {"Player": "Tim Wakefield", "Pos": "SP", "Role": "Long Relief", "Throws": "R", "ERA": 4.87, "WHIP": 1.34, "SO (K)": 116, "IP": "188.1", "ERA_v_LHB": 5.10, "ERA_v_RHB": 4.65},
            {"Player": "Keith Foulke", "Pos": "RP", "Role": "Closer", "Throws": "R", "ERA": 2.17, "WHIP": 0.94, "SO (K)": 79, "IP": "83.0", "ERA_v_LHB": 2.30, "ERA_v_RHB": 2.05}
        ]
    }
}

TEAM_COLORS = {
    "New York Mets": {"primary": "#002D72", "secondary": "#FF5910"},
    "Los Angeles Angels": {"primary": "#BA0021", "secondary": "#003263"},
    "New York Yankees": {"primary": "#0C2340", "secondary": "#C4CED4"},
    "Boston Red Sox": {"primary": "#BD3039", "secondary": "#0C2340"},
    "Los Angeles Dodgers": {"primary": "#005A9C", "secondary": "#A5ACAF"},
    "Texas Rangers": {"primary": "#003274", "secondary": "#C0111F"}
}

BALLPARK_MODIFIERS = {
    "San Diego Padres": {"run_mult": 0.93, "hr_mult": 0.85, "desc": "Petco Park - Marine layer limits carry"},
    "Los Angeles Dodgers": {"run_mult": 1.02, "hr_mult": 1.08, "desc": "Dodger Stadium - High structural carry vector"},
    "1927 New York Yankees": {"run_mult": 1.05, "hr_mult": 1.02, "desc": "Yankee Stadium I - Deep short porch design"},
    "2004 Boston Red Sox": {"run_mult": 1.08, "hr_mult": 1.02, "desc": "Fenway Park - Green Monster distortion indices"},
}
DEFAULT_BALLPARK = {"run_mult": 1.00, "hr_mult": 1.00, "desc": "Neutral standard atmosphere allocation"}

# ----------------------------------------------------
# ADVANCED MODULE 2: BAYESIAN LEAGUE REGRESSION
# ----------------------------------------------------
def apply_bayesian_stabilization(actual_stat, current_ab, stat_type="AVG"):
    if stat_type == "AVG":
        league_baseline = 0.244
        sample_anchor = 120
    else:
        league_baseline = 0.720
        sample_anchor = 150
        
    stabilized = ((actual_stat * current_ab) + (league_baseline * sample_anchor)) / (current_ab + sample_anchor)
    return round(stabilized, 3)

@st.cache_data(ttl=3600)
def get_mlb_teams():
    try:
        url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
        res = requests.get(url, timeout=5).json()
        teams = {}
        for team in res.get('teams', []):
            if team.get('active', True): teams[team['name']] = team['id']
        return dict(sorted(teams.items()))
    except:
        return {"1927 New York Yankees": 1, "2004 Boston Red Sox": 2}

live_teams = get_mlb_teams()
all_selectable_teams = sorted(list(set(list(live_teams.keys()) + list(RETRO_TEAMS.keys()))))

@st.cache_data(ttl=3600)
def get_detailed_roster_stats(team_id, team_name, stat_group="hitting"):
    if team_name in RETRO_TEAMS: return pd.DataFrame(RETRO_TEAMS[team_name][stat_group])
    players_list = []
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=Active&hydrate=person(stats(group=[{stat_group}],type=season,season=2026))"
        res = requests.get(url, timeout=5).json()
        
        counter = 0
        for member in res.get('roster', []):
            person = member.get('person', {})
            name = person.get('fullName', 'Unknown Player')
            pos = member.get('position', {}).get('abbreviation', 'N/A')
            stats_group = person.get('stats', [{}])[0].get('splits', [{}])
            
            if stats_group and 'stat' in stats_group[0]:
                stat = stats_group[0]['stat']
                if stat_group == "hitting":
                    ab = int(stat.get("atBats", 1))
                    raw_avg = float(stat.get("avg", ".244"))
                    raw_ops = float(stat.get("ops", ".720"))
                    
                    adjusted_avg = apply_bayesian_stabilization(raw_avg, ab, "AVG")
                    adjusted_ops = apply_bayesian_stabilization(raw_ops, ab, "OPS")
                    
                    players_list.append({
                        "Player": name, "Pos": pos, "Bats": person.get('batSide', {}).get('code', 'R'),
                        "AVG": adjusted_avg, "OPS": adjusted_ops,
                        "H": int(stat.get("hits", 0)), "HR": int(stat.get("homeRuns", 0)),
                        "RBI": int(stat.get("rbi", 0)), "BB": int(stat.get("baseOnBalls", 0)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "AB": ab, "SPD": random.randint(40, 95),
                        "AVG_v_LHP": round(adjusted_avg * random.choice([0.91, 1.08]), 3),
                        "AVG_v_RHP": round(adjusted_avg * random.choice([1.03, 0.94]), 3)
                    })
                elif stat_group == "pitching":
                    era_val = float(stat.get("era", 4.25))
                    if pos == "SP": bullpen_role = "SP"
                    elif counter % 4 == 0: bullpen_role = "Closer"
                    elif counter % 4 == 1: bullpen_role = "Setup"
                    elif counter % 4 == 2: bullpen_role = "Middle Relief"
                    else: bullpen_role = "Long Relief"
                    counter += 1
                    
                    players_list.append({
                        "Player": name, "Pos": pos, "Role": bullpen_role, "Throws": person.get('pitchHand', {}).get('code', 'R'),
                        "ERA": era_val, "WHIP": float(stat.get("whip", 1.30)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "IP": stat.get("inningsPitched", "10.0"),
                        "ERA_v_LHB": round(era_val * random.choice([1.06, 0.94]), 2),
                        "ERA_v_RHB": round(era_val * random.choice([0.94, 1.06]), 2)
                    })
    except: pass
    if not players_list:
        if stat_group == "hitting":
            return pd.DataFrame([{"Player": f"Batter {i+1}", "Pos": "OF", "Bats": random.choice(["R","L"]), "AVG": 0.250, "OPS": 0.740, "HR": random.randint(5,25), "AB": 200, "SPD": 65, "AVG_v_LHP": 0.240, "AVG_v_RHP": 0.255} for i in range(12)])
        else:
            roles = ["SP", "SP", "SP", "Middle Relief", "Setup", "Closer", "Long Relief"]
            return pd.DataFrame([{"Player": f"Pitcher {i+1}", "Pos": "P", "Role": roles[i % len(roles)], "Throws": random.choice(["R","L"]), "ERA": 4.00, "WHIP": 1.25, "SO (K)": 60, "IP": "50.0", "ERA_v_LHB": 4.10, "ERA_v_RHB": 3.90} for i in range(7)])
    return pd.DataFrame(players_list)

# ----------------------------------------------------
# MATCHUP & CONTROLS CONTROL PANEL
# ----------------------------------------------------
st.sidebar.header("⚾ Enterprise Simulator Panel")
away_team = st.sidebar.selectbox("Away Roster Array", all_selectable_teams, index=0, disabled=st.session_state["lineups_locked"])
home_team = st.sidebar.selectbox("Home Roster Array", all_selectable_teams, index=min(1, len(all_selectable_teams)-1), disabled=st.session_state["lineups_locked"])

st.sidebar.markdown("---")
sim_speed = st.sidebar.slider("Simulation Step Intercept Delay", 0.00, 0.40, 0.02, step=0.01)

theme_host = RETRO_TEAMS.get(home_team, TEAM_COLORS.get(home_team, {"primary": "#003274", "secondary": "#C0111F"}))
st.markdown(f"<style>h1, h2, h3, h4 {{ color: {theme_host['primary']}; }} .stButton>button {{ background-color: {theme_host['primary']} !important; color: white !important; }}</style>", unsafe_allow_html=True)

away_hitter_raw = get_detailed_roster_stats(live_teams.get(away_team, 0), away_team, "hitting")
home_hitter_raw = get_detailed_roster_stats(live_teams.get(home_team, 0), home_team, "hitting")
away_pitcher_raw = get_detailed_roster_stats(live_teams.get(away_team, 0), away_team, "pitching")
home_pitcher_raw = get_detailed_roster_stats(live_teams.get(home_team, 0), home_team, "pitching")

away_hitters_pool = away_hitter_raw[~away_hitter_raw["Pos"].isin(["SP", "RP", "P"])]
home_hitters_pool = home_hitter_raw[~home_hitter_raw["Pos"].isin(["SP", "RP", "P"])]

if not st.session_state["lineups_locked"]:
    st.subheader("📋 Lineup Ingestion Strategy Matrix")
    col_a, col_h = st.columns(2)
    with col_a:
        st.markdown(f"### {away_team}")
        away_pitchers_list = list(away_pitcher_raw[away_pitcher_raw["Role"]=="SP"]["Player"])
        if not away_pitchers_list: away_pitchers_list = list(away_pitcher_raw["Player"])
        away_sp_choice = st.selectbox(f"Select Pitching Ace ({away_team})", away_pitchers_list)
        
        away_batters = []
        default_top_away = away_hitters_pool.sort_values(by="OPS", ascending=False).head(9)["Player"].tolist()
        for slot in range(1, 10):
            def_idx = (slot - 1) if (slot - 1) < len(default_top_away) else 0
            b_choice = st.selectbox(f"Slot {slot} Batter", list(away_hitters_pool["Player"]), index=list(away_hitters_pool["Player"]).index(default_top_away[def_idx]), key=f"a_{slot}")
            away_batters.append(b_choice)
            
    with col_h:
        st.markdown(f"### {home_team}")
        home_pitchers_list = list(home_pitcher_raw[home_pitcher_raw["Role"]=="SP"]["Player"])
        if not home_pitchers_list: home_pitchers_list = list(home_pitcher_raw["Player"])
        home_sp_choice = st.selectbox(f"Select Pitching Ace ({home_team})", home_pitchers_list)
        
        home_batters = []
        default_top_home = home_hitters_pool.sort_values(by="OPS", ascending=False).head(9)["Player"].tolist()
        for slot in range(1, 10):
            def_idx = (slot - 1) if (slot - 1) < len(default_top_home) else 0
            b_choice = st.selectbox(f"Slot {slot} Batter ", list(home_hitters_pool["Player"]), index=list(home_hitters_pool["Player"]).index(default_top_home[def_idx]), key=f"h_{slot}")
            home_batters.append(b_choice)

    if st.button("🔒 Lock Framework Configurations & Generate Ecosystem Data", use_container_width=True):
        # FIX FOR SCREENSHOT 6: Prevent slice IndexError if dynamic criteria filter produces an empty DataFrame
        away_selected_df = away_pitcher_raw[away_pitcher_raw["Player"] == away_sp_choice]
        home_selected_df = home_pitcher_raw[home_pitcher_raw["Player"] == home_sp_choice]
        
        st.session_state["ready_away_sp"] = away_selected_df.iloc[0].to_dict() if not away_selected_df.empty else away_pitcher_raw.iloc[0].to_dict()
        st.session_state["ready_home_sp"] = home_selected_df.iloc[0].to_dict() if not home_selected_df.empty else home_pitcher_raw.iloc[0].to_dict()
        
        st.session_state["ready_away_lineup"] = pd.DataFrame([away_hitters_pool[away_hitters_pool["Player"] == name].iloc[0].to_dict() for name in away_batters])
        st.session_state["ready_home_lineup"] = pd.DataFrame([home_hitters_pool[home_hitters_pool["Player"] == name].iloc[0].to_dict() for name in home_batters])
        st.session_state["away_bullpen"] = away_pitcher_raw[away_pitcher_raw["Player"] != st.session_state["ready_away_sp"]["Player"]].to_dict('records')
        st.session_state["home_bullpen"] = home_pitcher_raw[home_pitcher_raw["Player"] != st.session_state["ready_home_sp"]["Player"]].to_dict('records')
        st.session_state["lineups_locked"] = True
        st.rerun()

else:
    st.sidebar.button("🔓 Release Lock System", on_click=lambda: st.session_state.update({"lineups_locked": False, "game_active": False, "leveraged_game_state": None}))
    
    away_lineup_final = st.session_state["ready_away_lineup"]
    home_lineup_final = st.session_state["ready_home_lineup"]
    away_pitcher_active = st.session_state["ready_away_sp"]
    home_pitcher_active = st.session_state["ready_home_sp"]

    st.subheader("🎲 Mathematical Simulation Run Configuration")
    sim_mode = st.radio("Simulation Model Mode Execution Type", ["Single Immersive Simulation", "Multi-Game Postseason Series Simulator"], horizontal=True)
    series_length = 1
    if sim_mode == "Multi-Game Postseason Series Simulator":
        series_length = st.selectbox("Series Iteration Range Block", [3, 5, 7], index=1)

    # ----------------------------------------------------
    # ADVANCED MODULE 3: ENVIRONMENTAL CLIMATE INTERCEPTOR
    # ----------------------------------------------------
    def generate_atmospheric_environment(home_team_name):
        temp = random.randint(54, 96)
        humidity = random.randint(25, 85)
        weather_mult = 1.0 + ((temp - 72) * 0.0022) - ((humidity - 50) * 0.0006)
        return {"temp": temp, "humidity": humidity, "mult": weather_mult}

    # ----------------------------------------------------
    # ADVANCED MODULE 4: LEVERAGE-INDEX BULLPEN MANAGER AI
    # ----------------------------------------------------
    def select_leverage_bullpen_arm(bullpen_list, inning, score_diff):
        if not bullpen_list:
            return {"Player": "Emergency Position Player", "ERA": 9.99, "Role": "Blowout Protection", "Throws": "R", "ERA_v_LHB": 9.99, "ERA_v_RHB": 9.99}
            
        if inning >= 9 and 1 <= score_diff <= 3:
            target_roles = ["Closer", "Setup"]
        elif inning >= 7 and score_diff <= 3:
            target_roles = ["Setup", "Middle Relief"]
        elif score_diff >= 6:
            target_roles = ["Long Relief", "Middle Relief"]
        else:
            target_roles = ["Middle Relief", "Long Relief"]

        for role in target_roles:
            for index, pitcher in enumerate(bullpen_list):
                if pitcher.get("Role") == role:
                    return bullpen_list.pop(index)
                    
        return bullpen_list.pop(0)

    def calculate_live_win_probability(g):
        base = 0.50
        run_diff = g["home_score"] - g["away_score"]
        base += run_diff * 0.125
        progress = (g["inning"] - 1) / 9.0
        if not g["top_half"]: progress += 0.05
        base += (run_diff * 0.06) * progress
        return max(0.01, min(0.99, base))

    def convert_prob_to_american_moneyline(prob):
        if prob >= 0.50:
            odds = int(-((prob / (1.0 - prob)) * 100))
            return f"{odds}" if odds <= -100 else "-100"
        else:
            odds = int(((1.0 - prob) / prob) * 100)
            return f"+{odds}"

    # ----------------------------------------------------
    # CORE UNIFIED TRACKING VECTOR SIMULATION ENGINE
    # ----------------------------------------------------
    def run_baseball_engine_iteration(g, env_mult, park_data, home_team, away_team):
        if g["top_half"]:
            g["home_p_pitches"] += random.randint(3, 6)
            score_diff = abs(g["away_score"] - g["home_score"])
            
            if (g["home_p_pitches"] > 88 and g["home_p_type"] == "SP") or (g["home_p_pitches"] > 25 and g["home_p_type"] == "RP") or (g["inning"] >= 9 and 1 <= (g["away_score"] - g["home_score"]) <= 3 and g["home_p_type"] == "SP"):
                reliever = select_leverage_bullpen_arm(g["home_bullpen_list"], g["inning"], score_diff)
                g["home_p_name"] = reliever["Player"]
                g["home_p_era"] = float(reliever["ERA"])
                g["home_p_throws"] = reliever.get("Throws", "R")
                g["home_p_type"] = reliever.get("Role", "RP")
                g["home_p_era_v_lhb"] = float(reliever.get("ERA_v_LHB", reliever["ERA"]))
                g["home_p_era_v_rhb"] = float(reliever.get("ERA_v_RHB", reliever["ERA"]))
                g["home_p_pitches"] = 0
                g["logs"].append(f"🔄 **AI Manager:** Home introduces bullpen asset `{reliever['Player']}` ({reliever.get('Role', 'RP')}) into high leverage lanes.")
                
            p_name, p_throws = g["home_p_name"], g.get("home_p_throws", "R")
            batter = away_lineup_final.iloc[g["away_idx"] % 9]
            b_team, opp_team = "away", "home"
            p_era = g["home_p_era_v_lhb"] if batter["Bats"] == "L" else g["home_p_era_v_rhb"]
            p_pitches_spent = g["home_p_pitches"]
        else:
            g["away_p_pitches"] += random.randint(3, 6)
            score_diff = abs(g["away_score"] - g["home_score"])
            
            if (g["away_p_pitches"] > 88 and g["away_p_type"] == "SP") or (g["away_p_pitches"] > 25 and g["away_p_type"] == "RP") or (g["inning"] >= 9 and 1 <= (g["home_score"] - g["away_score"]) <= 3 and g["away_p_type"] == "SP"):
                reliever = select_leverage_bullpen_arm(g["away_bullpen_list"], g["inning"], score_diff)
                g["away_p_name"] = reliever["Player"]
                g["away_p_era"] = float(reliever["ERA"])
                g["away_p_throws"] = reliever.get("Throws", "R")
                g["away_p_type"] = reliever.get("Role", "RP")
                g["away_p_era_v_lhb"] = float(reliever.get("ERA_v_LHB", reliever["ERA"]))
                g["away_p_era_v_rhb"] = float(reliever.get("ERA_v_RHB", reliever["ERA"]))
                g["away_p_pitches"] = 0
                g["logs"].append(f"🔄 **AI Manager:** Away calls upon bullpen asset `{reliever['Player']}` ({reliever.get('Role', 'RP')}) to suppress run distribution curves.")
                
            p_name, p_throws = g["away_p_name"], g.get("away_p_throws", "R")
            batter = home_lineup_final.iloc[g["home_idx"] % 9]
            b_team, opp_team = "home", "away"
            p_era = g["away_p_era_v_lhb"] if batter["Bats"] == "L" else g["away_p_era_v_rhb"]
            p_pitches_spent = g["away_p_pitches"]

        fatigue_coefficient = 1.0
        if g[f"{opp_team}_p_type"] == "SP" and p_pitches_spent > 30:
            fatigue_coefficient += (p_pitches_spent - 30) * 0.0038
        elif g[f"{opp_team}_p_type"] != "SP" and p_pitches_spent > 12:
            fatigue_coefficient += (p_pitches_spent - 12) * 0.0092
            
        effective_era = p_era * fatigue_coefficient
        
        if p_throws == "L": base_hit_prob = batter.get("AVG_v_LHP", batter["AVG"])
        else: base_hit_prob = batter.get("AVG_v_RHP", batter["AVG"])

        bb_chance = 0.082 * (effective_era / 4.0)
        if random.uniform(0, 1) < bb_chance:
            g[f"{b_team}_box"][batter["Player"]]["BB"] += 1
            g["logs"].append(f"🟢 **Walk!** {batter['Player']} structural walk transaction executed.")
            if g["bases"][0]:
                if g["bases"][1]:
                    if g["bases"][2]:
                        g[f"{b_team}_score"] += 1
                        g["line_score"][b_team][g["inning"]-1] = g["line_score"][b_team].get(g["inning"]-1, 0) + 1
                        g[f"{b_team}_box"][batter["Player"]]["RBI"] += 1
                    g["bases"][2] = g["bases"][1]
                g["bases"][1] = g["bases"][0]
            g["bases"][0] = batter["Player"]
            g[f"{b_team}_base_speeds"][batter["Player"]] = batter.get("SPD", 65)
        else:
            g[f"{b_team}_box"][batter["Player"]]["AB"] += 1
            hit_probability = base_hit_prob * park_data["run_mult"] * (effective_era / 4.15)
            
            if random.uniform(0, 1.0) <= hit_probability:
                g[f"{b_team}_hits"] += 1
                hr_chance = (batter["HR"] / max(1, batter["AB"])) * park_data["hr_mult"] * env_mult
                roll = random.uniform(0, 1)
                
                if roll <= hr_chance:
                    runs = 1 + sum([1 for r in g["bases"] if r is not None])
                    g[f"{b_team}_box"][batter["Player"]]["HR"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                    g[f"{b_team}_score"] += runs
                    g["line_score"][b_team][g["inning"]-1] = g["line_score"][b_team].get(g["inning"]-1, 0) + runs
                    g["bases"] = [None, None, None]
                    g[f"{b_team}_base_speeds"] = {}
                    g["logs"].append(f"💥 **HR!** {batter['Player']} hits a `{runs}-run` blast! (Velocity Scalar: {round(env_mult,2)}x)")
                elif roll <= hr_chance + 0.23:
                    runs = 0
                    if g["bases"][2]: runs += 1; g["bases"][2] = None
                    if g["bases"][1]: runs += 1; g["bases"][1] = None
                    if g["bases"][0]:
                        spd = g[f"{b_team}_base_speeds"].get(g["bases"][0], 65)
                        if spd > 72 or random.uniform(0,1) > 0.32:
                            runs += 1
                            g["logs"].append(f"🏃💨 *Extra Bases!* Speed tracking variable ({spd}) allows score from 1st on double.")
                        else: g["bases"][2] = g["bases"][0]
                        g["bases"][0] = None
                    g[f"{b_team}_box"][batter["Player"]]["2B"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                    g[f"{b_team}_score"] += runs
                    g["line_score"][b_team][g["inning"]-1] = g["line_score"][b_team].get(g["inning"]-1, 0) + runs
                    g["bases"][1] = batter["Player"]
                    g[f"{b_team}_base_speeds"][batter["Player"]] = batter.get("SPD", 65)
                    g["logs"].append(f"⚾ **Double!** {batter['Player']} hits a line drive down the line.")
                else:
                    runs = 0
                    if g["bases"][2]: runs += 1; g["bases"][2] = None
                    if g["bases"][1]:
                        spd = g[f"{b_team}_base_speeds"].get(g["bases"][1], 65)
                        if spd > 75 or random.uniform(0,1) > 0.38: runs += 1
                        else: g["bases"][2] = g["bases"][1]
                        g["bases"][1] = None
                    if g["bases"][0]:
                        g["bases"][1] = g["bases"][0]; g["bases"][0] = None
                    g[f"{b_team}_box"][batter["Player"]]["1B"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                    g[f"{b_team}_score"] += runs
                    g["line_score"][b_team][g["inning"]-1] = g["line_score"][b_team].get(g["inning"]-1, 0) + runs
                    g["bases"][0] = batter["Player"]
                    g[f"{b_team}_base_speeds"][batter["Player"]] = batter.get("SPD", 65)
                    g["logs"].append(f"🏃 **Base Hit!** {batter['Player']} loops a single.")
            else:
                g["outs"] += 1
                if random.uniform(0, 1) <= 0.25:
                    g["logs"].append(f"💨 *Strikeout!* {batter['Player']} chasing pitch sequence.")
                    g[f"{opp_team}_pitcher_k_count"] += 1
                else: g["logs"].append(f"🥎 *Out!* {batter['Player']} flies out to deep position lines.")

        b_stats = g[f"{b_team}_box"][batter["Player"]]
        b_stats["DK_PTS"] = (3 * b_stats["1B"]) + (5 * b_stats["2B"]) + (10 * b_stats["HR"]) + (2 * b_stats["RBI"]) + (2 * b_stats["BB"])
        b_stats["HRR_VAL"] = b_stats["H"] + b_stats["RBI"]
        b_stats["TOTAL_BASES"] = (1 * b_stats["1B"]) + (2 * b_stats["2B"]) + (4 * b_stats["HR"])

        if g["top_half"]: g["away_idx"] += 1
        else: g["home_idx"] += 1
        g["win_prob_history"].append(calculate_live_win_probability(g) * 100)

    # FIX FOR SCREENSHOTS 1, 2, & 4: Drop style.background_gradient dependencies to clear the headless server ImportError
    def render_vegas_projection_matrix(box_data, placeholder_obj=None):
        rows = []
        for p_name, s in box_data.items():
            hrr_line, tb_line = 1.5, 1.5
            hrr_val, tb_val, dk_pts = s.get("HRR_VAL", 0.0), s.get("TOTAL_BASES", 0.0), s.get("DK_PTS", 0.0)
            heat = round(60.0 + (s.get("HR", 0) * 15) + (s.get("H", 0) * 5), 2)
            chance = round(40.0 + (50.0 if hrr_val >= hrr_line else 10.0 * hrr_val), 2)
            rating = round(70.0 + dk_pts * 4, 2)
            if "DK_SALARY" not in s: s["DK_SALARY"] = random.randint(3800, 6400)
            
            rows.append({
                "PLAYER": p_name, "HEAT INDEX": min(99.9, heat), "HRR LINE": hrr_line, "HRR TOTAL": hrr_val,
                "TOTAL BASES": tb_val, "PROP EXP": "✅ OVER" if tb_val > tb_line else "❌ UNDER",
                "DK POINTS": dk_pts, "DK SALARY": f"${s['DK_SALARY']}", "HIT PROB %": min(100.0, chance), "POWER SCALAR": rating
            })
        df = pd.DataFrame(rows)
        if placeholder_obj: placeholder_obj.dataframe(df, use_container_width=True, hide_index=True)
        else: st.dataframe(df, use_container_width=True, hide_index=True)

    # ----------------------------------------------------
    # RUN TRACK: IMMERSIVE SINGLE-GAME GRAPHICAL INTERFACE
    # ----------------------------------------------------
    if sim_mode == "Single Immersive Simulation":
        if st.button("Launch Comprehensive Core Framework Simulation Vector Loop", type="primary", use_container_width=True):
            st.session_state["game_active"] = True
            st.session_state["leveraged_game_state"] = None

        if st.session_state["game_active"] or st.session_state["leveraged_game_state"] is not None:
            if st.session_state["leveraged_game_state"] is None:
                env_profile = generate_atmospheric_environment(home_team)
                
                # FIX FOR SCREENSHOT 3: Patched dynamic list composition setup to eliminate trailing initialization syntax errors
                st.session_state["leveraged_game_state"] = {
                    "inning": 1, "top_half": True, "away_score": 0, "home_score": 0, "away_hits": 0, "home_hits": 0, "away_errors": 0, "home_errors": 0,
                    "away_idx": 0, "home_idx": 0, "outs": 0, "bases": [None, None, None],
                    "line_score": {"away": {i: 0 for i in range(9)}, "home": {i: 0 for i in range(9)}},
                    "logs": [f"🏟️ Stadium Environment Settled. Temp: {env_profile['temp']}°F, Humidity: {env_profile['humidity']}%. Dynamic Barometric Multiplier: {round(env_profile['mult'], 3)}x"],
                    "away_box": {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in away_lineup_final["Player"]},
                    "home_box": {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in home_lineup_final["Player"]},
                    "away_base_speeds": {}, "home_base_speeds": {}, "env": env_profile,
                    "away_p_name": away_pitcher_active['Player'], "away_p_era": float(away_pitcher_active['ERA']), "away_p_pitches": 0, "away_p_type": "SP", "away_p_throws": away_pitcher_active.get("Throws", "R"),
                    "home_p_name": home_pitcher_active['Player'], "home_p_era": float(home_pitcher_active['ERA']), "home_p_pitches": 0, "home_p_type": "SP", "home_p_throws": home_pitcher_active.get("Throws", "R"),
                    "away_p_era_v_lhb": float(away_pitcher_active.get("ERA_v_LHB", away_pitcher_active['ERA'])), "away_p_era_v_rhb": float(away_pitcher_active.get("ERA_v_RHB", away_pitcher_active['ERA'])),
                    "home_p_era_v_lhb": float(home_pitcher_active.get("ERA_v_LHB", home_pitcher_active['ERA'])), "home_p_era_v_rhb": float(home_pitcher_active.get("ERA_v_RHB", home_pitcher_active['ERA'])),
                    "away_bullpen_list": list(st.session_state["away_bullpen"]), "home_bullpen_list": list(st.session_state["home_bullpen"]),
                    "away_pitcher_k_count": 0, "home_pitcher_k_count": 0, "win_prob_history": [50.0]
                }

            g = st.session_state["leveraged_game_state"]
            line_score_placeholder = st.empty()
            
            tab_view, tab_vegas, tab_away, tab_home = st.tabs(["🏟️ Live System Field Monitor", "🔮 Advanced Sportsbook Matrix", "📊 Away Box Grid", "📊 Home Box Grid"])
            with tab_view:
                f_col, g_col = st.columns(2)
                with f_col: field_viz = st.empty()
                with g_col: staff_viz = st.empty()
                ticker = st.empty()
            with tab_vegas:
                v_col1, v_col2 = st.columns(2)
                with v_col1: chart_placeholder = st.empty()
                with v_col2: odds_metrics_placeholder = st.empty()
                vegas_away_placeholder = st.empty()
                vegas_home_placeholder = st.empty()
                
            with tab_away: away_box_display = st.empty()
            with tab_home: home_box_display = st.empty()

            park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)

            while g["inning"] <= 9 or (g["away_score"] == g["home_score"]):
                half_str = "Top" if g["top_half"] else "Bottom"
                if g["inning"] - 1 not in g["line_score"]["away"]:
                    g["line_score"]["away"][g["inning"]-1] = 0; g["line_score"]["home"][g["inning"]-1] = 0

                while g["outs"] < 3:
                    if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]: break
                    run_baseball_engine_iteration(g, g["env"]["mult"], park_data, home_team, away_team)

                    inn_headers = "".join([f"<th style='padding:5px; width:22px;'>{i+1}</th>" for i in range(max(9, g['inning']))])
                    def row_render(k):
                        return "".join([f"<td style='text-align:center;'>{g['line_score'][k].get(i, 0 if i < g['inning']-1 else '-')}</td>" for i in range(max(9, g['inning']))])

                    line_score_placeholder.markdown(f"""
                    <div style="background:#0e131f; color:white; padding:10px; border-radius:6px; font-family:monospace; font-size:13px;">
                        <table style="width:100%;">
                            <thead><tr><th style="text-align:left;">TEAM</th>{inn_headers}<th>R</th><th>H</th><th>E</th></tr></thead>
                            <tbody>
                                <tr><td>Away</td>{row_render('away')}<td><b>{g['away_score']}</b></td><td>{g['away_hits']}</td><td>0</td></tr>
                                <tr><td>Home</td>{row_render('home')}<td><b>{g['home_score']}</b></td><td>{g['home_hits']}</td><td>0</td></tr>
                            </tbody>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                    b1, b2, b3 = ["🟥" if x else "⬜" for x in g["bases"]]
                    field_viz.markdown(f"<pre style='font-size:14px;'>       [{b2}] 2nd\n3rd [{b3}]     [{b1}] 1st\n       [🏃] Plate</pre>", unsafe_allow_html=True)
                    
                    staff_viz.markdown(f"**Inning Scenario:** `{half_str} {g['inning']}` | **Outs:** `{g['outs']}`\n\n`{g['away_p_name']}` ({g['away_p_type']}) Pitches: `{g['away_p_pitches']}` | K: `{g['home_pitcher_k_count']}`\n\n`{g['home_p_name']}` ({g['home_p_type']}) Pitches: `{g['home_p_pitches']}` | K: `{g['away_pitcher_k_count']}`")
                    ticker.markdown("\n\n".join(g["logs"][-3:]))
                    
                    away_box_display.dataframe(pd.DataFrame.from_dict(g["away_box"], orient="index"))
                    home_box_display.dataframe(pd.DataFrame.from_dict(g["home_box"], orient="index"))
                    
                    current_h_prob = g["win_prob_history"][-1] / 100.0
                    chart_placeholder.line_chart(pd.DataFrame(g["win_prob_history"], columns=["Home Team Win Probability %"]))
                    odds_metrics_placeholder.markdown(f"* **{home_team} Moneyline:** `{convert_prob_to_american_moneyline(current_h_prob)}` \n* **{away_team} Moneyline:** `{convert_prob_to_american_moneyline(1.0 - current_h_prob)}` \n\nAtmosphere: `{g['env']['temp']}°F` | Density Adjuster: `{round(g['env']['mult'],2)}x`")

                    render_vegas_projection_matrix(g["away_box"], vegas_away_placeholder)
                    render_vegas_projection_matrix(g["home_box"], vegas_home_placeholder)
                    if sim_speed > 0: time.sleep(sim_speed)

                g["outs"] = 0; g["bases"] = [None, None, None]; g["away_base_speeds"] = {}; g["home_base_speeds"] = {}
                g["top_half"] = not g["top_half"]
                if g["top_half"]: g["inning"] += 1

            st.success(f"### 🏁 System Complete. Processing Roster End Vectors.")
            st.session_state["game_active"] = False
            st.session_state["leveraged_game_state"] = None

    # ----------------------------------------------------
    # RUN TRACK: POSTSEASON BACKGROUND BATCH SIMULATOR
    # ----------------------------------------------------
    else:
        if st.button(f"⚡ Execute Postseason Series Frame Engine Block", use_container_width=True, type="primary"):
            away_wins, home_wins, needed_wins = 0, 0, (series_length // 2) + 1
            s_away_box = {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in away_lineup_final["Player"]}
            s_home_box = {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in home_lineup_final["Player"]}
            
            while away_wins < needed_wins and home_wins < needed_wins:
                env_profile = generate_atmospheric_environment(home_team)
                bg = {
                    "inning": 1, "top_half": True, "away_score": 0, "home_score": 0, "away_hits": 0, "home_hits": 0, "away_errors": 0, "home_errors": 0,
                    "away_idx": 0, "home_idx": 0, "outs": 0, "bases": [None, None, None], "line_score": {"away": {}, "home": {}}, "logs": [],
                    "away_box": {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in away_lineup_final["Player"]},
                    "home_box": {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in home_lineup_final["Player"]},
                    "away_base_speeds": {}, "home_base_speeds": {},
                    "away_p_name": away_pitcher_active['Player'], "away_p_era": float(away_pitcher_active['ERA']), "away_p_pitches": 0, "away_p_type": "SP", "away_p_throws": away_pitcher_active.get("Throws", "R"),
                    "home_p_name": home_pitcher_active['Player'], "home_p_era": float(home_pitcher_active['ERA']), "home_p_pitches": 0, "home_p_type": "SP", "home_p_throws": home_pitcher_active.get("Throws", "R"),
                    "away_p_era_v_lhb": float(away_pitcher_active.get("ERA_v_LHB", away_pitcher_active['ERA'])), "away_p_era_v_rhb": float(away_pitcher_active.get("ERA_v_RHB", away_pitcher_active['ERA'])),
                    "home_p_era_v_lhb": float(home_pitcher_active.get("ERA_v_LHB", home_pitcher_active['ERA'])), "home_p_era_v_rhb": float(home_pitcher_active.get("ERA_v_RHB", home_pitcher_active['ERA'])),
                    "away_bullpen_list": list(st.session_state["away_bullpen"]), "home_bullpen_list": list(st.session_state["home_bullpen"]),
                    "away_pitcher_k_count": 0, "home_pitcher_k_count": 0, "win_prob_history": [50.0]
                }
                park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)
                
                while bg["inning"] <= 9 or (bg["away_score"] == bg["home_score"]):
                    while bg["outs"] < 3:
                        if bg["inning"] >= 9 and not bg["top_half"] and bg["home_score"] > bg["away_score"]: break
                        run_baseball_engine_iteration(bg, env_profile["mult"], park_data, home_team, away_team)
                    bg["outs"] = 0; bg["bases"] = [None, None, None]; bg["away_base_speeds"] = {}; bg["home_base_speeds"] = {}
                    bg["top_half"] = not bg["top_half"]
                    if bg["top_half"]: bg["inning"] += 1
                
                for p in s_away_box:
                    for key in ["AB","H","1B","2B","HR","RBI","BB","DK_PTS","HRR_VAL","TOTAL_BASES"]: s_away_box[p][key] += bg["away_box"][p][key]
                for p in s_home_box:
                    for key in ["AB","H","1B","2B","HR","RBI","BB","DK_PTS","HRR_VAL","TOTAL_BASES"]: s_home_box[p][key] += bg["home_box"][p][key]
                if bg["home_score"] > bg["away_score"]: home_wins += 1
                else: away_wins += 1
            
            st.info(f"### Playoff Series Result Concluded: {away_team} ({away_wins}) vs {home_team} ({home_wins})")
            render_vegas_projection_matrix(s_away_box)
            render_vegas_projection_matrix(s_home_box)
