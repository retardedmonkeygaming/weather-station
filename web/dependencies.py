"""FastAPI Jinja2 templates dependency."""
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="weather_station/web/templates")