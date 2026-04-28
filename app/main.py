import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.firebase import init_firebase
from app.features.auth.router import router as auth_router
from app.features.categories.router import router as categories_router
from app.features.providers.router import router as providers_router
from app.features.users.router import router as users_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

settings = get_settings()

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

# Firebase
init_firebase()

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(providers_router)


@app.get("/health", description="Health check endpoint to verify the API is running")
async def health_check():
    return {"status": "healthy"}
