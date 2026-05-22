from functools import wraps

from flask import Response, redirect, request, session

from .settings import DEV_AUTOLOGIN_EMAIL, DEV_AUTOLOGIN_ROLE

CSRF_EXEMPT_PATHS = {"/login", "/logout", "/register", "/reset-password"}


def ensure_csrf_token():
    #token csrf por sesion, seguridad anti cross-site request
    if "csrf_token" not in session:
        import secrets

        session["csrf_token"] = secrets.token_urlsafe(16)


def should_redirect_to_login_page() -> bool:
    #api responde http no html
    path = request.path or ""
    if path.startswith("/api/") or path.startswith("/documents"):
        return False
    
    return request.method == "GET" and "text/html" in request.accept_mimetypes


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        #autologin soporte desarrollo

        if not session.get("email"):
            if DEV_AUTOLOGIN_EMAIL:
                session["email"] = DEV_AUTOLOGIN_EMAIL
                session["role"] = DEV_AUTOLOGIN_ROLE or "employee"
                ensure_csrf_token()

            else:
                if should_redirect_to_login_page():
                    return redirect("/log_in.html")
                return Response("Authentication required", status=401, mimetype="text/plain")
        return func(*args, **kwargs)



    return wrapper


def require_role(allowed_roles):
    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            #control basico de rol
            if not session.get("email"):
                if DEV_AUTOLOGIN_EMAIL:
                    session["email"] = DEV_AUTOLOGIN_EMAIL
                    session["role"] = DEV_AUTOLOGIN_ROLE or "employee"
                    ensure_csrf_token()

                else:
                    if should_redirect_to_login_page():
                        return redirect("/log_in.html")
                    return Response("Authentication required", status=401, mimetype="text/plain")
            role = session.get("role", "")


            if role not in allowed_roles:
                if should_redirect_to_login_page():
                    return redirect("/log_in.html")
                return Response("Forbidden", status=403, mimetype="text/plain")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def csrf_protect_request():
    #csrf en metodos con cambios
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.path in CSRF_EXEMPT_PATHS:
            return None
        
        if session.get("email"):
            ensure_csrf_token()

            sent = request.headers.get("X-CSRF-Token")
            if not sent or sent != session.get("csrf_token"):
                return Response("CSRF token missing or invalid", status=400, mimetype="text/plain")
                #print(
    return None
