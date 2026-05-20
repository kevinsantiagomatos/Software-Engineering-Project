import csv
import io
import json
import secrets
from datetime import date, datetime

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

    def parse_optional_date(value: str, field_name: str):
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid {field_name}. Use YYYY-MM-DD.")

    def normalize_text_filter(value: str):
        return (value or "").strip().lower()

    def parse_metrics_filters():
        created_from = parse_optional_date(request.args.get("created_from"), "created_from")
        created_to = parse_optional_date(request.args.get("created_to"), "created_to")
        if created_from and created_to and created_from > created_to:
            raise ValueError("created_from cannot be after created_to.")
        return {
            "stage": normalize_text_filter(request.args.get("stage")),
            "status": normalize_text_filter(request.args.get("status")),
            "employment_type": normalize_text_filter(request.args.get("employment_type")),
            "department": normalize_text_filter(request.args.get("department")),
            "created_from": created_from,
            "created_to": created_to,
        }

    def datetime_to_date(value):
        if not value:
            return None
        if hasattr(value, "date"):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value)
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).date()
        except Exception:
            return None

    def hire_matches_filters(row, filters):
        if filters["stage"] and (row.get("stage") or "").lower() != filters["stage"]:
            return False
        if filters["status"] and (row.get("hire_status") or "").lower() != filters["status"]:
            return False
        if filters["employment_type"] and (row.get("employment_type") or "").lower() != filters["employment_type"]:
            return False
        if filters["department"]:
            department = (row.get("department") or "").lower()
            if filters["department"] not in department:
                return False

        created_date = row.get("created_date_obj")
        if filters["created_from"] and created_date and created_date < filters["created_from"]:
            return False
        if filters["created_to"] and created_date and created_date > filters["created_to"]:
            return False
        if (filters["created_from"] or filters["created_to"]) and not created_date:
            return False
        return True

    def collect_hire_metric_rows(filters):
        hires = fetch_all(
            """
            SELECT id, email, first_name, last_name, department, manager, status, employment_type, created_at, start_date
            FROM new_hire
            """
        )
        docs = fetch_all("SELECT uploader_email, status, uploaded_at FROM document")
        tasks = fetch_all("SELECT owner_email, status, category, due_date FROM task")
        policies = fetch_all("SELECT email FROM policy_ack")
        trainings = fetch_all("SELECT email FROM training_completion")
        it_provisions = fetch_all("SELECT email FROM it_provision")
        it_access_items = fetch_all("SELECT email, access_key, state FROM it_access_item")
        compliance_items = fetch_all("SELECT email, check_key, state FROM compliance_review_item")

        docs_by_email = {}
        for doc in docs:
            email = (doc.get("uploader_email") or "").strip().lower()
            if email:
                docs_by_email.setdefault(email, []).append(doc)

        tasks_by_email = {}
        for task in tasks:
            email = (task.get("owner_email") or "").strip().lower()
            if email:
                tasks_by_email.setdefault(email, []).append(task)

        rows = []
        now_utc = datetime.utcnow()
        for hire in hires:
            email = (hire.get("email") or "").strip().lower()
            if not email:
                continue

            employment_type = (hire.get("employment_type") or "employee").strip().lower()
            progress = user_progress_snapshot(
                email,
                docs=docs,
                tasks=tasks,
                policies=policies,
                trainings=trainings,
                it_provisions=it_provisions,
                it_access_items=it_access_items,
                compliance_items=compliance_items,
                required_doc_types=effective_required_document_types_for_email(email, employment_type),
            )

            created_date = datetime_to_date(hire.get("created_at"))
            start_date = datetime_to_date(hire.get("start_date"))
            docs_for_user = docs_by_email.get(email, [])
            tasks_for_user = tasks_by_email.get(email, [])

            docs_uploaded = len(docs_for_user)
            docs_approved = sum(1 for d in docs_for_user if (d.get("status") or "").strip().lower() == "approved")
            docs_pending = sum(1 for d in docs_for_user if (d.get("status") or "").strip().lower() == "pending_review")
            docs_rejected = sum(1 for d in docs_for_user if (d.get("status") or "").strip().lower() == "rejected")
            tasks_completed = sum(1 for t in tasks_for_user if (t.get("status") or "").strip().lower() == "completed")
            tasks_blocked = sum(1 for t in tasks_for_user if (t.get("status") or "").strip().lower() == "blocked")

            full_name = f"{(hire.get('first_name') or '').strip()} {(hire.get('last_name') or '').strip()}".strip() or email
            age_days = None
            if created_date:
                try:
                    created_dt = datetime.combine(created_date, datetime.min.time())
                    age_days = round((now_utc - created_dt).total_seconds() / 86400, 2)
                except Exception:
                    age_days = None

            compliance = progress.get("compliance") or {}
            row = {
                "hire_id": hire.get("id") or "",
                "full_name": full_name,
                "email": email,
                "department": (hire.get("department") or "").strip(),
                "manager": (hire.get("manager") or "").strip(),
                "employment_type": employment_type,
                "hire_status": (hire.get("status") or "").strip().lower(),
                "stage": progress.get("stage") or "Unknown",
                "progress_percent": float(progress.get("progress_percent") or 0),
                "documents_required": int((progress.get("documents") or {}).get("total") or 0),
                "documents_required_approved": int((progress.get("documents") or {}).get("approved") or 0),
                "tasks_required": int((progress.get("tasks") or {}).get("total") or 0),
                "tasks_required_completed": int((progress.get("tasks") or {}).get("completed") or 0),
                "compliance_status": (compliance.get("overall_status") or "pending_review").strip().lower(),
                "compliance_approved_count": int(compliance.get("approved_count") or 0),
                "compliance_pending_count": int(compliance.get("pending_count") or 0),
                "compliance_flagged_count": int(compliance.get("flagged_count") or 0),
                "it_confirmed_count": int((progress.get("it_access") or {}).get("confirmed_count") or 0),
                "it_total_items": int((progress.get("it_access") or {}).get("total_items") or 0),
                "policies_signed": int(progress.get("policies_signed") or 0),
                "training_completed": int(progress.get("training_completed") or 0),
                "documents_uploaded": docs_uploaded,
                "documents_uploaded_approved": docs_approved,
                "documents_uploaded_pending_review": docs_pending,
                "documents_uploaded_rejected": docs_rejected,
                "tasks_assigned": len(tasks_for_user),
                "tasks_assigned_completed": tasks_completed,
                "tasks_assigned_blocked": tasks_blocked,
                "created_at": created_date.isoformat() if created_date else "",
                "start_date": start_date.isoformat() if start_date else "",
                "age_days": age_days if age_days is not None else "",
                "created_date_obj": created_date,
            }
            if hire_matches_filters(row, filters):
                rows.append(row)

        rows.sort(key=lambda r: ((r.get("created_at") or ""), r.get("email") or ""), reverse=True)
        return rows

    def summarize_metric_rows(rows):
        stage_counts = {}
        status_counts = {}
        employment_counts = {}
        compliance_counts = {"approved": 0, "pending_review": 0, "flagged": 0}
        progress_values = []
        age_days = []

        totals = {
            "new_hires": len(rows),
            "documents": 0,
            "documents_approved": 0,
            "documents_pending_review": 0,
            "documents_rejected": 0,
            "tasks": 0,
            "tasks_completed": 0,
            "tasks_blocked": 0,
            "policy_signatures": 0,
            "training_completions": 0,
            "it_provisions": 0,
            "it_access_items": 0,
            "compliance_approved_hires": 0,
            "compliance_pending_hires": 0,
            "compliance_flagged_hires": 0,
        }

        for row in rows:
            stage = row.get("stage") or "Unknown"
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

            status = row.get("hire_status") or "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1

            employment = row.get("employment_type") or "unknown"
            employment_counts[employment] = employment_counts.get(employment, 0) + 1

            compliance_status = row.get("compliance_status") or "pending_review"
            if compliance_status not in compliance_counts:
                compliance_counts[compliance_status] = 0
            compliance_counts[compliance_status] += 1

            totals["documents"] += int(row.get("documents_uploaded") or 0)
            totals["documents_approved"] += int(row.get("documents_uploaded_approved") or 0)
            totals["documents_pending_review"] += int(row.get("documents_uploaded_pending_review") or 0)
            totals["documents_rejected"] += int(row.get("documents_uploaded_rejected") or 0)
            totals["tasks"] += int(row.get("tasks_assigned") or 0)
            totals["tasks_completed"] += int(row.get("tasks_assigned_completed") or 0)
            totals["tasks_blocked"] += int(row.get("tasks_assigned_blocked") or 0)
            totals["policy_signatures"] += int(row.get("policies_signed") or 0)
            totals["training_completions"] += int(row.get("training_completed") or 0)
            totals["it_access_items"] += int(row.get("it_total_items") or 0)
            totals["it_provisions"] += int(row.get("it_confirmed_count") or 0)

            if compliance_status == "approved":
                totals["compliance_approved_hires"] += 1
            elif compliance_status == "flagged":
                totals["compliance_flagged_hires"] += 1
            else:
                totals["compliance_pending_hires"] += 1

            progress_values.append(float(row.get("progress_percent") or 0))
            if row.get("age_days") != "":
                age_days.append(float(row.get("age_days") or 0))

        avg_progress = round(sum(progress_values) / len(progress_values), 2) if progress_values else 0
        avg_onboarding_days = round(sum(age_days) / len(age_days), 2) if age_days else 0

        return {
            "totals": totals,
            "distribution": {
                "stage": stage_counts,
                "status": status_counts,
                "employment_type": employment_counts,
                "compliance": compliance_counts,
            },
            "kpis": {
                "average_progress_percent": avg_progress,
                "average_days_since_hire_created": avg_onboarding_days,
            },
        }

    def export_rows_csv(rows):
        fieldnames = [
            "hire_id",
            "full_name",
            "email",
            "department",
            "manager",
            "employment_type",
            "hire_status",
            "stage",
            "progress_percent",
            "documents_required",
            "documents_required_approved",
            "documents_uploaded",
            "documents_uploaded_approved",
            "documents_uploaded_pending_review",
            "documents_uploaded_rejected",
            "tasks_required",
            "tasks_required_completed",
            "tasks_assigned",
            "tasks_assigned_completed",
            "tasks_assigned_blocked",
            "compliance_status",
            "compliance_approved_count",
            "compliance_pending_count",
            "compliance_flagged_count",
            "it_confirmed_count",
            "it_total_items",
            "policies_signed",
            "training_completed",
            "created_at",
            "start_date",
            "age_days",
        ]
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(data)
        return stream.getvalue()

    def pdf_escape(text: str):
        return str(text or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def build_simple_pdf(lines, title="Onboarding Metrics Export"):
        if not lines:
            lines = ["No data for selected filters."]

        def chunked(values, size):
            for i in range(0, len(values), size):
                yield values[i : i + size]

        pages = list(chunked(lines, 44)) or [[]]
        objects = []

        def add_obj(data: bytes):
            objects.append(data)
            return len(objects)

        font_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        pages_id = add_obj(b"")
        page_ids = []

        generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        for block in pages:
            text_lines = [title, f"Generated: {generated}", ""] + block
            content_parts = ["BT", "/F1 10 Tf", "50 770 Td"]
            for idx, line in enumerate(text_lines):
                if idx > 0:
                    content_parts.append("0 -14 Td")
                content_parts.append(f"({pdf_escape(line)}) Tj")
            content_parts.append("ET")
            content = "\n".join(content_parts).encode("latin-1", "replace")
            content_id = add_obj(
                b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream"
            )
            page_id = add_obj(
                (
                    f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode("ascii")
            )
            page_ids.append(page_id)

        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        objects[pages_id - 1] = f"<< /Type /Pages /Kids [ {kids} ] /Count {len(page_ids)} >>".encode("ascii")
        catalog_id = add_obj(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii"))

        out = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            out += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"

        xref_pos = len(out)
        out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
        out += b"0000000000 65535 f \n"
        for offset in offsets[1:]:
            out += f"{offset:010d} 00000 n \n".encode("ascii")
        out += (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
        return out

    def export_rows_pdf(rows):
        lines = []
        for row in rows:
            lines.append(
                " | ".join(
                    [
                        row.get("email") or "",
                        row.get("stage") or "",
                        f"{row.get('progress_percent', 0)}%",
                        f"Docs {row.get('documents_required_approved', 0)}/{row.get('documents_required', 0)}",
                        f"Tasks {row.get('tasks_required_completed', 0)}/{row.get('tasks_required', 0)}",
                        f"Compliance {row.get('compliance_status') or 'pending_review'}",
                    ]
                )
            )
        return build_simple_pdf(lines)

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
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
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
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        try:
            filters = parse_metrics_filters()
        except ValueError as exc:
            return Response(str(exc), status=400, mimetype="text/plain")

        rows = collect_hire_metric_rows(filters)
        payload = summarize_metric_rows(rows)
        payload["filters"] = {
            "stage": filters["stage"],
            "status": filters["status"],
            "employment_type": filters["employment_type"],
            "department": filters["department"],
            "created_from": filters["created_from"].isoformat() if filters["created_from"] else "",
            "created_to": filters["created_to"].isoformat() if filters["created_to"] else "",
        }
        payload["rows_count"] = len(rows)
        return jsonify(payload)

    @app.get("/api/admin/metrics/export")
    @require_role(ADMIN_ROLES)
    def admin_metrics_export():
        if not can_manage_hiring_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        try:
            filters = parse_metrics_filters()
        except ValueError as exc:
            return Response(str(exc), status=400, mimetype="text/plain")

        fmt = (request.args.get("format") or "csv").strip().lower()
        rows = collect_hire_metric_rows(filters)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if fmt == "csv":
            content = export_rows_csv(rows)
            response = Response(content, mimetype="text/csv")
            response.headers["Content-Disposition"] = f'attachment; filename="onboarding_metrics_{stamp}.csv"'
            return response
        if fmt == "pdf":
            content = export_rows_pdf(rows)
            response = Response(content, mimetype="application/pdf")
            response.headers["Content-Disposition"] = f'attachment; filename="onboarding_metrics_{stamp}.pdf"'
            return response

        return Response("Invalid format. Use csv or pdf.", status=400, mimetype="text/plain")
