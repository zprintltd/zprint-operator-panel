import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="ZPRINT Operator Panel", layout="wide")

# ----------------------------
# CUSTOM CSS (BUTTON STYLING)
# ----------------------------
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

# 🔁 REPLACE WITH YOUR REAL SHEET URL
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14Ke6jLoN94HnwltRwCME-U0u5KK3adUZbBkXEL2LHxM/edit?usp=sharing")
sheet = spreadsheet.worksheet("WO_Log")

# ----------------------------
# LOAD DATA
# ----------------------------
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Clean column names (important)
df.columns = df.columns.str.strip()

st.title("ZPRINT Operator Work Panel")

if df.empty:
    st.warning("No data found in WO_Log.")
    st.stop()

# ----------------------------
# FILTER ACTIVE WORK
# ----------------------------
df_active = df[df["Status"] != "Completed"].copy()

# ----------------------------
# PREPARE DISPLAY DATA
# ----------------------------
display_columns = [
    "WO Number",
    "Date",
    "Client Name",
    "Category",
    "Subcategory",
    "Full Filename",
    "Assigned To Name",
    "Status"
]

# Ensure only existing columns are selected
display_columns = [col for col in display_columns if col in df_active.columns]

display_df = df_active[display_columns].copy()

# Sort newest first
if "WO Number" in display_df.columns:
    display_df["WO Number"] = pd.to_numeric(
        display_df["WO Number"],
        errors="coerce"
    )
    display_df = display_df.sort_values(
        by="WO Number",
        ascending=False,
        na_position="last"
    )

# Format Date if exists
if "Date" in display_df.columns:
    display_df["Date"] = pd.to_datetime(
        display_df["Date"], errors="coerce"
    ).dt.strftime("%d-%m-%Y")

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
    subset=["Status"] if "Status" in display_df.columns else []
)

# ----------------------------
# DISPLAY TABLE
# ----------------------------
st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True
)

st.divider()

# ----------------------------
# UPDATE STATUS SECTION
# ----------------------------
if not df_active.empty:

    wo_list = df_active["WO Number"].tolist()

    selected_wo = st.selectbox(
        "Select WO to Update",
        wo_list
    )

    new_status = st.selectbox(
        "Change Status To",
        ["In Progress", "Completed"]
    )

    if st.button("Update Status"):

        # Find matching row in dataframe
        row_match = df[df["WO Number"] == selected_wo]

        if not row_match.empty:
            row_index = row_match.index[0] + 2  # +2 because header + zero index

            # Find Status column number dynamically
            header_row = sheet.row_values(1)
            status_col_index = header_row.index("Status") + 1

            sheet.update_cell(row_index, status_col_index, new_status)

            st.success(f"WO {selected_wo} updated to {new_status}")
            st.experimental_rerun()
        else:
            st.error("WO not found.")
else:
    st.info("No active work orders to update.")
