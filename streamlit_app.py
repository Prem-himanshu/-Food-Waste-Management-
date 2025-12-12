import streamlit as st
import pandas as pd
import sqlite3
import os
import glob
import altair as alt
from datetime import datetime

st.set_page_config(page_title="Food Waste Management", layout="wide")

DB_PATH = "food_waste.db"

# ---------------------------------------------------------
# DATABASE UTILITIES
# ---------------------------------------------------------
def list_csvs():
    return sorted(glob.glob("*.csv"))

def create_db_from_csvs():
    csv_files = list_csvs()
    if not csv_files:
        return False, "No CSV files found."

    con = sqlite3.connect(DB_PATH)
    for file in csv_files:
        name = file.lower()
        if "provider" in name:
            table = "providers"
        elif "receiver" in name:
            table = "receivers"
        elif "listing" in name:
            table = "food_listings"
        elif "claim" in name:
            table = "claims"
        else:
            table = os.path.splitext(file)[0]

        try:
            df = pd.read_csv(file)
            df.to_sql(table, con, if_exists="replace", index=False)
        except Exception as e:
            con.close()
            return False, f"Error loading {file}: {e}"

    con.close()
    return True, "Database created from CSVs."

def ensure_db_ready():
    if os.path.exists(DB_PATH):
        return True, "DB exists."

    csvs = list_csvs()
    if csvs:
        ok, msg = create_db_from_csvs()
        return ok, msg

    return False, "Database missing & no CSVs found."

def run_query(q, params=()):
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(q, con, params=params)
    con.close()
    return df

def run_exec(q, params=()):
    con = sqlite3.connect(DB_PATH)
    con.execute(q, params)
    con.commit()
    con.close()

# ---------------------------------------------------------
# CHECK DATA
# ---------------------------------------------------------
ok, msg = ensure_db_ready()
if not ok:
    st.title("Food Waste Management System")
    st.error(msg)
    st.stop()

# ---------------------------------------------------------
# MAIN UI
# ---------------------------------------------------------
st.title("Food Waste Management System")

menu = st.sidebar.selectbox("Choose action", [
    "Dashboard / Filters",
    "Show Tables",
    "Add Listing",
    "Make Claim",
    "Update Claim Status"
])

# ---------------------------------------------------------
# DASHBOARD / FILTERS
# ---------------------------------------------------------
if menu == "Dashboard / Filters":
    st.header("Explore Food Listings")

    df_list = run_query("SELECT * FROM food_listings")
    df_prov = run_query("SELECT * FROM providers")
    df_recv = run_query("SELECT * FROM receivers")

    left, right = st.columns([2, 1])

    # sidebar filters
    st.sidebar.header("Filters")
    city_filter = st.sidebar.multiselect(
        "City", sorted(df_list["Location"].astype(str).unique())
    )

    prov_filter = st.sidebar.multiselect(
        "Provider", sorted(df_prov["Name"].astype(str).unique())
    )

    food_filter = st.sidebar.multiselect(
        "Food Type", sorted(df_list["Food_Type"].astype(str).unique())
    )

    meal_filter = st.sidebar.multiselect(
        "Meal Type", sorted(df_list["Meal_Type"].astype(str).unique())
    )

    min_qty = st.sidebar.number_input("Minimum Quantity", value=0, step=1)

    # apply filters
    df_filtered = df_list.copy()

    if city_filter:
        df_filtered = df_filtered[df_filtered["Location"].isin(city_filter)]

    if prov_filter:
        pids = df_prov[df_prov["Name"].isin(prov_filter)]["Provider_ID"].tolist()
        df_filtered = df_filtered[df_filtered["Provider_ID"].isin(pids)]

    if food_filter:
        df_filtered = df_filtered[df_filtered["Food_Type"].isin(food_filter)]

    if meal_filter:
        df_filtered = df_filtered[df_filtered["Meal_Type"].isin(meal_filter)]

    df_filtered = df_filtered[df_filtered["Quantity"].astype(int) >= min_qty]

    # LEFT PANEL — data table
    with left:
        st.subheader(f"Listings ({len(df_filtered)})")
        st.dataframe(df_filtered, use_container_width=True)

    # RIGHT PANEL — metrics + chart
    with right:
        st.subheader("Quick Stats")
        st.metric("Total Listings", len(df_list))
        st.metric("Total Providers", len(df_prov))
        st.metric("Total Receivers", len(df_recv))

        # --- Safe City Chart ---
        st.subheader("Listings per City")

        try:
            city_counts = df_list["Location"].astype(str).value_counts().reset_index()
            city_counts.columns = ["City", "Listings"]

            chart = (
                alt.Chart(city_counts)
                .mark_bar()
                .encode(
                    x=alt.X("City:N", sort="-y"),
                    y="Listings:Q",
                    tooltip=["City", "Listings"]
                )
            )
            st.altair_chart(chart, use_container_width=True)
        except:
            st.info("Chart unavailable. Showing table instead.")
            st.dataframe(city_counts)

# ---------------------------------------------------------
# SHOW TABLES
# ---------------------------------------------------------
if menu == "Show Tables":
    st.header("All Tables")

    for table in ["providers", "receivers", "food_listings", "claims"]:
        st.subheader(table)
        try:
            df = run_query(f"SELECT * FROM {table}")
            st.dataframe(df)
        except:
            st.warning(f"Cannot load table: {table}")

# ---------------------------------------------------------
# ADD LISTING
# ---------------------------------------------------------
if menu == "Add Listing":
    st.header("Add New Food Listing")

    with st.form("add"):
        food = st.text_input("Food Name")
        qty = st.number_input("Quantity", min_value=1)
        exp = st.date_input("Expiry Date")
        prov_id = st.number_input("Provider ID", min_value=1)
        city = st.text_input("City")
        food_type = st.selectbox("Food Type", ["Vegetarian", "Non-Vegetarian", "Vegan"])
        meal = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snacks"])

        submit = st.form_submit_button("Save")

    if submit:
        run_exec("""
            INSERT INTO food_listings (Food_Name, Quantity, Expiry_Date, Provider_ID, Location, Food_Type, Meal_Type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (food, qty, str(exp), prov_id, city, food_type, meal))

        st.success("Listing added successfully!")

# ---------------------------------------------------------
# MAKE CLAIM
# ---------------------------------------------------------
if menu == "Make Claim":
    st.header("Make a Claim")

    df_list = run_query("SELECT * FROM food_listings")

    if df_list.empty:
        st.info("No listings available.")
    else:
        fid = st.selectbox("Select Food ID", df_list["Food_ID"])
        rid = st.number_input("Receiver ID", min_value=1)

        if st.button("Submit"):
            run_exec("""
                INSERT INTO claims (Food_ID, Receiver_ID, Status, Timestamp)
                VALUES (?, ?, ?, ?)
            """, (fid, rid, "Pending", datetime.now().isoformat()))

            st.success("Claim submitted!")

# ---------------------------------------------------------
# UPDATE CLAIM STATUS
# ---------------------------------------------------------
if menu == "Update Claim Status":
    st.header("Update Claim Status")

    df_claims = run_query("SELECT * FROM claims")

    if df_claims.empty:
        st.info("No claims found.")
    else:
        cid = st.selectbox("Select Claim ID", df_claims["Claim_ID"])
        new_status = st.selectbox("New Status", ["Pending", "Completed", "Cancelled"])

        if st.button("Update"):
            run_exec("UPDATE claims SET Status = ? WHERE Claim_ID = ?", (new_status, cid))
            st.success("Claim updated!")

