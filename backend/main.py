from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.pdf import router as pdf_router
from app.api.questions import router as questions_router
from app.db.mongodb import mongodb


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongodb.connect()
    yield
    await mongodb.disconnect()


app = FastAPI(title="PYQ Parser API", lifespan=lifespan)

app.include_router(health_router)
app.include_router(pdf_router)
app.include_router(questions_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "PYQ Parser API", "status": "ok"}
