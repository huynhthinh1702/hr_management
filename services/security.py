import os

from flask import jsonify, request, session

try:
    from flask_limiter import Limiter
    from flask_limiter.errors import RateLimitExceeded
    from flask_limiter.util import get_remote_address
except ImportError:  # pragma: no cover - allows app boot before deps are installed
    Limiter = None
    RateLimitExceeded = Exception

    def get_remote_address():
        return request.remote_addr or "unknown"


def _rate_limit_key():
    user_id = session.get("user_id")
    if user_id:
        return f"user:{user_id}"
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return f"ip:{client_ip}"
    return f"ip:{get_remote_address()}"


def init_limiter(app):
    if Limiter is None:
        class NoopLimiter:
            def limit(self, *_args, **_kwargs):
                def decorator(fn):
                    return fn

                return decorator

        app.logger.warning("Flask-Limiter is not installed. Rate limiting is currently disabled.")
        return NoopLimiter()

    storage_uri = os.getenv("REDIS_URL") or os.getenv("RATE_LIMIT_REDIS_URL") or "memory://"
    limiter = Limiter(
        key_func=_rate_limit_key,
        app=app,
        storage_uri=storage_uri,
        default_limits=[],
        strategy="fixed-window",
        headers_enabled=True,
    )

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(error):
        description = getattr(error, "description", None) or "Too many requests. Please try again shortly."
        wants_json = request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"
        payload = {
            "error": "rate_limited",
            "message": description,
            "retry_after_seconds": getattr(error, "retry_after", None),
        }
        if wants_json:
            return jsonify(payload), 429
        return (
            jsonify(payload)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest"
            else (description, 429)
        )

    if storage_uri == "memory://":
        app.logger.warning(
            "Flask-Limiter is using in-memory storage. Set REDIS_URL for multi-worker production rate limits."
        )

    return limiter
