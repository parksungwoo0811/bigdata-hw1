from flask import jsonify, request
from flask_login import current_user

from .. import db
from ..models import UserProfile
from ..services.recommend import auto_goal_plan, weekly_report
from . import api_bp


@api_bp.post("/profile")
def upsert_profile():
    payload = request.get_json(force=True) or {}
    # Force user_id to be current_user
    user_id = current_user.id
    
    profile = UserProfile.query.get(user_id)
    if profile:
        for key, value in payload.items():
            if hasattr(profile, key) and key != "user_id":
                setattr(profile, key, value)
    else:
        # Should not happen often as we create profile on register, but safe to have
        payload["user_id"] = user_id
        profile = UserProfile(**payload)
        db.session.add(profile)

    db.session.commit()
    return jsonify({"ok": True, "profile": profile.as_dict()})


# list_profiles removed for security


@api_bp.get("/profile/<user_id>")
def get_profile(user_id):
    if user_id != current_user.id:
        return jsonify({"error": "unauthorized"}), 403
    profile = UserProfile.query.get_or_404(user_id)
    return jsonify(profile.as_dict())


@api_bp.delete("/profile/<user_id>")
def delete_profile(user_id):
    if user_id != current_user.id:
        return jsonify({"error": "unauthorized"}), 403
    profile = UserProfile.query.get_or_404(user_id)
    # Note: Deleting profile might break foreign keys if not cascaded.
    # For now, we just delete the profile data.
    db.session.delete(profile)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.post("/profile/auto-target")
def profile_auto_target():
    payload = request.get_json(force=True) or {}
    try:
        result = auto_goal_plan(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@api_bp.get("/reports/<user_id>")
def reports(user_id):
    days = int(request.args.get("days", 30))
    report = weekly_report(user_id, days=days)
    if not report:
        return jsonify({"error": "user not found"}), 404
    return jsonify(report)
