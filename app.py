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
# Pull the URL from your existing secrets
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet_url"]

# Open the spreadsheet using the URL instead of the name
spreadsheet = client.open_by_url(SHEET_URL)

# Define your worksheets
sheet = spreadsheet.worksheet("WO_Log")
users_sheet = spreadsheet.worksheet("users")

# Load records
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ----------------------------
# USER NAME MAPPING
# ----------------------------
try:
    user_data = users_sheet.get_all_records()
    df_users = pd.DataFrame(user_data)
    
    # Standardize column headers
    df_users.columns = [str(c).strip() for c in df_users.columns]
    
    # Mapping: Email (Col A) -> Name (Col B)
    # iloc[:, 0] is the 1st column, iloc[:, 1] is the 2nd
    name_map = dict(zip(
        df_users.iloc[:, 0].astype(str).str.strip().str.lower(), 
        df_users.iloc[:, 1].astype(str).str.strip()
    ))
    
    # Find the column in WO_Log that contains emails (usually "Assigned To")
    staff_email_col = next((c for c in df.columns if 'Assigned' in c), None)
    
    if staff_email_col:
        # Create the Name column: 
        # 1. Look up the email in the map
        # 2. If it's already a name (not found in map), keep the original value
        df["Assigned To Name"] = (
            df[staff_email_col]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(name_map)
            .fillna(df[staff_email_col]) 
        )
    else:
        df["Assigned To Name"] = "Unassigned"

except Exception as e:
    st.error(f"Mapping Error: {e}")
    df["Assigned To Name"] = "Mapping Error"
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
# UPDATE STATUS & ASSIGNMENT SECTION
# ----------------------------
st.subheader("📝 Update Task Details")

if not df_active.empty:
    # Prepare the list of WO numbers for the dropdown
    wo_list = df_active["WO Number"].astype(int).tolist()
    
    # Prepare the list of Staff Names for the dropdown
    # We pull this from our df_users mapping or list
    staff_options = sorted(list(name_map.values()))
    if "Unassigned" not in staff_options:
        staff_options.insert(0, "Unassigned")

    # Create three columns for a clean UI
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_wo = st.selectbox("Select WO #", wo_list)
    
    # Find current values for the selected WO to set as defaults
    current_row = df_active[df_active["WO Number"] == selected_wo].iloc[0]
    
    with col2:
        # Default to current assignee
        current_assignee = current_row["Assigned To Name"]
        try:
            assignee_idx = staff_options.index(current_assignee)
        except ValueError:
            assignee_idx = 0
            
        new_assignee = st.selectbox("Reassign To", staff_options, index=assignee_idx)

    with col3:
        # Default to current status
        current_status = current_row["Status"]
        # Clean the HTML tags if they were applied in the display_df
        if "Pending" in current_status: current_status = "Pending"
        if "In progress" in current_status: current_status = "In progress"
            
        status_options = ["Pending", "In progress", "Completed"]
        try:
            status_idx = status_options.index(current_status)
        except ValueError:
            status_idx = 0
            
        new_status = st.selectbox("Change Status", status_options, index=status_idx)

    if st.button("Save Changes", use_container_width=True):
        row_match = df[df["WO Number"] == selected_wo]
        
        if not row_match.empty:
            # 1. Calculate row index (header offset)
            row_index = row_match.index[0] + 2 
            
            # 2. Get header locations
            header_row = sheet.row_values(1)
            status_col_idx = header_row.index("Status") + 1
            # Dynamically find the original email/staff column
            staff_col_name = next((c for c in header_row if 'Assigned' in c), "Assigned To")
            staff_col_idx = header_row.index(staff_col_name) + 1
            
            # 3. Handle Email mapping for the save
            # We want to save the EMAIL back to the sheet, not the Name
            # Find the email key that belongs to the selected name
            reverse_map = {name: email for email, name in name_map.items()}
            email_to_save = reverse_map.get(new_assignee, new_assignee)

            # 4. Update both cells in Google Sheets
            sheet.update_cell(row_index, status_col_idx, new_status)
            sheet.update_cell(row_index, staff_col_idx, email_to_save)

            st.success(f"✅ WO {selected_wo} updated successfully!")
            st.rerun()
