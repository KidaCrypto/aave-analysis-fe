from flask import Flask
from .views import views
from .api import api

def create_app():
    app = Flask(__name__)
    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(api, url_prefix="/api/")

    return app