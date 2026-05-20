import json
import re
import secrets

import pymysql
from flask import Response, jsonify, request, session
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename


def register_hire_routes(app, deps):
    login_required = deps["login_required"]
    require_role = deps["require_role"]
    ADMIN_ROLES = deps["ADMIN_ROLES"]
    SUPERADMIN_ROLE = deps["SUPERADMIN_ROLE"]
    execute = deps["execute"]
    fetch_one = deps["fetch_one"]
    fetch_all = deps["fetch_all"]
    append_audit = deps["append_audit"]
    session_department_name = deps["session_department_name"]
    get_db_connection = deps["get_db_connection"]
    ONBOARDING_BLUEPRINT = deps["ONBOARDING_BLUEPRINT"]
    PLACEHOLDER_FILES = deps["PLACEHOLDER_FILES"]
    UPLOAD_DIR = deps["UPLOAD_DIR"]
    hydrate_hires_with_context = deps["hydrate_hires_with_context"]
    can_view_documents_admin = deps["can_view_documents_admin"]
    can_manage_hiring_admin = deps["can_manage_hiring_admin"]
    can_view_compliance_admin = deps["can_view_compliance_admin"]
    can_manage_compliance_admin = deps["can_manage_compliance_admin"]
    department_and_title_are_valid = deps["department_and_title_are_valid"]
    normalize_optional_date_field = deps["normalize_optional_date_field"]
    get_role_id = deps["get_role_id"]
    get_department_id = deps["get_department_id"]
    update_user_avatar_file = deps["update_user_avatar_file"]
    email_is_valid = deps["email_is_valid"]
    allowed_file = deps["allowed_file"]
    PROFILE_DIR = deps["PROFILE_DIR"]
    HIRES_DIR = deps["HIRES_DIR"]
    HR_ATTACHMENT_TYPES = deps["HR_ATTACHMENT_TYPES"]
    create_user_record = deps["create_user_record"]
    register_user_db = deps["register_user_db"]
    enrich_document_record = deps["enrich_document_record"]
    serialize_task_rows = deps["serialize_task_rows"]
    ensure_compliance_rows_for_email = deps["ensure_compliance_rows_for_email"]
    load_compliance_rows_for_email = deps["load_compliance_rows_for_email"]
    compliance_summary_for_rows = deps["compliance_summary_for_rows"]
    compliance_checklist_items = deps["compliance_checklist_items"]
    normalize_compliance_state = deps["normalize_compliance_state"]
    COMPLIANCE_STATE_PENDING = deps["COMPLIANCE_STATE_PENDING"]
    COMPLIANCE_STATE_APPROVED = deps["COMPLIANCE_STATE_APPROVED"]
    COMPLIANCE_STATE_FLAGGED = deps["COMPLIANCE_STATE_FLAGGED"]
    POLICY_ID_GROUPS = deps["POLICY_ID_GROUPS"]
    normalize_policy_id = deps["normalize_policy_id"]
    list_policy_catalog = deps["list_policy_catalog"]

    def requester_can_view_compliance() -> bool:
        return can_view_compliance_admin()

    def requester_can_manage_compliance() -> bool:
        return can_manage_compliance_admin()

    def requester_can_manage_training_for_others() -> bool:
        requester_role = (session.get("role") or "").strip().lower()
        return requester_role == SUPERADMIN_ROLE or requester_role == "manager" or (
            requester_role == "admin" and session_department_name() == "hr"
        )

    def serialize_policy_catalog_row(row):
        policy_id = normalize_policy_id(row.get("id") or row.get("policy_id") or "")
        label = (row.get("label") or policy_id).strip()
        file_path = (row.get("file_path") or "").strip().lstrip("/")
        url = (row.get("url") or "").strip() or (f"/uploads/{file_path}" if file_path else "")
        raw_active = row.get("is_active", True)
        if isinstance(raw_active, str):
            is_active = raw_active.strip().lower() not in {"0", "false", "no", "inactive"}
        else:
            is_active = bool(raw_active)
        return {
            "id": policy_id,
            "label": label,
            "file_path": file_path,
            "url": url,
            "is_active": is_active,
            "updated_at": row.get("updated_at") or "",
            "updated_by": row.get("updated_by") or "",
        }

    def policy_aliases_for_id(policy_id: str):
        canonical = normalize_policy_id(policy_id)
        aliases = POLICY_ID_GROUPS.get(canonical, {canonical})
        normalized = {(alias or "").strip().lower() for alias in aliases if (alias or "").strip()}
        if canonical:
            normalized.add(canonical)
        return sorted(normalized)

    def normalize_policy_review_state(value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"approved", "rejected", "pending_review", "signed"}:
            return normalized
        if normalized in {"pending", "review"}:
            return "pending_review"
        return "signed"

    @app.get("/api/policy/catalog")
    @login_required
    def policy_catalog():
        return jsonify({"policies": [serialize_policy_catalog_row(row) for row in list_policy_catalog()]})

    @app.get("/api/policy/admin/catalog")
    @login_required
    @require_role(ADMIN_ROLES)
    def policy_admin_catalog():
        if not requester_can_view_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")
        return jsonify(
            {
                "policies": [serialize_policy_catalog_row(row) for row in list_policy_catalog(include_inactive=True)],
                "can_manage": requester_can_manage_compliance(),
            }
        )

    @app.post("/api/policy/admin/update")
    @login_required
    @require_role(ADMIN_ROLES)
    def policy_admin_update():
        if not requester_can_manage_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")
        actor = (session.get("email") or "").strip().lower()
        raw_policy_id = (request.form.get("policy_id") or "").strip().lower()
        policy_id = normalize_policy_id(raw_policy_id)
        if not policy_id:
            return Response("policy_id is required.", status=400, mimetype="text/plain")

        existing = fetch_one(
            """
            SELECT policy_id, label, file_path
            FROM policy_definition
            WHERE policy_id = %s
            LIMIT 1
            """,
            (policy_id,),
        )
        if not existing:
            return Response("Policy definition not found.", status=404, mimetype="text/plain")

        label = (request.form.get("label") or "").strip() or (existing.get("label") or "").strip()
        if not label:
            return Response("Policy label is required.", status=400, mimetype="text/plain")

        file_path = (existing.get("file_path") or "").strip().lstrip("/")
        policy_file = request.files.get("policy_file")
        if policy_file and policy_file.filename:
            safe_name = secure_filename(policy_file.filename)
            if not safe_name.lower().endswith(".pdf"):
                return Response("Only PDF files are supported.", status=400, mimetype="text/plain")
            stored_name = f"{policy_id}.pdf"
            destination = UPLOAD_DIR / "policies" / stored_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            policy_file.save(destination)
            file_path = f"policies/{stored_name}"

        if not file_path:
            return Response("Policy file path is missing. Upload a PDF file.", status=400, mimetype="text/plain")

        execute(
            """
            INSERT INTO policy_definition (policy_id, label, file_path, updated_by)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                label = VALUES(label),
                file_path = VALUES(file_path),
                updated_by = VALUES(updated_by),
                updated_at = NOW(6)
            """,
            (policy_id, label, file_path, actor),
        )
        append_audit(
            "policy_definition_update",
            actor,
            {"policy_id": policy_id, "label": label, "file_path": file_path},
        )
        updated = fetch_one(
            """
            SELECT policy_id, label, file_path, is_active, updated_at, updated_by
            FROM policy_definition
            WHERE policy_id = %s
            LIMIT 1
            """,
            (policy_id,),
        ) or {"policy_id": policy_id, "label": label, "file_path": file_path}
        return jsonify({"status": "ok", "policy": serialize_policy_catalog_row(updated)})

    @app.post("/api/policy/admin/create")
    @login_required
    @require_role(ADMIN_ROLES)
    def policy_admin_create():
        if not requester_can_manage_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")

        actor = (session.get("email") or "").strip().lower()
        raw_policy_id = (request.form.get("policy_id") or "").strip().lower()
        policy_id = normalize_policy_id(raw_policy_id)
        label = (request.form.get("label") or "").strip()
        policy_file = request.files.get("policy_file")

        if not policy_id:
            return Response("policy_id is required.", status=400, mimetype="text/plain")
        if not re.match(r"^[a-z0-9_]{3,64}$", policy_id):
            return Response("policy_id must use 3-64 chars: lowercase letters, numbers, underscore.", status=400, mimetype="text/plain")
        if not label:
            return Response("Policy label is required.", status=400, mimetype="text/plain")
        if not policy_file or not policy_file.filename:
            return Response("Policy PDF file is required.", status=400, mimetype="text/plain")

        safe_name = secure_filename(policy_file.filename)
        if not safe_name.lower().endswith(".pdf"):
            return Response("Only PDF files are supported.", status=400, mimetype="text/plain")

        exists = fetch_one(
            """
            SELECT policy_id
            FROM policy_definition
            WHERE policy_id = %s
            LIMIT 1
            """,
            (policy_id,),
        )
        if exists:
            return Response("Policy already exists. Use update instead.", status=409, mimetype="text/plain")

        stored_name = f"{policy_id}.pdf"
        destination = UPLOAD_DIR / "policies" / stored_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        policy_file.save(destination)
        file_path = f"policies/{stored_name}"

        execute(
            """
            INSERT INTO policy_definition (policy_id, label, file_path, is_active, updated_by)
            VALUES (%s, %s, %s, 1, %s)
            """,
            (policy_id, label, file_path, actor),
        )
        append_audit(
            "policy_definition_create",
            actor,
            {"policy_id": policy_id, "label": label, "file_path": file_path},
        )
        created = fetch_one(
            """
            SELECT policy_id, label, file_path, is_active, updated_at, updated_by
            FROM policy_definition
            WHERE policy_id = %s
            LIMIT 1
            """,
            (policy_id,),
        ) or {"policy_id": policy_id, "label": label, "file_path": file_path, "is_active": 1}
        return jsonify({"status": "ok", "policy": serialize_policy_catalog_row(created)})

    @app.post("/api/policy/admin/state")
    @login_required
    @require_role(ADMIN_ROLES)
    def policy_admin_state():
        if not requester_can_manage_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")
        actor = (session.get("email") or "").strip().lower()
        policy_id = normalize_policy_id((request.form.get("policy_id") or "").strip().lower())
        raw_state = (request.form.get("state") or "").strip().lower()
        if not policy_id:
            return Response("policy_id is required.", status=400, mimetype="text/plain")

        if raw_state in {"1", "true", "active", "enabled"}:
            is_active = 1
        elif raw_state in {"0", "false", "inactive", "disabled"}:
            is_active = 0
        else:
            return Response("State must be active or inactive.", status=400, mimetype="text/plain")

        existing_catalog = {
            normalize_policy_id(row.get("id") or row.get("policy_id")): row
            for row in list_policy_catalog(include_inactive=True)
        }
        existing = existing_catalog.get(policy_id)
        if not existing:
            return Response("Policy definition not found.", status=404, mimetype="text/plain")

        execute(
            """
            INSERT INTO policy_definition (policy_id, label, file_path, is_active, updated_by)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                label = VALUES(label),
                file_path = VALUES(file_path),
                is_active = VALUES(is_active),
                updated_by = VALUES(updated_by),
                updated_at = NOW(6)
            """,
            (
                policy_id,
                (existing.get("label") or policy_id).strip(),
                (existing.get("file_path") or "").strip().lstrip("/"),
                is_active,
                actor,
            ),
        )
        append_audit(
            "policy_definition_state",
            actor,
            {"policy_id": policy_id, "is_active": bool(is_active)},
        )
        updated = fetch_one(
            """
            SELECT policy_id, label, file_path, is_active, updated_at, updated_by
            FROM policy_definition
            WHERE policy_id = %s
            LIMIT 1
            """,
            (policy_id,),
        ) or {
            "policy_id": policy_id,
            "label": (existing.get("label") or policy_id).strip(),
            "file_path": (existing.get("file_path") or "").strip().lstrip("/"),
            "is_active": is_active,
        }
        return jsonify({"status": "ok", "policy": serialize_policy_catalog_row(updated)})

    @app.post("/api/policy/admin/delete")
    @login_required
    @require_role(ADMIN_ROLES)
    def policy_admin_delete():
        if not requester_can_manage_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")
        actor = (session.get("email") or "").strip().lower()
        policy_id = normalize_policy_id((request.form.get("policy_id") or "").strip().lower())
        if not policy_id:
            return Response("policy_id is required.", status=400, mimetype="text/plain")

        core_policy_ids = {normalize_policy_id("company_policies"), normalize_policy_id("medical_plan")}
        if policy_id in core_policy_ids:
            return Response("Core policies cannot be deleted. Deactivate instead.", status=400, mimetype="text/plain")

        existing = fetch_one(
            """
            SELECT policy_id, label, file_path
            FROM policy_definition
            WHERE policy_id = %s
            LIMIT 1
            """,
            (policy_id,),
        )
        if not existing:
            return Response("Policy definition not found.", status=404, mimetype="text/plain")

        aliases = policy_aliases_for_id(policy_id)
        placeholders = ",".join(["%s"] * len(aliases))
        usage = fetch_one(
            f"""
            SELECT COUNT(*) AS c
            FROM policy_ack
            WHERE LOWER(policy_id) IN ({placeholders})
            """,
            tuple(aliases),
        )
        if int((usage or {}).get("c") or 0) > 0:
            return Response("Policy has acknowledgment history and cannot be deleted. Deactivate instead.", status=409, mimetype="text/plain")

        execute("DELETE FROM policy_definition WHERE policy_id = %s", (policy_id,))

        file_path = (existing.get("file_path") or "").strip().lstrip("/")
        if file_path:
            try:
                policies_dir = (UPLOAD_DIR / "policies").resolve()
                file_target = (UPLOAD_DIR / file_path).resolve()
                if str(file_target).startswith(str(policies_dir)) and file_target.exists():
                    file_target.unlink()
            except Exception:
                pass

        append_audit(
            "policy_definition_delete",
            actor,
            {"policy_id": policy_id, "label": (existing.get("label") or "").strip()},
        )
        return jsonify({"status": "ok", "policy_id": policy_id})

    @app.post("/api/policy/ack")
    @login_required
    def policy_ack():
        session_email = (session.get("email") or "").strip().lower()
        requester_role = (session.get("role") or "").strip().lower()
        email = (request.form.get("email") or "").strip().lower()
        policy_id_raw = (request.form.get("policy_id") or "").strip().lower()
        signature = (request.form.get("signature") or "").strip()
        policy_id = normalize_policy_id(policy_id_raw)
        if not session_email:
            return Response("Authentication required", status=401, mimetype="text/plain")
        if requester_role in ADMIN_ROLES:
            return Response("Admin accounts do not sign policy acknowledgments.", status=403, mimetype="text/plain")
        if not policy_id or not signature:
            return Response("policy_id and signature are required.", status=400, mimetype="text/plain")
        if email and email != session_email:
            return Response("Forbidden", status=403, mimetype="text/plain")

        available_policy_ids = {normalize_policy_id(row.get("id")) for row in list_policy_catalog()}
        if policy_id not in available_policy_ids:
            return Response("Unknown policy_id.", status=400, mimetype="text/plain")

        aliases = policy_aliases_for_id(policy_id)
        placeholders = ",".join(["%s"] * len(aliases))
        existing = fetch_one(
            f"""
            SELECT id, policy_id, status, signed_at
            FROM policy_ack
            WHERE LOWER(email)=LOWER(%s)
              AND LOWER(policy_id) IN ({placeholders})
            ORDER BY signed_at DESC
            LIMIT 1
            """,
            (session_email, *aliases),
        )
        if existing:
            return Response("This policy was already signed.", status=409, mimetype="text/plain")

        try:
            execute(
                """
                INSERT INTO policy_ack (id, email, policy_id, signature, status, signed_at)
                VALUES (%s,%s,%s,%s,%s,NOW())
                """,
                (secrets.token_hex(8), session_email, policy_id, signature, "pending_review"),
            )
        except pymysql.err.IntegrityError:
            return Response("This policy was already signed.", status=409, mimetype="text/plain")
        append_audit("policy_ack", session_email, {"policy_id": policy_id})
        return jsonify({"status": "ok", "email": session_email})

    @app.get("/api/policy/status")
    @login_required
    def policy_status():
        email = (request.args.get("email") or "").strip().lower()
        session_email = (session.get("email") or "").strip().lower()
        requester_role = (session.get("role") or "").strip().lower()
        can_admin_policy = requester_role == SUPERADMIN_ROLE or requester_role == "manager" or (
            requester_role == "admin" and session_department_name() in {"hr", "compliance"}
        )
        if email:
            if email != session_email and not can_admin_policy:
                return Response("Forbidden", status=403, mimetype="text/plain")
            policies = fetch_all("SELECT * FROM policy_ack WHERE email = %s", (email,))
        else:
            if can_admin_policy:
                policies = fetch_all("SELECT * FROM policy_ack")
            else:
                policies = fetch_all("SELECT * FROM policy_ack WHERE email = %s", (session_email,))
        return jsonify({"policies": policies})

    @app.get("/api/policy/admin/review")
    @login_required
    @require_role(ADMIN_ROLES)
    def policy_admin_review():
        if not requester_can_view_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")

        email_filter = (request.args.get("email") or "").strip().lower()
        policy_filter = normalize_policy_id((request.args.get("policy_id") or "").strip().lower())
        state_filter = (request.args.get("state") or "").strip().lower()
        allowed_state_filters = {"", "pending_signature", "pending_review", "signed", "approved", "rejected"}
        if state_filter not in allowed_state_filters:
            return Response("Invalid state filter.", status=400, mimetype="text/plain")

        catalog_rows = [serialize_policy_catalog_row(row) for row in list_policy_catalog(include_inactive=True)]
        if policy_filter and not any((row.get("id") or "") == policy_filter for row in catalog_rows):
            return Response("Unknown policy_id filter.", status=400, mimetype="text/plain")

        users = fetch_all(
            """
            SELECT
                LOWER(src.email) AS email,
                MAX(src.full_name) AS full_name
            FROM (
                SELECT nh.email AS email, TRIM(CONCAT_WS(' ', nh.first_name, nh.last_name)) AS full_name
                FROM new_hire nh
                WHERE nh.email IS NOT NULL AND nh.email <> ''
                UNION ALL
                SELECT u.email AS email, u.full_name AS full_name
                FROM `user` u
                WHERE u.email IS NOT NULL AND u.email <> ''
                  AND LOWER(COALESCE(u.role, '')) IN ('employee', 'contractor')
            ) src
            GROUP BY LOWER(src.email)
            ORDER BY LOWER(src.email)
            """
        )
        if email_filter:
            users = [u for u in users if email_filter in ((u.get("email") or "").strip().lower())]

        ack_rows = fetch_all(
            """
            SELECT
                pa.id,
                LOWER(pa.email) AS email,
                pa.policy_id,
                pa.signature,
                pa.status,
                pa.signed_at,
                pa.reviewed_by,
                pa.reviewed_at,
                pa.reviewer_note
            FROM policy_ack pa
            """
        )
        latest_by_user_policy = {}
        for row in ack_rows:
            email = (row.get("email") or "").strip().lower()
            if not email:
                continue
            canonical_policy_id = normalize_policy_id(row.get("policy_id") or "")
            if not canonical_policy_id:
                continue
            key = (email, canonical_policy_id)
            current = latest_by_user_policy.get(key)
            current_signed_at = str((current or {}).get("signed_at") or "")
            candidate_signed_at = str(row.get("signed_at") or "")
            if not current or candidate_signed_at >= current_signed_at:
                latest_by_user_policy[key] = row

        records = []
        for user_row in users:
            email = (user_row.get("email") or "").strip().lower()
            if not email:
                continue
            full_name = (user_row.get("full_name") or "").strip() or email
            for policy_row in catalog_rows:
                policy_id = normalize_policy_id(policy_row.get("id") or "")
                if not policy_id:
                    continue
                if policy_filter and policy_filter != policy_id:
                    continue
                ack_row = latest_by_user_policy.get((email, policy_id))
                signed = bool(ack_row)
                review_state = normalize_policy_review_state((ack_row or {}).get("status") or "signed") if signed else "pending_signature"
                if state_filter and review_state != state_filter:
                    continue
                records.append(
                    {
                        "email": email,
                        "full_name": full_name,
                        "policy_id": policy_id,
                        "policy_label": (policy_row.get("label") or policy_id).strip(),
                        "policy_active": bool(policy_row.get("is_active")),
                        "signed": signed,
                        "status": review_state,
                        "signature": (ack_row or {}).get("signature") or "",
                        "signed_at": (ack_row or {}).get("signed_at") or "",
                        "reviewed_by": (ack_row or {}).get("reviewed_by") or "",
                        "reviewed_at": (ack_row or {}).get("reviewed_at") or "",
                        "reviewer_note": (ack_row or {}).get("reviewer_note") or "",
                    }
                )

        summary = {
            "total": len(records),
            "signed": sum(1 for row in records if row.get("signed")),
            "pending_signature": sum(1 for row in records if row.get("status") == "pending_signature"),
            "pending_review": sum(1 for row in records if row.get("status") in {"pending_review", "signed"}),
            "approved": sum(1 for row in records if row.get("status") == "approved"),
            "rejected": sum(1 for row in records if row.get("status") == "rejected"),
        }

        return jsonify(
            {
                "records": records,
                "policies": catalog_rows,
                "summary": summary,
                "can_manage": requester_can_manage_compliance(),
            }
        )

    @app.post("/api/policy/admin/review-status")
    @login_required
    @require_role(ADMIN_ROLES)
    def policy_admin_review_status():
        if not requester_can_manage_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")

        actor = (session.get("email") or "").strip().lower()
        email = (request.form.get("email") or "").strip().lower()
        policy_id = normalize_policy_id((request.form.get("policy_id") or "").strip().lower())
        status = normalize_policy_review_state(request.form.get("status") or "pending_review")
        reviewer_note = (request.form.get("reviewer_note") or "").strip()

        if not email:
            return Response("Email is required.", status=400, mimetype="text/plain")
        if not policy_id:
            return Response("policy_id is required.", status=400, mimetype="text/plain")
        if status not in {"approved", "rejected", "pending_review"}:
            return Response("Invalid review status.", status=400, mimetype="text/plain")

        aliases = policy_aliases_for_id(policy_id)
        placeholders = ",".join(["%s"] * len(aliases))
        target = fetch_one(
            f"""
            SELECT id, policy_id, status
            FROM policy_ack
            WHERE LOWER(email)=LOWER(%s)
              AND LOWER(policy_id) IN ({placeholders})
            ORDER BY signed_at DESC
            LIMIT 1
            """,
            (email, *aliases),
        )
        if not target:
            return Response("No signed acknowledgment found for this user and policy.", status=404, mimetype="text/plain")

        try:
            execute(
                """
                UPDATE policy_ack
                SET status = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW(6),
                    reviewer_note = %s
                WHERE id = %s
                """,
                (status, actor, reviewer_note or None, target.get("id")),
            )
        except Exception:
            execute("UPDATE policy_ack SET status = %s WHERE id = %s", (status, target.get("id")))

        append_audit(
            "policy_ack_review_status",
            actor,
            {
                "email": email,
                "policy_id": policy_id,
                "status": status,
                "reviewer_note": reviewer_note,
            },
        )
        updated = fetch_one(
            """
            SELECT id, email, policy_id, status, signature, signed_at, reviewed_by, reviewed_at, reviewer_note
            FROM policy_ack
            WHERE id = %s
            LIMIT 1
            """,
            (target.get("id"),),
        ) or {}
        return jsonify({"status": "ok", "ack": updated})

    @app.get("/api/compliance/checklist")
    @login_required
    def compliance_checklist():
        requester_email = (session.get("email") or "").strip().lower()
        email = (request.args.get("email") or "").strip().lower() or requester_email
        if not email:
            return Response("Email is required.", status=400, mimetype="text/plain")
        if email != requester_email and not requester_can_view_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")
        ensure_compliance_rows_for_email(email)
        items = load_compliance_rows_for_email(email)
        return jsonify(
            {
                "email": email,
                "items": items,
                "summary": compliance_summary_for_rows(items),
                "template": compliance_checklist_items(),
                "can_manage": requester_can_manage_compliance(),
            }
        )

    @app.post("/api/compliance/checklist/<check_key>/status")
    @login_required
    @require_role(ADMIN_ROLES)
    def compliance_checklist_update(check_key):
        if not requester_can_manage_compliance():
            return Response("Forbidden", status=403, mimetype="text/plain")

        actor = (session.get("email") or "").strip().lower()
        email = (request.form.get("email") or "").strip().lower()
        key = (check_key or "").strip().lower()
        state = normalize_compliance_state(request.form.get("status") or COMPLIANCE_STATE_PENDING)
        note = (request.form.get("note") or "").strip()
        if not email:
            return Response("Email is required.", status=400, mimetype="text/plain")
        if state not in {COMPLIANCE_STATE_PENDING, COMPLIANCE_STATE_APPROVED, COMPLIANCE_STATE_FLAGGED}:
            return Response("Invalid compliance state.", status=400, mimetype="text/plain")

        template_keys = {(item.get("id") or "").strip().lower() for item in compliance_checklist_items()}
        if key not in template_keys:
            return Response("Unknown compliance check item.", status=400, mimetype="text/plain")

        ensure_compliance_rows_for_email(email)
        existing = fetch_one(
            "SELECT id, check_key FROM compliance_review_item WHERE LOWER(email)=LOWER(%s) AND check_key=%s LIMIT 1",
            (email, key),
        )
        if not existing:
            return Response("Compliance checklist item not found.", status=404, mimetype="text/plain")

        if key == "final_signoff" and state == COMPLIANCE_STATE_APPROVED:
            items = load_compliance_rows_for_email(email)
            blockers = [
                row.get("check_key")
                for row in items
                if (row.get("check_key") or "").strip().lower() != "final_signoff"
                and normalize_compliance_state(row.get("state")) != COMPLIANCE_STATE_APPROVED
            ]
            if blockers:
                return Response(
                    "Final sign-off requires all other compliance checks approved first.",
                    status=400,
                    mimetype="text/plain",
                )

        if state == COMPLIANCE_STATE_PENDING:
            execute(
                """
                UPDATE compliance_review_item
                SET state = %s,
                    reviewer_note = %s,
                    reviewed_by = NULL,
                    reviewed_at = NULL,
                    updated_at = NOW(6),
                    updated_by = %s
                WHERE LOWER(email)=LOWER(%s) AND check_key=%s
                """,
                (state, note or None, actor, email, key),
            )
        else:
            execute(
                """
                UPDATE compliance_review_item
                SET state = %s,
                    reviewer_note = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW(6),
                    updated_at = NOW(6),
                    updated_by = %s
                WHERE LOWER(email)=LOWER(%s) AND check_key=%s
                """,
                (state, note or None, actor, actor, email, key),
            )

        append_audit(
            "compliance_check_update",
            actor,
            {
                "email": email,
                "check_key": key,
                "state": state,
                "note": note or "",
            },
        )

        items = load_compliance_rows_for_email(email)
        updated = next((row for row in items if (row.get("check_key") or "").strip().lower() == key), None)
        return jsonify({"status": "ok", "item": updated, "summary": compliance_summary_for_rows(items)})

    @app.get("/api/onboarding/blueprint")
    @login_required
    def onboarding_blueprint():
        placeholders = []
        for rel_path, _ in PLACEHOLDER_FILES:
            placeholders.append({"path": f"/uploads/{rel_path}", "exists": (UPLOAD_DIR / rel_path).exists()})
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
        session_email = (session.get("email") or "").strip().lower()
        email = (request.form.get("email") or "").strip().lower()
        module_id = (request.form.get("module_id") or "").strip()
        if not email or not module_id:
            return Response("Email and module_id are required.", status=400, mimetype="text/plain")
        if email != session_email and not requester_can_manage_training_for_others():
            return Response("Forbidden", status=403, mimetype="text/plain")

        module = fetch_one("SELECT id FROM training_module WHERE id = %s LIMIT 1", (module_id,))
        if not module:
            return Response("Unknown module_id.", status=400, mimetype="text/plain")

        execute("DELETE FROM training_completion WHERE email = %s AND module_id = %s", (email, module_id))
        execute(
            "INSERT INTO training_completion (email, module_id, completed_at) VALUES (%s,%s,NOW())",
            (email, module_id),
        )
        append_audit("training_complete", session_email, {"email": email, "module_id": module_id})
        return jsonify({"status": "ok", "email": email, "module_id": module_id})

    @app.get("/api/training/status")
    @login_required
    def training_status():
        email = (request.args.get("email") or "").strip().lower()
        can_admin_training = requester_can_manage_training_for_others()
        if email:
            if email != session.get("email") and not can_admin_training:
                return Response("Forbidden", status=403, mimetype="text/plain")
            completions = fetch_all("SELECT * FROM training_completion WHERE email = %s", (email,))
        else:
            if not can_admin_training:
                return Response("Forbidden", status=403, mimetype="text/plain")
            completions = fetch_all("SELECT * FROM training_completion")
        return jsonify({"completions": completions})

    @app.get("/api/new-hires")
    @require_role(ADMIN_ROLES)
    def list_new_hires():
        hires = fetch_all("SELECT * FROM new_hire")
        attachments = fetch_all("SELECT * FROM new_hire_attachment")
        docs = fetch_all("SELECT * FROM document")
        tasks = fetch_all("SELECT * FROM task")
        policies = fetch_all("SELECT * FROM policy_ack")
        trainings = fetch_all("SELECT * FROM training_completion")
        it_provisions = fetch_all("SELECT * FROM it_provision")
        it_access_items = fetch_all("SELECT * FROM it_access_item")
        compliance_items = fetch_all("SELECT * FROM compliance_review_item")
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
            it_access_items=it_access_items,
            compliance_items=compliance_items,
            users_by_email=users_by_email,
        )
        return jsonify({"hires": hydrated})

    @app.get("/api/new-hires/<hire_id>")
    @require_role(ADMIN_ROLES)
    def get_new_hire_detail(hire_id):
        hire = fetch_one("SELECT * FROM new_hire WHERE id = %s", (hire_id,))
        if not hire:
            return Response("New hire not found.", status=404, mimetype="text/plain")

        attachments = fetch_all("SELECT * FROM new_hire_attachment WHERE hire_id = %s", (hire_id,))
        email = (hire.get("email") or "").lower()
        docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,)) if email else []
        if not can_view_documents_admin():
            docs = []
        tasks = fetch_all("SELECT * FROM task WHERE owner_email = %s", (email,)) if email else []
        requester_role = (session.get("role") or "").strip().lower()
        requester_department = session_department_name()
        compliance_only_view = requester_role == "admin" and requester_department == "compliance"
        if compliance_only_view:
            tasks = [row for row in tasks if (row.get("category") or "").strip().lower() == "compliance"]
        policies = fetch_all("SELECT * FROM policy_ack WHERE email = %s", (email,)) if email else []
        trainings = fetch_all("SELECT * FROM training_completion WHERE email = %s", (email,)) if email else []
        it_provisions = fetch_all("SELECT * FROM it_provision WHERE email = %s", (email,)) if email else []
        it_access_items = fetch_all("SELECT * FROM it_access_item WHERE email = %s", (email,)) if email else []
        if compliance_only_view:
            trainings = []
            it_provisions = []
            it_access_items = []
        ensure_compliance_rows_for_email(email)
        compliance_items = load_compliance_rows_for_email(email) if email else []
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
            it_access_items=it_access_items,
            compliance_items=compliance_items,
            users_by_email=users_by_email,
        )
        payload = hydrated[0] if hydrated else {}
        payload["documents"] = [enrich_document_record(d) for d in docs]
        payload["tasks"] = serialize_task_rows(tasks)
        payload["policies"] = policies
        payload["trainings"] = trainings
        payload["it_provisions"] = it_provisions
        payload["it_access_items"] = it_access_items
        payload["compliance"] = {
            "items": compliance_items,
            "summary": compliance_summary_for_rows(compliance_items),
        }
        return jsonify(payload)

    @app.post("/api/new-hires/<hire_id>")
    @require_role(ADMIN_ROLES)
    def update_new_hire(hire_id):
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
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
            role_id = get_role_id(payload["employment_type"])
            dep_id = get_department_id(payload["department"])
            execute(
                """
                UPDATE `user`
                SET full_name = %s, role = %s, role_id = %s, department = %s, department_id = %s, job_title = %s
                WHERE email = %s
                """,
                (full_name or email, payload["employment_type"], role_id, payload["department"], dep_id, payload["job_title"], email),
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
        requester_role = (session.get("role") or "").strip().lower()
        if email != session.get("email") and not (
            requester_role == SUPERADMIN_ROLE
            or requester_role == "manager"
            or (requester_role == "admin" and session_department_name() == "hr")
        ):
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
    @require_role(ADMIN_ROLES)
    def register_hire():
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
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
            role_id = get_role_id(employment_type)
            dep_id = get_department_id(department)
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
            execute(
                "UPDATE `user` SET role_id = %s, department_id = %s WHERE email = %s",
                (role_id, dep_id, email),
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
