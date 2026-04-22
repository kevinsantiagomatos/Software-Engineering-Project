import json
import secrets
from datetime import datetime

from flask import Response, jsonify, request, session


def register_admin_routes(app, deps):
    require_role = deps["require_role"]
    ADMIN_ROLES = deps["ADMIN_ROLES"]
    SUPERADMIN_ROLE = deps["SUPERADMIN_ROLE"]
    can_manage_hiring_admin = deps["can_manage_hiring_admin"]
    fetch_one = deps["fetch_one"]
    fetch_all = deps["fetch_all"]
    execute = deps["execute"]
    append_audit = deps["append_audit"]
    load_org_structure = deps["load_org_structure"]
    session_department_name = deps["session_department_name"]
    list_users = deps["list_users"]
    user_progress_snapshot = deps["user_progress_snapshot"]
    effective_required_document_types_for_email = deps["effective_required_document_types_for_email"]

    @app.post("/api/org/job-titles")
    @require_role(ADMIN_ROLES)
    def create_job_title():
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
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

    @app.post("/api/it/provision")
    @require_role(ADMIN_ROLES)
    def it_provision():
        requester_role = (session.get("role") or "").strip().lower()
        if not (requester_role == SUPERADMIN_ROLE or (requester_role == "admin" and session_department_name() == "it")):
            return Response("Forbidden", status=403, mimetype="text/plain")
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
    @require_role(ADMIN_ROLES)
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
    @require_role(ADMIN_ROLES)
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
                required_doc_types=effective_required_document_types_for_email(email, employment_type),
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
