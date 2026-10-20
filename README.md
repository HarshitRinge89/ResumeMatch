# ResumeMatch

A small resume-analysis web app built with Flask and SQLite.

- **Applicants** sign up, log in, upload a PDF resume, and see a match score, detected skills, email, phone and years of experience.
- **Recruiters** sign up, log in, and search the stored candidates by skills and minimum experience.

## Project structure

Keep everything in **one flat folder** (no `templates/` or `static/` subfolders):

```
app.py                     Flask backend: pages, auth API, resume parsing, search
database.db                SQLite database (created/updated automatically)
index.html                 Landing page
login.html / signup.html   Auth pages
applicant_dashboard.html   Applicant page (upload + results)
recruiter.html             Recruiter page (candidate search)
auth.js                    Login/signup logic (used by login.html and signup.html)
applicant.js               Applicant dashboard logic
script.js                  Home page button + recruiter search + logout
style.css                  Home and recruiter styles
login.css                  Login/signup styles
applicant.css              Applicant dashboard styles
```

## Requirements

- Python 3.9+
- `pip install flask pdfplumber`

## Run locally

```bash
cd "Backend"
python app.py
```

Then open **http://127.0.0.1:5000**.

Do not open the `.html` files by double-clicking them. The pages talk to the Flask server, so they must be loaded through it.

## How to use it

1. Go to `/signup.html` and create an **Applicant** account (min. 6-character password).
2. Upload a text-based PDF resume on the dashboard. You will see your score and details.
3. Log out, then create a **Recruiter** account.
4. Search for candidates, e.g. skills `python, sql` and experience `2`.

## How it works

### Pages and access control
Flask serves only a fixed list of pages and assets, so `app.py` and `database.db` cannot be downloaded. `applicant_dashboard.html` and `recruiter.html` are protected: without a login you are redirected to the login page, and each role is sent to its own dashboard.

### Authentication
Passwords are hashed with Werkzeug. After login, Flask stores the user id in a signed session cookie. Every protected API route reads that cookie to know who is calling and what role they have.

### Resume analysis (`/upload`)
1. `pdfplumber` extracts the PDF text.
2. Skills are matched against the `SKILLSET` list in `app.py` (whole-word match).
3. Email, phone (Indian mobile format) and experience (largest "N years" in the text) are extracted with regular expressions.
4. Score = `10 points per skill + 2 points per year of experience (max 5 years)`, capped at 100.
5. The result is saved in the `data` table, replacing the applicant's previous resume.

### Database
| Table | Columns |
|-------|---------|
| `users` | id, username, email, password (hash), role |
| `data` | id, user_id, name, phone, email, exp_in_years, skills (comma separated) |

Tables are created at startup. An older `database.db` is upgraded automatically (the `user_id` column is added).

## API reference

| Method | Route | Who | Purpose |
|--------|-------|-----|---------|
| POST | `/signup` | anyone | Create account (JSON: username, email, password, role) and log in |
| POST | `/login` | anyone | Log in (JSON: username, password, role) |
| POST | `/logout` | anyone | Clear the session |
| GET | `/api/me` | logged in | Current username and role |
| POST | `/upload` | applicant | Upload a PDF (form field `file`) |
| GET | `/api/my-profile` | applicant | Last analysed resume |
| GET | `/api/candidates?skills=a,b&experience=2` | recruiter | Search candidates |

## Customising

- **Add skills:** edit `SKILLSET` in `app.py`.
- **Change the scoring:** edit `compute_score()` in `app.py`.
- **Change max upload size:** `MAX_CONTENT_LENGTH` in `app.py` (default 5 MB).

## Known limitations

- Scanned or image-only PDFs cannot be read (no OCR).
- Experience detection is a rough guess.
- Skill detection only knows the skills in `SKILLSET`.
- No CSRF protection, email verification or password reset.
- `debug=True` and the default `SECRET_KEY` are for local development only. For anything public, set a `SECRET_KEY` environment variable, turn debug off, and run behind a production server such as gunicorn.

---

# What was changed and why

## app.py

The original had three routes (`/signup`, `/login`, `/upload`) and nothing else. Changes:

- **Database connection.** The original used one global connection. It is now opened per request (`get_db()`) and closed automatically (`close_db()`), which is safe when Flask handles several requests at once.
- **`init_db()`.** Creates the tables, adds the missing `user_id` column to old databases, and adds unique indexes on username and email so duplicate accounts can't be created. It runs when the file is loaded.
- **Serving pages.** The original never served any HTML. The `/` and `/<name>` routes now serve only whitelisted pages and assets (`PUBLIC_PAGES`, `ASSETS`). The dashboard routes check the session first and redirect if needed. `/applicant_dashboard` (no `.html`) is also accepted because your old form pointed there.
- **Sessions and roles.** `app.secret_key` enables sessions. `current_user()` looks up the logged-in user, and the `@api_login_required("role")` decorator protects API routes and returns 401 (not logged in) or 403 (wrong role) as JSON.
- **Signup and login.** Input is validated (required fields, email format, password length, valid role). Duplicate users get a 409. Login also checks that the chosen role matches the account, and both routes now put the user id in the session. `/logout` clears it.
- **Parsing fixes.**
  - Skills use a regex with boundaries, so "java" no longer matches inside "javascript". The list is also longer.
  - The phone regex no longer matches inside longer digit strings and accepts a `+91` prefix.
  - New `extract_experience()` replaces the hard-coded `0`.
  - New `compute_score()` adds an experience bonus and caps at 100.
- **`/upload`.** Requires an applicant login, checks the file is a PDF, handles unreadable or empty PDFs with a clear message instead of crashing, saves the resume against the user (replacing the old one), and returns the analysis.
- **New routes.** `/api/me`, `/api/my-profile` (so results show again when you return) and `/api/candidates` (recruiter search; results are sorted by number of matched skills, then experience).
- **Errors.** Files over 5 MB return a JSON error (413 handler).

## auth.js

The original was a fake login: it saved the username in `localStorage` and redirected, ignoring the password and role.

- `isSignup` detects which page it is on by looking for the `confirm-password` field, so one file serves both pages.
- `toggleForm()` now navigates between `login.html` and `signup.html`. The old version rewrote the page text, which was confusing.
- A message line is created above the submit button, shown in red for errors.
- On submit it builds a JSON payload, checks the two passwords match (signup), and calls `fetch` on `/signup` or `/login`. On success it redirects to the recruiter or applicant dashboard based on the role the server returns. On failure it shows the server's message.
- The button is disabled during the request to prevent double submits, and a network failure shows "Is app.py running?".

## applicant.js

The original `analyzeResume()` wrote fake values (82%, "Python, JavaScript, SQL") and was never connected to the page.

- `render(p)` fills the score, skills, email, phone and experience cards. It uses `innerText`, so text from a resume can't inject HTML.
- `loadProfile()` runs on page load and shows the last saved analysis; if you are not logged in it redirects to the login page.
- The form submit handler sends the chosen file to `/upload` with `FormData`, shows "Analyzing...", then either the results or the server's error message.
- `logout()` calls `/logout` and returns to the home page.

## script.js

- `checkLogin()` (home page "Upload Resume" button) now asks the server `/api/me` whether you are logged in, instead of reading `localStorage`, which anyone could fake. Logged-in users go to their dashboard, others to the login page.
- `logout()` was added.
- `findCandidates()` is new: `recruiter.html` called it but it did not exist. It reads the skills and experience fields, calls `/api/candidates`, and shows the results (or "No candidates found").
- `candidateCard()` builds each result card with `textContent`, so resume data is never inserted as HTML.

## Other files changed

- **signup.html:** loads `auth.js` (it loaded the wrong script), duplicate `id="username"` fixed (the email field is now `id="email"`), the button says "Sign Up", a navbar was added and the commented-out old code removed.
- **applicant_dashboard.html:** the form is handled by JavaScript, has a message area, logout button, PDF-only file picker, and loads `applicant.js`.
- **recruiter.html:** navbar, search form, results area, and loads `script.js`.
- **applicant.css / style.css:** styles for the new buttons, messages and candidate cards.