import hashlib
import os
import secrets

from flask import Response, jsonify, request, session
from werkzeug.utils import secure_filename


def register_document_routes(app, deps):
    login_required = deps["login_required"]
    require_role = deps["require_role"]
    ADMIN_ROLES = deps["ADMIN_ROLES"]
    execute = deps["execute"]
    fetch_all = deps["fetch_all"]
    fetch_one = deps["fetch_one"]
    get_db_connection = deps["get_db_connection"]
    append_audit = deps["append_audit"]
    can_manage_documents_admin = deps["can_manage_documents_admin"]
    can_view_documents_admin = deps["can_view_documents_admin"]
    can_manage_hiring_admin = deps["can_manage_hiring_admin"]
    effective_required_document_types_for_email = deps["effective_required_document_types_for_email"]
    get_user_role = deps["get_user_role"]
    email_is_valid = deps["email_is_valid"]
    allowed_file = deps["allowed_file"]
    MAX_UPLOAD_BYTES = deps["MAX_UPLOAD_BYTES"]
    UPLOAD_DIR = deps["UPLOAD_DIR"]
    enrich_document_record = deps["enrich_document_record"]
    REQUIRED_DOCUMENT_TYPES = deps["REQUIRED_DOCUMENT_TYPES"]
    slugify_doc_key = deps["slugify_doc_key"]

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

        role = get_user_role(email)
        valid_doc_ids = {d["id"] for d in effective_required_document_types_for_email(email, role)}
        if not doc_type or doc_type not in valid_doc_ids:
            return Response("Invalid or missing document type.", status=400, mimetype="text/plain")

        requester = session.get("email", "")
        if requester != email and not can_manage_documents_admin():
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
        requester_role = (session.get("role") or "").strip().lower()
        if not email and requester_role == "employee":
            email = requester or ""
        if email and email != requester and not can_view_documents_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        if not email and not can_view_documents_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        if email:
            docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
        else:
            docs = fetch_all("SELECT * FROM document")
        return jsonify({"documents": [enrich_document_record(doc) for doc in docs]})

    @app.post("/documents/<doc_id>/status")
    def update_document_status(doc_id):
        if not can_manage_documents_admin():
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

    @app.get("/documents/requirements")
    @login_required
    def document_requirements():
        email = (request.args.get("email") or "").strip().lower()
        requester = session.get("email")
        requester_role = (session.get("role") or "").strip().lower()
        if not email and requester_role == "employee":
            email = requester or ""
        if email and email != requester and not can_view_documents_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        if not email and not can_view_documents_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        if email:
            docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
        else:
            docs = fetch_all("SELECT * FROM document")
        effective_doc_types = effective_required_document_types_for_email(email) if email else REQUIRED_DOCUMENT_TYPES
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

        for doc in docs:
            if email and doc.get("uploader_email") != email and not can_view_documents_admin():
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

    @app.post("/api/new-hires/<hire_id>/document-slots")
    @require_role(ADMIN_ROLES)
    def create_hire_document_slot(hire_id):
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        hire = fetch_one("SELECT id, email, employment_type FROM new_hire WHERE id = %s", (hire_id,))
        if not hire:
            return Response("New hire not found.", status=404, mimetype="text/plain")

        label = (request.form.get("label") or "").strip()
        if not label:
            return Response("Document label is required.", status=400, mimetype="text/plain")

        optional_raw = (request.form.get("optional") or "").strip().lower()
        optional = optional_raw in {"1", "true", "yes", "on"}
        base_key = f"custom_{slugify_doc_key(label)}"

        blocked = {d.get("id") for d in REQUIRED_DOCUMENT_TYPES}
        existing_rows = fetch_all("SELECT doc_type FROM hire_document_slot WHERE hire_id = %s", (hire_id,))
        existing = {(r.get("doc_type") or "").strip().lower() for r in existing_rows}

        candidate = base_key
        suffix = 2
        while candidate in blocked or candidate in existing:
            candidate = f"{base_key}_{suffix}"
            suffix += 1

        execute(
            """
            INSERT INTO hire_document_slot (hire_id, doc_type, label, optional, created_by, created_at, is_active)
            VALUES (%s, %s, %s, %s, %s, NOW(), 1)
            """,
            (
                hire_id,
                candidate,
                label,
                1 if optional else 0,
                (session.get("email") or "").strip().lower(),
            ),
        )
        append_audit(
            "hire_document_slot_create",
            session.get("email", ""),
            {
                "hire_id": hire_id,
                "hire_email": (hire.get("email") or "").lower(),
                "doc_type": candidate,
                "label": label,
                "optional": optional,
            },
        )
        return jsonify(
            {
                "status": "ok",
                "slot": {"id": candidate, "label": label, "optional": optional, "custom": True},
                "requirements": effective_required_document_types_for_email(
                    (hire.get("email") or "").strip().lower(),
                    (hire.get("employment_type") or "").strip().lower(),
                ),
            }
        )
