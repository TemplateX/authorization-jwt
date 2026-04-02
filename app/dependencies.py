from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import SessionDep
from app.models import UserModel, TokenModel
from app.tokens_functions import decode_jwr


security = HTTPBearer()


async def get_current_user(
        session: SessionDep,
        auth: HTTPAuthorizationCredentials = Depends(security)
) -> UserModel:

    payload = decode_jwr(auth.credentials)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Токен валиден, но не содержит ID пользователя")

    query = (select(UserModel).where(UserModel.id == user_id).options(joinedload(UserModel.supervisor)))
    result = await session.execute(query)
    user = result.unique().scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Такого пользователя нет")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Этот аккаунт удален")

    return user


async def delete_user_refresh_tokens(user_id: int, session: AsyncSession):
    query = delete(TokenModel).where(TokenModel.user_id == user_id)
    await session.execute(query)