from typing import TypeVar, Generic, Type, Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepo(Generic[ModelType]):
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self._session = session
        self._model = model

    async def get_by_id(self, user_id: int) -> Optional[ModelType]:
        return await self._session.get(self._model, user_id)

    async def add(self, instance: ModelType) -> ModelType:
        self._session.add(instance)
        return instance

    async def get_one_or_none(self, **filters: Any) -> Optional[ModelType]:
        stmt = select(self._model).filter_by(**filters)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
