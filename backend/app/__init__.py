from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import db, jwt, bcrypt
from .utils.responses import err

load_dotenv()


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    if not app.config.get("TESTING"):
        for key in ("SECRET_KEY", "JWT_SECRET_KEY", "SQLALCHEMY_DATABASE_URI"):
            if not app.config.get(key):
                raise RuntimeError(f"Missing required environment variable for {key}")

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from . import models  # noqa: F401
    from .routes import register_blueprints
    register_blueprints(app)

    @jwt.unauthorized_loader
    def _missing(reason):
        return err("Authentication required", 401)

    @jwt.invalid_token_loader
    def _invalid(reason):
        return err("Invalid token", 401)

    @jwt.expired_token_loader
    def _expired(header, payload):
        return err("Session expired, please log in again", 401)

    @app.errorhandler(404)
    def _404(e):
        return err("Not found", 404)

    @app.errorhandler(405)
    def _405(e):
        return err("Method not allowed", 405)

    @app.errorhandler(500)
    def _500(e):
        db.session.rollback()
        return err("Something went wrong on our side", 500)

    @app.get("/api/health")
    def health():
        return {"success": True, "data": {"status": "ok", "service": "ElimuPro API"}}

    return app
