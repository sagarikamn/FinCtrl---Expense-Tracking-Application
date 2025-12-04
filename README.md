
<h1 align="center">💰 FinCtrl – Personal Expense Tracker</h1>
<p align="center">Track daily expenses • Set budgets • Get alerts • Generate reports • Stay financially in control</p>

---

#  1. Overview

**FinCtrl** is a Flask + SQLite based personal finance tracker that helps users efficiently record expenses, set monthly budgets, and monitor spending.

### Key Features
- ✔ Multi-user support  
- ✔ Daily expense tracking  
- ✔ Category-wise monthly budgets  
- ✔ Custom alert thresholds  
- ✔ Automatic overspending warnings  
- ✔ Monthly spending reports  
- ✔ Clean UI (HTML + CSS + JavaScript)

Backend logic is implemented in **app.py**, while the UI resides in **index.html** and **style.css**.

---

#  2. Project Structure

```

FinCtrl/
│── app.py                 # Flask backend & REST APIs
│── templates/index.html   # Web UI
│── static/style.css       # Styling
│── Dockerfile             # Docker build file
│── requirements.txt       # Python dependencies
README.md                  # Documentation

````

---

# 3. Clone the Repository

```sh
git clone https://github.com/sagarikamn/FinCtrl---Expense-Tracking-Application.git
cd FinCtrl---Expense-Tracking-Application
````

---

#  4. Steps to Run the Application

### Step 1 — Open Project

Open the folder in **Visual Studio Code**.

### Step 2 — Install Dependencies

```sh
pip install -r requirements.txt
```

###  Step 3 — Run the Application

```sh
python app.py
```

### Step 4 — Open in Browser

Click the link shown in terminal:

```
http://localhost:5000/
```

### Step 5 — Auto Database Setup

The app automatically creates:

* SQLite database
* Tables: **users**, **expenses**, **budgets**, **alerts**

### Step 6 — Start Using the Application

You can now:

* Create users
* Add expenses
* Set monthly budgets
* Configure alerts
* Generate monthly reports

---

# 5. Test Steps (For Evaluation)

### ✔ Test 1 — Create User

* Click **+ New User**
* Enter name & email
* **Expected:** User appears in dropdown

### ✔ Test 2 — Add Expense

* Select user → Enter amount, category, date
* **Expected:** Expense appears under "Recent Expenses"

### ✔ Test 3 — Set Budget

* Go to **Budgets** tab
* Select category, amount, month
* **Expected:** Budget added to list

### ✔ Test 4 — Configure Alert

* Enter category + % threshold
* **Expected:** Alert appears under "Active Alerts"

### ✔ Test 5 — Trigger Budget Alert

* Add expenses exceeding threshold
* **Expected:** Warning/alert message appears

### ✔ Test 6 — Generate Report

* Choose month → **Generate Report**
* **Expected:** Spending summary + comparison table

---

# 6. Docker Build & Run Instructions

### Build Docker Image

```sh
docker build -t finctrl-app .
```

### Run Container

```sh
docker run -d -p 5000:5000 --name finctrl finctrl-app
```

### Stop Container

```sh
docker stop finctrl
```

### Remove Container

```sh
docker rm finctrl
```

---

# 7. Edge Case Handling & Validation

The application includes full validation for real-world usage:

* **Invalid email formats** are rejected using regex.
* **Duplicate emails** are blocked via database UNIQUE constraints.
* **Future dates** for expenses are not allowed.
* **Zero or negative amount values** are rejected.
* **Amounts above ₹1,00,00,000** are blocked to avoid accidental entries.
* **Budgets must be positive**, otherwise rejected.
* **Alert thresholds must be 1–100%**, enforced through validation.
* **Duplicate budgets (same category & month)** are prevented.
* **Overspending automatically triggers alert notifications**.
* **Missing required fields** cause the request to be rejected.
* **Deleting a non-existing alert** does not break the system.
* **Empty states** show user-friendly messages (no budgets, no expenses, etc.).

---

