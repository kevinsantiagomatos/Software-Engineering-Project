import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, request, send_from_directory, Response, jsonify, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import quote_plus
import pymysql


HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "palogroup"),
    "cursorclass": pymysql.cursors.DictCursor,
    "charset": "utf8mb4",
    "autocommit": True,
}

BASE_DIR = Path(__file__).resolve().parents[1]
FRONT_END_DIR = BASE_DIR / "front_end"
STYLE_DIR = BASE_DIR / "style"
DATA_DIR = BASE_DIR / "data_store"
UPLOAD_DIR = BASE_DIR / "uploads"
PROFILE_DIR = UPLOAD_DIR / "profile"
HIRES_DIR = UPLOAD_DIR / "hires"

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
TASK_STATUSES = {"pending", "in_progress", "completed", "blocked"}
ROLE_CATEGORIES = {"employee", "contractor", "hr", "it", "compliance", "manager"}
REQUIRED_DOCUMENT_TYPES = [
    {"id": "government_id", "label": "Official Identification (license/passport)"},
    {"id": "w9", "label": "W-9 / Withholding tax form (Hacienda)"},
    {"id": "asume_clearance", "label": "ASUME certificate"},
    {"id": "background_check", "label": "Criminal Background Check"},
    {"id": "tax_return", "label": "Tax Return Filing Certification"},
    {"id": "bank_certification", "label": "Bank Account Certification for Direct Deposit"},
    {"id": "resume", "label": "Resume"},
    {"id": "certifications", "label": "Evidence of Certifications"},
    {"id": "signed_contract", "label": "Signed Contract"},
    {"id": "crim_compliance", "label": "CRIM Compliance Certification"},
    {"id": "comptroller_registry", "label": "Comptroller Contractor Registry"},
    {"id": "policy_ack", "label": "Policy acknowledgement (signed)"},
]
HR_ATTACHMENT_TYPES = [
    {"id": "offer_letter", "label": "Offer Letter"},
    {"id": "nda", "label": "NDA"},
    {"id": "w4", "label": "W-4"},
]

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET") or secrets.token_hex(32)

# Harden session cookies; defaults are safe for local dev and can be overridden via env
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def fetch_all(query: str, params=None):
    params = params or ()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def fetch_one(query: str, params=None):
    params = params or ()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()


def execute(query: str, params=None):
    params = params or ()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
        connection.commit()


def ensure_directories():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    HIRES_DIR.mkdir(parents=True, exist_ok=True)


def email_is_valid(email: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email or ""))


def verify_user(identifier: str, plain_password: str) -> bool:
    if not identifier or not plain_password:
        return False

    row = fetch_one("SELECT password_hash FROM `user` WHERE email = %s", (identifier,))
    if not row:
        return False
    stored = row["password_hash"]
    try:
        return check_password_hash(stored, plain_password)
    except (ValueError, TypeError):
        # Legacy unsalted SHA-256 fallback
        legacy = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return legacy == stored


def get_user_record(email: str):
    if not email:
        return None
    return fetch_one("SELECT email, full_name, role, department, created_at, avatar_url FROM `user` WHERE email = %s", (email,))


def require_role(allowed_roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get("email"):
                return Response("Authentication required", status=401, mimetype="text/plain")
            role = session.get("role", "")
            if role not in allowed_roles:
                return Response("Forbidden", status=403, mimetype="text/plain")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("email"):
            return Response("Authentication required", status=401, mimetype="text/plain")
        return func(*args, **kwargs)
    return wrapper


def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(16)


CSRF_EXEMPT_PATHS = {"/login", "/logout", "/register", "/reset-password"}


@app.before_request
def csrf_protect():
    # Enforce a lightweight CSRF check for state-changing requests when logged in
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.path in CSRF_EXEMPT_PATHS:
            return None
        if session.get("email"):
            ensure_csrf_token()
            sent = request.headers.get("X-CSRF-Token")
            if not sent or sent != session.get("csrf_token"):
                return Response("CSRF token missing or invalid", status=400, mimetype="text/plain")


@app.get("/api/csrf")
@login_required
def csrf_token():
    ensure_csrf_token()
    return jsonify({"csrf_token": session["csrf_token"]})


def update_user_avatar_file(email: str, avatar_url: str) -> bool:
    query = "UPDATE `user` SET avatar_url = %s WHERE email = %s"
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (avatar_url, email))
        connection.commit()
        return cursor.rowcount == 1


def append_audit(action: str, actor: str, detail: dict):
    execute(
        "INSERT INTO audit_log (id, action, actor, detail, timestamp) VALUES (%s,%s,%s,%s,NOW())",
        (secrets.token_hex(8), action, actor, json.dumps(detail)),
    )


def render_login_result(message: str) -> str:
    return (
        "<!DOCTYPE html>"
        "<html><body>"
        f"<h1>{message}</h1>"
        '<a href="/log_in.html">Back to login</a>'
        "</body></html>"
    )

def change_password(email: str, new_password: str) -> bool:
    if not email or not new_password:
        return False

    hashed = generate_password_hash(new_password)
    query = "UPDATE `user` SET password_hash = %s WHERE email = %s"
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (hashed, email))
            connection.commit()
            return cursor.rowcount == 1
ensure_directories()


def create_user_record(email: str, hashed: str, full_name: str, role: str, department: str):
    return {
        "id": secrets.token_hex(8),
        "email": email,
        "password_hash": hashed,
        "full_name": full_name,
        "role": role or "employee",
        "department": department,
        "status": "pending_hr_review",
        "created_at": datetime.utcnow(),
    }


def register_user_db(record: dict) -> bool:
    query = """
        INSERT INTO `user` (email, id, password_hash, full_name, role, department, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    record["email"],
                    record["id"],
                    record["password_hash"],
                    record["full_name"],
                    record["role"],
                    record["department"],
                    record["status"],
                    record["created_at"],
                ),
            )
        connection.commit()
    return True


@app.post("/register")
def register():
    full_name = (request.form.get("full_name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    confirm = request.form.get("confirm_password") or ""
    department = (request.form.get("department") or "").strip()
    role = (request.form.get("role") or "").strip() or "employee"

    if not full_name or not email or not password or not confirm:
        return Response("Missing required fields.", status=400, mimetype="text/plain")

    if not email_is_valid(email):
        return Response("Invalid email format.", status=400, mimetype="text/plain")

    if password != confirm:
        return Response("Passwords do not match.", status=400, mimetype="text/plain")

    if len(password) < 8:
        return Response("Password must be at least 8 characters.", status=400, mimetype="text/plain")

    hashed = generate_password_hash(password)
    record = create_user_record(email, hashed, full_name, role, department)

    try:
        register_user_db(record)
    except pymysql.err.IntegrityError:
        return Response("User already exists.", status=409, mimetype="text/plain")

    return jsonify({"status": "ok", "message": "Registration received and pending HR review."})

@app.post("/reset-password")
@login_required
def reset_password():
    email = request.form.get("email")          
    old_pw = request.form.get("current_password")  
    pw1   = request.form.get("password")
    pw2   = request.form.get("confirm_password")

    # Check for missing inputs
    if not email or not old_pw or not pw1 or not pw2:
         return Response("Missing fields.", status=400, mimetype="text/plain")

    # Make sure new passwords match
    if pw1 != pw2:
         return Response("Passwords do not match.", status=400, mimetype="text/plain")

    # Verify current password first
    try:
        valid_old = verify_user(email, old_pw)
        if not valid_old:
            return Response("Current password is incorrect.", status=401, mimetype="text/plain")

        # Proceed with password change
        changed = change_password(email, pw1)

    except Exception as exc:
        app.logger.error("Reset error: %s", exc, exc_info=True)
        return Response("Server error.", status=500, mimetype="text/plain")

    # Check if password was actually changed
    if not changed:
        return Response("Unable to change password.", status=500, mimetype="text/plain")

    # Success → redirect to login
    return redirect("/log_in.html?reset=ok", code=302)


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def list_users():
    rows = fetch_all("SELECT email, full_name, role, department, status, created_at FROM `user`")
    cleaned = []
    for u in rows:
        cleaned.append(
            {
                "email": u.get("email"),
                "full_name": u.get("full_name") or "",
                "role": u.get("role") or "",
                "department": u.get("department") or "",
                "status": u.get("status") or "",
                "created_at": u.get("created_at") or "",
            }
        )
    return cleaned


def user_progress_snapshot(email: str, docs=None, tasks=None, policies=None, trainings=None):
    docs = docs or []
    tasks = tasks or []
    policies = policies or []
    trainings = trainings or []
    ud = [d for d in docs if d.get("uploader_email") == email]
    ut = [t for t in tasks if t.get("owner_email") == email]
    upol = [p for p in policies if p.get("email") == email]
    utr = [t for t in trainings if t.get("email") == email]

    doc_total = len(ud)
    doc_done = sum(1 for d in ud if d.get("status") == "approved")
    task_total = len(ut)
    task_done = sum(1 for t in ut if t.get("status") == "completed")
    total_items = doc_total + task_total
    completed = doc_done + task_done
    percentage = (completed / total_items * 100) if total_items else 0

    # simple stage heuristic
    if doc_done and task_done and upol and utr:
        stage = "Completed"
    elif doc_done and (task_total or upol or utr):
        stage = "IT/Project/Training"
    elif doc_total:
        stage = "Documents"
    else:
        stage = "Account Created"

    return {
        "email": email,
        "documents": {"total": doc_total, "approved": doc_done},
        "tasks": {"total": task_total, "completed": task_done},
        "policies_signed": len(upol),
        "training_completed": len(utr),
        "progress_percent": round(percentage, 2),
        "stage": stage,
    }


def load_tasks():
    return fetch_all("SELECT * FROM task")


def create_task_record(payload: dict) -> dict:
    return {
        "id": secrets.token_hex(8),
        "title": payload.get("title", "").strip(),
        "description": payload.get("description", "").strip(),
        "owner_email": payload.get("owner_email", "").strip().lower(),
        "assigned_by": payload.get("assigned_by", "").strip().lower(),
        "category": payload.get("category", "employee"),
        "status": payload.get("status", "pending"),
        "due_date": payload.get("due_date", "").strip(),
        # store as MySQL-friendly strings (avoid ISO/Z format errors)
        "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.post("/documents/upload")
@login_required
def upload_documents():
    full_name = (request.form.get("full_name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    doc_type = (request.form.get("doc_type") or "").strip().lower()
    files = request.files.getlist("documents")

    if not full_name or not email:
        return Response("Full name and email are required.", status=400, mimetype="text/plain")

    if not email_is_valid(email):
        return Response("Invalid email format.", status=400, mimetype="text/plain")

    valid_doc_ids = {d["id"] for d in REQUIRED_DOCUMENT_TYPES}
    if not doc_type or doc_type not in valid_doc_ids:
        return Response("Invalid or missing document type.", status=400, mimetype="text/plain")

    requester = session.get("email", "")
    requester_role = session.get("role", "")
    if requester != email and requester_role not in {"hr", "manager", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")

    if not files:
        return Response("No documents provided.", status=400, mimetype="text/plain")

    stored_entries = []
    for file in files:
        if not file or not file.filename:
            continue

        if not allowed_file(file.filename):
            return Response("Unsupported file type.", status=400, mimetype="text/plain")

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_UPLOAD_BYTES:
            return Response("File too large. Max 10MB per file.", status=400, mimetype="text/plain")

        safe_name = secure_filename(file.filename)
        doc_id = secrets.token_hex(12)
        stored_name = f"{doc_id}_{safe_name}"
        destination = UPLOAD_DIR / stored_name
        file.save(destination)
        checksum = hashlib.sha256(destination.read_bytes()).hexdigest()

        execute(
            """
            INSERT INTO document (id, original_name, stored_name, uploader_email, uploader_name, status, size_bytes, checksum_sha256, uploaded_at, doc_type)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s)
            """,
            (
                doc_id,
                file.filename,
                stored_name,
                email,
                full_name,
                "pending_review",
                size,
                checksum,
                doc_type,
            ),
        )

        stored_entries.append(
            {
                "id": doc_id,
                "original_name": file.filename,
                "stored_name": stored_name,
                "uploader_email": email,
                "uploader_name": full_name,
                "status": "pending_review",
                "size_bytes": size,
                "checksum_sha256": checksum,
                "doc_type": doc_type,
            }
        )

    if not stored_entries:
        return Response("No valid documents received.", status=400, mimetype="text/plain")

    return jsonify({"status": "ok", "documents": stored_entries})


@app.get("/documents")
@login_required
def list_documents():
    email = (request.args.get("email") or "").strip().lower()
    requester = session.get("email")
    requester_role = session.get("role", "")
    if email and email != requester and requester_role not in {"hr", "manager", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if not email and requester_role not in {"hr", "manager", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if email:
        docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
    else:
        docs = fetch_all("SELECT * FROM document")
    return jsonify({"documents": docs})


@app.post("/documents/<doc_id>/status")
def update_document_status(doc_id):
    role = session.get("role", "")
    if role not in {"hr", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    status = (request.form.get("status") or "").strip().lower()
    if status not in {"approved", "rejected", "pending_review"}:
        return Response("Invalid status.", status=400, mimetype="text/plain")

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE document SET status = %s WHERE id = %s", (status, doc_id))
        connection.commit()
        if cursor.rowcount == 0:
            return Response("Document not found.", status=404, mimetype="text/plain")
    append_audit("doc_status", session.get("email", ""), {"doc_id": doc_id, "status": status})

    return jsonify({"status": "ok", "document_id": doc_id, "new_status": status})


@app.post("/api/tasks")
@login_required
@require_role({"hr", "manager", "it", "compliance"})
def create_task():
    payload = {
        "title": request.form.get("title") or "",
        "description": request.form.get("description") or "",
        "owner_email": (request.form.get("owner_email") or "").lower(),
        "assigned_by": (request.form.get("assigned_by") or "").lower(),
        "category": (request.form.get("category") or "").lower(),
        "status": (request.form.get("status") or "pending").lower(),
        "due_date": request.form.get("due_date") or "",
    }

    if not payload["title"] or not payload["owner_email"]:
        return Response("Title and owner_email are required.", status=400, mimetype="text/plain")

    if payload["category"] and payload["category"] not in ROLE_CATEGORIES:
        return Response("Invalid category.", status=400, mimetype="text/plain")

    if payload["status"] not in TASK_STATUSES:
        return Response("Invalid status.", status=400, mimetype="text/plain")

    record = create_task_record(payload)
    execute(
        """
        INSERT INTO task (id, title, description, owner_email, assigned_by, category, status, due_date, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            record["id"],
            record["title"],
            record["description"],
            record["owner_email"],
            record["assigned_by"],
            record["category"],
            record["status"],
            record["due_date"],
            record["created_at"],
            record["updated_at"],
        ),
    )
    return jsonify({"status": "ok", "task": record})


@app.get("/api/tasks")
@login_required
def list_tasks_api():
    email = (request.args.get("email") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    query = "SELECT * FROM task WHERE 1=1"
    params = []
    if email:
        query += " AND owner_email = %s"
        params.append(email)
    if category:
        query += " AND category = %s"
        params.append(category)
    requester = session.get("email")
    requester_role = session.get("role", "")
    if email and email != requester and requester_role not in {"hr", "manager", "it", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if not email and requester_role not in {"hr", "manager", "it", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")

    tasks = fetch_all(query, params)
    return jsonify({"tasks": tasks})


@app.post("/api/tasks/<task_id>/status")
@login_required
def update_task_status(task_id):
    status = (request.form.get("status") or "").strip().lower()
    if status not in TASK_STATUSES:
        return Response("Invalid status.", status=400, mimetype="text/plain")

    task = fetch_one("SELECT owner_email FROM task WHERE id = %s", (task_id,))
    if not task:
        return Response("Task not found.", status=404, mimetype="text/plain")
    requester = session.get("email")
    requester_role = session.get("role", "")
    if requester != task.get("owner_email") and requester_role not in {"hr", "manager", "it", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE task SET status = %s, updated_at = %s WHERE id = %s",
                (status, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), task_id),
            )
        connection.commit()
    return jsonify({"status": "ok", "task_id": task_id, "new_status": status})


@app.get("/api/progress")
@login_required
def onboarding_progress():
    email = (request.args.get("email") or "").strip().lower()
    if email:
        docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
        tasks = fetch_all("SELECT * FROM task WHERE owner_email = %s", (email,))
    else:
        docs = fetch_all("SELECT * FROM document")
        tasks = fetch_all("SELECT * FROM task")

    def user_progress(e):
        return user_progress_snapshot(
            e,
            docs=docs,
            tasks=tasks,
            policies=fetch_all("SELECT * FROM policy_ack"),
            trainings=fetch_all("SELECT * FROM training_completion"),
        )

    requester = session.get("email")
    requester_role = session.get("role", "")

    if email:
        if email != requester and requester_role not in {"hr", "manager", "compliance", "it"}:
            return Response("Forbidden", status=403, mimetype="text/plain")
        return jsonify(user_progress(email))

    if requester_role not in {"hr", "manager", "compliance", "it"}:
        return Response("Forbidden", status=403, mimetype="text/plain")

    emails = {d.get("uploader_email") for d in docs if d.get("uploader_email")} | {t.get("owner_email") for t in tasks if t.get("owner_email")}
    progress_list = [user_progress(e) for e in emails]
    return jsonify({"all": progress_list})


@app.get("/documents/requirements")
@login_required
def document_requirements():
    email = (request.args.get("email") or "").strip().lower()
    requester = session.get("email")
    requester_role = session.get("role", "")
    if email and email != requester and requester_role not in {"hr", "manager", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if not email and requester_role not in {"hr", "manager", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if email:
        docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
    else:
        docs = fetch_all("SELECT * FROM document")
    by_type = {}
    for doc_type in REQUIRED_DOCUMENT_TYPES:
        by_type[doc_type["id"]] = {
            "id": doc_type["id"],
            "label": doc_type["label"],
            "status": "missing",
            "documents": [],
        }

    requester = session.get("email")
    requester_role = session.get("role", "")

    for doc in docs:
        if email and doc.get("uploader_email") != email and requester_role not in {"hr", "manager", "compliance"}:
            continue
        dt = doc.get("doc_type")
        if dt and dt in by_type:
            bucket = by_type[dt]
            bucket["documents"].append(doc)
            if doc.get("status") == "approved":
                bucket["status"] = "approved"
            elif bucket["status"] != "approved":
                bucket["status"] = doc.get("status", "pending_review")

    return jsonify({"requirements": list(by_type.values())})


@app.post("/login")
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    try:
        is_valid = verify_user(username, password)
    except Exception as exc:
        app.logger.error("Login error: %s", exc, exc_info=True)
        return Response("Internal Server Error", status=500, mimetype="text/plain")

    if is_valid:
        user = get_user_record(username) or {}
        session["email"] = username
        session["role"] = (user.get("role") or "employee").lower()
        ensure_csrf_token()
        # Send the user to their dashboard with email prefilled for status checks.
        target = f"/dashboard.html?email={quote_plus(username)}"
        return redirect(target, code=302)

    return Response(render_login_result("Invalid credentials. Try again."), status=401, mimetype="text/html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect("/log_in.html")


@app.get("/api/user")
@login_required
def get_user():
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return Response("Email is required.", status=400, mimetype="text/plain")

    requester = session.get("email")
    requester_role = session.get("role", "")
    if email != requester and requester_role not in {"hr", "manager", "compliance", "it"}:
        return Response("Forbidden", status=403, mimetype="text/plain")

    record = get_user_record(email)
    if not record:
        return Response("User not found.", status=404, mimetype="text/plain")

    # normalize keys
    payload = {
        "email": record.get("email"),
        "full_name": record.get("full_name") or record.get("name") or "",
        "role": record.get("role") or "",
        "department": record.get("department") or "",
        "created_at": record.get("created_at") or record.get("createdAt") or "",
        "avatar_url": record.get("avatar_url") or "",
    }
    return jsonify(payload)


@app.get("/api/users")
@login_required
@require_role({"hr", "manager", "compliance", "it"})
def get_users():
    role_filter = (request.args.get("role") or "").strip().lower()
    users = list_users()
    if role_filter:
        users = [u for u in users if (u.get("role") or "").lower() == role_filter]
    return jsonify({"users": users})


@app.post("/api/policy/ack")
@login_required
def policy_ack():
    email = (request.form.get("email") or "").strip().lower()
    policy_id = (request.form.get("policy_id") or "").strip()
    signature = (request.form.get("signature") or "").strip()
    if not email or not policy_id or not signature:
        return Response("Email, policy_id, and signature are required.", status=400, mimetype="text/plain")
    if email != session.get("email"):
        return Response("Forbidden", status=403, mimetype="text/plain")
    execute(
        "INSERT INTO policy_ack (id, email, policy_id, signature, status, signed_at) VALUES (%s,%s,%s,%s,%s,NOW())",
        (secrets.token_hex(8), email, policy_id, signature, "signed"),
    )
    append_audit("policy_ack", email, {"policy_id": policy_id})
    return jsonify({"status": "ok"})


@app.get("/api/policy/status")
@login_required
def policy_status():
    email = (request.args.get("email") or "").strip().lower()
    if email:
        if email != session.get("email") and session.get("role") not in {"hr", "manager", "compliance"}:
            return Response("Forbidden", status=403, mimetype="text/plain")
        policies = fetch_all("SELECT * FROM policy_ack WHERE email = %s", (email,))
    else:
        if session.get("role") not in {"hr", "manager", "compliance"}:
            return Response("Forbidden", status=403, mimetype="text/plain")
        policies = fetch_all("SELECT * FROM policy_ack")
    return jsonify({"policies": policies})


@app.get("/api/training/list")
@login_required
def training_list():
    modules = fetch_all("SELECT * FROM training_module")
    if not modules:
        defaults = [
            ("security101", "Security 101", "Basic security practices"),
            ("handbook", "Employee Handbook", "Review company policies"),
            ("tools", "Tools Orientation", "Intro to internal tools"),
        ]
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO training_module (id, title, description) VALUES (%s,%s,%s)",
                    defaults,
                )
            connection.commit()
        modules = fetch_all("SELECT * FROM training_module")
    return jsonify({"modules": modules})


@app.post("/api/training/complete")
@login_required
def training_complete():
    email = (request.form.get("email") or "").strip().lower()
    module_id = (request.form.get("module_id") or "").strip()
    if not email or not module_id:
        return Response("Email and module_id are required.", status=400, mimetype="text/plain")
    if email != session.get("email"):
        return Response("Forbidden", status=403, mimetype="text/plain")
    execute("DELETE FROM training_completion WHERE email = %s AND module_id = %s", (email, module_id))
    execute(
        "INSERT INTO training_completion (email, module_id, completed_at) VALUES (%s,%s,NOW())",
        (email, module_id),
    )
    append_audit("training_complete", email, {"module_id": module_id})
    return jsonify({"status": "ok"})


@app.get("/api/training/status")
@login_required
def training_status():
    email = (request.args.get("email") or "").strip().lower()
    if email:
        if email != session.get("email") and session.get("role") not in {"hr", "manager", "compliance"}:
            return Response("Forbidden", status=403, mimetype="text/plain")
        completions = fetch_all("SELECT * FROM training_completion WHERE email = %s", (email,))
    else:
        if session.get("role") not in {"hr", "manager", "compliance"}:
            return Response("Forbidden", status=403, mimetype="text/plain")
        completions = fetch_all("SELECT * FROM training_completion")
    return jsonify({"completions": completions})


@app.post("/api/it/provision")
@require_role({"it", "manager"})
def it_provision():
    email = (request.form.get("email") or "").strip().lower()
    items = request.form.get("items") or "[]"
    try:
        parsed = json.loads(items)
    except json.JSONDecodeError:
        return Response("Invalid items payload.", status=400, mimetype="text/plain")
    execute(
        "INSERT INTO it_provision (id, email, items_json, completed_at) VALUES (%s,%s,%s,NOW())",
        (secrets.token_hex(8), email, json.dumps(parsed)),
    )
    append_audit("it_provision", session.get("email", ""), {"email": email, "items": parsed})
    return jsonify({"status": "ok"})


@app.get("/api/report/summary")
@require_role({"hr", "manager", "compliance", "it"})
def report_summary():
    users = list_users()
    docs = fetch_all("SELECT status FROM document")
    tasks = fetch_all("SELECT status FROM task")
    policies = fetch_all("SELECT id FROM policy_ack")
    trainings = fetch_all("SELECT id FROM training_completion")
    summary = {
        "users": len(users),
        "documents_uploaded": len(docs),
        "documents_approved": sum(1 for d in docs if d.get("status") == "approved"),
        "tasks_total": len(tasks),
        "tasks_completed": sum(1 for t in tasks if t.get("status") == "completed"),
        "policy_signed": len(policies),
        "training_completed": len(trainings),
    }
    return jsonify({"summary": summary})


@app.get("/api/new-hires")
@require_role({"hr", "manager", "compliance", "it"})
def list_new_hires():
    hires = fetch_all("SELECT * FROM new_hire")
    attachments = fetch_all("SELECT * FROM new_hire_attachment")
    docs = fetch_all("SELECT * FROM document")
    tasks = fetch_all("SELECT * FROM task")
    policies = fetch_all("SELECT * FROM policy_ack")
    trainings = fetch_all("SELECT * FROM training_completion")

    att_by_hire = {}
    for att in attachments:
        att_by_hire.setdefault(att["hire_id"], []).append(att)

    for hire in hires:
        hire["attachments"] = att_by_hire.get(hire["id"], [])
        email = (hire.get("email") or "").lower()
        if email:
            hire["progress"] = user_progress_snapshot(email, docs=docs, tasks=tasks, policies=policies, trainings=trainings)
    return jsonify({"hires": hires})


@app.post("/api/profile/photo")
@login_required
def upload_profile_photo():
    email = (request.form.get("email") or "").strip().lower()
    file = request.files.get("photo")

    if not email or not email_is_valid(email):
        return Response("Valid email is required.", status=400, mimetype="text/plain")
    if email != session.get("email") and session.get("role") not in {"hr", "manager"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if not file or not file.filename:
        return Response("No photo provided.", status=400, mimetype="text/plain")
    if not allowed_file(file.filename):
        return Response("Unsupported file type.", status=400, mimetype="text/plain")

    safe_name = secure_filename(file.filename)
    stored_name = f"{secrets.token_hex(8)}_{safe_name}"
    destination = PROFILE_DIR / stored_name
    file.save(destination)

    url_path = f"/uploads/profile/{stored_name}"
    saved = update_user_avatar_file(email, url_path)
    if not saved:
        return Response("User not found.", status=404, mimetype="text/plain")

    return jsonify({"status": "ok", "avatar_url": url_path})


@app.post("/api/hr/register-hire")
@app.post("/api/hr/register-hire/")
@require_role({"hr", "manager"})
def register_hire():
    data = request.form
    files = request.files
    required_fields = ["first_name", "last_name", "email", "role"]
    for field in required_fields:
        if not data.get(field):
            return Response(f"{field} is required.", status=400, mimetype="text/plain")

    email = data.get("email").strip().lower()
    if not email_is_valid(email):
        return Response("Invalid email.", status=400, mimetype="text/plain")

    hire_id = secrets.token_hex(8)
    execute(
        """
        INSERT INTO new_hire (
            id, first_name, middle_name, last_name, email, phone, dob, gov_id,
            street, city, state, postal_code, country, role, department, manager,
            start_date, status, created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        """,
        (
            hire_id,
            data.get("first_name", "").strip(),
            data.get("middle_name", "").strip(),
            data.get("last_name", "").strip(),
            email,
            data.get("phone", "").strip(),
            data.get("dob", None) or None,
            data.get("gov_id", "").strip(),
            data.get("street", "").strip(),
            data.get("city", "").strip(),
            data.get("state", "").strip(),
            data.get("postal_code", "").strip(),
            data.get("country", "").strip(),
            data.get("role", "").strip(),
            data.get("department", "").strip(),
            data.get("manager", "").strip(),
            data.get("start_date", None) or None,
            "pending_document_submission",
        ),
    )

    for att in HR_ATTACHMENT_TYPES:
        f = files.get(att["id"])
        if f and f.filename:
            if not allowed_file(f.filename):
                return Response(f"Unsupported file type for {att['id']}.", status=400, mimetype="text/plain")
            safe = secure_filename(f.filename)
            stored = f"{hire_id}_{att['id']}_{safe}"
            path = HIRES_DIR / stored
            f.save(path)
            execute(
                "INSERT INTO new_hire_attachment (hire_id, att_type, original_name, stored_name, url) VALUES (%s,%s,%s,%s,%s)",
                (hire_id, att["id"], f.filename, stored, f"/uploads/hires/{stored}"),
            )

    append_audit("hire_register", session.get("email", ""), {"hire_id": hire_id})
    return jsonify({"status": "ok", "hire_id": hire_id})


def serve_frontend(asset_path: str):
    if not FRONT_END_DIR.exists():
        return Response("Front-end directory missing", status=500, mimetype="text/plain")
    
    return send_from_directory(FRONT_END_DIR, asset_path)


@app.get("/")
def root():
    return serve_frontend("log_in.html")


@app.get("/style/<path:asset_path>")
def style_assets(asset_path):
    if not STYLE_DIR.exists():
        return Response("Style directory missing", status=500, mimetype="text/plain")
    
    return send_from_directory(STYLE_DIR, asset_path)


@app.get("/uploads/<path:asset_path>")
@login_required
def uploaded_assets(asset_path):
    if not UPLOAD_DIR.exists():
        return Response("Uploads directory missing", status=404, mimetype="text/plain")
    return send_from_directory(UPLOAD_DIR, asset_path)


@app.get("/<path:asset_path>")
def static_assets(asset_path):
    return serve_frontend(asset_path)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
