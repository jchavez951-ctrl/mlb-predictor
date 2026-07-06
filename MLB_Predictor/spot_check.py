import streamlit as st
import requests
import random
import time
import pandas as pd
import numpy as np
import copy

st.set_page_config(page_title="Institutional MLB Quant Engine", page_icon="⚾", layout="wide")

# ----------------------------------------------------
# SYSTEM STATE PERSISTENCE
# ----------------------------------------------------
if "lineups_locked" not in st.session_state:
    st.session_state["lineups_locked"] = False
if "game_active" not in st.session_state:
    st.session_state["game_active"] = False
if "monte_carlo_results" not in st.session_state:
    st.session_state["monte_carlo_results"] = None

# ----------------------------------------------------
# ADVANCED BASELINE CONFIGURATIONS & HISTORICAL COHORTS
# ----------------------------------------------------
LEAGUE_BASELINE = {
    "AVG": 0.244, "OBP": 0.315, "SLG": 0.402, "BABIP": 0.290,
    "BB_RATE": 0.085, "K_RATE": 0.225, "HR_PA_RATE": 0.030,
    "1B_H_RATE": 0.635, "2B_H_RATE": 0.210, "3B_H_RATE": 0.015, "HR_H_RATE": 0.140
}

RETRO_TEAMS = {
    "1927 New York Yankees": {
        "primary": "#0C2340", "secondary": "#C4CED4",
        "hitting": [
            {"Player": "Earle Combs", "Pos": "CF", "Bats": "L", "BB_RATE": 0.095, "K_RATE": 0.048, "HR_PA_RATE": 0.008, "BABIP": 0.354, "1B_H_RATE": 0.720, "2B_H_RATE": 0.160, "3B_H_RATE": 0.090, "HR_H_RATE": 0.030, "SPD": 88, "PA": 710},
            {"Player": "Mark Koenig", "Pos": "SS", "Bats": "B", "BB_RATE": 0.039, "K_RATE": 0.075, "HR_PA_RATE": 0.005, "BABIP": 0.297, "1B_H_RATE": 0.770, "2B_H_RATE": 0.140, "3B_H_RATE": 0.075, "HR_H_RATE": 0.015, "SPD": 75, "PA": 650},
            {"Player": "Babe Ruth", "Pos": "RF", "Bats": "L", "BB_RATE": 0.198, "K_RATE": 0.129, "HR_PA_RATE": 0.087, "BABIP": 0.345, "1B_H_RATE": 0.450, "2B_H_RATE": 0.150, "3B_H_RATE": 0.040, "HR_H_RATE": 0.360, "SPD": 65, "PA": 691},
            {"Player": "Lou Gehrig", "Pos": "1B", "Bats": "L", "BB_RATE": 0.151, "K_RATE": 0.119, "HR_PA_RATE": 0.065, "BABIP": 0.370, "1B_H_RATE": 0.470, "2B_H_RATE": 0.240, "3B_H_RATE": 0.080, "HR_H_RATE": 0.210, "SPD": 60, "PA": 717},
            {"Player": "Bob Meusel", "Pos": "LF", "Bats": "R", "BB_RATE": 0.066, "K_RATE": 0.098, "HR_PA_RATE": 0.013, "BABIP": 0.346, "1B_H_RATE": 0.650, "2B_H_RATE": 0.220, "3B_H_RATE": 0.050, "HR_H_RATE": 0.080, "SPD": 78, "PA": 615},
            {"Player": "Tony Lazzeri", "Pos": "2B", "Bats": "R", "BB_RATE": 0.106, "K_RATE": 0.134, "HR_PA_RATE": 0.026, "BABIP": 0.329, "1B_H_RATE": 0.610, "2B_H_RATE": 0.170, "3B_H_RATE": 0.050, "HR_H_RATE": 0.170, "SPD": 72, "PA": 642},
            {"Player": "Joe Dugan", "Pos": "3B", "Bats": "R", "BB_RATE": 0.064, "K_RATE": 0.069, "HR_PA_RATE": 0.005, "BABIP": 0.283, "1B_H_RATE": 0.790, "2B_H_RATE": 0.150, "3B_H_RATE": 0.040, "HR_H_RATE": 0.020, "SPD": 55, "PA": 420},
            {"Player": "Pat Collins", "Pos": "C", "Bats": "R", "BB_RATE": 0.155, "K_RATE": 0.141, "HR_PA_RATE": 0.021, "BABIP": 0.298, "1B_H_RATE": 0.580, "2B_H_RATE": 0.200, "3B_H_RATE": 0.020, "HR_H_RATE": 0.200, "SPD": 40, "PA": 330},
            {"Player": "Ray Morehart", "Pos": "IF", "Bats": "L", "BB_RATE": 0.082, "K_RATE": 0.090, "HR_PA_RATE": 0.004, "BABIP": 0.273, "1B_H_RATE": 0.780, "2B_H_RATE": 0.150, "3B_H_RATE": 0.050, "HR_H_RATE": 0.020, "SPD": 68, "PA": 220}
        ],
        "pitching": [
            {"Player": "Waite Hoyt", "Pos": "SP", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.052, "K_ALLOWED_RATE": 0.083, "HR_PA_ALLOWED_RATE": 0.012, "BABIP_ALLOWED": 0.268, "OAVG": 0.222, "IP": "256.2", "ERA": 2.63},
            {"Player": "Herb Pennock", "Pos": "SP", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.050, "K_ALLOWED_RATE": 0.056, "HR_PA_ALLOWED_RATE": 0.015, "BABIP_ALLOWED": 0.272, "OAVG": 0.235, "IP": "209.2", "ERA": 3.00},
            {"Player": "Wilcy Moore", "Pos": "RP", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.062, "K_ALLOWED_RATE": 0.081, "HR_PA_ALLOWED_RATE": 0.009, "BABIP_ALLOWED": 0.258, "OAVG": 0.218, "IP": "213.0", "ERA": 2.28}
        ]
    },
    "2004 Boston Red Sox": {
        "primary": "#BD3039", "secondary": "#0C2340",
        "hitting": [
            {"Player": "Johnny Damon", "Pos": "CF", "Bats": "L", "BB_RATE": 0.108, "K_RATE": 0.102, "HR_PA_RATE": 0.028, "BABIP": 0.324, "1B_H_RATE": 0.630, "2B_H_RATE": 0.210, "3B_H_RATE": 0.030, "HR_H_RATE": 0.130, "SPD": 90, "PA": 711},
            {"Player": "Mark Bellhorn", "Pos": "2B", "Bats": "B", "BB_RATE": 0.142, "K_RATE": 0.284, "HR_PA_RATE": 0.027, "BABIP": 0.331, "1B_H_RATE": 0.540, "2B_H_RATE": 0.270, "3B_H_RATE": 0.020, "HR_H_RATE": 0.170, "SPD": 62, "PA": 605},
            {"Player": "Manny Ramirez", "Pos": "LF", "Bats": "R", "BB_RATE": 0.119, "K_RATE": 0.183, "HR_PA_RATE": 0.063, "BABIP": 0.336, "1B_H_RATE": 0.520, "2B_H_RATE": 0.220, "3B_H_RATE": 0.010, "HR_H_RATE": 0.250, "SPD": 50, "PA": 681},
            {"Player": "David Ortiz", "Pos": "DH", "Bats": "L", "BB_RATE": 0.111, "K_RATE": 0.197, "HR_PA_RATE": 0.061, "BABIP": 0.331, "1B_H_RATE": 0.490, "2B_H_RATE": 0.280, "3B_H_RATE": 0.010, "HR_H_RATE": 0.220, "SPD": 45, "PA": 669},
            {"Player": "Kevin Millar", "Pos": "1B", "Bats": "R", "BB_RATE": 0.115, "K_RATE": 0.145, "HR_PA_RATE": 0.029, "BABIP": 0.321, "1B_H_RATE": 0.620, "2B_H_RATE": 0.230, "3B_H_RATE": 0.000, "HR_H_RATE": 0.150, "SPD": 42, "PA": 612},
            {"Player": "Jason Varitek", "Pos": "C", "Bats": "B", "BB_RATE": 0.110, "K_RATE": 0.214, "HR_PA_RATE": 0.033, "BABIP": 0.339, "1B_H_RATE": 0.560, "2B_H_RATE": 0.250, "3B_H_RATE": 0.010, "HR_H_RATE": 0.180, "SPD": 48, "PA": 550},
            {"Player": "Orlando Cabrera", "Pos": "SS", "Bats": "R", "BB_RATE": 0.071, "K_RATE": 0.112, "HR_PA_RATE": 0.012, "BABIP": 0.315, "1B_H_RATE": 0.680, "2B_H_RATE": 0.200, "3B_H_RATE": 0.020, "HR_H_RATE": 0.100, "SPD": 78, "PA": 260},
            {"Player": "Bill Mueller", "Pos": "3B", "Bats": "B", "BB_RATE": 0.105, "K_RATE": 0.131, "HR_PA_RATE": 0.026, "BABIP": 0.311, "1B_H_RATE": 0.640, "2B_H_RATE": 0.220, "3B_H_RATE": 0.010, "HR_H_RATE": 0.130, "SPD": 58, "PA": 460},
            {"Player": "Trot Nixon", "Pos": "RF", "Bats": "L", "BB_RATE": 0.125, "K_RATE": 0.165, "HR_PA_RATE": 0.035, "BABIP": 0.319, "1B_H_RATE": 0.550, "2B_H_RATE": 0.250, "3B_H_RATE": 0.010, "HR_H_RATE": 0.190, "SPD": 70, "PA": 165}
        ],
        "pitching": [
            {"Player": "Curt Schilling", "Pos": "SP", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.038, "K_ALLOWED_RATE": 0.221, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.285, "OAVG": 0.231, "IP": "226.2", "ERA": 3.26},
            {"Player": "Pedro Martinez", "Pos": "SP", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.067, "K_ALLOWED_RATE": 0.253, "HR_PA_ALLOWED_RATE": 0.029, "BABIP_ALLOWED": 0.292, "OAVG": 0.239, "IP": "217.0", "ERA": 3.90},
            {"Player": "Keith Foulke", "Pos": "RP", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.048, "K_ALLOWED_RATE": 0.245, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.231, "OAVG": 0.198, "IP": "83.0", "ERA": 2.17}
        ]
    }
}

BALLPARK_ENV = {
    "1927 New York Yankees": {"run_mult": 1.05, "hr_mult": 1.02, "babip_mult": 1.01, "desc": "Yankee Stadium I - Deep asymmetric lines"},
    "2004 Boston Red Sox": {"run_mult": 1.08, "hr_mult": 1.02, "babip_mult": 1.04, "desc": "Fenway Park - Wall deflection anomalies"},
    "Neutral Site": {"run_mult": 1.00, "hr_mult": 1.00, "babip_mult": 1.00, "desc": "Standard Baseline Matrix Environment"}
}

# ----------------------------------------------------
# ADVANCED MATHEMATICAL FUNCTIONS
# ----------------------------------------------------
def calculate_log_odds(player_rate, pitcher_rate, league_rate):
    """ Bill James Log-Odds Matchup Equation to normalize interaction points """
    player_rate = max(0.001, min(0.999, player_rate))
    pitcher_rate = max(0.001, min(0.999, pitcher_rate))
    league_rate = max(0.001, min(0.999, league_rate))
    
    odds_b = player_rate / (1.0 - player_rate)
    odds_p = pitcher_rate / (1.0 - pitcher_rate)
    odds_l = league_rate / (1.0 - league_rate)
    
    final_odds = (odds_b * odds_p) / odds_l
    return final_odds / (1.0 + final_odds)

def apply_bayesian_stabilization(raw_rate, opportunities, baseline_rate, sample_weight=150):
    """ Stabilizes sparse real-time API fields into actionable predictive data """
    return ((raw_rate * opportunities) + (baseline_rate * sample_weight)) / (opportunities + sample_weight)

@st.cache_data(ttl=3600)
def fetch_mlb_live_data():
    try:
        url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
        res = requests.get(url, timeout=5).json()
        return {team['name']: team['id'] for team in res.get('teams', []) if team.get('active', True)}
    except:
        return {"1927 New York Yankees": 1, "2004 Boston Red Sox": 2}

live_teams_map = fetch_mlb_live_data()
all_teams_list = sorted(list(set(list(live_teams_map.keys()) + list(RETRO_TEAMS.keys()))))

def build_predictive_roster(team_name, team_id, side="hitting"):
    if team_name in RETRO_TEAMS:
        return pd.DataFrame(RETRO_TEAMS[team_name][side])
    
    fallback_list = []
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=Active&hydrate=person(stats(group=[{side}],type=season,season=2026))"
        res = requests.get(url, timeout=5).json()
        
        for idx, member in enumerate(res.get('roster', [])):
            person = member.get('person', {})
            name = person.get('fullName', 'Unknown Quant')
            pos = member.get('position', {}).get('abbreviation', 'N/A')
            splits = person.get('stats', [{}])[0].get('splits', [{}])
            
            if splits and 'stat' in splits[0]:
                s = splits[0]['stat']
                if side == "hitting":
                    pa = int(s.get("plateAppearances", 1))
                    bb = int(s.get("baseOnBalls", 0))
                    so = int(s.get("strikeOuts", 0))
                    hr = int(s.get("homeRuns", 0))
                    hits = int(s.get("hits", 0))
                    ab = int(s.get("atBats", 1))
                    
                    raw_bb_rate = bb / max(1, pa)
                    raw_k_rate = so / max(1, pa)
                    raw_hr_pa = hr / max(1, pa)
                    raw_babip = (hits - hr) / max(1, (ab - so - hr + int(s.get("sf", 0))))
                    
                    fallback_list.append({
                        "Player": name, "Pos": pos, "Bats": person.get('batSide', {}).get('code', 'R'),
                        "BB_RATE": apply_bayesian_stabilization(raw_bb_rate, pa, LEAGUE_BASELINE["BB_RATE"]),
                        "K_RATE": apply_bayesian_stabilization(raw_k_rate, pa, LEAGUE_BASELINE["K_RATE"]),
                        "HR_PA_RATE": apply_bayesian_stabilization(raw_hr_pa, pa, LEAGUE_BASELINE["HR_PA_RATE"]),
                        "BABIP": apply_bayesian_stabilization(raw_babip, ab, LEAGUE_BASELINE["BABIP"]),
                        "1B_H_RATE": LEAGUE_BASELINE["1B_H_RATE"], "2B_H_RATE": LEAGUE_BASELINE["2B_H_RATE"],
                        "3B_H_RATE": LEAGUE_BASELINE["3B_H_RATE"], "HR_H_RATE": LEAGUE_BASELINE["HR_H_RATE"],
                        "SPD": random.randint(45, 90), "PA": pa
                    })
                else:
                    bf = int(s.get("battersFaced", 1))
                    bb = int(s.get("baseOnBalls", 0))
                    so = int(s.get("strikeOuts", 0))
                    hr = int(s.get("homeRuns", 0))
                    hits = int(s.get("hits", 0))
                    
                    fallback_list.append({
                        "Player": name, "Pos": pos, "Role": "SP" if pos == "SP" else ("Closer" if idx % 5 == 0 else "RP"),
                        "Throws": person.get('pitchHand', {}).get('code', 'R'),
                        "BB_ALLOWED_RATE": apply_bayesian_stabilization(bb/max(1, bf), bf, LEAGUE_BASELINE["BB_RATE"]),
                        "K_ALLOWED_RATE": apply_bayesian_stabilization(so/max(1, bf), bf, LEAGUE_BASELINE["K_RATE"]),
                        "HR_PA_ALLOWED_RATE": apply_bayesian_stabilization(hr/max(1, bf), bf, LEAGUE_BASELINE["HR_PA_RATE"]),
                        "BABIP_ALLOWED": apply_bayesian_stabilization(0.290, bf, LEAGUE_BASELINE["BABIP"]),
                        "OAVG": float(s.get("avg", 0.244)), "IP": s.get("inningsPitched", "30.0"), "ERA": float(s.get("era", 4.00))
                    })
    except: pass
    
    if not fallback_list:
        if side == "hitting":
            return pd.DataFrame([{"Player": f"Synthetic Batter {i}", "Pos": "OF", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.21, "HR_PA_RATE": 0.03, "BABIP": 0.290, "1B_H_RATE": 0.63, "2B_H_RATE": 0.21, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 65, "PA": 300} for i in range(9)])
        else:
            return pd.DataFrame([{"Player": f"Synthetic Pitcher {i}", "Pos": "P", "Role": "SP" if i==0 else "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.290, "OAVG": 0.244, "IP": "50.0", "ERA": 4.00} for i in range(5)])
            
    return pd.DataFrame(fallback_list)

# ----------------------------------------------------
# CONTROL BOARD INTERFACE UI
# ----------------------------------------------------
st.sidebar.header("⚙️ Quantitative Parameters")
away_selection = st.sidebar.selectbox("Away Organization", all_teams_list, index=0)
home_selection = st.sidebar.selectbox("Home Organization", all_teams_list, index=min(1, len(all_teams_list)-1))

st.sidebar.markdown("---")
vegas_line_input = st.sidebar.number_input("Vegas Consensus Moneyline Market (Home)", value=-110, step=5)
playback_speed = st.sidebar.slider("Visual Simulation Gate Latency", 0.0, 0.5, 0.01, step=0.01)

away_h_pool = build_predictive_roster(away_selection, live_teams_map.get(away_selection, 0), "hitting")
home_h_pool = build_predictive_roster(home_selection, live_teams_map.get(home_selection, 0), "hitting")
away_p_pool = build_predictive_roster(away_selection, live_teams_map.get(away_selection, 0), "pitching")
home_p_pool = build_predictive_roster(home_selection, live_teams_map.get(home_selection, 0), "pitching")

if not st.session_state["lineups_locked"]:
    st.subheader("📋 Core Lineup Configuration Ingestion")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### {away_selection} Depth Assets")
        sp_choice_a = st.selectbox("Starting Pitcher Choice (Away)", list(away_p_pool[away_p_pool["Role"]=="SP"]["Player"]) if not away_p_pool[away_p_pool["Role"]=="SP"].empty else list(away_p_pool["Player"]))
        batters_a = []
        for i in range(9):
            b = st.selectbox(f"Away Lineup Slot {i+1}", list(away_h_pool["Player"]), index=min(i, len(away_h_pool)-1), key=f"a_s_{i}")
            batters_a.append(b)
            
    with col2:
        st.markdown(f"#### {home_selection} Depth Assets")
        sp_choice_h = st.selectbox("Starting Pitcher Choice (Home)", list(home_p_pool[home_p_pool["Role"]=="SP"]["Player"]) if not home_p_pool[home_p_pool["Role"]=="SP"].empty else list(home_p_pool["Player"]))
        batters_h = []
        for i in range(9):
            b = st.selectbox(f"Home Lineup Slot {i+1}", list(home_h_pool["Player"]), index=min(i, len(home_h_pool)-1), key=f"h_s_{i}")
            batters_h.append(b)
            
    if st.button("🔒 Structural Lock Lineups & Run 1,000x Monte Carlo Engine", use_container_width=True):
        st.session_state["locked_away_sp"] = away_p_pool[away_p_pool["Player"] == sp_choice_a].iloc[0].to_dict()
        st.session_state["locked_home_sp"] = home_p_pool[home_p_pool["Player"] == sp_choice_h].iloc[0].to_dict()
        st.session_state["locked_away_lineup"] = [away_h_pool[away_h_pool["Player"] == b].iloc[0].to_dict() for b in batters_a]
        st.session_state["locked_home_lineup"] = [home_h_pool[home_h_pool["Player"] == b].iloc[0].to_dict() for b in batters_h]
        st.session_state["locked_away_bullpen"] = away_p_pool[away_p_pool["Player"] != sp_choice_a].to_dict("records")
        st.session_state["locked_home_bullpen"] = home_p_pool[home_p_pool["Player"] != sp_choice_h].to_dict("records")
        st.session_state["lineups_locked"] = True
        st.session_state["monte_carlo_results"] = None
        st.rerun()
else:
    st.sidebar.button("🔓 Release Ecosystem Parameters", on_click=lambda: st.session_state.update({"lineups_locked": False, "game_active": False, "monte_carlo_results": None}))

    # ----------------------------------------------------
    # ADVANCED QUANT MODULE: DIPS MARKOV SIMULATION ENGINE
    # ----------------------------------------------------
    class DipsMarkovEngine:
        def __init__(self, away_lineup, home_lineup, away_sp, home_sp, away_bp, home_bp, park_rules):
            self.away_lineup = away_lineup
            self.home_lineup = home_lineup
            self.away_sp = away_sp
            self.home_sp = home_sp
            self.away_bp = copy.deepcopy(away_bp)
            self.home_bp = copy.deepcopy(home_bp)
            self.park = park_rules
            
        def execute_matchup_vector(self, batter, pitcher, order_cycle):
            """ Computes the exact 8-dimensional probability vector for plate appearance outcomes """
            # Platoon Splits Matrix Calibration
            platoon_mult = 1.05 if batter["Bats"] != pitcher["Throws"] else 0.92
            
            # Times Through the Order Penalty (TTOP) Calculation Loop
            ttop_mult = 1.0
            if pitcher["Role"] == "SP":
                if order_cycle == 2: ttop_mult = 1.06
                elif order_cycle >= 3: ttop_mult = 1.18

            # Resolve the Independent Outcomes (DIPS Framework Layer)
            bb_prob = calculate_log_odds(batter["BB_RATE"], pitcher["BB_ALLOWED_RATE"] * ttop_mult, LEAGUE_BASELINE["BB_RATE"])
            k_prob = calculate_log_odds(batter["K_RATE"], pitcher["K_ALLOWED_RATE"] * ttop_mult, LEAGUE_BASELINE["K_RATE"])
            hr_prob = calculate_log_odds(batter["HR_PA_RATE"], pitcher["HR_PA_ALLOWED_RATE"] * ttop_mult, LEAGUE_BASELINE["HR_PA_RATE"]) * self.park["hr_mult"]
            
            # Enforce probability scaling bounds
            sum_isolated = bb_prob + k_prob + hr_prob
            if sum_isolated >= 0.95:
                scale = 0.95 / sum_isolated
                bb_prob *= scale; k_prob *= scale; hr_prob *= scale
                
            # Fielded Metrics Matrix Estimation (BABIP)
            remainder = 1.0 - (bb_prob + k_prob + hr_prob)
            babip_matchup = calculate_log_odds(batter["BABIP"] * platoon_mult, pitcher["BABIP_ALLOWED"], LEAGUE_BASELINE["BABIP"]) * self.park["babip_mult"]
            
            hit_in_play_prob = remainder * babip_matchup
            out_in_play_prob = remainder - hit_in_play_prob
            
            single_p = hit_in_play_prob * 0.74
            double_p = hit_in_play_prob * 0.22
            triple_p = hit_in_play_prob * 0.04
            
            return {
                "BB": bb_prob, "K": k_prob, "HR": hr_prob,
                "1B": single_p, "2B": double_p, "3B": triple_p, "OUT": out_in_play_prob
            }

        def step_markov_state(self, state, outcome):
            """ Evaluates exact run movement using an implicit 24-state transition logic map """
            outs = state["outs"]
            bases = list(state["bases"])
            runs_scored = 0
            event_log = ""
            
            if outcome == "K" or outcome == "OUT":
                outs += 1
                event_log = "Strikeout recorded" if outcome == "K" else "Fielded play out vector resolved"
                return outs, bases, runs_scored, event_log
                
            if outcome == "BB":
                event_log = "Base on Balls tracking transaction"
                if not bases[0]: bases[0] = True
                elif not bases[1]: bases[1] = True
                elif not bases[2]: bases[2] = True
                else: runs_scored += 1
                return outs, bases, runs_scored, event_log

            if outcome == "HR":
                runs_scored = 1 + sum(1 for b in bases if b)
                bases = [False, False, False]
                event_log = f"Home Run vector mutation: {runs_scored} runs cross plate"
                return outs, bases, runs_scored, event_log

            # Hit-In-Play Variable Vector Distributions
            if outcome == "1B":
                event_log = "Single hit tracking index"
                new_bases = [True, False, False]
                if bases[2]: runs_scored += 1
                if bases[1]: new_bases[2] = True
                if bases[0]: new_bases[1] = True
                bases = new_bases
            elif outcome == "2B":
                event_log = "Double hit tracking index"
                new_bases = [False, True, False]
                if bases[2]: runs_scored += 1
                if bases[1]: runs_scored += 1
                if bases[0]: new_bases[2] = True
                bases = new_bases
            elif outcome == "3B":
                event_log = "Triple hit tracking index"
                if bases[2]: runs_scored += 1
                if bases[1]: runs_scored += 1
                if bases[0]: runs_scored += 1
                bases = [False, False, True]
                
            return outs, bases, runs_scored, event_log

        def run_full_game(self, tracking_mode=False):
            """ Loops through standard baseball state boundaries to provide clean mathematical convergence data """
            g = {
                "inning": 1, "top_half": True, "away_score": 0, "home_score": 0,
                "away_lineup_idx": 0, "home_lineup_idx": 0,
                "away_p": copy.deepcopy(self.away_sp), "home_p": copy.deepcopy(self.home_sp),
                "away_pitches": 0, "home_pitches": 0, "away_bf": 0, "home_bf": 0,
                "box_scores": {
                    "away": {p["Player"]: {"AB":0,"H":0,"1B":0,"2B":0,"3B":0,"HR":0,"BB":0,"RBI":0,"K":0} for p in self.away_lineup},
                    "home": {p["Player"]: {"AB":0,"H":0,"1B":0,"2B":0,"3B":0,"HR":0,"BB":0,"RBI":0,"K":0} for p in self.home_lineup}
                },
                "log_history": [], "win_prob_history": [50.0]
            }
            
            park_data = BALLPARK_ENV.get(home_selection, BALLPARK_ENV["Neutral Site"])
            
            while g["inning"] <= 9 or (g["away_score"] == g["home_score"]):
                # Leverage-Index Inning Bullpen Transition Protocol Checks
                score_diff = abs(g["away_score"] - g["home_score"])
                if g["top_half"]:
                    if (g["home_pitches"] > 85 and g["home_p"]["Role"] == "SP") or (g["home_pitches"] > 25 and g["home_p"]["Role"] != "SP") or (g["inning"] >= 8 and score_diff <= 3 and g["home_p"]["Role"] == "SP"):
                        if self.home_bp:
                            g["home_p"] = self.home_bp.pop(0)
                            g["home_pitches"] = 0
                else:
                    if (g["away_pitches"] > 85 and g["away_p"]["Role"] == "SP") or (g["away_pitches"] > 25 and g["away_p"]["Role"] != "SP") or (g["inning"] >= 8 and score_diff <= 3 and g["away_p"]["Role"] == "SP"):
                        if self.away_bp:
                            g["away_p"] = self.away_bp.pop(0)
                            g["away_pitches"] = 0

                # Clear state architecture for the half-inning
                state = {"outs": 0, "bases": [False, False, False]}
                
                # Check for walkoff parameters
                if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]:
                    break
                    
                while state["outs"] < 3:
                    if g["top_half"]:
                        batter = self.away_lineup[g["away_lineup_idx"] % 9]
                        pitcher = g["home_p"]
                        g["home_pitches"] += random.randint(3, 6)
                        order_cycle = (g["away_lineup_idx"] // 9) + 1
                    else:
                        batter = self.home_lineup[g["home_lineup_idx"] % 9]
                        pitcher = g["away_p"]
                        g["away_pitches"] += random.randint(3, 6)
                        order_cycle = (g["home_lineup_idx"] // 9) + 1
                        
                    prob_vector = self.execute_matchup_vector(batter, pitcher, order_cycle)
                    
                    # Core Monte Carlo Stochastic Outcome Realization
                    keys = list(prob_vector.keys())
                    values = list(prob_vector.values())
                    outcome = random.choices(keys, weights=values, k=1)[0]
                    
                    # Mutate game logs and stat tables based on outcome
                    t_key = "away" if g["top_half"] else "home"
                    b_box = g["box_scores"][t_key][batter["Player"]]
                    
                    if outcome in ["1B", "2B", "3B", "HR"]:
                        b_box["H"] += 1
                        b_box[outcome] += 1
                        b_box["AB"] += 1
                    elif outcome == "BB": b_box["BB"] += 1
                    elif outcome == "K": 
                        b_box["K"] += 1
                        b_box["AB"] += 1
                    else: b_box["AB"] += 1
                    
                    old_outs, old_bases, runs, log_text = state["outs"], state["bases"], 0, ""
                    state["outs"], state["bases"], runs, log_text = self.step_markov_state(state, outcome)
                    
                    if runs > 0:
                        b_box["RBI"] += runs
                        if g["top_half"]: g["away_score"] += runs
                        else: g["home_score"] += runs
                        
                    if tracking_mode:
                        g["log_history"].append(f"**Inning {g['inning']} ({'Top' if g['top_half'] else 'Bot'}):** `{batter['Player']}` facing `{pitcher['Player']}` -> **{outcome}** ({log_text}). Score: A:{g['away_score']} - H:{g['home_score']}")
                    
                    if g["top_half"]: g["away_lineup_idx"] += 1
                    else: g["home_lineup_idx"] += 1
                    
                    if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]:
                        break # Walk-off protection boundary check
                        
                # Progress frame matrices
                if tracking_mode:
                    live_wp = 0.50 + (g["home_score"] - g["away_score"]) * 0.08
                    g["win_prob_history"].append(max(0.01, min(0.99, live_wp)) * 100)
                    
                g["top_half"] = not g["top_half"]
                if g["top_half"]: g["inning"] += 1
                
            return g

    # ----------------------------------------------------
    # SYSTEM ENGINE HIGH-SPEED MULTI-THREAD CONVERGENCE LOOP
    # ----------------------------------------------------
    if st.session_state["monte_carlo_results"] is None:
        with st.spinner("Executing 1,000x Background Monte Carlo Convergence Loops..."):
            park_rules = BALLPARK_ENV.get(home_selection, BALLPARK_ENV["Neutral Site"])
            engine = DipsMarkovEngine(
                st.session_state["locked_away_lineup"], st.session_state["locked_home_lineup"],
                st.session_state["locked_away_sp"], st.session_state
