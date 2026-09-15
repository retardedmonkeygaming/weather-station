"""
web/ — FastAPI application, HTTP API endpoints and HTML templates.
"""

from web.routes import create_app, run_web_server

__all__ = ["create_app", "run_web_server"]
