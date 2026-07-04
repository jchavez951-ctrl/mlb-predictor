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

# Fetch Base Rosters
away_hitter_raw = get_detailed_roster_stats(live_teams.get(away_team, 0), away_team, "hitting")
home_hitter_raw = get_detailed_roster_stats(live_teams.get(home_team, 0), home_team, "hitting")
away_pitcher_raw = get_detailed_roster_stats(live_teams.get(away_team, 0), away_team, "pitching")
home_pitcher_raw = get_detailed_roster_stats(live_teams.get(home_team, 0), home_team, "pitching")

# Filter out pure pitchers from hitting pool
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
        # Pitcher selection drop
        away_sp_choice = st.selectbox(f"Choose Starting Pitcher ({away_team})", list(away_pitcher_raw["Player"]))
        
        # 1-9 Batting selections
        away_batters = []
        default_top_away = away_hitters_pool.sort_values(by="OPS", ascending=False).head(9)["Player"].tolist()
        for slot in range(1, 10):
            def_idx = (slot - 1) if (slot - 1) < len(default_top_away) else 0
            b_choice = st.selectbox(f"Slot #{slot} Batter", list(away_hitters_pool["Player"]), index=list(away_hitters_pool["Player"]).index(default_top_away[def_idx]))
            away_batters.append(b_choice)
            
    with col_h:
        st.markdown(f"### 📋 {home_team} Lineup Card")
        # Pitcher selection drop
        home_sp_choice = st.selectbox(f"Choose Starting Pitcher ({home_team})", list(home_pitcher_raw["Player"]))
        
        # 1-9 Batting selections
        home_batters = []
        default_top_home = home_hitters_pool.sort_values(by="OPS", ascending=False).head(9)["Player"].tolist()
        for slot in range(1, 10):
            def_idx = (slot - 1) if (slot - 1) < len(default_top_home) else 0
            b_choice = st.selectbox(f"Slot #{slot} Batter ", list(home_hitters_pool["Player"]), index=list(home_hitters_pool["Player"]).index(default_top_home[def_idx]))
            home_batters.append(b_choice)

    st.markdown("---")
    if st.button("🔒 Lock Rosters & Lineups", use_container_width=True):
        # Build finalized objects into session memory
        a_sp_row = away_pitcher_raw[away_pitcher_raw["Player"] == away_sp_choice].iloc[0]
        h_sp_row = home_pitcher_raw[home_pitcher_raw["Player"] == home_sp_choice].iloc[0]
        
        # Build 1-9 Lineup tracking metrics
        a_lineup = []
        for index, name in enumerate(away_batters):
            p_row = away_hitters_pool[away_hitters_pool["Player"] == name].iloc[0].to_dict()
            p_row["Order"] = index + 1
            a_lineup.append(p_row)
            
        h_lineup = []
        for index, name in enumerate(home_batters):
            p_row = home_hitters_pool[home_hitters_pool["Player"] == name].iloc[0].to_dict()
            p_row["Order"] = index + 1
            h_lineup.append(p_row)
            
        st.session_state["ready_away_sp"] = a_sp_row.to_dict()
        st.session_state["ready_home_sp"] = h_sp_row.to_dict()
        st.session_state["ready_away_lineup"] = pd.DataFrame(a_lineup)
        st.session_state["ready_home_lineup"] = pd.DataFrame(h_lineup)
        st.session_state["away_bullpen_pool"] = home_pitcher_raw[home_pitcher_raw["Player"] != away_sp_choice]
        st.session_state["home_bullpen_pool"] = home_pitcher_raw[home_pitcher_raw["Player"] != home_sp_choice]
        st.session_state["lineups_locked"] = True
        st.sidebar.success("Lineups Secured!")
        st.rerun()

else:
    # ----------------------------------------------------
# MATCH ENVIRONMENT ACTIVE SIMULATION RUNNER
# ----------------------------------------------------
    st.sidebar.button("🔓 Unlock & Reset Lineups", on_click=lambda: st.session_state.update({"lineups_locked": False, "game_active": False, "leveraged_game_state": None}))
    
    # Extract persistent variables
    away_lineup_final = st.session_state["ready_away_lineup"]
    home_lineup_final = st.session_state["ready_home_lineup"]
    away_pitcher_active = st.session_state["ready_away_sp"]
    home_pitcher_active = st.session_state["ready_home_sp"]
    
    st.subheader("🏟️ Matchup Active: Lineup Cards Locked & Loaded")
    disp_l, disp_r = st.columns(2)
    with disp_l:
        st.markdown(f"##### {away_team}")
        st.write(f"🥎 **Starting Pitcher:** `{away_pitcher_active['Player']}` (ERA: {away_pitcher_active['ERA']} | Throws: {away_pitcher_active['Throws']})")
        st.dataframe(away_lineup_final[["Order", "Player", "Pos", "AVG", "OPS"]], use_container_width=True, hide_index=True)
    with disp_r:
        st.markdown(f"##### {home_team}")
        st.write(f"🥎 **Starting Pitcher:** `{home_pitcher_active['Player']}` (ERA: {home_pitcher_active['ERA']} | Throws: {home_pitcher_active['Throws']})")
        st.dataframe(home_lineup_final[["Order", "Player", "Pos", "AVG", "OPS"]], use_container_width=True, hide_index=True)

    st.markdown("---")
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.subheader("☀️ Weather Verification")
        if "weather" not in st.session_state:
            st.session_state["weather"] = {"temp": 72, "speed": 5, "dir": "Neutral", "mult": 1.0}
        w = st.session_state["weather"]
        st.write(f"🌡️ **Game Environment Temp:** `{w['temp']}°F` | 💨 **Wind:** `{w['speed']} MPH {w['dir']}`")
    with m_col2:
        st.subheader("🎲 Action Deck")
        if st.button("Launch Locked Game Simulation Framework", type="primary"):
            st.session_state["game_active"] = True
            st.session_state["leveraged_game_state"] = None
            st.session_state["final_reports"] = None

    # SIMULATION ENGINE CORE
    if st.session_state["game_active"] or st.session_state["leveraged_game_state"] is not None:
        if st.session_state["leveraged_game_state"] is None:
            st.session_state["leveraged_game_state"] = {
                "inning": 1, "top_half": True, "away_score": 0, "home_score": 0,
                "away_idx": 0, "home_idx": 0, "away_bf": 0, "home_bf": 0, "outs": 0,
                "bases": [None, None, None], "logs": ["🏟️ Play Ball! Lineups Locked By User Request."],
                "away_box": {p: {"AB": 0, "H": 0, "HR": 0, "RBI": 0, "SO": 0} for p in away_lineup_final["Player"]},
                "home_box": {p: {"AB": 0, "H": 0, "HR": 0, "RBI": 0, "SO": 0} for p in home_lineup_final["Player"]},
                "current_away_p": f"{away_pitcher_active['Player']} (SP)", "current_away_era": float(away_pitcher_active['ERA']), "current_away_hand": str(away_pitcher_active['Throws']),
                "current_home_p": f"{home_pitcher_active['Player']} (SP)", "current_home_era": float(home_pitcher_active['ERA']), "current_home_hand": str(home_pitcher_active['Throws']),
                "chart_data": [{"Inning": "Start", f"{away_team} Win %": 50.0}]
            }

        g = st.session_state["leveraged_game_state"]
        status_field = st.status("Simulating absolute live pitches across customized batting charts...", expanded=True)
        scoreboard = st.empty()
        
        tab_view, tab_away, tab_home = st.tabs(["🏟️ Diamond Tracker", f"📊 {away_team} Stats", f"📊 {home_team} Stats"])
        with tab_view:
            f_col, g_col = st.columns([1, 1])
            with f_col: field_viz = st.empty()
            with g_col: graph_viz = st.empty()
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
            if g["inning"] >= 10 and g["outs"] == 0 and g["bases"] == [None, None, None]:
                g["bases"][1] = "Ghost Runner"

            while g["outs"] < 3:
                if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]: break

                # Resolve Batter Iterators
                if g["top_half"]:
                    batter = away_lineup_final.iloc[g["away_idx"] % 9]
                    b_team = "away"
                    p_era = g["current_home_era"]
                    p_hand = g["current_home_hand"]
                    g["home_bf"] += 1
                else:
                    batter = home_lineup_final.iloc[g["home_idx"] % 9]
                    b_team = "home"
                    p_era = g["current_away_era"]
                    p_hand = g["current_away_hand"]
                    g["away_bf"] += 1

                # Sabermetric Pitch Formulation Calculations
                plat_mult = 1.05 if batter["Bats"] != p_hand else 0.95
                hit_p = batter["AVG"] * park_data["run_mult"] * plat_mult * (p_era / 4.2)
                
                if batter["Player"] not in g[f"{b_team}_box"]:
                    g[f"{b_team}_box"][batter["Player"]] = {"AB": 0, "H": 0, "HR": 0, "RBI": 0, "SO": 0}
                g[f"{b_team}_box"][batter["Player"]]["AB"] += 1

                # Outcome Wheel Roll
                if random.uniform(0, 1.0) <= hit_p:
                    hr_chance = (batter["HR"] / max(1, batter["AB"])) * park_data["hr_mult"]
                    roll = random.uniform(0, 1)
                    if roll <= hr_chance:
                        runs = 1 + sum([1 for r in g["bases"] if r is not None])
                        g[f"{b_team}_box"][batter["Player"]]["HR"] += 1
                        g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                        g[f"{b_team}_box"][batter["Player"]]["RBI"] += runs
                        if g["top_half"]: g["away_score"] += runs
                        else: g["home_score"] += runs
                        g["bases"] = [None, None, None]
                        g["logs"].append(f"💥 **HR!** Slot #{batter['Order']} ({batter['Player']}) crushes a {runs}-run blast!")
                    else:
                        g[f"{b_team}_box"][batter["Player"]]["H"] += 1
                        g["bases"][0] = batter["Player"]
                        g["logs"].append(f"🏃 **Single!** Slot #{batter['Order']} ({batter['Player']}) drops a clean base hit.")
                else:
                    g["outs"] += 1
                    g["logs"].append(f"🥎 *Out!* Slot #{batter['Order']} ({batter['Player']}) retires at first.")

                if g["top_half"]: g["away_idx"] += 1
                else: g["home_idx"] += 1

                # Display updates
                scoreboard.markdown(f"### 🏟️ {away_team} `{g['away_score']}` @ {home_team} `{g['home_score']}` | Inning {g['inning']} ({half_str}) | Outs: {g['outs']}")
                field_viz.markdown(print_ascii_diamond(g["bases"]), unsafe_allow_html=True)
                ticker.markdown("\n\n".join(g["logs"][-3:]))
                
                away_box_display.dataframe(pd.DataFrame.from_dict(g["away_box"], orient="index"), use_container_width=True)
                home_box_display.dataframe(pd.DataFrame.from_dict(g["home_box"], orient="index"), use_container_width=True)
                time.sleep(0.04)

            g["outs"] = 0; g["bases"] = [None, None, None]
            if g["top_half"]: g["top_half"] = False
            else: g["top_half"] = True; g["inning"] += 1

        status_field.update(label="🏆 Framework Simulation Concluded Successfully!", state="complete")
        if g["home_score"] > g["away_score"]: st.success(f"### 🏆 {home_team} Wins!")
        else: st.info(f"### 🏆 {away_team} Wins!")
        
        st.session_state["game_active"] = False
        st.session_state["final_reports"] = {"away": g["away_box"], "home": g["home_box"]}
        st.session_state["leveraged_game_state"] = None
