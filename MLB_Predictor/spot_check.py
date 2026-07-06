import streamlit as st
import json

# This automatically loads your team data from the file you just created
try:
    with open('MLB_Predictor/rosters.json', 'r') as f:
        ROSTER_DATABASE = json.load(f)
except FileNotFoundError:
    st.error("rosters.json file not found. Please ensure it is in the MLB_Predictor folder.")
    st.stop()

ALL_TEAMS = list(ROSTER_DATABASE.keys())

st.set_page_config(page_title="MLB Analytics", layout="wide")
st.sidebar.header("Team Selection")

away_selection = st.sidebar.selectbox("Away Roster", options=ALL_TEAMS)
home_selection = st.sidebar.selectbox("Home Roster", options=ALL_TEAMS)

st.write(f"### Current Matchup: {away_selection} vs {home_selection}")
