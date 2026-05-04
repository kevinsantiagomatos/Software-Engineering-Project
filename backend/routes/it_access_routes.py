from datetime import datetime

from flask import Response, jsonify, request, session


def register_it_access_routes(app, deps):
    login_required = deps["login_required"]
    require_role = deps["require_role"]
    ADMIN_ROLES = deps["ADMIN_ROLES"]
    fetch_one = deps["fetch_one"]
    execute = deps["execute"]
    append_audit = deps["append_audit"]
    can_view_it_access_admin = deps["can_view_it_access_admin"]
    can_manage_it_access_admin = deps["can_manage_it_access_admin"]
    ensure_it_access_rows_for_email = deps["ensure_it_access_rows_for_email"]
    load_it_access_items_for_email = deps["load_it_access_items_for_email"]
    it_access_template_items = deps["it_access_template_items"]
    normalize_it_access_state = deps["normalize_it_access_state"]
    it_access_summary_for_rows = deps["it_access_summary_for_rows"]
    IT_ACCESS_STATE_NOT_CONFIGURED = deps["IT_ACCESS_STATE_NOT_CONFIGURED"]
    IT_ACCESS_STATE_PENDING = deps["IT_ACCESS_STATE_PENDING"]
    IT_ACCESS_STATE_CONFIRMED = deps["IT_ACCESS_STATE_CONFIRMED"]
    IT_ACCESS_STATE_DECLINED = deps["IT_ACCESS_STATE_DECLINED"]
    IT_ACCESS_STATE_ERROR = deps["IT_ACCESS_STATE_ERROR"]

    def email_exists(email: str) -> bool:
        if not email:
            return False
        in_user = fetch_one("SELECT email FROM `user` WHERE LOWER(email)=LOWER(%s) LIMIT 1", (email,))
        if in_user:
            return True
        in_hire = fetch_one("SELECT email FROM new_hire WHERE LOWER(email)=LOWER(%s) LIMIT 1", (email,))
        return bool(in_hire)

    def refresh_payload(email: str):
        items = load_it_access_items_for_email(email)
        summary = it_access_summary_for_rows(items)
        return {"email": email, "items": items, "summary": summary}

    @app.get("/api/it-access/template")
    @login_required
    def it_access_template():
        return jsonify({"items": it_access_template_items()})

    @app.get("/api/it-access")
    @login_required
    def list_it_access():
        requester_email = (session.get("email") or "").strip().lower()
        requester_role = (session.get("role") or "").strip().lower()
        email = (request.args.get("email") or "").strip().lower() or requester_email
        if not email:
            return Response("Email is required.", status=400, mimetype="text/plain")
        if email != requester_email and requester_role not in ADMIN_ROLES:
            return Response("Forbidden", status=403, mimetype="text/plain")
        if email != requester_email and requester_role in ADMIN_ROLES and not can_view_it_access_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")
        if not email_exists(email):
            return Response("User/new hire not found.", status=404, mimetype="text/plain")

        ensure_it_access_rows_for_email(email)
        payload = refresh_payload(email)
        can_manage = can_manage_it_access_admin()
        is_owner = email == requester_email
        for item in payload["items"]:
            state = (item.get("state") or "").strip().lower()
            can_respond = is_owner and state in {IT_ACCESS_STATE_PENDING, IT_ACCESS_STATE_DECLINED, IT_ACCESS_STATE_ERROR}
            item["can_configure"] = can_manage
            item["can_respond"] = can_respond
            item["can_confirm"] = can_respond
            item["can_decline"] = can_respond
        payload["can_manage"] = can_manage
        payload["is_owner"] = is_owner
        return jsonify(payload)

    @app.post("/api/it-access/<access_key>/configure")
    @login_required
    @require_role(ADMIN_ROLES)
    def configure_it_access_item(access_key):
        if not can_manage_it_access_admin():
            return Response("Forbidden", status=403, mimetype="text/plain")

        actor = (session.get("email") or "").strip().lower()
        email = (request.form.get("email") or "").strip().lower()
        key = (access_key or "").strip().lower()
        if not email:
            return Response("Email is required.", status=400, mimetype="text/plain")
        if not key:
            return Response("access_key is required.", status=400, mimetype="text/plain")
        if not email_exists(email):
            return Response("User/new hire not found.", status=404, mimetype="text/plain")

        template_map = {item["id"]: item for item in it_access_template_items()}
        if key not in template_map:
            exists = fetch_one(
                "SELECT id FROM it_access_item WHERE LOWER(email)=LOWER(%s) AND access_key=%s LIMIT 1",
                (email, key),
            )
            if not exists:
                return Response("Unknown access_key.", status=400, mimetype="text/plain")

        state = normalize_it_access_state(request.form.get("state") or IT_ACCESS_STATE_PENDING)
        if state not in {IT_ACCESS_STATE_NOT_CONFIGURED, IT_ACCESS_STATE_PENDING, IT_ACCESS_STATE_ERROR}:
            return Response("Invalid state for IT configuration.", status=400, mimetype="text/plain")

        details = (request.form.get("details") or "").strip()
        portal_url = (request.form.get("portal_url") or "").strip()
        username_hint = (request.form.get("username_hint") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        configured_at = None if state == IT_ACCESS_STATE_NOT_CONFIGURED else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        configured_by = None if state == IT_ACCESS_STATE_NOT_CONFIGURED else actor
        access_title = (
            (request.form.get("access_title") or "").strip()
            or (template_map.get(key, {}) or {}).get("title")
            or key.replace("_", " ").title()
        )

        execute(
            """
            INSERT INTO it_access_item (
                email, access_key, access_title, state, details, portal_url, username_hint, notes,
                configured_by, configured_at, hire_response_note, hire_response_at, created_at, updated_at, updated_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, NOW(6), NOW(6), %s)
            ON DUPLICATE KEY UPDATE
                access_title = VALUES(access_title),
                state = VALUES(state),
                details = VALUES(details),
                portal_url = VALUES(portal_url),
                username_hint = VALUES(username_hint),
                notes = VALUES(notes),
                configured_by = VALUES(configured_by),
                configured_at = VALUES(configured_at),
                hire_response_note = CASE
                    WHEN VALUES(state) IN ('not_configured', 'configured_pending_confirmation', 'configured_error') THEN NULL
                    ELSE hire_response_note
                END,
                hire_response_at = CASE
                    WHEN VALUES(state) IN ('not_configured', 'configured_pending_confirmation', 'configured_error') THEN NULL
                    ELSE hire_response_at
                END,
                updated_at = NOW(6),
                updated_by = VALUES(updated_by)
            """,
            (
                email,
                key,
                access_title,
                state,
                details or None,
                portal_url or None,
                username_hint or None,
                notes or None,
                configured_by,
                configured_at,
                actor,
            ),
        )

        append_audit(
            "it_access_configure",
            actor,
            {
                "email": email,
                "access_key": key,
                "state": state,
            },
        )
        payload = refresh_payload(email)
        item = next((row for row in payload["items"] if (row.get("access_key") or "").strip().lower() == key), None)
        return jsonify({"status": "ok", "item": item, "summary": payload["summary"]})

    @app.post("/api/it-access/<access_key>/respond")
    @login_required
    def respond_it_access_item(access_key):
        requester_email = (session.get("email") or "").strip().lower()
        key = (access_key or "").strip().lower()
        email = (request.form.get("email") or "").strip().lower() or requester_email
        response = (request.form.get("response") or "").strip().lower()
        note = (request.form.get("note") or "").strip()
        if not key:
            return Response("access_key is required.", status=400, mimetype="text/plain")
        if email != requester_email:
            return Response("Forbidden", status=403, mimetype="text/plain")
        if response not in {"confirmed", "declined"}:
            return Response("response must be confirmed or declined.", status=400, mimetype="text/plain")

        ensure_it_access_rows_for_email(email)
        existing = fetch_one(
            """
            SELECT id, state
            FROM it_access_item
            WHERE LOWER(email)=LOWER(%s) AND access_key=%s
            LIMIT 1
            """,
            (email, key),
        )
        if not existing:
            return Response("IT access item not found.", status=404, mimetype="text/plain")

        current_state = normalize_it_access_state(existing.get("state"))
        if current_state == IT_ACCESS_STATE_NOT_CONFIGURED:
            return Response("IT has not configured this access yet.", status=400, mimetype="text/plain")

        new_state = IT_ACCESS_STATE_CONFIRMED if response == "confirmed" else IT_ACCESS_STATE_DECLINED
        execute(
            """
            UPDATE it_access_item
            SET state = %s,
                hire_response_note = %s,
                hire_response_at = NOW(6),
                updated_at = NOW(6),
                updated_by = %s
            WHERE LOWER(email)=LOWER(%s) AND access_key=%s
            """,
            (new_state, note or None, requester_email, email, key),
        )
        append_audit(
            "it_access_response",
            requester_email,
            {
                "email": email,
                "access_key": key,
                "response": response,
            },
        )

        payload = refresh_payload(email)
        item = next((row for row in payload["items"] if (row.get("access_key") or "").strip().lower() == key), None)
        return jsonify({"status": "ok", "item": item, "summary": payload["summary"]})
