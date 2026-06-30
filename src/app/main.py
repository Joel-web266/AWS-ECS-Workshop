"""Application entry point for the ECS Workshop."""

import logging
import os
import secrets

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from src.app.routes import api

logger = logging.getLogger(__name__)


def create_app(config=None):
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

    if config:
        app.config.update(config)

    app.register_blueprint(api)
    _register_error_handlers(app)

    return app


def _register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        logger.warning("HTTP %d: %s - %s", exc.code, exc.name, exc.description)
        return jsonify({
            "error": exc.name,
            "message": exc.description,
            "status_code": exc.code,
        }), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        logger.exception("Unhandled exception: %s", exc)
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
        }), 500


if __name__ == "__main__":
    application = create_app()
    application.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )
