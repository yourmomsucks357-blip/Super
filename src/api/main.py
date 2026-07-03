from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.telemetry import collector
from src.jobs.queue import job_queue
from .routes.agents import router as agents_router
from .routes.telemetry import router as telemetry_router
from .routes.chat import router as chat_router
from .routes.jobs import router as jobs_router
from .routes.workflows import router as workflows_router
from .routes.memory import router as memory_router
from .routes.behavior import router as behavior_router
from .routes.uploads import router as uploads_router

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await collector.start()
    await job_queue.start()
    yield
    await collector.stop()
    await job_queue.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(telemetry_router)
app.include_router(chat_router)
app.include_router(jobs_router)
app.include_router(workflows_router)
app.include_router(memory_router)
app.include_router(behavior_router)
app.include_router(uploads_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def root():
    html = (STATIC_DIR / "index.html").read_text()
    return HTMLResponse(html)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}
