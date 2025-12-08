from flask import jsonify, request

from ..services import recommend as recommend_service
from . import api_bp


@api_bp.get("/dashboard/<user_id>")
def dashboard(user_id):
    data = recommend_service.dashboard(user_id)
    if not data:
        return jsonify({"error": "user not found"}), 404
    return jsonify(data)


@api_bp.get("/recommend/food/<user_id>")
def recommend_food(user_id):
    topn = int(request.args.get("topn", 3))
    raw_excludes = request.args.getlist("exclude")
    if not raw_excludes and request.args.get("exclude"):
        raw_excludes = [
            part
            for part in request.args.get("exclude", "").split(",")
            if part
        ]
    exclude_names = [name.strip() for name in raw_excludes if name and name.strip()]
    payload = recommend_service.recommend_foods(user_id, topn, exclude_names)
    if not payload["meals"]:
        return jsonify({**payload, "note": "user not found or no catalog data"})
    return jsonify(payload)


@api_bp.get("/recommend/workout/<user_id>")
def recommend_workout(user_id):
    topn = int(request.args.get("topn", 3))
    topn = int(request.args.get("topn", 3))
    minutes_str = request.args.get("minutes")
    minutes = int(minutes_str) if minutes_str else None
    raw_excludes = request.args.getlist("exclude")
    if not raw_excludes and request.args.get("exclude"):
        raw_excludes = [
            part
            for part in request.args.get("exclude", "").split(",")
            if part
        ]
    exclude_names = [name.strip() for name in raw_excludes if name and name.strip()]
    result = recommend_service.recommend_workouts(
        user_id, topn, minutes, exclude_names
    )
    if not result["items"]:
        return jsonify({**result, "note": "user not found or no catalog data"})
    return jsonify(result)



@api_bp.get("/recommend/coach/<user_id>")
def recommend_coach(user_id):
    result = recommend_service.get_ai_coach_message(user_id)
    return jsonify(result)
