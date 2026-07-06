# ----------------------------------------------------
# STATE RESET CALLBACK FUNCTIONS
# ----------------------------------------------------
def reset_simulation_framework():
    """Definitively force-unlocks and wipes out calculated matrices upon team changes"""
    st.session_state["lineups_locked"] = False
    st.session_state["monte_carlo_results"] = None

# ----------------------------------------------------
# CONTROL BOARD INTERFACE UI
# ----------------------------------------------------
st.sidebar.header("⚾ Enterprise Simulator Panel")
all_teams_list = list(ROSTER_DATABASE.keys())

# Dynamic Callbacks: This instructs Streamlit to wipe the slate clean BEFORE updating the dropdowns
away_selection = st.sidebar.selectbox(
    "Away Roster Array", 
    all_teams_list, 
    index=0, 
    key="away_team_widget",
    on_change=reset_simulation_framework
)

home_selection = st.sidebar.selectbox(
    "Home Roster Array", 
    all_teams_list, 
    index=1, 
    key="home_team_widget",
    on_change=reset_simulation_framework
)
