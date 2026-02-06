from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv()

    app = Flask(__name__)

    from app.routes.events import events_bp

    app.register_blueprint(events_bp, url_prefix='/events')

    return app