import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Full name is required.")
    if not email:
        return render_template("register.html", error="Email address is required.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    confirm = request.form.get("confirm_password", "")
    if password != confirm:
        return render_template("register.html", error="Passwords do not match.")

    db = get_db()
    try:
        if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            return render_template("register.html", error="An account with that email already exists.")

        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        session["user_id"]   = user["id"]
        session["user_name"] = name
    finally:
        db.close()

    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("login.html")

    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    db = get_db()
    try:
        user = db.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        db.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        db = get_db()
        try:
            if not name:
                user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                return render_template("profile.html", user=user, error="Name cannot be empty.")
            db.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
            db.commit()
        finally:
            db.close()
        session["user_name"] = name
        return redirect(url_for("profile", updated="1"))

    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        db.close()

    success = "Profile updated successfully." if request.args.get("updated") else None

    stats = {
        "total_spent":  "₹8,830.00",
        "tx_count":     8,
        "top_category": "Bills",
    }

    transactions = [
        {"date": "2026-10-11", "description": "Miscellaneous",  "category": "Other",         "amount": "₹350.00"},
        {"date": "2026-10-10", "description": "Restaurant",     "category": "Food",          "amount": "₹480.00"},
        {"date": "2026-10-09", "description": "Clothes",        "category": "Shopping",      "amount": "₹2,100.00"},
        {"date": "2026-10-07", "description": "Movie + dinner", "category": "Entertainment", "amount": "₹1,200.00"},
        {"date": "2026-10-05", "description": "Pharmacy",       "category": "Health",        "amount": "₹600.00"},
    ]

    categories = [
        {"name": "Bills",         "amount": "₹3,200.00", "pct": 36},
        {"name": "Shopping",      "amount": "₹2,100.00", "pct": 24},
        {"name": "Food",          "amount": "₹1,330.00", "pct": 15},
        {"name": "Entertainment", "amount": "₹1,200.00", "pct": 14},
        {"name": "Health",        "amount": "₹600.00",   "pct": 7},
        {"name": "Other",         "amount": "₹400.00",   "pct": 4},
    ]

    return render_template("profile.html", user=user, success=success,
                           stats=stats, transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
