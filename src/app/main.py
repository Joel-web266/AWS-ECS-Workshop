"""Application entry point for the ECS Workshop."""

from flask import Flask

from src.app.routes import api


def create_app(config=None):
    app = Flask(__name__)

    if config:
        app.config.update(config)

    app.register_blueprint(api)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=True)
