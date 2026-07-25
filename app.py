"""FastAPI Application Factory."""
import sys
import os

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from weather_station.web.routes import dashboard, designer, settings, logs, api
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
def create_app() -> FastAPI:
    app = FastAPI(title="Weather Station & UI Designer")
    app.mount("/static", StaticFiles(directory="weather_station/web/static"), name="static")
    app.include_router(dashboard.router)
    app.include_router(designer.router)
    app.include_router(settings.router)
    app.include_router(logs.router)
    app.include_router(api.router)
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)