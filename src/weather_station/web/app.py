import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# This finds the directory where THIS file (app.py) lives
BASE_DIR = Path(__file__).resolve().parent

# Mount static and templates using absolute paths
# It will now find the folders correctly relative to app.py
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))