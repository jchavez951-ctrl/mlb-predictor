import streamlit as st
import numpy as np
import pandas as pd

# ----------------------------------------------------
# 1. ROSTER DATABASE
# ----------------------------------------------------
ROSTER_DATABASE = {
    "Athletics": {
        "primary": "#003831", "secondary": "#EFB21E",
        "hitting": [{"Player": "Nick Kurtz", "Pos": "1B", "Bats": "L", "BB_RATE": 0.135, "K_RATE": 0.210, "HR_PA_RATE": 0.045, "BABIP": 0.315, "1B_H_RATE": 0.58, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 65, "PA": 450}],
        "pitching": [{"Player": "Mason Miller", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.385, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.265, "OAVG": 0.185, "IP": "75.0", "ERA": 2.10, "Fatigue": 0.0}]
    },
    "Baltimore Orioles": {
        "primary": "#DF4618", "secondary": "#000000",
        "hitting": [{"Player": "Adley Rutschman", "Pos": "C", "Bats": "B", "BB_RATE": 0.110, "K_RATE": 0.155, "HR_PA_RATE": 0.035, "BABIP": 0.295, "1B_H_RATE": 0.64, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.13, "SPD": 50, "PA": 650}],
        "pitching": [{"Player": "Corbin Burnes", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.250, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.280, "OAVG": 0.215, "IP": "194.1", "ERA": 2.95, "Fatigue": 0.0}]
    },
    "New York Yankees": {
        "primary": "#1C2841", "secondary": "#FFFFFF",
        "hitting": [{"Player": "Aaron Judge", "Pos": "RF", "Bats": "R", "BB_RATE": 0.150, "K_RATE": 0.250, "HR_PA_RATE": 0.080, "BABIP": 0.320, "1B_H_RATE": 0.40, "2B_H_RATE": 0.20, "3B_H_RATE": 0.01, "HR_H_RATE": 0.39, "SPD": 60, "PA": 600}],
        "pitching": [{"Player": "Gerrit Cole", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.060, "K_ALLOWED_RATE": 0.280, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.270, "OAVG": 0.200, "IP": "180.0", "ERA": 3.00, "Fatigue": 0.0}]
    }
}

# ----------------------------------------------------
# 2. DEFINITIONS & ALIASES
# ----------------------------------------------------
# Using a single source of truth for the team list
ALL_TEAMS = list(ROSTER_DATABASE.keys())
all_teams_list = ALL_TEAMS 

# ----------------------------------------------------
# 3. UI RENDER
# ----------------------------------------------------
st.set_page_config(page_title="MLB Analytics", layout="wide")
st.sidebar.header("Team Selection")

away_selection = st.sidebar.selectbox("Away Roster Array", options=ALL_TEAMS, key="away_team_select")
home_selection = st.sidebar.selectbox("Home Roster Array", options=ALL_TEAMS, key="home_team_select")

st.write(f"### Current Matchup: {away_selection} vs {home_selection}")

# Displaying the raw data for validation
st.write("---")
st.write("#### Available Team Data Keys:")
st.write(ALL_TEAMS)
