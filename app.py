from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import re

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("expenseTracker.db")
    cur = conn.cursor()
    
    #users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    #expenses table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    #budgets table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            year INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, category, month, year)
        )
    """)
    #alerts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            threshold_percentage INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, category)
        )
    """)

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect("expenseTracker.db")
    conn.row_factory = sqlite3.Row
    return conn

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_budget_alerts(user_id, category, month, year):
    conn = get_db()
    c = conn.cursor()

    budget = c.execute("""
        SELECT amount FROM budgets
        WHERE user_id=? AND category=? AND month=? AND year=?
    """, (user_id, category, month, year)).fetchone()

    if not budget:
        conn.close()
        return None

    budget_amount = budget["amount"]
    
    if budget_amount <= 0:
        conn.close()
        return None

    spend = c.execute("""
        SELECT COALESCE(SUM(amount), 0) as total
        FROM expenses
        WHERE user_id=? AND category=? AND strftime('%m',date)=? AND strftime('%Y',date)=?
    """, (user_id, category, month, str(year))).fetchone()

    spent_total = spend["total"]

    alert_row = c.execute("""
        SELECT threshold_percentage FROM alerts
        WHERE user_id=? AND category=?
    """, (user_id, category)).fetchone()

    conn.close()

    alerts = []

    try:
        percent = (spent_total / budget_amount) * 100
    except:
        percent = 0

    if spent_total > budget_amount:
        over_amount = spent_total - budget_amount
        alerts.append({
            "type": "danger",
            "message": f"⚠️ Budget exceeded in {category}! You've spent ₹{spent_total:.2f} (₹{over_amount:.2f} over your ₹{budget_amount:.2f} budget)"
        })
    elif alert_row and percent >= alert_row["threshold_percentage"]:
        remaining_percent = 100 - percent
        remaining_amount = budget_amount - spent_total
        alerts.append({
            "type": "warning",
            "message": f"⚡ Warning: Only {remaining_percent:.1f}% (₹{remaining_amount:.2f}) of your {category} budget remaining"
        })

    return alerts if alerts else None


@app.route("/")
def index():
    return render_template("index.html")


# users
@app.route("/api/users", methods=["GET", "POST"])
def users():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        data = request.json
        if not data.get("name") or not data.get("email"):
            conn.close()
            return jsonify({"success": False, "error": "Name and email are required"}), 400
        if not validate_email(data["email"]):
            conn.close()
            return jsonify({"success": False, "error": "Invalid email format"}), 400
        try:
            c.execute("INSERT INTO users (name,email) VALUES (?,?)",
                      (data["name"].strip(), data["email"].strip().lower()))
            conn.commit()
            uid = c.lastrowid
            conn.close()
            return jsonify({"success": True, "user_id": uid}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"success": False, "error": "This email is already registered"}), 400
    else:
        all_users = c.execute("SELECT * FROM users ORDER BY name").fetchall()
        conn.close()
        return jsonify([dict(u) for u in all_users])

# expenses
@app.route("/api/expenses", methods=["GET", "POST"])
def expenses():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        data = request.json
        try:
            amount = float(data["amount"])
            if amount <= 0:
                conn.close()
                return jsonify({"success": False, "error": "Amount must be greater than zero"}), 400
            if amount > 10000000:  # 1 crore limit
                conn.close()
                return jsonify({"success": False, "error": "Amount seems too large. Please check."}), 400
        except (ValueError, KeyError):
            conn.close()
            return jsonify({"success": False, "error": "Invalid amount"}), 400
        try:
            expense_date = datetime.strptime(data["date"], "%Y-%m-%d")
            if expense_date > datetime.now():
                conn.close()
                return jsonify({"success": False, "error": "Cannot add expenses for future dates"}), 400
        except ValueError:
            conn.close()
            return jsonify({"success": False, "error": "Invalid date format"}), 400

        c.execute("""
            INSERT INTO expenses (user_id,amount,category,description,date)
            VALUES (?,?,?,?,?)
        """, (data["user_id"], amount, data["category"],
              data.get("description", "").strip(), data["date"]))

        conn.commit()
        exp_id = c.lastrowid

        alerts = check_budget_alerts(data["user_id"], data["category"],
                                     expense_date.strftime("%m"), expense_date.year)

        conn.close()
        return jsonify({"success": True, "expense_id": exp_id, "alerts": alerts}), 201

    else:
        user_id = request.args.get("user_id")
        rows = c.execute("""
            SELECT e.*, u.name as user_name
            FROM expenses e JOIN users u ON e.user_id=u.id
            WHERE e.user_id=?
            ORDER BY e.date DESC
        """, (user_id,)).fetchall()

        conn.close()
        return jsonify([dict(r) for r in rows])

# budgets
@app.route("/api/budgets", methods=["GET", "POST", "PUT"])
def budgets():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        data = request.json
        try:
            amount = float(data["amount"])
            if amount <= 0:
                conn.close()
                return jsonify({"success": False, "error": "Budget must be greater than zero"}), 400
            if amount > 10000000:
                conn.close()
                return jsonify({"success": False, "error": "Budget amount seems too large"}), 400
        except (ValueError, KeyError):
            conn.close()
            return jsonify({"success": False, "error": "Invalid budget amount"}), 400
        
        try:
            c.execute("""
                INSERT INTO budgets (user_id,category,amount,month,year)
                VALUES (?,?,?,?,?)
            """, (data["user_id"], data["category"], amount,
                  data["month"], data["year"]))

            conn.commit()
            bid = c.lastrowid
            conn.close()
            return jsonify({"success": True, "budget_id": bid}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"success": False, "error": "Budget already exists for this category and month"}), 400

    elif request.method == "PUT":
        data = request.json
        try:
            amount = float(data["amount"])
            if amount <= 0:
                conn.close()
                return jsonify({"success": False, "error": "Budget must be greater than zero"}), 400
        except (ValueError, KeyError):
            conn.close()
            return jsonify({"success": False, "error": "Invalid budget amount"}), 400
        
        c.execute("""
            UPDATE budgets SET amount=?
            WHERE user_id=? AND category=? AND month=? AND year=?
        """, (amount, data["user_id"], data["category"],
              data["month"], data["year"]))

        conn.commit()
        conn.close()
        return jsonify({"success": True})

    else:
        user_id = request.args.get("user_id")
        month = request.args.get("month")
        year = request.args.get("year")

        q = "SELECT * FROM budgets WHERE user_id=?"
        params = [user_id]

        if month:
            q += " AND month=?"
            params.append(month)
        if year:
            q += " AND year=?"
            params.append(year)

        q += " ORDER BY year DESC, month DESC, category"

        rows = c.execute(q, params).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])


# alerts
@app.route("/api/alerts", methods=["GET", "POST", "DELETE"])
def alerts():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        data = request.json
        try:
            threshold = int(data["threshold_percentage"])
            if threshold < 1 or threshold > 100:
                conn.close()
                return jsonify({"success": False, "error": "Threshold must be between 1 and 100"}), 400
        except (ValueError, KeyError):
            conn.close()
            return jsonify({"success": False, "error": "Invalid threshold value"}), 400
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO alerts (user_id,category,threshold_percentage)
                VALUES (?,?,?)
            """, (data["user_id"], data["category"], threshold))

            conn.commit()
            aid = c.lastrowid
            conn.close()
            return jsonify({"success": True, "alert_id": aid}), 201
        except Exception as e:
            conn.close()
            return jsonify({"success": False, "error": str(e)}), 400

    elif request.method == "DELETE":
        uid = request.args.get("user_id")
        cat = request.args.get("category")
        c.execute("DELETE FROM alerts WHERE user_id=? AND category=?", (uid, cat))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    else:
        uid = request.args.get("user_id")
        rows = c.execute("SELECT * FROM alerts WHERE user_id=? ORDER BY category",
                         (uid,)).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

@app.route("/api/reports/monthly", methods=["GET"])
def monthly_report():
    user_id = request.args.get("user_id")
    month = request.args.get("month")
    year = request.args.get("year")

    conn = get_db()
    c = conn.cursor()

    total = c.execute("""
        SELECT COALESCE(SUM(amount),0) as total
        FROM expenses
        WHERE user_id=? AND strftime('%m',date)=? AND strftime('%Y',date)=?
    """, (user_id, month, year)).fetchone()

    cats = c.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id=? AND strftime('%m',date)=? AND strftime('%Y',date)=?
        GROUP BY category ORDER BY total DESC
    """, (user_id, month, year)).fetchall()

    bud = c.execute("""
        SELECT category, amount FROM budgets
        WHERE user_id=? AND month=? AND year=?
    """, (user_id, month, year)).fetchall()

    conn.close()

    comparison = []
    for b in bud:
        spent = next((x["total"] for x in cats if x["category"] == b["category"]), 0)
        remaining = b["amount"] - spent
        percentage = (spent / b["amount"] * 100) if b["amount"] > 0 else 0
        
        comparison.append({
            "category": b["category"],
            "budget": b["amount"],
            "spent": spent,
            "remaining": remaining,
            "percentage": percentage,
            "is_over": spent > b["amount"]
        })

    return jsonify({
        "total_spending": total["total"],
        "category_spending": [dict(x) for x in cats],
        "budget_comparison": comparison
    })


if __name__ == "__main__":
    print("🚀 Starting FinCtrl...")
    print("📊 Setting up database...")
    init_db()
    print("✅ Database ready!")
    print("🌐 Server starting on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)