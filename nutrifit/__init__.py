from flask import Flask, redirect, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .config import get_config

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        # Ensure tables exist for a quick local MVP run; migrations remain supported.
        db.create_all()

    from .api import api_bp
    from .web.views import web_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)

    @app.route("/")
    def index():
        return redirect("/home?user_id=demo", code=302)

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
