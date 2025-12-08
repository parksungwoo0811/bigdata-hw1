from flask import Blueprint, current_app, jsonify, request

api_bp = Blueprint("api", __name__)


from flask_login import current_user

@api_bp.before_request
def require_api_key():
    # Allow session-based auth for frontend
    if current_user.is_authenticated:
        return

    # expected = current_app.config.get("API_KEY")
    # provided = request.headers.get("X-API-Key")
    # if expected and provided != expected:
    #     return jsonify({"error": "missing or invalid API key"}), 401
    return


from . import logs, profile, recommend  # noqa: E402,F401
