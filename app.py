import os
from functools import wraps
from flask import Flask, render_template, request, redirect, session, flash
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3 

app = Flask(__name__)



    SESSION_PERMANENT=False,
    SESSION_TYPE="filesystem",
    SECRET_KEY=os.urandom(24)
)
Session(app)


def query_db(query, args=(), one=False):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "finance.db")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, args)
        if "INSERT" in query or "UPDATE" in query or "DELETE" in query:
            conn.commit()
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
@login_required
def index ():
    user_id = session["user_id"]


    expenses = query_db("SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC", [user_id])
    res = query_db("SELECT SUM(amount) as total FROM expenses WHERE user_id = ?", [user_id], one=True)

    return render_template("index.html", expenses=expenses, total=res['total'] or 0)

@app.route("/add", methods=["POST"])
@login_required
def add():
    amount = request.form.get("amount")
    category = request.form.get("category")

    if not amount or not category:
        flash("Fill out all fields!")
        return redirect("/")

    query_db("INSERT INTO expenses (user_id, amount, category) VALUES (?, ?, ?)",
             [session["user_id"], amount, category])

    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Missing username/password", 400

        hash = generate_password_hash(password)
        try:
            query_db("INSERT INTO users (username, hash) VALUES (?, ?)", [username, hash])
            return redirect("/login")
        except sqlite3.IntegrityError:
            return "That username is already gone.", 400

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)

        if user and check_password_hash(user["hash"], password):
            session["user_id"] = user["id"]
            return redirect("/")

        flash("Invalid username and/or password")
        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
