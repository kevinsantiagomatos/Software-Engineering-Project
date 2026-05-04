import hashlib
import importlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, request, Response, jsonify, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from urllib.parse import quote_plus
import pymysql
from core.db import execute, fetch_all, fetch_one, get_db_connection
from core.security import (
    csrf_protect_request,
    ensure_csrf_token,
    login_required,
    require_role,
    should_redirect_to_login_page,
)
from core.settings import (
    BACKEND_DIR,
    DATA_DIR,
    DB_AUTO_INIT,
    DB_CONFIG,
    FRONT_END_DIR,
    HIRES_DIR,
    HOST,
    PLACEHOLDER_DIR,
    PORT,
    PROFILE_DIR,
    SCHEMA_PATH,
    STYLE_DIR,
    UPLOAD_DIR,
)
from routes.admin_routes import register_admin_routes
from routes.auth_routes import register_auth_routes
from routes.document_routes import register_document_routes
from routes.hire_routes import register_hire_routes
from routes.it_access_routes import register_it_access_routes
from routes.page_routes import register_page_routes
from routes.task_routes import register_task_routes
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
DEPARTMENT_ADMIN_ROLES = {"hr", "it", "compliance"}
SUPERADMIN_ROLE = "superadmin"
ROLE_CATEGORIES = {"employee", "contractor", "manager", "admin", "superadmin"}
TASK_CATEGORIES = {"employee", "contractor", "manager", "admin", "hr", "it", "compliance"}
ADMIN_ROLES = {"admin", "manager", SUPERADMIN_ROLE}
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
IT_ACCESS_STATE_NOT_CONFIGURED = "not_configured"
IT_ACCESS_STATE_PENDING = "configured_pending_confirmation"
IT_ACCESS_STATE_CONFIRMED = "configured_confirmed"
IT_ACCESS_STATE_DECLINED = "configured_declined"
IT_ACCESS_STATE_ERROR = "configured_error"
IT_ACCESS_STATES = {
    IT_ACCESS_STATE_NOT_CONFIGURED,
    IT_ACCESS_STATE_PENDING,
    IT_ACCESS_STATE_CONFIRMED,
    IT_ACCESS_STATE_DECLINED,
    IT_ACCESS_STATE_ERROR,
}
IT_ACCESS_TEMPLATE_KEY_ORDER = [
    item.get("id")
    for item in (ONBOARDING_BLUEPRINT.get("integration", {}).get("operations_it", {}).get("checklist", []) or [])
    if (item.get("id") or "").strip()
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
    if not _table_exists("role"):
        execute(
            """
            CREATE TABLE role (
                id BIGINT NOT NULL AUTO_INCREMENT,
                name VARCHAR(64) NOT NULL,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                PRIMARY KEY (id),
                UNIQUE KEY uq_role_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

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
    if not _column_exists("user", "role_id"):
        execute("ALTER TABLE `user` ADD COLUMN role_id BIGINT NULL AFTER role")
        execute("ALTER TABLE `user` ADD KEY idx_user_role_id (role_id)")
    if not _column_exists("user", "department_id"):
        execute("ALTER TABLE `user` ADD COLUMN department_id BIGINT NULL AFTER department")
        execute("ALTER TABLE `user` ADD KEY idx_user_department_id (department_id)")
    if not _table_exists("hire_document_slot"):
        execute(
            """
            CREATE TABLE hire_document_slot (
                id BIGINT NOT NULL AUTO_INCREMENT,
                hire_id VARCHAR(64) NOT NULL,
                doc_type VARCHAR(64) NOT NULL,
                label VARCHAR(255) NOT NULL,
                optional TINYINT(1) NOT NULL DEFAULT 0,
                created_by VARCHAR(255) DEFAULT NULL,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                PRIMARY KEY (id),
                UNIQUE KEY uq_hire_doc_slot_type (hire_id, doc_type),
                KEY idx_hire_doc_slot_hire_active (hire_id, is_active),
                CONSTRAINT fk_hire_doc_slot_hire
                    FOREIGN KEY (hire_id) REFERENCES new_hire (id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

    if not _table_exists("it_access_item"):
        execute(
            """
            CREATE TABLE it_access_item (
                id BIGINT NOT NULL AUTO_INCREMENT,
                email VARCHAR(255) NOT NULL,
                access_key VARCHAR(64) NOT NULL,
                access_title VARCHAR(255) NOT NULL,
                state VARCHAR(48) NOT NULL DEFAULT 'not_configured',
                details TEXT DEFAULT NULL,
                portal_url VARCHAR(512) DEFAULT NULL,
                username_hint VARCHAR(255) DEFAULT NULL,
                notes TEXT DEFAULT NULL,
                configured_by VARCHAR(255) DEFAULT NULL,
                configured_at DATETIME(6) DEFAULT NULL,
                hire_response_note TEXT DEFAULT NULL,
                hire_response_at DATETIME(6) DEFAULT NULL,
                created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                updated_by VARCHAR(255) DEFAULT NULL,
                PRIMARY KEY (id),
                UNIQUE KEY uq_it_access_email_key (email, access_key),
                KEY idx_it_access_email_state (email, state),
                KEY idx_it_access_email_updated (email, updated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

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

    for role_name in ("employee", "contractor", "manager", "admin", "superadmin"):
        execute(
            """
            INSERT INTO role (name, is_active, created_at)
            VALUES (%s, 1, NOW())
            ON DUPLICATE KEY UPDATE is_active = VALUES(is_active)
            """,
            (role_name,),
        )

    # Normalize legacy role values into canonical model.
    execute(
        """
        UPDATE `user`
        SET role = CASE
            WHEN LOWER(role) IN ('hr','it','compliance') THEN 'admin'
            WHEN LOWER(role) IN ('employee','contractor','manager','admin','superadmin') THEN LOWER(role)
            ELSE 'employee'
        END
        """
    )

    # Set department for legacy departmental admins when not set.
    execute("UPDATE `user` SET department = 'HR' WHERE LOWER(role)='admin' AND (department IS NULL OR department='') AND LOWER(email) LIKE %s", ("%hr%",))
    execute("UPDATE `user` SET department = 'IT' WHERE LOWER(role)='admin' AND (department IS NULL OR department='') AND LOWER(email) LIKE %s", ("%it%",))
    execute("UPDATE `user` SET department = 'Compliance' WHERE LOWER(role)='admin' AND (department IS NULL OR department='') AND LOWER(email) LIKE %s", ("%compliance%",))

    execute(
        """
        UPDATE `user` u
        LEFT JOIN role r ON LOWER(r.name) = LOWER(u.role)
        SET u.role_id = r.id
        WHERE u.role_id IS NULL OR u.role_id = 0
        """
    )
    execute(
        """
        UPDATE `user` u
        LEFT JOIN department d ON LOWER(d.name) = LOWER(u.department)
        SET u.department_id = d.id
        WHERE u.department_id IS NULL OR u.department_id = 0
        """
    )
    execute(
        """
        UPDATE `user`
        SET department_id = NULL, department = NULL
        WHERE LOWER(role) = 'superadmin'
        """
    )

    # Backfill granular IT access checklist from legacy coarse it_provision records.
    if _table_exists("it_provision"):
        legacy_it_rows = fetch_all(
            """
            SELECT DISTINCT LOWER(email) AS email
            FROM it_provision
            WHERE email IS NOT NULL AND email <> ''
            """
        )
        template_items = ONBOARDING_BLUEPRINT.get("integration", {}).get("operations_it", {}).get("checklist", []) or []
        template_map = {
            (item.get("id") or "").strip().lower(): (item.get("title") or "IT Access").strip()
            for item in template_items
            if (item.get("id") or "").strip()
        }
        for row in legacy_it_rows:
            legacy_email = (row.get("email") or "").strip().lower()
            if not legacy_email:
                continue
            for access_key, access_title in template_map.items():
                execute(
                    """
                    INSERT INTO it_access_item (
                        email, access_key, access_title, state, configured_by, configured_at, hire_response_at, created_at, updated_at, updated_by
                    )
                    VALUES (%s, %s, %s, %s, %s, NOW(6), NOW(6), NOW(6), NOW(6), %s)
                    ON DUPLICATE KEY UPDATE access_title = VALUES(access_title)
                    """,
                    (
                        legacy_email,
                        access_key,
                        access_title,
                        IT_ACCESS_STATE_CONFIRMED,
                        "legacy_migration",
                        "legacy_migration",
                    ),
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
        """
        SELECT
            u.email,
            u.full_name,
            COALESCE(r.name, u.role) AS role,
            COALESCE(d.name, u.department) AS department,
            u.job_title,
            u.created_at,
            u.avatar_url
        FROM `user` u
        LEFT JOIN role r ON r.id = u.role_id
        LEFT JOIN department d ON d.id = u.department_id
        WHERE u.email = %s
        """,
        (email,),
    )

@app.before_request
def csrf_protect():
    return csrf_protect_request()


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
    canonical_role, canonical_department = canonicalize_role_and_department(role, department)
    return {
        "id": secrets.token_hex(8),
        "email": email,
        "password_hash": hashed,
        "full_name": full_name,
        "role": canonical_role,
        "department": canonical_department,
        "role_id": get_role_id(canonical_role),
        "department_id": get_department_id(canonical_department),
        "job_title": (job_title or "").strip(),
        "status": "pending_hr_review",
        "created_at": datetime.utcnow(),
    }


def register_user_db(record: dict) -> bool:
    query = """
        INSERT INTO `user` (email, id, password_hash, full_name, role, role_id, department, department_id, job_title, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    record.get("role_id"),
                    record["department"],
                    record.get("department_id"),
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
    role, department = canonicalize_role_and_department(role, department)

    if not full_name or not email or not password or not confirm:
        return Response("Missing required fields.", status=400, mimetype="text/plain")

    if not email_is_valid(email):
        return Response("Invalid email format.", status=400, mimetype="text/plain")

    if password != confirm:
        return Response("Passwords do not match.", status=400, mimetype="text/plain")

    if len(password) < 8:
        return Response("Password must be at least 8 characters.", status=400, mimetype="text/plain")
    if role != SUPERADMIN_ROLE and not department_and_title_are_valid(department, job_title):
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
    rows = fetch_all(
        """
        SELECT
            u.email,
            u.full_name,
            COALESCE(r.name, u.role) AS role,
            COALESCE(d.name, u.department) AS department,
            u.job_title,
            u.status,
            u.created_at
        FROM `user` u
        LEFT JOIN role r ON r.id = u.role_id
        LEFT JOIN department d ON d.id = u.department_id
        """
    )
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


def canonicalize_role_and_department(role: str, department: str):
    role_normalized = (role or "").strip().lower() or "employee"
    department_name = (department or "").strip()
    legacy_admin_map = {"hr": "HR", "it": "IT", "compliance": "Compliance"}
    if role_normalized in legacy_admin_map:
        return "admin", (department_name or legacy_admin_map[role_normalized]).strip()
    if role_normalized not in ROLE_CATEGORIES:
        role_normalized = "employee"
    if role_normalized == SUPERADMIN_ROLE:
        return SUPERADMIN_ROLE, ""
    if role_normalized == "admin" and not department_name:
        department_name = "HR"
    return role_normalized, department_name


def get_role_id(role_name: str):
    row = fetch_one("SELECT id FROM role WHERE LOWER(name)=LOWER(%s) LIMIT 1", ((role_name or "").strip().lower(),))
    return (row or {}).get("id")


def get_department_id(department_name: str):
    if not department_name:
        return None
    row = fetch_one("SELECT id FROM department WHERE LOWER(name)=LOWER(%s) LIMIT 1", ((department_name or "").strip(),))
    return (row or {}).get("id")


def session_department_name() -> str:
    return (session.get("department") or "").strip().lower()


def can_view_documents_admin() -> bool:
    role = (session.get("role") or "").strip().lower()
    department = session_department_name()
    return role == SUPERADMIN_ROLE or role == "manager" or (role == "admin" and department in {"hr", "compliance"})


def can_manage_documents_admin() -> bool:
    role = (session.get("role") or "").strip().lower()
    department = session_department_name()
    return role == SUPERADMIN_ROLE or (role == "admin" and department in {"hr", "compliance"})


def can_manage_hiring_admin() -> bool:
    role = (session.get("role") or "").strip().lower()
    department = session_department_name()
    return role == SUPERADMIN_ROLE or role == "manager" or (role == "admin" and department == "hr")


def can_view_it_access_admin() -> bool:
    role = (session.get("role") or "").strip().lower()
    department = session_department_name()
    return role == SUPERADMIN_ROLE or role == "manager" or (role == "admin" and department in {"hr", "it", "compliance"})


def can_manage_it_access_admin() -> bool:
    role = (session.get("role") or "").strip().lower()
    department = session_department_name()
    return role == SUPERADMIN_ROLE or (role == "admin" and department == "it")


def task_category_allowed_for_current_admin(category: str) -> bool:
    role = (session.get("role") or "").strip().lower()
    department = session_department_name()
    normalized = (category or "").strip().lower()

    if role == SUPERADMIN_ROLE or role == "manager":
        return True
    if role != "admin":
        return False
    if department == "it":
        return normalized == "it"
    if department in {"hr", "compliance"}:
        return normalized in TASK_CATEGORIES and normalized != "it"
    return False


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


def slugify_doc_key(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
    slug = slug.strip("_")
    if not slug:
        slug = "extra_document"
    return slug[:48]


def get_hire_by_email(email: str):
    normalized = (email or "").strip().lower()
    if not normalized:
        return None
    return fetch_one(
        "SELECT id, email, employment_type FROM new_hire WHERE LOWER(email) = LOWER(%s) LIMIT 1",
        (normalized,),
    )


def load_custom_document_slots_for_hire(hire_id: str):
    if not hire_id:
        return []
    rows = fetch_all(
        """
        SELECT hire_id, doc_type, label, optional, created_by, created_at, is_active
        FROM hire_document_slot
        WHERE hire_id = %s AND is_active = 1
        ORDER BY created_at ASC
        """,
        (hire_id,),
    )
    return [
        {
            "id": (r.get("doc_type") or "").strip().lower(),
            "label": (r.get("label") or "Additional document").strip(),
            "optional": bool(r.get("optional")),
            "custom": True,
        }
        for r in rows
        if (r.get("doc_type") or "").strip()
    ]


def effective_required_document_types_for_email(email: str, role_hint: str = ""):
    role = (role_hint or get_user_role(email) or "").strip().lower()
    base = required_document_types_for_role(role)
    hire = get_hire_by_email(email)
    if not hire:
        return base
    custom_slots = load_custom_document_slots_for_hire(hire.get("id"))
    if not custom_slots:
        return base
    existing = {d.get("id") for d in base}
    merged = list(base)
    for slot in custom_slots:
        if slot.get("id") and slot.get("id") not in existing:
            merged.append(slot)
            existing.add(slot.get("id"))
    return merged


def it_access_template_items():
    checklist = ONBOARDING_BLUEPRINT.get("integration", {}).get("operations_it", {}).get("checklist", []) or []
    items = []
    for item in checklist:
        key = (item.get("id") or "").strip().lower()
        if not key:
            continue
        items.append(
            {
                "id": key,
                "title": (item.get("title") or key.replace("_", " ").title()).strip(),
                "target": (item.get("target") or "it").strip().lower(),
            }
        )
    return items


def normalize_it_access_state(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in IT_ACCESS_STATES:
        return IT_ACCESS_STATE_NOT_CONFIGURED
    return normalized


def it_access_state_label(state: str) -> str:
    normalized = normalize_it_access_state(state)
    labels = {
        IT_ACCESS_STATE_NOT_CONFIGURED: "Not configured",
        IT_ACCESS_STATE_PENDING: "Configured, awaiting confirmation",
        IT_ACCESS_STATE_CONFIRMED: "Configured and confirmed",
        IT_ACCESS_STATE_DECLINED: "Configured, access declined",
        IT_ACCESS_STATE_ERROR: "Configured, access error",
    }
    return labels.get(normalized, "Not configured")


def it_access_state_color(state: str) -> str:
    normalized = normalize_it_access_state(state)
    palette = {
        IT_ACCESS_STATE_NOT_CONFIGURED: "white",
        IT_ACCESS_STATE_PENDING: "yellow",
        IT_ACCESS_STATE_CONFIRMED: "green",
        IT_ACCESS_STATE_DECLINED: "red",
        IT_ACCESS_STATE_ERROR: "red",
    }
    return palette.get(normalized, "white")


def ensure_it_access_rows_for_email(email: str):
    normalized = (email or "").strip().lower()
    if not normalized:
        return
    for item in it_access_template_items():
        execute(
            """
            INSERT INTO it_access_item (email, access_key, access_title, state, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(6), NOW(6))
            ON DUPLICATE KEY UPDATE access_title = VALUES(access_title)
            """,
            (normalized, item["id"], item["title"], IT_ACCESS_STATE_NOT_CONFIGURED),
        )


def serialize_it_access_rows(rows):
    normalized = []
    for row in rows or []:
        item = dict(row or {})
        state = normalize_it_access_state(item.get("state"))
        item["email"] = (item.get("email") or "").strip().lower()
        item["access_key"] = (item.get("access_key") or "").strip().lower()
        item["access_title"] = (item.get("access_title") or item.get("access_key") or "IT Access").strip()
        item["state"] = state
        item["state_label"] = it_access_state_label(state)
        item["state_color"] = it_access_state_color(state)
        item["configured"] = state != IT_ACCESS_STATE_NOT_CONFIGURED
        item["confirmed"] = state == IT_ACCESS_STATE_CONFIRMED
        for date_field in ("configured_at", "hire_response_at", "created_at", "updated_at"):
            value = item.get(date_field)
            if value is None:
                item[date_field] = None
            elif hasattr(value, "isoformat"):
                item[date_field] = value.isoformat()
            else:
                item[date_field] = str(value)
        normalized.append(item)
    return normalized


def load_it_access_items_for_email(email: str):
    normalized = (email or "").strip().lower()
    if not normalized:
        return []
    rows = fetch_all(
        """
        SELECT
            id,
            email,
            access_key,
            access_title,
            state,
            details,
            portal_url,
            username_hint,
            notes,
            configured_by,
            configured_at,
            hire_response_note,
            hire_response_at,
            created_at,
            updated_at,
            updated_by
        FROM it_access_item
        WHERE LOWER(email) = LOWER(%s)
        """,
        (normalized,),
    )
    order = {key: idx for idx, key in enumerate(IT_ACCESS_TEMPLATE_KEY_ORDER)}
    serialized = serialize_it_access_rows(rows)
    serialized.sort(
        key=lambda row: (
            order.get((row.get("access_key") or "").strip().lower(), 999),
            (row.get("access_title") or "").strip().lower(),
        )
    )
    return serialized


def it_access_summary_for_rows(rows):
    states_by_key = {
        item["id"]: IT_ACCESS_STATE_NOT_CONFIGURED for item in it_access_template_items()
    }
    for row in rows or []:
        key = (row.get("access_key") or "").strip().lower()
        if key in states_by_key:
            states_by_key[key] = normalize_it_access_state(row.get("state"))

    total = len(states_by_key)
    confirmed = sum(1 for state in states_by_key.values() if state == IT_ACCESS_STATE_CONFIRMED)
    pending = sum(1 for state in states_by_key.values() if state == IT_ACCESS_STATE_PENDING)
    issues = sum(1 for state in states_by_key.values() if state in {IT_ACCESS_STATE_DECLINED, IT_ACCESS_STATE_ERROR})
    configured = sum(1 for state in states_by_key.values() if state != IT_ACCESS_STATE_NOT_CONFIGURED)
    not_configured = sum(1 for state in states_by_key.values() if state == IT_ACCESS_STATE_NOT_CONFIGURED)
    return {
        "total_items": total,
        "configured_count": configured,
        "confirmed_count": confirmed,
        "pending_count": pending,
        "issues_count": issues,
        "not_configured_count": not_configured,
        "all_confirmed": total > 0 and confirmed == total,
    }


def normalize_optional_date_field(value, field_name: str):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name}. Use YYYY-MM-DD.") from exc
    return parsed.strftime("%Y-%m-%d")


def user_progress_snapshot(
    email: str,
    docs=None,
    tasks=None,
    policies=None,
    trainings=None,
    it_provisions=None,
    required_doc_types=None,
    it_access_items=None,
):
    docs = docs or []
    tasks = tasks or []
    policies = policies or []
    trainings = trainings or []
    it_provisions = it_provisions or []
    it_access_items = it_access_items or []

    ud = [d for d in docs if d.get("uploader_email") == email]
    ut = [t for t in tasks if t.get("owner_email") == email]
    upol = [p for p in policies if p.get("email") == email]
    utr = [t for t in trainings if t.get("email") == email]
    uit = [p for p in it_provisions if p.get("email") == email]
    uita = [item for item in it_access_items if (item.get("email") or "").strip().lower() == email]
    it_summary = it_access_summary_for_rows(uita)
    it_done = bool(it_summary.get("all_confirmed")) or bool(uit)

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
        {"key": "it_access", "label": "IT provisioning completed", "done": it_done},
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
        "it_provisioned": int(it_summary.get("confirmed_count") or len(uit)),
        "it_access": {
            **it_summary,
            "legacy_records": len(uit),
        },
        "progress_percent": round(percentage, 2),
        "stage": stage,
    }


def hydrate_hires_with_context(
    hires,
    attachments,
    docs,
    tasks,
    policies,
    trainings,
    it_provisions,
    it_access_items=None,
    users_by_email=None,
):
    users_by_email = users_by_email or {}
    it_access_items = it_access_items or []
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
                it_access_items=it_access_items,
                required_doc_types=effective_required_document_types_for_email(email, employment_type),
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


register_admin_routes(
    app,
    {
        "require_role": require_role,
        "ADMIN_ROLES": ADMIN_ROLES,
        "SUPERADMIN_ROLE": SUPERADMIN_ROLE,
        "can_manage_hiring_admin": can_manage_hiring_admin,
        "fetch_one": fetch_one,
        "fetch_all": fetch_all,
        "execute": execute,
        "append_audit": append_audit,
        "load_org_structure": load_org_structure,
        "session_department_name": session_department_name,
        "list_users": list_users,
        "user_progress_snapshot": user_progress_snapshot,
        "effective_required_document_types_for_email": effective_required_document_types_for_email,
    },
)
register_hire_routes(
    app,
    {
        "login_required": login_required,
        "require_role": require_role,
        "ADMIN_ROLES": ADMIN_ROLES,
        "SUPERADMIN_ROLE": SUPERADMIN_ROLE,
        "execute": execute,
        "fetch_one": fetch_one,
        "fetch_all": fetch_all,
        "append_audit": append_audit,
        "session_department_name": session_department_name,
        "get_db_connection": get_db_connection,
        "ONBOARDING_BLUEPRINT": ONBOARDING_BLUEPRINT,
        "PLACEHOLDER_FILES": PLACEHOLDER_FILES,
        "UPLOAD_DIR": UPLOAD_DIR,
        "hydrate_hires_with_context": hydrate_hires_with_context,
        "can_view_documents_admin": can_view_documents_admin,
        "can_manage_hiring_admin": can_manage_hiring_admin,
        "department_and_title_are_valid": department_and_title_are_valid,
        "normalize_optional_date_field": normalize_optional_date_field,
        "get_role_id": get_role_id,
        "get_department_id": get_department_id,
        "update_user_avatar_file": update_user_avatar_file,
        "email_is_valid": email_is_valid,
        "allowed_file": allowed_file,
        "PROFILE_DIR": PROFILE_DIR,
        "HIRES_DIR": HIRES_DIR,
        "HR_ATTACHMENT_TYPES": HR_ATTACHMENT_TYPES,
        "create_user_record": create_user_record,
        "register_user_db": register_user_db,
        "enrich_document_record": enrich_document_record,
        "serialize_task_rows": serialize_task_rows,
    },
)
register_it_access_routes(
    app,
    {
        "login_required": login_required,
        "require_role": require_role,
        "ADMIN_ROLES": ADMIN_ROLES,
        "fetch_one": fetch_one,
        "execute": execute,
        "append_audit": append_audit,
        "can_view_it_access_admin": can_view_it_access_admin,
        "can_manage_it_access_admin": can_manage_it_access_admin,
        "ensure_it_access_rows_for_email": ensure_it_access_rows_for_email,
        "load_it_access_items_for_email": load_it_access_items_for_email,
        "it_access_template_items": it_access_template_items,
        "normalize_it_access_state": normalize_it_access_state,
        "it_access_summary_for_rows": it_access_summary_for_rows,
        "IT_ACCESS_STATE_NOT_CONFIGURED": IT_ACCESS_STATE_NOT_CONFIGURED,
        "IT_ACCESS_STATE_PENDING": IT_ACCESS_STATE_PENDING,
        "IT_ACCESS_STATE_CONFIRMED": IT_ACCESS_STATE_CONFIRMED,
        "IT_ACCESS_STATE_DECLINED": IT_ACCESS_STATE_DECLINED,
        "IT_ACCESS_STATE_ERROR": IT_ACCESS_STATE_ERROR,
    },
)
register_document_routes(
    app,
    {
        "login_required": login_required,
        "require_role": require_role,
        "ADMIN_ROLES": ADMIN_ROLES,
        "execute": execute,
        "fetch_all": fetch_all,
        "fetch_one": fetch_one,
        "get_db_connection": get_db_connection,
        "append_audit": append_audit,
        "can_manage_documents_admin": can_manage_documents_admin,
        "can_view_documents_admin": can_view_documents_admin,
        "can_manage_hiring_admin": can_manage_hiring_admin,
        "effective_required_document_types_for_email": effective_required_document_types_for_email,
        "get_user_role": get_user_role,
        "email_is_valid": email_is_valid,
        "allowed_file": allowed_file,
        "MAX_UPLOAD_BYTES": MAX_UPLOAD_BYTES,
        "UPLOAD_DIR": UPLOAD_DIR,
        "enrich_document_record": enrich_document_record,
        "REQUIRED_DOCUMENT_TYPES": REQUIRED_DOCUMENT_TYPES,
        "slugify_doc_key": slugify_doc_key,
    },
)
register_task_routes(
    app,
    {
        "login_required": login_required,
        "require_role": require_role,
        "ADMIN_ROLES": ADMIN_ROLES,
        "TASK_CATEGORIES": TASK_CATEGORIES,
        "TASK_STATUSES": TASK_STATUSES,
        "fetch_one": fetch_one,
        "fetch_all": fetch_all,
        "execute": execute,
        "get_db_connection": get_db_connection,
        "session_department_name": session_department_name,
        "task_category_allowed_for_current_admin": task_category_allowed_for_current_admin,
        "normalize_optional_date": normalize_optional_date,
        "create_task_record": create_task_record,
        "serialize_task_rows": serialize_task_rows,
        "user_progress_snapshot": user_progress_snapshot,
        "effective_required_document_types_for_email": effective_required_document_types_for_email,
    },
)
register_auth_routes(
    app,
    {
        "verify_user": verify_user,
        "get_user_record": get_user_record,
        "canonicalize_role_and_department": canonicalize_role_and_department,
        "ensure_csrf_token": ensure_csrf_token,
        "login_required": login_required,
        "require_role": require_role,
        "ADMIN_ROLES": ADMIN_ROLES,
        "SUPERADMIN_ROLE": SUPERADMIN_ROLE,
        "quote_plus": quote_plus,
        "list_users": list_users,
        "email_is_valid": email_is_valid,
        "ROLE_CATEGORIES": ROLE_CATEGORIES,
        "fetch_one": fetch_one,
        "fetch_all": fetch_all,
        "execute": execute,
        "get_role_id": get_role_id,
        "get_department_id": get_department_id,
        "append_audit": append_audit,
        "load_org_structure": load_org_structure,
        "can_manage_hiring_admin": can_manage_hiring_admin,
    },
)
serve_frontend = register_page_routes(
    app,
    {
        "FRONT_END_DIR": FRONT_END_DIR,
        "STYLE_DIR": STYLE_DIR,
        "UPLOAD_DIR": UPLOAD_DIR,
        "quote_plus": quote_plus,
        "login_required": login_required,
        "require_role": require_role,
        "SUPERADMIN_ROLE": SUPERADMIN_ROLE,
    },
)


@app.errorhandler(401)
@app.errorhandler(403)
def handle_auth_errors(err):
    # For browser requests, serve the public login page directly.
    if should_redirect_to_login_page():
        return serve_frontend("log_in.html")
    return Response(err.description if hasattr(err, "description") else "Forbidden", status=err.code, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
