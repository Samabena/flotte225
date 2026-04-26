from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Flotte225 API",
    version="1.0.0",
    docs_url="/docs" if settings.SHOW_DOCS else None,
    redoc_url="/redoc" if settings.SHOW_DOCS else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Disable caching for static assets in dev so JS/HTML edits are picked up
# without manual hard-reloads. API responses are unaffected.
@app.middleware("http")
async def no_cache_static(request: Request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith("/api/") and request.url.path != "/health":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Rewrite clean URLs (e.g. /vehicles) to their .html counterpart so
# StaticFiles can serve them without exposing the extension in the browser.
@app.middleware("http")
async def clean_url_rewrite(request: Request, call_next):
    path = request.scope["path"]
    last_segment = path.split("/")[-1]
    if (
        not path.startswith("/api/")
        and path not in ("/health", "/docs", "/redoc", "/openapi.json")
        and path != "/"
        and "." not in last_segment
        and last_segment != ""
    ):
        request.scope["path"] = path + ".html"
    return await call_next(request)


# Serve the frontend in development only — in production the frontend is a
# separate static site service (e.g. Render static site) so no mount needed.
if settings.ENVIRONMENT == "development":
    app.mount("/", StaticFiles(directory="/frontend", html=True), name="frontend")
