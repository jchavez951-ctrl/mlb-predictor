import streamlit as st
import json
import os

# 1. Get the directory where the current script (spot_check.py) is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Join that with the filename
file_path = os.path.join(current_dir, 'rosters.json')

# 3. Open it
try:
    with open(file_path, 'r') as f:
        ROSTER_DATABASE = json.load(f)
except FileNotFoundError:
    st.error(f"Could not find rosters.json at: {file_path}")
    st.stop()
    # Change the path logic to look in the parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# The '..' tells Python to look one folder up
file_path = os.path.join(current_dir, '..', 'rosters.json') 

with open(file_path, 'r') as f:
    ROSTER_DATABASE = json.load(f)
