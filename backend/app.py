import hashlib
import importlib
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
DEV_AUTOLOGIN_EMAIL = (os.getenv("DEV_AUTOLOGIN_EMAIL") or "").strip().lower()
DEV_AUTOLOGIN_ROLE = (os.getenv("DEV_AUTOLOGIN_ROLE") or "hr").strip().lower()


DB_CONFIG = {
    # Aiven defaults for shared team environment; can still be overridden via env vars.
    "host": os.getenv("DB_HOST", "paolidb-paoli.a.aivencloud.com"),
    "port": int(os.getenv("DB_PORT", "28505")),
    "user": os.getenv("DB_USER", "avnadmin"),
    "password": os.getenv("DB_PASSWORD", "AVNS_PACy97fO-lDRRMeoPvG"),
    "database": os.getenv("DB_NAME", "defaultdb"),
    "cursorclass": pymysql.cursors.DictCursor,
    "charset": "utf8mb4",
    "autocommit": True,
}
DB_AUTO_INIT = os.getenv("DB_AUTO_INIT", "true").strip().lower() not in {"0", "false", "no"}

BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
FRONT_END_DIR = BASE_DIR / "front_end"
STYLE_DIR = BASE_DIR / "style"
DATA_DIR = BASE_DIR / "data_store"
UPLOAD_DIR = BASE_DIR / "uploads"
PROFILE_DIR = UPLOAD_DIR / "profile"
HIRES_DIR = UPLOAD_DIR / "hires"
PLACEHOLDER_DIR = UPLOAD_DIR / "placeholders"
SCHEMA_PATH = BACKEND_DIR / "sql" / "schema.sql"
REQUIRED_TABLES = (
    "department",
    "job_title",
    "user",
    "audit_log",
    "document",
    "task",
    "policy_ack",
    "training_module",
    "training_completion",
    "it_provision",
    "new_hire",
    "new_hire_attachment",
)
DEFAULT_DEPARTMENTS = [
    "Operations",
    "HR",
    "IT",
    "Compliance",
    "Management",
]
DEFAULT_JOB_TITLES = {
    "Operations": ["Operations Coordinator", "Project Coordinator", "Business Analyst"],
    "HR": ["HR Generalist", "Recruiter", "HR Coordinator"],
    "IT": ["Software Engineer", "Developer", "QA Engineer", "IT Support Specialist"],
    "Compliance": ["Compliance Analyst", "Compliance Officer", "Risk Analyst"],
    "Management": ["Project Manager", "Operations Manager", "Team Lead"],
}
PLACEHOLDER_FILES = [
    ("policies/company_policies.pdf", "Placeholder for Company Policies. Replace with signed version."),
    ("policies/medical_plan_policy.pdf", "Placeholder for Medical Plan Policy. Replace with signed version."),
    ("policies/billing_manual.pdf", "Placeholder for Billing Manual. Replace with official document."),
    ("contracts/offer_letter_template.pdf", "Placeholder offer letter template. Replace with DocuSeal export."),
    ("contracts/nda_template.pdf", "Placeholder NDA template. Replace with executed NDA."),
]

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
TASK_STATUSES = {"pending", "in_progress", "completed", "blocked"}
ROLE_CATEGORIES = {"employee", "contractor", "hr", "it", "compliance", "manager"}
ADMIN_ROLES = {"hr", "it", "compliance", "manager"}
REQUIRED_DOCUMENT_TYPES = [
    {"id": "government_id", "label": "Official Identification (license/passport)", "optional": False},
    {"id": "w9", "label": "W-9 / Withholding tax form (Hacienda)", "optional": False},
    {"id": "merchant_registry", "label": "Registro de Comerciante (Dept. de Hacienda)", "optional": False},
    {"id": "asume_clearance", "label": "ASUME certificate", "optional": False},
    {"id": "background_check", "label": "Criminal Background Check", "optional": False},
    {"id": "tax_return", "label": "Certificación de Radicación de Planillas", "optional": False},
    {"id": "bank_certification", "label": "Bank Account Certification for Direct Deposit", "optional": False},
    {"id": "resume", "label": "Resume", "optional": False},
    {"id": "certifications", "label": "Evidence of Certifications", "optional": True},
    {"id": "signed_contract", "label": "Signed Contract", "optional": False},
    {"id": "crim_compliance", "label": "CRIM Compliance Certification", "optional": False},
    {"id": "comptroller_registry", "label": "Comptroller Contractor Registry (gov contracts)", "optional": True},
]
HR_ATTACHMENT_TYPES = [
    {"id": "offer_letter", "label": "Offer Letter"},
    {"id": "nda", "label": "NDA"},
    {"id": "w4", "label": "W-4"},
]
ONBOARDING_BLUEPRINT = {
    "preboarding": {
        "summary": "Approvals, offer, document collection, contract review/signature, archival.",
        "steps": [
            {"id": "approval", "title": "Approval of candidate", "owners": ["executive", "operations", "compliance", "finance"], "deliverable": "Recorded approval decision"},
            {"id": "offer", "title": "Issue formal offer", "owners": ["operations"], "deliverable": "Offer letter sent via email/DocuSeal"},
            {"id": "document_request", "title": "Request mandatory documentation", "owners": ["hr"], "deliverable": "All required documents uploaded"},
            {"id": "document_validation", "title": "Validate documentation", "owners": ["hr", "compliance"], "deliverable": "Documents marked approved/rejected"},
            {"id": "contract_draft", "title": "Send contract draft for review", "owners": ["compliance"], "deliverable": "Contract draft shared with contractor"},
            {"id": "contract_sign", "title": "Final review & signature (DocuSeal)", "owners": ["compliance", "executive"], "deliverable": "Signed contract"},
            {"id": "contract_archive", "title": "Archive signed contract (SharePoint & physical)", "owners": ["compliance"], "deliverable": "Signed contract stored in repository"},
        ],
    },
    "integration": {
        "hr": {
            "summary": "Policy acknowledgements and billing orientation.",
            "checklist": [
                {"id": "policy_company", "title": "Sign Company Policies", "target": "policy_ack"},
                {"id": "policy_medical", "title": "Sign Medical Plan Policy", "target": "policy_ack"},
                {"id": "billing_orientation", "title": "Billing manual orientation", "target": "training"},
            ],
        },
        "operations_it": {
            "summary": "Devices, identity and core tool access.",
            "checklist": [
                {"id": "laptop_intune", "title": "Configure laptop with Intune and required apps", "target": "it"},
                {"id": "m365_account", "title": "Create Microsoft 365 account + Out of Office", "target": "it"},
                {"id": "quickbooks_time", "title": "Grant QuickBooks Time access (@paoli.io)", "target": "it"},
                {"id": "slack_access", "title": "Add to Slack with SSO", "target": "it"},
                {"id": "atlassian_access", "title": "Add to Jira & Confluence (SSO)", "target": "it"},
                {"id": "client_access", "title": "Provision client/project access", "target": "it"},
            ],
        },
        "training": {
            "summary": "Orientation led by PM/Technical Architect within 90 days.",
            "checklist": [
                {"id": "rrhh_policies", "title": "HR policies & norms walkthrough", "target": "training"},
                {"id": "it_security", "title": "IT security + MFA configuration", "target": "training"},
                {"id": "agile_flow", "title": "Agile flow, time entry & documentation", "target": "training"},
            ],
        },
    },
    "documents_required": REQUIRED_DOCUMENT_TYPES,
    "stakeholders": [
        {"id": "hr", "name": "Vianca (HR)", "responsibilities": "Coordination, documents, policies"},
        {"id": "it", "name": "Bryan (IT)", "responsibilities": "Access, device setup, support"},
        {"id": "pm", "name": "Doris (PM)", "responsibilities": "Tasks, objectives, agile onboarding"},
        {"id": "compliance", "name": "Elliot (Compliance)", "responsibilities": "Contracts, approvals"},
    ],
}

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
    PLACEHOLDER_DIR.mkdir(parents=True, exist_ok=True)


def _split_sql_statements(script: str):
    statements = []
    current = []
    in_single = False
    in_double = False
    prev = ""
    for ch in script:
        if ch == "'" and not in_double and prev != "\\":
            in_single = not in_single
        elif ch == '"' and not in_single and prev != "\\":
            in_double = not in_double
        if ch == ";" and not in_single and not in_double:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(ch)
        prev = ch
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _run_sql_script(path: Path):
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    filtered_lines = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            filtered_lines.append(line)
            continue
        if stripped.startswith("--"):
            continue
        filtered_lines.append(line)
    script = "\n".join(filtered_lines)
    statements = _split_sql_statements(script)
    if not statements:
        return
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        connection.commit()


def ensure_database_schema():
    if not DB_AUTO_INIT:
        return
    if not SCHEMA_PATH.exists():
        app.logger.warning("DB schema file not found at %s", SCHEMA_PATH)
        return
    existing = fetch_all("SHOW TABLES")
    table_names = set()
    for row in existing:
        if row:
            table_names.update(row.values())
    if all(t in table_names for t in REQUIRED_TABLES):
        return
    app.logger.info("Applying DB schema from %s", SCHEMA_PATH)
    _run_sql_script(SCHEMA_PATH)
    app.logger.info("DB schema initialization complete.")


def _table_exists(table_name: str) -> bool:
    row = fetch_one(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """,
        (DB_CONFIG["database"], table_name),
    )
    return bool((row or {}).get("c"))


def _column_exists(table_name: str, column_name: str) -> bool:
    row = fetch_one(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (DB_CONFIG["database"], table_name, column_name),
    )
    return bool((row or {}).get("c"))


def ensure_additive_schema():
    # Safe additive changes for already-initialized databases.
    if not _table_exists("department"):
        execute(
            """
            CREATE TABLE department (
                id BIGINT NOT NULL AUTO_INCREMENT,
                name VARCHAR(128) NOT NULL,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                PRIMARY KEY (id),
                UNIQUE KEY uq_department_name (name),
                KEY idx_department_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

    if not _table_exists("job_title"):
        execute(
            """
            CREATE TABLE job_title (
                id BIGINT NOT NULL AUTO_INCREMENT,
                department_id BIGINT NOT NULL,
                name VARCHAR(128) NOT NULL,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                PRIMARY KEY (id),
                UNIQUE KEY uq_job_title_department_name (department_id, name),
                KEY idx_job_title_department (department_id),
                KEY idx_job_title_active (is_active),
                CONSTRAINT fk_job_title_department
                    FOREIGN KEY (department_id) REFERENCES department (id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

    if not _column_exists("user", "job_title"):
        execute("ALTER TABLE `user` ADD COLUMN job_title VARCHAR(128) DEFAULT NULL AFTER department")
        execute("ALTER TABLE `user` ADD KEY idx_user_job_title (job_title)")
    if not _column_exists("new_hire", "job_title"):
        execute("ALTER TABLE new_hire ADD COLUMN job_title VARCHAR(128) DEFAULT NULL AFTER department")
        execute("ALTER TABLE new_hire ADD KEY idx_new_hire_job_title (job_title)")

    for dep_name in DEFAULT_DEPARTMENTS:
        execute(
            """
            INSERT INTO department (name, is_active, created_at)
            VALUES (%s, 1, NOW())
            ON DUPLICATE KEY UPDATE is_active = VALUES(is_active)
            """,
            (dep_name,),
        )
    for dep_name, titles in DEFAULT_JOB_TITLES.items():
        dep = fetch_one("SELECT id FROM department WHERE LOWER(name)=LOWER(%s) LIMIT 1", (dep_name,))
        if not dep:
            continue
        dep_id = dep.get("id")
        for title in titles:
            execute(
                """
                INSERT INTO job_title (department_id, name, is_active, created_at)
                VALUES (%s, %s, 1, NOW())
                ON DUPLICATE KEY UPDATE is_active = VALUES(is_active)
                """,
                (dep_id, title),
            )


def ensure_placeholder_assets():
    """
    Create small placeholder PDF files so front-end links don't 404 when official PDFs
    are not yet uploaded. Safe to run repeatedly.
    """
    ensure_directories()
    PdfWriter = None
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = importlib.import_module(module_name)
            PdfWriter = getattr(module, "PdfWriter", None)
            if PdfWriter is not None:
                break
        except Exception:
            continue

    def write_pdf(path: Path, title: str):
        if PdfWriter is None:
            path.write_text(title, encoding="utf-8")
            return
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)  # Letter size; blank is fine for placeholder
        writer.add_metadata({"/Title": title})
        with path.open("wb") as f:
            writer.write(f)

    for rel_path, description in PLACEHOLDER_FILES:
        path = UPLOAD_DIR / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            write_pdf(path, description)


def enrich_document_record(doc: dict) -> dict:
    enriched = dict(doc or {})
    stored_name = (enriched.get("stored_name") or "").strip()
    original_name = (enriched.get("original_name") or stored_name or "document").strip()
    if stored_name:
        enriched["view_url"] = f"/uploads/{stored_name}"
        enriched["download_url"] = f"/uploads/{stored_name}?download=1&filename={quote_plus(original_name)}"
    else:
        enriched["view_url"] = ""
        enriched["download_url"] = ""
    return enriched


def email_is_valid(email: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email or ""))


def verify_user(identifier: str, plain_password: str) -> bool:
    identifier = (identifier or "").strip().lower()
    if not identifier or not plain_password:
        return False

    row = fetch_one("SELECT password_hash FROM `user` WHERE email = %s", (identifier,))
    if not row:
        return False
    stored = row["password_hash"]
    try:
        if check_password_hash(stored, plain_password):
            return True
    except (ValueError, TypeError):
        # fall through to legacy check
        pass

    # Legacy unsalted SHA-256 fallback (plain hex digest)
    legacy = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return legacy == stored


def get_user_record(email: str):
    if not email:
        return None
    return fetch_one(
        "SELECT email, full_name, role, department, job_title, created_at, avatar_url FROM `user` WHERE email = %s",
        (email,),
    )


def require_role(allowed_roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get("email"):
                if DEV_AUTOLOGIN_EMAIL:
                    session["email"] = DEV_AUTOLOGIN_EMAIL
                    session["role"] = DEV_AUTOLOGIN_ROLE or "employee"
                    ensure_csrf_token()
                else:
                    if should_redirect_to_login_page():
                        return redirect("/log_in.html")
                    return Response("Authentication required", status=401, mimetype="text/plain")
            role = session.get("role", "")
            if role not in allowed_roles:
                if should_redirect_to_login_page():
                    return redirect("/log_in.html")
                return Response("Forbidden", status=403, mimetype="text/plain")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def should_redirect_to_login_page() -> bool:
    """
    Only redirect for real page navigation requests.
    API/data routes should return 401/403 instead of HTML redirects.
    """
    path = request.path or ""
    if path.startswith("/api/") or path.startswith("/documents"):
        return False
    return request.method == "GET" and "text/html" in request.accept_mimetypes


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("email"):
            # Dev autologin fallback
            if DEV_AUTOLOGIN_EMAIL:
                session["email"] = DEV_AUTOLOGIN_EMAIL
                session["role"] = DEV_AUTOLOGIN_ROLE or "employee"
                ensure_csrf_token()
            else:
                if should_redirect_to_login_page():
                    return redirect("/log_in.html")
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
ensure_database_schema()
ensure_additive_schema()
ensure_placeholder_assets()


def create_user_record(email: str, hashed: str, full_name: str, role: str, department: str, job_title: str = ""):
    return {
        "id": secrets.token_hex(8),
        "email": email,
        "password_hash": hashed,
        "full_name": full_name,
        "role": role or "employee",
        "department": department,
        "job_title": (job_title or "").strip(),
        "status": "pending_hr_review",
        "created_at": datetime.utcnow(),
    }


def register_user_db(record: dict) -> bool:
    query = """
        INSERT INTO `user` (email, id, password_hash, full_name, role, department, job_title, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    record.get("job_title", ""),
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
    job_title = (request.form.get("job_title") or "").strip()
    role = (request.form.get("role") or "").strip() or "employee"

    if not full_name or not email or not password or not confirm:
        return Response("Missing required fields.", status=400, mimetype="text/plain")

    if not email_is_valid(email):
        return Response("Invalid email format.", status=400, mimetype="text/plain")

    if password != confirm:
        return Response("Passwords do not match.", status=400, mimetype="text/plain")

    if len(password) < 8:
        return Response("Password must be at least 8 characters.", status=400, mimetype="text/plain")
    if not department_and_title_are_valid(department, job_title):
        return Response("Invalid department/job title combination.", status=400, mimetype="text/plain")

    hashed = generate_password_hash(password)
    record = create_user_record(email, hashed, full_name, role, department, job_title)

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
    rows = fetch_all("SELECT email, full_name, role, department, job_title, status, created_at FROM `user`")
    cleaned = []
    for u in rows:
        cleaned.append(
            {
                "email": u.get("email"),
                "full_name": u.get("full_name") or "",
                "role": u.get("role") or "",
                "department": u.get("department") or "",
                "job_title": u.get("job_title") or "",
                "status": u.get("status") or "",
                "created_at": u.get("created_at") or "",
            }
        )
    return cleaned


def load_org_structure(active_only: bool = True):
    dep_where = "WHERE d.is_active = 1" if active_only else ""
    title_where = "AND jt.is_active = 1" if active_only else ""
    rows = fetch_all(
        f"""
        SELECT d.id AS department_id, d.name AS department_name,
               jt.id AS title_id, jt.name AS title_name
        FROM department d
        LEFT JOIN job_title jt ON jt.department_id = d.id {title_where}
        {dep_where}
        ORDER BY d.name ASC, jt.name ASC
        """
    )
    buckets = {}
    for row in rows:
        dep_id = row.get("department_id")
        if dep_id not in buckets:
            buckets[dep_id] = {
                "id": dep_id,
                "name": row.get("department_name") or "",
                "job_titles": [],
            }
        if row.get("title_id"):
            buckets[dep_id]["job_titles"].append(
                {"id": row.get("title_id"), "name": row.get("title_name") or ""}
            )
    return [buckets[k] for k in sorted(buckets, key=lambda x: (buckets[x]["name"] or "").lower())]


def department_and_title_are_valid(department_name: str, title_name: str) -> bool:
    if not title_name:
        return True
    if not department_name:
        return False
    row = fetch_one(
        """
        SELECT jt.id
        FROM department d
        JOIN job_title jt ON jt.department_id = d.id
        WHERE LOWER(d.name)=LOWER(%s) AND LOWER(jt.name)=LOWER(%s)
          AND d.is_active = 1 AND jt.is_active = 1
        LIMIT 1
        """,
        (department_name, title_name),
    )
    return bool(row)


def normalize_optional_date(value):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.") from exc
    return parsed.strftime("%Y-%m-%d")


def serialize_task_rows(rows):
    normalized = []
    for row in rows or []:
        item = dict(row or {})
        due = item.get("due_date")
        if due is None:
            item["due_date"] = None
        elif hasattr(due, "strftime"):
            item["due_date"] = due.strftime("%Y-%m-%d")
        else:
            item["due_date"] = str(due)
        normalized.append(item)
    return normalized


def get_user_role(email: str) -> str:
    if not email:
        return ""
    row = fetch_one("SELECT role FROM `user` WHERE email = %s", (email,))
    return (row or {}).get("role", "") or ""


def required_document_types_for_role(role: str):
    normalized = (role or "").strip().lower()
    # Registro de Comerciante is only required for contractors.
    contractor_only = {"merchant_registry"}
    filtered = []
    for doc in REQUIRED_DOCUMENT_TYPES:
        if doc.get("id") in contractor_only and normalized != "contractor":
            continue
        filtered.append(doc)
    return filtered


def normalize_optional_date_field(value, field_name: str):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name}. Use YYYY-MM-DD.") from exc
    return parsed.strftime("%Y-%m-%d")


def user_progress_snapshot(email: str, docs=None, tasks=None, policies=None, trainings=None, it_provisions=None, required_doc_types=None):
    docs = docs or []
    tasks = tasks or []
    policies = policies or []
    trainings = trainings or []
    it_provisions = it_provisions or []

    ud = [d for d in docs if d.get("uploader_email") == email]
    ut = [t for t in tasks if t.get("owner_email") == email]
    upol = [p for p in policies if p.get("email") == email]
    utr = [t for t in trainings if t.get("email") == email]
    uit = [p for p in it_provisions if p.get("email") == email]

    required_doc_types = required_doc_types or REQUIRED_DOCUMENT_TYPES
    required_doc_ids = [d["id"] for d in required_doc_types if not d.get("optional")]
    doc_status_by_type = {doc_id: "missing" for doc_id in required_doc_ids}
    for d in ud:
        dt = d.get("doc_type")
        if dt in doc_status_by_type:
            current = doc_status_by_type[dt]
            status = d.get("status", "pending_review")
            if status == "approved":
                doc_status_by_type[dt] = "approved"
            elif current != "approved":
                doc_status_by_type[dt] = status

    doc_total = len(required_doc_ids)
    doc_done = sum(1 for status in doc_status_by_type.values() if status == "approved")

    expected_checks = [
        {"key": "policy_ack", "label": "Policies acknowledged", "done": bool(upol)},
        {"key": "training", "label": "Training completed", "done": bool(utr)},
        {"key": "it_access", "label": "IT provisioning completed", "done": bool(uit)},
    ]
    extra_total = len(expected_checks)
    extra_done = sum(1 for item in expected_checks if item["done"])

    task_total = len(ut) + extra_total
    task_done = sum(1 for t in ut if t.get("status") == "completed") + extra_done

    total_items = doc_total + task_total
    completed = doc_done + task_done
    percentage = (completed / total_items * 100) if total_items else 0

    if doc_done == doc_total and task_done == task_total and task_total > 0:
        stage = "Completed"
    elif doc_done == doc_total:
        stage = "IT/Project/Training"
    elif doc_done:
        stage = "Documents"
    else:
        stage = "Account Created"

    return {
        "email": email,
        "documents": {"total": doc_total, "approved": doc_done},
        "tasks": {"total": task_total, "completed": task_done},
        "policies_signed": len(upol),
        "training_completed": len(utr),
        "it_provisioned": len(uit),
        "progress_percent": round(percentage, 2),
        "stage": stage,
    }


def hydrate_hires_with_context(hires, attachments, docs, tasks, policies, trainings, it_provisions, users_by_email=None):
    users_by_email = users_by_email or {}
    att_by_hire = {}
    for att in attachments:
        att_by_hire.setdefault(att["hire_id"], []).append(att)

    hydrated = []
    for hire in hires:
        item = dict(hire or {})
        email = (item.get("email") or "").lower()
        linked_user = users_by_email.get(email, {})
        item["attachments"] = att_by_hire.get(item.get("id"), [])
        item["avatar_url"] = linked_user.get("avatar_url") or ""
        if linked_user.get("full_name"):
            item["full_name"] = linked_user.get("full_name")
        if email:
            employment_type = (item.get("employment_type") or "").lower()
            item["progress"] = user_progress_snapshot(
                email,
                docs=docs,
                tasks=tasks,
                policies=policies,
                trainings=trainings,
                it_provisions=it_provisions,
                required_doc_types=required_document_types_for_role(employment_type),
            )
        hydrated.append(item)
    return hydrated


def load_tasks():
    return fetch_all("SELECT * FROM task")


def create_task_record(payload: dict) -> dict:
    due_date = payload.get("due_date")
    return {
        "id": secrets.token_hex(8),
        "title": payload.get("title", "").strip(),
        "description": payload.get("description", "").strip(),
        "owner_email": payload.get("owner_email", "").strip().lower(),
        "assigned_by": payload.get("assigned_by", "").strip().lower(),
        "category": payload.get("category", "employee"),
        "status": payload.get("status", "pending"),
        "due_date": due_date if due_date else None,
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

    return jsonify({"status": "ok", "documents": [enrich_document_record(doc) for doc in stored_entries]})


@app.get("/documents")
@login_required
def list_documents():
    email = (request.args.get("email") or "").strip().lower()
    requester = session.get("email")
    requester_role = session.get("role", "")
    if not email and requester_role == "employee":
        email = requester or ""
    if email and email != requester and requester_role not in {"hr", "manager", "compliance", "it"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if not email and requester_role not in {"hr", "manager", "compliance", "it"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if email:
        docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
    else:
        docs = fetch_all("SELECT * FROM document")
    return jsonify({"documents": [enrich_document_record(doc) for doc in docs]})


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

    try:
        payload["due_date"] = normalize_optional_date(payload.get("due_date"))
    except ValueError as exc:
        return Response(str(exc), status=400, mimetype="text/plain")

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
    return jsonify({"status": "ok", "task": serialize_task_rows([record])[0]})


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
    if not email and requester_role == "employee":
        email = requester or ""
        query += " AND owner_email = %s"
        params.append(email)
    if email and email != requester and requester_role not in {"hr", "manager", "it", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if not email and requester_role not in {"hr", "manager", "it", "compliance"}:
        return Response("Forbidden", status=403, mimetype="text/plain")

    tasks = fetch_all(query, params)
    return jsonify({"tasks": serialize_task_rows(tasks)})


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
    requester = session.get("email")
    requester_role = session.get("role", "")
    if not email and requester_role == "employee":
        email = requester or ""
    if email:
        docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
        tasks = fetch_all("SELECT * FROM task WHERE owner_email = %s", (email,))
        it_provisions = fetch_all("SELECT * FROM it_provision WHERE email = %s", (email,))
    else:
        docs = fetch_all("SELECT * FROM document")
        tasks = fetch_all("SELECT * FROM task")
        it_provisions = fetch_all("SELECT * FROM it_provision")

    def user_progress(e):
        role = get_user_role(e)
        required_doc_types = required_document_types_for_role(role)
        return user_progress_snapshot(
            e,
            docs=docs,
            tasks=tasks,
            policies=fetch_all("SELECT * FROM policy_ack"),
            trainings=fetch_all("SELECT * FROM training_completion"),
            it_provisions=it_provisions,
            required_doc_types=required_doc_types,
        )

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
    if not email and requester_role == "employee":
        email = requester or ""
    if email and email != requester and requester_role not in {"hr", "manager", "compliance", "it"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if not email and requester_role not in {"hr", "manager", "compliance", "it"}:
        return Response("Forbidden", status=403, mimetype="text/plain")
    if email:
        docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
    else:
        docs = fetch_all("SELECT * FROM document")
    target_role = get_user_role(email) if email else ""
    effective_doc_types = required_document_types_for_role(target_role) if email else REQUIRED_DOCUMENT_TYPES
    by_type = {}
    for doc_type in effective_doc_types:
        by_type[doc_type["id"]] = {
            "id": doc_type["id"],
            "label": doc_type["label"],
            "optional": bool(doc_type.get("optional")),
            "status": "missing",
            "documents": [],
            "last_updated": None,
        }

    requester = session.get("email")
    requester_role = session.get("role", "")

    for doc in docs:
        if email and doc.get("uploader_email") != email and requester_role not in {"hr", "manager", "compliance"}:
            continue
        dt = doc.get("doc_type")
        if dt and dt in by_type:
            bucket = by_type[dt]
            bucket["documents"].append(enrich_document_record(doc))
            uploaded_at = doc.get("uploaded_at")
            if uploaded_at:
                bucket["last_updated"] = max(bucket["last_updated"], uploaded_at) if bucket["last_updated"] else uploaded_at
            if doc.get("status") == "approved":
                bucket["status"] = "approved"
            elif bucket["status"] != "approved":
                bucket["status"] = doc.get("status", "pending_review")

    return jsonify({"requirements": list(by_type.values())})


@app.post("/login")
def login():
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""

    try:
        is_valid = verify_user(username, password)
    except Exception as exc:
        app.logger.error("Login error: %s", exc, exc_info=True)
        return Response("Internal Server Error", status=500, mimetype="text/plain")

    if is_valid:
        user = get_user_record(username) or {}
        role = (user.get("role") or "employee").lower()
        session["email"] = username
        session["role"] = role
        ensure_csrf_token()
        if role in ADMIN_ROLES:
            target = "/admin_panel.html?login=success"
        else:
            target = f"/dashboard.html?email={quote_plus(username)}&login=success"
        return redirect(target, code=302)

    return redirect("/log_in.html?error=invalid_credentials", code=302)


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
        "job_title": record.get("job_title") or "",
        "created_at": record.get("created_at") or record.get("createdAt") or "",
        "avatar_url": record.get("avatar_url") or "",
    }
    return jsonify(payload)


@app.get("/api/session")
@login_required
def get_session_info():
    email = (session.get("email") or "").strip().lower()
    role = (session.get("role") or "").strip().lower()
    user = get_user_record(email) or {}
    return jsonify(
        {
            "email": email,
            "role": role,
            "full_name": user.get("full_name") or email,
            "department": user.get("department") or "",
            "job_title": user.get("job_title") or "",
            "created_at": user.get("created_at") or "",
            "avatar_url": user.get("avatar_url") or "",
        }
    )


@app.get("/api/users")
@login_required
@require_role({"hr", "manager", "compliance", "it"})
def get_users():
    role_filter = (request.args.get("role") or "").strip().lower()
    users = list_users()
    if role_filter:
        users = [u for u in users if (u.get("role") or "").lower() == role_filter]
    return jsonify({"users": users})


@app.get("/api/org/structure")
def get_org_structure():
    departments = load_org_structure(active_only=True)
    return jsonify({"departments": departments})


@app.post("/api/org/departments")
@require_role({"hr", "manager"})
def create_department():
    name = (request.form.get("name") or "").strip()
    if not name:
        return Response("Department name is required.", status=400, mimetype="text/plain")
    execute(
        """
        INSERT INTO department (name, is_active, created_at)
        VALUES (%s, 1, NOW())
        ON DUPLICATE KEY UPDATE is_active = VALUES(is_active)
        """,
        (name,),
    )
    append_audit("department_create", session.get("email", ""), {"name": name})
    return jsonify({"status": "ok", "departments": load_org_structure(active_only=True)})


@app.post("/api/org/job-titles")
@require_role({"hr", "manager"})
def create_job_title():
    title = (request.form.get("title") or "").strip()
    dep_id_raw = (request.form.get("department_id") or "").strip()
    dep_name = (request.form.get("department") or "").strip()
    if not title:
        return Response("Job title is required.", status=400, mimetype="text/plain")

    dep = None
    if dep_id_raw.isdigit():
        dep = fetch_one("SELECT id, name FROM department WHERE id = %s", (int(dep_id_raw),))
    if not dep and dep_name:
        dep = fetch_one("SELECT id, name FROM department WHERE LOWER(name)=LOWER(%s) LIMIT 1", (dep_name,))
    if not dep:
        return Response("Valid department is required.", status=400, mimetype="text/plain")

    execute(
        """
        INSERT INTO job_title (department_id, name, is_active, created_at)
        VALUES (%s, %s, 1, NOW())
        ON DUPLICATE KEY UPDATE is_active = VALUES(is_active)
        """,
        (dep.get("id"), title),
    )
    append_audit(
        "job_title_create",
        session.get("email", ""),
        {"department_id": dep.get("id"), "department": dep.get("name"), "title": title},
    )
    return jsonify({"status": "ok", "departments": load_org_structure(active_only=True)})


@app.post("/api/policy/ack")
@login_required
def policy_ack():
    session_email = (session.get("email") or "").strip().lower()
    email = (request.form.get("email") or "").strip().lower()
    policy_id = (request.form.get("policy_id") or "").strip()
    signature = (request.form.get("signature") or "").strip()
    if not session_email:
        return Response("Authentication required", status=401, mimetype="text/plain")
    if not policy_id or not signature:
        return Response("policy_id and signature are required.", status=400, mimetype="text/plain")
    if email and email != session_email:
        return Response("Forbidden", status=403, mimetype="text/plain")
    execute(
        """
        INSERT INTO policy_ack (id, email, policy_id, signature, status, signed_at)
        VALUES (%s,%s,%s,%s,%s,NOW())
        ON DUPLICATE KEY UPDATE
            signature = VALUES(signature),
            status = VALUES(status),
            signed_at = VALUES(signed_at)
        """,
        (secrets.token_hex(8), session_email, policy_id, signature, "signed"),
    )
    append_audit("policy_ack", session_email, {"policy_id": policy_id})
    return jsonify({"status": "ok", "email": session_email})


@app.get("/api/policy/status")
@login_required
def policy_status():
    email = (request.args.get("email") or "").strip().lower()
    session_email = (session.get("email") or "").strip().lower()
    requester_role = session.get("role", "")
    if email:
        if email != session_email and requester_role not in {"hr", "manager", "compliance"}:
            return Response("Forbidden", status=403, mimetype="text/plain")
        policies = fetch_all("SELECT * FROM policy_ack WHERE email = %s", (email,))
    else:
        if requester_role in {"hr", "manager", "compliance"}:
            policies = fetch_all("SELECT * FROM policy_ack")
        else:
            policies = fetch_all("SELECT * FROM policy_ack WHERE email = %s", (session_email,))
    return jsonify({"policies": policies})


@app.get("/api/onboarding/blueprint")
@login_required
def onboarding_blueprint():
    """
    Lightweight API that returns the onboarding flow captured in the UPRA questionnaire.
    Includes required documents and placeholder file URLs so the front end can link without 404s.
    """
    placeholders = []
    for rel_path, _ in PLACEHOLDER_FILES:
        placeholders.append({"path": f"/uploads/{rel_path}", "exists": (UPLOAD_DIR / rel_path).exists()})
    # Deep-ish copy to avoid accidental mutation of the global constant
    blueprint = json.loads(json.dumps(ONBOARDING_BLUEPRINT))
    blueprint["placeholders"] = placeholders
    return jsonify(blueprint)


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


@app.get("/api/admin/metrics")
@require_role({"hr", "manager", "compliance", "it"})
def admin_metrics():
    hires = fetch_all("SELECT id, email, status, employment_type, created_at FROM new_hire")
    docs = fetch_all("SELECT uploader_email, status, uploaded_at FROM document")
    tasks = fetch_all("SELECT owner_email, status FROM task")
    policies = fetch_all("SELECT email FROM policy_ack")
    trainings = fetch_all("SELECT email FROM training_completion")
    it_provisions = fetch_all("SELECT email FROM it_provision")

    stage_counts = {}
    status_counts = {}
    employment_counts = {"employee": 0, "contractor": 0}
    progress_values = []
    age_days = []
    now_utc = datetime.utcnow()

    for hire in hires:
        email = (hire.get("email") or "").lower()
        if not email:
            continue
        employment_type = (hire.get("employment_type") or "employee").lower()
        if employment_type not in employment_counts:
            employment_counts[employment_type] = 0
        employment_counts[employment_type] += 1

        status = (hire.get("status") or "unknown").lower()
        status_counts[status] = status_counts.get(status, 0) + 1

        progress = user_progress_snapshot(
            email,
            docs=docs,
            tasks=tasks,
            policies=policies,
            trainings=trainings,
            it_provisions=it_provisions,
            required_doc_types=required_document_types_for_role(employment_type),
        )
        stage = progress.get("stage") or "Unknown"
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        progress_values.append(float(progress.get("progress_percent") or 0))

        created_at = hire.get("created_at")
        if created_at:
            try:
                created_dt = created_at if hasattr(created_at, "timestamp") else datetime.fromisoformat(str(created_at))
                age = (now_utc - created_dt).total_seconds() / 86400
                if age >= 0:
                    age_days.append(age)
            except Exception:
                pass

    total_hires = len([h for h in hires if (h.get("email") or "").strip()])
    approved_docs = sum(1 for d in docs if d.get("status") == "approved")
    pending_docs = sum(1 for d in docs if d.get("status") == "pending_review")
    rejected_docs = sum(1 for d in docs if d.get("status") == "rejected")
    completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
    blocked_tasks = sum(1 for t in tasks if t.get("status") == "blocked")

    avg_progress = round(sum(progress_values) / len(progress_values), 2) if progress_values else 0
    avg_onboarding_days = round(sum(age_days) / len(age_days), 2) if age_days else 0

    return jsonify(
        {
            "totals": {
                "new_hires": total_hires,
                "documents": len(docs),
                "documents_approved": approved_docs,
                "documents_pending_review": pending_docs,
                "documents_rejected": rejected_docs,
                "tasks": len(tasks),
                "tasks_completed": completed_tasks,
                "tasks_blocked": blocked_tasks,
                "policy_signatures": len(policies),
                "training_completions": len(trainings),
                "it_provisions": len(it_provisions),
            },
            "distribution": {
                "stage": stage_counts,
                "status": status_counts,
                "employment_type": employment_counts,
            },
            "kpis": {
                "average_progress_percent": avg_progress,
                "average_days_since_hire_created": avg_onboarding_days,
            },
        }
    )


@app.get("/api/new-hires")
@require_role({"hr", "manager", "compliance", "it"})
def list_new_hires():
    hires = fetch_all("SELECT * FROM new_hire")
    attachments = fetch_all("SELECT * FROM new_hire_attachment")
    docs = fetch_all("SELECT * FROM document")
    tasks = fetch_all("SELECT * FROM task")
    policies = fetch_all("SELECT * FROM policy_ack")
    trainings = fetch_all("SELECT * FROM training_completion")
    it_provisions = fetch_all("SELECT * FROM it_provision")
    users = fetch_all("SELECT email, full_name, avatar_url FROM `user`")
    users_by_email = {(u.get("email") or "").lower(): u for u in users}
    hydrated = hydrate_hires_with_context(
        hires,
        attachments,
        docs,
        tasks,
        policies,
        trainings,
        it_provisions,
        users_by_email=users_by_email,
    )
    return jsonify({"hires": hydrated})


@app.get("/api/new-hires/<hire_id>")
@require_role({"hr", "manager", "compliance", "it"})
def get_new_hire_detail(hire_id):
    hire = fetch_one("SELECT * FROM new_hire WHERE id = %s", (hire_id,))
    if not hire:
        return Response("New hire not found.", status=404, mimetype="text/plain")

    attachments = fetch_all("SELECT * FROM new_hire_attachment WHERE hire_id = %s", (hire_id,))
    email = (hire.get("email") or "").lower()
    docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,)) if email else []
    tasks = fetch_all("SELECT * FROM task WHERE owner_email = %s", (email,)) if email else []
    policies = fetch_all("SELECT * FROM policy_ack WHERE email = %s", (email,)) if email else []
    trainings = fetch_all("SELECT * FROM training_completion WHERE email = %s", (email,)) if email else []
    it_provisions = fetch_all("SELECT * FROM it_provision WHERE email = %s", (email,)) if email else []
    user = fetch_one("SELECT email, full_name, avatar_url FROM `user` WHERE email = %s", (email,)) if email else {}
    users_by_email = {email: user} if email else {}

    hydrated = hydrate_hires_with_context(
        [hire],
        attachments,
        docs,
        tasks,
        policies,
        trainings,
        it_provisions,
        users_by_email=users_by_email,
    )
    payload = hydrated[0] if hydrated else {}
    payload["documents"] = [enrich_document_record(d) for d in docs]
    payload["tasks"] = serialize_task_rows(tasks)
    payload["policies"] = policies
    payload["trainings"] = trainings
    payload["it_provisions"] = it_provisions
    return jsonify(payload)


@app.post("/api/new-hires/<hire_id>")
@require_role({"hr"})
def update_new_hire(hire_id):
    existing = fetch_one("SELECT id, email FROM new_hire WHERE id = %s", (hire_id,))
    if not existing:
        return Response("New hire not found.", status=404, mimetype="text/plain")

    payload = {
        "first_name": (request.form.get("first_name") or "").strip(),
        "middle_name": (request.form.get("middle_name") or "").strip(),
        "last_name": (request.form.get("last_name") or "").strip(),
        "phone": (request.form.get("phone") or "").strip(),
        "gov_id": (request.form.get("gov_id") or "").strip(),
        "street": (request.form.get("street") or "").strip(),
        "city": (request.form.get("city") or "").strip(),
        "state": (request.form.get("state") or "").strip(),
        "postal_code": (request.form.get("postal_code") or "").strip(),
        "country": (request.form.get("country") or "").strip(),
        "department": (request.form.get("department") or "").strip(),
        "job_title": (request.form.get("job_title") or "").strip(),
        "manager": (request.form.get("manager") or "").strip(),
        "status": (request.form.get("status") or "").strip(),
        "employment_type": (request.form.get("employment_type") or "").strip().lower(),
    }
    if payload["employment_type"] not in {"employee", "contractor"}:
        return Response("Invalid employment_type. Must be employee or contractor.", status=400, mimetype="text/plain")
    if not department_and_title_are_valid(payload["department"], payload["job_title"]):
        return Response("Invalid department/job title combination.", status=400, mimetype="text/plain")

    try:
        dob = normalize_optional_date_field(request.form.get("dob"), "dob")
        start_date = normalize_optional_date_field(request.form.get("start_date"), "start_date")
    except ValueError as exc:
        return Response(str(exc), status=400, mimetype="text/plain")

    execute(
        """
        UPDATE new_hire
        SET first_name = %s,
            middle_name = %s,
            last_name = %s,
            phone = %s,
            dob = %s,
            gov_id = %s,
            street = %s,
            city = %s,
            state = %s,
            postal_code = %s,
            country = %s,
            employment_type = %s,
            department = %s,
            job_title = %s,
            manager = %s,
            start_date = %s,
            status = %s
        WHERE id = %s
        """,
        (
            payload["first_name"],
            payload["middle_name"],
            payload["last_name"],
            payload["phone"],
            dob,
            payload["gov_id"],
            payload["street"],
            payload["city"],
            payload["state"],
            payload["postal_code"],
            payload["country"],
            payload["employment_type"],
            payload["department"],
            payload["job_title"],
            payload["manager"],
            start_date,
            payload["status"] or "pending_document_submission",
            hire_id,
        ),
    )

    email = (existing.get("email") or "").strip().lower()
    full_name = " ".join(part for part in [payload["first_name"], payload["middle_name"], payload["last_name"]] if part).strip()
    if email:
        execute(
            "UPDATE `user` SET full_name = %s, role = %s, department = %s, job_title = %s WHERE email = %s",
            (full_name or email, payload["employment_type"], payload["department"], payload["job_title"], email),
        )

    append_audit(
        "hire_update",
        session.get("email", ""),
        {"hire_id": hire_id, "email": email, "updated_fields": list(payload.keys()) + ["dob", "start_date"]},
    )
    return jsonify({"status": "ok", "hire_id": hire_id})


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
    required_fields = ["first_name", "last_name", "email", "employment_type", "department", "job_title", "temp_password"]
    for field in required_fields:
        if not data.get(field):
            return Response(f"{field} is required.", status=400, mimetype="text/plain")

    email = data.get("email").strip().lower()
    if not email_is_valid(email):
        return Response("Invalid email.", status=400, mimetype="text/plain")
    temp_password = data.get("temp_password") or ""
    if len(temp_password) < 8:
        return Response("Temporary password must be at least 8 characters.", status=400, mimetype="text/plain")
    if fetch_one("SELECT email FROM `user` WHERE email = %s", (email,)):
        return Response("A user with this email already exists.", status=409, mimetype="text/plain")

    hire_id = secrets.token_hex(8)
    first = data.get("first_name", "").strip()
    middle = data.get("middle_name", "").strip()
    last = data.get("last_name", "").strip()
    full_name = " ".join(part for part in [first, middle, last] if part).strip()
    employment_type = (data.get("employment_type") or "").strip().lower()
    if employment_type not in {"employee", "contractor"}:
        return Response("Invalid employment_type. Must be employee or contractor.", status=400, mimetype="text/plain")
    department = data.get("department", "").strip()
    job_title = data.get("job_title", "").strip()
    if not department_and_title_are_valid(department, job_title):
        return Response("Invalid department/job title combination.", status=400, mimetype="text/plain")

    execute(
        """
        INSERT INTO new_hire (
            id, first_name, middle_name, last_name, email, phone, dob, gov_id,
            street, city, state, postal_code, country, employment_type, department, job_title, manager,
            start_date, status, created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        """,
        (
            hire_id,
            first,
            middle,
            last,
            email,
            data.get("phone", "").strip(),
            data.get("dob", None) or None,
            data.get("gov_id", "").strip(),
            data.get("street", "").strip(),
            data.get("city", "").strip(),
            data.get("state", "").strip(),
            data.get("postal_code", "").strip(),
            data.get("country", "").strip(),
            employment_type,
            department,
            job_title,
            data.get("manager", "").strip(),
            data.get("start_date", None) or None,
            "pending_document_submission",
        ),
    )
    try:
        register_user_db(
            create_user_record(
                email=email,
                hashed=generate_password_hash(temp_password),
                full_name=full_name or email,
                role=employment_type,
                department=department,
                job_title=job_title,
            )
        )
    except pymysql.err.IntegrityError:
        return Response("A user with this email already exists.", status=409, mimetype="text/plain")

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
                """
                INSERT INTO new_hire_attachment (hire_id, att_type, original_name, stored_name, url)
                VALUES (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    original_name = VALUES(original_name),
                    stored_name = VALUES(stored_name),
                    url = VALUES(url)
                """,
                (hire_id, att["id"], f.filename, stored, f"/uploads/hires/{stored}"),
            )

    append_audit(
        "hire_register",
        session.get("email", ""),
        {"hire_id": hire_id, "email": email, "employment_type": employment_type},
    )
    return jsonify({"status": "ok", "hire_id": hire_id, "account_created": True})


def serve_frontend(asset_path: str):
    if not FRONT_END_DIR.exists():
        return Response("Front-end directory missing", status=500, mimetype="text/plain")
    
    return send_from_directory(FRONT_END_DIR, asset_path)


@app.get("/")
def root():
    return serve_frontend("log_in.html")


@app.get("/log_in.html")
def login_page():
    # Keep login page explicitly public and directly reachable.
    return serve_frontend("log_in.html")


@app.get("/admin_panel")
def admin_panel_alias():
    return redirect("/admin_panel.html", code=302)


@app.get("/admin_hire_detail")
def admin_hire_detail_alias():
    hire_id = (request.args.get("hire_id") or "").strip()
    if hire_id:
        return redirect(f"/admin_hire_detail.html?hire_id={quote_plus(hire_id)}", code=302)
    return redirect("/admin_hire_detail.html", code=302)


@app.get("/admin_metrics")
def admin_metrics_alias():
    return redirect("/admin_metrics.html", code=302)


@app.get("/dashboard")
def dashboard_alias():
    email = (request.args.get("email") or "").strip()
    if email:
        return redirect(f"/dashboard.html?email={quote_plus(email)}", code=302)
    return redirect("/dashboard.html", code=302)


@app.get("/profile")
def profile_alias():
    email = (request.args.get("email") or "").strip()
    if email:
        return redirect(f"/profile.html?email={quote_plus(email)}", code=302)
    return redirect("/profile.html", code=302)


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
    download_requested = (request.args.get("download") or "").strip().lower() in {"1", "true", "yes"}
    filename = (request.args.get("filename") or "").strip() or Path(asset_path).name
    if download_requested:
        return send_from_directory(UPLOAD_DIR, asset_path, as_attachment=True, download_name=filename)
    return send_from_directory(UPLOAD_DIR, asset_path)


@app.get("/<path:asset_path>")
def static_assets(asset_path):
    return serve_frontend(asset_path)


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)


@app.errorhandler(401)
@app.errorhandler(403)
def handle_auth_errors(err):
    # For browser requests, serve the public login page directly.
    if should_redirect_to_login_page():
        return serve_frontend("log_in.html")
    return Response(err.description if hasattr(err, "description") else "Forbidden", status=err.code, mimetype="text/plain")
