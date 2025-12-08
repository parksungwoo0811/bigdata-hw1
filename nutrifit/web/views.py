from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import login_required, current_user

web_bp = Blueprint("web", __name__)


@web_bp.get("/dashboard")
def legacy_dashboard():
    return redirect(url_for("web.home_page"))





@web_bp.get("/home")
@login_required
def home_page():
    return render_template("pages/home.html", profile=current_user.profile)


@web_bp.get("/meal")
@login_required
def meal_page():
    return render_template("pages/meal.html")


@web_bp.get("/workout")
@login_required
def workout_page():
    minutes = request.args.get("minutes", "20")
    return render_template("pages/workout.html", minutes=minutes)


@web_bp.get("/reports")
@login_required
def reports_page():
    return render_template("pages/reports.html", user_id=current_user.id)


@web_bp.get("/hw1")
def hw1_page():
    return render_template("hw1.html")


@web_bp.get("/explain")
def explain_page():
    return render_template("hw1.html")
