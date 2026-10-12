# Spec: Registration

## Overview

Implement user registration so new visitors can create a Spendly account. This step wires up the existing `register.html` form (which already renders correctly) to a POST handler that validates input, prevents duplicate emails, hashes the password, inserts the new user into the database, and starts a session. After registration the user is redirected to the landing page as a logged-in user. This is the first step that writes user-generated data to the database and establishes the session mechanism all future authenticated routes will rely on.

## Depends on

- Step 01 — Database setup (`get_db`, `init_db`, `seed_db` and the `users` table must exist)

## Routes

- `GET /register` — render the registration form — public
- `POST /register` — handle form submission, create account, start session, redirect — public

## Database changes

No database changes. The `users` table created in Step 01 is sufficient.

## Templates

- **Modify:** `templates/register.html` — already renders the form and displays `{{ error }}`; no changes needed unless the error style is missing from CSS
- **Modify:** `templates/base.html` — update navbar to show user name / logout link when `session.user_name` is set

## Files to change

- `app.py` — add `secret_key`, import `os / request / redirect / url_for / session / generate_password_hash`, convert `GET /register` stub to `GET+POST` handler
- `templates/base.html` — conditionally show logged-in state in navbar
- `static/css/style.css` — add `.auth-error` style if not already present

## Files to create

None.

## New dependencies

No new dependencies. `werkzeug.security` is already installed.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- `secret_key` read from `SECRET_KEY` env var with a dev fallback string
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate server-side: name non-empty, email non-empty, password ≥ 8 characters
- Normalise email to lowercase before the duplicate check and insert
- On duplicate email: re-render form with a user-friendly error (do not crash)
- On success: set `session["user_id"]` and `session["user_name"]`, then redirect

## Definition of done

- [ ] `GET /register` returns 200 and renders the form
- [ ] Submitting empty name shows "Full name is required." error
- [ ] Submitting a password shorter than 8 characters shows an error
- [ ] Submitting a duplicate email shows "An account with that email already exists."
- [ ] Submitting valid data creates a new row in the `users` table
- [ ] After successful registration `session["user_id"]` is set
- [ ] After successful registration the browser is redirected (302) to `/`
- [ ] Registering twice with the same email (different case) is rejected (email is lowercased)
- [ ] Navbar shows the user's name after registration (session visible in base template)
- [ ] App starts without errors
