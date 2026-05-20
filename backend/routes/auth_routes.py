from flask import Response, jsonify, redirect, request, session


def register_auth_routes(app, deps):
    verify_user = deps["verify_user"]
    get_user_record = deps["get_user_record"]
    canonicalize_role_and_department = deps["canonicalize_role_and_department"]
    ensure_csrf_token = deps["ensure_csrf_token"]
    login_required = deps["login_required"]
    require_role = deps["require_role"]
    ADMIN_ROLES = deps["ADMIN_ROLES"]
    SUPERADMIN_ROLE = deps["SUPERADMIN_ROLE"]
    quote_plus = deps["quote_plus"]
    list_users = deps["list_users"]
    email_is_valid = deps["email_is_valid"]
    ROLE_CATEGORIES = deps["ROLE_CATEGORIES"]
    fetch_one = deps["fetch_one"]
    execute = deps["execute"]
    get_role_id = deps["get_role_id"]
    get_department_id = deps["get_department_id"]
    append_audit = deps["append_audit"]
    load_org_structure = deps["load_org_structure"]
    can_manage_hiring_admin = deps["can_manage_hiring_admin"]

    @app.get("/api/csrf")
    @login_required
    def csrf_token():
        ensure_csrf_token()
        return jsonify({"csrf_token": session["csrf_token"]})

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
            role, department = canonicalize_role_and_department(user.get("role"), user.get("department"))
            session["email"] = username
            session["role"] = role
            session["department"] = department
            ensure_csrf_token()
            if role == SUPERADMIN_ROLE:
                target = "/superadmin_dashboard.html?login=success"
            elif role in ADMIN_ROLES:
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
        if email != requester and requester_role not in ADMIN_ROLES:
            return Response("Forbidden", status=403, mimetype="text/plain")

        record = get_user_record(email)
        if not record:
            return Response("User not found.", status=404, mimetype="text/plain")

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
        user = get_user_record(email) or {}
        role, department = canonicalize_role_and_department(user.get("role"), user.get("department"))
        session["role"] = role
        session["department"] = department
        return jsonify(
            {
                "email": email,
                "role": role,
                "full_name": user.get("full_name") or email,
                "department": department or "",
                "job_title": user.get("job_title") or "",
                "created_at": user.get("created_at") or "",
                "avatar_url": user.get("avatar_url") or "",
            }
        )

    @app.get("/api/users")
    @login_required
    @require_role(ADMIN_ROLES)
    def get_users():
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        role_filter = (request.args.get("role") or "").strip().lower()
        users = list_users()
        if role_filter:
            users = [u for u in users if (u.get("role") or "").lower() == role_filter]
        return jsonify({"users": users})

    @app.post("/api/admin/users/<email>/role")
    @require_role({SUPERADMIN_ROLE})
    def superadmin_update_user_role(email):
        normalized_email = (email or "").strip().lower()
        new_role = (request.form.get("role") or "").strip().lower()
        requested_department = (request.form.get("department") or "").strip()
        if not normalized_email or not email_is_valid(normalized_email):
            return Response("Valid email is required.", status=400, mimetype="text/plain")
        if new_role not in ROLE_CATEGORIES:
            return Response("Invalid role.", status=400, mimetype="text/plain")
        existing = fetch_one("SELECT email, role FROM `user` WHERE email = %s", (normalized_email,))
        if not existing:
            return Response("User not found.", status=404, mimetype="text/plain")
        canonical_role, canonical_department = canonicalize_role_and_department(new_role, requested_department)
        role_id = get_role_id(canonical_role)
        department_id = get_department_id(canonical_department)
        execute(
            """
            UPDATE `user`
            SET role = %s, role_id = %s, department = %s, department_id = %s
            WHERE email = %s
            """,
            (canonical_role, role_id, canonical_department or None, department_id, normalized_email),
        )
        append_audit(
            "superadmin_user_role_update",
            session.get("email", ""),
            {
                "email": normalized_email,
                "old_role": existing.get("role"),
                "new_role": canonical_role,
                "department": canonical_department or None,
            },
        )
        return jsonify(
            {
                "status": "ok",
                "email": normalized_email,
                "role": canonical_role,
                "department": canonical_department or None,
            }
        )

    @app.post("/api/admin/users/<email>/status")
    @require_role({SUPERADMIN_ROLE})
    def superadmin_update_user_status(email):
        normalized_email = (email or "").strip().lower()
        new_status = (request.form.get("status") or "").strip().lower()
        allowed_statuses = {"active", "inactive", "disabled", "pending_hr_review"}
        if not normalized_email or not email_is_valid(normalized_email):
            return Response("Valid email is required.", status=400, mimetype="text/plain")
        if new_status not in allowed_statuses:
            return Response("Invalid status.", status=400, mimetype="text/plain")
        existing = fetch_one("SELECT email, status FROM `user` WHERE email = %s", (normalized_email,))
        if not existing:
            return Response("User not found.", status=404, mimetype="text/plain")

        execute("UPDATE `user` SET status = %s WHERE email = %s", (new_status, normalized_email))
        append_audit(
            "superadmin_user_status_update",
            session.get("email", ""),
            {"email": normalized_email, "old_status": existing.get("status"), "new_status": new_status},
        )
        return jsonify({"status": "ok", "email": normalized_email, "user_status": new_status})

    @app.get("/api/admin/audit-log")
    @require_role({SUPERADMIN_ROLE})
    def superadmin_audit_log():
        limit_raw = (request.args.get("limit") or "100").strip()
        try:
            limit = max(1, min(500, int(limit_raw)))
        except ValueError:
            return Response("Invalid limit.", status=400, mimetype="text/plain")
        rows = fetch_all(
            """
            SELECT id, action, actor, detail, timestamp
            FROM audit_log
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (limit,),
        )
        return jsonify({"entries": rows, "limit": limit})

    @app.get("/api/org/structure")
    def get_org_structure():
        departments = load_org_structure(active_only=True)
        return jsonify({"departments": departments})

    @app.post("/api/org/departments")
    @require_role(ADMIN_ROLES)
    def create_department():
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
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
