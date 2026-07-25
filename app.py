"""FastAPI Application Factory."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from weather_station.web.routes import dashboard, designer, settings, logs, api


def create_app() -> FastAPI:
    app = FastAPI(title="Weather Station & UI Designer")

    # Static CSS and JS assets
    app.mount("/static", StaticFiles(directory="weather_station/web/static"), name="static")

    # Include Router Endpoints
    app.include_router(dashboard.router)
    app.include_router(designer.router)
    app.include_router(settings.router)
    app.include_router(logs.router)
    app.include_router(api.router)

    return app