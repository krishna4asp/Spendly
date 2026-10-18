"""
tests/test_07-add-expenses.py

Tests for the "Add Expense" feature (Step 7).
Based on spec: .claude/specs/07-add-expenses.md

Covers:
  - Unit tests for insert_expense: happy path, description=None
  - GET /expenses/add: auth guard, 200, category <select>, form method POST
  - POST /expenses/add: auth guard, valid insert + redirect, validation errors
    (missing amount, amount=0, non-numeric amount, invalid category, invalid date),
    optional description stored as NULL
"""

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from app import app as flask_app

# ---------------------------------------------------------------------------
# Test user constants
# ---------------------------------------------------------------------------

TEST_EMAIL = "addexpense@example.com"
TEST_PASS  = "addexpensepass1"

VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


# ---------------------------------------------------------------------------
# Fixtures — mirror the pattern from test_date_filter_profile.py exactly
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """
    Redirect all database I/O to an isolated temp file, create the schema,
    and insert one test user.  The monkeypatch is automatically undone after
    each test so the real spendly.db is never touched.
    """
    from database.db import init_db, get_db

    db_path = str(tmp_path / "test_add_expense.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    # Create tables in the temp file
    init_db()

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Add Expense Tester", TEST_EMAIL, generate_password_hash(TEST_PASS)),
        )
        db.commit()

        user_id = db.execute(
            "SELECT id FROM users WHERE email = ?", (TEST_EMAIL,)
        ).fetchone()["id"]
    finally:
        db.close()

    yield user_id


@pytest.fixture()
def client(seeded_db):
    """Unauthenticated Flask test client backed by the isolated seeded DB."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture()
def auth_client(client):
    """Flask test client already logged in as the seeded test user."""
    client.post("/login", data={"email": TEST_EMAIL, "password": TEST_PASS})
    return client


# ---------------------------------------------------------------------------
# Unit tests for insert_expense
# ---------------------------------------------------------------------------

class TestInsertExpense:

    def test_insert_expense_valid_data_row_exists(self, seeded_db):
        """insert_expense with full valid args creates a retrievable row in the DB."""
        from database.queries import insert_expense
        from database.db import get_db

        user_id = seeded_db
        insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")

        db = get_db()
        try:
            row = db.execute(
                "SELECT * FROM expenses WHERE user_id = ? AND category = ? AND date = ?",
                (user_id, "Food", "2026-03-20"),
            ).fetchone()
        finally:
            db.close()

        assert row is not None, "insert_expense must create a row in the expenses table"
        assert float(row["amount"]) == 50.0, "amount must be stored as 50.0"
        assert row["category"] == "Food", "category must be stored as 'Food'"
        assert row["date"] == "2026-03-20", "date must be stored as '2026-03-20'"
        assert row["description"] == "Lunch", "description must be stored as 'Lunch'"

    def test_insert_expense_none_description_stored_as_null(self, seeded_db):
        """insert_expense with description=None stores NULL in the DB."""
        from database.queries import insert_expense
        from database.db import get_db

        user_id = seeded_db
        insert_expense(user_id, 75.0, "Transport", "2026-03-21", None)

        db = get_db()
        try:
            row = db.execute(
                "SELECT description FROM expenses WHERE user_id = ? AND category = ? AND date = ?",
                (user_id, "Transport", "2026-03-21"),
            ).fetchone()
        finally:
            db.close()

        assert row is not None, "Row must be inserted even when description is None"
        assert row["description"] is None, (
            "description must be stored as NULL when None is passed"
        )


# ---------------------------------------------------------------------------
# GET /expenses/add — auth guard
# ---------------------------------------------------------------------------

class TestGetAddExpenseAuthGuard:

    def test_unauthenticated_get_redirects_to_login(self, client):
        r = client.get("/expenses/add")
        assert r.status_code == 302, (
            "Unauthenticated GET /expenses/add must return 302"
        )
        assert "/login" in r.headers["Location"], (
            "Unauthenticated GET /expenses/add must redirect to /login"
        )


# ---------------------------------------------------------------------------
# GET /expenses/add — authenticated
# ---------------------------------------------------------------------------

class TestGetAddExpenseAuthenticated:

    def test_authenticated_get_returns_200(self, auth_client):
        r = auth_client.get("/expenses/add")
        assert r.status_code == 200, (
            "Authenticated GET /expenses/add must return 200"
        )

    def test_response_contains_category_select(self, auth_client):
        html = auth_client.get("/expenses/add").data.decode()
        assert "<select" in html, (
            "Response must contain a <select> element for category"
        )

    def test_response_contains_all_seven_category_options(self, auth_client):
        html = auth_client.get("/expenses/add").data.decode()
        for category in VALID_CATEGORIES:
            assert category in html, (
                f"Category option '{category}' must be present in the form"
            )

    def test_response_contains_exactly_seven_categories(self, auth_client):
        """All 7 fixed categories and no extras are required by the spec."""
        html = auth_client.get("/expenses/add").data.decode()
        # Each expected category must appear at least once
        found = [cat for cat in VALID_CATEGORIES if cat in html]
        assert len(found) == 7, (
            f"Expected exactly 7 category options, found matching: {found}"
        )

    def test_response_contains_form_with_post_method(self, auth_client):
        html = auth_client.get("/expenses/add").data.decode()
        assert "<form" in html, "Response must contain a <form> element"
        assert (
            'method="POST"' in html
            or 'method="post"' in html
        ), "Form must use POST method"


# ---------------------------------------------------------------------------
# POST /expenses/add — auth guard
# ---------------------------------------------------------------------------

class TestPostAddExpenseAuthGuard:

    def test_unauthenticated_post_redirects_to_login(self, client):
        r = client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert r.status_code == 302, (
            "Unauthenticated POST /expenses/add must return 302"
        )
        assert "/login" in r.headers["Location"], (
            "Unauthenticated POST /expenses/add must redirect to /login"
        )


# ---------------------------------------------------------------------------
# POST /expenses/add — authenticated, valid data
# ---------------------------------------------------------------------------

class TestPostAddExpenseValid:

    def test_valid_post_redirects_to_profile(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert r.status_code == 302, (
            "Valid POST /expenses/add must redirect (302)"
        )
        assert "/profile" in r.headers["Location"], (
            "Valid POST /expenses/add must redirect to /profile"
        )

    def test_valid_post_row_inserted_in_db(self, auth_client, seeded_db):
        from database.db import get_db

        auth_client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })

        db = get_db()
        try:
            row = db.execute(
                "SELECT * FROM expenses WHERE user_id = ? AND category = ? AND date = ?",
                (seeded_db, "Food", "2026-03-20"),
            ).fetchone()
        finally:
            db.close()

        assert row is not None, (
            "After valid POST /expenses/add, new expense row must exist in DB"
        )
        assert float(row["amount"]) == 50.0, "Stored amount must be 50.0"

    def test_valid_post_no_description_redirects_to_profile(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "30.0",
            "category": "Transport",
            "date": "2026-03-21",
            "description": "",
        })
        assert r.status_code == 302, (
            "POST /expenses/add with empty description must redirect (302)"
        )
        assert "/profile" in r.headers["Location"], (
            "POST /expenses/add with empty description must redirect to /profile"
        )

    def test_valid_post_no_description_row_has_null_description(self, auth_client, seeded_db):
        from database.db import get_db

        auth_client.post("/expenses/add", data={
            "amount": "30.0",
            "category": "Transport",
            "date": "2026-03-21",
            "description": "",
        })

        db = get_db()
        try:
            row = db.execute(
                "SELECT description FROM expenses WHERE user_id = ? AND category = ? AND date = ?",
                (seeded_db, "Transport", "2026-03-21"),
            ).fetchone()
        finally:
            db.close()

        assert row is not None, (
            "Row must be inserted when description is blank"
        )
        assert row["description"] is None, (
            "Blank description must be stored as NULL"
        )


# ---------------------------------------------------------------------------
# POST /expenses/add — authenticated, validation errors
# ---------------------------------------------------------------------------

class TestPostAddExpenseValidationErrors:

    def test_missing_amount_returns_200(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert r.status_code == 200, (
            "Missing amount must re-render form (200), not redirect"
        )

    def test_missing_amount_shows_error_message(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        html = r.data.decode()
        # The spec requires an error message to appear; the exact wording is
        # implementation-specific, but there must be some error indicator.
        assert (
            "error" in html.lower()
            or "invalid" in html.lower()
            or "required" in html.lower()
            or "amount" in html.lower()
        ), "Missing amount must produce a visible error message in the response"

    def test_zero_amount_returns_200(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert r.status_code == 200, (
            "amount=0 must re-render form (200), not redirect"
        )

    def test_zero_amount_shows_error_message(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        html = r.data.decode()
        assert (
            "error" in html.lower()
            or "invalid" in html.lower()
            or "greater" in html.lower()
            or "positive" in html.lower()
            or "amount" in html.lower()
        ), "amount=0 must produce a visible error message in the response"

    def test_non_numeric_amount_returns_200(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert r.status_code == 200, (
            "Non-numeric amount must re-render form (200), not redirect"
        )

    def test_non_numeric_amount_shows_error_message(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        html = r.data.decode()
        assert (
            "error" in html.lower()
            or "invalid" in html.lower()
            or "number" in html.lower()
            or "numeric" in html.lower()
            or "amount" in html.lower()
        ), "Non-numeric amount must produce a visible error message in the response"

    def test_invalid_category_returns_200(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "NotARealCategory",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert r.status_code == 200, (
            "Invalid category must re-render form (200), not redirect"
        )

    def test_invalid_category_shows_error_message(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "NotARealCategory",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        html = r.data.decode()
        assert (
            "error" in html.lower()
            or "invalid" in html.lower()
            or "category" in html.lower()
        ), "Invalid category must produce a visible error message in the response"

    def test_invalid_date_returns_200(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "not-a-date",
            "description": "Lunch",
        })
        assert r.status_code == 200, (
            "Invalid date must re-render form (200), not redirect"
        )

    def test_invalid_date_shows_error_message(self, auth_client):
        r = auth_client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "not-a-date",
            "description": "Lunch",
        })
        html = r.data.decode()
        assert (
            "error" in html.lower()
            or "invalid" in html.lower()
            or "date" in html.lower()
        ), "Invalid date must produce a visible error message in the response"

    @pytest.mark.parametrize("bad_amount,label", [
        ("",     "empty string"),
        ("0",    "zero"),
        ("-5",   "negative number"),
        ("abc",  "non-numeric string"),
        ("0.00", "zero as decimal"),
    ])
    def test_various_invalid_amounts_return_200(self, auth_client, bad_amount, label):
        r = auth_client.post("/expenses/add", data={
            "amount": bad_amount,
            "category": "Food",
            "date": "2026-03-20",
            "description": "Test",
        })
        assert r.status_code == 200, (
            f"Amount '{label}' ({bad_amount!r}) must re-render form with 200, not redirect"
        )

    @pytest.mark.parametrize("bad_category", [
        "NotACategory",
        "",
        "food",          # wrong case — must be exact match
        "FOOD",
        "Snacks",
        " Food",         # leading space
    ])
    def test_various_invalid_categories_return_200(self, auth_client, bad_category):
        r = auth_client.post("/expenses/add", data={
            "amount": "50.0",
            "category": bad_category,
            "date": "2026-03-20",
            "description": "Test",
        })
        assert r.status_code == 200, (
            f"Category {bad_category!r} (not in fixed list) must re-render form with 200"
        )

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",
        "20260320",      # missing hyphens
        "2026/03/20",    # wrong separator
        "03-20-2026",    # wrong order
        "2026-99-01",    # invalid month
        "2026-03-99",    # invalid day
    ])
    def test_various_invalid_dates_return_200(self, auth_client, bad_date):
        r = auth_client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": bad_date,
            "description": "Test",
        })
        assert r.status_code == 200, (
            f"Date {bad_date!r} must re-render form with 200, not redirect"
        )
