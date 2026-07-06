import streamlit as st
import numpy as np
import pandas as pd
import random
import time
import copy

st.set_page_config(page_title="Ultimate MLB Analytics Platform v2", page_icon="⚾", layout="wide")

# ----------------------------------------------------
# SYSTEM STATE PERSISTENCE & GLOBAL RESET HANDLERS
# ----------------------------------------------------
if "lineups_locked" not in st.session_state:
    st.session_state["lineups_locked"] = False
if "monte_carlo_results" not in st.session_state:
    st.session_state["monte_carlo_results"] = None
# TRACKING KEY: Used to force Streamlit to completely recreate widget instances
if "away_generation_id" not in st.session_state:
    st.session_state["away_generation_id"] = str(random.randint(1000, 9999))
if "home_generation_id" not in st.session_state:
    st.session_state["home_generation_id"] = str(random.randint(1000, 9999))

def reset_away_framework():
    """Forces an explicit generation update to completely wipe old widget indexes"""
    st.session_state["lineups_locked"] = False
    st.session_state["monte_carlo_results"] = None
    st.session_state["away_generation_id"] = str(random.randint(1000, 9999))
    st.rerun()

def reset_home_framework():
    """Forces an explicit generation update to completely wipe old widget indexes"""
    st.session_state["lineups_locked"] = False
    st.session_state["monte_carlo_results"] = None
    st.session_state["home_generation_id"] = str(random.randint(1000, 9999))
    st.rerun()

def global_unlock_reset():
    """Fallback structural unlock resetting engine"""
    st.session_state["lineups_locked"] = False
    st.session_state["monte_carlo_results"] = None

# Global Placeholders to definitively stop Streamlit KeyError race-conditions
if "locked_away_sp" not in st.session_state: st.session_state["locked_away_sp"] = {}
if "locked_home_sp" not in st.session_state: st.session_state["locked_home_sp"] = {}
if "locked_away_lineup" not in st.session_state: st.session_state["locked_away_lineup"] = []
if "locked_home_lineup" not in st.session_state: st.session_state["locked_home_lineup"] = []
if "locked_away_bullpen" not in st.session_state: st.session_state["locked_away_bullpen"] = []
if "locked_home_bullpen" not in st.session_state: st.session_state["locked_home_bullpen"] = []

# ----------------------------------------------------
# ADVANCED BASELINE CONFIGURATIONS & HISTORICAL COHORTS
# ----------------------------------------------------
LEAGUE_BASELINE = {
    "AVG": 0.244, "OBP": 0.315, "SLG": 0.402, "BABIP": 0.290,
    "BB_RATE": 0.085, "K_RATE": 0.225, "HR_PA_RATE": 0.030,
    "1B_H_RATE": 0.635, "2B_H_RATE": 0.210, "3B_H_RATE": 0.015, "HR_H_RATE": 0.140
}

ROSTER_DATABASE = {
    "Athletics": {
        "primary": "#003831", "secondary": "#EFB21E",
        "hitting": [
            {"Player": "Nick Kurtz", "Pos": "1B", "Bats": "L", "BB_RATE": 0.135, "K_RATE": 0.210, "HR_PA_RATE": 0.045, "BABIP": 0.315, "1B_H_RATE": 0.58, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 65, "PA": 450},
            {"Player": "Shea Langeliers", "Pos": "C", "Bats": "R", "BB_RATE": 0.082, "K_RATE": 0.255, "HR_PA_RATE": 0.052, "BABIP": 0.270, "1B_H_RATE": 0.52, "2B_H_RATE": 0.20, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 55, "PA": 510},
            {"Player": "Brent Rooker", "Pos": "DH", "Bats": "R", "BB_RATE": 0.112, "K_RATE": 0.285, "HR_PA_RATE": 0.065, "BABIP": 0.340, "1B_H_RATE": 0.48, "2B_H_RATE": 0.23, "3B_H_RATE": 0.01, "HR_H_RATE": 0.28, "SPD": 58, "PA": 580},
            {"Player": "Lawrence Butler", "Pos": "RF", "Bats": "L", "BB_RATE": 0.091, "K_RATE": 0.240, "HR_PA_RATE": 0.042, "BABIP": 0.320, "1B_H_RATE": 0.60, "2B_H_RATE": 0.22, "3B_H_RATE": 0.03, "HR_H_RATE": 0.15, "SPD": 82, "PA": 480},
            {"Player": "Zack Gelof", "Pos": "2B", "Bats": "R", "BB_RATE": 0.088, "K_RATE": 0.290, "HR_PA_RATE": 0.038, "BABIP": 0.305, "1B_H_RATE": 0.59, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.15, "SPD": 85, "PA": 540},
            {"Player": "Jonah Heim", "Pos": "C", "Bats": "B", "BB_RATE": 0.075, "K_RATE": 0.195, "HR_PA_RATE": 0.028, "BABIP": 0.280, "1B_H_RATE": 0.65, "2B_H_RATE": 0.22, "3B_H_RATE": 0.00, "HR_H_RATE": 0.13, "SPD": 45, "PA": 420},
            {"Player": "Alika Williams", "Pos": "SS", "Bats": "R", "BB_RATE": 0.060, "K_RATE": 0.220, "HR_PA_RATE": 0.010, "BABIP": 0.295, "1B_H_RATE": 0.78, "2B_H_RATE": 0.16, "3B_H_RATE": 0.04, "HR_H_RATE": 0.02, "SPD": 78, "PA": 280},
            {"Player": "Henry Bolte", "Pos": "LF", "Bats": "R", "BB_RATE": 0.105, "K_RATE": 0.310, "HR_PA_RATE": 0.040, "BABIP": 0.330, "1B_H_RATE": 0.55, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.18, "SPD": 88, "PA": 310},
            {"Player": "Brian Serven", "Pos": "C", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.250, "HR_PA_RATE": 0.012, "BABIP": 0.260, "1B_H_RATE": 0.75, "2B_H_RATE": 0.18, "3B_H_RATE": 0.01, "HR_H_RATE": 0.06, "SPD": 40, "PA": 150}
        ],
        "pitching": [
            {"Player": "Mason Miller", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.385, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.265, "OAVG": 0.185, "IP": "75.0", "ERA": 2.10, "Fatigue": 0.0},
            {"Player": "JP Sears", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.072, "K_ALLOWED_RATE": 0.210, "HR_PA_ALLOWED_RATE": 0.038, "BABIP_ALLOWED": 0.290, "OAVG": 0.245, "IP": "175.1", "ERA": 4.25, "Fatigue": 0.0},
            {"Player": "Lucas Erceg", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.270, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.285, "OAVG": 0.220, "IP": "65.0", "ERA": 3.15, "Fatigue": 0.0},
            {"Player": "Tyler Ferguson", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.090, "K_ALLOWED_RATE": 0.260, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.275, "OAVG": 0.225, "IP": "55.0", "ERA": 3.40, "Fatigue": 0.0}
        ]
    },
    "Baltimore Orioles": {
        "primary": "#DF4618", "secondary": "#000000",
        "hitting": [
            {"Player": "Adley Rutschman", "Pos": "C", "Bats": "B", "BB_RATE": 0.110, "K_RATE": 0.155, "HR_PA_RATE": 0.035, "BABIP": 0.295, "1B_H_RATE": 0.64, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.13, "SPD": 50, "PA": 650},
            {"Player": "Gunnar Henderson", "Pos": "SS", "Bats": "L", "BB_RATE": 0.125, "K_RATE": 0.220, "HR_PA_RATE": 0.058, "BABIP": 0.335, "1B_H_RATE": 0.54, "2B_H_RATE": 0.24, "3B_H_RATE": 0.04, "HR_H_RATE": 0.18, "SPD": 86, "PA": 680},
            {"Player": "Anthony Santander", "Pos": "RF", "Bats": "B", "BB_RATE": 0.085, "K_RATE": 0.190, "HR_PA_RATE": 0.062, "BABIP": 0.265, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 48, "PA": 640},
            {"Player": "Jordan Westburg", "Pos": "3B", "Bats": "R", "BB_RATE": 0.078, "K_RATE": 0.225, "HR_PA_RATE": 0.038, "BABIP": 0.325, "1B_H_RATE": 0.58, "2B_H_RATE": 0.25, "3B_H_RATE": 0.03, "HR_H_RATE": 0.14, "SPD": 76, "PA": 550},
            {"Player": "Ryan Mountcastle", "Pos": "1B", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.225, "HR_PA_RATE": 0.035, "BABIP": 0.330, "1B_H_RATE": 0.60, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 60, "PA": 520},
            {"Player": "Colton Cowser", "Pos": "LF", "Bats": "L", "BB_RATE": 0.102, "K_RATE": 0.285, "HR_PA_RATE": 0.045, "BABIP": 0.310, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 80, "PA": 500},
            {"Player": "Cedric Mullins", "Pos": "CF", "Bats": "L", "BB_RATE": 0.088, "K_RATE": 0.215, "HR_PA_RATE": 0.032, "BABIP": 0.285, "1B_H_RATE": 0.62, "2B_H_RATE": 0.20, "3B_H_RATE": 0.03, "HR_H_RATE": 0.15, "SPD": 88, "PA": 480},
            {"Player": "Leody Taveras", "Pos": "CF", "Bats": "B", "BB_RATE": 0.070, "K_RATE": 0.210, "HR_PA_RATE": 0.022, "BABIP": 0.300, "1B_H_RATE": 0.68, "2B_H_RATE": 0.20, "3B_H_RATE": 0.02, "HR_H_RATE": 0.10, "SPD": 84, "PA": 410},
            {"Player": "Jackson Holliday", "Pos": "2B", "Bats": "L", "BB_RATE": 0.115, "K_RATE": 0.260, "HR_PA_RATE": 0.030, "BABIP": 0.315, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.03, "HR_H_RATE": 0.13, "SPD": 82, "PA": 460}
        ],
        "pitching": [
            {"Player": "Corbin Burnes", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.250, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.280, "OAVG": 0.215, "IP": "194.1", "ERA": 2.95, "Fatigue": 0.0},
            {"Player": "Grayson Rodriguez", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.265, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.295, "OAVG": 0.230, "IP": "162.0", "ERA": 3.80, "Fatigue": 0.0},
            {"Player": "Yennier Cano", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.060, "K_ALLOWED_RATE": 0.230, "HR_PA_ALLOWED_RATE": 0.015, "BABIP_ALLOWED": 0.290, "OAVG": 0.225, "IP": "70.0", "ERA": 2.85, "Fatigue": 0.0},
            {"Player": "Seranthony Dominguez", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.095, "K_ALLOWED_RATE": 0.275, "HR_PA_ALLOWED_RATE": 0.030, "BABIP_ALLOWED": 0.280, "OAVG": 0.218, "IP": "60.0", "ERA": 3.60, "Fatigue": 0.0}
        ]
    }
}

BALLPARK_ENV = {
    "Athletics": {"run_mult": 0.95, "hr_mult": 0.88, "babip_mult": 0.98},
    "Baltimore Orioles": {"run_mult": 1.02, "hr_mult": 0.95, "babip_mult": 1.01}
}

# ----------------------------------------------------
# LOG-ODDS ALGORITHMIC MATRIX
# ----------------------------------------------------
def calculate_log_odds(player_rate, pitcher_rate, league_rate):
    player_rate = max(0.001, min(0.999, player_rate))
    pitcher_rate = max(0.001, min(0.999, pitcher_rate))
    league_rate = max(0.001, min(0.999, league_rate))
    
    odds_b = player_rate / (1.0 - player_rate)
    odds_p = pitcher_rate / (1.0 - pitcher_rate)
    odds_l = league_rate / (1.0 - league_rate)
    
    final_odds = (odds_b * odds_p) / odds_l
    return final_odds / (1.0 + final_odds)

def safe_extract_player(roster_dict, side, player_name, fallback_idx=0):
    pool = roster_dict.get(side, [])
    if not pool:
        return {}
    matched = [p for p in pool if p["Player"] == player_name]
    if matched:
        return copy.deepcopy(matched[0])
    return copy.deepcopy(pool[min(fallback_idx, len(pool) - 1)])

# ----------------------------------------------------
# CONTROL BOARD INTERFACE UI
# ----------------------------------------------------
st.sidebar.header("⚾ Enterprise Simulator Panel")
all_teams_list = list(ROSTER_DATABASE.keys())

away_selection = st.sidebar.selectbox(
    "Away Roster Array", 
    all_teams_list, 
    index=0, 
    key="away_team_widget",
    on_change=reset_away_framework
)

home_selection = st.sidebar.selectbox(
    "Home Roster Array", 
    all_teams_list, 
    index=1, 
    key="home_team_widget",
    on_change=reset_home_framework
)

st.sidebar.markdown("### ☁️ Environmental Weather Tensors")
temperature = st.sidebar.slider("Ambient Temperature (°F)", 40, 105, 73, step=1)
stadium_alt = st.sidebar.slider("Stadium Elevation (Feet)", 0, 5280, 400, step=100)
wind_vector = st.sidebar.selectbox("Wind Spatial Direction", ["Calm / Neutral", "Blowing In (Deadened)", "Blowing Out (Boosted)"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏛️ Vegas Consensus Line Input")
vegas_line_input = st.sidebar.number_input("Market Closing Moneyline (Home Team)", value=-110, step=5)
playback_speed = st.sidebar.slider("Simulation Step Intercept Delay", 0.00, 0.50, 0.02, step=0.01)

away_h_pool = ROSTER_DATABASE[away_selection]["hitting"]
home_h_pool = ROSTER_DATABASE[home_selection]["hitting"]
away_p_pool = ROSTER_DATABASE[away_selection]["pitching"]
home_p_pool = ROSTER_DATABASE[home_selection]["pitching"]

# ----------------------------------------------------
# VIEW ROUTER RENDER SEPARATION
# ----------------------------------------------------
if not st.session_state["lineups_locked"]:
    st.subheader("📋 Core Lineup Configuration Ingestion")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### {away_selection} Lineup Assets")
        # Unique keys incorporating the away generation string force complete structural remounting
        sp_choice_a = st.selectbox("Starting Pitcher Choice (Away)", [p["Player"] for p in away_p_pool if p["Role"] == "SP"], key=f"sp_away_{away_selection}_{st.session_state['away_generation_id']}")
        batters_a = []
        for i in range(9):
            default_idx = min(i, len(away_h_pool)-1)
            b = st.selectbox(f"Away Slot {i+1} Batter", [p["Player"] for p in away_h_pool], index=default_idx, key=f"a_slot_{away_selection}_{i}_{st.session_state['away_generation_id']}")
            batters_a.append(b)
            
    with col2:
        st.markdown(f"#### {home_selection} Lineup Assets")
        sp_choice_h = st.selectbox("Starting Pitcher Choice (Home)", [p["Player"] for p in home_p_pool if p["Role"] == "SP"], key=f"sp_home_{home_selection}_{st.session_state['home_generation_id']}")
        batters_h = []
        for i in range(9):
            default_idx = min(i, len(home_h_pool)-1)
            b = st.selectbox(f"Home Slot {i+1} Batter", [p["Player"] for p in home_h_pool], index=default_idx, key=f"h_slot_{home_selection}_{i}_{st.session_state['home_generation_id']}")
            batters_h.append(b)
            
    if st.button("🔒 Lock Framework Configurations & Generate Ecosystem Data", use_container_width=True):
        st.session_state["locked_away_sp"] = safe_extract_player(ROSTER_DATABASE[away_selection], "pitching", sp_choice_a, 0)
        st.session_state["locked_home_sp"] = safe_extract_player(ROSTER_DATABASE[home_selection], "pitching", sp_choice_h, 0)
        
        st.session_state["locked_away_lineup"] = [safe_extract_player(ROSTER_DATABASE[away_selection], "hitting", b, idx) for idx, b in enumerate(batters_a)]
        st.session_state["locked_home_lineup"] = [safe_extract_player(ROSTER_DATABASE[home_selection], "hitting", b, idx) for idx, b in enumerate(batters_h)]
        
        st.session_state["locked_away_bullpen"] = [p for p in away_p_pool if p["Player"] != sp_choice_a]
        st.session_state["locked_home_bullpen"] = [p for p in home_p_pool if p["Player"] != sp_choice_h]
        
        st.session_state["lineups_locked"] = True
        st.session_state["monte_carlo_results"] = None
        st.rerun()
else:
    st.sidebar.button("🔓 Release Lock System", on_click=global_unlock_reset, use_container_width=True)

    # ----------------------------------------------------
    # ADVANCED QUANT MODULE: 24-STATE MARKOV SIMULATION ENGINE
    # ----------------------------------------------------
    class DipsMarkovEngine:
        def __init__(self, away_lineup, home_lineup, away_sp, home_sp, away_bp, home_bp, park_rules, env_tensors):
            self.away_lineup = away_lineup
            self.home_lineup = home_lineup
            self.away_sp = away_sp
            self.home_sp = home_sp
            self.away_bp = copy.deepcopy(away_bp)
            self.home_bp = copy.deepcopy(home_bp)
            self.park = park_rules
            self.env = env_tensors
            
        def execute_matchup_vector(self, batter, pitcher, order_cycle):
            is_platoon = (batter["Bats"] == "L" and pitcher["Throws"] == "R") or (batter["Bats"] == "R" and pitcher["Throws"] == "L")
            platoon_mult = 1.07 if is_platoon else 0.93
            
            fatigue_penalty = 1.0 + (pitcher.get("Fatigue", 0.0) * 0.35)
            ttop_mult = 1.0 + ((order_cycle - 1) * 0.06) if pitcher["Role"] == "SP" else 1.0
            
            temp_density_scalar = 1.0 + ((self.env["temp"] - 72) * 0.0012)
            elevation_scalar = 1.0 + (self.env["elevation"] / 5280 * 0.05)
            wind_scalar = 1.10 if self.env["wind"] == "Blowing Out (Boosted)" else (0.90 if self.env["wind"] == "Blowing In (Deadened)" else 1.0)

            bb_prob = calculate_log_odds(batter["BB_RATE"], pitcher["BB_ALLOWED_RATE"] * ttop_mult * fatigue_penalty, LEAGUE_BASELINE["BB_RATE"])
            k_prob = calculate_log_odds(batter["K_RATE"], pitcher["K_ALLOWED_RATE"] * ttop_mult * fatigue_penalty, LEAGUE_BASELINE["K_RATE"])
            
            hr_base = calculate_log_odds(batter["HR_PA_RATE"], pitcher["HR_PA_ALLOWED_RATE"] * ttop_mult * fatigue_penalty, LEAGUE_BASELINE["HR_PA_RATE"])
            hr_prob = hr_base * self.park["hr_mult"] * temp_density_scalar * elevation_scalar * wind_scalar
            
            sum_isolated = bb_prob + k_prob + hr_prob
            if sum_isolated >= 0.95:
                scale = 0.95 / sum_isolated
                bb_prob *= scale; k_prob *= scale; hr_prob *= scale
                
            remainder = 1.0 - (bb_prob + k_prob + hr_prob)
            babip_matchup = calculate_log_odds(batter["BABIP"] * platoon_mult, pitcher["BABIP_ALLOWED"] * fatigue_penalty, LEAGUE_BASELINE["BABIP"]) * self.park["babip_mult"]
            
            hit_in_play_prob = remainder * babip_matchup
            out_in_play_prob = remainder - hit_in_play_prob
            
            return {
                "BB": bb_prob, "K": k_prob, "HR": hr_prob,
                "1B": hit_in_play_prob * 0.65, "2B": hit_in_play_prob * 0.21,
                "3B": hit_in_play_prob * 0.02, "OUT": out_in_play_prob
            }

        def step_markov_24_state(self, state, outcome, runner_spd):
            outs = state["outs"]
            bases = list(state["bases"])
            runs_scored = 0
            event_log = ""
            
            if outcome in ["K", "OUT"]:
                outs += 1
                return outs, bases, 0, "Strikeout" if outcome == "K" else "Fielded Out"
                
            if outcome == "BB":
                if not bases[0]: bases[0] = True
                elif not bases[1]: bases[1] = True
                elif not bases[2]: bases[2] = True
                else: runs_scored += 1
                return outs, bases, runs_scored, "Base on Balls"

            if outcome == "HR":
                runs_scored = 1 + sum(1 for b in bases if b)
                return outs, [False, False, False], runs_scored, f"Home Run ({runs_scored} Run Shot)"

            spd_factor = runner_spd / 100.0
            if outcome == "1B":
                new_bases = [True, False, False]
                if bases[2]: runs_scored += 1
                if bases[1]:
                    if spd_factor > 0.68 or random.random() < 0.45: runs_scored += 1
                    else: new_bases[2] = True
                if bases[0]: new_bases[1] = True
                bases = new_bases
                event_log = "Single"
            elif outcome == "2B":
                new_bases = [False, True, False]
                if bases[2]: runs_scored += 1
                if bases[1]: runs_scored += 1
                if bases[0]:
                    if spd_factor > 0.65: runs_scored += 1
                    else: new_bases[2] = True
                bases = new_bases
                event_log = "Double"
            elif outcome == "3B":
                runs_scored = sum(1 for b in bases if b)
                bases = [False, False, True]
                event_log = "Triple"
                
            return outs, bases, runs_scored, event_log

        def run_full_game(self, tracking_mode=False):
            g = {
                "inning": 1, "top_half": True, "away_score": 0, "home_score": 0,
                "away_lineup_idx": 0, "home_lineup_idx": 0,
                "away_p": copy.deepcopy(self.away_sp), "home_p": copy.deepcopy(self.home_sp),
                "away_pitches": 0, "home_pitches": 0,
                "box_scores": {
                    "away": {p["Player"]: {"AB":0,"H":0,"1B":0,"2B":0,"3B":0,"HR":0,"BB":0,"RBI":0,"K":0} for p in self.away_lineup},
                    "home": {p["Player"]: {"AB":0,"H":0,"1B":0,"2B":0,"3B":0,"HR":0,"BB":0,"RBI":0,"K":0} for p in self.home_lineup}
                },
                "log_history": [], "win_prob_history": [50.0]
            }
            
            while g["inning"] <= 9 or (g["away_score"] == g["home_score"]):
                if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]:
                    break
                
                if g["top_half"] and ((g["home_pitches"] > 95 and g["home_p"]["Role"] == "SP") or g["home_pitches"] > 30):
                    if self.home_bp: g["home_p"] = self.home_bp.pop(0); g["home_pitches"] = 0
                elif not g["top_half"] and ((g["away_pitches"] > 95 and g
