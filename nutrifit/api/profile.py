from flask import jsonify, request

from .. import db
from ..models import UserProfile
from ..services.recommend import auto_goal_plan, weekly_report
from . import api_bp


@api_bp.post("/profile")
def upsert_profile():
    payload = request.get_json(force=True) or {}
    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    profile = UserProfile.query.get(user_id)
    if profile:
        for key, value in payload.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
    else:
        profile = UserProfile(**payload)
        db.session.add(profile)

    db.session.commit()
    return jsonify({"ok": True, "profile": profile.as_dict()})


@api_bp.get("/profile")
def list_profiles():
    profiles = (
        UserProfile.query.order_by(UserProfile.user_id.asc()).all()
    )
    items = [
        {"user_id": profile.user_id, "name": profile.name}
        for profile in profiles
    ]
    return jsonify({"items": items})


@api_bp.get("/profile/<user_id>")
def get_profile(user_id):
    profile = UserProfile.query.get_or_404(user_id)
    return jsonify(profile.as_dict())


@api_bp.delete("/profile/<user_id>")
def delete_profile(user_id):
    profile = UserProfile.query.get_or_404(user_id)
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
