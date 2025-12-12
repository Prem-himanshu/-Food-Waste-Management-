# streamlit_app.py
# Food Waste Management — full Streamlit app
# Auto-loads CSVs or uses food_waste.db. Replace or extend as needed.

import streamlit as st
import pandas as pd
import sqlite3
import glob
import os
from datetime import datetime
import altair as alt

st.set_page_config(page_title="Food Waste Management", layout="wide")

DB_PATH = "food_waste.db"

# ------------------ Utilities ------------------
def list_csvs():
    return sorted(glob.glob("*.csv"))

def create_db_from_csvs(db_path=DB_PATH):
    """Create or update DB from CSVs found in repo root."""
    csvs = list_csvs()
    if not csvs:
        return False, "No CSV files found in repo root."
    con = sqlite3.connect(db_path)
    loaded = []
    for f in csvs:
        name = f.lower()
        if "food_list" in name:
            tbl = "food_listings"
        elif "provider" in name:
            tbl = "providers"
        elif "receiver" in name:
            tbl = "receivers"
        elif "claim" in name:
            tbl = "claims"
        else:
            tbl = os.path.splitext(f)[0]
        try:
            df = pd.read_csv(f)
            df.to_sql(tbl, con, if_exists="replace", index=False)
            loaded.append((f, tbl, len(df)))
        except Exception as e:
            con.close()
            return False, f"Failed to load {f}: {e}"
    con.commit()
    con.close()
    return True, loaded

def inspect_db(db_path=DB_PATH):
    if not os.path.exists(db_path):
        return []
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    con.close()
    return tables

def run_query(q, params=()):
    con = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(q, con, params=params)
    finally:
        con.close()
    return df

def run_exec(q, params=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(q, params)
    con.commit()
    con.close()

# ------------------ Startup: ensure DB/tables ------------------
def ensure_data():
    tables = inspect_db()
    required = {"providers","receivers","food_listings","claims"}
    if required.issubset(set(tables)):
        return True, "All required tables present."
    # if CSVs exist, build db from CSVs
    csvs = list_csvs()
    if csvs:
        ok, info = create_db_from_csvs()
        if ok:
            return True, f"DB created from CSVs: {info}"
        else:
            return False, f"Failed to create DB from CSVs: {info}"
    # no CSVs and DB missing required tables
    return False, f"Missing required tables {required - set(tables)}. Upload CSVs or a proper food_waste.db."

ok, msg = ensure_data()
if not ok:
    st.error("Data not ready: " + str(msg))
    st.info("Place CSV files (providers/receivers/food_listings/claims) or upload a food_waste.db in the repo root, then refresh the app.")
    st.stop()
else:
    st.success("Data ready: " + str(msg))

# ------------------ App UI ------------------
st.title("Food Waste Management System")

st.sidebar.header("Actions")
action = st.sidebar.selectbox("Choose action", [
    "Dashboard / Filters",
    "Show Tables",
    "Add Food Listing",
    "Make Claim",
    "Update Claim Status",
    "Run SQL Queries (15+)"
])

# ---- Dashboard / Filters (sidebar filters, no default selections) ----
if action == "Dashboard / Filters":
    st.header("Explore food listings")

    # load data
    try:
        df_listings = run_query("SELECT * FROM food_listings")
    except Exception as e:
        st.error("Failed to read food_listings: " + str(e))
        st.stop()
    df_providers = run_query("SELECT * FROM providers")
    df_receivers = run_query("SELECT * FROM receivers")
    df_claims = run_query("SELECT * FROM claims")

    # normalize column names
    df_listings.columns = [c.strip() for c in df_listings.columns]

  # ---------------- prepare options for filters (safe types) ----------------
# ensure columns exist and convert to plain python types to avoid Altair errors
cities = []
providers = []
food_types = []
meal_types = []

if 'Location' in df_listings.columns:
    # convert to str and drop nulls
    cities = sorted(df_listings['Location'].dropna().astype(str).unique())

if 'Name' in df_providers.columns:
    providers = sorted(df_providers['Name'].dropna().astype(str).unique())

if 'Food_Type' in df_listings.columns:
    food_types = sorted(df_listings['Food_Type'].dropna().astype(str).unique())

if 'Meal_Type' in df_listings.columns:
    meal_types = sorted(df_listings['Meal_Type'].dropna().astype(str).unique())

# ---------------- Sidebar filters (no defaults) ----------------
st.sidebar.header("Filters")
st.sidebar.write("Leave filters empty to show all results.")
city = st.sidebar.multiselect("City", options=cities)                # no default selection
provider_sel = st.sidebar.multiselect("Provider", options=providers) # no default selection
food_type_sel = st.sidebar.multiselect("Food Type", options=food_types)
meal_sel = st.sidebar.multiselect("Meal Type", options=meal_types)
min_qty = st.sidebar.number_input("Minimum Quantity", value=0, step=1, min_value=0)

# ---------------- Apply filters locally ----------------
df_filtered = df_listings.copy()
if city:
    df_filtered = df_filtered[df_filtered['Location'].astype(str).isin(city)]
if provider_sel:
    if 'Provider_ID' in df_listings.columns and 'Provider_ID' in df_providers.columns:
        pids = df_providers[df_providers['Name'].astype(str).isin(provider_sel)]['Provider_ID'].tolist()
        df_filtered = df_filtered[df_filtered['Provider_ID'].isin(pids)]
    else:
        if 'Provider_Name' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Provider_Name'].astype(str).isin(provider_sel)]
if food_type_sel:
    df_filtered = df_filtered[df_filtered['Food_Type'].astype(str).isin(food_type_sel)]
if meal_sel:
    df_filtered = df_filtered[df_filtered['Meal_Type'].astype(str).isin(meal_sel)]
if 'Quantity' in df_filtered.columns:
    try:
        df_filtered = df_filtered[df_filtered['Quantity'].fillna(0).astype(float) >= float(min_qty)]
    except Exception:
        pass

# ---------------- Right-side quick stats + safe Altair chart ----------------
left, right = st.columns([2,1])
with left:
    st.write(f"### {len(df_filtered)} matching listings")
    st.dataframe(df_filtered)

with right:
    st.write("### Quick stats")
    total_qty = df_listings['Quantity'].dropna().astype(float).sum() if 'Quantity' in df_listings.columns else 0
    st.metric("Total Quantity (all listings)", int(total_qty))
    st.metric("Total Providers", len(df_providers))
    st.metric("Total Receivers", len(df_receivers))

    # build a safe city chart (convert types, limit top N)
    if 'Location' in df_listings.columns:
        city_counts = (
            df_listings['Location']
            .astype(str)
            .value_counts()
            .reset_index()
            .rename(columns={'index': 'City', 'Location': 'Listings'})
        )
        if not city_counts.empty:
            city_counts['City'] = city_counts['City'].astype(str)
            city_counts['Listings'] = city_counts['Listings'].fillna(0).astype(int)
            # limit to top N to avoid extremely large charts
            TOP_N = 40
            city_counts = city_counts.nlargest(TOP_N, 'Listings')

            chart = (
                alt.Chart(city_counts)
                .mark_bar()
                .encode(
                    x=alt.X('City:N', sort='-y', title='City'),
                    y=alt.Y('Listings:Q', title='Listings'),
                    tooltip=[alt.Tooltip('City:N'), alt.Tooltip('Listings:Q')]
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)


# Show Tables
elif action == "Show Tables":
    st.header("Database tables")
    for t in ["providers","receivers","food_listings","claims"]:
        st.write(f"### {t}")
        try:
            df = run_query(f"SELECT * FROM {t} LIMIT 200")
            st.dataframe(df)
        except Exception as e:
            st.error(f"Error reading table {t}: {e}")

# Add Food Listing
elif action == "Add Food Listing":
    st.header("Add a new Food Listing")
    with st.form("add_listing"):
        provider_id = st.text_input("Provider ID (existing provider) - integer")
        food_name = st.text_input("Food name")
        qty = st.number_input("Quantity", value=1, min_value=0, step=1)
        expiry = st.date_input("Expiry date (optional)")
        location = st.text_input("Location / City")
        food_type = st.selectbox("Food Type", options=["Vegetarian","Non-Vegetarian","Vegan","Other"])
        meal_type = st.selectbox("Meal Type", options=["Breakfast","Lunch","Dinner","Snacks","Other"])
        submitted = st.form_submit_button("Add Listing")
    if submitted:
        try:
            run_exec("""
            INSERT INTO food_listings (Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type)
            VALUES (?,?,?,?,?,?,?,?)
            """, (food_name, qty, expiry.strftime("%Y-%m-%d") if expiry else None, int(provider_id) if provider_id else None, None, location, food_type, meal_type))
            st.success("Listing added successfully.")
        except Exception as e:
            st.error(f"Failed to add listing: {e}")

# Make Claim
elif action == "Make Claim":
    st.header("Claim available food")
    df_listings = run_query("SELECT * FROM food_listings")
    if df_listings.empty:
        st.info("No listings available.")
    else:
        pick = st.selectbox("Pick Food_ID", df_listings['Food_ID'].tolist())
        receiver_id = st.text_input("Receiver ID (existing) - integer")
        if st.button("Submit Claim"):
            try:
                ts = datetime.now().isoformat()
                run_exec("INSERT INTO claims (Food_ID, Receiver_ID, Status, Timestamp) VALUES (?, ?, ?, ?)",
                         (int(pick), int(receiver_id), "Pending", ts))
                st.success("Claim submitted as Pending.")
            except Exception as e:
                st.error(f"Error submitting claim: {e}")

# Update Claim Status
elif action == "Update Claim Status":
    st.header("Update a claim status (Pending -> Completed/Cancelled)")
    df_claims = run_query("SELECT * FROM claims")
    if df_claims.empty:
        st.info("No claims in database.")
    else:
        claim_id = st.selectbox("Claim_ID", df_claims['Claim_ID'].tolist())
        new_status = st.selectbox("New status", ["Completed","Cancelled","Pending"])
        if st.button("Update"):
            try:
                run_exec("UPDATE claims SET Status = ? WHERE Claim_ID = ?", (new_status, claim_id))
                st.success("Claim updated.")
            except Exception as e:
                st.error(f"Failed to update: {e}")

# Run SQL Queries (15+)
elif action == "Run SQL Queries (15+)":
    st.header("Predefined SQL queries and insights")
    queries = {
        "1. Providers & receivers per city": """
            SELECT p.City AS City,
                   COUNT(DISTINCT p.Provider_ID) AS Providers,
                   (SELECT COUNT(DISTINCT r.Receiver_ID) FROM receivers r WHERE r.City = p.City) AS Receivers
            FROM providers p GROUP BY p.City ORDER BY Providers DESC
        """,
        "2. Provider types contributing most food (by count listings)": """
            SELECT Provider_Type, COUNT(*) AS Listings FROM food_listings GROUP BY Provider_Type ORDER BY Listings DESC
        """,
        "3. Provider contacts in city (example: choose city)": "SELECT Name, Contact FROM providers WHERE City = ?",
        "4. Receivers with most claims": """
            SELECT r.Name, COUNT(*) AS Claims
            FROM claims c JOIN receivers r ON c.Receiver_ID = r.Receiver_ID
            GROUP BY r.Name ORDER BY Claims DESC
        """,
        "5. Total quantity available": "SELECT SUM(CAST(Quantity AS INTEGER)) AS TotalQuantity FROM food_listings",
        "6. City with highest listings": """
            SELECT Location AS City, COUNT(*) AS Listings FROM food_listings GROUP BY Location ORDER BY Listings DESC LIMIT 10
        """,
        "7. Most common food types": "SELECT Food_Type, COUNT(*) AS Count FROM food_listings GROUP BY Food_Type ORDER BY Count DESC",
        "8. Claims per food item": "SELECT f.Food_ID, f.Food_Name, COUNT(c.Claim_ID) AS ClaimCount FROM food_listings f LEFT JOIN claims c ON f.Food_ID = c.Food_ID GROUP BY f.Food_ID ORDER BY ClaimCount DESC",
        "9. Provider with highest successful claims": """
            SELECT p.Name, COUNT(*) AS SuccessfulClaims
            FROM claims c JOIN food_listings f ON c.Food_ID = f.Food_ID JOIN providers p ON f.Provider_ID = p.Provider_ID
            WHERE c.Status = 'Completed'
            GROUP BY p.Name ORDER BY SuccessfulClaims DESC
        """,
        "10. Claims status percentage": """
            SELECT Status, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM claims), 2) AS Percentage FROM claims GROUP BY Status
        """,
        "11. Avg quantity claimed per receiver": """
            SELECT r.Name, AVG(cast(f.Quantity as float)) as AvgQuantity
            FROM claims c JOIN receivers r ON c.Receiver_ID = r.Receiver_ID JOIN food_listings f ON c.Food_ID = f.Food_ID
            GROUP BY r.Name ORDER BY AvgQuantity DESC
        """,
        "12. Most claimed meal type": "SELECT Meal_Type, COUNT(*) AS Count FROM food_listings f JOIN claims c ON f.Food_ID = c.Food_ID GROUP BY Meal_Type ORDER BY Count DESC",
        "13. Total quantity donated by each provider": "SELECT p.Name, SUM(CAST(f.Quantity AS INTEGER)) AS TotalDonated FROM food_listings f JOIN providers p ON f.Provider_ID = p.Provider_ID GROUP BY p.Name ORDER BY TotalDonated DESC",
        "14. Listings expiring soon (next 7 days)": "SELECT * FROM food_listings WHERE date(Expiry_Date) <= date('now','+7 days')",
        "15. Top 10 food items by quantity": "SELECT Food_Name, SUM(CAST(Quantity AS INTEGER)) AS TotalQty FROM food_listings GROUP BY Food_Name ORDER BY TotalQty DESC LIMIT 10"
    }

    query_choice = st.selectbox("Choose query", list(queries.keys()))
    chosen_q = queries[query_choice]
    if "choose city" in chosen_q.lower():
        city_input = st.text_input("Enter city for provider contact list")
        if st.button("Run query"):
            df = run_query(queries["3. Provider contacts in city (example: choose city)"], params=(city_input,))
            st.write(df)
    else:
        if st.button("Run selected query"):
            df = run_query(chosen_q)
            st.write(df)
            if not df.empty:
                numeric_cols = df.select_dtypes(include=['int','float']).columns.tolist()
                if numeric_cols:
                    col = numeric_cols[0]
                    chart = alt.Chart(df).mark_bar().encode(x=df.columns[0]+":N", y=col+':Q', tooltip=list(df.columns)).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)

st.write("---")
st.caption("App: providers, receivers, food listings, claims; filters, CRUD, SQL analysis.")
