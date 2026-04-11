import os

from fastapi import HTTPException, APIRouter

from app.models import Base, UserRole, UserModel
from app.utils.pwdhash import password_to_hash
from app.database import SessionDep, engine

router = APIRouter(prefix="/service", tags=["Service"])


@router.post(
    "/setup_database",
    summary="Сброс и инициализация базы данных",
    description=(
        "Внимание! Этот эндпоинт полностью удаляет все таблицы и данные "
        "и регистрирует администратора. "
        "Требует секретный ключ, заданный в DATA_BASE_SETUP_KEY."
    ),
)
async def setup_database(
        setup_db_key: str,
        session: SessionDep
):
    if setup_db_key != os.getenv("DATA_BASE_SETUP_KEY"):
        raise HTTPException(status_code=403, detail="Неверный ключ")

    async with engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    hashed_password = password_to_hash(os.getenv("ADMIN_PASSWORD"))

    new_user = UserModel(
        supervisor_id=None,
        role=UserRole.admin,
        user_email=os.getenv("ADMIN_EMAIL"),
        password=hashed_password,
        is_active=True,
        user_name=os.getenv("ADMIN_NAME"),
        user_surname=os.getenv("ADMIN_SURNAME"),
        user_patronymic=os.getenv("ADMIN_PATRONYMIC"),
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return {"status": True, "detail": "База данных очищена. Создан админ"}
