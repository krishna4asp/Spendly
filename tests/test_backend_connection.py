import pytest
from app import app as flask_app
from database.db import get_db
from database.queries import get_summary_stats, get_recent_transactions, get_category_breakdown
from werkzeug.security import generate_password_hash

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASS  = "demo123"


@pytest.fixture()
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def _get_user_id(email):
    db = get_db()
    try:
        row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return row["id"] if row else None
    finally:
        db.close()


@pytest.fixture()
def empty_user():
    """Insert a user with no expenses; delete after the test."""
    email = "no-expenses@test.example"
    db = get_db()
    try:
        db.execute(
            "INSERT OR IGNORE INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Empty User", email, generate_password_hash("password")),
        )
        db.commit()
        user_id = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]
    finally:
        db.close()
    yield user_id
    db = get_db()
    try:
        db.execute("DELETE FROM users WHERE email = ?", (email,))
        db.commit()
    finally:
        db.close()


# ── get_summary_stats ───────────────────────────────────────────────────────

def test_summary_stats_with_expenses():
    stats = get_summary_stats(_get_user_id(DEMO_EMAIL))
    assert stats["total_spent"] == "₹9,030.00"
    assert stats["tx_count"] == 8
    assert stats["top_category"] == "Bills"

def test_summary_stats_no_expenses(empty_user):
    stats = get_summary_stats(empty_user)
    assert stats["total_spent"] == "₹0.00"
    assert stats["tx_count"] == 0
    assert stats["top_category"] == "—"


# ── get_recent_transactions ─────────────────────────────────────────────────

def test_recent_transactions_with_expenses():
    txns = get_recent_transactions(_get_user_id(DEMO_EMAIL))
    assert len(txns) == 8
    assert txns[0]["date"] == "2026-10-11"   # newest first
    assert txns[-1]["date"] == "2026-10-01"  # oldest last
    for tx in txns:
        assert set(tx.keys()) == {"date", "description", "category", "amount"}
        assert tx["amount"].startswith("₹")

def test_recent_transactions_no_expenses(empty_user):
    assert get_recent_transactions(empty_user) == []

def test_recent_transactions_limit():
    txns = get_recent_transactions(_get_user_id(DEMO_EMAIL), limit=3)
    assert len(txns) == 3


# ── get_category_breakdown ──────────────────────────────────────────────────

def test_category_breakdown_with_expenses():
    cats = get_category_breakdown(_get_user_id(DEMO_EMAIL))
    assert len(cats) == 7                       # 7 distinct categories in seed data
    assert cats[0]["name"] == "Bills"           # highest spend first
    assert cats[0]["amount"] == "₹3,200.00"
    assert sum(c["pct"] for c in cats) == 100   # percentages must sum to 100
    for c in cats:
        assert isinstance(c["pct"], int)

def test_category_breakdown_no_expenses(empty_user):
    assert get_category_breakdown(empty_user) == []


# ── GET /profile route ──────────────────────────────────────────────────────

def test_profile_unauthenticated_redirects(client):
    r = client.get("/profile")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]

def test_profile_authenticated_200(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASS})
    assert client.get("/profile").status_code == 200

def test_profile_shows_real_data(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASS})
    html = client.get("/profile").data.decode()
    assert "Demo User" in html
    assert DEMO_EMAIL in html
    assert "₹9,030.00" in html
    assert "Bills" in html
    assert "₹" in html

def test_profile_new_user_no_crash(client):
    client.post("/register", data={
        "name": "Test Zero",
        "email": "testzero@example.com",
        "password": "password123",
        "confirm_password": "password123",
    })
    r = client.get("/profile")
    assert r.status_code == 200
    html = r.data.decode()
    assert "₹0.00" in html
    # Clean up
    db = get_db()
    try:
        db.execute("DELETE FROM users WHERE email = ?", ("testzero@example.com",))
        db.commit()
    finally:
        db.close()
