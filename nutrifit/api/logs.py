from datetime import datetime, timedelta, timezone

from flask import jsonify, request

from .. import db
from ..models import FoodLog, WorkoutLog
from . import api_bp


def _today_range():
    now = datetime.now().astimezone()
    start_local = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _to_local_iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone().isoformat()


@api_bp.post("/food-log")
def add_food_log():
    payload = request.get_json(force=True) or {}
    required = {"user_id", "food_name", "kcal"}
    if not required.issubset(payload):
        return jsonify({"error": "user_id, food_name, kcal are required"}), 400

    # Round float values to 1 decimal place as per requirement
    for key in ["kcal", "protein_g", "fat_g", "carb_g"]:
        if key in payload and payload[key] is not None:
            try:
                payload[key] = round(float(payload[key]), 1)
            except (ValueError, TypeError):
                pass # Let validation or DB handle invalid types

    log = FoodLog(**payload)
    db.session.add(log)
    db.session.commit()
    return jsonify({"ok": True, "id": log.id})


@api_bp.get("/food-log/<user_id>")
def list_food_logs(user_id):
    query = FoodLog.query.filter_by(user_id=user_id).order_by(FoodLog.ts.desc())
    if request.args.get("today"):
        start, end = _today_range()
        query = query.filter(FoodLog.ts >= start, FoodLog.ts < end)
    logs = [
        {
            "id": log.id,
            "food_name": log.food_name,
            "kcal": log.kcal,
            "protein_g": log.protein_g,
            "fat_g": log.fat_g,
            "carb_g": log.carb_g,
            "ts": _to_local_iso(log.ts),
        }
        for log in query.all()
    ]
    return jsonify({"items": logs})


@api_bp.delete("/food-log/<int:log_id>")
def delete_food_log(log_id):
    log = FoodLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.post("/workout-log")
def add_workout_log():
    payload = request.get_json(force=True) or {}
    required = {"user_id", "workout_name", "kcal_burn"}
    if not required.issubset(payload):
        return jsonify({"error": "user_id, workout_name, kcal_burn are required"}), 400

    # Round float values to 1 decimal place as per requirement
    for key in ["minutes", "kcal_burn"]:
        if key in payload and payload[key] is not None:
            try:
                payload[key] = round(float(payload[key]), 1)
            except (ValueError, TypeError):
                pass

    log = WorkoutLog(**payload)
    db.session.add(log)
    db.session.commit()
    return jsonify({"ok": True, "id": log.id})


@api_bp.get("/workout-log/<user_id>")
def list_workout_logs(user_id):
    query = WorkoutLog.query.filter_by(user_id=user_id).order_by(WorkoutLog.ts.desc())
    if request.args.get("today"):
        start, end = _today_range()
        query = query.filter(WorkoutLog.ts >= start, WorkoutLog.ts < end)
    logs = [
        {
            "id": log.id,
            "workout_name": log.workout_name,
            "minutes": log.minutes,
            "mets": log.mets,
            "kcal_burn": log.kcal_burn,
            "ts": _to_local_iso(log.ts),
        }
        for log in query.all()
    ]
    return jsonify({"items": logs})


@api_bp.delete("/workout-log/<int:log_id>")
def delete_workout_log(log_id):
    log = WorkoutLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    return jsonify({"ok": True})
