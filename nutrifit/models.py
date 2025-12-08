from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from . import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.String(64), primary_key=True)  # user_id
    password_hash = db.Column(db.String(128))
    
    # Relationship to profile
    profile = db.relationship("UserProfile", backref="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UserProfile(db.Model):
    __tablename__ = "user_profile"

    user_id = db.Column(db.String(64), db.ForeignKey("user.id"), primary_key=True)
    name = db.Column(db.String(80))
    sex = db.Column(db.String(10))
    age = db.Column(db.Integer)
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    activity_level = db.Column(db.String(20))
    goal_type = db.Column(db.String(20))
    goal_kcal = db.Column(db.Integer)
    allergies = db.Column(db.String(255))
    forbidden = db.Column(db.String(255))
    budget = db.Column(db.Integer)
    exercise_minutes = db.Column(db.Integer, default=0)

    def as_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "activity_level": self.activity_level,
            "goal_type": self.goal_type,
            "goal_kcal": self.goal_kcal,
            "allergies": self.allergies,
            "forbidden": self.forbidden,
            "budget": self.budget,
            "exercise_minutes": self.exercise_minutes or 0,
        }


class FoodLog(db.Model):
    __tablename__ = "food_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.String(64), db.ForeignKey("user_profile.user_id"), nullable=False
    )
    ts = db.Column(db.DateTime, default=datetime.utcnow)
    food_name = db.Column(db.String(120))
    portion_g = db.Column(db.Float)
    kcal = db.Column(db.Float)
    protein_g = db.Column(db.Float)
    fat_g = db.Column(db.Float)
    carb_g = db.Column(db.Float)


class WorkoutLog(db.Model):
    __tablename__ = "workout_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.String(64), db.ForeignKey("user_profile.user_id"), nullable=False
    )
    ts = db.Column(db.DateTime, default=datetime.utcnow)
    workout_name = db.Column(db.String(120))
    minutes = db.Column(db.Integer)
    mets = db.Column(db.Float)
    kcal_burn = db.Column(db.Float)


class CatalogFood(db.Model):
    __tablename__ = "catalog_food"

    food_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    kcal = db.Column(db.Float)
    protein_g = db.Column(db.Float)
    fat_g = db.Column(db.Float)
    carb_g = db.Column(db.Float)
    tags = db.Column(db.String(255))


class CatalogWorkout(db.Model):
    __tablename__ = "catalog_workout"

    workout_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    mets = db.Column(db.Float)
    category = db.Column(db.String(50))
    min_minutes = db.Column(db.Integer)
    max_minutes = db.Column(db.Integer)
