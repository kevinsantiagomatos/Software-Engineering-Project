from datetime import datetime

from flask import Response, jsonify, request, session


def register_task_routes(app, deps):
    #configura rutas de este modulo
    login_required = deps["login_required"]
    require_role = deps["require_role"]
    ADMIN_ROLES = deps["ADMIN_ROLES"]
    TASK_CATEGORIES = deps["TASK_CATEGORIES"]
    TASK_STATUSES = deps["TASK_STATUSES"]
    fetch_one = deps["fetch_one"]
    fetch_all = deps["fetch_all"]
    execute = deps["execute"]
    get_db_connection = deps["get_db_connection"]
    session_department_name = deps["session_department_name"]
    task_category_allowed_for_current_admin = deps["task_category_allowed_for_current_admin"]
    normalize_optional_date = deps["normalize_optional_date"]
    create_task_record = deps["create_task_record"]
    serialize_task_rows = deps["serialize_task_rows"]
    user_progress_snapshot = deps["user_progress_snapshot"]
    effective_required_document_types_for_email = deps["effective_required_document_types_for_email"]
    ensure_compliance_rows_for_email = deps["ensure_compliance_rows_for_email"]

    def manager_assigned_hire_emails(manager_email: str):
        #obtiene hires bajo alcance del project manager autenticado
        if not manager_email:
            return set()
        rows = fetch_all(
            """
            SELECT LOWER(email) AS email
            FROM new_hire
            WHERE LOWER(COALESCE(project_manager_email, '')) = LOWER(%s)
               OR LOWER(COALESCE(manager, '')) = LOWER(%s)
            """,
            (manager_email, manager_email),
        )
        return {str(row.get("email") or "").strip().lower() for row in rows if row.get("email")}

    @app.post("/api/tasks")
    @login_required
    @require_role(ADMIN_ROLES)
    def create_task():
        #crea tarea con reglas por rol y categoria permitida
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
        if not payload["assigned_by"]:
            payload["assigned_by"] = (session.get("email") or "").strip().lower()

        if payload["category"] and payload["category"] not in TASK_CATEGORIES:
            return Response("Invalid category.", status=400, mimetype="text/plain")
        requester_role = (session.get("role") or "").strip().lower()
        if requester_role == "admin" and not payload["category"]:
            department = session_department_name()
            if department == "it":
                payload["category"] = "it"
            elif department == "compliance":
                payload["category"] = "compliance"
            else:
                payload["category"] = "hr"
        if requester_role == "manager":
            payload["category"] = "manager"
            requester_email = (session.get("email") or "").strip().lower()
            allowed_owner_emails = manager_assigned_hire_emails(requester_email)
            if payload["owner_email"] not in allowed_owner_emails:
                return Response("Forbidden", status=403, mimetype="text/plain")
        if requester_role in ADMIN_ROLES and not task_category_allowed_for_current_admin(payload["category"]):
            return Response("Forbidden", status=403, mimetype="text/plain")

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
        #lista tareas filtradas por permisos y filtros opcionales
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
        requester_role = (session.get("role") or "").strip().lower()
        requester_department = session_department_name()
        requester_email = (requester or "").strip().lower()
        if not email and requester_role == "employee":
            email = requester or ""
            query += " AND owner_email = %s"
            params.append(email)
        if email and email != requester and requester_role not in ADMIN_ROLES:
            return Response("Forbidden", status=403, mimetype="text/plain")
        if not email and requester_role not in ADMIN_ROLES:
            return Response("Forbidden", status=403, mimetype="text/plain")
        if requester_role == "manager":
            allowed_owner_emails = manager_assigned_hire_emails(requester_email)
            if email:
                if email not in allowed_owner_emails:
                    return Response("Forbidden", status=403, mimetype="text/plain")
            else:
                if not allowed_owner_emails:
                    return jsonify({"tasks": []})
                placeholders = ",".join(["%s"] * len(allowed_owner_emails))
                query += f" AND owner_email IN ({placeholders})"
                params.extend(sorted(allowed_owner_emails))
            query += " AND category = %s"
            params.append("manager")
        if requester_role == "admin" and requester_department == "it":
            query += " AND category = %s"
            params.append("it")
        if requester_role == "admin" and requester_department == "compliance":
            query += " AND category = %s"
            params.append("compliance")

        tasks = fetch_all(query, params)
        return jsonify({"tasks": serialize_task_rows(tasks)})

    @app.post("/api/tasks/<task_id>/status")
    @login_required
    def update_task_status(task_id):
        #actualiza estado de tarea respetando ownership y permisos
        status = (request.form.get("status") or "").strip().lower()
        if status not in TASK_STATUSES:
            return Response("Invalid status.", status=400, mimetype="text/plain")

        task = fetch_one("SELECT owner_email, category FROM task WHERE id = %s", (task_id,))
        if not task:
            return Response("Task not found.", status=404, mimetype="text/plain")
        requester = session.get("email")
        requester_role = (session.get("role") or "").strip().lower()
        requester_email = (requester or "").strip().lower()
        if requester != task.get("owner_email") and requester_role not in ADMIN_ROLES:
            return Response("Forbidden", status=403, mimetype="text/plain")
        if requester_role in ADMIN_ROLES and requester != task.get("owner_email"):
            if not task_category_allowed_for_current_admin(task.get("category") or ""):
                return Response("Forbidden", status=403, mimetype="text/plain")
            if requester_role == "manager":
                allowed_owner_emails = manager_assigned_hire_emails(requester_email)
                if (task.get("owner_email") or "").strip().lower() not in allowed_owner_emails:
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
        #construye progreso individual o agregado para paneles
        email = (request.args.get("email") or "").strip().lower()
        requester = session.get("email")
        requester_role = session.get("role", "")
        if not email and requester_role == "employee":
            email = requester or ""
        if email:
            docs = fetch_all("SELECT * FROM document WHERE uploader_email = %s", (email,))
            tasks = fetch_all("SELECT * FROM task WHERE owner_email = %s", (email,))
            it_provisions = fetch_all("SELECT * FROM it_provision WHERE email = %s", (email,))
            it_access_items = fetch_all("SELECT * FROM it_access_item WHERE email = %s", (email,))
            ensure_compliance_rows_for_email(email)
            compliance_items = fetch_all("SELECT * FROM compliance_review_item WHERE email = %s", (email,))
        else:
            docs = fetch_all("SELECT * FROM document")
            tasks = fetch_all("SELECT * FROM task")
            it_provisions = fetch_all("SELECT * FROM it_provision")
            it_access_items = fetch_all("SELECT * FROM it_access_item")
            compliance_items = fetch_all("SELECT * FROM compliance_review_item")

        def user_progress(e):
            #helper interno de rutas
            required_doc_types = effective_required_document_types_for_email(e)
            return user_progress_snapshot(
                e,
                docs=docs,
                tasks=tasks,
                policies=fetch_all("SELECT * FROM policy_ack"),
                trainings=fetch_all("SELECT * FROM training_completion"),
                it_provisions=it_provisions,
                it_access_items=it_access_items,
                compliance_items=compliance_items,
                required_doc_types=required_doc_types,
            )

        if email:
            if email != requester and requester_role not in ADMIN_ROLES:
                return Response("Forbidden", status=403, mimetype="text/plain")
            return jsonify(user_progress(email))

        if requester_role not in ADMIN_ROLES:
            return Response("Forbidden", status=403, mimetype="text/plain")

        emails = {d.get("uploader_email") for d in docs if d.get("uploader_email")} | {t.get("owner_email") for t in tasks if t.get("owner_email")}
        progress_list = [user_progress(e) for e in emails]
        return jsonify({"all": progress_list})
