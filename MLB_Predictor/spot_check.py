import streamlit as st
import requests
import random
import time
import pandas as pd

st.set_page_config(page_title="Live MLB Analytics Platform", page_icon="⚾", layout="wide")

# ----------------------------------------------------
# STANDINGS DATA PERSISTENCE LAYER
# ----------------------------------------------------
if "standings" not in st.session_state:
    st.session_state["standings"] = {}

def record_game_result(winner, loser):
    if winner not in st.session_state["standings"]: st.session_state["standings"][winner] = {"W": 0, "L": 0}
    if loser not in st.session_state["standings"]: st.session_state["standings"][loser] = {"W": 0, "L": 0}
    st.session_state["standings"][winner]["W"] += 1
    st.session_state["standings"][loser]["L"] += 1

# ----------------------------------------------------
# RETRO HISTORICAL DATABASE SQUADS
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
    "1927 New York Yankees": {"run_mult": 1.05, "hr_mult": 1.02, "desc": "Yankee Stadium I - Short right field tracking lines"},
    "2004 Boston Red Sox": {"run_mult": 1.08, "hr_mult": 1.02, "desc": "Fenway Park - Green Monster wall factors"}
}
DEFAULT_BALLPARK = {"run_mult": 1.00, "hr_mult": 1.00, "desc": "Standard neutral environment active"}

# ----------------------------------------------------
# LIVE MLB REST API CACHE ENGINE
# ----------------------------------------------------
@st.cache_data(ttl=3600)
def get_mlb_teams():
    url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    res = requests.get(url).json()
    teams = {}
    for team in res.get('teams', []):
        if team.get('active', False) and team['name'] in TEAM_COLORS:
            teams[team['name']] = team['id']
    return dict(sorted(teams.items()))

try: live_teams = get_mlb_teams()
except: live_teams = {}

all_selectable_teams = sorted(list(live_teams.keys()) + list(RETRO_TEAMS.keys()))

@st.cache_data(ttl=3600)
def get_detailed_roster_stats(team_id, team_name, stat_group="hitting"):
    if team_name in RETRO_TEAMS: return pd.DataFrame(RETRO_TEAMS[team_name][stat_group])
    players_list = []
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=Active&hydrate=person(stats(group=[{stat_group}],type=season,season=2026))"
        res = requests.get(url).json()
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
    return pd.DataFrame(players_list)

# ----------------------------------------------------
# MATCHUP DESIGN SYSTEMS & SIDEBARS
# ----------------------------------------------------
st.sidebar.header("Matchup Setup Panel")
away_team = st.sidebar.selectbox("Away Team (Visitor)", all_selectable_teams, index=0)
home_team = st.sidebar.selectbox("Home Team (Host)", all_selectable_teams, index=min(1, len(all_selectable_teams)-1))

if "leveraged_game_state" not in st.session_state:
    st.session_state["leveraged_game_state"] = None
if "final_reports" not in st.session_state:
    st.session_state["final_reports"] = None

theme_host = RETRO_TEAMS.get(home_team, TEAM_COLORS.get(home_team, {"primary": "#1E1E1E", "secondary": "#777777"}))
st.markdown(f"<style>h1, h2, h3, h4 {{ color: {theme_host['primary']}; }} .stButton>button {{ background-color: {theme_host['primary']} !important; color: white !important; }}</style>", unsafe_allow_html=True)

away_hitter_raw = get_detailed_roster_stats(live_teams.get(away_team), away_team, "hitting")
home_hitter_raw = get_detailed_roster_stats(live_teams.get(home_team), home_team, "hitting")
away_pitcher_df = get_detailed_roster_stats(live_teams.get(away_team), away_team, "pitching")
home_pitcher_df = get_detailed_roster_stats(live_teams.get(home_team), home_team, "pitching")

st.subheader("📋 Team Lineup Card Management")
l_col1, l_col2 = st.columns(2)
with l_col1:
    st.markdown(f"#### {away_team}")
    away_p_names = list(away_pitcher_df["Player"]) if not away_pitcher_df.empty else ["Unknown Starter"]
    away_starter_sel = st.selectbox("Select Starter", away_p_names, key="a_sp")
    away_h_names = list(away_hitter_raw["Player"]) if not away_hitter_raw.empty else ["Generic Batter"]
    away_lineup = st.multiselect("Batting Lineup", away_h_names, default=away_h_names[:9] if len(away_h_names)>=9 else away_h_names)
with l_col2:
    st.markdown(f"#### {home_team}")
    home_p_names = list(home_pitcher_df["Player"]) if not home_pitcher_df.empty else ["Unknown Starter"]
    home_starter_sel = st.selectbox("Select Starter", home_p_names, key="h_sp")
    home_h_names = list(home_hitter_raw["Player"]) if not home_hitter_raw.empty else ["Generic Batter"]
    home_lineup = st.multiselect("Batting Lineup", home_h_names, default=home_h_names[:9] if len(home_h_names)>=9 else home_h_names)

away_selected_hitters = away_hitter_raw[away_hitter_raw["Player"].isin(away_lineup)].copy() if away_lineup else away_hitter_raw.head(9).copy()
home_selected_hitters = home_hitter_raw[home_hitter_raw["Player"].isin(home_lineup)].copy() if home_lineup else home_hitter_raw.head(9).copy()

away_sp_row = away_pitcher_df[away_pitcher_df["Player"] == away_starter_sel]
home_sp_row = home_pitcher_df[home_pitcher_df["Player"] == home_starter_sel]

away_sp_era = float(away_sp_row.iloc[0]["ERA"]) if not away_sp_row.empty else 4.20
home_sp_era = float(home_sp_row.iloc[0]["ERA"]) if not home_sp_row.empty else 4.20
away_sp_hand = str(away_sp_row.iloc[0]["Throws"]) if not away_sp_row.empty else "R"
home_sp_hand = str(home_sp_row.iloc[0]["Throws"]) if not home_sp_row.empty else "R"

park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)

# ----------------------------------------------------
# WEATHER & SABERMETRIC ENGINE ODDS
# ----------------------------------------------------
st.markdown("---")
m_col1, m_col2 = st.columns(2)

with m_col1:
    st.subheader("☀️ Weather Vector Matrix")
    if "weather" not in st.session_state or st.sidebar.button("Generate New Atmospheric Profile"):
        temp = random.randint(45, 98)
        wind_spd = random.randint(0, 22)
        wind_dir = random.choice(["Out to Dead Center 🚀", "Blowing Straight In 🪂", "Crosswind Left to Right 🧭"])
        w_hr_mult = 1.0
        if temp > 85: w_hr_mult += 0.08
        if temp < 55: w_hr_mult -= 0.08
        if "Out" in wind_dir: w_hr_mult += (wind_spd * 0.01)
        if "In" in wind_dir: w_hr_mult -= (wind_spd * 0.01)
        st.session_state["weather"] = {"temp": temp, "speed": wind_spd, "dir": wind_dir, "mult": w_hr_mult}

    w = st.session_state["weather"]
    st.write(f"🌡️ **Game Temperature:** `{w['temp']}°F` | 💨 **Wind Vectors:** `{w['speed']} MPH` {w['dir']}")

    data_away_p = RETRO_TEAMS.get(away_team, TEAM_COLORS.get(away_team, {"runs_scored": 720, "runs_allowed": 720}))
    data_home_p = RETRO_TEAMS.get(home_team, TEAM_COLORS.get(home_team, {"runs_scored": 720, "runs_allowed": 720}))
    pyth_a = (data_away_p["runs_scored"]**1.83) / ((data_away_p["runs_scored"]**1.83) + (data_away_p["runs_allowed"]**1.83))
    pyth_h = (data_home_p["runs_scored"]**1.83) / ((data_home_p["runs_scored"]**1.83) + (data_home_p["runs_allowed"]**1.83))
    calc_away_pct = (pyth_a / (pyth_a + pyth_h)) * 100
    st.markdown("##### Sabermetric Prediction Odds")
    st.progress(int(calc_away_pct))

with m_col2:
    st.subheader("🎲 Simulation Controller")
    if "game_active" not in st.session_state:
        st.session_state["game_active"] = False
        
    if st.button("Launch Game Simulation Framework"):
        st.session_state["game_active"] = True
        st.session_state["leveraged_game_state"] = None
        st.session_state["final_reports"] = None

# ----------------------------------------------------
# LIVE MATRIX SIMULATION ENGINE LOOP
# ----------------------------------------------------
if st.session_state["game_active"] or st.session_state["leveraged_game_state"] is not None:
    if st.session_state["leveraged_game_state"] is None:
        away_box_init = {p: {"AB": 0, "H": 0, "HR": 0, "RBI": 0, "SO": 0} for p in away_selected_hitters["Player"]}
        home_box_init = {p: {"AB": 0, "H": 0, "HR": 0, "RBI": 0, "SO": 0} for p in home_selected_hitters["Player"]}
        
        st.session_state["leveraged_game_state"] = {
            "inning": 1, "top_half": True, "away_score": 0, "home_score": 0,
            "away_idx": 0, "home_idx": 0, "away_bf": 0, "home_bf": 0, "outs": 0,
            "bases": [None, None, None], "logs": ["🏟️ Umpire signals play ball!"],
            "away_box": away_box_init, "home_box": home_box_init,
            "current_away_p": f"{away_starter_sel} (SP)", "current_away_era": away_sp_era, "current_away_hand": away_sp_hand,
            "current_home_p": f"{home_starter_sel} (SP)", "current_home_era": home_sp_era, "current_home_hand": home_sp_hand,
            "interrupted": False, "strategy_selected": False, "bullpen_call": False, "chart_data": [{"Inning": "Start", f"{away_team} Win %": 50.0}]
        }

    g = st.session_state["leveraged_game_state"]
    
    status_field = st.status("⚾ Simulating live matchups...", expanded=True)
    scoreboard = st.empty()
    
    tab_view, tab_away, tab_home = st.tabs(["🏟️ Live Diamond Feed", f"📊 {away_team} Box", f"📊 {home_team} Box"])
    
    with tab_view:
        c_left, c_right = st.columns([1, 1])
        with c_left: field_viz = st.empty()
        with c_right: graph_viz = st.empty()
        ticker = st.empty()
        
    with tab_away:
        away_box_display = st.empty()
    with tab_home:
        home_box_display = st.empty()

    def print_ascii_diamond(runners):
        b1 = "🟥" if runners[0] else "⬜"
        b2 = "🟥" if runners[1] else "⬜"
        b3 = "🟥" if runners[2] else "⬜"
        return f"<pre style='line-height:1.2; font-weight:bold;'>       [{b2}] 2nd\n       /   \\\n3rd [{b3}]     [{b1}] 1st\n       \\   /\n       [🏃] Home</pre>"

    # Interrupt Manager Strategy Evaluation
    if g.get("interrupted", False):
        st.warning("⚠️ **HIGH LEVERAGE MOMENT: Manager Choice Demanded!**")
        d1, d2 = st.columns(2)
        with d1:
            if st.button("🔴 Strategic Safety: Pitch Around Corner"):
                g["logs"].append("📋 *Manager Strategy:* Demanded safe pitch-around mechanics.")
                g["interrupted"] = False
                g["strategy_selected"] = True
                st.session_state["leveraged_game_state"] = g
                st.rerun()
        with d2:
            if st.button("🟢 Deep Attack: Swing Away/Full Max Volleys"):
                g["logs"].append("📋 *Manager Strategy:* Approved maximum swinging aggression variables.")
                g["interrupted"] = False
                g["strategy_selected"] = True
                st.session_state["leveraged_game_state"] = g
                st.rerun()
        st.stop()

    # Manual Bullpen Manager Call Prompts
    if g.get("bullpen_call", False):
        st.warning(f"🔄 **BULLPEN CALL NEEDED: Select Pitcher to take the mound**")
        active_bp = home_pitcher_df if g["top_half"] else away_pitcher_df
        bp_choices = list(active_bp["Player"]) if not active_bp.empty else ["Generic Closer"]
        sel_reliever = st.selectbox("Choose Relief Pitcher", bp_choices)
        if st.button("Confirm Pitching Change"):
            rel_row = active_bp[active_bp["Player"] == sel_reliever].iloc[0]
            if g["top_half"]:
                g["current_home_p"], g["current_home_era"], g["current_home_hand"] = f"{rel_row['Player']} (RP)", float(rel_row['ERA']), str(rel_row['Throws'])
                g["home_bf"] = 0
            else:
                g["current_away_p"], g["current_away_era"], g["current_away_hand"] = f"{rel_row['Player']} (RP)", float(rel_row['ERA']), str(rel_row['Throws'])
                g["away_bf"] = 0
            g["logs"].append(f"🔄 Manager visits mound: **{rel_row['Player']}** takes the ball.")
            g["bullpen_call"] = False
            st.session_state["leveraged_game_state"] = g
            st.rerun()
        st.stop()

    # Core Execution Engine Loops
    while g["inning"] <= 12 or (g["away_score"] == g["home_score"]):
        half_str = "Top" if g["top_half"] else "Bottom"
        
        # Modern MLB Extra Inning Ghost Runner Logic
        if g["inning"] >= 10 and g["outs"] == 0 and g["bases"] == [None, None, None]:
            g["bases"][1] = "Ghost Runner"
            g["logs"].append("👻 **MLB Ghost Runner Rule Active:** Automated runner placed onto 2nd base.")

        while g["outs"] < 3:
            if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]: break
            
            if g["top_half"] and g["home_bf"] >= 15 and "SP" in g["current_home_p"]:
                g["bullpen_call"] = True; st.session_state["leveraged_game_state"] = g; st.rerun()
            if not g["top_half"] and g["away_bf"] >= 15 and "SP" in g["current_away_p"]:
                g["bullpen_call"] = True; st.session_state["leveraged_game_state"] = g; st.rerun()

            if g["inning"] >= 7 and sum([1 for r in g["bases"] if r is not None]) >= 2 and g["outs"] >= 1 and not g.get("strategy_selected", False):
                g["interrupted"] = True; st.session_state["leveraged_game_state"] = g; st.rerun()

            if g["top_half"]:
                batter = away_selected_hitters.iloc[g["away_idx"] % len(away_selected_hitters)]
                b_team = "away"
                p_era = g["current_home_era"]
                p_hand = g["current_home_hand"]
                g["home_bf"] += 1
            else:
                batter = home_selected_hitters.iloc[g["home_idx"] % len(home_selected_hitters)]
                b_team = "home"
                p_era = g["current_away_era"]
                p_hand = g["current_away_hand"]
                g["away_bf"] += 1

            plat_mult = 1.05 if batter["Bats"] != p_hand else 0.95
            hit_p = batter["AVG"] * park_data["run_mult"] * plat_mult * (p_era / 4.1)
            
            if batter["Player"] not in g[f"{b_team}_box"]:
                g[f"{b_team}_box"][batter["Player"]] = {"AB": 0, "H": 0, "HR": 0, "RBI": 0, "SO": 0}
            g[f"{b_team}_box"][batter["Player"]]["AB"] += 1

            if random.uniform(0, 1.05) <= hit_p:
                hr_chance = (batter["HR"] / max(1, batter["AB"])) * park_data["hr_mult"] * w["mult"]
                roll = random.uniform(0, 1)
                if roll <= hr_chance:
                    runs = 1 + sum([1 for r in g["bases"] if r is not None])
                    g[f"{b_team}_box"][batter["Player"]]["HR"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                    g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                    if g["top_half"]: g["away_score"] += runs
                    else: g["home_score"] += runs
                    g["bases"] = [None, None, None]
                    g["logs"].append(f"💥 **HR!** {batter['Player']} hits a `{runs}-run` shot off {g['current_home_p'] if g['top_half'] else g['current_away_p']}!")
                    
                    if g["top_half"]: g["current_home_era"] += 0.45
                    else: g["current_away_era"] += 0.45
                elif roll <= hr_chance + 0.16:
                    runs = sum([1 for r in g["bases"][1:] if r is not None])
                    g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                    g["bases"][2] = g["bases"][0]; g["bases"][1] = batter["Player"]; g["bases"][0] = None
                    if g["top_half"]: g["away_score"] += runs
                    else: g["home_score"] += runs
                    g["logs"].append(f"⚾ **Double!** {batter['Player']} lines one into the gap.")
                    
                    if g["top_half"]: g["current_home_era"] += 0.15
                    else: g["current_away_era"] += 0.15
                else:
                    runs = 1 if g["bases"][2] else 0
                    g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                    g["bases"][2] = g["bases"][1]; g["bases"][1] = g["bases"][0]; g["bases"][0] = batter["Player"]
                    if g["top_half"]: g["away_score"] += runs
                    else: g["home_score"] += runs
                    g["logs"].append(f"🏃 **Single!** {batter['Player']} drops a base hit.")
                    
                    if g["top_half"]: g["current_home_era"] += 0.10
                    else: g["current_away_era"] += 0.10
            else:
                g["outs"] += 1
                if random.uniform(0, 1) <= 0.32:
                    g[f"{b_team}_box"][batter["Player"]]["SO"] += 1
                    g["logs"].append(f"💨 *Strikeout!* {batter['Player']} down swinging.")
                else:
                    g["logs"].append(f"🥎 *Out!* {batter['Player']} flies out.")

            g["strategy_selected"] = False

            if g["top_half"]: g["away_idx"] += 1
            else: g["home_idx"] += 1

            scoreboard.markdown(f"### 🏟️ LIVE SCOREBOARD: {away_team} `{g['away_score']}` vs {home_team} `{g['home_score']}` (Inning {g['inning']} - Outs: {g['outs']})")
            field_viz.markdown(print_ascii_diamond(g["bases"]), unsafe_allow_html=True)
            
            away_box_display.dataframe(pd.DataFrame.from_dict(g["away_box"], orient="index"), use_container_width=True)
            home_box_display.dataframe(pd.DataFrame.from_dict(g["home_box"], orient="index"), use_container_width=True)
            
            score_diff = g["away_score"] - g["home_score"]
            base_prob = 50.0 + (score_diff * 9.5) - ((g["inning"] if not g["top_half"] else g["inning"] - 0.5) * 0.4)
            clamped_prob = max(1.0, min(99.0, base_prob))
            
            df_chart = pd.DataFrame(g["chart_data"])
            graph_viz.line_chart(df_chart.set_index("Inning"))
            ticker.markdown("\n\n".join(g["logs"][-3:]))
            time.sleep(0.05)

        g["chart_data"].append({"Inning": f"{g['inning']} {half_str}", f"{away_team} Win %": clamped_prob})
        g["outs"] = 0; g["bases"] = [None, None, None]
        if g["top_half"]: g["top_half"] = False
        else: g["top_half"] = True; g["inning"] += 1

    status_field.update(label="🏆 Framework Simulation Completed!", state="complete", expanded=False)
    st.balloons()
    
    if g["home_score"] > g["away_score"]:
        record_game_result(home_team, away_team)
        st.success(f"### 🏆 {home_team} Wins! `{g['home_score']}` - `{g['away_score']}`")
    else:
        record_game_result(away_team, home_team)
        st.info(f"### 🏆 {away_team} Wins! `{g['away_score']}` - `{g['home_score']}`")

    st.session_state["game_active"] = False
    st.session_state["final_reports"] = {"away": g["away_box"], "home": g["home_box"], "full_logs": g["logs"]}
    st.session_state["leveraged_game_state"] = None

# ----------------------------------------------------
# NEW UPGRADE: NARRATIVE GAME LOG ACCORDION
# ----------------------------------------------------
if st.session_state["final_reports"] is not None:
    fr = st.session_state["final_reports"]
    
    if "full_logs" in fr:
        st.markdown("---")
        with st.expander("📜 Complete Play-by-Play Game Narrative Log", expanded=True):
            # Reverse logs so the absolute newest critical plays show at the top of the feed
            st.text_area("Game History Transcript Tracking", value="\n".join(reversed(fr["full_logs"])), height=250)

    st.markdown("---")
    st.subheader("📊 Post-Game Box Score Ledgers")
    
    df_a = pd.DataFrame.from_dict(fr["away"], orient="index")
    df_h = pd.DataFrame.from_dict(fr["home"], orient="index")
    
    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown(f"#### {away_team} Final Stats")
        st.dataframe(df_a, use_container_width=True)
        csv_a = df_a.to_csv().encode('utf-8')
        st.download_button(f"📥 Export {away_team} Box Score (CSV)", data=csv_a, file_name=f"{away_team.replace(' ', '_')}_box.csv", mime="text/csv")
    with bc2:
        st.markdown(f"#### {home_team} Final Stats")
        st.dataframe(df_h, use_container_width=True)
        csv_h = df_h.to_csv().encode('utf-8')
        st.download_button(f"📥 Export {home_team} Box Score (CSV)", data=csv_h, file_name=f"{home_team.replace(' ', '_')}_box.csv", mime="text/csv")

# Standings Display Boards
st.markdown("---")
st.subheader("🏆 Persistent Campaign Standings Leaderboard")
if st.session_state["standings"]:
    std_list = []
    for t, s in st.session_state["standings"].items():
        tot = s["W"] + s["L"]
        std_list.append({"Franchise Team Name": t, "Wins": s["W"], "Losses": s["L"], "Win Pct": f"{(s['W']/tot if tot>0 else 0):.3f}"})
    st.dataframe(pd.DataFrame(std_list).sort_values(by="Wins", ascending=False).set_index("Franchise Team Name"), use_container_width=True)
else:
    st.caption("No matches simulated in this current runtime session yet.")
