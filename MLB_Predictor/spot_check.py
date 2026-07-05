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
                    players_list.append({
                        "Player": name, "Pos": pos, "Bats": person.get('batSide', {}).get('code', 'R'),
                        "AVG": float(stat.get("avg", ".000")), "OPS": float(stat.get("ops", ".000")),
                        "H": int(stat.get("hits", 0)), "HR": int(stat.get("homeRuns", 0)),
                        "RBI": int(stat.get("rbi", 0)), "BB": int(stat.get("baseOnBalls", 0)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "AB": int(stat.get("atBats", 1))
                    })
                elif stat_group == "pitching":
                    players_list.append({
                        "Player": name, "Pos": pos, "Throws": person.get('pitchHand', {}).get('code', 'R'),
                        "ERA": float(stat.get("era", 4.50)), "WHIP": float(stat.get("whip", 1.30)),
                        "SO (K)": int(stat.get("strikeOuts", 0)), "IP": stat.get("inningsPitched", "0.0")
                    })
    except: pass
    if not players_list:
        if stat_group == "hitting":
            return pd.DataFrame([{"Player": f"Batter {i+1}", "Pos": "OF", "Bats": random.choice(["R","L"]), "AVG": 0.260, "OPS": 0.750, "HR": random.randint(0,20), "AB": 300} for i in range(12)])
        else:
            return pd.DataFrame([{"Player": f"Pitcher {i+1}", "Pos": random.choice(["SP","RP"]), "Throws": random.choice(["R","L"]), "ERA": 4.10, "WHIP": 1.28, "SO (K)": 70, "IP": "80.0"} for i in range(7)])
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
        """Calculates a live home-team win probability vector baseline based on current game state context."""
        base = 0.50
        run_diff = g["home_score"] - g["away_score"]
        base += run_diff * 0.12
        
        # Inning leverage escalation multiplier
        progress = (g["inning"] - 1) / 9.0
        if not g["top_half"]: progress += 0.05
        
        base += (run_diff * 0.05) * progress
        
        # Base occupancy impacts
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
        if not g.get("away_bullpen_list"):
            g["away_bullpen_list"] = [{"Player": f"Reliever A{i}", "ERA": 4.00, "Throws": "R", "Pos": "RP"} for i in range(5)]
        if not g.get("home_bullpen_list"):
            g["home_bullpen_list"] = [{"Player": f"Reliever H{i}", "ERA": 4.00, "Throws": "R", "Pos": "RP"} for i in range(5)]

        if g["top_half"]:
            g["home_p_pitches"] += random.randint(3, 6)
            is_high_leverage_closer_situation = (g["inning"] >= 9 and 1 <= (g["away_score"] - g["home_score"]) <= 3)
            if (g["home_p_pitches"] > 85 or is_high_leverage_closer_situation) and g["home_p_type"] == "SP":
                if len(g["home_bullpen_list"]) > 0:
                    reliever = g["home_bullpen_list"].pop(0)
                    g["home_p_name"] = reliever["Player"]
                    g["home_p_era"] = float(reliever["ERA"])
                    g["home_p_throws"] = reliever.get("Throws", "R")
                    g["home_p_pitches"] = 0
                    g["home_p_type"] = "RP"
            p_name, p_era, p_pitches, p_throws = g["home_p_name"], g["home_p_era"], g["home_p_pitches"], g.get("home_p_throws", "R")
            batter = away_lineup_final.iloc[g["away_idx"] % 9]
            b_team, opp_team = "away", "home"
        else:
            g["away_p_pitches"] += random.randint(3, 6)
            is_high_leverage_closer_situation = (g["inning"] >= 9 and 1 <= (g["home_score"] - g["away_score"]) <= 3)
            if (g["away_p_pitches"] > 85 or is_high_leverage_closer_situation) and g["away_p_type"] == "SP":
                if len(g["away_bullpen_list"]) > 0:
                    reliever = g["away_bullpen_list"].pop(0)
                    g["away_p_name"] = reliever["Player"]
                    g["away_p_era"] = float(reliever["ERA"])
                    g["away_p_throws"] = reliever.get("Throws", "R")
                    g["away_p_pitches"] = 0
                    g["away_p_type"] = "RP"
            p_name, p_era, p_pitches, p_throws = g["away_p_name"], g["away_p_era"], g["away_p_pitches"], g.get("away_p_throws", "R")
            batter = home_lineup_final.iloc[g["home_idx"] % 9]
            b_team, opp_team = "home", "away"

        platoon_modifier = 1.0
        b_bats = batter.get("Bats", "R")
        if b_bats == "L" and p_throws == "L": platoon_modifier = 0.90
        elif b_bats == "R" and p_throws == "R": platoon_modifier = 0.94
        elif (b_bats == "L" and p_throws == "R") or (b_bats == "R" and p_throws == "L"): platoon_modifier = 1.08

        effective_era = p_era * (1.25 if (p_pitches > 80 and g[f"{opp_team}_p_type"] == "SP") else 1.0)
        
        bb_chance = 0.08 * (effective_era / 4.0)
        if random.uniform(0, 1) < bb_chance:
            g[f"{b_team}_box"][batter["Player"]]["BB"] += 1
            g["logs"].append(f"🟢 **Walk!** {batter['Player']} draws a walk.")
            if g["bases"][0]:
                if g["bases"][1]:
                    if g["bases"][2]:
                        g[f"{b_team}_score"] += 1
                        g
