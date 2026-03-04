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
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- NEW: LOAD USERS FOR NAME MAPPING ---
try:
    # Assuming 'users_sheet' is your connection to the Users tab
    # If you haven't defined it, use: users_sheet = client.open("YourSheetName").worksheet("users")
    user_data = users_sheet.get_all_records()
    df_users = pd.DataFrame(user_data)
    
    # Create mapping: Email (Col A) -> Name (Col B)
    # Using .strip() and .lower() to ensure matches even with typos
    name_map = dict(zip(
        df_users.iloc[:, 0].astype(str).str.strip().str.lower(), 
        df_users.iloc[:, 1].astype(str).str.strip()
    ))
except Exception as e:
    st.error(f"Could not load user names: {e}")
    name_map = {}

if df.empty:
    st.warning("No data found in WO_Log.")
    st.stop()

# Clean column names
df.columns = df.columns.str.strip()

# ----------------------------
# CLEAN & FILTER DATA
# ----------------------------

# 1. Create the "Assigned To Name" column dynamically
# We look for the column that usually holds the email (often 'Assigned To')
staff_email_col = next((c for c in df.columns if 'Assigned' in c), None)

if staff_email_col:
    # Map the email to the Name, if not found, keep the original value (the email)
    df["Assigned To Name"] = (
        df[staff_email_col]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(name_map)
        .fillna(df[staff_email_col]) # Fallback to email if name not found
    )
else:
    df["Assigned To Name"] = "Unassigned"

# Convert WO Number to numeric
df["WO Number"] = pd.to_numeric(df["WO Number"], errors="coerce")
df = df[df["WO Number"].notna()]

if "Date" in df.columns:
    df = df[df["Date"].notna()]

# Keep only Pending & In progress
df_active = df[df["Status"].isin(["Pending", "In progress"])].copy()

# ----------------------------
# TITLE
# ----------------------------
st.title("ZPRINT Operator Work Panel")

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
    "Assigned To Name", # This now exists because we created it above!
    "Status"
]

# Ensure we only try to display columns that actually exist
display_columns = [col for col in display_columns if col in df_active.columns]
display_df = df_active[display_columns].copy()

# Format WO Number cleanly
display_df["WO Number"] = display_df["WO Number"].astype(int)
display_df = display_df.sort_values(by="WO Number", ascending=False)

# Format Date
if "Date" in display_df.columns:
    display_df["Date"] = pd.to_datetime(
        display_df["Date"],
        errors="coerce"
    ).dt.strftime("%d-%m-%Y")

# ----------------------------
# STATUS BADGE RENDERING
# ----------------------------
def render_status_badge(status):
    if status == "Pending":
        return '<span class="status-pending" style="padding: 2px 8px; border-radius: 4px; background-color: #ffeeba; color: #856404;">Pending</span>'
    elif status == "In progress":
        return '<span class="status-progress" style="padding: 2px 8px; border-radius: 4px; background-color: #b8daff; color: #004085;">In progress</span>'
    return status

display_df["Status"] = display_df["Status"].apply(render_status_badge)

# Display Table
st.markdown(
    display_df.to_html(escape=False, index=False),
    unsafe_allow_html=True
)

st.divider()

# ----------------------------
# UPDATE STATUS SECTION
# ----------------------------
if not df_active.empty:
    wo_list = df_active["WO Number"].astype(int).tolist()
    
    col_a, col_b = st.columns(2)
    selected_wo = col_a.selectbox("Select WO to Update", wo_list)
    new_status = col_b.selectbox("Change Status To", ["In progress", "Completed"])

    if st.button("Update Status", use_container_width=True):
        row_match = df[df["WO Number"] == selected_wo]
        if not row_match.empty:
            row_index = row_match.index[0] + 2 
            header_row = sheet.row_values(1)
            status_col_index = header_row.index("Status") + 1
            
            sheet.update_cell(row_index, status_col_index, new_status)
            st.success(f"WO {selected_wo} updated to {new_status}")
            st.rerun()
else:
    st.info("No active work orders to update.")
