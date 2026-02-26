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
# --- Clean & Format WO Number ---
if "WO Number" in display_df.columns:
    display_df["WO Number"] = pd.to_numeric(
        display_df["WO Number"],
        errors="coerce"
    ).fillna(0).astype(int)

    display_df = display_df.sort_values(
        by="WO Number",
        ascending=False
    )

# Format Date if exists
if "Date" in display_df.columns:
    display_df["Date"] = pd.to_datetime(
        display_df["Date"], errors="coerce"
    ).dt.strftime("%d-%m-%Y")

# ----------------------------
# STATUS COLOR FUNCTION
# ----------------------------
def render_status_badge(status):
    if status == "Pending":
        return '<span class="status-pending">Pending</span>'
    elif status == "In Progress":
        return '<span class="status-progress">In Progress</span>'
    elif status == "Completed":
        return '<span class="status-completed">Completed</span>'
    return status

if "Status" in display_df.columns:
    display_df["Status"] = display_df["Status"].apply(render_status_badge)

st.markdown(
    display_df.to_html(escape=False, index=False),
    unsafe_allow_html=True
)

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
