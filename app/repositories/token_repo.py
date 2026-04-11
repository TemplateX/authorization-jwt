from typing import TypeVar

from sqlalchemy import delete

from app.models import Base, TokenModel
from app.repositories.base import BaseRepo

ModelType = TypeVar("ModelType", bound=Base)


class TokenRepository(BaseRepo[TokenModel]):
    def __init__(self, session):
        super().__init__(session, TokenModel)

    async def get_by_refresh_hash(self, refresh_hash: str):
        return await self.get_one_or_none(refresh_hash_token=refresh_hash)

    async def delete_all_refresh(self, user_id: int):
        stmt = delete(TokenModel).where(TokenModel.user_id == user_id)
        await self._session.execute(stmt)

    async def delete_token(self, token: TokenModel):
        await self._session.delete(token)
