from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel, UserRole
from app.utils.pwdhash import verify_password, password_to_hash
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas import UserProfileSchema, UserUpdateSchema, UserChangePasswordSchema


class ProfileService:
    def __init__(self, user_repo: UserRepository, token_repo: TokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def get_profile(
            self,
            user: UserModel
    ) -> UserProfileSchema:

        return UserProfileSchema.model_validate(user)

    async def deactivate_profile(
            self,
            user: UserModel,
            session: AsyncSession,
    ):
        if user.role == UserRole.admin:
            raise HTTPException(
                status_code=403,
                detail="Вы не можете себя деактивировать"
            )

        await self.user_repo.deactivate(user)
        await self.token_repo.delete_all_refresh(user.id)
        await session.commit()

        return {"status": True, "detail": "Профиль деактивирован"}

    async def edit_profile(
            self,
            data: UserUpdateSchema,
            user: UserModel,
            session: AsyncSession
    ) -> UserProfileSchema:

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)

        await session.commit()

        updated_user = await self.user_repo.get_by_id_with_supervisor(user.id)

        return UserProfileSchema.model_validate(updated_user)

    async def change_user_password(
            self,
            data: UserChangePasswordSchema,
            user: UserModel,
            session: AsyncSession
    ):
        if not verify_password(data.old_password, user.password):
            raise HTTPException(
                status_code=400,
                detail="Неверный старый пароль"
            )

        user.password = password_to_hash(data.new_password)

        await self.token_repo.delete_all_refresh(user.id)

        await session.commit()
        return {"status": True, "detail": "Пароль обновлен. Refresh токен удален"}
