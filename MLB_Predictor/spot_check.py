import streamlit as st
import numpy as np
import pandas as pd
import random
import time
import copy

st.set_page_config(page_title="Ultimate MLB Analytics Platform v2", page_icon="⚾", layout="wide")

# ----------------------------------------------------
# SYSTEM STATE PERSISTENCE & FAULT-TOLERANT INITIALIZATION
# ----------------------------------------------------
if "lineups_locked" not in st.session_state:
    st.session_state["lineups_locked"] = False
if "monte_carlo_results" not in st.session_state:
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

# Unified player data matrices with built-in advanced sabermetric metrics
ROSTER_DATABASE_FALLBACK = {
    "Athletics": {
        "primary": "#003831", "secondary": "#EFB21E",
        "hitting": [
            {"Player": "Joshua Kuroda-Grauer", "Pos": "3B", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.21, "HR_PA_RATE": 0.010, "BABIP": 0.31, "1B_H_RATE": 0.60, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 60, "PA": 300},
            {"Player": "Shea Langeliers", "Pos": "C", "Bats": "R", "BB_RATE": 0.082, "K_RATE": 0.255, "HR_PA_RATE": 0.052, "BABIP": 0.27, "1B_H_RATE": 0.52, "2B_H_RATE": 0.2, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 55, "PA": 510},
            {"Player": "Nick Kurtz", "Pos": "DH", "Bats": "L", "BB_RATE": 0.135, "K_RATE": 0.21, "HR_PA_RATE": 0.045, "BABIP": 0.315, "1B_H_RATE": 0.58, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 65, "PA": 450},
            {"Player": "Jonah Heim", "Pos": "1B", "Bats": "B", "BB_RATE": 0.075, "K_RATE": 0.195, "HR_PA_RATE": 0.028, "BABIP": 0.28, "1B_H_RATE": 0.65, "2B_H_RATE": 0.22, "3B_H_RATE": 0.0, "HR_H_RATE": 0.13, "SPD": 45, "PA": 420},
            {"Player": "Jacob Wilson", "Pos": "SS", "Bats": "R", "BB_RATE": 0.035, "K_RATE": 0.115, "HR_PA_RATE": 0.018, "BABIP": 0.290, "1B_H_RATE": 0.66, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.08, "SPD": 55, "PA": 580},
            {"Player": "Zack Gelof", "Pos": "LF", "Bats": "R", "BB_RATE": 0.088, "K_RATE": 0.29, "HR_PA_RATE": 0.038, "BABIP": 0.305, "1B_H_RATE": 0.59, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.15, "SPD": 85, "PA": 540},
            {"Player": "Colby Thomas", "Pos": "RF", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.25, "HR_PA_RATE": 0.028, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 60, "PA": 380},
            {"Player": "Henry Bolte", "Pos": "CF", "Bats": "R", "BB_RATE": 0.105, "K_RATE": 0.31, "HR_PA_RATE": 0.04, "BABIP": 0.33, "1B_H_RATE": 0.55, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.18, "SPD": 88, "PA": 310},
            {"Player": "Alika Williams", "Pos": "2B", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.22, "HR_PA_RATE": 0.01, "BABIP": 0.295, "1B_H_RATE": 0.78, "2B_H_RATE": 0.16, "3B_H_RATE": 0.04, "HR_H_RATE": 0.02, "SPD": 78, "PA": 280},
        ],
        "pitching": [
            {"Player": "Mason Miller", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.385, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.265, "OAVG": 0.185, "IP": "75.0", "ERA": 2.1, "Fatigue": 0.0},
            {"Player": "JP Sears", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.072, "K_ALLOWED_RATE": 0.21, "HR_PA_ALLOWED_RATE": 0.038, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "175.1", "ERA": 4.25, "Fatigue": 0.0},
            {"Player": "T.J. McFarland", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.19, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "55.0", "ERA": 3.9, "Fatigue": 0.0},
            {"Player": "Tyler Ferguson", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.275, "OAVG": 0.225, "IP": "55.0", "ERA": 3.4, "Fatigue": 0.0},
            {"Player": "Luis Severino", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Gage Jump", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.095, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.29, "OAVG": 0.235, "IP": "38.0", "ERA": 4.50, "Fatigue": 0.0},
            {"Player": "Joey Estes", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Justin Sterner", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Grant Holman", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Jose Suarez", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.20, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.250, "IP": "60.0", "ERA": 4.56, "Fatigue": 0.0},
        ]
    },
    "Baltimore Orioles": {
        "primary": "#DF4618", "secondary": "#000000",
        "hitting": [
            {"Player": "Adley Rutschman", "Pos": "C", "Bats": "B", "BB_RATE": 0.11, "K_RATE": 0.155, "HR_PA_RATE": 0.035, "BABIP": 0.295, "1B_H_RATE": 0.64, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.13, "SPD": 50, "PA": 650},
            {"Player": "Gunnar Henderson", "Pos": "SS", "Bats": "L", "BB_RATE": 0.125, "K_RATE": 0.22, "HR_PA_RATE": 0.058, "BABIP": 0.335, "1B_H_RATE": 0.54, "2B_H_RATE": 0.24, "3B_H_RATE": 0.04, "HR_H_RATE": 0.18, "SPD": 86, "PA": 680},
            {"Player": "Dylan Beavers", "Pos": "RF", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.27, "HR_PA_RATE": 0.016, "BABIP": 0.28, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 60, "PA": 250},
            {"Player": "Blaze Alexander", "Pos": "3B", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.235, "HR_PA_RATE": 0.020, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.17, "SPD": 65, "PA": 400},
            {"Player": "Pete Alonso", "Pos": "1B", "Bats": "R", "BB_RATE": 0.11, "K_RATE": 0.195, "HR_PA_RATE": 0.052, "BABIP": 0.28, "1B_H_RATE": 0.44, "2B_H_RATE": 0.24, "3B_H_RATE": 0.0, "HR_H_RATE": 0.32, "SPD": 35, "PA": 630},
            {"Player": "Colton Cowser", "Pos": "CF", "Bats": "L", "BB_RATE": 0.102, "K_RATE": 0.285, "HR_PA_RATE": 0.045, "BABIP": 0.31, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 80, "PA": 500},
            {"Player": "Taylor Ward", "Pos": "LF", "Bats": "R", "BB_RATE": 0.09, "K_RATE": 0.21, "HR_PA_RATE": 0.030, "BABIP": 0.28, "1B_H_RATE": 0.50, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.23, "SPD": 45, "PA": 500},
            {"Player": "Samuel Basallo", "Pos": "DH", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.235, "HR_PA_RATE": 0.038, "BABIP": 0.29, "1B_H_RATE": 0.48, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.26, "SPD": 40, "PA": 380},
            {"Player": "Jackson Holliday", "Pos": "2B", "Bats": "L", "BB_RATE": 0.115, "K_RATE": 0.26, "HR_PA_RATE": 0.03, "BABIP": 0.315, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.03, "HR_H_RATE": 0.13, "SPD": 82, "PA": 460},
        ],
        "pitching": [
            {"Player": "Corbin Burnes", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.25, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "194.1", "ERA": 2.95, "Fatigue": 0.0},
            {"Player": "Grayson Rodriguez", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.265, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.295, "OAVG": 0.23, "IP": "162.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Yennier Cano", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.015, "BABIP_ALLOWED": 0.29, "OAVG": 0.225, "IP": "70.0", "ERA": 2.85, "Fatigue": 0.0},
            {"Player": "Felix Bautista", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.34, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.195, "IP": "60.0", "ERA": 2.50, "Fatigue": 0.0},
            {"Player": "Zach Eflin", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Trevor Rogers", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.275, "OAVG": 0.205, "IP": "175.0", "ERA": 2.20, "Fatigue": 0.0},
            {"Player": "Cade Povich", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Bryan Baker", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Keegan Akin", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Dillon Tate", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "New York Yankees": {
        "primary": "#0C2340", "secondary": "#C4CED4",
        "hitting": [
            {"Player": "Jasson Dominguez", "Pos": "RF", "Bats": "B", "BB_RATE": 0.06, "K_RATE": 0.27, "HR_PA_RATE": 0.020, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 65, "PA": 250},
            {"Player": "Ben Rice", "Pos": "DH", "Bats": "L", "BB_RATE": 0.115, "K_RATE": 0.225, "HR_PA_RATE": 0.042, "BABIP": 0.290, "1B_H_RATE": 0.48, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.26, "SPD": 45, "PA": 520},
            {"Player": "Cody Bellinger", "Pos": "LF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.137, "HR_PA_RATE": 0.032, "BABIP": 0.29, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.20, "SPD": 60, "PA": 600},
            {"Player": "Amed Rosario", "Pos": "3B", "Bats": "R", "BB_RATE": 0.045, "K_RATE": 0.145, "HR_PA_RATE": 0.028, "BABIP": 0.28, "1B_H_RATE": 0.60, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 62, "PA": 250},
            {"Player": "Jose Caballero", "Pos": "SS", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.20, "HR_PA_RATE": 0.012, "BABIP": 0.29, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 72, "PA": 480},
            {"Player": "Austin Wells", "Pos": "C", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.23, "HR_PA_RATE": 0.035, "BABIP": 0.285, "1B_H_RATE": 0.55, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.18, "SPD": 45, "PA": 480},
            {"Player": "Jazz Chisholm Jr.", "Pos": "2B", "Bats": "L", "BB_RATE": 0.082, "K_RATE": 0.245, "HR_PA_RATE": 0.042, "BABIP": 0.31, "1B_H_RATE": 0.55, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.18, "SPD": 88, "PA": 560},
            {"Player": "Trent Grisham", "Pos": "CF", "Bats": "L", "BB_RATE": 0.105, "K_RATE": 0.225, "HR_PA_RATE": 0.038, "BABIP": 0.27, "1B_H_RATE": 0.55, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 70, "PA": 470},
            {"Player": "Paul Goldschmidt", "Pos": "1B", "Bats": "R", "BB_RATE": 0.085, "K_RATE": 0.185, "HR_PA_RATE": 0.028, "BABIP": 0.3, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 42, "PA": 520},
        ],
        "pitching": [
            {"Player": "Gerrit Cole", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.058, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.285, "OAVG": 0.22, "IP": "180.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Max Fried", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.275, "OAVG": 0.23, "IP": "170.0", "ERA": 3.1, "Fatigue": 0.0},
            {"Player": "Jake Cousins", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.27, "OAVG": 0.210, "IP": "60.0", "ERA": 3.10, "Fatigue": 0.0},
            {"Player": "Fernando Cruz", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.10, "K_ALLOWED_RATE": 0.32, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.26, "OAVG": 0.20, "IP": "58.0", "ERA": 2.80, "Fatigue": 0.0},
            {"Player": "Marcus Stroman", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Clarke Schmidt", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Will Warren", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Ian Hamilton", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Tim Hill", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Paul Blackburn", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.20, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.28, "OAVG": 0.230, "IP": "50.0", "ERA": 2.90, "Fatigue": 0.0},
        ]
    },
    "Los Angeles Dodgers": {
        "primary": "#005A9C", "secondary": "#EF3E42",
        "hitting": [
            {"Player": "Shohei Ohtani", "Pos": "DH", "Bats": "L", "BB_RATE": 0.14, "K_RATE": 0.245, "HR_PA_RATE": 0.068, "BABIP": 0.32, "1B_H_RATE": 0.46, "2B_H_RATE": 0.2, "3B_H_RATE": 0.03, "HR_H_RATE": 0.31, "SPD": 82, "PA": 660},
            {"Player": "Mookie Betts", "Pos": "SS", "Bats": "R", "BB_RATE": 0.115, "K_RATE": 0.135, "HR_PA_RATE": 0.038, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.17, "SPD": 70, "PA": 630},
            {"Player": "Freddie Freeman", "Pos": "1B", "Bats": "L", "BB_RATE": 0.112, "K_RATE": 0.145, "HR_PA_RATE": 0.032, "BABIP": 0.32, "1B_H_RATE": 0.55, "2B_H_RATE": 0.3, "3B_H_RATE": 0.01, "HR_H_RATE": 0.14, "SPD": 45, "PA": 610},
            {"Player": "Teoscar Hernandez", "Pos": "RF", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.235, "HR_PA_RATE": 0.048, "BABIP": 0.3, "1B_H_RATE": 0.5, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.25, "SPD": 55, "PA": 580},
            {"Player": "Dalton Rushing", "Pos": "C", "Bats": "L", "BB_RATE": 0.095, "K_RATE": 0.20, "HR_PA_RATE": 0.032, "BABIP": 0.29, "1B_H_RATE": 0.48, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.25, "SPD": 45, "PA": 400},
            {"Player": "Max Muncy", "Pos": "3B", "Bats": "L", "BB_RATE": 0.145, "K_RATE": 0.265, "HR_PA_RATE": 0.045, "BABIP": 0.28, "1B_H_RATE": 0.44, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.29, "SPD": 35, "PA": 470},
            {"Player": "Tommy Edman", "Pos": "2B", "Bats": "B", "BB_RATE": 0.068, "K_RATE": 0.16, "HR_PA_RATE": 0.025, "BABIP": 0.285, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.03, "HR_H_RATE": 0.13, "SPD": 84, "PA": 520},
            {"Player": "Kyle Tucker", "Pos": "LF", "Bats": "L", "BB_RATE": 0.115, "K_RATE": 0.165, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.5, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.23, "SPD": 65, "PA": 400},
            {"Player": "Andy Pages", "Pos": "CF", "Bats": "R", "BB_RATE": 0.062, "K_RATE": 0.225, "HR_PA_RATE": 0.03, "BABIP": 0.295, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 65, "PA": 480},
        ],
        "pitching": [
            {"Player": "Tyler Glasnow", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.068, "K_ALLOWED_RATE": 0.32, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.28, "OAVG": 0.205, "IP": "140.0", "ERA": 3.3, "Fatigue": 0.0},
            {"Player": "Yoshinobu Yamamoto", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.275, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.275, "OAVG": 0.215, "IP": "165.0", "ERA": 2.95, "Fatigue": 0.0},
            {"Player": "Blake Treinen", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.295, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.275, "OAVG": 0.21, "IP": "62.0", "ERA": 2.6, "Fatigue": 0.0},
            {"Player": "Edwin Diaz", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.34, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.26, "OAVG": 0.185, "IP": "62.0", "ERA": 2.10, "Fatigue": 0.0},
            {"Player": "Emmet Sheehan", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "120.0", "ERA": 4.10, "Fatigue": 0.0},
            {"Player": "Blake Snell", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.095, "K_ALLOWED_RATE": 0.30, "HR_PA_ALLOWED_RATE": 0.020, "BABIP_ALLOWED": 0.275, "OAVG": 0.205, "IP": "155.0", "ERA": 2.90, "Fatigue": 0.0},
            {"Player": "Roki Sasaki", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.260, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.280, "OAVG": 0.215, "IP": "130.0", "ERA": 3.35, "Fatigue": 0.0},
            {"Player": "Evan Phillips", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Alex Vesia", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Michael Kopech", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Atlanta Braves": {
        "primary": "#CE1141", "secondary": "#13274F",
        "hitting": [
            {"Player": "Ronald Acuna Jr.", "Pos": "RF", "Bats": "R", "BB_RATE": 0.115, "K_RATE": 0.195, "HR_PA_RATE": 0.045, "BABIP": 0.33, "1B_H_RATE": 0.52, "2B_H_RATE": 0.22, "3B_H_RATE": 0.03, "HR_H_RATE": 0.23, "SPD": 92, "PA": 620},
            {"Player": "Matt Olson", "Pos": "1B", "Bats": "L", "BB_RATE": 0.115, "K_RATE": 0.215, "HR_PA_RATE": 0.045, "BABIP": 0.28, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 40, "PA": 630},
            {"Player": "Austin Riley", "Pos": "3B", "Bats": "R", "BB_RATE": 0.088, "K_RATE": 0.235, "HR_PA_RATE": 0.042, "BABIP": 0.3, "1B_H_RATE": 0.5, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.24, "SPD": 45, "PA": 590},
            {"Player": "Ozzie Albies", "Pos": "2B", "Bats": "B", "BB_RATE": 0.058, "K_RATE": 0.155, "HR_PA_RATE": 0.032, "BABIP": 0.275, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 78, "PA": 580},
            {"Player": "Drake Baldwin", "Pos": "C", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.195, "HR_PA_RATE": 0.030, "BABIP": 0.300, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 45, "PA": 480},
            {"Player": "Marcell Ozuna", "Pos": "DH", "Bats": "R", "BB_RATE": 0.1, "K_RATE": 0.245, "HR_PA_RATE": 0.05, "BABIP": 0.29, "1B_H_RATE": 0.46, "2B_H_RATE": 0.24, "3B_H_RATE": 0.0, "HR_H_RATE": 0.3, "SPD": 30, "PA": 560},
            {"Player": "Michael Harris II", "Pos": "CF", "Bats": "L", "BB_RATE": 0.055, "K_RATE": 0.185, "HR_PA_RATE": 0.03, "BABIP": 0.3, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.15, "SPD": 80, "PA": 540},
            {"Player": "Orlando Arcia", "Pos": "SS", "Bats": "R", "BB_RATE": 0.05, "K_RATE": 0.17, "HR_PA_RATE": 0.022, "BABIP": 0.27, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 58, "PA": 460},
            {"Player": "Mike Yastrzemski", "Pos": "LF", "Bats": "L", "BB_RATE": 0.1, "K_RATE": 0.215, "HR_PA_RATE": 0.03, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.2, "SPD": 45, "PA": 420},
        ],
        "pitching": [
            {"Player": "Chris Sale", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.31, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.28, "OAVG": 0.21, "IP": "175.0", "ERA": 2.85, "Fatigue": 0.0},
            {"Player": "Spencer Schwellenbach", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.05, "K_ALLOWED_RATE": 0.245, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.235, "IP": "160.0", "ERA": 3.5, "Fatigue": 0.0},
            {"Player": "Pierce Johnson", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "65.0", "ERA": 3.0, "Fatigue": 0.0},
            {"Player": "Raisel Iglesias", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.27, "OAVG": 0.205, "IP": "60.0", "ERA": 2.75, "Fatigue": 0.0},
            {"Player": "Reynaldo Lopez", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Bryce Elder", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "AJ Smith-Shawver", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Joe Jimenez", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Aaron Bummer", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Dylan Lee", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Houston Astros": {
        "primary": "#002D62", "secondary": "#EB6E1F",
        "hitting": [
            {"Player": "Yordan Alvarez", "Pos": "DH", "Bats": "L", "BB_RATE": 0.135, "K_RATE": 0.185, "HR_PA_RATE": 0.058, "BABIP": 0.31, "1B_H_RATE": 0.46, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.29, "SPD": 35, "PA": 560},
            {"Player": "Jose Altuve", "Pos": "2B", "Bats": "R", "BB_RATE": 0.078, "K_RATE": 0.135, "HR_PA_RATE": 0.032, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 68, "PA": 640},
            {"Player": "Yainer Diaz", "Pos": "C", "Bats": "R", "BB_RATE": 0.045, "K_RATE": 0.155, "HR_PA_RATE": 0.032, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 42, "PA": 520},
            {"Player": "Isaac Paredes", "Pos": "3B", "Bats": "R", "BB_RATE": 0.11, "K_RATE": 0.15, "HR_PA_RATE": 0.038, "BABIP": 0.25, "1B_H_RATE": 0.46, "2B_H_RATE": 0.28, "3B_H_RATE": 0.0, "HR_H_RATE": 0.26, "SPD": 35, "PA": 570},
            {"Player": "Christian Walker", "Pos": "1B", "Bats": "R", "BB_RATE": 0.095, "K_RATE": 0.225, "HR_PA_RATE": 0.038, "BABIP": 0.28, "1B_H_RATE": 0.48, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.25, "SPD": 45, "PA": 560},
            {"Player": "Jeremy Pena", "Pos": "SS", "Bats": "R", "BB_RATE": 0.058, "K_RATE": 0.2, "HR_PA_RATE": 0.03, "BABIP": 0.295, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 72, "PA": 600},
            {"Player": "Chas McCormick", "Pos": "CF", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.235, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.55, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.18, "SPD": 74, "PA": 470},
            {"Player": "Cam Smith", "Pos": "RF", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.22, "HR_PA_RATE": 0.028, "BABIP": 0.31, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 60, "PA": 500},
            {"Player": "Victor Caratini", "Pos": "C", "Bats": "B", "BB_RATE": 0.085, "K_RATE": 0.17, "HR_PA_RATE": 0.018, "BABIP": 0.28, "1B_H_RATE": 0.66, "2B_H_RATE": 0.2, "3B_H_RATE": 0.0, "HR_H_RATE": 0.1, "SPD": 38, "PA": 300},
        ],
        "pitching": [
            {"Player": "Colton Gordon", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.225, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.285, "OAVG": 0.240, "IP": "150.0", "ERA": 3.90, "Fatigue": 0.0},
            {"Player": "Hunter Brown", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.068, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "180.0", "ERA": 2.9, "Fatigue": 0.0},
            {"Player": "Bryan Abreu", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.32, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.205, "IP": "65.0", "ERA": 2.9, "Fatigue": 0.0},
            {"Player": "Josh Hader", "Pos": "P", "Role": "Closer", "Throws": "L", "BB_ALLOWED_RATE": 0.11, "K_ALLOWED_RATE": 0.36, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.25, "OAVG": 0.18, "IP": "58.0", "ERA": 2.4, "Fatigue": 0.0},
            {"Player": "Lance McCullers Jr.", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Cristian Javier", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Spencer Arrighetti", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Rafael Montero", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Ryan Pressly", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Bryan King", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Philadelphia Phillies": {
        "primary": "#E81828", "secondary": "#002D72",
        "hitting": [
            {"Player": "Bryce Harper", "Pos": "1B", "Bats": "L", "BB_RATE": 0.13, "K_RATE": 0.185, "HR_PA_RATE": 0.048, "BABIP": 0.31, "1B_H_RATE": 0.48, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.26, "SPD": 48, "PA": 600},
            {"Player": "Trea Turner", "Pos": "SS", "Bats": "R", "BB_RATE": 0.068, "K_RATE": 0.175, "HR_PA_RATE": 0.032, "BABIP": 0.31, "1B_H_RATE": 0.56, "2B_H_RATE": 0.22, "3B_H_RATE": 0.04, "HR_H_RATE": 0.18, "SPD": 90, "PA": 640},
            {"Player": "Kyle Schwarber", "Pos": "DH", "Bats": "L", "BB_RATE": 0.15, "K_RATE": 0.285, "HR_PA_RATE": 0.062, "BABIP": 0.26, "1B_H_RATE": 0.38, "2B_H_RATE": 0.24, "3B_H_RATE": 0.0, "HR_H_RATE": 0.38, "SPD": 35, "PA": 620},
            {"Player": "Alec Bohm", "Pos": "3B", "Bats": "R", "BB_RATE": 0.062, "K_RATE": 0.155, "HR_PA_RATE": 0.025, "BABIP": 0.305, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 42, "PA": 590},
            {"Player": "J.T. Realmuto", "Pos": "C", "Bats": "R", "BB_RATE": 0.072, "K_RATE": 0.185, "HR_PA_RATE": 0.028, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 55, "PA": 500},
            {"Player": "Bryson Stott", "Pos": "2B", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.155, "HR_PA_RATE": 0.02, "BABIP": 0.295, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.12, "SPD": 68, "PA": 570},
            {"Player": "Brandon Marsh", "Pos": "LF", "Bats": "L", "BB_RATE": 0.095, "K_RATE": 0.255, "HR_PA_RATE": 0.028, "BABIP": 0.31, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.17, "SPD": 65, "PA": 450},
            {"Player": "Gabriel Rincones Jr.", "Pos": "RF", "Bats": "L", "BB_RATE": 0.06, "K_RATE": 0.27, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.46, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.28, "SPD": 40, "PA": 200},
            {"Player": "Justin Crawford", "Pos": "CF", "Bats": "L", "BB_RATE": 0.055, "K_RATE": 0.18, "HR_PA_RATE": 0.010, "BABIP": 0.31, "1B_H_RATE": 0.66, "2B_H_RATE": 0.20, "3B_H_RATE": 0.04, "HR_H_RATE": 0.06, "SPD": 88, "PA": 300},
        ],
        "pitching": [
            {"Player": "Zack Wheeler", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.205, "IP": "195.0", "ERA": 2.65, "Fatigue": 0.0},
            {"Player": "Cristopher Sanchez", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "185.0", "ERA": 3.0, "Fatigue": 0.0},
            {"Player": "Matt Strahm", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "68.0", "ERA": 3.1, "Fatigue": 0.0},
            {"Player": "Jhoan Duran", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.33, "HR_PA_ALLOWED_RATE": 0.016, "BABIP_ALLOWED": 0.26, "OAVG": 0.185, "IP": "62.0", "ERA": 2.3, "Fatigue": 0.0},
            {"Player": "Aaron Nola", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Jesus Luzardo", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.245, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "150.0", "ERA": 3.90, "Fatigue": 0.0},
            {"Player": "Taijuan Walker", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Orion Kerkering", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Jose Alvarado", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Gregory Soto", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.275, "OAVG": 0.21, "IP": "62.0", "ERA": 2.90, "Fatigue": 0.0},
        ]
    },
    "Chicago Cubs": {
        "primary": "#0E3386", "secondary": "#CC3433",
        "hitting": [
            {"Player": "Pete Crow-Armstrong", "Pos": "CF", "Bats": "L", "BB_RATE": 0.055, "K_RATE": 0.215, "HR_PA_RATE": 0.038, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.24, "3B_H_RATE": 0.04, "HR_H_RATE": 0.2, "SPD": 92, "PA": 610},
            {"Player": "Seiya Suzuki", "Pos": "RF", "Bats": "R", "BB_RATE": 0.1, "K_RATE": 0.22, "HR_PA_RATE": 0.038, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 48, "PA": 550},
            {"Player": "Michael Conforto", "Pos": "DH", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.225, "HR_PA_RATE": 0.032, "BABIP": 0.27, "1B_H_RATE": 0.50, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.22, "SPD": 45, "PA": 400},
            {"Player": "Michael Busch", "Pos": "1B", "Bats": "L", "BB_RATE": 0.092, "K_RATE": 0.235, "HR_PA_RATE": 0.035, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 45, "PA": 560},
            {"Player": "Nico Hoerner", "Pos": "2B", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.115, "HR_PA_RATE": 0.015, "BABIP": 0.295, "1B_H_RATE": 0.68, "2B_H_RATE": 0.2, "3B_H_RATE": 0.02, "HR_H_RATE": 0.1, "SPD": 78, "PA": 590},
            {"Player": "Dansby Swanson", "Pos": "SS", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.21, "HR_PA_RATE": 0.03, "BABIP": 0.285, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.17, "SPD": 60, "PA": 570},
            {"Player": "Ian Happ", "Pos": "LF", "Bats": "B", "BB_RATE": 0.105, "K_RATE": 0.225, "HR_PA_RATE": 0.032, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 55, "PA": 600},
            {"Player": "Alex Bregman", "Pos": "3B", "Bats": "R", "BB_RATE": 0.115, "K_RATE": 0.13, "HR_PA_RATE": 0.03, "BABIP": 0.27, "1B_H_RATE": 0.54, "2B_H_RATE": 0.28, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 45, "PA": 500},
            {"Player": "Miguel Amaya", "Pos": "C", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.225, "HR_PA_RATE": 0.025, "BABIP": 0.28, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 40, "PA": 380},
        ],
        "pitching": [
            {"Player": "Matthew Boyd", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.062, "K_ALLOWED_RATE": 0.245, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "170.0", "ERA": 3.05, "Fatigue": 0.0},
            {"Player": "Shota Imanaga", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.27, "OAVG": 0.22, "IP": "165.0", "ERA": 3.25, "Fatigue": 0.0},
            {"Player": "Porter Hodge", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.275, "OAVG": 0.215, "IP": "65.0", "ERA": 3.1, "Fatigue": 0.0},
            {"Player": "Daniel Palencia", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.095, "K_ALLOWED_RATE": 0.3, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.205, "IP": "58.0", "ERA": 2.9, "Fatigue": 0.0},
            {"Player": "Javier Assad", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "David Peterson", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.285, "OAVG": 0.245, "IP": "70.0", "ERA": 6.10, "Fatigue": 0.0},
            {"Player": "Colin Rea", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Ryan Brasier", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Brad Keller", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.21, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Julian Merryweather", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "San Diego Padres": {
        "primary": "#2F241D", "secondary": "#FFC425",
        "hitting": [
            {"Player": "Fernando Tatis Jr.", "Pos": "RF", "Bats": "R", "BB_RATE": 0.1, "K_RATE": 0.215, "HR_PA_RATE": 0.048, "BABIP": 0.31, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.25, "SPD": 82, "PA": 630},
            {"Player": "Manny Machado", "Pos": "3B", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.15, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 48, "PA": 620},
            {"Player": "Luis Arraez", "Pos": "1B", "Bats": "L", "BB_RATE": 0.055, "K_RATE": 0.065, "HR_PA_RATE": 0.01, "BABIP": 0.32, "1B_H_RATE": 0.74, "2B_H_RATE": 0.19, "3B_H_RATE": 0.01, "HR_H_RATE": 0.06, "SPD": 45, "PA": 610},
            {"Player": "Jackson Merrill", "Pos": "CF", "Bats": "L", "BB_RATE": 0.055, "K_RATE": 0.17, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.17, "SPD": 68, "PA": 600},
            {"Player": "Xander Bogaerts", "Pos": "SS", "Bats": "R", "BB_RATE": 0.078, "K_RATE": 0.175, "HR_PA_RATE": 0.025, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 55, "PA": 560},
            {"Player": "Jake Cronenworth", "Pos": "2B", "Bats": "L", "BB_RATE": 0.095, "K_RATE": 0.18, "HR_PA_RATE": 0.022, "BABIP": 0.28, "1B_H_RATE": 0.58, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 50, "PA": 550},
            {"Player": "Gavin Sheets", "Pos": "DH", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.225, "HR_PA_RATE": 0.035, "BABIP": 0.29, "1B_H_RATE": 0.5, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.22, "SPD": 35, "PA": 420},
            {"Player": "Ramon Laureano", "Pos": "LF", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.24, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.54, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.2, "SPD": 72, "PA": 460},
            {"Player": "Elias Diaz", "Pos": "C", "Bats": "R", "BB_RATE": 0.05, "K_RATE": 0.185, "HR_PA_RATE": 0.02, "BABIP": 0.275, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.0, "HR_H_RATE": 0.16, "SPD": 35, "PA": 380},
        ],
        "pitching": [
            {"Player": "Ryan Bergert", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "140.0", "ERA": 4.10, "Fatigue": 0.0},
            {"Player": "Michael King", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "175.0", "ERA": 3.15, "Fatigue": 0.0},
            {"Player": "Jeremiah Estrada", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.32, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.27, "OAVG": 0.2, "IP": "68.0", "ERA": 2.7, "Fatigue": 0.0},
            {"Player": "Robert Suarez", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.265, "OAVG": 0.205, "IP": "62.0", "ERA": 2.65, "Fatigue": 0.0},
            {"Player": "Yu Darvish", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Nick Pivetta", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Randy Vasquez", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Adrian Morejon", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Wandy Peralta", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Bryan Hoeing", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Texas Rangers": {
        "primary": "#003278", "secondary": "#C0111F",
        "hitting": [
            {"Player": "Corey Seager", "Pos": "SS", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.185, "HR_PA_RATE": 0.045, "BABIP": 0.29, "1B_H_RATE": 0.48, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.24, "SPD": 45, "PA": 600},
            {"Player": "Marcus Semien", "Pos": "2B", "Bats": "R", "BB_RATE": 0.088, "K_RATE": 0.17, "HR_PA_RATE": 0.032, "BABIP": 0.27, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 62, "PA": 660},
            {"Player": "Wyatt Langford", "Pos": "LF", "Bats": "R", "BB_RATE": 0.085, "K_RATE": 0.225, "HR_PA_RATE": 0.038, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.2, "SPD": 75, "PA": 590},
            {"Player": "Josh Jung", "Pos": "3B", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.225, "HR_PA_RATE": 0.035, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 48, "PA": 520},
            {"Player": "Sam Huff", "Pos": "C", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.26, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.48, "2B_H_RATE": 0.26, "3B_H_RATE": 0.0, "HR_H_RATE": 0.26, "SPD": 35, "PA": 350},
            {"Player": "Brandon Nimmo", "Pos": "RF", "Bats": "L", "BB_RATE": 0.135, "K_RATE": 0.185, "HR_PA_RATE": 0.028, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 55, "PA": 480},
            {"Player": "Jake Burger", "Pos": "1B", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.26, "HR_PA_RATE": 0.045, "BABIP": 0.29, "1B_H_RATE": 0.44, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.3, "SPD": 40, "PA": 500},
            {"Player": "Evan Carter", "Pos": "CF", "Bats": "L", "BB_RATE": 0.1, "K_RATE": 0.23, "HR_PA_RATE": 0.028, "BABIP": 0.3, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.17, "SPD": 76, "PA": 450},
            {"Player": "Ezequiel Duran", "Pos": "DH", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.25, "HR_PA_RATE": 0.03, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 62, "PA": 380},
        ],
        "pitching": [
            {"Player": "Jacob deGrom", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.045, "K_ALLOWED_RATE": 0.32, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.195, "IP": "150.0", "ERA": 2.6, "Fatigue": 0.0},
            {"Player": "Nathan Eovaldi", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.05, "K_ALLOWED_RATE": 0.225, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "170.0", "ERA": 3.35, "Fatigue": 0.0},
            {"Player": "Chris Martin", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.04, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "62.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Jacob Webb", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.275, "OAVG": 0.22, "IP": "55.0", "ERA": 3.3, "Fatigue": 0.0},
            {"Player": "Tyler Mahle", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Josh Sborz", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Cody Bradford", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "MacKenzie Gore", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "175.0", "ERA": 3.40, "Fatigue": 0.0},
            {"Player": "Cole Winn", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Grant Anderson", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Boston Red Sox": {
        "primary": "#BD3039", "secondary": "#0C2340",
        "hitting": [
            {"Player": "Willson Contreras", "Pos": "1B", "Bats": "R", "BB_RATE": 0.10, "K_RATE": 0.195, "HR_PA_RATE": 0.030, "BABIP": 0.29, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 40, "PA": 500},
            {"Player": "Roman Anthony", "Pos": "RF", "Bats": "L", "BB_RATE": 0.11, "K_RATE": 0.21, "HR_PA_RATE": 0.035, "BABIP": 0.32, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.2, "SPD": 65, "PA": 560},
            {"Player": "Jarren Duran", "Pos": "CF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.195, "HR_PA_RATE": 0.028, "BABIP": 0.31, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.04, "HR_H_RATE": 0.16, "SPD": 88, "PA": 640},
            {"Player": "Trevor Story", "Pos": "SS", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.235, "HR_PA_RATE": 0.032, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 62, "PA": 520},
            {"Player": "Wilyer Abreu", "Pos": "LF", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.21, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 68, "PA": 540},
            {"Player": "Kristian Campbell", "Pos": "3B", "Bats": "R", "BB_RATE": 0.09, "K_RATE": 0.22, "HR_PA_RATE": 0.022, "BABIP": 0.30, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.17, "SPD": 60, "PA": 500},
            {"Player": "Connor Wong", "Pos": "C", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.225, "HR_PA_RATE": 0.022, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 55, "PA": 400},
            {"Player": "Triston Casas", "Pos": "1B", "Bats": "L", "BB_RATE": 0.125, "K_RATE": 0.23, "HR_PA_RATE": 0.038, "BABIP": 0.28, "1B_H_RATE": 0.46, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.26, "SPD": 38, "PA": 480},
            {"Player": "Anthony Seigler", "Pos": "2B", "Bats": "B", "BB_RATE": 0.08, "K_RATE": 0.19, "HR_PA_RATE": 0.010, "BABIP": 0.29, "1B_H_RATE": 0.60, "2B_H_RATE": 0.22, "3B_H_RATE": 0.02, "HR_H_RATE": 0.09, "SPD": 55, "PA": 280},
        ],
        "pitching": [
            {"Player": "Patrick Sandoval", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.245, "IP": "60.0", "ERA": 4.10, "Fatigue": 0.0},
            {"Player": "Lucas Giolito", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.245, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "165.0", "ERA": 3.7, "Fatigue": 0.0},
            {"Player": "Justin Slaten", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.25, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "65.0", "ERA": 3.1, "Fatigue": 0.0},
            {"Player": "Aroldis Chapman", "Pos": "P", "Role": "Closer", "Throws": "L", "BB_ALLOWED_RATE": 0.11, "K_ALLOWED_RATE": 0.34, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.26, "OAVG": 0.19, "IP": "58.0", "ERA": 2.7, "Fatigue": 0.0},
            {"Player": "Brayan Bello", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Sonny Gray", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "175.0", "ERA": 3.30, "Fatigue": 0.0},
            {"Player": "Ranger Suarez", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.225, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.280, "OAVG": 0.230, "IP": "170.0", "ERA": 3.10, "Fatigue": 0.0},
            {"Player": "Greg Weissert", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Cooper Criswell", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Brennan Bernardino", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Seattle Mariners": {
        "primary": "#0C2C56", "secondary": "#005C5C",
        "hitting": [
            {"Player": "Cal Raleigh", "Pos": "C", "Bats": "B", "BB_RATE": 0.105, "K_RATE": 0.23, "HR_PA_RATE": 0.068, "BABIP": 0.28, "1B_H_RATE": 0.38, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.39, "SPD": 35, "PA": 600},
            {"Player": "Randy Arozarena", "Pos": "LF", "Bats": "R", "BB_RATE": 0.095, "K_RATE": 0.24, "HR_PA_RATE": 0.032, "BABIP": 0.29, "1B_H_RATE": 0.52, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.21, "SPD": 74, "PA": 570},
            {"Player": "Dominic Canzone", "Pos": "DH", "Bats": "L", "BB_RATE": 0.065, "K_RATE": 0.235, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.48, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.26, "SPD": 40, "PA": 380},
            {"Player": "Josh Naylor", "Pos": "1B", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.155, "HR_PA_RATE": 0.028, "BABIP": 0.3, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.18, "SPD": 42, "PA": 560},
            {"Player": "J.P. Crawford", "Pos": "3B", "Bats": "L", "BB_RATE": 0.11, "K_RATE": 0.155, "HR_PA_RATE": 0.018, "BABIP": 0.285, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.13, "SPD": 58, "PA": 570},
            {"Player": "Luke Raley", "Pos": "RF", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.26, "HR_PA_RATE": 0.035, "BABIP": 0.29, "1B_H_RATE": 0.48, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.25, "SPD": 55, "PA": 460},
            {"Player": "Cole Young", "Pos": "2B", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.19, "HR_PA_RATE": 0.018, "BABIP": 0.30, "1B_H_RATE": 0.58, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.15, "SPD": 60, "PA": 400},
            {"Player": "Julio Rodriguez", "Pos": "CF", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.225, "HR_PA_RATE": 0.038, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.21, "SPD": 82, "PA": 630},
            {"Player": "Colt Emerson", "Pos": "SS", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.22, "HR_PA_RATE": 0.020, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.17, "SPD": 55, "PA": 350},
        ],
        "pitching": [
            {"Player": "Logan Gilbert", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.048, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.285, "OAVG": 0.22, "IP": "190.0", "ERA": 3.1, "Fatigue": 0.0},
            {"Player": "George Kirby", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.035, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.235, "IP": "180.0", "ERA": 3.45, "Fatigue": 0.0},
            {"Player": "Andres Munoz", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.33, "HR_PA_ALLOWED_RATE": 0.016, "BABIP_ALLOWED": 0.265, "OAVG": 0.19, "IP": "65.0", "ERA": 2.2, "Fatigue": 0.0},
            {"Player": "Matt Brash", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.31, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.205, "IP": "58.0", "ERA": 2.9, "Fatigue": 0.0},
            {"Player": "Bryce Miller", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Bryan Woo", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Emerson Hancock", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Gregory Santos", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Casey Legumina", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Trent Thornton", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "New York Mets": {
        "primary": "#002D72", "secondary": "#FF5910",
        "hitting": [
            {"Player": "Francisco Lindor", "Pos": "SS", "Bats": "B", "BB_RATE": 0.09, "K_RATE": 0.155, "HR_PA_RATE": 0.035, "BABIP": 0.28, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 72, "PA": 660},
            {"Player": "Juan Soto", "Pos": "DH", "Bats": "L", "BB_RATE": 0.175, "K_RATE": 0.175, "HR_PA_RATE": 0.055, "BABIP": 0.31, "1B_H_RATE": 0.5, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.24, "SPD": 50, "PA": 660},
            {"Player": "Mark Vientos", "Pos": "1B", "Bats": "R", "BB_RATE": 0.085, "K_RATE": 0.235, "HR_PA_RATE": 0.030, "BABIP": 0.27, "1B_H_RATE": 0.44, "2B_H_RATE": 0.25, "3B_H_RATE": 0.0, "HR_H_RATE": 0.31, "SPD": 35, "PA": 460},
            {"Player": "Bo Bichette", "Pos": "3B", "Bats": "R", "BB_RATE": 0.055, "K_RATE": 0.20, "HR_PA_RATE": 0.020, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.17, "SPD": 55, "PA": 480},
            {"Player": "Carson Benge", "Pos": "RF", "Bats": "L", "BB_RATE": 0.10, "K_RATE": 0.185, "HR_PA_RATE": 0.018, "BABIP": 0.30, "1B_H_RATE": 0.58, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.13, "SPD": 60, "PA": 380},
            {"Player": "Brett Baty", "Pos": "2B", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.22, "HR_PA_RATE": 0.025, "BABIP": 0.29, "1B_H_RATE": 0.52, "2B_H_RATE": 0.28, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 45, "PA": 470},
            {"Player": "Luis Torrens", "Pos": "C", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.19, "HR_PA_RATE": 0.022, "BABIP": 0.28, "1B_H_RATE": 0.54, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.18, "SPD": 40, "PA": 380},
            {"Player": "Tyrone Taylor", "Pos": "LF", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.225, "HR_PA_RATE": 0.025, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 65, "PA": 400},
            {"Player": "A.J. Ewing", "Pos": "CF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.24, "HR_PA_RATE": 0.015, "BABIP": 0.30, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.11, "SPD": 78, "PA": 300},
        ],
        "pitching": [
            {"Player": "Kodai Senga", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.27, "OAVG": 0.21, "IP": "150.0", "ERA": 2.9, "Fatigue": 0.0},
            {"Player": "Sean Manaea", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "170.0", "ERA": 3.35, "Fatigue": 0.0},
            {"Player": "Reed Garrett", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.275, "OAVG": 0.215, "IP": "65.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Devin Williams", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.10, "K_ALLOWED_RATE": 0.34, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.260, "OAVG": 0.190, "IP": "58.0", "ERA": 2.50, "Fatigue": 0.0},
            {"Player": "Clay Holmes", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.215, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.240, "IP": "150.0", "ERA": 4.20, "Fatigue": 0.0},
            {"Player": "Nolan McLean", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.230, "IP": "140.0", "ERA": 3.73, "Fatigue": 0.0},
            {"Player": "Freddy Peralta", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.27, "OAVG": 0.215, "IP": "170.0", "ERA": 3.10, "Fatigue": 0.0},
            {"Player": "Luke Weaver", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.27, "OAVG": 0.205, "IP": "70.0", "ERA": 2.85, "Fatigue": 0.0},
            {"Player": "Ryne Stanek", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Danny Young", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Arizona Diamondbacks": {
        "primary": "#A71930", "secondary": "#E3D4AD",
        "hitting": [
            {"Player": "Ketel Marte", "Pos": "2B", "Bats": "B", "BB_RATE": 0.105, "K_RATE": 0.17, "HR_PA_RATE": 0.038, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.28, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 55, "PA": 590},
            {"Player": "Corbin Carroll", "Pos": "LF", "Bats": "L", "BB_RATE": 0.095, "K_RATE": 0.2, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.24, "3B_H_RATE": 0.04, "HR_H_RATE": 0.2, "SPD": 90, "PA": 630},
            {"Player": "Geraldo Perdomo", "Pos": "SS", "Bats": "B", "BB_RATE": 0.1, "K_RATE": 0.155, "HR_PA_RATE": 0.02, "BABIP": 0.29, "1B_H_RATE": 0.6, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 72, "PA": 600},
            {"Player": "Nolan Arenado", "Pos": "3B", "Bats": "R", "BB_RATE": 0.07, "K_RATE": 0.15, "HR_PA_RATE": 0.028, "BABIP": 0.28, "1B_H_RATE": 0.54, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.18, "SPD": 40, "PA": 590},
            {"Player": "Tim Tawa", "Pos": "1B", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.21, "HR_PA_RATE": 0.02, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.16, "SPD": 45, "PA": 350},
            {"Player": "Gabriel Moreno", "Pos": "C", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.155, "HR_PA_RATE": 0.02, "BABIP": 0.3, "1B_H_RATE": 0.6, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 45, "PA": 500},
            {"Player": "Jake McCarthy", "Pos": "RF", "Bats": "L", "BB_RATE": 0.06, "K_RATE": 0.20, "HR_PA_RATE": 0.018, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.15, "SPD": 75, "PA": 400},
            {"Player": "Alek Thomas", "Pos": "CF", "Bats": "L", "BB_RATE": 0.058, "K_RATE": 0.18, "HR_PA_RATE": 0.022, "BABIP": 0.295, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.15, "SPD": 78, "PA": 450},
            {"Player": "Pavin Smith", "Pos": "DH", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.15, "HR_PA_RATE": 0.022, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 40, "PA": 400},
        ],
        "pitching": [
            {"Player": "Zac Gallen", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.245, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.28, "OAVG": 0.23, "IP": "180.0", "ERA": 3.55, "Fatigue": 0.0},
            {"Player": "Brandon Pfaadt", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.05, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "175.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Kevin Ginkel", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.275, "OAVG": 0.215, "IP": "65.0", "ERA": 3.1, "Fatigue": 0.0},
            {"Player": "Justin Martinez", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.3, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.265, "OAVG": 0.2, "IP": "60.0", "ERA": 2.8, "Fatigue": 0.0},
            {"Player": "Merrill Kelly", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Eduardo Rodriguez", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Ryne Nelson", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Ryan Thompson", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Joe Mantiply", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Kyle Backhus", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Colorado Rockies": {
        "primary": "#333366", "secondary": "#C4CED4",
        "hitting": [
            {"Player": "Ezequiel Tovar", "Pos": "SS", "Bats": "R", "BB_RATE": 0.058, "K_RATE": 0.205, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 62, "PA": 600},
            {"Player": "Kyle Karros", "Pos": "3B", "Bats": "R", "BB_RATE": 0.10, "K_RATE": 0.24, "HR_PA_RATE": 0.020, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 45, "PA": 400},
            {"Player": "Brenton Doyle", "Pos": "CF", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.24, "HR_PA_RATE": 0.03, "BABIP": 0.3, "1B_H_RATE": 0.54, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.19, "SPD": 75, "PA": 550},
            {"Player": "Hunter Goodman", "Pos": "C", "Bats": "R", "BB_RATE": 0.045, "K_RATE": 0.22, "HR_PA_RATE": 0.035, "BABIP": 0.29, "1B_H_RATE": 0.5, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.23, "SPD": 40, "PA": 500},
            {"Player": "TJ Rumfield", "Pos": "1B", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.22, "HR_PA_RATE": 0.024, "BABIP": 0.29, "1B_H_RATE": 0.52, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.20, "SPD": 40, "PA": 380},
            {"Player": "Jordan Beck", "Pos": "RF", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.245, "HR_PA_RATE": 0.028, "BABIP": 0.295, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 60, "PA": 480},
            {"Player": "Kris Bryant", "Pos": "DH", "Bats": "R", "BB_RATE": 0.09, "K_RATE": 0.225, "HR_PA_RATE": 0.028, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 40, "PA": 400},
            {"Player": "Sam Hilliard", "Pos": "LF", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.29, "HR_PA_RATE": 0.03, "BABIP": 0.3, "1B_H_RATE": 0.48, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.24, "SPD": 65, "PA": 350},
            {"Player": "Adael Amador", "Pos": "2B", "Bats": "B", "BB_RATE": 0.085, "K_RATE": 0.2, "HR_PA_RATE": 0.018, "BABIP": 0.29, "1B_H_RATE": 0.6, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 68, "PA": 380},
        ],
        "pitching": [
            {"Player": "Kyle Freeland", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.18, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.3, "OAVG": 0.265, "IP": "170.0", "ERA": 4.6, "Fatigue": 0.0},
            {"Player": "Antonio Senzatela", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.17, "HR_PA_ALLOWED_RATE": 0.035, "BABIP_ALLOWED": 0.305, "OAVG": 0.27, "IP": "150.0", "ERA": 4.9, "Fatigue": 0.0},
            {"Player": "Victor Vodnik", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "65.0", "ERA": 3.9, "Fatigue": 0.0},
            {"Player": "Seth Halvorsen", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.1, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "55.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Ryan Feltner", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Austin Gomber", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Bradley Blalock", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Jalen Beeks", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Angel Chivilli", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Tyler Kinley", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "San Francisco Giants": {
        "primary": "#FD5A1E", "secondary": "#27251F",
        "hitting": [
            {"Player": "Matt Chapman", "Pos": "3B", "Bats": "R", "BB_RATE": 0.1, "K_RATE": 0.235, "HR_PA_RATE": 0.038, "BABIP": 0.3, "1B_H_RATE": 0.5, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.23, "SPD": 45, "PA": 610},
            {"Player": "Jung Hoo Lee", "Pos": "CF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.135, "HR_PA_RATE": 0.018, "BABIP": 0.3, "1B_H_RATE": 0.64, "2B_H_RATE": 0.22, "3B_H_RATE": 0.01, "HR_H_RATE": 0.13, "SPD": 62, "PA": 580},
            {"Player": "Willy Adames", "Pos": "SS", "Bats": "R", "BB_RATE": 0.095, "K_RATE": 0.245, "HR_PA_RATE": 0.035, "BABIP": 0.29, "1B_H_RATE": 0.5, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.22, "SPD": 55, "PA": 620},
            {"Player": "Heliot Ramos", "Pos": "RF", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.23, "HR_PA_RATE": 0.03, "BABIP": 0.3, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 58, "PA": 550},
            {"Player": "Andy Thomas", "Pos": "C", "Bats": "R", "BB_RATE": 0.07, "K_RATE": 0.22, "HR_PA_RATE": 0.020, "BABIP": 0.28, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 40, "PA": 350},
            {"Player": "LaMonte Wade Jr.", "Pos": "1B", "Bats": "L", "BB_RATE": 0.12, "K_RATE": 0.195, "HR_PA_RATE": 0.025, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 45, "PA": 440},
            {"Player": "Tyler Fitzgerald", "Pos": "2B", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.23, "HR_PA_RATE": 0.025, "BABIP": 0.3, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.17, "SPD": 78, "PA": 480},
            {"Player": "Drew Gilbert", "Pos": "LF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.24, "HR_PA_RATE": 0.022, "BABIP": 0.30, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 62, "PA": 380},
            {"Player": "Rafael Devers", "Pos": "DH", "Bats": "L", "BB_RATE": 0.105, "K_RATE": 0.22, "HR_PA_RATE": 0.042, "BABIP": 0.3, "1B_H_RATE": 0.48, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.24, "SPD": 40, "PA": 620},
        ],
        "pitching": [
            {"Player": "Logan Webb", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.048, "K_ALLOWED_RATE": 0.225, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "205.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Robbie Ray", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.095, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "160.0", "ERA": 3.6, "Fatigue": 0.0},
            {"Player": "Randy Rodriguez", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.31, "HR_PA_ALLOWED_RATE": 0.015, "BABIP_ALLOWED": 0.27, "OAVG": 0.195, "IP": "68.0", "ERA": 2.2, "Fatigue": 0.0},
            {"Player": "Camilo Doval", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.095, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.27, "OAVG": 0.21, "IP": "60.0", "ERA": 3.0, "Fatigue": 0.0},
            {"Player": "Landen Roupp", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "150.0", "ERA": 3.60, "Fatigue": 0.0},
            {"Player": "Kyle Harrison", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Hayden Birdsong", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Erik Miller", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Ryan Walker", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Tristan Beck", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Cincinnati Reds": {
        "primary": "#C6011F", "secondary": "#000000",
        "hitting": [
            {"Player": "Elly De La Cruz", "Pos": "SS", "Bats": "B", "BB_RATE": 0.075, "K_RATE": 0.27, "HR_PA_RATE": 0.042, "BABIP": 0.32, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.05, "HR_H_RATE": 0.23, "SPD": 96, "PA": 640},
            {"Player": "Sal Stewart", "Pos": "1B", "Bats": "R", "BB_RATE": 0.09, "K_RATE": 0.20, "HR_PA_RATE": 0.036, "BABIP": 0.27, "1B_H_RATE": 0.48, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.25, "SPD": 45, "PA": 400},
            {"Player": "Spencer Steer", "Pos": "CF", "Bats": "R", "BB_RATE": 0.085, "K_RATE": 0.195, "HR_PA_RATE": 0.03, "BABIP": 0.28, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 48, "PA": 590},
            {"Player": "Tyler Stephenson", "Pos": "C", "Bats": "R", "BB_RATE": 0.095, "K_RATE": 0.185, "HR_PA_RATE": 0.025, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 42, "PA": 460},
            {"Player": "Ke'Bryan Hayes", "Pos": "3B", "Bats": "R", "BB_RATE": 0.045, "K_RATE": 0.20, "HR_PA_RATE": 0.010, "BABIP": 0.24, "1B_H_RATE": 0.60, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.13, "SPD": 55, "PA": 200},
            {"Player": "Edwin Arroyo", "Pos": "2B", "Bats": "B", "BB_RATE": 0.065, "K_RATE": 0.21, "HR_PA_RATE": 0.015, "BABIP": 0.29, "1B_H_RATE": 0.60, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.13, "SPD": 68, "PA": 400},
            {"Player": "JJ Bleday", "Pos": "LF", "Bats": "L", "BB_RATE": 0.12, "K_RATE": 0.235, "HR_PA_RATE": 0.038, "BABIP": 0.27, "1B_H_RATE": 0.46, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 50, "PA": 400},
            {"Player": "Noelvi Marte", "Pos": "RF", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.225, "HR_PA_RATE": 0.028, "BABIP": 0.3, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 55, "PA": 480},
            {"Player": "Eugenio Suarez", "Pos": "DH", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.30, "HR_PA_RATE": 0.050, "BABIP": 0.260, "1B_H_RATE": 0.36, "2B_H_RATE": 0.24, "3B_H_RATE": 0.00, "HR_H_RATE": 0.40, "SPD": 30, "PA": 500},
        ],
        "pitching": [
            {"Player": "Hunter Greene", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.062, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.21, "IP": "170.0", "ERA": 2.75, "Fatigue": 0.0},
            {"Player": "Nick Lodolo", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.255, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "150.0", "ERA": 3.4, "Fatigue": 0.0},
            {"Player": "Tony Santillan", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "65.0", "ERA": 3.3, "Fatigue": 0.0},
            {"Player": "Alexis Diaz", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.1, "K_ALLOWED_RATE": 0.3, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.205, "IP": "58.0", "ERA": 3.1, "Fatigue": 0.0},
            {"Player": "Andrew Abbott", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Brady Singer", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Carson Spiers", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Emilio Pagan", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Scott Barlow", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.25, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.230, "IP": "55.0", "ERA": 3.85, "Fatigue": 0.0},
            {"Player": "Sam Moll", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Milwaukee Brewers": {
        "primary": "#12284B", "secondary": "#FFC52F",
        "hitting": [
            {"Player": "William Contreras", "Pos": "C", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.185, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.2, "SPD": 45, "PA": 620},
            {"Player": "Jackson Chourio", "Pos": "LF", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.21, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.25, "3B_H_RATE": 0.03, "HR_H_RATE": 0.2, "SPD": 82, "PA": 610},
            {"Player": "Christian Yelich", "Pos": "DH", "Bats": "L", "BB_RATE": 0.105, "K_RATE": 0.22, "HR_PA_RATE": 0.026, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 45, "PA": 400},
            {"Player": "Brice Turang", "Pos": "2B", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.17, "HR_PA_RATE": 0.015, "BABIP": 0.29, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.03, "HR_H_RATE": 0.13, "SPD": 84, "PA": 560},
            {"Player": "Joey Ortiz", "Pos": "3B", "Bats": "R", "BB_RATE": 0.07, "K_RATE": 0.165, "HR_PA_RATE": 0.02, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 62, "PA": 540},
            {"Player": "Andrew Vaughn", "Pos": "1B", "Bats": "R", "BB_RATE": 0.07, "K_RATE": 0.19, "HR_PA_RATE": 0.025, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.18, "SPD": 35, "PA": 250},
            {"Player": "Sal Frelick", "Pos": "RF", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.14, "HR_PA_RATE": 0.012, "BABIP": 0.3, "1B_H_RATE": 0.68, "2B_H_RATE": 0.2, "3B_H_RATE": 0.02, "HR_H_RATE": 0.1, "SPD": 68, "PA": 480},
            {"Player": "Cooper Pratt", "Pos": "SS", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.24, "HR_PA_RATE": 0.006, "BABIP": 0.28, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.02, "HR_H_RATE": 0.07, "SPD": 70, "PA": 200},
            {"Player": "Garrett Mitchell", "Pos": "CF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.235, "HR_PA_RATE": 0.028, "BABIP": 0.30, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.03, "HR_H_RATE": 0.19, "SPD": 75, "PA": 320},
        ],
        "pitching": [
            {"Player": "Jacob Misiorowski", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.36, "HR_PA_ALLOWED_RATE": 0.012, "BABIP_ALLOWED": 0.255, "OAVG": 0.175, "IP": "150.0", "ERA": 1.60, "Fatigue": 0.0},
            {"Player": "Jose Quintana", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.205, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "165.0", "ERA": 3.6, "Fatigue": 0.0},
            {"Player": "Trevor Megill", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.275, "OAVG": 0.215, "IP": "60.0", "ERA": 2.9, "Fatigue": 0.0},
            {"Player": "Abner Uribe", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.015, "BABIP_ALLOWED": 0.27, "OAVG": 0.205, "IP": "58.0", "ERA": 2.8, "Fatigue": 0.0},
            {"Player": "Aaron Ashby", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Logan Henderson", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.016, "BABIP_ALLOWED": 0.275, "OAVG": 0.210, "IP": "23.0", "ERA": 2.74, "Fatigue": 0.0},
            {"Player": "Tobias Myers", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Joel Payamps", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "DL Hall", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Angel Zerpa", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
        ]
    },
    "Pittsburgh Pirates": {
        "primary": "#27251F", "secondary": "#FDB827",
        "hitting": [
            {"Player": "Jake Mangum", "Pos": "CF", "Bats": "B", "BB_RATE": 0.055, "K_RATE": 0.135, "HR_PA_RATE": 0.008, "BABIP": 0.32, "1B_H_RATE": 0.72, "2B_H_RATE": 0.20, "3B_H_RATE": 0.03, "HR_H_RATE": 0.05, "SPD": 78, "PA": 400},
            {"Player": "Bryan Reynolds", "Pos": "LF", "Bats": "B", "BB_RATE": 0.09, "K_RATE": 0.21, "HR_PA_RATE": 0.03, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 55, "PA": 610},
            {"Player": "Jared Triolo", "Pos": "SS", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.185, "HR_PA_RATE": 0.015, "BABIP": 0.29, "1B_H_RATE": 0.60, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.13, "SPD": 55, "PA": 460},
            {"Player": "Rafael Flores Jr.", "Pos": "C", "Bats": "R", "BB_RATE": 0.055, "K_RATE": 0.235, "HR_PA_RATE": 0.020, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.18, "SPD": 45, "PA": 250},
            {"Player": "Tyler Callihan", "Pos": "1B", "Bats": "L", "BB_RATE": 0.065, "K_RATE": 0.24, "HR_PA_RATE": 0.026, "BABIP": 0.30, "1B_H_RATE": 0.48, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.25, "SPD": 45, "PA": 300},
            {"Player": "Nick Gonzales", "Pos": "3B", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.195, "HR_PA_RATE": 0.02, "BABIP": 0.3, "1B_H_RATE": 0.6, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 60, "PA": 490},
            {"Player": "Brandon Lowe", "Pos": "2B", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.23, "HR_PA_RATE": 0.038, "BABIP": 0.28, "1B_H_RATE": 0.46, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 45, "PA": 540},
            {"Player": "Esmerlyn Valdez", "Pos": "RF", "Bats": "R", "BB_RATE": 0.05, "K_RATE": 0.26, "HR_PA_RATE": 0.038, "BABIP": 0.30, "1B_H_RATE": 0.46, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.28, "SPD": 50, "PA": 200},
            {"Player": "Ryan O'Hearn", "Pos": "DH", "Bats": "L", "BB_RATE": 0.095, "K_RATE": 0.185, "HR_PA_RATE": 0.032, "BABIP": 0.290, "1B_H_RATE": 0.54, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.18, "SPD": 40, "PA": 500},
        ],
        "pitching": [
            {"Player": "Paul Skenes", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.045, "K_ALLOWED_RATE": 0.31, "HR_PA_ALLOWED_RATE": 0.016, "BABIP_ALLOWED": 0.27, "OAVG": 0.19, "IP": "195.0", "ERA": 2.1, "Fatigue": 0.0},
            {"Player": "Mitch Keller", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.058, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.29, "OAVG": 0.235, "IP": "180.0", "ERA": 3.65, "Fatigue": 0.0},
            {"Player": "Colin Holderman", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.23, "IP": "62.0", "ERA": 3.5, "Fatigue": 0.0},
            {"Player": "David Bednar", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.21, "IP": "58.0", "ERA": 3.0, "Fatigue": 0.0},
            {"Player": "Jared Jones", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Bailey Falter", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Braxton Ashcraft", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "108.1", "ERA": 3.24, "Fatigue": 0.0},
            {"Player": "Dauri Moreta", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Caleb Ferguson", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.25, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "55.0", "ERA": 3.7, "Fatigue": 0.0},
            {"Player": "Ryan Borucki", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "St. Louis Cardinals": {
        "primary": "#C41E3A", "secondary": "#0C2340",
        "hitting": [
            {"Player": "JJ Wetherholt", "Pos": "2B", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.22, "HR_PA_RATE": 0.018, "BABIP": 0.30, "1B_H_RATE": 0.58, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 62, "PA": 380},
            {"Player": "Ivan Herrera", "Pos": "C", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.20, "HR_PA_RATE": 0.028, "BABIP": 0.30, "1B_H_RATE": 0.52, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.20, "SPD": 40, "PA": 420},
            {"Player": "Masyn Winn", "Pos": "SS", "Bats": "R", "BB_RATE": 0.05, "K_RATE": 0.15, "HR_PA_RATE": 0.02, "BABIP": 0.29, "1B_H_RATE": 0.6, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 68, "PA": 600},
            {"Player": "Bryce Torres", "Pos": "LF", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.28, "HR_PA_RATE": 0.030, "BABIP": 0.26, "1B_H_RATE": 0.40, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.32, "SPD": 55, "PA": 200},
            {"Player": "Lars Nootbaar", "Pos": "RF", "Bats": "L", "BB_RATE": 0.115, "K_RATE": 0.215, "HR_PA_RATE": 0.028, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 60, "PA": 500},
            {"Player": "Alec Burleson", "Pos": "1B", "Bats": "L", "BB_RATE": 0.055, "K_RATE": 0.175, "HR_PA_RATE": 0.025, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.16, "SPD": 40, "PA": 550},
            {"Player": "Nathan Church", "Pos": "CF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.23, "HR_PA_RATE": 0.024, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.21, "SPD": 60, "PA": 350},
            {"Player": "Jordan Walker", "Pos": "DH", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.25, "HR_PA_RATE": 0.03, "BABIP": 0.3, "1B_H_RATE": 0.5, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.22, "SPD": 55, "PA": 400},
            {"Player": "Jose Fermin", "Pos": "3B", "Bats": "R", "BB_RATE": 0.055, "K_RATE": 0.19, "HR_PA_RATE": 0.026, "BABIP": 0.29, "1B_H_RATE": 0.50, "2B_H_RATE": 0.27, "3B_H_RATE": 0.02, "HR_H_RATE": 0.21, "SPD": 55, "PA": 250},
        ],
        "pitching": [
            {"Player": "Matthew Liberatore", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.21, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.285, "OAVG": 0.245, "IP": "155.0", "ERA": 4.10, "Fatigue": 0.0},
            {"Player": "Erick Fedde", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "165.0", "ERA": 3.75, "Fatigue": 0.0},
            {"Player": "Ryan Helsley", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.32, "HR_PA_ALLOWED_RATE": 0.016, "BABIP_ALLOWED": 0.27, "OAVG": 0.2, "IP": "62.0", "ERA": 2.6, "Fatigue": 0.0},
            {"Player": "JoJo Romero", "Pos": "P", "Role": "Closer", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.275, "OAVG": 0.22, "IP": "58.0", "ERA": 3.1, "Fatigue": 0.0},
            {"Player": "Andre Pallante", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Dustin May", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.245, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.290, "OAVG": 0.240, "IP": "150.0", "ERA": 4.30, "Fatigue": 0.0},
            {"Player": "Michael McGreevy", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Phil Maton", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Andrew Kittredge", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Riley O'Brien", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Miami Marlins": {
        "primary": "#00A3E0", "secondary": "#EF3340",
        "hitting": [
            {"Player": "Kyle Stowers", "Pos": "1B", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.24, "HR_PA_RATE": 0.038, "BABIP": 0.3, "1B_H_RATE": 0.5, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.23, "SPD": 55, "PA": 560},
            {"Player": "Xavier Edwards", "Pos": "2B", "Bats": "B", "BB_RATE": 0.075, "K_RATE": 0.17, "HR_PA_RATE": 0.01, "BABIP": 0.31, "1B_H_RATE": 0.68, "2B_H_RATE": 0.2, "3B_H_RATE": 0.03, "HR_H_RATE": 0.09, "SPD": 82, "PA": 580},
            {"Player": "Jodanny Mack", "Pos": "C", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.24, "HR_PA_RATE": 0.030, "BABIP": 0.29, "1B_H_RATE": 0.44, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.29, "SPD": 40, "PA": 200},
            {"Player": "Javier Sanoja", "Pos": "3B", "Bats": "B", "BB_RATE": 0.06, "K_RATE": 0.20, "HR_PA_RATE": 0.010, "BABIP": 0.29, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.12, "SPD": 60, "PA": 280},
            {"Player": "Heriberto Hernandez", "Pos": "LF", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.26, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.46, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 45, "PA": 420},
            {"Player": "Leo Jimenez", "Pos": "DH", "Bats": "R", "BB_RATE": 0.05, "K_RATE": 0.24, "HR_PA_RATE": 0.008, "BABIP": 0.29, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.12, "SPD": 55, "PA": 380},
            {"Player": "Esteury Ruiz", "Pos": "RF", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.23, "HR_PA_RATE": 0.010, "BABIP": 0.30, "1B_H_RATE": 0.62, "2B_H_RATE": 0.20, "3B_H_RATE": 0.04, "HR_H_RATE": 0.08, "SPD": 88, "PA": 350},
            {"Player": "Jakob Marsee", "Pos": "CF", "Bats": "L", "BB_RATE": 0.095, "K_RATE": 0.22, "HR_PA_RATE": 0.022, "BABIP": 0.3, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.17, "SPD": 72, "PA": 400},
            {"Player": "Otto Lopez", "Pos": "SS", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.19, "HR_PA_RATE": 0.015, "BABIP": 0.3, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.12, "SPD": 68, "PA": 380},
        ],
        "pitching": [
            {"Player": "Sandy Alcantara", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.225, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "170.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Chris Paddack", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.205, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.285, "OAVG": 0.245, "IP": "150.0", "ERA": 4.20, "Fatigue": 0.0},
            {"Player": "Anthony Bender", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "62.0", "ERA": 3.6, "Fatigue": 0.0},
            {"Player": "Calvin Faucher", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.23, "IP": "55.0", "ERA": 3.7, "Fatigue": 0.0},
            {"Player": "Janson Junk", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.21, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.235, "IP": "140.0", "ERA": 3.95, "Fatigue": 0.0},
            {"Player": "Max Meyer", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Eury Perez", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Ronny Henriquez", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.23, "IP": "55.0", "ERA": 3.70, "Fatigue": 0.0},
            {"Player": "Declan Cronin", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Andrew Nardi", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Washington Nationals": {
        "primary": "#AB0003", "secondary": "#14225A",
        "hitting": [
            {"Player": "James Wood", "Pos": "RF", "Bats": "L", "BB_RATE": 0.1, "K_RATE": 0.25, "HR_PA_RATE": 0.045, "BABIP": 0.32, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.26, "SPD": 62, "PA": 610},
            {"Player": "CJ Abrams", "Pos": "SS", "Bats": "L", "BB_RATE": 0.06, "K_RATE": 0.185, "HR_PA_RATE": 0.028, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.17, "SPD": 82, "PA": 610},
            {"Player": "Keibert Ruiz", "Pos": "C", "Bats": "B", "BB_RATE": 0.07, "K_RATE": 0.145, "HR_PA_RATE": 0.022, "BABIP": 0.27, "1B_H_RATE": 0.58, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 40, "PA": 520},
            {"Player": "Luis Garcia Jr.", "Pos": "1B", "Bats": "L", "BB_RATE": 0.05, "K_RATE": 0.145, "HR_PA_RATE": 0.02, "BABIP": 0.29, "1B_H_RATE": 0.6, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.13, "SPD": 55, "PA": 570},
            {"Player": "Nasim Nunez", "Pos": "2B", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.185, "HR_PA_RATE": 0.004, "BABIP": 0.28, "1B_H_RATE": 0.66, "2B_H_RATE": 0.20, "3B_H_RATE": 0.03, "HR_H_RATE": 0.03, "SPD": 88, "PA": 380},
            {"Player": "Adrian Chaparro", "Pos": "DH", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.24, "HR_PA_RATE": 0.020, "BABIP": 0.24, "1B_H_RATE": 0.50, "2B_H_RATE": 0.28, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 45, "PA": 80},
            {"Player": "Jacob Young", "Pos": "CF", "Bats": "L", "BB_RATE": 0.055, "K_RATE": 0.175, "HR_PA_RATE": 0.008, "BABIP": 0.3, "1B_H_RATE": 0.68, "2B_H_RATE": 0.2, "3B_H_RATE": 0.03, "HR_H_RATE": 0.09, "SPD": 88, "PA": 450},
            {"Player": "Dylan Crews", "Pos": "LF", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.22, "HR_PA_RATE": 0.028, "BABIP": 0.3, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 72, "PA": 480},
            {"Player": "Curtis Mead", "Pos": "3B", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.21, "HR_PA_RATE": 0.022, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 50, "PA": 300},
        ],
        "pitching": [
            {"Player": "Miles Mikolas", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.045, "K_ALLOWED_RATE": 0.175, "HR_PA_ALLOWED_RATE": 0.030, "BABIP_ALLOWED": 0.290, "OAVG": 0.260, "IP": "160.0", "ERA": 4.20, "Fatigue": 0.0},
            {"Player": "Mitchell Parker", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.205, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "160.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Jose A. Ferrer", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.25, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "60.0", "ERA": 3.5, "Fatigue": 0.0},
            {"Player": "Clayton Beeter", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.28, "OAVG": 0.230, "IP": "55.0", "ERA": 3.90, "Fatigue": 0.0},
            {"Player": "Trevor Williams", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "DJ Herz", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Jake Irvin", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Colin Poche", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Robert Garcia", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Derek Law", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Toronto Blue Jays": {
        "primary": "#134A8E", "secondary": "#1D2D5C",
        "hitting": [
            {"Player": "Vladimir Guerrero Jr.", "Pos": "1B", "Bats": "R", "BB_RATE": 0.11, "K_RATE": 0.15, "HR_PA_RATE": 0.038, "BABIP": 0.31, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 45, "PA": 650},
            {"Player": "Kazuma Okamoto", "Pos": "3B", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.195, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 40, "PA": 480},
            {"Player": "George Springer", "Pos": "DH", "Bats": "R", "BB_RATE": 0.11, "K_RATE": 0.195, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.5, "2B_H_RATE": 0.28, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 55, "PA": 570},
            {"Player": "Alejandro Kirk", "Pos": "C", "Bats": "R", "BB_RATE": 0.09, "K_RATE": 0.125, "HR_PA_RATE": 0.018, "BABIP": 0.29, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.0, "HR_H_RATE": 0.14, "SPD": 30, "PA": 500},
            {"Player": "Nathan Lukes", "Pos": "CF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.14, "HR_PA_RATE": 0.018, "BABIP": 0.30, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.12, "SPD": 55, "PA": 350},
            {"Player": "Ernie Clement", "Pos": "2B", "Bats": "R", "BB_RATE": 0.035, "K_RATE": 0.11, "HR_PA_RATE": 0.012, "BABIP": 0.29, "1B_H_RATE": 0.68, "2B_H_RATE": 0.2, "3B_H_RATE": 0.02, "HR_H_RATE": 0.1, "SPD": 55, "PA": 500},
            {"Player": "Andres Gimenez", "Pos": "SS", "Bats": "L", "BB_RATE": 0.06, "K_RATE": 0.175, "HR_PA_RATE": 0.018, "BABIP": 0.29, "1B_H_RATE": 0.6, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 68, "PA": 520},
            {"Player": "Addison Barger", "Pos": "RF", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.245, "HR_PA_RATE": 0.032, "BABIP": 0.3, "1B_H_RATE": 0.5, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.22, "SPD": 55, "PA": 460},
            {"Player": "Anthony Santander", "Pos": "LF", "Bats": "B", "BB_RATE": 0.085, "K_RATE": 0.195, "HR_PA_RATE": 0.058, "BABIP": 0.26, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 45, "PA": 500},
        ],
        "pitching": [
            {"Player": "Jose Berrios", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.28, "OAVG": 0.235, "IP": "190.0", "ERA": 3.9, "Fatigue": 0.0},
            {"Player": "Kevin Gausman", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.29, "OAVG": 0.235, "IP": "175.0", "ERA": 3.65, "Fatigue": 0.0},
            {"Player": "Yimi Garcia", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "62.0", "ERA": 3.4, "Fatigue": 0.0},
            {"Player": "Jeff Hoffman", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.3, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.27, "OAVG": 0.21, "IP": "58.0", "ERA": 2.7, "Fatigue": 0.0},
            {"Player": "Chris Bassitt", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Bowden Francis", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Dylan Cease", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.025, "BABIP_ALLOWED": 0.285, "OAVG": 0.225, "IP": "175.0", "ERA": 3.55, "Fatigue": 0.0},
            {"Player": "Erik Swanson", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Yariel Rodriguez", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Braydon Fisher", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.235, "IP": "50.0", "ERA": 3.9, "Fatigue": 0.0},
        ]
    },
    "Tampa Bay Rays": {
        "primary": "#092C5C", "secondary": "#8FBCE6",
        "hitting": [
            {"Player": "Junior Caminero", "Pos": "3B", "Bats": "R", "BB_RATE": 0.055, "K_RATE": 0.2, "HR_PA_RATE": 0.045, "BABIP": 0.29, "1B_H_RATE": 0.46, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.27, "SPD": 55, "PA": 620},
            {"Player": "Yandy Diaz", "Pos": "1B", "Bats": "R", "BB_RATE": 0.1, "K_RATE": 0.15, "HR_PA_RATE": 0.022, "BABIP": 0.32, "1B_H_RATE": 0.58, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 40, "PA": 580},
            {"Player": "Ha-Seong Kim", "Pos": "2B", "Bats": "R", "BB_RATE": 0.085, "K_RATE": 0.185, "HR_PA_RATE": 0.020, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 65, "PA": 400},
            {"Player": "Jonathan Aranda", "Pos": "DH", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.195, "HR_PA_RATE": 0.022, "BABIP": 0.32, "1B_H_RATE": 0.58, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.15, "SPD": 50, "PA": 500},
            {"Player": "Taylor Walls", "Pos": "SS", "Bats": "B", "BB_RATE": 0.09, "K_RATE": 0.225, "HR_PA_RATE": 0.015, "BABIP": 0.28, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 60, "PA": 380},
            {"Player": "Gavin Lux", "Pos": "2B", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.205, "HR_PA_RATE": 0.020, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.15, "SPD": 55, "PA": 500},
            {"Player": "Jonny DeLuca", "Pos": "CF", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.26, "HR_PA_RATE": 0.022, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.19, "SPD": 65, "PA": 350},
            {"Player": "Danny Jansen", "Pos": "C", "Bats": "R", "BB_RATE": 0.095, "K_RATE": 0.225, "HR_PA_RATE": 0.032, "BABIP": 0.27, "1B_H_RATE": 0.5, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.23, "SPD": 35, "PA": 420},
            {"Player": "Victor Mesa Jr.", "Pos": "LF", "Bats": "L", "BB_RATE": 0.05, "K_RATE": 0.20, "HR_PA_RATE": 0.010, "BABIP": 0.30, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.07, "SPD": 78, "PA": 350},
        ],
        "pitching": [
            {"Player": "Shane Baz", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "160.0", "ERA": 3.5, "Fatigue": 0.0},
            {"Player": "Ryan Pepiot", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.25, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "170.0", "ERA": 3.3, "Fatigue": 0.0},
            {"Player": "Garrett Cleavinger", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.275, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Pete Fairbanks", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.31, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.21, "IP": "55.0", "ERA": 2.8, "Fatigue": 0.0},
            {"Player": "Zack Littell", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Taj Bradley", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Drew Rasmussen", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "150.0", "ERA": 3.50, "Fatigue": 0.0},
            {"Player": "Jacob Waguespack", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Kevin Kelly", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Manuel Rodriguez", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Chicago White Sox": {
        "primary": "#27251F", "secondary": "#C4CED4",
        "hitting": [
            {"Player": "Sam Antonacci", "Pos": "LF", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.21, "HR_PA_RATE": 0.015, "BABIP": 0.30, "1B_H_RATE": 0.58, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.13, "SPD": 65, "PA": 350},
            {"Player": "Jacob Gonzalez", "Pos": "1B", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.22, "HR_PA_RATE": 0.020, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.16, "SPD": 45, "PA": 350},
            {"Player": "Miguel Vargas", "Pos": "3B", "Bats": "R", "BB_RATE": 0.09, "K_RATE": 0.23, "HR_PA_RATE": 0.022, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 55, "PA": 480},
            {"Player": "Colson Montgomery", "Pos": "SS", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.245, "HR_PA_RATE": 0.028, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.2, "SPD": 50, "PA": 480},
            {"Player": "Chase Meidroth", "Pos": "2B", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.185, "HR_PA_RATE": 0.010, "BABIP": 0.29, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.08, "SPD": 62, "PA": 420},
            {"Player": "Randal Grichuk", "Pos": "DH", "Bats": "R", "BB_RATE": 0.05, "K_RATE": 0.235, "HR_PA_RATE": 0.032, "BABIP": 0.28, "1B_H_RATE": 0.46, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.28, "SPD": 45, "PA": 350},
            {"Player": "Braden Montgomery", "Pos": "RF", "Bats": "B", "BB_RATE": 0.07, "K_RATE": 0.26, "HR_PA_RATE": 0.025, "BABIP": 0.30, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.20, "SPD": 55, "PA": 350},
            {"Player": "Kyle Teel", "Pos": "C", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.20, "HR_PA_RATE": 0.018, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 45, "PA": 380},
            {"Player": "Luisangel Acuna", "Pos": "CF", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.21, "HR_PA_RATE": 0.018, "BABIP": 0.3, "1B_H_RATE": 0.62, "2B_H_RATE": 0.22, "3B_H_RATE": 0.03, "HR_H_RATE": 0.13, "SPD": 82, "PA": 400},
        ],
        "pitching": [
            {"Player": "Sean Burke", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.235, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "150.0", "ERA": 4.2, "Fatigue": 0.0},
            {"Player": "Jonathan Cannon", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.295, "OAVG": 0.25, "IP": "150.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Steven Wilson", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "60.0", "ERA": 4.1, "Fatigue": 0.0},
            {"Player": "Seranthony Dominguez", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.28, "OAVG": 0.245, "IP": "55.0", "ERA": 4.20, "Fatigue": 0.0},
            {"Player": "Davis Martin", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Drew Thorpe", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Ky Bush", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Bryan Hudson", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.045, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.010, "BABIP_ALLOWED": 0.26, "OAVG": 0.19, "IP": "20.0", "ERA": 0.90, "Fatigue": 0.0},
            {"Player": "Jordan Leasure", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Anthony Kay", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.10, "Fatigue": 0.0},
        ]
    },
    "Cleveland Guardians": {
        "primary": "#00385D", "secondary": "#E50022",
        "hitting": [
            {"Player": "Steven Kwan", "Pos": "LF", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.095, "HR_PA_RATE": 0.012, "BABIP": 0.3, "1B_H_RATE": 0.68, "2B_H_RATE": 0.22, "3B_H_RATE": 0.02, "HR_H_RATE": 0.08, "SPD": 68, "PA": 620},
            {"Player": "Brayan Rocchio", "Pos": "SS", "Bats": "B", "BB_RATE": 0.055, "K_RATE": 0.19, "HR_PA_RATE": 0.018, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.15, "SPD": 65, "PA": 480},
            {"Player": "Chase DeLauter", "Pos": "RF", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.235, "HR_PA_RATE": 0.028, "BABIP": 0.30, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.20, "SPD": 55, "PA": 380},
            {"Player": "Kyle Manzardo", "Pos": "1B", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.205, "HR_PA_RATE": 0.028, "BABIP": 0.28, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 40, "PA": 560},
            {"Player": "Rhys Hoskins", "Pos": "DH", "Bats": "R", "BB_RATE": 0.115, "K_RATE": 0.23, "HR_PA_RATE": 0.038, "BABIP": 0.27, "1B_H_RATE": 0.46, "2B_H_RATE": 0.26, "3B_H_RATE": 0.0, "HR_H_RATE": 0.28, "SPD": 35, "PA": 300},
            {"Player": "Kahlil Watson", "Pos": "CF", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.24, "HR_PA_RATE": 0.015, "BABIP": 0.30, "1B_H_RATE": 0.58, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.12, "SPD": 75, "PA": 350},
            {"Player": "Daniel Schneemann", "Pos": "3B", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.22, "HR_PA_RATE": 0.02, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 62, "PA": 420},
            {"Player": "Austin Hedges", "Pos": "C", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.235, "HR_PA_RATE": 0.020, "BABIP": 0.26, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.18, "SPD": 35, "PA": 300},
            {"Player": "Travis Bazzana", "Pos": "2B", "Bats": "L", "BB_RATE": 0.11, "K_RATE": 0.20, "HR_PA_RATE": 0.022, "BABIP": 0.30, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 70, "PA": 420},
        ],
        "pitching": [
            {"Player": "Tanner Bibee", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.245, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "180.0", "ERA": 3.3, "Fatigue": 0.0},
            {"Player": "Gavin Williams", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.25, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "160.0", "ERA": 3.55, "Fatigue": 0.0},
            {"Player": "Hunter Gaddis", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.275, "OAVG": 0.215, "IP": "70.0", "ERA": 2.8, "Fatigue": 0.0},
            {"Player": "Emmanuel Clase", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.01, "BABIP_ALLOWED": 0.27, "OAVG": 0.2, "IP": "65.0", "ERA": 2.3, "Fatigue": 0.0},
            {"Player": "Ben Lively", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Slade Cecconi", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.21, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.285, "OAVG": 0.240, "IP": "150.0", "ERA": 4.20, "Fatigue": 0.0},
            {"Player": "Joey Cantillo", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Cade Smith", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Erik Sabrowski", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Nic Enright", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Detroit Tigers": {
        "primary": "#0C2340", "secondary": "#FA4616",
        "hitting": [
            {"Player": "Riley Greene", "Pos": "LF", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.235, "HR_PA_RATE": 0.038, "BABIP": 0.31, "1B_H_RATE": 0.5, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.23, "SPD": 62, "PA": 620},
            {"Player": "Zach McKinstry", "Pos": "2B", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.185, "HR_PA_RATE": 0.02, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 65, "PA": 520},
            {"Player": "Spencer Torkelson", "Pos": "1B", "Bats": "R", "BB_RATE": 0.095, "K_RATE": 0.225, "HR_PA_RATE": 0.038, "BABIP": 0.27, "1B_H_RATE": 0.46, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 40, "PA": 560},
            {"Player": "Kerry Carpenter", "Pos": "RF", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.215, "HR_PA_RATE": 0.038, "BABIP": 0.28, "1B_H_RATE": 0.46, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 45, "PA": 490},
            {"Player": "Colt Keith", "Pos": "3B", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.21, "HR_PA_RATE": 0.025, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 45, "PA": 460},
            {"Player": "Jake Rogers", "Pos": "C", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.29, "HR_PA_RATE": 0.025, "BABIP": 0.25, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 40, "PA": 350},
            {"Player": "Kevin McGonigle", "Pos": "SS", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.185, "HR_PA_RATE": 0.020, "BABIP": 0.31, "1B_H_RATE": 0.58, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.14, "SPD": 55, "PA": 420},
            {"Player": "James Outman", "Pos": "CF", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.30, "HR_PA_RATE": 0.026, "BABIP": 0.26, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.05, "HR_H_RATE": 0.23, "SPD": 70, "PA": 200},
            {"Player": "Enmanuel Valencia", "Pos": "DH", "Bats": "L", "BB_RATE": 0.07, "K_RATE": 0.24, "HR_PA_RATE": 0.030, "BABIP": 0.28, "1B_H_RATE": 0.44, "2B_H_RATE": 0.25, "3B_H_RATE": 0.01, "HR_H_RATE": 0.30, "SPD": 40, "PA": 50},
        ],
        "pitching": [
            {"Player": "Tarik Skubal", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.045, "K_ALLOWED_RATE": 0.33, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.27, "OAVG": 0.185, "IP": "195.0", "ERA": 2.2, "Fatigue": 0.0},
            {"Player": "Framber Valdez", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.225, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.285, "OAVG": 0.235, "IP": "195.0", "ERA": 3.15, "Fatigue": 0.0},
            {"Player": "Tyler Holton", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.24, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.22, "IP": "70.0", "ERA": 3.0, "Fatigue": 0.0},
            {"Player": "Will Vest", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.275, "OAVG": 0.215, "IP": "60.0", "ERA": 2.7, "Fatigue": 0.0},
            {"Player": "Jack Flaherty", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Reese Olson", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Justin Verlander", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.20, "HR_PA_ALLOWED_RATE": 0.030, "BABIP_ALLOWED": 0.290, "OAVG": 0.250, "IP": "130.0", "ERA": 4.30, "Fatigue": 0.0},
            {"Player": "Tommy Kahnle", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Beau Brieske", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Brenan Hanifee", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Kansas City Royals": {
        "primary": "#004687", "secondary": "#BD9B60",
        "hitting": [
            {"Player": "Bobby Witt Jr.", "Pos": "SS", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.155, "HR_PA_RATE": 0.038, "BABIP": 0.32, "1B_H_RATE": 0.5, "2B_H_RATE": 0.24, "3B_H_RATE": 0.04, "HR_H_RATE": 0.22, "SPD": 92, "PA": 660},
            {"Player": "Salvador Perez", "Pos": "1B", "Bats": "R", "BB_RATE": 0.045, "K_RATE": 0.18, "HR_PA_RATE": 0.035, "BABIP": 0.26, "1B_H_RATE": 0.48, "2B_H_RATE": 0.26, "3B_H_RATE": 0.0, "HR_H_RATE": 0.26, "SPD": 25, "PA": 580},
            {"Player": "Nick Loftin", "Pos": "DH", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.22, "HR_PA_RATE": 0.024, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 55, "PA": 250},
            {"Player": "Josh Rojas", "Pos": "3B", "Bats": "L", "BB_RATE": 0.08, "K_RATE": 0.19, "HR_PA_RATE": 0.038, "BABIP": 0.20, "1B_H_RATE": 0.62, "2B_H_RATE": 0.15, "3B_H_RATE": 0.0, "HR_H_RATE": 0.23, "SPD": 55, "PA": 100},
            {"Player": "Michael Massey", "Pos": "2B", "Bats": "L", "BB_RATE": 0.06, "K_RATE": 0.2, "HR_PA_RATE": 0.022, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 55, "PA": 480},
            {"Player": "Jac Caglianone", "Pos": "RF", "Bats": "L", "BB_RATE": 0.05, "K_RATE": 0.25, "HR_PA_RATE": 0.035, "BABIP": 0.29, "1B_H_RATE": 0.46, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.27, "SPD": 50, "PA": 420},
            {"Player": "Lane Thomas", "Pos": "CF", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.21, "HR_PA_RATE": 0.028, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.20, "SPD": 65, "PA": 460},
            {"Player": "Isaac Collins", "Pos": "LF", "Bats": "B", "BB_RATE": 0.09, "K_RATE": 0.20, "HR_PA_RATE": 0.022, "BABIP": 0.30, "1B_H_RATE": 0.56, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.17, "SPD": 65, "PA": 420},
            {"Player": "Carter Jensen", "Pos": "C", "Bats": "L", "BB_RATE": 0.075, "K_RATE": 0.22, "HR_PA_RATE": 0.030, "BABIP": 0.28, "1B_H_RATE": 0.50, "2B_H_RATE": 0.27, "3B_H_RATE": 0.01, "HR_H_RATE": 0.22, "SPD": 45, "PA": 300},
        ],
        "pitching": [
            {"Player": "Cole Ragans", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.29, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "180.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Seth Lugo", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.21, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.23, "IP": "185.0", "ERA": 3.35, "Fatigue": 0.0},
            {"Player": "Lucas Erceg", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.285, "OAVG": 0.22, "IP": "65.0", "ERA": 3.15, "Fatigue": 0.0},
            {"Player": "Carlos Estevez", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.275, "OAVG": 0.22, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Michael Wacha", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Kris Bubic", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Michael Lorenzen", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "John Schreiber", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Steven Cruz", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.020, "BABIP_ALLOWED": 0.28, "OAVG": 0.220, "IP": "55.0", "ERA": 3.60, "Fatigue": 0.0},
            {"Player": "Sam Long", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Minnesota Twins": {
        "primary": "#002B5C", "secondary": "#D31145",
        "hitting": [
            {"Player": "Royce Lewis", "Pos": "3B", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.22, "HR_PA_RATE": 0.035, "BABIP": 0.3, "1B_H_RATE": 0.52, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.21, "SPD": 60, "PA": 500},
            {"Player": "Byron Buxton", "Pos": "CF", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.255, "HR_PA_RATE": 0.042, "BABIP": 0.3, "1B_H_RATE": 0.48, "2B_H_RATE": 0.24, "3B_H_RATE": 0.03, "HR_H_RATE": 0.25, "SPD": 85, "PA": 480},
            {"Player": "Carlos Correa", "Pos": "SS", "Bats": "R", "BB_RATE": 0.09, "K_RATE": 0.17, "HR_PA_RATE": 0.025, "BABIP": 0.28, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.17, "SPD": 45, "PA": 570},
            {"Player": "Ryan Jeffers", "Pos": "C", "Bats": "R", "BB_RATE": 0.095, "K_RATE": 0.215, "HR_PA_RATE": 0.03, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 40, "PA": 480},
            {"Player": "Trevor Larnach", "Pos": "LF", "Bats": "L", "BB_RATE": 0.085, "K_RATE": 0.22, "HR_PA_RATE": 0.03, "BABIP": 0.29, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 45, "PA": 480},
            {"Player": "Brooks Lee", "Pos": "2B", "Bats": "B", "BB_RATE": 0.055, "K_RATE": 0.19, "HR_PA_RATE": 0.022, "BABIP": 0.29, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.16, "SPD": 50, "PA": 480},
            {"Player": "Matt Wallner", "Pos": "RF", "Bats": "L", "BB_RATE": 0.11, "K_RATE": 0.26, "HR_PA_RATE": 0.038, "BABIP": 0.29, "1B_H_RATE": 0.46, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.27, "SPD": 45, "PA": 440},
            {"Player": "Luke Keaschall", "Pos": "2B", "Bats": "R", "BB_RATE": 0.08, "K_RATE": 0.205, "HR_PA_RATE": 0.020, "BABIP": 0.31, "1B_H_RATE": 0.56, "2B_H_RATE": 0.26, "3B_H_RATE": 0.03, "HR_H_RATE": 0.15, "SPD": 72, "PA": 400},
            {"Player": "Josh Bell", "Pos": "1B", "Bats": "B", "BB_RATE": 0.11, "K_RATE": 0.19, "HR_PA_RATE": 0.022, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.28, "3B_H_RATE": 0.01, "HR_H_RATE": 0.19, "SPD": 35, "PA": 450},
        ],
        "pitching": [
            {"Player": "Pablo Lopez", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.055, "K_ALLOWED_RATE": 0.26, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "185.0", "ERA": 3.4, "Fatigue": 0.0},
            {"Player": "Joe Ryan", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.05, "K_ALLOWED_RATE": 0.255, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.27, "OAVG": 0.22, "IP": "170.0", "ERA": 3.55, "Fatigue": 0.0},
            {"Player": "Griffin Jax", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.06, "K_ALLOWED_RATE": 0.32, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.27, "OAVG": 0.2, "IP": "68.0", "ERA": 2.6, "Fatigue": 0.0},
            {"Player": "Cole Sands", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.255, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "58.0", "ERA": 3.40, "Fatigue": 0.0},
            {"Player": "Bailey Ober", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Simeon Woods Richardson", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.225, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "140.0", "ERA": 4.30, "Fatigue": 0.0},
            {"Player": "David Festa", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Brock Stewart", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.02, "BABIP_ALLOWED": 0.28, "OAVG": 0.215, "IP": "60.0", "ERA": 3.2, "Fatigue": 0.0},
            {"Player": "Justin Topa", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Louie Varland", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "50.0", "ERA": 4.2, "Fatigue": 0.0},
        ]
    },
    "Los Angeles Angels": {
        "primary": "#BA0021", "secondary": "#003263",
        "hitting": [
            {"Player": "Mike Trout", "Pos": "CF", "Bats": "R", "BB_RATE": 0.13, "K_RATE": 0.24, "HR_PA_RATE": 0.048, "BABIP": 0.3, "1B_H_RATE": 0.46, "2B_H_RATE": 0.24, "3B_H_RATE": 0.02, "HR_H_RATE": 0.28, "SPD": 60, "PA": 500},
            {"Player": "Zach Neto", "Pos": "SS", "Bats": "R", "BB_RATE": 0.075, "K_RATE": 0.185, "HR_PA_RATE": 0.028, "BABIP": 0.29, "1B_H_RATE": 0.54, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.18, "SPD": 70, "PA": 600},
            {"Player": "Josh Lowe", "Pos": "LF", "Bats": "R", "BB_RATE": 0.065, "K_RATE": 0.25, "HR_PA_RATE": 0.022, "BABIP": 0.30, "1B_H_RATE": 0.52, "2B_H_RATE": 0.25, "3B_H_RATE": 0.03, "HR_H_RATE": 0.20, "SPD": 68, "PA": 400},
            {"Player": "Nolan Schanuel", "Pos": "1B", "Bats": "L", "BB_RATE": 0.09, "K_RATE": 0.13, "HR_PA_RATE": 0.015, "BABIP": 0.29, "1B_H_RATE": 0.62, "2B_H_RATE": 0.24, "3B_H_RATE": 0.01, "HR_H_RATE": 0.13, "SPD": 45, "PA": 610},
            {"Player": "Logan O'Hoppe", "Pos": "C", "Bats": "R", "BB_RATE": 0.07, "K_RATE": 0.225, "HR_PA_RATE": 0.028, "BABIP": 0.28, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.01, "HR_H_RATE": 0.21, "SPD": 40, "PA": 500},
            {"Player": "Yoan Moncada", "Pos": "3B", "Bats": "B", "BB_RATE": 0.10, "K_RATE": 0.26, "HR_PA_RATE": 0.022, "BABIP": 0.30, "1B_H_RATE": 0.52, "2B_H_RATE": 0.26, "3B_H_RATE": 0.02, "HR_H_RATE": 0.20, "SPD": 55, "PA": 400},
            {"Player": "Jo Adell", "Pos": "RF", "Bats": "R", "BB_RATE": 0.06, "K_RATE": 0.29, "HR_PA_RATE": 0.038, "BABIP": 0.29, "1B_H_RATE": 0.46, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.27, "SPD": 65, "PA": 480},
            {"Player": "Luis Rengifo", "Pos": "2B", "Bats": "B", "BB_RATE": 0.07, "K_RATE": 0.185, "HR_PA_RATE": 0.02, "BABIP": 0.29, "1B_H_RATE": 0.58, "2B_H_RATE": 0.25, "3B_H_RATE": 0.02, "HR_H_RATE": 0.15, "SPD": 65, "PA": 500},
            {"Player": "Jorge Soler", "Pos": "DH", "Bats": "R", "BB_RATE": 0.095, "K_RATE": 0.27, "HR_PA_RATE": 0.038, "BABIP": 0.27, "1B_H_RATE": 0.44, "2B_H_RATE": 0.26, "3B_H_RATE": 0.0, "HR_H_RATE": 0.3, "SPD": 35, "PA": 480},
        ],
        "pitching": [
            {"Player": "Ryan Johnson", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.075, "K_ALLOWED_RATE": 0.205, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "70.0", "ERA": 4.20, "Fatigue": 0.0},
            {"Player": "Jose Soriano", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.21, "HR_PA_ALLOWED_RATE": 0.018, "BABIP_ALLOWED": 0.29, "OAVG": 0.24, "IP": "160.0", "ERA": 3.7, "Fatigue": 0.0},
            {"Player": "Drew Pomeranz", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.020, "BABIP_ALLOWED": 0.28, "OAVG": 0.220, "IP": "55.0", "ERA": 3.40, "Fatigue": 0.0},
            {"Player": "Jordan Romano", "Pos": "P", "Role": "Closer", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.27, "HR_PA_ALLOWED_RATE": 0.026, "BABIP_ALLOWED": 0.27, "OAVG": 0.22, "IP": "55.0", "ERA": 3.60, "Fatigue": 0.0},
            {"Player": "Yusei Kikuchi", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.07, "K_ALLOWED_RATE": 0.22, "HR_PA_ALLOWED_RATE": 0.028, "BABIP_ALLOWED": 0.29, "OAVG": 0.245, "IP": "150.0", "ERA": 4.0, "Fatigue": 0.0},
            {"Player": "Reid Detmers", "Pos": "P", "Role": "SP", "Throws": "L", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.2, "HR_PA_ALLOWED_RATE": 0.03, "BABIP_ALLOWED": 0.295, "OAVG": 0.255, "IP": "140.0", "ERA": 4.5, "Fatigue": 0.0},
            {"Player": "Jack Kochanowicz", "Pos": "P", "Role": "SP", "Throws": "R", "BB_ALLOWED_RATE": 0.085, "K_ALLOWED_RATE": 0.185, "HR_PA_ALLOWED_RATE": 0.032, "BABIP_ALLOWED": 0.3, "OAVG": 0.26, "IP": "120.0", "ERA": 4.8, "Fatigue": 0.0},
            {"Player": "Brent Suter", "Pos": "P", "Role": "RP", "Throws": "L", "BB_ALLOWED_RATE": 0.065, "K_ALLOWED_RATE": 0.19, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.245, "IP": "55.0", "ERA": 3.90, "Fatigue": 0.0},
            {"Player": "Sam Bachman", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.08, "K_ALLOWED_RATE": 0.23, "HR_PA_ALLOWED_RATE": 0.024, "BABIP_ALLOWED": 0.285, "OAVG": 0.23, "IP": "55.0", "ERA": 3.8, "Fatigue": 0.0},
            {"Player": "Ryan Zeferjahn", "Pos": "P", "Role": "RP", "Throws": "R", "BB_ALLOWED_RATE": 0.09, "K_ALLOWED_RATE": 0.28, "HR_PA_ALLOWED_RATE": 0.022, "BABIP_ALLOWED": 0.28, "OAVG": 0.225, "IP": "50.0", "ERA": 3.70, "Fatigue": 0.0},
        ]
    },
}

# ----------------------------------------------------
# LIVE ROSTER DATA LOADER
# ----------------------------------------------------
# Prefers a nightly-refreshed roster_data.json (see refresh_rosters.py) over
# the hardcoded ROSTER_DATABASE_FALLBACK above, so the app reflects current
# rosters/rates automatically instead of only updating when someone manually
# edits this file. Falls back safely to the hardcoded data if the JSON file
# is missing, malformed, or doesn't look like a complete 30-team dataset --
# this app should never crash or run empty just because a nightly refresh
# hiccuped or hasn't run yet.
import json as _json
import os as _os

def _load_roster_database():
    json_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "roster_data.json")
    try:
        with open(json_path, "r") as f:
            data = _json.load(f)
        if not isinstance(data, dict) or len(data) < 30:
            raise ValueError(f"roster_data.json has {len(data) if isinstance(data, dict) else 'invalid'} teams, expected 30")
        for team, roster in data.items():
            if not roster.get("hitting") or not roster.get("pitching"):
                raise ValueError(f"{team} is missing hitting or pitching data in roster_data.json")
        return data
    except FileNotFoundError:
        return ROSTER_DATABASE_FALLBACK
    except Exception as e:
        print(f"[roster loader] Falling back to hardcoded roster data -- roster_data.json problem: {e}")
        return ROSTER_DATABASE_FALLBACK

ROSTER_DATABASE = _load_roster_database()

# ----------------------------------------------------
# CONTACT QUALITY DATA LOADER (OPTIONAL)
# ----------------------------------------------------
# Unlike rosters and park factors, this data is genuinely optional -- there's
# no hardcoded fallback, because the app works fine without it (views that
# use this just don't show these extra columns if it's missing). Loads
# MLB_Predictor/contact_quality.json if present (see
# refresh_contact_quality.py), which has real Statcast Barrel%/HardHit%/xwOBA
# per hitter, keyed by player name to match ROSTER_DATABASE's "Player" field.
def _load_contact_quality():
    json_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "contact_quality.json")
    try:
        with open(json_path, "r") as f:
            data = _json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"[contact quality loader] Ignoring contact_quality.json -- problem reading it: {e}")
        return {}

CONTACT_QUALITY = _load_contact_quality()

BALLPARK_ENV_FALLBACK = {

    "Athletics": {"run_mult": 0.95, "hr_mult": 0.88, "babip_mult": 0.98},
    "Baltimore Orioles": {"run_mult": 1.02, "hr_mult": 0.95, "babip_mult": 1.01},
    "New York Yankees": {"run_mult": 1.05, "hr_mult": 1.12, "babip_mult": 1.00},
    "Los Angeles Dodgers": {"run_mult": 0.98, "hr_mult": 1.02, "babip_mult": 0.97},
    "Atlanta Braves": {"run_mult": 1.03, "hr_mult": 1.05, "babip_mult": 1.00},
    "Houston Astros": {"run_mult": 1.00, "hr_mult": 0.98, "babip_mult": 1.00},
    "Philadelphia Phillies": {"run_mult": 1.04, "hr_mult": 1.08, "babip_mult": 1.00},
    "Chicago Cubs": {"run_mult": 1.02, "hr_mult": 1.03, "babip_mult": 1.01},
    "San Diego Padres": {"run_mult": 0.93, "hr_mult": 0.85, "babip_mult": 0.98},
    "Texas Rangers": {"run_mult": 0.97, "hr_mult": 0.95, "babip_mult": 0.99},
    "Boston Red Sox": {"run_mult": 1.06, "hr_mult": 0.97, "babip_mult": 1.03},
    "Seattle Mariners": {"run_mult": 0.92, "hr_mult": 0.90, "babip_mult": 0.97},
    "New York Mets": {"run_mult": 0.98, "hr_mult": 0.95, "babip_mult": 0.99},
    "Arizona Diamondbacks": {"run_mult": 1.05, "hr_mult": 1.02, "babip_mult": 1.02},
    "Colorado Rockies": {"run_mult": 1.15, "hr_mult": 1.20, "babip_mult": 1.05},
    "San Francisco Giants": {"run_mult": 0.90, "hr_mult": 0.82, "babip_mult": 0.97},
    "Cincinnati Reds": {"run_mult": 1.08, "hr_mult": 1.15, "babip_mult": 1.00},
    "Milwaukee Brewers": {"run_mult": 0.99, "hr_mult": 1.00, "babip_mult": 1.00},
    "Pittsburgh Pirates": {"run_mult": 0.94, "hr_mult": 0.90, "babip_mult": 0.99},
    "St. Louis Cardinals": {"run_mult": 0.97, "hr_mult": 0.95, "babip_mult": 1.00},
    "Miami Marlins": {"run_mult": 0.90, "hr_mult": 0.85, "babip_mult": 0.98},
    "Washington Nationals": {"run_mult": 0.97, "hr_mult": 0.95, "babip_mult": 0.99},
    "Toronto Blue Jays": {"run_mult": 1.00, "hr_mult": 1.00, "babip_mult": 1.00},
    "Tampa Bay Rays": {"run_mult": 0.93, "hr_mult": 0.90, "babip_mult": 0.97},
    "Chicago White Sox": {"run_mult": 1.01, "hr_mult": 1.00, "babip_mult": 1.00},
    "Cleveland Guardians": {"run_mult": 0.96, "hr_mult": 0.92, "babip_mult": 0.98},
    "Detroit Tigers": {"run_mult": 0.98, "hr_mult": 0.98, "babip_mult": 0.99},
    "Kansas City Royals": {"run_mult": 0.98, "hr_mult": 0.95, "babip_mult": 1.00},
    "Minnesota Twins": {"run_mult": 0.99, "hr_mult": 0.98, "babip_mult": 0.99},
    "Los Angeles Angels": {"run_mult": 0.99, "hr_mult": 0.97, "babip_mult": 0.99}
}

# ----------------------------------------------------
# PARK FACTOR DATA LOADER
# ----------------------------------------------------
# Same pattern as the roster loader above: prefers a refreshed
# ballpark_env.json (see refresh_park_factors.py) over the hardcoded
# BALLPARK_ENV_FALLBACK, falling back safely if the file is missing,
# malformed, or incomplete. Unlike rosters, park factors barely change
# year to year, so this file is only expected to be refreshed
# occasionally (manually run), not nightly.
def _load_ballpark_env():
    json_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ballpark_env.json")
    try:
        with open(json_path, "r") as f:
            data = _json.load(f)
        if not isinstance(data, dict) or len(data) < 30:
            raise ValueError(f"ballpark_env.json has {len(data) if isinstance(data, dict) else 'invalid'} teams, expected 30")
        for team, factors in data.items():
            if not all(k in factors for k in ("run_mult", "hr_mult", "babip_mult")):
                raise ValueError(f"{team} is missing one or more multiplier fields in ballpark_env.json")
        return data
    except FileNotFoundError:
        return BALLPARK_ENV_FALLBACK
    except Exception as e:
        print(f"[ballpark loader] Falling back to hardcoded park factors -- ballpark_env.json problem: {e}")
        return BALLPARK_ENV_FALLBACK

BALLPARK_ENV = _load_ballpark_env()

# ----------------------------------------------------
# ADVANCED MATHEMATICAL LOG-ODDS AND FALLBACK SAFETY HANDLERS
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

# ----------------------------------------------------
# SMALL-SAMPLE REGRESSION (STABILIZATION)
# ----------------------------------------------------
# Real player rate stats are noisy in small samples -- a hitter with 250 PA and a hot streak
# isn't actually a true-talent .320 hitter, he just hasn't faced enough pitches for luck to
# average out. These stabilization points (PA/BF needed for a stat to be ~50% reliable) come
# from Russell Carleton's widely-cited sabermetric research. Below that many PA/BF, a stat is
# shrunk substantially toward the league average; above it, the observed rate is trusted more.
BATTER_STABILIZATION_PA = {
    "K_RATE": 60, "BB_RATE": 120, "HR_PA_RATE": 170, "BABIP": 820,
}
# Pitcher rates are noisier than batter rates at the same sample size (this is itself a
# well-established sabermetric finding), so pitcher stabilization points are set higher --
# especially BABIP and HR/9, which are famously luck-driven over anything less than a full season.
PITCHER_STABILIZATION_BF = {
    "K_ALLOWED_RATE": 70, "BB_ALLOWED_RATE": 170, "HR_PA_ALLOWED_RATE": 1200, "BABIP_ALLOWED": 2000,
}

def regress_to_mean(observed_rate, sample_size, league_rate, stabilization_point):
    """Shrinks an observed rate toward the league average in proportion to how small the
    sample is relative to the stat's stabilization point. sample_size=0 returns the league
    average; sample_size >> stabilization_point returns close to the observed rate."""
    sample_size = max(0.0, sample_size)
    return (sample_size * observed_rate + stabilization_point * league_rate) / (sample_size + stabilization_point)

def safe_extract_player(roster_dict, side, player_name, fallback_idx=0):
    """ Absolute defense framework against out-of-bounds positional slice indexing """
    pool = roster_dict.get(side, [])
    if not pool:
        return {}
    matched = [p for p in pool if p["Player"] == player_name]
    if matched:
        return matched[0].copy()
    return pool[min(fallback_idx, len(pool) - 1)].copy()

# ----------------------------------------------------
# CONTROL BOARD INTERFACE UI
# ----------------------------------------------------
st.sidebar.header("⚾ Enterprise Simulator Panel")
all_teams_list = list(ROSTER_DATABASE.keys())
away_selection = st.sidebar.selectbox("Away Roster Array", all_teams_list, index=0)
home_selection = st.sidebar.selectbox("Home Roster Array", all_teams_list, index=1)

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

if not st.session_state["lineups_locked"]:
    st.subheader("📋 Core Lineup Configuration Ingestion")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### {away_selection} Lineup Assets")
        sp_choice_a = st.selectbox("Starting Pitcher Choice (Away)", [p["Player"] for p in away_p_pool if p["Role"] == "SP"])
        batters_a = []
        for i in range(9):
            b = st.selectbox(f"Away Slot {i+1} Batter", [p["Player"] for p in away_h_pool], index=min(i, len(away_h_pool)-1), key=f"a_slot_key_{i}")
            batters_a.append(b)
            
    with col2:
        st.markdown(f"#### {home_selection} Lineup Assets")
        sp_choice_h = st.selectbox("Starting Pitcher Choice (Home)", [p["Player"] for p in home_p_pool if p["Role"] == "SP"])
        batters_h = []
        for i in range(9):
            b = st.selectbox(f"Home Slot {i+1} Batter", [p["Player"] for p in home_h_pool], index=min(i, len(home_h_pool)-1), key=f"h_slot_key_{i}")
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
    st.sidebar.button("🔓 Release Lock System", on_click=lambda: st.session_state.update({"lineups_locked": False, "monte_carlo_results": None}))

    # ----------------------------------------------------
    # ADVANCED QUANT MODULE: 24-STATE MARKOV SIMULATION ENGINE
    # ----------------------------------------------------
    class DipsMarkovEngine:
        def __init__(self, away_lineup, home_lineup, away_sp, home_sp, away_bp, home_bp, park_rules, env_tensors):
            self.away_lineup = away_lineup
            self.home_lineup = home_lineup
            self.away_sp = away_sp
            self.home_sp = home_sp
            self.away_bp = [p.copy() for p in away_bp]
            self.home_bp = [p.copy() for p in home_bp]
            self.park = park_rules
            self.env = env_tensors
            # Precompute each player's small-sample-regressed rates ONCE here rather than
            # recalculating the same regression math on every single at-bat. These rates only
            # depend on a player's static season totals (PA for hitters, IP for pitchers),
            # never on in-game state, so across 1000 Monte Carlo iterations x ~35 at-bats per
            # game this was previously identical redundant work done tens of thousands of times.
            for batter in self.away_lineup + self.home_lineup:
                self._cache_batter_rates(batter)
            for pitcher in [self.away_sp, self.home_sp] + self.away_bp + self.home_bp:
                self._cache_pitcher_rates(pitcher)

        @staticmethod
        def _cache_batter_rates(batter):
            if "_reg_bb" in batter:
                return  # already cached (e.g. shared lineup dict reused across engine instances)
            pa = batter.get("PA", 300)
            batter["_reg_bb"] = regress_to_mean(batter["BB_RATE"], pa, LEAGUE_BASELINE["BB_RATE"], BATTER_STABILIZATION_PA["BB_RATE"])
            batter["_reg_k"] = regress_to_mean(batter["K_RATE"], pa, LEAGUE_BASELINE["K_RATE"], BATTER_STABILIZATION_PA["K_RATE"])
            batter["_reg_hr"] = regress_to_mean(batter["HR_PA_RATE"], pa, LEAGUE_BASELINE["HR_PA_RATE"], BATTER_STABILIZATION_PA["HR_PA_RATE"])
            batter["_reg_babip"] = regress_to_mean(batter["BABIP"], pa, LEAGUE_BASELINE["BABIP"], BATTER_STABILIZATION_PA["BABIP"])

        @staticmethod
        def _cache_pitcher_rates(pitcher):
            if "_reg_bb" in pitcher:
                return
            try:
                ip = float(pitcher.get("IP", "100.0"))
            except (TypeError, ValueError):
                ip = 100.0
            bf = ip * 4.3  # ~4.3 batters faced per inning pitched, league-average
            pitcher["_reg_bb"] = regress_to_mean(pitcher["BB_ALLOWED_RATE"], bf, LEAGUE_BASELINE["BB_RATE"], PITCHER_STABILIZATION_BF["BB_ALLOWED_RATE"])
            pitcher["_reg_k"] = regress_to_mean(pitcher["K_ALLOWED_RATE"], bf, LEAGUE_BASELINE["K_RATE"], PITCHER_STABILIZATION_BF["K_ALLOWED_RATE"])
            pitcher["_reg_hr"] = regress_to_mean(pitcher["HR_PA_ALLOWED_RATE"], bf, LEAGUE_BASELINE["HR_PA_RATE"], PITCHER_STABILIZATION_BF["HR_PA_ALLOWED_RATE"])
            pitcher["_reg_babip"] = regress_to_mean(pitcher["BABIP_ALLOWED"], bf, LEAGUE_BASELINE["BABIP"], PITCHER_STABILIZATION_BF["BABIP_ALLOWED"])

        def execute_matchup_vector(self, batter, pitcher, order_cycle):
            is_platoon = (batter["Bats"] == "L" and pitcher["Throws"] == "R") or (batter["Bats"] == "R" and pitcher["Throws"] == "L")
            platoon_mult = 1.07 if is_platoon else 0.93
            
            fatigue_penalty = 1.0 + (pitcher.get("Fatigue", 0.0) * 0.35)
            # Fatigue affects strikeouts in the OPPOSITE direction from walks/hard-contact: a
            # tiring pitcher loses command (more walks) and velocity/movement (more hard
            # contact/HR), but also loses swing-and-miss sharpness, so strikeouts should
            # decline, not rise, as fatigue increases.
            k_fatigue_penalty = 1.0 - (pitcher.get("Fatigue", 0.0) * 0.20)
            ttop_mult = 1.0 + ((order_cycle - 1) * 0.06) if pitcher["Role"] == "SP" else 1.0
            
            # Dynamic Environmental Atmosphere Scalers
            temp_density_scalar = 1.0 + ((self.env["temp"] - 72) * 0.0012)
            elevation_scalar = 1.0 + (self.env["elevation"] / 5280 * 0.05)
            wind_scalar = 1.10 if self.env["wind"] == "Blowing Out (Boosted)" else (0.90 if self.env["wind"] == "Blowing In (Deadened)" else 1.0)

            # Small-sample-regressed rates were precomputed once in __init__ (see
            # _cache_batter_rates/_cache_pitcher_rates) rather than recalculated here every
            # at-bat -- same result, far less redundant work across 1000 iterations.
            b_bb_rate = batter["_reg_bb"]
            b_k_rate = batter["_reg_k"]
            b_hr_rate = batter["_reg_hr"]
            b_babip = batter["_reg_babip"]

            p_bb_rate = pitcher["_reg_bb"]
            p_k_rate = pitcher["_reg_k"]
            p_hr_rate = pitcher["_reg_hr"]
            p_babip = pitcher["_reg_babip"]

            bb_prob = calculate_log_odds(b_bb_rate, p_bb_rate * ttop_mult * fatigue_penalty, LEAGUE_BASELINE["BB_RATE"])
            k_prob = calculate_log_odds(b_k_rate, p_k_rate * ttop_mult * k_fatigue_penalty, LEAGUE_BASELINE["K_RATE"])
            
            hr_base = calculate_log_odds(b_hr_rate, p_hr_rate * ttop_mult * fatigue_penalty, LEAGUE_BASELINE["HR_PA_RATE"])
            hr_prob = hr_base * self.park["hr_mult"] * temp_density_scalar * elevation_scalar * wind_scalar
            
            sum_isolated = bb_prob + k_prob + hr_prob
            if sum_isolated >= 0.95:
                scale = 0.95 / sum_isolated
                bb_prob *= scale; k_prob *= scale; hr_prob *= scale
                
            remainder = 1.0 - (bb_prob + k_prob + hr_prob)
            babip_matchup = calculate_log_odds(b_babip * platoon_mult, p_babip * fatigue_penalty, LEAGUE_BASELINE["BABIP"]) * self.park["babip_mult"]
            
            hit_in_play_prob = remainder * babip_matchup
            out_in_play_prob = remainder - hit_in_play_prob
            
            # Park run_mult scales extra-base-hit frequency (doubles/triples) -- this is the
            # mechanism by which park dimensions/altitude drive run-scoring beyond what's
            # already captured by hr_mult (home runs) and babip_mult (overall hit rate).
            # Coors Field's huge outfield, for example, inflates doubles/triples independent
            # of home run or overall-hit rate; a small park does the opposite.
            run_mult = self.park.get("run_mult", 1.0)
            # NOTE: these three base fractions must sum to 1.0 -- they represent the full
            # breakdown of hit_in_play_prob into singles/doubles/triples. A previous version of
            # this formula used 0.65/0.21/0.02, which only summed to 0.88: 12% of the
            # probability that a ball in play should be a hit was silently vanishing from the
            # outcome weights every at-bat instead of being credited to any hit type, quietly
            # suppressing the league-wide hit and run-scoring rate. Normalized here (same
            # 65:21:2 ratio between 1B/2B/3B, now summing to exactly 1.0).
            base_1b, base_2b, base_3b = 0.65/0.88, 0.21/0.88, 0.02/0.88
            adj_2b = base_2b * run_mult
            adj_3b = base_3b * run_mult
            adj_1b = base_1b - (adj_2b - base_2b) - (adj_3b - base_3b)
            adj_1b = max(0.0, adj_1b)
            
            return {
                "BB": bb_prob, "K": k_prob, "HR": hr_prob,
                "1B": hit_in_play_prob * adj_1b, "2B": hit_in_play_prob * adj_2b,
                "3B": hit_in_play_prob * adj_3b, "OUT": out_in_play_prob
            }

        def step_markov_24_state(self, state, outcome, batter_name, runner_spd):
            # Bases now store the PLAYER NAME occupying each base (or None if empty),
            # instead of a bare boolean, so runs scored can be credited to the correct batter.
            outs = state["outs"]
            bases = list(state["bases"])
            scored_runners = []
            event_log = ""
            
            if outcome in ["K", "OUT"]:
                # Fielding error check goes FIRST, before any out is recorded -- a real
                # reached-on-error isn't an out at all (the batter reaches safely, existing
                # runners force-advance exactly like a walk), so this has to be resolved before
                # the outs+=1 below. Errors were previously entirely unmodeled: every batted-ball
                # out was assumed clean, when in reality roughly 1.5-2% of them aren't.
                if outcome == "OUT" and random.random() < 0.018:
                    bases = list(bases)
                    if bases[0] is not None and bases[1] is not None and bases[2] is not None:
                        scored_runners.append(bases[2])
                        bases = [batter_name, bases[0], bases[1]]
                    elif bases[0] is not None and bases[1] is not None:
                        bases = [batter_name, bases[0], bases[1]]
                    elif bases[0] is not None:
                        bases = [batter_name, bases[0], bases[2]]
                    else:
                        bases = [batter_name, bases[1], bases[2]]
                    return outs, bases, scored_runners, "Reached on Error"

                prior_outs = outs  # outs BEFORE this play, needed for both the sac-fly and DP rules below
                outs += 1
                # A runner on third with fewer than 2 outs scores on a real fraction of batted-ball
                # outs (the classic sacrifice fly, plus productive groundouts) -- this was previously
                # unmodeled entirely, meaning outs never advanced or scored a runner no matter the
                # situation. Strikeouts never allow this (nobody's put the ball in play), and per the
                # actual sac-fly rule, the run does NOT count if this out is the third out of the inning
                # (the batted-ball out happens before the runner can legally tag and score).
                if outcome == "OUT" and prior_outs < 2 and bases[2] is not None:
                    if random.random() < 0.45:
                        bases = list(bases)
                        scored_runners.append(bases[2])
                        bases[2] = None
                        return outs, bases, scored_runners, "Sacrifice Fly"
                # Double play: a runner on first with fewer than 2 outs is sometimes erased by a
                # ground ball, at roughly the real MLB GIDP rate for this situation. This only
                # applies once the sac-fly check above has already been tried and didn't fire
                # (a single batted ball is either a fly ball or a ground ball, not both, so these
                # two checks are mutually exclusive in practice even though they're sequential here).
                if outcome == "OUT" and prior_outs < 2 and bases[0] is not None:
                    if random.random() < 0.12:
                        outs += 1  # the second out -- the lead runner, in addition to the batter
                        bases = list(bases)
                        bases[0] = None
                        return outs, bases, scored_runners, "Double Play"
                return outs, bases, scored_runners, "Strikeout" if outcome == "K" else "Fielded Lineout/Groundout"
                
            if outcome == "BB":
                # Proper force-advancement logic on a walk
                if bases[0] is not None and bases[1] is not None and bases[2] is not None:
                    scored_runners.append(bases[2])
                    bases = [batter_name, bases[0], bases[1]]
                elif bases[0] is not None and bases[1] is not None:
                    bases = [batter_name, bases[0], bases[1]]
                elif bases[0] is not None:
                    bases = [batter_name, bases[0], bases[2]]
                else:
                    bases = [batter_name, bases[1], bases[2]]
                return outs, bases, scored_runners, "Base on Balls"

            if outcome == "HR":
                scored_runners = [b for b in bases if b is not None] + [batter_name]
                return outs, [None, None, None], scored_runners, f"Home Run ({len(scored_runners)} Run Shot)"

            spd_factor = runner_spd / 100.0
            if outcome == "1B":
                new_bases = [batter_name, None, None]
                if bases[2] is not None: scored_runners.append(bases[2])
                if bases[1] is not None:
                    if spd_factor > 0.68 or random.random() < 0.45: scored_runners.append(bases[1])
                    else: new_bases[2] = bases[1]
                if bases[0] is not None: new_bases[1] = bases[0]
                bases = new_bases
                event_log = "Base Hit Single"
            elif outcome == "2B":
                new_bases = [None, batter_name, None]
                if bases[2] is not None: scored_runners.append(bases[2])
                if bases[1] is not None: scored_runners.append(bases[1])
                if bases[0] is not None:
                    if spd_factor > 0.65: scored_runners.append(bases[0])
                    else: new_bases[2] = bases[0]
                bases = new_bases
                event_log = "Double down the baseline"
            elif outcome == "3B":
                scored_runners = [b for b in bases if b is not None]
                bases = [None, None, batter_name]
                event_log = "Triple deep into the gap"
                
            return outs, bases, scored_runners, event_log

        def select_next_reliever(self, bullpen_list, own_score, opp_score, inning):
            """Picks the next arm from the bullpen, but reserves the Closer for genuine save
            situations (9th inning or later, leading by 1-3 runs) instead of using him in
            roster-list order regardless of game context. This mirrors how real managers
            actually deploy their closer -- saved for the highest-leverage spot, not just
            whichever arm happens to be next on the depth chart."""
            if not bullpen_list:
                return None
            lead = own_score - opp_score
            is_save_situation = inning >= 9 and 1 <= lead <= 3

            closer_idx = next((i for i, p in enumerate(bullpen_list) if p["Role"] == "Closer"), None)
            if is_save_situation and closer_idx is not None:
                return bullpen_list.pop(closer_idx)

            # Not a save situation: pull a non-closer arm first, keeping the closer in reserve.
            non_closer_idx = next((i for i, p in enumerate(bullpen_list) if p["Role"] != "Closer"), None)
            if non_closer_idx is not None:
                return bullpen_list.pop(non_closer_idx)

            # Bullpen is down to just the closer (extras/blowout/exhausted pen) -- use him anyway.
            return bullpen_list.pop(0)

        def run_full_game(self, tracking_mode=False):
            # IMPORTANT: bullpens are copied fresh here so repeated calls (e.g. across a
            # 1000x Monte Carlo loop) don't permanently drain self.away_bp/self.home_bp.
            # Shallow .copy() is safe and much faster than deepcopy here: every pitcher dict
            # only holds flat primitive values (str/float/int), no nested mutable structures,
            # so there's nothing for a deep copy to protect that a shallow copy doesn't already.
            local_away_bp = [p.copy() for p in self.away_bp]
            local_home_bp = [p.copy() for p in self.home_bp]
            all_away_pitchers = [self.away_sp] + local_away_bp
            all_home_pitchers = [self.home_sp] + local_home_bp

            g = {
                "inning": 1, "top_half": True, "away_score": 0, "home_score": 0,
                "away_lineup_idx": 0, "home_lineup_idx": 0,
                "away_p": self.away_sp.copy(), "home_p": self.home_sp.copy(),
                "away_pitches": 0, "home_pitches": 0,
                "box_scores": {
                    "away": {p["Player"]: {"AB":0,"H":0,"1B":0,"2B":0,"3B":0,"HR":0,"BB":0,"RBI":0,"K":0,"R":0,"SB":0} for p in self.away_lineup},
                    "home": {p["Player"]: {"AB":0,"H":0,"1B":0,"2B":0,"3B":0,"HR":0,"BB":0,"RBI":0,"K":0,"R":0,"SB":0} for p in self.home_lineup},
                    "away_pitching": {p["Player"]: {"K":0,"BB":0,"H":0,"ER":0,"Outs":0} for p in all_away_pitchers},
                    "home_pitching": {p["Player"]: {"K":0,"BB":0,"H":0,"ER":0,"Outs":0} for p in all_home_pitchers}
                },
                "log_history": [], "win_prob_history": [50.0]
            }
            
            while g["inning"] <= 9 or (g["away_score"] == g["home_score"]):
                score_diff = abs(g["away_score"] - g["home_score"])
                if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]:
                    break # Home team walk-off rule safety block
                
                # Dynamic AI Bullpen Hook Logic
                # Starters get pulled after ~95 pitches; relief/closer arms get a quicker ~30-pitch hook.
                # Uses pitcher IDENTITY (is this the pitcher who started today's game?) rather than
                # roster Role label -- a team's 2nd/3rd starter is still labeled "SP" in the roster
                # data even when he's the one entering as a mid-game reliever, so checking Role alone
                # would let him keep the lenient 95-pitch starter's threshold indefinitely and
                # effectively never get pulled again, starving the rest of the bullpen (including
                # the closer) of any realistic chance to appear.
                home_is_todays_starter = g["home_p"]["Player"] == self.home_sp["Player"]
                away_is_todays_starter = g["away_p"]["Player"] == self.away_sp["Player"]
                if g["top_half"] and (
                    (home_is_todays_starter and g["home_pitches"] > 95) or
                    (not home_is_todays_starter and g["home_pitches"] > 30)
                ):
                    next_p = self.select_next_reliever(local_home_bp, g["home_score"], g["away_score"], g["inning"])
                    if next_p: g["home_p"] = next_p; g["home_pitches"] = 0
                elif not g["top_half"] and (
                    (away_is_todays_starter and g["away_pitches"] > 95) or
                    (not away_is_todays_starter and g["away_pitches"] > 30)
                ):
                    next_p = self.select_next_reliever(local_away_bp, g["away_score"], g["home_score"], g["inning"])
                    if next_p: g["away_p"] = next_p; g["away_pitches"] = 0

                # Manfred Runner rule: since 2020, every half-inning from the 10th onward
                # starts with a runner automatically placed on second base (representing the
                # player who would have made the last out, i.e. the batter one slot ahead of
                # this half-inning's leadoff hitter in the order). This was previously
                # unmodeled -- extra innings were simulated identically to a normal 9th, which
                # meaningfully understates how much easier it is to score in real extra innings.
                if g["inning"] >= 10:
                    if g["top_half"]:
                        ghost_idx = (g["away_lineup_idx"] - 1) % 9
                        ghost_name = self.away_lineup[ghost_idx]["Player"]
                    else:
                        ghost_idx = (g["home_lineup_idx"] - 1) % 9
                        ghost_name = self.home_lineup[ghost_idx]["Player"]
                    state = {"outs": 0, "bases": [None, ghost_name, None]}
                else:
                    state = {"outs": 0, "bases": [None, None, None]}
                while state["outs"] < 3:
                    if g["top_half"]:
                        batter = self.away_lineup[g["away_lineup_idx"] % 9]
                        pitcher = g["home_p"]
                        g["home_pitches"] += random.randint(3, 6)
                        order_cycle = (g["away_lineup_idx"] // 9) + 1
                        # In-game fatigue: ramps up as this pitcher's pitch count THIS OUTING
                        # rises (resets to 0 whenever a new pitcher enters, since home_pitches
                        # itself resets on a pitching change). No effect for the first ~25
                        # pitches, then climbs -- by 95 pitches (roughly a starter's typical
                        # pull threshold) a pitcher is meaningfully more hittable than fresh.
                        pitcher["Fatigue"] = max(0.0, (g["home_pitches"] - 25) / 100.0)
                    else:
                        batter = self.home_lineup[g["home_lineup_idx"] % 9]
                        pitcher = g["away_p"]
                        g["away_pitches"] += random.randint(3, 6)
                        order_cycle = (g["home_lineup_idx"] // 9) + 1
                        pitcher["Fatigue"] = max(0.0, (g["away_pitches"] - 25) / 100.0)
                        
                    t_key = "away" if g["top_half"] else "home"
                    pitch_key = "home_pitching" if g["top_half"] else "away_pitching"

                    # Stolen base sub-event: fires before this plate appearance resolves, when
                    # there's a real attempt opportunity (runner on first, second base open).
                    # Scaled by the RUNNER's own speed (SPD), not the current batter's -- this
                    # was previously not modeled or tracked at all despite SB being a standard
                    # prop market. Deliberately limited to 1st-to-2nd, which is the large
                    # majority of real MLB stolen base attempts; 2nd-to-3rd is rarer and adds
                    # complexity for comparatively little accuracy gain.
                    if state["bases"][0] is not None and state["bases"][1] is None:
                        batting_lineup = self.away_lineup if g["top_half"] else self.home_lineup
                        runner_name = state["bases"][0]
                        runner = next((p for p in batting_lineup if p["Player"] == runner_name), None)
                        if runner is not None:
                            spd = runner.get("SPD", 50)
                            attempt_prob = 0.05 + (spd / 100.0) * 0.15
                            if random.random() < attempt_prob:
                                success_prob = 0.65 + (spd / 100.0) * 0.25
                                if random.random() < success_prob:
                                    state["bases"][0] = None
                                    state["bases"][1] = runner_name
                                    g["box_scores"][t_key][runner_name]["SB"] += 1
                                else:
                                    state["bases"][0] = None
                                    state["outs"] += 1
                                    if state["outs"] >= 3:
                                        break  # caught stealing was the 3rd out, inning over

                    prob_vector = self.execute_matchup_vector(batter, pitcher, order_cycle)
                    outcome = random.choices(list(prob_vector.keys()), weights=list(prob_vector.values()), k=1)[0]
                    
                    b_box = g["box_scores"][t_key][batter["Player"]]
                    p_box = g["box_scores"][pitch_key][pitcher["Player"]]
                    
                    if outcome in ["1B", "2B", "3B", "HR"]:
                        b_box["H"] += 1; b_box[outcome] += 1; b_box["AB"] += 1
                        p_box["H"] += 1
                    elif outcome == "BB":
                        b_box["BB"] += 1; p_box["BB"] += 1
                    elif outcome == "K":
                        b_box["K"] += 1; b_box["AB"] += 1
                        p_box["K"] += 1; p_box["Outs"] += 1
                    # outcome == "OUT" crediting is deferred below, since we don't yet know
                    # whether it resolves as a genuine out, a double play (2 outs), or a
                    # reached-on-error (0 outs) until step_markov_24_state runs.
                    
                    prior_state_outs = state["outs"]
                    state["outs"], state["bases"], scored_runners, log_text = self.step_markov_24_state(state, outcome, batter["Player"], batter["SPD"])

                    if outcome == "OUT":
                        # A reached-on-error still counts as an at-bat (correctly lowers batting
                        # average) but doesn't charge the pitcher an out. A double play charges
                        # the pitcher TWO outs, not one -- using the actual outs delta here
                        # (rather than assuming every "OUT" outcome is worth exactly one out)
                        # keeps this correct automatically for both cases instead of needing a
                        # separate hardcoded rule per sub-event.
                        b_box["AB"] += 1
                        p_box["Outs"] += (state["outs"] - prior_state_outs)

                    runs = len(scored_runners)
                    if runs > 0:
                        b_box["RBI"] += runs
                        p_box["ER"] += runs
                        for runner_name in scored_runners:
                            if runner_name in g["box_scores"][t_key]:
                                g["box_scores"][t_key][runner_name]["R"] += 1
                        if g["top_half"]: g["away_score"] += runs
                        else: g["home_score"] += runs
                        
                    if tracking_mode:
                        g["log_history"].append(f"**Inning {g['inning']} ({'Top' if g['top_half'] else 'Bot'}):** `{batter['Player']}` vs `{pitcher['Player']}` ➔ **{outcome}** ({log_text}). [A:{g['away_score']} - H:{g['home_score']}]")
                    
                    if g["top_half"]: g["away_lineup_idx"] += 1
                    else: g["home_lineup_idx"] += 1
                    if g["inning"] >= 9 and not g["top_half"] and g["home_score"] > g["away_score"]: break
                        
                g["top_half"] = not g["top_half"]
                if g["top_half"]: g["inning"] += 1
                
            return g

    # ----------------------------------------------------
    # RUN ENGINE MONTE CARLO INTEGRATION
    # ----------------------------------------------------
    env_tensors = {"temp": temperature, "elevation": stadium_alt, "wind": wind_vector}
    park_rules = BALLPARK_ENV.get(home_selection, {"run_mult": 1.0, "hr_mult": 1.0, "babip_mult": 1.0})

    def _mc_results_are_stale(results):
        # Guards against stale st.session_state["monte_carlo_results"] left over from a
        # previous version of this app (e.g. right after a code update) whose cached dict
        # shape doesn't match what the current renderers expect.
        if results is None:
            return True
        required_top_keys = {"home_win_prob", "away_box_means", "home_box_means", "away_pitch_means", "home_pitch_means",
                              "away_role_map", "home_role_map", "away_box_dist", "home_box_dist", "away_pitch_dist", "home_pitch_dist"}
        if not required_top_keys.issubset(results.keys()):
            return True
        required_hit_keys = {"AB","H","1B","2B","3B","HR","BB","RBI","K","R","SB"}
        for box in (results["away_box_means"], results["home_box_means"]):
            for stats in box.values():
                if not required_hit_keys.issubset(stats.keys()):
                    return True
        required_pitch_keys = {"K","BB","H","ER","Outs"}
        for box in (results["away_pitch_means"], results["home_pitch_means"]):
            for stats in box.values():
                if not required_pitch_keys.issubset(stats.keys()):
                    return True
        return False

    if _mc_results_are_stale(st.session_state["monte_carlo_results"]):
        with st.spinner("Executing 1,000x Structural Monte Carlo Base Operations..."):
            engine = DipsMarkovEngine(st.session_state["locked_away_lineup"], st.session_state["locked_home_lineup"], st.session_state["locked_away_sp"], st.session_state["locked_home_sp"], st.session_state["locked_away_bullpen"], st.session_state["locked_home_bullpen"], park_rules, env_tensors)
            home_wins = 0
            agg_away_box = {p["Player"]: {"AB":0,"H":0,"1B":0,"2B":0,"3B":0,"HR":0,"BB":0,"RBI":0,"K":0,"R":0,"SB":0} for p in st.session_state["locked_away_lineup"]}
            agg_home_box = {p["Player"]: {"AB":0,"H":0,"1B":0,"2B":0,"3B":0,"HR":0,"BB":0,"RBI":0,"K":0,"R":0,"SB":0} for p in st.session_state["locked_home_lineup"]}
            away_pitcher_pool = [st.session_state["locked_away_sp"]] + st.session_state["locked_away_bullpen"]
            home_pitcher_pool = [st.session_state["locked_home_sp"]] + st.session_state["locked_home_bullpen"]
            agg_away_pitch = {p["Player"]: {"K":0,"BB":0,"H":0,"ER":0,"Outs":0} for p in away_pitcher_pool}
            agg_home_pitch = {p["Player"]: {"K":0,"BB":0,"H":0,"ER":0,"Outs":0} for p in home_pitcher_pool}
            # Per-iteration outcome tracking (not just running sums) -- lets props report the
            # real empirical probability of clearing a line, not just an average-vs-line
            # comparison, which is misleading for skewed counting stats like HR (mostly 0s
            # with occasional multi-HR games) or K (varies a lot game-to-game).
            dist_away_box = {p["Player"]: {"H": [], "TB": [], "HR": [], "RBI": [], "R": [], "SB": []} for p in st.session_state["locked_away_lineup"]}
            dist_home_box = {p["Player"]: {"H": [], "TB": [], "HR": [], "RBI": [], "R": [], "SB": []} for p in st.session_state["locked_home_lineup"]}
            dist_away_pitch = {p["Player"]: {"K": []} for p in away_pitcher_pool}
            dist_home_pitch = {p["Player"]: {"K": []} for p in home_pitcher_pool}
            
            iterations = 1000
            for _ in range(iterations):
                sim_res = engine.run_full_game(tracking_mode=False)
                if sim_res["home_score"] > sim_res["away_score"]: home_wins += 1
                for p in agg_away_box:
                    for s in agg_away_box[p]: agg_away_box[p][s] += sim_res["box_scores"]["away"][p][s]
                    stats = sim_res["box_scores"]["away"][p]
                    tb = stats["1B"] + stats["2B"]*2 + stats["3B"]*3 + stats["HR"]*4
                    dist_away_box[p]["H"].append(stats["H"]); dist_away_box[p]["TB"].append(tb)
                    dist_away_box[p]["HR"].append(stats["HR"]); dist_away_box[p]["RBI"].append(stats["RBI"]); dist_away_box[p]["R"].append(stats["R"])
                    dist_away_box[p]["SB"].append(stats["SB"])
                for p in agg_home_box:
                    for s in agg_home_box[p]: agg_home_box[p][s] += sim_res["box_scores"]["home"][p][s]
                    stats = sim_res["box_scores"]["home"][p]
                    tb = stats["1B"] + stats["2B"]*2 + stats["3B"]*3 + stats["HR"]*4
                    dist_home_box[p]["H"].append(stats["H"]); dist_home_box[p]["TB"].append(tb)
                    dist_home_box[p]["HR"].append(stats["HR"]); dist_home_box[p]["RBI"].append(stats["RBI"]); dist_home_box[p]["R"].append(stats["R"])
                    dist_home_box[p]["SB"].append(stats["SB"])
                for p in agg_away_pitch:
                    for s in agg_away_pitch[p]: agg_away_pitch[p][s] += sim_res["box_scores"]["away_pitching"][p][s]
                    dist_away_pitch[p]["K"].append(sim_res["box_scores"]["away_pitching"][p]["K"])
                for p in agg_home_pitch:
                    for s in agg_home_pitch[p]: agg_home_pitch[p][s] += sim_res["box_scores"]["home_pitching"][p][s]
                    dist_home_pitch[p]["K"].append(sim_res["box_scores"]["home_pitching"][p]["K"])
                    
            for p in agg_away_box:
                for s in agg_away_box[p]: agg_away_box[p][s] /= iterations
            for p in agg_home_box:
                for s in agg_home_box[p]: agg_home_box[p][s] /= iterations
            for p in agg_away_pitch:
                for s in agg_away_pitch[p]: agg_away_pitch[p][s] /= iterations
            for p in agg_home_pitch:
                for s in agg_home_pitch[p]: agg_home_pitch[p][s] /= iterations
                
            away_role_map = {p["Player"]: p["Role"] for p in away_pitcher_pool}
            home_role_map = {p["Player"]: p["Role"] for p in home_pitcher_pool}
                
            st.session_state["monte_carlo_results"] = {
                "home_win_prob": home_wins / iterations,
                "away_box_means": agg_away_box, "home_box_means": agg_home_box,
                "away_pitch_means": agg_away_pitch, "home_pitch_means": agg_home_pitch,
                "away_role_map": away_role_map, "home_role_map": home_role_map,
                "away_box_dist": dist_away_box, "home_box_dist": dist_home_box,
                "away_pitch_dist": dist_away_pitch, "home_pitch_dist": dist_home_pitch,
            }

    # ----------------------------------------------------
    # SPORTSBOOK & POSTSEASON INTERFACE RENDERS
    # ----------------------------------------------------
    mc = st.session_state["monte_carlo_results"]
    h_prob = mc["home_win_prob"]
    
    def convert_prob_to_line(p):
        if p >= 0.999: return "-10000"
        if p <= 0.001: return "+10000"
        return f"-{int((p/(1-p))*100)}" if p >= 0.50 else f"+{int(((1-p)/p)*100)}"
        
    market_implied_prob = abs(vegas_line_input)/(abs(vegas_line_input)+100) if vegas_line_input < 0 else 100/(vegas_line_input+100)
    ev_edge = (h_prob - market_implied_prob) * 100

    st.markdown("### 🎲 High-Convergence Sportsbook Matrix Analytics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sim Projected Winner", home_selection if h_prob >= 0.5 else away_selection)
    c2.metric("Engine Fair Line Prob", f"{round(h_prob*100, 2)}%", delta=f"Fair Line: {convert_prob_to_line(h_prob)}")
    c3.metric("Vegas Implied Baseline", f"{round(market_implied_prob*100, 1)}%", delta=f"Input: {vegas_line_input}")
    c4.metric("Alpha Discovered Edge", f"{round(ev_edge, 2)}% EV", delta_color="inverse" if ev_edge < 0 else "normal")

    # Kelly criterion stake sizing -- given the model's win probability and the moneyline price
    # entered above, this computes the mathematically "optimal" fraction of a bankroll to risk.
    # This is a standard staking formula, not financial advice -- full Kelly is also famously
    # aggressive/volatile in practice, which is why many bettors use a fraction of it (shown below).
    def kelly_fraction(model_prob, american_odds):
        decimal_odds = 1 + (100 / abs(american_odds)) if american_odds < 0 else 1 + (american_odds / 100)
        b = decimal_odds - 1
        return (b * model_prob - (1 - model_prob)) / b

    home_kelly = kelly_fraction(h_prob, vegas_line_input)
    st.markdown("#### 💰 Kelly Stake Sizing (Home Line, at the price entered above)")
    k1, k2, k3 = st.columns(3)
    k1.metric("Full Kelly Stake", f"{max(0, home_kelly)*100:.1f}% of bankroll")
    k2.metric("Half Kelly (common in practice)", f"{max(0, home_kelly)*50:.1f}% of bankroll")
    k3.metric("Quarter Kelly (conservative)", f"{max(0, home_kelly)*25:.1f}% of bankroll")
    if home_kelly <= 0:
        st.caption("Kelly stake is 0% -- at this price, the model doesn't see a positive edge on the home side, so the formula says not to bet it.")
    else:
        st.caption("This is a mathematical staking formula based on your inputs, not financial advice -- Kelly assumes your model probability is accurate, which it isn't guaranteed to be, and full Kelly stakes are volatile even when the edge is real. Many bettors use half or quarter Kelly for that reason.")

    st.markdown("---")
    st.markdown("### 🏆 Best-Of-7 Postseason Series Tensor Mode")
    if st.button("Simulate Full 7-Game World Series Run", use_container_width=True):
        a_wins, h_wins = 0, 0
        series_history = []
        for game_num in range(1, 8):
            if a_wins == 4 or h_wins == 4: break
            s_engine = DipsMarkovEngine(st.session_state["locked_away_lineup"], st.session_state["locked_home_lineup"], st.session_state["locked_away_sp"], st.session_state["locked_home_sp"], st.session_state["locked_away_bullpen"], st.session_state["locked_home_bullpen"], park_rules, env_tensors)
            s_res = s_engine.run_full_game(tracking_mode=False)
            if s_res["home_score"] > s_res["away_score"]:
                h_wins += 1; winner = home_selection
            else:
                a_wins += 1; winner = away_selection
            series_history.append(f"Game {game_num}: {away_selection} {s_res['away_score']} @ {home_selection} {s_res['home_score']} ➔ Winner: **{winner}**")
        st.markdown(f"#### Series Resolution: **{home_selection if h_wins==4 else away_selection} Wins ({h_wins if h_wins==4 else a_wins} - {a_wins if h_wins==4 else h_wins})**")
        for h in series_history: st.write(h)

    st.markdown("---")
    def render_hitting_prop_matrix_view(means_data, dist_data):
        # Standard PrizePicks/DK-style lines by market. Edge = projection minus the line.
        H_LINE, HR_LINE, RBI_LINE, R_LINE, TB_LINE, SB_LINE = 1.5, 0.5, 0.5, 0.5, 1.5, 0.5
        def prob_over(values, line):
            if not values: return 0.5
            return sum(1 for v in values if v > line) / len(values)
        rows = []
        for name, stats in means_data.items():
            hits_exp = stats.get("H", 0)
            hr_exp = stats.get("HR", 0)
            rbi_exp = stats.get("RBI", 0)
            r_exp = stats.get("R", 0)
            sb_exp = stats.get("SB", 0)
            tb_exp = stats.get("1B", 0) + (stats.get("2B", 0) * 2) + (stats.get("3B", 0) * 3) + (stats.get("HR", 0) * 4)
            dk_exp = (hits_exp * 3) + (stats.get("2B", 0) * 2) + (stats.get("HR", 0) * 7) + (stats.get("RBI", 0) * 2) + (stats.get("BB", 0) * 2) + (r_exp * 2) + (sb_exp * 5)
            d = dist_data.get(name, {})
            h_p = prob_over(d.get("H", []), H_LINE)
            hr_p = prob_over(d.get("HR", []), HR_LINE)
            rbi_p = prob_over(d.get("RBI", []), RBI_LINE)
            r_p = prob_over(d.get("R", []), R_LINE)
            tb_p = prob_over(d.get("TB", []), TB_LINE)
            sb_p = prob_over(d.get("SB", []), SB_LINE)
            rows.append({
                "Player Asset": name,
                "Proj Hits": round(hits_exp, 2), "Hits Line": H_LINE, "Hits Over%": f"{h_p*100:.0f}%",
                "Proj HR": round(hr_exp, 2), "HR Line": HR_LINE, "HR Over%": f"{hr_p*100:.0f}%",
                "Proj RBI": round(rbi_exp, 2), "RBI Line": RBI_LINE, "RBI Over%": f"{rbi_p*100:.0f}%",
                "Proj Runs": round(r_exp, 2), "Runs Line": R_LINE, "Runs Over%": f"{r_p*100:.0f}%",
                "Proj SB": round(sb_exp, 2), "SB Line": SB_LINE, "SB Over%": f"{sb_p*100:.0f}%",
                "Proj TB": round(tb_exp, 2), "TB Line": TB_LINE, "TB Over%": f"{tb_p*100:.0f}%",
                "DraftKings FP Exp": round(dk_exp, 2)
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Over% = share of the 1,000 simulated games where the player actually cleared the line -- a truer read than comparing the average alone, since HR/RBI/Runs are lumpy stats (mostly 0s with occasional multi-event games) that an average can understate or overstate.")

    def render_pitching_prop_matrix_view(means_data, role_map, dist_data):
        def prob_over(values, line):
            if not values: return 0.5
            return sum(1 for v in values if v > line) / len(values)
        rows = []
        for name, stats in means_data.items():
            role = role_map.get(name, "RP")
            ip_exp = stats.get("Outs", 0) / 3.0
            k_exp = stats.get("K", 0)
            # Standard-shaped K lines: starters get a full-game line, bullpen arms get a short-relief line
            k_line = 4.5 if role == "SP" else 0.5
            k_p = prob_over(dist_data.get(name, {}).get("K", []), k_line)
            rows.append({
                "Pitcher": name, "Role": role,
                "Proj IP": round(ip_exp, 2),
                "Proj K": round(k_exp, 2), "K Line": k_line, "K Over%": f"{k_p*100:.0f}%",
                "Proj BB Allowed": round(stats.get("BB", 0), 2),
                "Proj H Allowed": round(stats.get("H", 0), 2),
                "Proj ER": round(stats.get("ER", 0), 2)
            })
        # Show starters first, then bullpen in appearance order
        rows.sort(key=lambda r: 0 if r["Role"] == "SP" else 1)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("K Over% = share of the 1,000 simulated games where the pitcher actually cleared the strikeout line.")

    def render_hr_leaderboard(away_team_name, away_means, away_dist, home_team_name, home_means, home_dist, park_hr_mult):
        # Combines both lineups into one ranked list, sorted by real simulated
        # HR probability -- this reuses the exact same regressed, park- and
        # weather-adjusted HR projections already computed for the per-team
        # prop tables above, just re-sorted into a single cross-team view.
        # When CONTACT_QUALITY has data for a player (see
        # refresh_contact_quality.py), their real Statcast Barrel%/HardHit%/
        # xwOBA gets shown alongside the simulated probability -- this is
        # genuinely optional context, not baked into the underlying
        # simulation itself, so it's fine for some/all players to show
        # blank here if that data hasn't been refreshed or isn't available
        # for a given player yet.
        def prob_over(values, line):
            if not values: return 0.0
            return sum(1 for v in values if v > line) / len(values)

        rows = []
        for team_name, means_data, dist_data in [(away_team_name, away_means, away_dist), (home_team_name, home_means, home_dist)]:
            for name, stats in means_data.items():
                hr_exp = stats.get("HR", 0)
                hr_p = prob_over(dist_data.get(name, {}).get("HR", []), 0.5)
                cq = CONTACT_QUALITY.get(name, {})
                rows.append({
                    "Team": team_name, "Hitter": name,
                    "Proj HR": round(hr_exp, 3), "HR Over 0.5%": f"{hr_p*100:.1f}%",
                    "Barrel%": cq.get("barrel_pct"), "HardHit%": cq.get("hardhit_pct"),
                    "xwOBA": cq.get("xwoba"), "Exit Velo": cq.get("avg_exit_velo"),
                    "_sort": hr_p,
                })

        rows.sort(key=lambda r: r["_sort"], reverse=True)
        for r in rows: del r["_sort"]

        park_note = "hitter-friendly" if park_hr_mult > 1.03 else ("pitcher-friendly" if park_hr_mult < 0.97 else "roughly neutral")
        st.caption(f"Tonight's park HR factor: {park_hr_mult:.2f} ({park_note}) -- already baked into every projection below.")
        if not CONTACT_QUALITY:
            st.caption("Real Statcast contact-quality data (Barrel%/HardHit%/xwOBA) isn't loaded yet -- run refresh_contact_quality.py to add it.")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Ranked by HR Over 0.5% (share of the 1,000 simulated games with at least one home run). This reflects simulated outcome probability -- it does not include Statcast contact-quality data (Barrel%, HardHit%, xwOBAcon), which isn't currently part of the roster data pipeline.")

    t_prop_away, t_prop_home, t_pitch_away, t_pitch_home, t_hr_board = st.tabs([
        f"📊 {away_selection} Hitting Props", f"📊 {home_selection} Hitting Props",
        f"⚾ {away_selection} Pitching Props", f"⚾ {home_selection} Pitching Props",
        "💣 HR Leaderboard"
    ])
    with t_prop_away: render_hitting_prop_matrix_view(mc["away_box_means"], mc["away_box_dist"])
    with t_prop_home: render_hitting_prop_matrix_view(mc["home_box_means"], mc["home_box_dist"])
    with t_pitch_away: render_pitching_prop_matrix_view(mc["away_pitch_means"], mc["away_role_map"], mc["away_pitch_dist"])
    with t_pitch_home: render_pitching_prop_matrix_view(mc["home_pitch_means"], mc["home_role_map"], mc["home_pitch_dist"])
    with t_hr_board: render_hr_leaderboard(away_selection, mc["away_box_means"], mc["away_box_dist"], home_selection, mc["home_box_means"], mc["home_box_dist"], park_rules["hr_mult"])

    st.markdown("### 🏟️ Live Play-By-Play Visual Render Interface")
    if st.button("Launch Immersive Real-Time Simulation Walkthrough Loop", type="primary", use_container_width=True):
        active_engine = DipsMarkovEngine(st.session_state["locked_away_lineup"], st.session_state["locked_home_lineup"], st.session_state["locked_away_sp"], st.session_state["locked_home_sp"], st.session_state["locked_away_bullpen"], st.session_state["locked_home_bullpen"], park_rules, env_tensors)
        g = active_engine.run_full_game(tracking_mode=True)
        log_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        for i, log_entry in enumerate(g["log_history"]):
            log_placeholder.markdown(f"""
            <div style="background-color:#0f172a; border-left: 5px solid #38bdf8; padding: 15px; border-radius: 4px; font-family: monospace;">
                <p style="color:#f8fafc; font-size:14px; margin:0;">{log_entry}</p>
            </div>
            """, unsafe_allow_html=True)
            progress_bar.progress(min(1.0, (i + 1) / len(g["log_history"])))
            if playback_speed > 0: time.sleep(playback_speed)
        st.success(f"🏁 Interface Playback Complete. Final Score Matrix Resolved: {away_selection} {g['away_score']} - {home_selection} {g['home_score']}")
