import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.routers import generate


@asynccontextmanager
async def lifespan(app: FastAPI):
    temp_dir = os.getenv("TEMP_DIR", "/tmp/thumbnails")
    os.makedirs(temp_dir, exist_ok=True)
    conv_dir = os.getenv("TEMP_DIR", "/tmp/conversions")
    os.makedirs(conv_dir, exist_ok=True)
    yield


app = FastAPI(
    title="unoconv-api",
    description="REST API for thumbnails and file conversion using LibreOffice",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy", "service": "unoconv-api"}