from fastapi import HTTPException, Depends, APIRouter

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models import UserRole, UserModel
from app.pwdhash import password_to_hash, verify_password
from app.schemas import UserProfileSchema, UserUpdateSchema, UserChangePasswordSchema
from app.database import SessionDep
from app.dependencies import get_current_user, delete_user_refresh_tokens


router = APIRouter(tags=["Profile"])

@router.get("/profile")
async def get_profile(
        user: UserModel = Depends(get_current_user)
) -> UserProfileSchema:

    return UserProfileSchema.model_validate(user)


@router.delete("/profile")
async def deactivate_profile(
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
):
    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Вы не можете себя деактивировать"
        )
    try:
        user.is_active = False
        await delete_user_refresh_tokens(user.id, session)
        await session.commit()
        return {"status": True, "detail": "Профиль деактивирован"}

    except Exception as e:
        await session.rollback()
        raise e


@router.patch("/profile")
async def edit_profile(
        data: UserUpdateSchema,
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
) -> UserProfileSchema:
    try:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)

        await session.commit()
        query = (
            select(UserModel)
            .where(UserModel.id == user.id)
            .options(joinedload(UserModel.supervisor))
        )
        result = await session.execute(query)
        updated_user = result.unique().scalar_one()

        return UserProfileSchema.model_validate(updated_user)

    except Exception as e:
        await session.rollback()  # Отменяем изменения в бд
        raise e


@router.post("/profile/change-password")
async def change_user_password(
        data: UserChangePasswordSchema,
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
):
    if not verify_password(data.old_password, user.password):
        raise HTTPException(
            status_code=400,
            detail="Неверный старый пароль"
        )

    user.password = password_to_hash(data.new_password)

    await delete_user_refresh_tokens(user.id, session)

    try:
        await session.commit()
        return {"status": True, "detail": "Пароль обновлен. Refresh токен удален"}
    except Exception as e:
        await session.rollback()
        raise e