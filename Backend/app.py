import os
import re
import sqlite3
from functools import wraps

import pdfplumber
from flask import (Flask, request, jsonify, session, g, send_from_directory,
                   redirect, abort)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__, static_folder=None)
#todo:secret_key setup
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Files the server is allowed to hand out
PUBLIC_PAGES = {"index.html", "login.html", "signup.html"}
ASSETS = {"style.css", "login.css", "applicant.css",
          "script.js", "auth.js", "applicant.js"}
ROLES = {"applicant", "recruiter"}


# ================= DATABASE =================
def get_db():
    """One SQLite connection per request (a single global one is not thread-safe)."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT,
            password TEXT,
            role TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            exp_in_years INTEGER,
            skills TEXT
        )""")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(data)")]
    if "user_id" not in cols:
        conn.execute("ALTER TABLE data ADD COLUMN user_id INTEGER")

    for name, col in (("idx_users_username", "username"), ("idx_users_email", "email")):
        try:
            conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON users({col})")
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()


init_db()


# ================= RESUME PARSING =================
SKILLSET = [
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "sql", "mysql",
    "postgresql", "mongodb", "html", "css", "react", "angular", "node.js", "express.js",
    "flask", "fastapi", "django", "git", "docker", "aws", "excel", "machine learning",
    "deep learning", "operating systems", "data analysis", "pandas", "numpy", "tensorflow", "linux", "kafka", "docker",
    "spring boot", "golang", "swift", "kubernetes","cloud computing", "redis", "jwt",
    "jenkins", "prometheus", "postman", "devops", "asp.net core", "rabbitmq", 
]

# "java" must not match inside "javascript", so require a non-word boundary.
SKILL_PATTERNS = {
    s: re.compile(r"(?<![a-z0-9+#])" + re.escape(s) + r"(?![a-z0-9+#])")
    for s in SKILLSET
}


def read_pdf(file_storage):
    parts = []
    with pdfplumber.open(file_storage.stream) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    return "\n".join(parts)


def extract_skills(text):
    text = text.lower()
    return [s for s, pat in SKILL_PATTERNS.items() if pat.search(text)]


def extract_email(text):
    m = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.\w+", text)
    return m.group() if m else ""


def extract_phone(text):
    # Indian mobile number, optionally prefixed by +91
    m = re.search(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{9})(?!\d)", text)
    return m.group(1) if m else ""


def extract_experience(text):
    """Largest 'N years' / 'N yrs' figure in the text (a rough heuristic)."""
    found = re.findall(r"(\d{1,2})(?:\.\d)?\s*\+?\s*(?:years?|yrs?)\b", text.lower())
    return max((int(x) for x in found), default=0)


def compute_score(skills, experience):
    return min(100, len(skills) * 10 + min(experience, 5) * 2)


#AUTH
def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    return get_db().execute(
        "SELECT id, username, email, role FROM users WHERE id=?", (uid,)
    ).fetchone()


def api_login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"message": "You are logged out,Please log in first"}), 401
            if role and user["role"] != role:
                return jsonify({"message": f"This is only for {role}s"}), 403
            return fn(user, *args, **kwargs)
        return wrapper
    return deco


def home_for(role):
    return "/recruiter.html" if role == "recruiter" else "/applicant_dashboard.html"


#PAGES
@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<name>")
def pages(name):
    if name in PUBLIC_PAGES or name in ASSETS:
        return send_from_directory(BASE_DIR, name)

    protected = {
        "applicant_dashboard.html": "applicant", "applicant_dashboard": "applicant",
        "recruiter.html": "recruiter", "recruiter": "recruiter",
    }
    if name in protected:
        user = current_user()
        if not user:
            return redirect("/login.html")
        if user["role"] != protected[name]:
            return redirect(home_for(user["role"]))
        page = "applicant_dashboard.html" if protected[name] == "applicant" else "recruiter.html"
        return send_from_directory(BASE_DIR, page)

    abort(404)


#AUTH API 
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = str(data.get("role", ""))

    if not username or not email or not password:
        return jsonify({"message": "Username, email and password are required"}), 400
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({"message": "Enter a valid email address"}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters"}), 400
    if role not in ROLES:
        return jsonify({"message": "Choose a valid role"}), 400

    db = get_db()
    exists = db.execute("SELECT 1 FROM users WHERE username=? OR email=?",
                        (username, email)).fetchone()
    if exists:
        return jsonify({"message": "Username or email is already registered"}), 409

    try:
        cur = db.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?,?,?,?)",
            (username, email, generate_password_hash(password), role))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Username or email is already registered"}), 409

    session.clear()
    session["uid"] = cur.lastrowid
    return jsonify({"message": "User created", "role": role}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    role = str(data.get("role", ""))

    user = get_db().execute(
        "SELECT id, password, role FROM users WHERE username=?", (username,)
    ).fetchone()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid username or password"}), 401
    if role and role != user["role"]:
        return jsonify({"message": f"This account is registered as: {user['role']}. "
                                   f"Change 'Login as' and try again."}), 403

    session.clear()
    session["uid"] = user["id"]
    return jsonify({"message": "Login success", "role": user["role"]})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/me")
@api_login_required()
def me(user):
    return jsonify({"username": user["username"], "role": user["role"]})


#Resume API 
def profile_json(row):
    skills = [s for s in (row["skills"] or "").split(",") if s]
    exp = row["exp_in_years"] or 0
    return {
        "name": row["name"],
        "skills": skills,
        "email": row["email"] or "",
        "phone": row["phone"] or "",
        "experience": exp,
        "score": compute_score(skills, exp),
    }


@app.route("/upload", methods=["POST"])
@api_login_required("applicant")
def upload(user):
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"message": "Please choose a PDF file"}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"message": "Only PDF resumes are supported!"}), 400

    try:
        text = read_pdf(file)
    except Exception:
        return jsonify({"message": "Could not read that file."}), 400
    if not text.strip():
        return jsonify({"message": "No text found in the PDF (scanned images are not supported)"}), 400

    skills = extract_skills(text)
    email = extract_email(text)
    phone = extract_phone(text)
    experience = extract_experience(text)

    # One resume per applicant: replace the previous one.
    db = get_db()
    db.execute("DELETE FROM data WHERE user_id=?", (user["id"],))
    db.execute(
        "INSERT INTO data (user_id, name, phone, email, exp_in_years, skills) VALUES (?,?,?,?,?,?)",
        (user["id"], user["username"], phone, email, experience, ",".join(skills)))
    db.commit()

    return jsonify({
        "skills": skills,
        "email": email,
        "phone": phone,
        "experience": experience,
        "score": compute_score(skills, experience),
    })


@app.route("/api/my-profile")
@api_login_required("applicant")
def my_profile(user):
    row = get_db().execute(
        "SELECT name, phone, email, exp_in_years, skills FROM data WHERE user_id=?",
        (user["id"],)).fetchone()
    return jsonify({"profile": profile_json(row) if row else None})


@app.route("/api/candidates")
@api_login_required("recruiter")
def candidates(user):
    wanted = [s.strip().lower() for s in request.args.get("skills", "").split(",") if s.strip()]
    min_exp = request.args.get("experience", default=0, type=int) or 0

    rows = get_db().execute(
        "SELECT name, phone, email, exp_in_years, skills FROM data").fetchall()

    results = []
    for row in rows:
        p = profile_json(row)
        if p["experience"] < min_exp:
            continue
        matched = [s for s in wanted if s in p["skills"]]
        if wanted and not matched:
            continue
        p["matched"] = matched
        results.append(p)

    results.sort(key=lambda p: (-len(p["matched"]), -p["experience"], -p["score"]))
    return jsonify({"candidates": results})


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"message": "File is too large (max 5 MB)"}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)