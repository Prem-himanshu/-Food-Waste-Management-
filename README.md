# 🍽️ Food Waste Management System  
A Streamlit web application designed to reduce food wastage by connecting **food providers** (restaurants, events, NGOs) with **receivers** (orphanages, shelters, communities).  
Built with **Python, Streamlit, SQLite, and Pandas**, this system supports food listing, claiming, tracking, and data analytics.

---

## 🚀 Features

### 🔹 1. Provider & Receiver Management  
- Manage providers and receivers  
- Store contacts, locations, and food types  
- View all records in tabular format  

### 🔹 2. Food Listings  
- Add food listings with details:
  - Food name  
  - Quantity  
  - Expiry date  
  - Location  
  - Provider  

- Filter listings by:
  - City  
  - Meal type  
  - Food type  
  - Provider  
  - Quantity  

### 🔹 3. Claim Management  
- Make claims on available food  
- Track status: **Pending → Completed / Cancelled**  
- View all claims in dashboard  

### 🔹 4. Dashboard & Analytics  
- Total quantity available  
- Top contributing providers  
- Claims per city  
- 15+ ready-made SQL insights (e.g., most claimed food, most active receivers)

### 🔹 5. Database Auto-Builder  
- If no `food_waste.db` exists, the app automatically reads CSVs and rebuilds the database.

---

## 🛠️ Tech Stack
- **Python**  
- **Streamlit**  
- **SQLite**  
- **Pandas**  
- **Altair (charts)**  

---

## 📦 Project Structure

```
├── streamlit_app.py
├── food_waste.db (optional)
├── providers_data.csv
├── receivers_data.csv
├── food_listings_data.csv
├── claims_data.csv
├── requirements.txt
```

---

## 🧪 How to Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/Prem-himanshu/-Food-Waste-Management-.git
cd -Food-Waste-Management-
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit app
```bash
streamlit run streamlit_app.py
```

---

## 🌐 Live Demo  
Hosted on Streamlit Cloud:  
👉 *Add your Streamlit URL here once deployed*

---

## 📊 Future Enhancements
- Login authentication system  
- Email/SMS notification for food claims  
- Maps integration for pickup routes  
- Mobile-friendly UI  
- Admin dashboard  

---

## 🤝 Contribution
Feel free to fork the project, open issues, or submit PRs.

---

## 🙌 Author  
**Himanshu Kumar**  
Food Waste Reduction | Python Developer | Data & ML Enthusiast  
LinkedIn: [Your Profile Link Here]  
GitHub: https://github.com/Prem-himanshu  
