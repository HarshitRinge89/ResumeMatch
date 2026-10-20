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