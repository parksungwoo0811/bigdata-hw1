from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from nutrifit import db
from nutrifit.models import User, UserProfile

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("web.home_page"))
    
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        user = User.query.get(user_id)
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("web.home_page"))
        
        flash("아이디 또는 비밀번호가 올바르지 않습니다.")
    
    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("web.home_page"))
    
    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        
        if User.query.get(user_id):
            flash("이미 존재하는 아이디입니다.")
        else:
            new_user = User(id=user_id)
            new_user.set_password(password)
            
            # Create profile with data from form
            profile_data = {
                "user_id": user_id,
                "name": request.form.get("name"),
                "age": request.form.get("age"),
                "sex": request.form.get("sex"),
                "height_cm": request.form.get("height_cm"),
                "weight_kg": request.form.get("weight_kg"),
                "activity_level": request.form.get("activity_level"),
                "goal_type": request.form.get("goal_type"),
                "goal_kcal": request.form.get("goal_kcal"),
                "exercise_minutes": request.form.get("minutes") or request.form.get("exercise_minutes"),
            }
            # Filter out empty values
            profile_data = {k: v for k, v in profile_data.items() if v}
            
            profile = UserProfile(**profile_data)
            
            # Explicitly link for current session
            new_user.profile = profile
            
            db.session.add(new_user)
            db.session.add(profile)
            db.session.commit()
            
            login_user(new_user)
            return redirect(url_for("web.home_page"))
            
    return render_template("auth/register.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
