import os
import psycopg2
import pandas as pd
import numpy as np
import io

from flask import Flask, request, render_template, redirect, session, send_file
from flask_bcrypt import Bcrypt

# AI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ======================
# APP INIT
# ======================
app = Flask(__name__)
app.secret_key = "secret123"
bcrypt = Bcrypt(app)

# ======================
# DB CONNECTION
# ======================
def get_db():
    db_url = os.getenv("DATABASE_URL")

    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url, sslmode="require")

    return psycopg2.connect(
        host="localhost",
        database="ai_risk_engine",
        user="postgres",
        password="password",
        port=5432
    )

# ======================
# MODEL LOAD (SAFE)
# ======================
model = None
IDS = []
EMBEDDINGS = None
DATA_MAP = {}

def init_model():
    global model
    if model is None:
        print("Loading model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')

# ======================
# LOAD EMBEDDINGS (SAFE)
# ======================
def load_embeddings():
    global IDS, EMBEDDINGS, DATA_MAP

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT id, process, risk, impact, mitigation, category FROM risks")
        rows = cursor.fetchall()

        IDS = []
        texts = []
        DATA_MAP = {}

        for r in rows:
            IDS.append(r[0])
            texts.append(r[1])
            DATA_MAP[r[0]] = {
                "risk": r[2],
                "impact": r[3],
                "mitigation": r[4],
                "category": r[5]
            }

        if texts:
            init_model()
            EMBEDDINGS = model.encode(texts)
        else:
            EMBEDDINGS = None

        cursor.close()
        db.close()

        print("Embeddings loaded:", len(IDS))

    except Exception as e:
        print("ERROR load_embeddings:", e)
        EMBEDDINGS = None

# ======================
# AUTO INIT (IMPORTANT)
# ======================
@app.before_request
def init_once():
    global EMBEDDINGS
    if EMBEDDINGS is None:
        load_embeddings()

# ======================
# RISK SCORING
# ======================
def calculate_risk_score(risk, impact):
    text = (risk + " " + impact).lower()

    if any(k in text for k in ["fraud", "kebocoran", "finansial"]):
        impact_score = 5
    elif any(k in text for k in ["reputasi", "regulasi"]):
        impact_score = 4
    elif any(k in text for k in ["operasional", "error"]):
        impact_score = 3
    else:
        impact_score = 2

    if any(k in text for k in ["sering", "umum"]):
        likelihood = 5
    elif "tinggi" in text:
        likelihood = 4
    elif "jarang" in text:
        likelihood = 2
    else:
        likelihood = 3

    score = impact_score * likelihood

    if score >= 16:
        level = "High"
    elif score >= 9:
        level = "Medium"
    else:
        level = "Low"

    return score, level

# ======================
# SEARCH
# ======================
def semantic_search(query):
    if EMBEDDINGS is None:
        return []

    query_vec = model.encode([query])
    scores = cosine_similarity(query_vec, EMBEDDINGS)[0]
    top_idx = np.argsort(scores)[::-1][:10]

    results = []

    for i in top_idx:
        rid = IDS[i]
        data = DATA_MAP[rid]

        score, level = calculate_risk_score(data["risk"], data["impact"])

        results.append({
            "risk": data["risk"],
            "impact": data["impact"],
            "mitigation": data["mitigation"],
            "category": data["category"],
            "similarity": float(scores[i]),
            "risk_score": score,
            "level": level
        })

    return results

# ======================
# AUTH HELPERS
# ======================
def is_logged_in():
    return "user" in session

def is_admin():
    return session.get("role") == "admin"

# ======================
# ROUTES
# ======================
@app.route("/")
def index():
    return "APP HIDUP 🚀"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT username, password, role FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user and bcrypt.check_password_hash(user[1], password):
            session["user"] = user[0]
            session["role"] = user[2]
            return redirect("/dashboard")

        return "Login gagal"

    return "Login Page"

@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect("/login")

    return "Dashboard OK"

# ======================
# RUN (LOCAL ONLY)
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

app = Flask(__name__)
app.secret_key = "secret123"

bcrypt = Bcrypt(app)

# ======================
# DB CONNECTION
# ======================
import os
import psycopg2

def get_db():
    db_url = os.getenv("DATABASE_URL")

    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url, sslmode="require")

    return psycopg2.connect(
        host="localhost",
        database="ai_risk_engine",
        user="postgres",
        password="password"
    )
# ======================
# MODEL LOAD
# ======================
model = SentenceTransformer('all-MiniLM-L6-v2')

IDS = []
EMBEDDINGS = None
DATA_MAP = {}

# ======================
# LOAD EMBEDDINGS
# ======================
def load_embeddings():
    global IDS, EMBEDDINGS, DATA_MAP

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id, process, risk, impact, mitigation, category FROM risks")
    rows = cursor.fetchall()

    IDS = []
    texts = []
    DATA_MAP = {}

    for r in rows:
        IDS.append(r[0])
        texts.append(r[1])
        DATA_MAP[r[0]] = {
            "risk": r[2],
            "impact": r[3],
            "mitigation": r[4],
            "category": r[5]
        }

    if len(texts) > 0:
        EMBEDDINGS = model.encode(texts)
    else:
        EMBEDDINGS = None

    cursor.close()
    db.close()

# ======================
# RISK SCORING
# ======================
def calculate_risk_score(risk, impact):
    text = (risk + " " + impact).lower()

    if any(k in text for k in ["fraud", "kebocoran", "finansial"]):
        impact_score = 5
    elif any(k in text for k in ["reputasi", "regulasi"]):
        impact_score = 4
    elif any(k in text for k in ["operasional", "error"]):
        impact_score = 3
    else:
        impact_score = 2

    if any(k in text for k in ["sering", "umum"]):
        likelihood = 5
    elif "tinggi" in text:
        likelihood = 4
    elif "jarang" in text:
        likelihood = 2
    else:
        likelihood = 3

    score = impact_score * likelihood

    if score >= 16:
        level = "High"
    elif score >= 9:
        level = "Medium"
    else:
        level = "Low"

    return score, level

# ======================
# SEMANTIC SEARCH
# ======================
def semantic_search(query):

    if EMBEDDINGS is None or len(EMBEDDINGS) == 0:
        return []

    query_vec = model.encode([query])
    scores = cosine_similarity(query_vec, EMBEDDINGS)[0]

    top_idx = np.argsort(scores)[::-1][:10]

    results = []

    for i in top_idx:
        rid = IDS[i]
        data = DATA_MAP[rid]

        risk_score, level = calculate_risk_score(
            data["risk"], data["impact"]
        )

        results.append({
            "risk": data["risk"],
            "impact": data["impact"],
            "mitigation": data["mitigation"],
            "category": data["category"],
            "similarity": float(scores[i]),
            "risk_score": risk_score,
            "level": level
        })

    return results

# ======================
# HELPERS
# ======================
def is_logged_in():
    return "user" in session

def is_admin():
    return session.get("role") == "admin"

def log_activity(username, action):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (username, action) VALUES (%s, %s)",
        (username, action)
    )
    db.commit()
    cursor.close()
    db.close()

# ======================
# LOGIN
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT username, password, role FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and bcrypt.check_password_hash(user[1], password):
            session["user"] = user[0]
            session["role"] = user[2]
            log_activity(username, "Login")
            return redirect("/")

        return "Login gagal"

    return render_template("login.html")

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    if "user" in session:
        log_activity(session["user"], "Logout")
    session.clear()
    return redirect("/login")

# ======================
# HOME
# ======================
@app.route("/", methods=["GET", "POST"])
def home():

    if not is_logged_in():
        return redirect("/login")

    results = []
    query = ""

    if request.method == "POST":
        query = request.form["process"]
        results = semantic_search(query)
        # 🔥 SAVE HISTORY
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
INSERT INTO search_history (username, query)
VALUES (%s, %s)
""", (session["user"], query))

    db.commit()
    cursor.close()
    db.close()

    db = get_db()
    cursor = db.cursor()

    for r in results:
        cursor.execute("""
    INSERT INTO analysis_logs (username, process, risk, impact, category, level)
    VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        session["user"],
        query,
        r["risk"],
        r["impact"],
        r["category"],
        r["level"]
    ))

    db.commit()
    cursor.close()
    db.close()
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
SELECT id, query FROM search_history
WHERE username=%s
ORDER BY timestamp DESC
LIMIT 10
""", (session["user"],))

    history = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template(
        "index.html",
        results=results,
        query=query,
        history=history,
        role=session.get("role")  # 🔥 FIX MENU ADMIN
    )

# ======================
# ADMIN PAGE
# ======================
@app.route("/admin")
def admin():
    if not is_admin():
        return "Unauthorized"
    return render_template("admin.html")

# ======================
# Dashboard
# ======================
@app.route("/dashboard")
def dashboard():

    if not is_logged_in():
        return redirect("/login")

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    username = request.args.get("username")
    level = request.args.get("level")

    db = get_db()
    cursor = db.cursor()

    # ======================
    # MAIN QUERY
    # ======================
    query = "SELECT username, process, risk, impact, category, level, timestamp FROM analysis_logs WHERE 1=1"
    params = []

    if start_date:
        query += " AND timestamp >= %s"
        params.append(start_date)

    if end_date:
        query += " AND timestamp <= %s"
        params.append(end_date)

    if username:
        query += " AND username = %s"
        params.append(username)

    if level:
        query += " AND level = %s"
        params.append(level)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()

    # ======================
    # HITUNG DASHBOARD
    # ======================
    total = len(rows)
    high = medium = low = 0
    categories = {}

    for r in rows:
        lvl = r[5]

        if lvl == "High":
            high += 1
        elif lvl == "Medium":
            medium += 1
        else:
            low += 1

        cat = r[4]
        categories[cat] = categories.get(cat, 0) + 1

    # ======================
    # 🔥 TOP PROCESS
    # ======================
    cursor.execute("""
    SELECT process, COUNT(*) as total
    FROM analysis_logs
    GROUP BY process
    ORDER BY total DESC
    LIMIT 5
    """)
    top_process = cursor.fetchall()

    # ======================
    # 🔥 TOP RISK
    # ======================
    cursor.execute("""
    SELECT risk, COUNT(*) as total
    FROM analysis_logs
    GROUP BY risk
    ORDER BY total DESC
    LIMIT 5
    """)
    top_risk = cursor.fetchall()

    # ======================
    # USER LIST
    # ======================
    cursor.execute("SELECT DISTINCT username FROM analysis_logs")
    users = [u[0] for u in cursor.fetchall()]

    # 🔥 CLOSE DI PALING AKHIR
    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        total=total,
        high=high,
        medium=medium,
        low=low,
        categories=categories,
        users=users,
        top_process=top_process,
        top_risk=top_risk,
        role=session.get("role")
    )
# ======================
# UPLOAD
# ======================
@app.route("/upload", methods=["POST"])
def upload():

    if not is_admin():
        return "Unauthorized"

    file = request.files.get("file")
    df = pd.read_excel(file)

    db = get_db()
    cursor = db.cursor()

    for _, row in df.iterrows():
        cursor.execute("""
        INSERT INTO risks (process, risk, impact, mitigation, category)
        VALUES (%s, %s, %s, %s, %s)
        """, (
            row["process"],
            row["risk"],
            row["impact"],
            row["mitigation"],
            row["category"]
        ))

    db.commit()
    cursor.close()
    db.close()

    load_embeddings()

    log_activity(session["user"], "Upload data risk")

    return redirect("/admin")

# ======================
# USERS
# ======================
@app.route("/users")
def users():
    if not is_admin():
        return "Unauthorized"

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT username, role FROM users")
    rows = cursor.fetchall()

    data = [{"username": r[0], "role": r[1]} for r in rows]

    cursor.close()
    db.close()

    return render_template("users.html", data=data)

# ======================
# ADD USER
# ======================
@app.route("/add_user", methods=["POST"])
def add_user():

    if not is_admin():
        return "Unauthorized"

    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
        (username, hashed, role)
    )

    db.commit()
    cursor.close()
    db.close()

    log_activity(session["user"], f"Tambah user {username}")

    return redirect("/users")

# ======================
# AUDIT
# ======================
@app.route("/audit")
def audit():

    if not is_admin():
        return "Unauthorized"

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT username, action, timestamp FROM audit_logs ORDER BY timestamp DESC"
    )

    rows = cursor.fetchall()

    logs = [
        {"username": r[0], "action": r[1], "timestamp": r[2]}
        for r in rows
    ]

    cursor.close()
    db.close()

    return render_template("audit.html", logs=logs)

# ======================
# DELETE HISTORY
# ======================
@app.route("/delete_history/<int:id>")
def delete_history(id):

    if not is_logged_in():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
    DELETE FROM search_history
    WHERE id = %s AND username = %s
    """, (id, session["user"]))

    db.commit()
    cursor.close()
    db.close()

    return redirect("/")

@app.route("/clear_history")
def clear_history():

    if not is_logged_in():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
    DELETE FROM search_history
    WHERE username = %s
    """, (session["user"],))

    db.commit()
    cursor.close()
    db.close()

    return redirect("/")

# ======================
# download excel
# ======================
from flask import send_file
import io

@app.route("/export_excel")
def export_excel():

    if not is_logged_in():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
    SELECT process, risk, impact, category, level, timestamp
    FROM analysis_logs
    ORDER BY timestamp DESC
    """)

    rows = cursor.fetchall()
    cursor.close()
    db.close()

    df = pd.DataFrame(rows, columns=[
        "Process", "Risk", "Impact", "Category", "Level", "Timestamp"
    ])

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        download_name="risk_analysis.xlsx",
        as_attachment=True
    )
# ======================
# INIT
# ======================
load_embeddings()

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)