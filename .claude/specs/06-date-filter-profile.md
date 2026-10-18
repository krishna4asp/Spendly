# Spec: Date Filter for Profile Page

## Overview

Step 6 adds a date range filter to the profile page dashboard. Currently the
profile page shows all-time summary stats, the 10 most recent transactions, and
an all-time category breakdown. This step lets users narrow every data section
— stats, transactions, and category breakdown — to a chosen date range using
from/to date inputs. The filter is a plain HTML GET form so the selected range
is reflected in the URL and survives a page refresh. When no dates are supplied
the page behaves exactly as it does today (all-time data).

## Depends on

- Step 1: Database setup (`expenses` table with `date` TEXT column in YYYY-MM-DD format)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 5: Backend routes for profile (live queries via `database/queries.py`)

## Routes

No new routes. The existing `GET /profile` route is modified to accept two
optional query parameters:

- `date_from` — ISO date string `YYYY-MM-DD`, inclusive lower bound
- `date_to` — ISO date string `YYYY-MM-DD`, inclusive upper bound

## Database changes

No database changes. All filtering is done at query time with `WHERE date >=
? AND date <= ?` clauses added to existing queries.

## Templates

- **Modify**: `templates/profile.html`
  - Add a date filter form above the "Recent Transactions" card using a
    `<form method="GET" action="/profile">` with two `<input type="date">`
    fields (`name="date_from"` and `name="date_to"`) and a submit button.
  - Add a "Clear" link that navigates to `/profile` with no query params.
  - Display the active filter range as a subtitle under the "Recent
    Transactions" and "Spending by Category" card headers when a filter is
    active (e.g. "Filtered: 2026-10-01 → 2026-10-07").
  - The stats row (`profile-stats`) must also reflect the filtered range.

## Files to change

- `database/queries.py` — update all three query functions to accept optional
  `date_from` and `date_to` keyword arguments and apply them to the WHERE clause
- `app.py` — read `date_from` and `date_to` from `request.args` in the `profile()`
  view and pass them to all three query helpers; pass them back to the template
  so the form pre-fills with the current selection
- `templates/profile.html` — add the filter form and conditional filter labels

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Date values from `request.args` must be validated: accept only strings that
  match `YYYY-MM-DD` (10 characters, digits and hyphens in the right positions);
  silently ignore any value that fails validation rather than crashing
- If only `date_from` is supplied, filter `date >= date_from` with no upper bound
- If only `date_to` is supplied, filter `date <= date_to` with no lower bound
- If neither is supplied, return all records (existing behaviour)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles — add any new component styles to `static/css/style.css`
  in a new labelled section before the `/* Responsive */` block
- Currency must always display as ₹ — never £ or $
- The filter form must be accessible: `<label>` elements must be associated
  with their `<input>` via matching `for`/`id` attributes

## Definition of done

- [ ] Visiting `/profile` with no query params shows all-time data (unchanged behaviour)
- [ ] Visiting `/profile?date_from=2026-10-01&date_to=2026-10-07` shows only transactions
      dated 2026-10-01 through 2026-10-07 inclusive
- [ ] The stats card (Total Spent, Transactions, Top Category) updates to reflect the
      filtered date range, not all-time totals
- [ ] The category breakdown updates to reflect only expenses within the filtered range
- [ ] The date inputs in the filter form are pre-filled with the currently active
      `date_from` and `date_to` values after submitting
- [ ] Clicking the "Clear" link resets to all-time data with empty date inputs
- [ ] Supplying only `date_from` returns all transactions from that date onward
- [ ] Supplying only `date_to` returns all transactions up to and including that date
- [ ] Supplying an invalid date string (e.g. `date_from=not-a-date`) is silently
      ignored — the page loads with all-time data and no error
- [ ] A user with no expenses in the selected range sees ₹0.00 total, 0 transactions,
      empty category breakdown — no errors
