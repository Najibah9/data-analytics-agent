import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.config import settings
from app.api.routes import router as api_router

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Data Analytics Dashboard API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(os.path.join("app", "index.html"))


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": settings.LLM_MODEL,
        "upload_dir": settings.UPLOAD_DIR,
    }
