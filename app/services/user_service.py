from typing import List

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel, UserRole
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas import UserProfileSchema, AdminUserUpdateSchema


class UserService:
    def __init__(self, user_repo: UserRepository, token_repo: TokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def assign_users(
            self,
            target_id: int,
            user: UserModel,
            session: AsyncSession
    ) -> UserProfileSchema:

        if user.role == UserRole.user:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав"
            )
        elif user.role == UserRole.admin:
            raise HTTPException(
                status_code=403,
                detail="Зайди в админ панель"
            )

        target_user = await self.user_repo.get_by_id(target_id)

        if not target_user:
            raise HTTPException(status_code=404, detail="Такого пользователя нет")
        elif target_user.id == user.id:
            raise HTTPException(status_code=400, detail="Вы не можете назначить самого себя")
        elif target_user.supervisor_id == user.id:
            raise HTTPException(status_code=400, detail="Этот пользователь уже закреплен за вами")
        elif target_user.supervisor_id is not None or not target_user.is_active:
            raise HTTPException(status_code=400, detail="Этого пользователя нельзя назначить себе")
        elif user.role == UserRole.editor and target_user.role != UserRole.user:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав"
            )
        elif user.role == UserRole.moderator and target_user.role != UserRole.editor:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав"
            )
        else:
            target_user.supervisor_id = user.id
            await session.commit()

            updated_user = await self.user_repo.get_by_id_with_supervisor(target_id)

            return UserProfileSchema.model_validate(updated_user)

    async def search_free_users(
            self,
            user: UserModel
    ) -> List[UserProfileSchema]:

        if user.role == UserRole.editor:
            target_role = UserRole.user
        elif user.role == UserRole.moderator:
            target_role = UserRole.editor
        elif user.role == UserRole.admin:
            raise HTTPException(
                status_code=403,
                detail="Зайди в админ панель"
            )
        else:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав"
            )

        users = await self.user_repo.get_free_users(target_role)

        return [UserProfileSchema.model_validate(u) for u in users]

    async def get_my_users(
            self,
            user: UserModel,
    ) -> List[UserProfileSchema]:

        if user.role == UserRole.editor:
            target_role = UserRole.user
        elif user.role == UserRole.moderator:
            target_role = UserRole.editor
        elif user.role == UserRole.admin:
            raise HTTPException(
                status_code=403,
                detail="Зайди в админ панель"
            )
        else:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав"
            )

        users = await self.user_repo.get_users_by_supervisor(user.id, target_role)

        return [UserProfileSchema.model_validate(user) for user in users]

    async def admin_get_user(
            self,
            target_id: int,
            user: UserModel
    ) -> UserProfileSchema:
        if user.role != UserRole.admin:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав"
            )

        target_user = await self.user_repo.get_by_id_with_supervisor(target_id)

        if not target_user:
            raise HTTPException(status_code=404, detail="Такого пользователя нет")

        return UserProfileSchema.model_validate(target_user)

    async def admin_edit_all(
            self,
            data: AdminUserUpdateSchema,
            target_id: int,
            user: UserModel,
            session: AsyncSession,
    ) -> UserProfileSchema:

        if user.role != UserRole.admin:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав"
            )

        target_user = await self.user_repo.get_by_id_with_supervisor(target_id)

        if not target_user:
            raise HTTPException(
                status_code=404,
                detail="Такого пользователя нет"
            )

        if target_user.role == UserRole.admin and target_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав"
            )

        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("role") == UserRole.admin and target_user.role != UserRole.admin:
            raise HTTPException(
                status_code=403,
                detail="У вас нет прав назначать новых администраторов"
            )

        if target_id == user.id:
            if update_data.get("is_active") is False:
                raise HTTPException(
                    status_code=400,
                    detail="Вы не можете себя деактивировать"
                )

            if "role" in update_data and update_data["role"] != UserRole.admin:
                raise HTTPException(
                    status_code=400,
                    detail="Админ не может изменить свою роль"
                )

        if "supervisor_id" in update_data:

            update_supervisor_id = update_data["supervisor_id"]

            if target_user.role == UserRole.admin and update_supervisor_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Администратор не может иметь руководителя"
                )
            if update_supervisor_id == target_id:
                raise HTTPException(
                    status_code=400,
                    detail="Вы не можете назначить самого себя"
                )
            if update_supervisor_id is not None:
                supervisor_data = await self.user_repo.get_by_id(update_supervisor_id)
                if not supervisor_data:
                    raise HTTPException(status_code=404, detail="Такого пользователя нет")
                if supervisor_data.role == UserRole.admin and update_supervisor_id != user.id:
                    raise HTTPException(
                        status_code=403,
                        detail="Вы не можете назначать подчиненных другим администраторам"
                    )
        if "user_email" in update_data:
            new_email = update_data["user_email"]
            if not await self.user_repo.is_email_unique(new_email, target_id):
                raise HTTPException(
                    status_code=400,
                    detail="Пользователь с таким email уже существует"
                )

        for key, value in update_data.items():
            setattr(target_user, key, value)

        if update_data.get("is_active") is False or "role" in update_data:
            await self.token_repo.delete_all_refresh(target_user.id)

        try:
            await session.commit()
        except IntegrityError:
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким email уже существует"
            )

        # так надо. Иначе будет подгружать старые данные супервайзера.
        if "supervisor_id" in update_data:
            # Убираем старый объект из кэша сессии. Иначе ошибка greenlet
            session.expunge(target_user)
            # Загружаем заново с актуальным supervisor
            target_user = await self.user_repo.get_by_id_with_supervisor(target_id)
        return UserProfileSchema.model_validate(target_user)
