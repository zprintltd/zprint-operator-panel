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

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json",
    scope
)

client = gspread.authorize(creds)
sheet = client.open("ZPRINT WO System – Version 2").worksheet("WO_Log")

# ----------------------------
# LOAD DATA
# ----------------------------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Only show active work
df_active = df[df["Status"] != "Completed"]

st.title("ZPRINT Operator Work Panel")

# ----------------------------
# DISPLAY TABLE
# ----------------------------
st.dataframe(
    df_active[[
        "WO Number",
        "Date",
        "Client",
        "Category",
        "Subcategory",
        "Status"
    ]]
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
