from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exam import router as exam_router
from app.api.health import router as health_router
from app.api.intelligence import router as intelligence_router
from app.api.materials import router as materials_router
from app.api.pdf import router as pdf_router
from app.api.progress import router as progress_router
from app.api.questions import router as questions_router
from app.db.mongodb import mongodb


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongodb.connect()
    yield
    await mongodb.disconnect()


app = FastAPI(title="PYQ Parser API", lifespan=lifespan)

# Allows the static frontend (served from a different origin/port, or
# opened directly as a file) to call this API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(pdf_router)
app.include_router(questions_router)
app.include_router(exam_router)
app.include_router(intelligence_router)
app.include_router(materials_router)
app.include_router(progress_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "PYQ Parser API", "status": "ok"}
