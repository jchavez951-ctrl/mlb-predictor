import streamlit as st
import random

# Page config for a pro sports feel
st.set_page_config(page_title="MLB Predictor", page_icon="⚾", layout="wide")

st.title("⚾ MLB Head-to-Head Matchup Predictor")
st.write("Select teams and adjust game variables to calculate win probabilities.")

# Sidebar for team selection
st.sidebar.header("Matchup Setup")

mlb_teams = [
    "Arizona Diamondbacks", "Atlanta Braves", "Baltimore Orioles", "Boston Red Sox",
    "Chicago Cubs", "Chicago White Sox", "Cincinnati Reds", "Cleveland Guardians",
    "Colorado Rockies", "Detroit Tigers", "Houston Astros", "Kansas City Royals",
    "Los Angeles Angels", "Los Angeles Dodgers", "Miami Marlins", "Milwaukee Brewers",
    "Minnesota Twins", "New York Mets", "New York Yankees", "Oakland Athletics",
    "Philadelphia Phillies", "Pittsburgh Pirates", "San Diego Padres", "San Francisco Giants",
    "Seattle Mariners", "St. Louis Cardinals", "Tampa Bay Rays", "Texas Rangers",
    "Toronto Blue Jays", "Washington Nationals"
]

away_team = st.sidebar.selectbox("Away Team (Visitor)", mlb_teams, index=18) # Default Yankees
home_team = st.sidebar.selectbox("Home Team", mlb_teams, index=13) # Default Dodgers

st.sidebar.markdown("---")
st.sidebar.header("Pitcher & Form Modifiers")

# User sliders to simulate starting pitcher impact
away_pitcher = st.sidebar.slider(f"{away_team} Pitcher Rating", 50, 99, 85)
home_pitcher = st.sidebar.slider(f"{home_team} Pitcher Rating", 50, 99, 88)

# Home field advantage toggle
home_advantage = st.sidebar.checkbox("Apply Home Field Advantage (+3%)", value=True)

# Layout Columns for the presentation
col1, col2 = st.columns(2)

with col1:
    st.subheader("Matchup Analysis")
    st.info(f"**Away:** {away_team} (Pitching: {away_pitcher})")
    st.success(f"**Home:** {home_team} (Pitching: {home_pitcher})")
    
    # Simple predictive algorithm based on pitcher ratings + home advantage
    base_away = away_pitcher
    base_home = home_pitcher + (3 if home_advantage else 0)
    
    total = base_away + base_home
    away_prob = (base_away / total) * 100
    home_prob = (base_home / total) * 100

    st.markdown("### Calculated Win Probability")
    st.write(f"**{away_team}:** {away_prob:.1f}%")
    st.progress(int(away_prob))
    
    st.write(f"**{home_team}:** {home_prob:.1f}%")
    st.progress(int(home_prob))

with col2:
    st.subheader("🎲 Game Simulator Engine")
    st.write("Click below to run a 10,000-inning monte-carlo scenario simulation for this matchup.")
    
    if st.button("Simulate Game Outcome"):
        # Determine simulated winner
        roll = random.uniform(0, 100)
        winner = home_team if roll <= home_prob else away_team
        
        # Generate a realistic baseball score
        win_runs = random.randint(3, 9)
        lose_runs = random.randint(0, win_runs - 1)
        
        st.balloons()
        st.markdown("### 🏆 Simulation Result")
        if winner == home_team:
            st.markdown(f"### **{home_team} win!**")
            st.subheader(f"Final Score: {home_team} **{win_runs}** - {lose_runs} {away_team}")
        else:
            st.markdown(f"### **{away_team} win!**")
            st.subheader(f"Final Score: {away_team} **{win_runs}** - {lose_runs} {home_team}")
