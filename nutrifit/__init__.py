from flask import Flask, redirect, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from .config import get_config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .models import User

    with app.app_context():
        # Ensure tables exist for a quick local MVP run; migrations remain supported.
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    from .api import api_bp
    from .web.views import web_bp
    from .web.auth import auth_bp
    from .api.ai import ai_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_bp, url_prefix="/api/ai")

    @app.route("/")
    def index():
        return redirect("/home", code=302)

    @app.route(
        "/api/v1",
        defaults={"subpath": ""},
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    @app.route(
        "/api/v1/<path:subpath>",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    def api_v1_proxy(subpath: str):
        target = f"/api/{subpath}".rstrip("/") or "/api"
        query = request.query_string.decode()
        if query:
            target = f"{target}?{query}"
        return redirect(target, code=307)

    return app
