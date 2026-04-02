from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import JSONResponse

from app.database import engine
from app.models import Base
from app.routers.auth import router as auth_router
from app.routers.profile import router as profile_router
from app.routers.users import router as users_router
from app.routers.service import router as service_router


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    async with engine.begin() as conn:
        print(f"База данных для '{app_instance.title}' готова к работе.")
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


router = APIRouter(prefix="/service", tags=["Service"])

app = FastAPI(title="Система аутентификации и авторизации", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(
        request: Request,
        exc: Exception
):
    print(f"Ошибка в {request.method} {request.url}")
    print(f"Текст ошибки: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Что-то пошло не так на сервере. Мы уже работаем над этим."}
    )


app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(users_router)
app.include_router(service_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
