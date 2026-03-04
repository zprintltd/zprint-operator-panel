import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="ZPRINT Operator Panel", layout="wide")

# ----------------------------
# CUSTOM CSS
# ----------------------------
st.markdown("""
<style>

/* Primary Update Button */
div.stButton > button {
    background-color: #1F2933;
    color: white;
    border-radius: 8px;
    padding: 0.6em 1.2em;
    font-weight: 600;
    border: none;
}
div.stButton > button:hover {
    background-color: #F4B400;
    color: black;
}

/* Status Badge Styling */
.status-pending {
    background-color: #ffe6e6;
    color: #cc0000;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: 600;
}
.status-progress {
    background-color: #fff4cc;
    color: #cc8400;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: 600;
}
.status-completed {
    background-color: #e6f4ea;
    color: #137333;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

# ----------------------------
# GOOGLE SHEETS CONNECTION
# ----------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    scope
)

client = gspread.authorize(creds)

# 🔁 PUT YOUR REAL SHEET URL HERE
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit?usp=sharing")
sheet = spreadsheet.worksheet("WO_Log")

# ----------------------------
# LOAD DATA
# ----------------------------
# 1. Define your sheets (Make sure the names match your Google Sheet tabs exactly)
sheet = client.open("Your_Spreadsheet_Name").worksheet("WO_Log")
users_sheet = client.open("Your_Spreadsheet_Name").worksheet("users") # Add this line!

# 2. Get data from WO_Log
data = sheet.get_all_records()
df = pd.DataFrame(data)

# 3. Get data from users for mapping
try:
    user_data = users_sheet.get_all_records()
    df_users = pd.DataFrame(user_data)
    
    # Standardize column headers in users sheet
    df_users.columns = df_users.columns.str.strip()
    
    # Create mapping: Email (Col A) -> Name (Col B)
    # This assumes Email is the 1st column and Name is the 2nd
    name_map = dict(zip(
        df_users.iloc[:, 0].astype(str).str.strip().str.lower(), 
        df_users.iloc[:, 1].astype(str).str.strip()
    ))
except Exception as e:
    st.error(f"Could not load user names: {e}")
    name_map = {}
