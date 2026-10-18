"""
tests/test_date_filter_profile.py

Tests for the date-range filter feature on the GET /profile route.
Based on spec: .claude/specs/06-date-filter-profile.md

Covers:
  - Auth guard: unauthenticated requests redirect to /login
  - Happy paths: both bounds, date_from only, date_to only, no filter (all-time)
  - Validation: invalid date strings silently ignored, page loads with all-time data
  - Stats accuracy: Total Spent and Top Category reflect filtered range
  - Category breakdown restricted to filtered range
  - Edge case: no expenses in selected range shows Rs.0.00, 0 transactions, no error
  - Template: form pre-fills active dates, Filtered label, Clear link, Rs. currency,
    form uses GET method, accessibility (for= / id= pairing)
"""

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app

# ---------------------------------------------------------------------------
# Seed constants — deterministic dates and amounts used in all assertions
#
# Dates chosen so each filter scenario produces a unique, unambiguous total:
#   Oct 1–7  : Food (500) + Transport (300) = 800
#   Oct 8+   : Bills (200) + Shopping (400) = 600
#   All-time :                               = 1400
# ---------------------------------------------------------------------------

SEED_EXPENSES = [
    # (amount, category, date, description)
    (500.00, "Food",      "2026-10-01", "Oct 1 food"),
    (300.00, "Transport", "2026-10-05", "Oct 5 transport"),
    (200.00, "Bills",     "2026-10-10", "Oct 10 bills"),
    (400.00, "Shopping",  "2026-10-15", "Oct 15 shopping"),
]

TEST_EMAIL = "filtertest@example.com"
TEST_PASS  = "filterpass1"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """
    Redirect all database I/O to an isolated temp file, create the schema,
    insert one test user and four expenses with known dates and amounts.

    The monkeypatch is automatically undone after each test, so the real
    spendly.db is never touched.
    """
    import database.db as db_module
    from database.db import init_db, get_db

    db_path = str(tmp_path / "test_filter.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    # Create tables in the temp file
    init_db()

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Filter Tester", TEST_EMAIL, generate_password_hash(TEST_PASS)),
        )
        db.commit()

        user_id = db.execute(
            "SELECT id FROM users WHERE email = ?", (TEST_EMAIL,)
        ).fetchone()["id"]

        db.executemany(
            "INSERT INTO expenses"
            " (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            [
                (user_id, amt, cat, dt, desc)
                for amt, cat, dt, desc in SEED_EXPENSES
            ],
        )
        db.commit()
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
# Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:

    def test_unauthenticated_profile_redirects(self, client):
        r = client.get("/profile")
        assert r.status_code == 302, "Unauthenticated /profile must redirect"
        assert "/login" in r.headers["Location"]

    def test_unauthenticated_profile_with_date_params_redirects(self, client):
        r = client.get("/profile?date_from=2026-10-01&date_to=2026-10-07")
        assert r.status_code == 302, "Auth guard must apply even when date params are present"
        assert "/login" in r.headers["Location"]


# ---------------------------------------------------------------------------
# No filter — all-time data (existing behaviour must be unchanged)
# ---------------------------------------------------------------------------

class TestNoFilter:

    def test_no_filter_returns_200(self, auth_client):
        assert auth_client.get("/profile").status_code == 200

    def test_no_filter_all_time_total(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert "₹1,400.00" in html, "All-time total must be ₹1,400.00"

    def test_no_filter_all_categories_present(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        for _, category, _, _ in SEED_EXPENSES:
            assert category in html, f"Category '{category}' must appear in all-time view"

    def test_no_filter_top_category_is_food(self, auth_client):
        # Food (500) is the highest-spend single category in the seed data
        html = auth_client.get("/profile").data.decode()
        assert "Food" in html

    def test_no_filter_currency_is_rupee_symbol(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert "₹" in html, "Currency must use the Rupee symbol"
        assert "£" not in html, "Currency must not use the Pound symbol"


# ---------------------------------------------------------------------------
# Both date_from and date_to supplied
# ---------------------------------------------------------------------------

class TestBothBounds:

    def test_both_bounds_returns_200(self, auth_client):
        r = auth_client.get("/profile?date_from=2026-10-01&date_to=2026-10-07")
        assert r.status_code == 200

    def test_both_bounds_correct_total(self, auth_client):
        # Oct 1 (500) + Oct 5 (300) = 800; Oct 10 and 15 excluded
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "₹800.00" in html, "Filtered total Oct 1–7 must be ₹800.00"

    def test_both_bounds_hides_alltime_total(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "₹1,400.00" not in html, (
            "All-time total (₹1,400.00) must not appear when a date filter is active"
        )

    def test_lower_bound_inclusive(self, auth_client):
        # Single day: Oct 1 only — amount must appear
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-01"
        ).data.decode()
        assert "₹500.00" in html, "Lower bound date must be inclusive"

    def test_upper_bound_inclusive(self, auth_client):
        # Single day: Oct 5 only — amount must appear
        html = auth_client.get(
            "/profile?date_from=2026-10-05&date_to=2026-10-05"
        ).data.decode()
        assert "₹300.00" in html, "Upper bound date must be inclusive"

    def test_both_bounds_top_category_reflects_filter(self, auth_client):
        # In Oct 1–7 range: Food (500) > Transport (300)
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "Food" in html, "Top category for Oct 1–7 must be Food"

    def test_both_bounds_out_of_range_amounts_absent(self, auth_client):
        # Bills (Oct 10, ₹200.00) and Shopping (Oct 15, ₹400.00) outside range
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "₹200.00" not in html, "Bills amount must not appear for Oct 1–7 filter"
        assert "₹400.00" not in html, "Shopping amount must not appear for Oct 1–7 filter"

    def test_both_bounds_in_range_category_amounts_present(self, auth_client):
        # Food and Transport totals must appear in the category breakdown
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "₹500.00" in html, "Food amount must appear for Oct 1–7 filter"
        assert "₹300.00" in html, "Transport amount must appear for Oct 1–7 filter"


# ---------------------------------------------------------------------------
# Only date_from supplied (no upper bound)
# ---------------------------------------------------------------------------

class TestOnlyDateFrom:

    def test_date_from_only_returns_200(self, auth_client):
        assert auth_client.get("/profile?date_from=2026-10-08").status_code == 200

    def test_date_from_only_correct_total(self, auth_client):
        # Oct 10 (200) + Oct 15 (400) = 600; Oct 1 and Oct 5 excluded
        html = auth_client.get("/profile?date_from=2026-10-08").data.decode()
        assert "₹600.00" in html, "date_from only: total must be ₹600.00"

    def test_date_from_only_excludes_earlier_amounts(self, auth_client):
        html = auth_client.get("/profile?date_from=2026-10-08").data.decode()
        assert "₹500.00" not in html, "Oct 1 (Food) must be excluded by date_from=2026-10-08"
        assert "₹300.00" not in html, "Oct 5 (Transport) must be excluded by date_from=2026-10-08"

    def test_date_from_only_includes_all_later_categories(self, auth_client):
        html = auth_client.get("/profile?date_from=2026-10-08").data.decode()
        assert "Bills" in html, "Bills (Oct 10) must appear when date_from=2026-10-08"
        assert "Shopping" in html, "Shopping (Oct 15) must appear when date_from=2026-10-08"

    def test_date_from_only_no_alltime_total(self, auth_client):
        html = auth_client.get("/profile?date_from=2026-10-08").data.decode()
        assert "₹1,400.00" not in html, "All-time total must not appear when date_from is active"


# ---------------------------------------------------------------------------
# Only date_to supplied (no lower bound)
# ---------------------------------------------------------------------------

class TestOnlyDateTo:

    def test_date_to_only_returns_200(self, auth_client):
        assert auth_client.get("/profile?date_to=2026-10-05").status_code == 200

    def test_date_to_only_correct_total(self, auth_client):
        # Oct 1 (500) + Oct 5 (300) = 800; Oct 10 and Oct 15 excluded
        html = auth_client.get("/profile?date_to=2026-10-05").data.decode()
        assert "₹800.00" in html, "date_to only: total must be ₹800.00"

    def test_date_to_only_excludes_later_amounts(self, auth_client):
        html = auth_client.get("/profile?date_to=2026-10-05").data.decode()
        assert "₹200.00" not in html, "Oct 10 (Bills) must be excluded by date_to=2026-10-05"
        assert "₹400.00" not in html, "Oct 15 (Shopping) must be excluded by date_to=2026-10-05"

    def test_date_to_only_includes_all_earlier_categories(self, auth_client):
        html = auth_client.get("/profile?date_to=2026-10-05").data.decode()
        assert "Food" in html, "Food (Oct 1) must appear when date_to=2026-10-05"
        assert "Transport" in html, "Transport (Oct 5) must appear when date_to=2026-10-05"

    def test_date_to_only_no_alltime_total(self, auth_client):
        html = auth_client.get("/profile?date_to=2026-10-05").data.decode()
        assert "₹1,400.00" not in html, "All-time total must not appear when date_to is active"


# ---------------------------------------------------------------------------
# Invalid date validation — silently ignored, all-time data shown
# ---------------------------------------------------------------------------

class TestInvalidDateValidation:

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",        # letters, 10 chars, passes length but fails strptime
        "2026-99-99",        # invalid month/day, 10 chars, fails strptime
        "20261001",          # correct digits, no hyphens, 8 chars — fails length check
        "2026/10/01",        # wrong separator, 10 chars, fails strptime
        "abc",               # too short
        "2026-10-1",         # not zero-padded, 9 chars — fails length check
        "2026-10-001",       # too long, 11 chars — fails length check
        " 2026-10-01",       # leading space, 11 chars — fails length check
    ])
    def test_invalid_date_from_silently_ignored(self, auth_client, bad_date):
        r = auth_client.get(f"/profile?date_from={bad_date}")
        assert r.status_code == 200, (
            f"Invalid date_from={bad_date!r} must not cause an error"
        )
        html = r.data.decode()
        assert "₹1,400.00" in html, (
            f"Invalid date_from={bad_date!r} must be silently ignored; "
            "page must show all-time total of ₹1,400.00"
        )

    @pytest.mark.parametrize("bad_date", [
        "not-a-date",
        "2026-99-99",
        "20261031",
        "2026/10/31",
        "2026-10-3",         # not zero-padded, 9 chars
    ])
    def test_invalid_date_to_silently_ignored(self, auth_client, bad_date):
        r = auth_client.get(f"/profile?date_to={bad_date}")
        assert r.status_code == 200, (
            f"Invalid date_to={bad_date!r} must not cause an error"
        )
        html = r.data.decode()
        assert "₹1,400.00" in html, (
            f"Invalid date_to={bad_date!r} must be silently ignored; "
            "page must show all-time total of ₹1,400.00"
        )

    def test_valid_date_from_invalid_date_to_uses_from_only(self, auth_client):
        # Valid date_from + invalid date_to → invalid date_to ignored → only lower bound applied
        r = auth_client.get("/profile?date_from=2026-10-08&date_to=not-a-date")
        assert r.status_code == 200
        html = r.data.decode()
        # Oct 10 (200) + Oct 15 (400) = 600  (no upper bound since date_to is invalid)
        assert "₹600.00" in html, (
            "When date_to is invalid, only date_from should apply; total must be ₹600.00"
        )

    def test_invalid_date_from_valid_date_to_uses_to_only(self, auth_client):
        # Invalid date_from + valid date_to → invalid date_from ignored → only upper bound applied
        r = auth_client.get("/profile?date_from=not-a-date&date_to=2026-10-05")
        assert r.status_code == 200
        html = r.data.decode()
        # Oct 1 (500) + Oct 5 (300) = 800  (no lower bound since date_from is invalid)
        assert "₹800.00" in html, (
            "When date_from is invalid, only date_to should apply; total must be ₹800.00"
        )


# ---------------------------------------------------------------------------
# Edge case: no expenses in the selected range
# ---------------------------------------------------------------------------

class TestNoExpensesInRange:

    def test_future_range_returns_200(self, auth_client):
        # November 2026 has no seeded expenses
        r = auth_client.get("/profile?date_from=2026-11-01&date_to=2026-11-30")
        assert r.status_code == 200, "Empty date range must not raise an error"

    def test_future_range_total_is_zero(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-11-01&date_to=2026-11-30"
        ).data.decode()
        assert "₹0.00" in html, "Empty date range must show ₹0.00 total"

    def test_future_range_no_category_amounts(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-11-01&date_to=2026-11-30"
        ).data.decode()
        for amount_str in ["₹500.00", "₹300.00", "₹200.00", "₹400.00", "₹1,400.00"]:
            assert amount_str not in html, (
                f"{amount_str} must not appear for an empty date range"
            )

    def test_past_range_before_all_expenses_returns_zero(self, auth_client):
        # Range entirely before the oldest expense (Sep 2026)
        r = auth_client.get("/profile?date_from=2026-09-01&date_to=2026-09-30")
        assert r.status_code == 200
        html = r.data.decode()
        assert "₹0.00" in html, "Range before all expenses must show ₹0.00"

    def test_date_from_after_all_expenses_returns_zero(self, auth_client):
        # date_from beyond the latest expense
        r = auth_client.get("/profile?date_from=2026-12-01")
        assert r.status_code == 200
        html = r.data.decode()
        assert "₹0.00" in html, "date_from after all expenses must yield ₹0.00"


# ---------------------------------------------------------------------------
# Template features: form pre-fill, Filtered label, Clear link, accessibility
# ---------------------------------------------------------------------------

class TestTemplateFeatures:

    def test_filter_form_has_date_from_input(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert 'name="date_from"' in html, "Filter form must include a date_from input"

    def test_filter_form_has_date_to_input(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert 'name="date_to"' in html, "Filter form must include a date_to input"

    def test_filter_form_uses_get_method(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert (
            'method="GET"' in html or 'method="get"' in html
        ), "Filter form must use the GET method"

    def test_filter_form_pre_fills_date_from(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert 'value="2026-10-01"' in html, (
            "date_from input must be pre-filled with the active filter value"
        )

    def test_filter_form_pre_fills_date_to(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert 'value="2026-10-07"' in html, (
            "date_to input must be pre-filled with the active filter value"
        )

    def test_filtered_label_appears_when_both_bounds_active(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "Filtered" in html, (
            "'Filtered' label must appear when a date filter is active"
        )

    def test_filtered_label_shows_date_from_in_label(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "2026-10-01" in html, (
            "Active date_from value must appear in the filter label on the page"
        )

    def test_filtered_label_shows_date_to_in_label(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "2026-10-07" in html, (
            "Active date_to value must appear in the filter label on the page"
        )

    def test_filtered_label_absent_without_filter(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert "Filtered:" not in html, (
            "'Filtered:' subtitle must not appear when no date filter is active"
        )

    def test_clear_link_navigates_to_profile_without_params(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        # The Clear link must point to /profile with no query string
        assert 'href="/profile"' in html, (
            "Clear link must navigate to /profile with no query parameters"
        )

    def test_clear_link_text_or_label_present(self, auth_client):
        html = auth_client.get(
            "/profile?date_from=2026-10-01&date_to=2026-10-07"
        ).data.decode()
        assert "Clear" in html, "A Clear link must be visible when a filter is active"

    def test_labels_have_for_attribute_for_accessibility(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert "for=" in html, (
            "Form labels must use the 'for' attribute to associate with inputs"
        )

    def test_date_from_input_has_id_for_label_association(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert 'id="date_from"' in html, (
            "date_from input must have id='date_from' to match its label's for= attribute"
        )

    def test_date_to_input_has_id_for_label_association(self, auth_client):
        html = auth_client.get("/profile").data.decode()
        assert 'id="date_to"' in html, (
            "date_to input must have id='date_to' to match its label's for= attribute"
        )
