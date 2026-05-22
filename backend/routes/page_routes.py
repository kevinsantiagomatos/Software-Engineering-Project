from pathlib import Path

from flask import Response, redirect, request, send_from_directory


def register_page_routes(app, deps):
    #configura rutas de este modulo
    FRONT_END_DIR = deps["FRONT_END_DIR"]
    STYLE_DIR = deps["STYLE_DIR"]
    UPLOAD_DIR = deps["UPLOAD_DIR"]
    quote_plus = deps["quote_plus"]
    login_required = deps["login_required"]
    require_role = deps["require_role"]
    SUPERADMIN_ROLE = deps["SUPERADMIN_ROLE"]

    def serve_frontend(asset_path: str):
        #sirve html/js estatico desde front end
        if not FRONT_END_DIR.exists():
            return Response("Front-end directory missing", status=500, mimetype="text/plain")
        return send_from_directory(FRONT_END_DIR, asset_path)

    @app.get("/")
    def root():
        #endpoint principal de esta ruta
        return serve_frontend("log_in.html")

    @app.get("/log_in.html")
    def login_page():
        #endpoint principal de esta ruta
        return serve_frontend("log_in.html")

    @app.get("/admin_panel")
    def admin_panel_alias():
        #alias corto para panel administrativo
        return redirect("/admin_panel.html", code=302)

    @app.get("/admin_hire_detail")
    def admin_hire_detail_alias():
        #endpoint administrativo principal
        hire_id = (request.args.get("hire_id") or "").strip()
        if hire_id:
            return redirect(f"/admin_hire_detail.html?hire_id={quote_plus(hire_id)}", code=302)
        return redirect("/admin_hire_detail.html", code=302)

    @app.get("/admin_metrics")
    def admin_metrics_alias():
        #endpoint administrativo principal
        return redirect("/admin_metrics.html", code=302)

    @app.get("/superadmin")
    @login_required
    @require_role({SUPERADMIN_ROLE})
    def superadmin_alias():
        #endpoint principal de esta ruta
        return redirect("/superadmin_dashboard.html", code=302)

    @app.get("/dashboard")
    def dashboard_alias():
        #endpoint principal de esta ruta
        email = (request.args.get("email") or "").strip()
        if email:
            return redirect(f"/dashboard.html?email={quote_plus(email)}", code=302)
        return redirect("/dashboard.html", code=302)

    @app.get("/profile")
    def profile_alias():
        #endpoint principal de esta ruta
        email = (request.args.get("email") or "").strip()
        if email:
            return redirect(f"/profile.html?email={quote_plus(email)}", code=302)
        return redirect("/profile.html", code=302)

    @app.get("/project_assignment")
    def project_assignment_alias():
        #endpoint principal de esta ruta
        email = (request.args.get("email") or "").strip()
        if email:
            return redirect(f"/project_assignment.html?email={quote_plus(email)}", code=302)
        return redirect("/project_assignment.html", code=302)

    @app.get("/manager_workspace")
    def manager_workspace_alias():
        #endpoint principal de esta ruta
        return redirect("/manager_workspace.html", code=302)

    @app.get("/style/<path:asset_path>")
    def style_assets(asset_path):
        #endpoint principal de esta ruta
        if not STYLE_DIR.exists():
            return Response("Style directory missing", status=500, mimetype="text/plain")
        return send_from_directory(STYLE_DIR, asset_path)

    @app.get("/uploads/<path:asset_path>")
    @login_required
    def uploaded_assets(asset_path):
        #sirve archivos subidos con opcion de descarga forzada
        if not UPLOAD_DIR.exists():
            return Response("Uploads directory missing", status=404, mimetype="text/plain")
        download_requested = (request.args.get("download") or "").strip().lower() in {"1", "true", "yes"}
        filename = (request.args.get("filename") or "").strip() or Path(asset_path).name
        if download_requested:
            return send_from_directory(UPLOAD_DIR, asset_path, as_attachment=True, download_name=filename)
        return send_from_directory(UPLOAD_DIR, asset_path)

    @app.get("/<path:asset_path>")
    def static_assets(asset_path):
        #endpoint principal de esta ruta
        return serve_frontend(asset_path)

    return serve_frontend
