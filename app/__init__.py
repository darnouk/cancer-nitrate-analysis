from flask import Flask

def create_app():
    import os
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    app = Flask(__name__,
                static_folder=os.path.join(base_dir, "static"),
                template_folder=os.path.join(base_dir, "app", "templates"))

    from .routes import main
    app.register_blueprint(main)

    return app
