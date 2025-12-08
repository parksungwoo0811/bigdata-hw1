from flask import Blueprint, request, jsonify
from nutrifit.services.ai import get_ai_service

ai_bp = Blueprint("ai", __name__)

@ai_bp.post("/food")
def analyze_food():
    data = request.json or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    service = get_ai_service()
    result = service.analyze_food(text)
    return jsonify(result)

@ai_bp.post("/workout")
def analyze_workout():
    data = request.json or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    service = get_ai_service()
    result = service.analyze_workout(text)
    return jsonify(result)
