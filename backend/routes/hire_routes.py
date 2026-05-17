import json
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

    def requester_can_view_compliance() -> bool:
        role = (session.get("role") or "").strip().lower()
        if role in {"compliance", "hr"}:
            return True
        return can_view_compliance_admin()

    def requester_can_manage_compliance() -> bool:
        role = (session.get("role") or "").strip().lower()
        if role == "compliance":
            return True
        return can_manage_compliance_admin()

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
        requester_role = (session.get("role") or "").strip().lower()
        can_admin_training = requester_role == SUPERADMIN_ROLE or requester_role == "manager" or (
            requester_role == "admin" and session_department_name() in {"hr", "compliance"}
        )
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
        policies = fetch_all("SELECT * FROM policy_ack WHERE email = %s", (email,)) if email else []
        trainings = fetch_all("SELECT * FROM training_completion WHERE email = %s", (email,)) if email else []
        it_provisions = fetch_all("SELECT * FROM it_provision WHERE email = %s", (email,)) if email else []
        it_access_items = fetch_all("SELECT * FROM it_access_item WHERE email = %s", (email,)) if email else []
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
