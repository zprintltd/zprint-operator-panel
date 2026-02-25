st.markdown("""
<style>
div.stButton > button {
    background-color: #1F2933;
    color: white;
    border-radius: 8px;
    padding: 0.5em 1em;
    font-weight: 600;
}

div.stButton > button:hover {
    background-color: #F4B400;
    color: black;
}
</style>
""", unsafe_allow_html=True)
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# ----------------------------
# GOOGLE SHEETS CONNECTION
# ----------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    scope
)

client = gspread.authorize(creds)

client = gspread.authorize(creds)
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit?usp=sharing").worksheet("WO_Log")

# ----------------------------
# LOAD DATA
# ----------------------------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Only show active work
df_active = df[df["Status"] != "Completed"]

st.title("ZPRINT Operator Work Panel")

# ----------------------------
# ----------------------------
# PREPARE DISPLAY DATA
# ----------------------------

# Only show active work (exclude Completed if desired)
df_active = df.copy()

# Optional: comment this line if you want to show ALL
# df_active = df[df["Status"] != "Completed"]

# Select columns to display
display_df = df_active[[
    "WO Number",
    "Date",
    "Client Name (View)",      # Change to your exact column name
    "Category",
    "Subcategory",
    "Full Filename",
    "Assigned To Name",        # Change to your exact column name
    "Status"
]].copy()

# Sort newest WO first
display_df = display_df.sort_values(
    by="WO Number",
    ascending=False
)

# ----------------------------
# STATUS COLOR FUNCTION
# ----------------------------

def color_status(val):
    if val == "Completed":
        return "color: green; font-weight: 600;"
    elif val == "In Progress":
        return "color: orange; font-weight: 600;"
    elif val == "Pending":
        return "color: red; font-weight: 600;"
    return ""

styled_df = display_df.style.map(
    color_status,
    subset=["Status"]
)

# ----------------------------
# DISPLAY TABLE
# ----------------------------

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True
)
# ----------------------------
# SELECT WO TO UPDATE
# ----------------------------
wo_list = df_active["WO Number"].tolist()
selected_wo = st.selectbox("Select WO to Update", wo_list)

new_status = st.selectbox(
    "Change Status To",
    ["In Progress", "Completed"]
)

if st.button("Update Status"):

    # Find row index in Google Sheet
    cell = sheet.find(str(selected_wo))
    row_index = cell.row

    # Status column is K (11th column)
    sheet.update_cell(row_index, 11, new_status)

    st.success(f"WO {selected_wo} updated to {new_status}")
