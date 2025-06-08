import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import uvicorn
from app.core.database import init_db
from app.api.v1.routes import router as api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""

    print("Initializing database...")
    await init_db()
    print("Database initialized successfully")
    
    yield
    

    print("Application shutting down...")



app = FastAPI(
    title=settings.project_name,
    description=f"""
    {settings.project_description}
    

    
    * **Организации** - управление организациями с возможностью поиска и фильтрации
    * **Здания** - управление зданиями с географическими координатами
    * **Виды деятельности** - древовидная структура видов деятельности (до 3 уровней)
    

    
    Все запросы требуют API ключ в заголовке `X-API-Key`.
    По умолчанию используется ключ: `{settings.api_key}`
    

    
    * Поиск организаций по названию
    * Фильтрация по зданию и виду деятельности
    * Географический поиск по радиусу или прямоугольной области
    * Поиск с включением дочерних видов деятельности
    

    
    * Используется PostgreSQL с asyncpg драйвером
    * Миграции управляются через Alembic
    * Поддержка асинхронных операций
    """,
    version=settings.project_version,
    debug=settings.debug,
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
    tags=["API v1"]
)


@app.get("/", include_in_schema=False)
async def root():
    """Перенаправление на документацию API"""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "message": f"{settings.project_name} is running",
        "version": settings.project_version
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Обработчик ошибки 404"""
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Обработчик внутренних ошибок сервера"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", settings.port))
    host = os.getenv("HOST", settings.host)
    debug = settings.debug
    
    print(f"Starting {settings.project_name} v{settings.project_version}")
    print(f"Server will run on {host}:{port}")
    print(f"Debug mode: {debug}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        access_log=True,
        log_level="info" if not debug else "debug"
    )