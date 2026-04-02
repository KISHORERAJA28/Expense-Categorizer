import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, session, flash
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

app = Flask(__name__)


)
Session(app)

def db_run(query, args=(), one=False):
    db_path = os.path.join(os.path.dirname(__file__), "finance.db")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, args)
        if any(x in query.upper() for x in ["INSERT", "UPDATE", "DELETE"]):
            conn.commit()
        res = cur.fetchall()
        return (res[0] if res else None) if one else res

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

@app.route("/")
@login_required
def index():
    uid = session["user_id"]
    this_month = datetime.now().strftime('%Y-%m')

    user = db_run("SELECT budget FROM users WHERE id = ?", [uid], one=True)
    salary = user['budget'] or 0

    all_expenses = db_run("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC", [uid])
    monthly_sum = db_run("SELECT SUM(amount) as total FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ?",
                         [uid, this_month], one=True)

    total_spent = monthly_sum['total'] or 0
    surplus = salary - total_spent

    strategy = None
    if surplus >= 20000:
        strategy = {"amt": "20,000", "focus": "Multi-cap approach with Step-up features", "corpus": "₹44.8 Lakhs"}
    elif surplus >= 15000:
        strategy = {"amt": "15,000", "focus": "Goal-based (Education/Retirement) with ELSS for tax", "corpus": "₹33.6 Lakhs"}
    elif surplus >= 10000:
        strategy = {"amt": "10,000", "focus": "Diversified Portfolio (Equity + Debt/PPF)", "corpus": "₹22.4 Lakhs"}
    elif surplus >= 5000:
        strategy = {"amt": "5,000", "focus": "Small-Cap or Index Funds for long-term growth", "corpus": "₹11.2 Lakhs"}

    return render_template("index.html", expenses=all_expenses, spent=total_spent, salary=salary, surplus=surplus, strategy=strategy)

@app.route("/add", methods=["POST"])
@login_required
def add():
    amt, cat = request.form.get("amount"), request.form.get("category")
    if amt and cat:
        db_run("INSERT INTO expenses (user_id, amount, category) VALUES (?, ?, ?)", [session["user_id"], float(amt), cat])
    return redirect("/")

@app.route("/update_salary", methods=["POST"])
@login_required
def update_salary():
    salary = request.form.get("salary")
    if salary:
        db_run("UPDATE users SET budget = ? WHERE id = ?", [salary, session["user_id"]])
    return redirect("/")

@app.route("/clear", methods=["POST"])
@login_required
def clear():
    db_run("DELETE FROM expenses WHERE user_id = ?", [session["user_id"]])
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u, p = request.form.get("username"), request.form.get("password")
        try:
            db_run("INSERT INTO users (username, hash) VALUES (?, ?)", [u, generate_password_hash(p)])
            return redirect("/login")
        except: return "Username taken", 400
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db_run("SELECT * FROM users WHERE username = ?", [request.form.get("username")], one=True)
        if user and check_password_hash(user["hash"], request.form.get("password")):
            session["user_id"] = user["id"]
            return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
