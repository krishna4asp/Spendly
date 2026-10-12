import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
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

    return redirect(url_for("landing"))


@app.route("/login")
def login():
    return render_template("login.html")


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
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
