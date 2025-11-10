from flask import Blueprint, current_app, redirect, render_template, request, url_for

web_bp = Blueprint("web", __name__)


@web_bp.get("/dashboard")
def legacy_dashboard():
    return redirect(url_for("web.home_page"))


@web_bp.get("/home")
def home_page():
    user_id = request.args.get("user_id", "demo")
    api_key = current_app.config.get("API_KEY")
    return render_template("pages/home.html", user_id=user_id, api_key=api_key)


@web_bp.get("/meal")
def meal_page():
    user_id = request.args.get("user_id", "demo")
    api_key = current_app.config.get("API_KEY")
    return render_template("pages/meal.html", user_id=user_id, api_key=api_key)


@web_bp.get("/workout")
def workout_page():
    user_id = request.args.get("user_id", "demo")
    minutes = request.args.get("minutes", "20")
    api_key = current_app.config.get("API_KEY")
    return render_template(
        "pages/workout.html", user_id=user_id, minutes=minutes, api_key=api_key
    )


@web_bp.get("/reports")
def reports_page():
    user_id = request.args.get("user_id", "demo")
    api_key = current_app.config.get("API_KEY")
    return render_template("pages/reports.html", user_id=user_id, api_key=api_key)


@web_bp.get("/hw1")
def hw1_page():
    return render_template("hw1.html")


@web_bp.get("/explain")
def explain_page():
    return render_template("hw1.html")
