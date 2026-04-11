from typing import TypeVar, Optional, List

from sqlalchemy.orm import joinedload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base, UserModel, UserRole
from app.repositories.base import BaseRepo

ModelType = TypeVar("ModelType", bound=Base)


class UserRepository(BaseRepo[UserModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserModel)

    async def get_by_email(
            self,
            email: str
    ) -> Optional[UserModel]:
        return await self.get_one_or_none(user_email=email)

    async def get_by_id_with_supervisor(
            self,
            target_id: int
    ) -> Optional[UserModel]:
        stmt = (
            select(self._model).
            where(self._model.id == target_id).
            options(joinedload(self._model.supervisor))
        )
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_free_users(self, target_role: UserRole):
        stmt = select(self._model).where(
            self._model.role == target_role,
            self._model.supervisor_id.is_(None),
            self._model.is_active == True
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_users_by_supervisor(
            self,
            supervisor_id: int,
            role: Optional[UserRole] = None
    ) -> List[UserModel]:
        stmt = select(self._model).where(self._model.supervisor_id == supervisor_id)
        if role is not None:
            stmt = stmt.where(self._model.role == role)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def is_email_unique(
            self,
            email: str,
            exclude_user_id: int
    ) -> bool:
        stmt = select(self._model).where(
            self._model.user_email == email,
            self._model.id != exclude_user_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is None

    async def deactivate(self, user: UserModel) -> UserModel:
        # Ругается, требует сделать метод статическим
        # в profile_service вызывается deactivate_profile так
        # await self.user_repo.deactivate(user)
        user.is_active = False
        return user
