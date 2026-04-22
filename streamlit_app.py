import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import altair as alt

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Food Waste Management", layout="wide")

DB_PATH = "food_waste.db"

# ---------------- DATABASE SETUP ----------------
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # food listings table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS food_listings (
        Food_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Food_Name TEXT,
        Quantity INTEGER,
        Expiry_Date TEXT,
        Provider_ID INTEGER,
        Location TEXT,
        Food_Type TEXT,
        Meal_Type TEXT
    )
    """)

    # claims table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        Claim_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Food_ID INTEGER,
        Receiver_ID INTEGER,
        Status TEXT,
        Timestamp TEXT
    )
    """)

    con.commit()
    con.close()

# ---------------- DB FUNCTIONS ----------------
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

# ---------------- INIT ----------------
init_db()

# ---------------- TITLE ----------------
st.title("🍱 Food Waste Management System")

# ---------------- MENU ----------------
menu = st.sidebar.selectbox("Choose Action", [
    "Dashboard",
    "Add Listing",
    "Make Claim",
    "Update Claim Status"
])

# =====================================================
# DASHBOARD
# =====================================================
if menu == "Dashboard":
    st.header("📊 Food Listings Dashboard")

    try:
        df = run_query("SELECT * FROM food_listings")

        if df.empty:
            st.info("No food listings available.")
        else:
            st.dataframe(df, use_container_width=True)

            # chart
            st.subheader("Listings by City")

            try:
                city_counts = df["Location"].astype(str).value_counts().reset_index()
                city_counts.columns = ["City", "Listings"]

                chart = alt.Chart(city_counts).mark_bar().encode(
                    x="City:N",
                    y="Listings:Q",
                    tooltip=["City", "Listings"]
                )

                st.altair_chart(chart, use_container_width=True)

            except:
                st.warning("Chart unavailable.")

    except Exception as e:
        st.error(f"Error: {e}")

# =====================================================
# ADD LISTING
# =====================================================
elif menu == "Add Listing":
    st.header("➕ Add Food Listing")

    with st.form("add_form"):
        food = st.text_input("Food Name")
        qty = st.number_input("Quantity", min_value=1)
        exp = st.date_input("Expiry Date")
        provider = st.number_input("Provider ID", min_value=1)
        city = st.text_input("City")

        food_type = st.selectbox("Food Type", [
            "Vegetarian", "Non-Vegetarian", "Vegan"
        ])

        meal_type = st.selectbox("Meal Type", [
            "Breakfast", "Lunch", "Dinner", "Snacks"
        ])

        submit = st.form_submit_button("Save")

    if submit:
        run_exec("""
            INSERT INTO food_listings 
            (Food_Name, Quantity, Expiry_Date, Provider_ID, Location, Food_Type, Meal_Type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (food, qty, str(exp), provider, city, food_type, meal_type))

        st.success("✅ Food listing added!")

# =====================================================
# MAKE CLAIM
# =====================================================
elif menu == "Make Claim":
    st.header("📦 Make a Claim")

    df = run_query("SELECT * FROM food_listings")

    if df.empty:
        st.info("No food available.")
    else:
        st.dataframe(df)

        food_id = st.selectbox("Select Food ID", df["Food_ID"])
        receiver_id = st.number_input("Receiver ID", min_value=1)

        if st.button("Submit Claim"):
            run_exec("""
                INSERT INTO claims (Food_ID, Receiver_ID, Status, Timestamp)
                VALUES (?, ?, ?, ?)
            """, (food_id, receiver_id, "Pending", datetime.now().isoformat()))

            st.success("✅ Claim submitted!")

# =====================================================
# UPDATE CLAIM STATUS
# =====================================================
elif menu == "Update Claim Status":
    st.header("🔄 Update Claim Status")

    df = run_query("SELECT * FROM claims")

    if df.empty:
        st.info("No claims found.")
    else:
        st.dataframe(df)

        claim_id = st.selectbox("Select Claim ID", df["Claim_ID"])
        status = st.selectbox("New Status", [
            "Pending", "Completed", "Cancelled"
        ])

        if st.button("Update Status"):
            run_exec("""
                UPDATE claims SET Status=? WHERE Claim_ID=?
            """, (status, claim_id))

            st.success("✅ Status updated!")
