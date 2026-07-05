import streamlit as st
import requests
import random
import time
import pandas as pd
import numpy as np

st.set_page_config(page_title="Live MLB Analytics Platform", page_icon="⚾", layout="wide")

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
# DATA WAREHOUSE SQUADS & RETRO ROSTERS
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
            {"Player": "Waite Hoyt", "Pos": "SP", "Throws": "R", "ERA": 2.63, "WHIP": 1.15, "SO (K)": 86, "IP": "256.2", "ERA_v_LHB": 2.80, "ERA_v_RHB": 2.50},
            {"Player": "Herb Pennock", "Pos": "SP", "Throws": "L", "ERA": 3.00, "WHIP": 1.21, "SO (K)": 51, "IP": "209.2", "ERA_v_LHB": 2.60, "ERA_v_RHB": 3.15},
            {"Player": "Urban Shocker", "Pos": "SP", "Throws": "R", "ERA": 2.84, "WHIP": 1.16, "SO (K)": 35, "IP": "200.0", "ERA_v_LHB": 3.05, "ERA_v_RHB": 2.70},
            {"Player": "Wilcy Moore", "Pos": "RP", "Throws": "R", "ERA": 2.28, "WHIP": 1.14, "SO (K)": 75, "IP": "213.0", "ERA_v_LHB": 2.40, "ERA_v_RHB": 2.15}
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
            {"Player": "Bill Mueller", "Pos": "3B", "Bats": "B", "AVG": 0.283, "OPS": 0.795, "HR": 12, "AB": 399, "SPD": 58, "AVG_v_LHP": 0.270, "AVG_v_RHP": 0.289},
            {"Player": "Trot Nixon", "Pos": "RF", "Bats": "L", "AVG": 0.293, "OPS": 0.871, "HR": 6, "AB": 140, "SPD": 70, "AVG_v_LHP": 0.235, "AVG_v_RHP": 0.305}
        ],
        "pitching": [
            {"Player": "Curt Schilling", "Pos": "SP", "Throws": "R", "ERA": 3.26, "WHIP": 1.06, "SO (K)": 203, "IP": "226.2", "ERA_v_LHB": 3.45, "ERA_v_RHB": 3.10},
            {"Player": "Pedro Martinez", "Pos": "SP", "Throws": "R", "ERA": 3.90, "WHIP": 1.21, "SO (K)": 227, "IP": "217.0", "ERA_v_LHB": 4.10, "ERA_v_RHB": 3.70},
            {"Player": "Tim Wakefield", "Pos": "SP", "Throws": "R", "ERA": 4.87, "WHIP": 1.34, "SO (K)": 116, "IP": "188.1", "ERA_v_LHB": 5.10, "ERA_v_RHB": 4.65},
            {"Player": "Keith Foulke", "Pos": "RP", "Throws": "R", "ERA": 2.17, "WHIP": 0.94, "SO (K)": 79, "IP": "83.0", "ERA_v_LHB": 2.30, "ERA_v_RHB": 2.05}
        ]
    }
}

TEAM_COLORS = {
    "New York Mets": {"primary": "#002D72", "secondary": "#FF5910"},
    "Los Angeles Angels": {"primary": "#BA0021", "secondary": "#003263"},
    "New York Yankees": {"primary": "#0C2340", "secondary": "#C4CED4"},
    "Boston Red Sox": {"primary": "#BD3039", "secondary": "#0C2340"},
    "Los Angeles Dodgers": {"primary": "#005A9C", "secondary": "#A5ACAF"},
    "Chicago Cubs": {"primary": "#0E3386", "secondary": "#CC3433"},
    "San Francisco Giants": {"primary": "#FD5A1E", "secondary": "#27251F"},
    "San Diego Padres": {"primary": "#2F241D", "secondary": "#FFC425"},
    "Detroit Tigers": {"primary": "#0C2340", "secondary": "#FA4616"},
    "Texas Rangers": {"primary": "#003274", "secondary": "#C0111F"}
}

BALLPARK_MODIFIERS = {
    "San Diego Padres": {"run_mult": 0.93, "hr_mult": 0.85, "desc": "Petco Park - Coastal dimensions limit scoring"},
    "Los Angeles Dodgers": {"run_mult": 1.02, "hr_mult": 1.08, "desc": "Dodger Stadium - Favors power carries"},
    "1927 New York Yankees": {"run_mult": 1.05, "hr_mult": 1.02, "desc": "Yankee Stadium I - Short right field tracking lines"},
    "2004 Boston Red Sox": {"run_mult": 1.08, "hr_mult": 1.02, "desc": "Fenway Park - Green Monster wall factors"},
    "Texas Rangers": {"run_mult": 1.04, "hr_mult": 1.06, "desc": "Globe Life Field - Variable roof thermodynamics"}
}
DEFAULT_BALLPARK = {"run_mult": 1.00, "hr_mult": 1.00, "desc": "Standard neutral environment active"}

@st.cache_data(ttl=3600)
def get_mlb_teams():
    url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    try:
        res = requests.get(url, timeout=5).json()
        teams = {}
        for team in res.get('teams', []):
            if team.get('active', True): teams[team['name']] = team['id']
        return dict(sorted(teams.items()))
    except:
        return {"1927 New York Yankees": 1, "2004 Boston Red Sox": 2, "Detroit Tigers": 3, "Texas Rangers": 4}

live_teams = get_mlb_teams()
all_selectable_teams = sorted(list(set(list(live_teams.keys()) + list(RETRO_TEAMS.keys()))))

@st.cache_data(ttl=3600)
def get_detailed_roster_stats(team_id, team_name, stat_group="hitting"):
    if team_name in RETRO_TEAMS: return pd.DataFrame(RETRO_TEAMS[team_name][stat_group])
    players_list = []
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=Active&hydrate=person(stats(group=[{stat_group}],type=season,season=2026))"
        res = requests.get(url, timeout=5).json()
        for member in res.get('roster', []):
            person = member.get('person', {})
            name = person.get('fullName', 'Unknown Player')
            pos = member.get('position', {}).get('abbreviation', 'N/A')
            stats_group = person.get('stats', [{}])[0].get('splits', [{}])
            if stats_group and 'stat' in stats_group[0]:
                stat = stats_group[0]['stat']
                if stat_group == "hitting":
                    avg_val = float(stat.get("avg", ".000"))
                    players_list.append({
                        "Player": name, "Pos": pos, "Bats": person.get('batSide', {}).get('code', 'R'),
                        "AVG": avg_val, "OPS": float(stat.get("ops", ".000")),
                        "H": int(stat.get("hits", 0)), "HR": int(stat.get("homeRuns", 0)),
                        "RBI": int(stat.get("rbi", 0)), "BB": int(stat.get("baseOnBalls", 0)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "AB": int(stat.get("atBats", 1)),
                        "SPD": random.randint(45, 92),
                        "AVG_v_LHP": round(avg_val * random.choice([0.92, 1.06]), 3),
                        "AVG_v_RHP": round(avg_val * random.choice([1.04, 0.95]), 3)
                    })
                elif stat_group == "pitching":
                    era_val = float(stat.get("era", 4.50))
                    players_list.append({
                        "Player": name, "Pos": pos, "Throws": person.get('pitchHand', {}).get('code', 'R'),
                        "ERA": era_val, "WHIP": float(stat.get("whip", 1.30)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "IP": stat.get("inningsPitched", "0.0"),
                        "ERA_v_LHB": round(era_val * random.choice([1.08, 0.94]), 2),
                        "ERA_v_RHB": round(era_val * random.choice([0.93, 1.07]), 2)
                    })
    except: pass
    if not players_list:
        if stat_group == "hitting":
            return pd.DataFrame([{"Player": f"Batter {i+1}", "Pos": "OF", "Bats": random.choice(["R","L"]), "AVG": 0.260, "OPS": 0.750, "HR": random.randint(0,20), "AB": 300, "SPD": 65, "AVG_v_LHP": 0.250, "AVG_v_RHP": 0.265} for i in range(12)])
        else:
            return pd.DataFrame([{"Player": f"Pitcher {i+1}", "Pos": random.choice(["SP","RP"]), "Throws": random.choice(["R","L"]), "ERA": 4.10, "WHIP": 1.28, "SO (K)": 70, "IP": "80.0", "ERA_v_LHB": 4.20, "ERA_v_RHB": 4.00} for i in range(7)])
    return pd.DataFrame(players_list)

# ----------------------------------------------------
# MATCHUP PANEL INTERFACE
# ----------------------------------------------------
st.sidebar.header("⚾ Franchise Matchup Selector")
away_team = st.sidebar.selectbox("Away Team (Visitor)", all_selectable_teams, index=0, disabled=st.session_state["lineups_locked"])
home_team = st.sidebar.selectbox("Home Team (Host)", all_selectable_teams, index=min(1, len(all_selectable_teams)-1), disabled=st.session_state["lineups_locked"])

st.sidebar.markdown("---")
st.sidebar.subheader("🕹️ Simulation Controllers")
sim_speed = st.sidebar.slider("Engine Frame Delay (Seconds)", 0.00, 0.40, 0.03, step=0.01)

theme_host = RETRO_TEAMS.get(home_team, TEAM_COLORS.get(home_team, {"primary": "#003274", "secondary": "#C0111F"}))
st.markdown(f"<style>h1, h2, h3, h4 {{ color: {theme_host['primary']}; }} .stButton>button {{ background-color: {theme_host['primary']} !important; color: white !important; }}</style>", unsafe_allow_html=True)

away_hitter_raw = get_detailed_roster_stats(live_teams.get(away_team, 0), away_team, "hitting")
home_hitter_raw = get_detailed_roster_stats(live_teams.get(home_team, 0), home_team, "hitting")
away_pitcher_raw = get_detailed_roster_stats(live_teams.get(away_team, 0), away_team, "pitching")
home_pitcher_raw = get_detailed_roster_stats(live_teams.get(home_team, 0), home_team, "pitching")

away_hitters_pool = away_hitter_raw[~away_hitter_raw["Pos"].isin(["SP", "RP", "P"])]
home_hitters_pool = home_hitter_raw[~home_hitter_raw["Pos"].isin(["SP", "RP", "P"])]

# ----------------------------------------------------
# VISUAL MANAGERS CORNER: LINEUP EDITOR
# ----------------------------------------------------
if not st.session_state["lineups_locked"]:
    st.subheader("🛠️ Strategy Room: Customize Orders & Pitchers")
    col_a, col_h = st.columns(2)
    with col_a:
        st.markdown(f"### 📋 {away_team}")
        away_sp_choice = st.selectbox(f"Choose Starter ({away_team})", list(away_pitcher_raw["Player"]))
        away_batters = []
        default_top_away = away_hitters_pool.sort_values(by="OPS", ascending=False).head(9)["Player"].tolist()
        for slot in range(1, 10):
            def_idx = (slot - 1) if (slot - 1) < len(default_top_away) else 0
            b_choice = st.selectbox(f"Slot #{slot} Batter", list(away_hitters_pool["Player"]), index=list(away_hitters_pool["Player"]).index(default_top_away[def_idx]), key=f"a_{slot}")
            away_batters.append(b_choice)
            
    with col_h:
        st.markdown(f"### 📋 {home_team}")
        home_sp_choice = st.selectbox(f"Choose Starter ({home_team})", list(home_pitcher_raw["Player"]))
        home_batters = []
        default_top_home = home_hitters_pool.sort_values(by="OPS", ascending=False).head(9)["Player"].tolist()
        for slot in range(1, 10):
            def_idx = (slot - 1) if (slot - 1) < len(default_top_home) else 0
            b_choice = st.selectbox(f"Slot #{slot} Batter ", list(home_hitters_pool["Player"]), index=list(home_hitters_pool["Player"]).index(default_top_home[def_idx]), key=f"h_{slot}")
            home_batters.append(b_choice)

    st.markdown("---")
    if st.button("🔒 Lock Lineups & Initialize Game Systems", use_container_width=True):
        st.session_state["ready_away_sp"] = away_pitcher_raw[away_pitcher_raw["Player"] == away_sp_choice].iloc[0].to_dict()
        st.session_state["ready_home_sp"] = home_pitcher_raw[home_pitcher_raw["Player"] == home_sp_choice].iloc[0].to_dict()
        
        st.session_state["ready_away_lineup"] = pd.DataFrame([away_hitters_pool[away_hitters_pool["Player"] == name].iloc[0].to_dict() for name in away_batters])
        st.session_state["ready_home_lineup"] = pd.DataFrame([home_hitters_pool[home_hitters_pool["Player"] == name].iloc[0].to_dict() for name in home_batters])
        
        st.session_state["away_bullpen"] = away_pitcher_raw[away_pitcher_raw["Player"] != away_sp_choice].to_dict('records')
        st.session_state["home_bullpen"] = home_pitcher_raw[home_pitcher_raw["Player"] != home_sp_choice].to_dict('records')
        st.session_state["lineups_locked"] = True
        st.rerun()

else:
    st.sidebar.button("🔓 Unlock & Reset Lineups", on_click=lambda: st.session_state.update({"lineups_locked": False, "game_active": False, "leveraged_game_state": None}))
    
    away_lineup_final = st.session_state["ready_away_lineup"]
    home_lineup_final = st.session_state["ready_home_lineup"]
    away_pitcher_active = st.session_state["ready_away_sp"]
    home_pitcher_active = st.session_state["ready_home_sp"]

    st.subheader("🎲 Action Deck: Choose Simulation Mode")
    sim_mode = st.radio("Select Framework Model", ["Single Immersive Simulation", "Multi-Game Postseason Series Simulator"], horizontal=True)
    
    series_length = 1
    if sim_mode == "Multi-Game Postseason Series Simulator":
        series_length = st.selectbox("Series Format Scale", [3, 5, 7], index=1)

    # ----------------------------------------------------
    # VEGAS ODDS UTILITY CALCULATORS
    # ----------------------------------------------------
    def calculate_live_win_probability(g):
        base = 0.50
        run_diff = g["home_score"] - g["away_score"]
        base += run_diff * 0.12
        
        progress = (g["inning"] - 1) / 9.0
        if not g["top_half"]: progress += 0.05
        
        base += (run_diff * 0.05) * progress
        
        base_weight = 0.0
        if g["bases"][0]: base_weight += 0.02
        if g["bases"][1]: base_weight += 0.04
        if g["bases"][2]: base_weight += 0.06
        
        if g["top_half"]: base -= base_weight * (1.0 + progress)
        else: base += base_weight * (1.0 + progress)
        
        return max(0.01, min(0.99, base))

    def convert_prob_to_american_moneyline(prob):
        if prob >= 0.50:
            odds = int(-((prob / (1.0 - prob)) * 100))
            return f"{odds}" if odds <= -100 else "-100"
        else:
            odds = int(((1.0 - prob) / prob) * 100)
            return f"+{odds}"

    # ----------------------------------------------------
    # CORE BASEBALL ENGINE ITERATION VECTOR
    # ----------------------------------------------------
    def run_baseball_engine_iteration(g, weather_mult, park_data, home_team, away_team):
        if g["top_half"]:
            g["home_p_pitches"] += random.randint(3, 6)
            is_high_leverage_closer_situation = (g["inning"] >= 9 and 1 <= (g["away_score"] - g["home_score"]) <= 3)
            if (g["home_p_pitches"] > 85 or is_high_leverage_closer_situation) and g["home_p_type"] == "SP":
                if len(g["home_bullpen_list"]) > 0:
                    reliever = g["home_bullpen_list"].pop(0)
                    g["home_p_name"] = reliever["Player"]
                    g["home_p_era"] = float(reliever["ERA"])
                    g["home_p_throws"] = reliever.get("Throws", "R")
                    g["home_p_era_v_lhb"] = float(reliever.get("ERA_v_LHB", reliever["ERA"]))
                    g["home_p_era_v_rhb"] = float(reliever.get("ERA_v_RHB", reliever["ERA"]))
                    g["home_p_pitches"] = 0
                    g["home_p_type"] = "RP"
            p_name, p_throws = g["home_p_name"], g.get("home_p_throws", "R")
            batter = away_lineup_final.iloc[g["away_idx"] % 9]
            b_team, opp_team = "away", "home"
            p_era = g["home_p_era_v_lhb"] if batter["Bats"] == "L" else g["home_p_era_v_rhb"]
        else:
            g["away_p_pitches"] += random.randint(3, 6)
            is_high_leverage_closer_situation = (g["inning"] >= 9 and 1 <= (g["home_score"] - g["away_score"]) <= 3)
            if (g["away_p_pitches"] > 85 or is_high_leverage_closer_situation) and g["away_p_type"] == "SP":
                if len(g["away_bullpen_list"]) > 0:
                    reliever = g["away_bullpen_list"].pop(0)
                    g["away_p_name"] = reliever["Player"]
                    g["away_p_era"] = float(reliever["ERA"])
                    g["away_p_throws"] = reliever.get("Throws", "R")
                    g["away_p_era_v_lhb"] = float(reliever.get("ERA_v_LHB", reliever["ERA"]))
                    g["away_p_era_v_rhb"] = float(reliever.get("ERA_v_RHB", reliever["ERA"]))
                    g["away_p_pitches"] = 0
                    g["away_p_type"] = "RP"
            p_name, p_throws = g["away_p_name"], g.get("away_p_throws", "R")
            batter = home_lineup_final.iloc[g["home_idx"] % 9]
            b_team, opp_team = "home", "away"
            p_era = g["away_p_era_v_lhb"] if batter["Bats"] == "L" else g["away_p_era_v_rhb"]

        # ADVANCED MODIFIER 1: True Situational Platoon Matrix Splits Lookup
        if p_throws == "L":
            base_hit_prob = batter.get("AVG_v_LHP", batter["AVG"])
        else:
            base_hit_prob = batter.get("AVG_v_RHP", batter["AVG"])

        effective_era = p_era * (1.25 if (g[f"{opp_team}_p_pitches"] > 80 and g[f"{opp_team}_p_type"] == "SP") else 1.0)
        
        bb_chance = 0.08 * (effective_era / 4.0)
        if random.uniform(0, 1) < bb_chance:
            g[f"{b_team}_box"][batter["Player"]]["BB"] += 1
            g["logs"].append(f"🟢 **Walk!** {batter['Player']} draws a walk.")
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
            hit_probability = base_hit_prob * park_data["run_mult"] * (effective_era / 4.10)
            
            if random.uniform(0, 1.0) <= hit_probability:
                g[f"{b_team}_hits"] += 1
                hr_chance = (batter["HR"] / max(1, batter["AB"])) * park_data["hr_mult"] * weather_mult
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
                    g["logs"].append(f"💥 **HR!** {batter['Player']} hits a `{runs}-run` home run!")
                elif roll <= hr_chance + 0.22:
                    # ADVANCED MODIFIER 2: Dynamic Speed Tracking Vector Logic
                    runs = 0
                    if g["bases"][2]: runs += 1; g["bases"][2] = None
                    if g["bases"][1]: runs += 1; g["bases"][1] = None
                    if g["bases"][0]:
                        spd = g[f"{b_team}_base_speeds"].get(g["bases"][0], 65)
                        if spd > 72 or random.uniform(0,1) > 0.35:
                            runs += 1
                            g["logs"].append(f"🏃💨 *Extra Bases!* {g['bases'][0]} scores all the way from 1st on the double!")
                        else:
                            g["bases"][2] = g["bases"][0]
                        g["bases"][0] = None
                    
                    g[f"{b_team}_box"][batter["Player"]]["2B"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                    g[f"{b_team}_score"] += runs
                    g["line_score"][b_team][g["inning"]-1] = g["line_score"][b_team].get(g["inning"]-1, 0) + runs
                    g["bases"][1] = batter["Player"]
                    g[f"{b_team}_base_speeds"][batter["Player"]] = batter.get("SPD", 65)
                    g["logs"].append(f"⚾ **Double!** {batter['Player']} hits a gapper.")
                else:
                    runs = 0
                    if g["bases"][2]: runs += 1; g["bases"][2] = None
                    if g["bases"][1]:
                        spd = g[f"{b_team}_base_speeds"].get(g["bases"][1], 65)
                        if spd > 75 or random.uniform(0,1) > 0.40:
                            runs += 1
                            g["logs"].append(f"🏃💨 *Speed Threat!* {g['bases'][1]} scores from 2nd on a single.")
                        else:
                            g["bases"][2] = g["bases"][1]
                        g["bases"][1] = None
                    if g["bases"][0]:
                        g["bases"][1] = g["bases"][0]
                        g["bases"][0] = None
                        
                    g[f"{b_team}_box"][batter["Player"]]["1B"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                    g[f"{b_team}_score"] += runs
                    g["line_score"][b_team][g["inning"]-1] = g["line_score"][b_team].get(g["inning"]-1, 0) + runs
                    g["bases"][0] = batter["Player"]
                    g[f"{b_team}_base_speeds"][batter["Player"]] = batter.get("SPD", 65)
                    g["logs"].append(f"🏃 **Base Hit!** {batter['Player']} hits a single.")
            else:
                g["outs"] += 1
                if random.uniform(0, 1) <= 0.24:
                    g["logs"].append(f"💨 *Strikeout!* {batter['Player']} strikes out.")
                    g[f"{opp_team}_pitcher_k_count"] += 1
                else:
                    g["logs"].append(f"🥎 *Out!* {batter['Player']} grounds out.")

        b_stats = g[f"{b_team}_box"][batter["Player"]]
        b_stats["DK_PTS"] = (3 * b_stats["1B"]) + (5 * b_stats["2B"]) + (10 * b_stats["HR"]) + (2 * b_stats["RBI"]) + (2 * b_stats["BB"])
        b_stats["HRR_VAL"] = b_stats["H"] + b_stats["RBI"]
        b_stats["TOTAL_BASES"] = (1 * b_stats["1B"]) + (2 * b_stats["2B"]) + (4 * b_stats["HR"])

        if g["top_half"]: g["away_idx"] += 1
        else: g["home_idx"] += 1

        current_home_wp = calculate_live_win_probability(g)
        g["win_prob_history"].append(current_home_wp * 100)

    # ----------------------------------------------------
    # SAFE RENDERING BLOCK (SAFE AGAINST MISSING MATPLOTLIB)
    # ----------------------------------------------------
    def render_vegas_projection_matrix(box_data, title, placeholder_obj=None):
        rows = []
        for p_name, s in box_data.items():
            hrr_line = 1.5 if s.get("HR", 0) == 0 else 2.5
            tb_line = 1.5
            hrr_val = s.get("HRR_VAL", 0.0)
            tb_val = s.get("TOTAL_BASES", 0.0)
            dk_pts = s.get("DK_PTS", 0.0)
            
            heat = round(60.0 + (s.get("HR", 0) * 15) + (s.get("H", 0) * 5), 2)
            chance = round(40.0 + (50.0 if hrr_val >= hrr_line else 10.0 * hrr_val), 2)
            rating = round(70.0 + dk_pts * 4, 2)
            g_rating = round(rating * 1.8, 1)
            dk_salary = s.get("DK_SALARY", random.randint(4000, 6200))
            s["DK_SALARY"] = dk_salary
            
            rows.append({
                "PLAYER": p_name, "HEAT": min(99.9, heat), "HRR LINE": hrr_line, "HRR VAL": hrr_val,
                "TOTAL BASES": tb_val, "O/U PROP LINE": tb_line, "PROP STATUS": "✅ OVER" if tb_val > tb_line else "❌ UNDER",
                "DK POINTS": dk_pts, "DK SALARY": f"${dk_salary}", "CHANCE %": min(100.0, chance), "RATING": rating, "G RATING": g_rating
            })
            
        df = pd.DataFrame(rows)

        try:
            styled_df = df.style.background_gradient(cmap="RdYlGn", subset=["HEAT", "HRR VAL", "CHANCE %", "RATING", "G RATING"])
            if placeholder_obj: placeholder_obj.dataframe(styled_df, use_container_width=True, hide_index=True)
            else: st.dataframe(styled_df, use_container_width=True, hide_index=True)
        except Exception:
            if placeholder_obj: placeholder_obj.dataframe(df, use_container_width=True, hide_index=True)
            else: st.dataframe(df, use_container_width=True, hide_index=True)

    # ----------------------------------------------------
    # MODE A: SINGLE GRAPHIC INTERACTIVE MODE
    # ----------------------------------------------------
    if sim_mode == "Single Immersive Simulation":
        if st.button("Launch Game Simulation Vector Loop", type="primary", use_container_width=True):
            st.session_state["game_active"] = True
            st.session_state["leveraged_game_state"] = None

        if st.session_state["game_active"] or st.session_state["leveraged_game_state"] is not None:
            if st.session_state["leveraged_game_state"] is None:
                st.session_state["leveraged_game_state"] = {
                    "inning": 1, "top_half": True, "away_score": 0, "home_score": 0,
                    "away_hits": 0, "home_hits": 0, "away_errors": 0, "home_errors": 0,
                    "away_idx": 0, "home_idx": 0, "outs": 0, "bases": [None, None, None],
                    "line_score": {"away": {i: 0 for i in range(9)}, "home": {i: 0 for i in range(9)}},
                    "logs": ["🏟️ Strategic Roster Arrays Locked."],
                    "away_box": {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in away_lineup_final["Player"]},
                    "home_box": {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in home_lineup_final["Player"]},
                    "away_base_speeds": {}, "home_base_speeds": {},
                    "away_p_name": away_pitcher_active['Player'], "away_p_era": float(away_pitcher_active['ERA']), "away_p_pitches": 0, "away_p_type": "SP", "away_p_throws": away_pitcher_active.get("Throws", "R"),
                    "home_p_name": home_pitcher_active['Player'], "home_p_era": float(home_pitcher_active['ERA']), "home_p_pitches": 0, "home_p_type": "SP", "home_p_throws": home_pitcher_active.get("Throws", "R"),
                    "away_p_era_v_lhb": float(away_pitcher_active.get("ERA_v_LHB", away_pitcher_active['ERA'])),
                    "away_p_era_v_rhb": float(away_pitcher_active.get("ERA_v_RHB", away_pitcher_active['ERA'])),
                    "home_p_era_v_lhb": float(home_pitcher_active.get("ERA_v_LHB", home_pitcher_active['ERA'])),
                    "home_p_era_v_rhb": float(home_pitcher_active.get("ERA_v_RHB", home_pitcher_active['ERA'])),
                    "away_bullpen_list": list(st.session_state["away_bullpen"]),
                    "home_bullpen_list": list(st.session_state["home_bullpen"]),
                    "away_pitcher_k_count": 0, "home_pitcher_k_count": 0,
                    "win_prob_history": [50.0]
                }

            g = st.session_state["leveraged_game_state"]
            line_score_placeholder = st.empty()
            
            tab_view, tab_vegas, tab_away, tab_home = st.tabs(["🏟️ Live Diamond Tracker", "🔮 Vegas Sportsbook Matrix", f"📊 {away_team} Box", f"📊 {home_team} Box"])
            with tab_view:
                f_col, g_col = st.columns([1, 1])
                with f_col: field_viz = st.empty()
                with g_col: staff_viz = st.empty()
                ticker = st.empty()
            with tab_vegas:
                v_col1, v_col2 = st.columns(2)
                with v_col1:
                    st.markdown("### 📈 Live Win Probability Curve")
                    chart_placeholder = st.empty()
                with v_col2:
                    st.markdown("### 🎲 Live Sportsbook Moneylines")
                    odds_metrics_placeholder = st.empty()
                
                st.markdown(f"#### {away_team} Prop Betting Matrix")
                vegas_away_placeholder = st.empty()
                st.markdown(f"#### {home_team} Prop Betting Matrix")
                vegas_home_placeholder = st.empty()
                
            with tab_away: away_box_display = st.empty()
            with tab_home: home_box_display = st.empty()

            park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)

            while g["inning"] <= 9 or (g["away_score"] == g["home_score"]):
                half_str = "Top" if g["top_half"] else "Bottom"
                if g["inning"] - 1 not in g["line_score"]["away"]:
                    g["line_score"]["away"][g["inning"]-1] = 0
                    g["line_score"]["home"][g["inning"]-1] = 0

                while g["outs"] < 3:
                    if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]: break
                    run_baseball_engine_iteration(g, 1.02, park_data, home_team, away_team)

                    inn_headers = "".join([f"<th style='padding:6px; border:1px solid #444; width:25px;'>{i+1}</th>" for i in range(max(9, g['inning']))])
                    def build_row_cells(team_key):
                        cells = ""
                        for i in range(max(9, g['inning'])):
                            val = g["line_score"][team_key].get(i, "-")
                            if val == "-" and i < g["inning"] - 1: val = 0
                            cells += f"<td style='padding:6px; border:1px solid #444; text-align:center;'>{val}</td>"
                        return cells

                    html_scoreboard = f"""
                    <div style="background-color:#111622; border-radius:8px; padding:12px; margin-bottom:15px; border:1px solid #2d3748; font-family:monospace;">
                        <table style="width:100%; border-collapse: collapse; color: white; font-size:14px;">
                            <thead>
                                <tr style="background-color:#1e293b;">
                                    <th style="text-align:left; padding:6px; width:150px;">TEAM</th>{inn_headers}
                                    <th style="padding:6px; border-left:2px solid #444; background:#0f172a; width:35px;">R</th>
                                    <th style="padding:6px; width:35px;">H</th>
                                    <th style="padding:6px; width:35px;">E</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr><td>⚾ {away_team[:15]}</td>{build_row_cells("away")}<td style="color:#38bdf8; text-align:center; background:#1e293b;">{g['away_score']}</td><td style="text-align:center;">{g['away_hits']}</td><td style="color:#f87171; text-align:center;">{g['away_errors']}</td></tr>
                                <tr><td>🏠 {home_team[:15]}</td>{build_row_cells("home")}<td style="color:#38bdf8; text-align:center; background:#1e293b;">{g['home_score']}</td><td style="text-align:center;">{g['home_hits']}</td><td style="color:#f87171; text-align:center;">{g['home_errors']}</td></tr>
                            </tbody>
                        </table>
                    </div>
                    """
                    line_score_placeholder.markdown(html_scoreboard, unsafe_allow_html=True)

                    b1 = "🟥" if g["bases"][0] else "⬜"
                    b2 = "🟥" if g["bases"][1] else "⬜"
                    b3 = "🟥" if g["bases"][2] else "⬜"
                    field_viz.markdown(f"<pre style='font-size:15px;'>       [{b2}] 2nd\n3rd [{b3}]     [{b1}] 1st\n       [🏃] Home</pre>", unsafe_allow_html=True)
                    
                    staff_viz.markdown(f"**Inning:** `{half_str} {g['inning']}` | **Outs:** `{g['outs']}`\n\n`{g['away_p_name']}` Pitches: `{g['away_p_pitches']}` | Ks: `{g['home_pitcher_k_count']}`\n\n`{g['home_p_name']}` Pitches: `{g['home_p_pitches']}` | Ks: `{g['away_pitcher_k_count']}`")
                    ticker.markdown("\n\n".join(g["logs"][-3:]))
                    
                    away_box_display.dataframe(pd.DataFrame.from_dict(g["away_box"], orient="index"))
                    home_box_display.dataframe(pd.DataFrame.from_dict(g["home_box"], orient="index"))
                    
                    current_h_prob = g["win_prob_history"][-1] / 100.0
                    home_ml = convert_prob_to_american_moneyline(current_h_prob)
                    away_ml = convert_prob_to_american_moneyline(1.0 - current_h_prob)
                    
                    chart_placeholder.line_chart(pd.DataFrame(g["win_prob_history"], columns=["Home Team Win Probability %"]))
                    
                    odds_metrics_placeholder.markdown(f"""
                    * **{home_team} (Home Moneyline):** `{home_ml}`
                    * **{away_team} (Away Moneyline):** `{away_ml}`
                    * **Pitcher Strikeout Props Status:**
                        * *{g['away_p_name']}* O/U Line: `5.5` | Current Total: **{g['home_pitcher_k_count']}**
                        * *{g['home_p_name']}* O/U Line: `5.5` | Current Total: **{g['away_pitcher_k_count']}**
                    """)

                    render_vegas_projection_matrix(g["away_box"], away_team, vegas_away_placeholder)
                    render_vegas_projection_matrix(g["home_box"], home_team, vegas_home_placeholder)

                    if sim_speed > 0: time.sleep(sim_speed)

                g["outs"] = 0; g["bases"] = [None, None, None]; g["away_base_speeds"] = {}; g["home_base_speeds"] = {}
                g["top_half"] = not g["top_half"]
                if g["top_half"]: g["inning"] += 1

            st.success(f"### 🏆 Game Complete.")
            st.session_state["game_active"] = False
            st.session_state["leveraged_game_state"] = None

    # ----------------------------------------------------
    # MODE B: POSTSEASON BACKGROUND SIMULATOR SERIES MODE
    # ----------------------------------------------------
    else:
        st.write("---")
        if st.button(f"⚡ Execute Postseason {series_length}-Game Series Engine Block", use_container_width=True, type="primary"):
            away_series_wins, home_series_wins, game_number = 0, 0, 1
            needed_wins = (series_length // 2) + 1
            
            series_away_box = {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in away_lineup_final["Player"]}
            series_home_box = {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in home_lineup_final["Player"]}
            
            while away_series_wins < needed_wins and home_series_wins < needed_wins:
                bg = {
                    "inning": 1, "top_half": True, "away_score": 0, "home_score": 0, "away_hits": 0, "home_hits": 0, "away_errors": 0, "home_errors": 0,
                    "away_idx": 0, "home_idx": 0, "outs": 0, "bases": [None, None, None], "line_score": {"away": {}, "home": {}}, "logs": [],
                    "away_box": {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in away_lineup_final["Player"]},
                    "home_box": {p: {"AB": 0, "H": 0, "1B": 0, "2B": 0, "HR": 0, "RBI": 0, "BB": 0, "DK_PTS": 0.0, "HRR_VAL": 0.0, "TOTAL_BASES": 0.0} for p in home_lineup_final["Player"]},
                    "away_base_speeds": {}, "home_base_speeds": {},
                    "away_p_name": away_pitcher_active['Player'], "away_p_era": float(away_pitcher_active['ERA']), "away_p_pitches": 0, "away_p_type": "SP", "away_p_throws": away_pitcher_active.get("Throws", "R"),
                    "home_p_name": home_pitcher_active['Player'], "home_p_era": float(home_pitcher_active['ERA']), "home_p_pitches": 0, "home_p_type": "SP", "home_p_throws": home_pitcher_active.get("Throws", "R"),
                    "away_p_era_v_lhb": float(away_pitcher_active.get("ERA_v_LHB", away_pitcher_active['ERA'])),
                    "away_p_era_v_rhb": float(away_pitcher_active.get("ERA_v_RHB", away_pitcher_active['ERA'])),
                    "home_p_era_v_lhb": float(home_pitcher_active.get("ERA_v_LHB", home_pitcher_active['ERA'])),
                    "home_p_era_v_rhb": float(home_pitcher_active.get("ERA_v_RHB", home_pitcher_active['ERA'])),
                    "away_bullpen_list": list(st.session_state["away_bullpen"]),
                    "home_bullpen_list": list(st.session_state["home_bullpen"]),
                    "away_pitcher_k_count": 0, "home_pitcher_k_count": 0, "win_prob_history": [50.0]
                }
                park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)
                
                while bg["inning"] <= 9 or (bg["away_score"] == bg["home_score"]):
                    while bg["outs"] < 3:
                        if bg["inning"] >= 9 and not bg["top_half"] and bg["home_score"] > bg["away_score"]: break
                        run_baseball_engine_iteration(bg, 1.00, park_data, home_team, away_team)
                    bg["outs"] = 0; bg["bases"] = [None, None, None]; bg["away_base_speeds"] = {}; bg["home_base_speeds"] = {}
                    bg["top_half"] = not bg["top_half"]
                    if bg["top_half"]: bg["inning"] += 1
                
                for p in series_away_box:
                    for key in ["AB","H","1B","2B","HR","RBI","BB","DK_PTS","HRR_VAL","TOTAL_BASES"]: series_away_box[p][key] += bg["away_box"][p][key]
                for p in series_home_box:
                    for key in ["AB","H","1B","2B","HR","RBI","BB","DK_PTS","HRR_VAL","TOTAL_BASES"]: series_home_box[p][key] += bg["home_box"][p][key]

                if bg["home_score"] > bg["away_score"]: home_series_wins += 1
                else: away_series_wins += 1
                game_number += 1
            
            st.info(f"### Playoff Series Concluded! {away_team}: {away_series_wins} Wins | {home_team}: {home_series_wins} Wins")
            render_vegas_projection_matrix(series_away_box, f"{away_team} Accumulated Stats")
            render_vegas_projection_matrix(series_home_box, f"{home_team} Accumulated Stats")
