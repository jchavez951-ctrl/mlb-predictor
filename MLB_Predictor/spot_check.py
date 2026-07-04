import streamlit as st
import requests
import random
import time
import pandas as pd

st.set_page_config(page_title="Live MLB Analytics Platform", page_icon="⚾", layout="wide")

# ----------------------------------------------------
# STATE PERSISTENCE LAYER
# ----------------------------------------------------
if "standings" not in st.session_state:
    st.session_state["standings"] = {}
if "lineups_locked" not in st.session_state:
    st.session_state["lineups_locked"] = False
if "final_reports" not in st.session_state:
    st.session_state["final_reports"] = None
if "leveraged_game_state" not in st.session_state:
    st.session_state["leveraged_game_state"] = None
if "game_active" not in st.session_state:
    st.session_state["game_active"] = False
if "away_bullpen" not in st.session_state:
    st.session_state["away_bullpen"] = []
if "home_bullpen" not in st.session_state:
    st.session_state["home_bullpen"] = []

def record_game_result(winner, loser):
    if winner not in st.session_state["standings"]: st.session_state["standings"][winner] = {"W": 0, "L": 0}
    if loser not in st.session_state["standings"]: st.session_state["standings"][loser] = {"W": 0, "L": 0}
    st.session_state["standings"][winner]["W"] += 1
    st.session_state["standings"][loser]["L"] += 1

# ----------------------------------------------------
# DATA WAREHOUSE SQUADS
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
        return {"1927 New York Yankees": 1, "2004 Boston Red Sox": 2, "New York Yankees": 3, "Boston Red Sox": 4, "Los Angeles Dodgers": 5, "San Diego Padres": 6}

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
            return pd.DataFrame([{"Player": f"Player {i+1}", "Pos": "OF", "Bats": "R", "AVG": 0.270, "OPS": 0.800, "HR": 10, "AB": 300} for i in range(12)])
        else:
            return pd.DataFrame([{"Player": f"Pitcher {i+1}", "Pos": "SP", "Throws": "R", "ERA": 3.50, "WHIP": 1.20, "SO (K)": 80, "IP": "100.0"} for i in range(5)])
    return pd.DataFrame(players_list)

# ----------------------------------------------------
# MATCHUP DESIGN SIDEBAR
# ----------------------------------------------------
st.sidebar.header("⚾ Franchise Matchup Selector")
away_team = st.sidebar.selectbox("Away Team (Visitor)", all_selectable_teams, index=0, disabled=st.session_state["lineups_locked"])
home_team = st.sidebar.selectbox("Home Team (Host)", all_selectable_teams, index=min(1, len(all_selectable_teams)-1), disabled=st.session_state["lineups_locked"])

theme_host = RETRO_TEAMS.get(home_team, TEAM_COLORS.get(home_team, {"primary": "#0C2340", "secondary": "#777777"}))
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
    st.subheader("🛠️ Strategy Room: Customize Batting Orders & Starting Pitchers")
    st.info("Set your exact starting pitcher and 1-9 batting configuration below. When you are ready, lock the lineups to open the game simulation controllers.")
    
    col_a, col_h = st.columns(2)
    with col_a:
        st.markdown(f"### 📋 {away_team} Lineup Card")
        away_sp_choice = st.selectbox(f"Choose Starting Pitcher ({away_team})", list(away_pitcher_raw["Player"]))
        away_batters = []
        default_top_away = away_hitters_pool.sort_values(by="OPS", ascending=False).head(9)["Player"].tolist()
        for slot in range(1, 10):
            def_idx = (slot - 1) if (slot - 1) < len(default_top_away) else 0
            b_choice = st.selectbox(f"Slot #{slot} Batter", list(away_hitters_pool["Player"]), index=list(away_hitters_pool["Player"]).index(default_top_away[def_idx]))
            away_batters.append(b_choice)
            
    with col_h:
        st.markdown(f"### 📋 {home_team} Lineup Card")
        home_sp_choice = st.selectbox(f"Choose Starting Pitcher ({home_team})", list(home_pitcher_raw["Player"]))
        home_batters = []
        default_top_home = home_hitters_pool.sort_values(by="OPS", ascending=False).head(9)["Player"].tolist()
        for slot in range(1, 10):
            def_idx = (slot - 1) if (slot - 1) < len(default_top_home) else 0
            b_choice = st.selectbox(f"Slot #{slot} Batter ", list(home_hitters_pool["Player"]), index=list(home_hitters_pool["Player"]).index(default_top_home[def_idx]))
            home_batters.append(b_choice)

    st.markdown("---")
    if st.button("🔒 Lock Rosters & Lineups", use_container_width=True):
        st.session_state["ready_away_sp"] = away_pitcher_raw[away_pitcher_raw["Player"] == away_sp_choice].iloc[0].to_dict()
        st.session_state["ready_home_sp"] = home_pitcher_raw[home_pitcher_raw["Player"] == home_sp_choice].iloc[0].to_dict()
        
        st.session_state["ready_away_lineup"] = pd.DataFrame([away_hitters_pool[away_hitters_pool["Player"] == name].iloc[0].to_dict() for name in away_batters])
        st.session_state["ready_away_lineup"]["Order"] = range(1, 10)
        st.session_state["ready_home_lineup"] = pd.DataFrame([home_hitters_pool[home_hitters_pool["Player"] == name].iloc[0].to_dict() for name in home_batters])
        st.session_state["ready_home_lineup"]["Order"] = range(1, 10)
        
        st.session_state["away_bullpen"] = away_pitcher_raw[away_pitcher_raw["Player"] != away_sp_choice].to_dict('records')
        st.session_state["home_bullpen"] = home_pitcher_raw[home_pitcher_raw["Player"] != home_sp_choice].to_dict('records')
        st.session_state["lineups_locked"] = True
        st.rerun()

else:
    # ----------------------------------------------------
    # MATCH ENVIRONMENT ACTIVE SIMULATION RUNNER
    # ----------------------------------------------------
    st.sidebar.button("🔓 Unlock & Reset Lineups", on_click=lambda: st.session_state.update({"lineups_locked": False, "game_active": False, "leveraged_game_state": None}))
    
    away_lineup_final = st.session_state["ready_away_lineup"]
    home_lineup_final = st.session_state["ready_home_lineup"]
    away_pitcher_active = st.session_state["ready_away_sp"]
    home_pitcher_active = st.session_state["ready_home_sp"]
    
    st.subheader("🏟️ Game Center: Roster Configuration Active")
    disp_l, disp_r = st.columns(2)
    with disp_l:
        st.markdown(f"##### {away_team}")
        st.dataframe(away_lineup_final[["Order", "Player", "Pos", "AVG", "OPS"]], use_container_width=True, hide_index=True)
    with disp_r:
        st.markdown(f"##### {home_team}")
        st.dataframe(home_lineup_final[["Order", "Player", "Pos", "AVG", "OPS"]], use_container_width=True, hide_index=True)

    st.markdown("---")
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.subheader("☀️ Weather Verification")
        if "weather" not in st.session_state:
            st.session_state["weather"] = {"temp": 75, "speed": 4, "dir": "Out to Center Field 🚀", "mult": 1.04}
        w = st.session_state["weather"]
        st.write(f"🌡️ **Game Temperature:** `{w['temp']}°F` | 💨 **Wind:** `{w['speed']} MPH {w['dir']}`")
    with m_col2:
        st.subheader("🎲 Action Deck")
        if st.button("Launch Locked Game Simulation Framework", type="primary"):
            st.session_state["game_active"] = True
            st.session_state["leveraged_game_state"] = None

    # SIMULATION ENGINE CORE
    if st.session_state["game_active"] or st.session_state["leveraged_game_state"] is not None:
        if st.session_state["leveraged_game_state"] is None:
            st.session_state["leveraged_game_state"] = {
                "inning": 1, "top_half": True, "away_score": 0, "home_score": 0,
                "away_idx": 0, "home_idx": 0, "outs": 0,
                "bases": [None, None, None], "logs": ["🏟️ Play Ball! Lineups locked."],
                "away_box": {p: {"AB": 0, "H": 0, "BB": 0, "HR": 0, "RBI": 0, "SO": 0} for p in away_lineup_final["Player"]},
                "home_box": {p: {"AB": 0, "H": 0, "BB": 0, "HR": 0, "RBI": 0, "SO": 0} for p in home_lineup_final["Player"]},
                "away_p_name": away_pitcher_active['Player'], "away_p_era": float(away_pitcher_active['ERA']), "away_p_pitches": 0, "away_p_type": "SP",
                "home_p_name": home_pitcher_active['Player'], "home_p_era": float(home_pitcher_active['ERA']), "home_p_pitches": 0, "home_p_type": "SP"
            }

        g = st.session_state["leveraged_game_state"]
        status_field = st.status("Processing full base advancement tracking tables...", expanded=True)
        scoreboard = st.empty()
        
        tab_view, tab_away, tab_home = st.tabs(["🏟️ Diamond Tracker", f"📊 {away_team} Box", f"📊 {home_team} Box"])
        with tab_view:
            f_col, g_col = st.columns([1, 1])
            with f_col: field_viz = st.empty()
            with g_col: staff_viz = st.empty()
            ticker = st.empty()
            
        with tab_away: away_box_display = st.empty()
        with tab_home: home_box_display = st.empty()

        park_data = BALLPARK_MODIFIERS.get(home_team, DEFAULT_BALLPARK)

        def print_ascii_diamond(runners):
            b1 = "🟥" if runners[0] else "⬜"
            b2 = "🟥" if runners[1] else "⬜"
            b3 = "🟥" if runners[2] else "⬜"
            return f"<pre style='line-height:1.2; font-weight:bold;'>       [{b2}] 2nd\n       /   \\\n3rd [{b3}]     [{b1}] 1st\n       \\   /\n       [🏃] Home</pre>"

        while g["inning"] <= 9 or (g["away_score"] == g["home_score"]):
            half_str = "Top" if g["top_half"] else "Bottom"

            while g["outs"] < 3:
                if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]: break

                # Safe Bullpen Checks using .get() to completely prevent KeyErrors
                away_bp_pool = st.session_state.get("away_bullpen", [])
                home_bp_pool = st.session_state.get("home_bullpen", [])

                # Manager AI: Bullpen Deployment & Fatigue Math
                if g["top_half"]:
                    g["home_p_pitches"] += random.randint(3, 6)
                    if g["home_p_pitches"] > 90 and g["home_p_type"] == "SP" and len(home_bp_pool) > 0:
                        reliever = random.choice(home_bp_pool)
                        g["home_p_name"] = reliever["Player"] + " (RP)"
                        g["home_p_era"] = float(reliever["ERA"])
                        g["home_p_pitches"] = 0
                        g["home_p_type"] = "RP"
                        g["logs"].append(f"📣 **Pitching Change:** {home_team} brings in reliever {g['home_p_name']}.")
                    p_name, p_era, p_pitches = g["home_p_name"], g["home_p_era"], g["home_p_pitches"]
                    batter = away_lineup_final.iloc[g["away_idx"] % 9]
                    b_team = "away"
                else:
                    g["away_p_pitches"] += random.randint(3, 6)
                    if g["away_p_pitches"] > 90 and g["away_p_type"] == "SP" and len(away_bp_pool) > 0:
                        reliever = random.choice(away_bp_pool)
                        g["away_p_name"] = reliever["Player"] + " (RP)"
                        g["away_p_era"] = float(reliever["ERA"])
                        g["away_p_pitches"] = 0
                        g["away_p_type"] = "RP"
                        g["logs"].append(f"📣 **Pitching Change:** {away_team} brings in reliever {g['away_p_name']}.")
                    p_name, p_era, p_pitches = g["away_p_name"], g["away_p_era"], g["away_p_pitches"]
                    batter = home_lineup_final.iloc[g["home_idx"] % 9]
                    b_team = "home"

                # Apply Fatigue Multiplier to Pitcher ERA
                fatigue_mult = 1.25 if p_pitches > 85 else 1.0
                effective_era = p_era * fatigue_mult

                # 1. BB / OBP Checklist
                bb_chance = 0.08 * (effective_era / 4.0)
                if random.uniform(0, 1) < bb_chance:
                    g[f"{b_team}_box"][batter["Player"]]["BB"] += 1
                    g["logs"].append(f"🟢 **Walk!** {batter['Player']} works a full-count base on balls.")
                    # Base progression for walk
                    if g["bases"][0]:
                        if g["bases"][1]:
                            if g["bases"][2]:
                                if g["top_half"]: g["away_score"] += 1
                                else: g["home_score"] += 1
                                g[f"{b_team}_box"][batter["Player"]]["RBI"] += 1
                            g["bases"][2] = g["bases"][1]
                        g["bases"][1] = g["bases"][0]
                    g["bases"][0] = batter["Player"]
                else:
                    # Player actually registers an official At-Bat
                    g[f"{b_team}_box"][batter["Player"]]["AB"] += 1
                    hit_p = batter["AVG"] * park_data["run_mult"] * (effective_era / 4.1)

                    if random.uniform(0, 1.0) <= hit_p:
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
                            g["logs"].append(f"💥 **HR!** {batter['Player']} absolute moonshot! `{runs}-run` home run!")
                        elif roll <= hr_chance + 0.22:
                            # Accurate Double Progression Matrix
                            runs = sum([1 for r in g["bases"][1:] if r is not None])
                            if g["bases"][0] and random.uniform(0, 1) < 0.45: # 45% runner from 1st scores
                                runs += 1
                                g["bases"][0] = None
                            g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                            g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                            if g["top_half"]: g["away_score"] += runs
                            else: g["home_score"] += runs
                            g["bases"][2] = g["bases"][0]; g["bases"][1] = batter["Player"]; g["bases"][0] = None
                            g["logs"].append(f"⚾ **Double!** {batter['Player']} rips a bullet into the gap.")
                        else:
                            # Accurate Single Progression Matrix
                            runs = 1 if g["bases"][2] else 0
                            g["bases"][2] = None
                            if g["bases"][1] and random.uniform(0, 1) < 0.60: # 60% runner from 2nd scores on single
                                runs += 1
                                g["bases"][1] = None
                            g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                            g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                            if g["top_half"]: g["away_score"] += runs
                            else: g["home_score"] += runs
                            g["bases"][2] = g["bases"][1]; g["bases"][1] = g["bases"][0]; g["bases"][0] = batter["Player"]
                            g["logs"].append(f"🏃 **Single!** {batter['Player']} hits a clean single to outfield.")
                    else:
                        g["outs"] += 1
                        if random.uniform(0, 1) <= 0.25:
                            g[f"{b_team}_box"][batter["Player"]]["SO"] += 1
                            g["logs"].append(f"💨 *Strikeout!* {batter['Player']} chasing high heat.")
                        else:
                            # Sac Fly Check
                            if g["outs"] < 3 and g["bases"][2] and random.uniform(0, 1) < 0.10:
                                if g["top_half"]: g["away_score"] += 1
                                else: g["home_score"] += 1
                                g[f"{b_team}_box"][batter["Player"]]["RBI"] += 1
                                g["bases"][2] = None
                                g["logs"].append(f"📐 *Sacrifice Fly!* {batter['Player']} drives home a run on a deep out.")
                            else:
                                g["logs"].append(f"🥎 *Out!* {batter['Player']} grounds out to center.")

                if g["top_half"]: g["away_idx"] += 1
                else: g["home_idx"] += 1

                # Update Display Cards
                scoreboard.markdown(f"### 🏟️ {away_team} `{g['away_score']}` @ {home_team} `{g['home_score']}` | Inning {g['inning']} ({half_str}) | Outs: {g['outs']}")
                field_viz.markdown(print_ascii_diamond(g["bases"]), unsafe_allow_html=True)
                
                staff_viz.markdown(f"""
                **Live Pitching Matrix**
                * **Away Mound:** `{g['away_p_name']}` — `{g['away_p_pitches']}` Pitches (ERA: {g['away_p_era']})
                * **Home Mound:** `{g['home_p_name']}` — `{g['home_p_pitches']}` Pitches (ERA: {g['home_p_era']})
                """)
                
                ticker.markdown("\n\n".join(g["logs"][-3:]))
                away_box_display.dataframe(pd.DataFrame.from_dict(g["away_box"], orient="index"), use_container_width=True)
                home_box_display.dataframe(pd.DataFrame.from_dict(g["home_box"], orient="index"), use_container_width=True)
                time.sleep(0.04)

            g["outs"] = 0; g["bases"] = [None, None, None]
            if g["top_half"]: g["top_half"] = False
            else: g["top_half"] = True; g["inning"] += 1

        status_field.update(label="🏆 Campaign Game Simulation Finalized!", state="complete")
        if g["home_score"] > g["away_score"]: st.success(f"### 🏆 {home_team} Wins! {g['home_score']} - {g['away_score']}")
        else: st.info(f"### 🏆 {away_team} Wins! {g['away_score']} - {g['home_score']}")
            
        st.session_state["game_active"] = False
        st.session_state["leveraged_game_state"] = None
