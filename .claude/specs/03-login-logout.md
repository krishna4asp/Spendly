# Spec: Login and Logout

## Overview

Implement login and logout so registered users can authenticate and end their session. This step wires up the existing `login.html` form to a POST handler that verifies email and password against the database, starts a session on success, and provides a logout route that clears the session. Together these complete the core auth loop started in Step 02 (Registration).

## Depends on

- Step 01 — Database setup (`users` table with `password_hash` column)
- Step 02 — Registration (`secret_key`, session infrastructure, navbar conditional already in place)

## Routes

- `GET /login` — render the login form; redirect to `/` if already logged in — public
- `POST /login` — verify credentials, start session, redirect to `/` — public
- `GET /logout` — clear session, redirect to `/` — logged-in

## Database changes

No database changes. The `users` table from Step 01 is sufficient.

## Templates

- **Modify:** `templates/login.html` — already renders `{{ error }}`; no structural changes needed
- **Modify:** `templates/base.html` — no changes needed if Step 02 is merged (navbar conditional already present)

## Files to change

- `app.py` — add `check_password_hash` import; convert `GET /login` stub to `GET+POST` handler; implement `GET /logout`

## Files to create

None.

## New dependencies

No new dependencies. `werkzeug.security.check_password_hash` is already installed.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never string-format SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Normalise email to lowercase before the database lookup
- On invalid credentials: re-render the form with a **generic** error — "Invalid email or password." (do not reveal whether the email exists)
- On success: set `session["user_id"]` and `session["user_name"]`, then redirect to `/`
- `GET /login` when already logged in: redirect to `/` immediately
- `GET /logout`: call `session.clear()`, then redirect to `/`

## Definition of done

- [ ] `GET /login` returns 200 and renders the form
- [ ] `GET /login` when session is active redirects to `/` (no re-login loop)
- [ ] Submitting wrong email shows "Invalid email or password."
- [ ] Submitting correct email with wrong password shows "Invalid email or password."
- [ ] Submitting valid credentials sets `session["user_id"]` and `session["user_name"]`
- [ ] After successful login the browser is redirected (302) to `/`
- [ ] Navbar shows the user's name after login (session visible in base template)
- [ ] `GET /logout` clears the session and redirects to `/`
- [ ] After logout the navbar shows "Sign in" / "Get started" again
- [ ] App starts without errors
