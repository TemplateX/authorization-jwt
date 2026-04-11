from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import SessionDep
from app.models import UserModel
from app.services.auth_service import AuthService
from app.services.profile_service import ProfileService
from app.services.user_service import UserService
from app.utils.tokens_functions import decode_jwr
from app.repositories.user_repo import UserRepository
from app.repositories.token_repo import TokenRepository

security = HTTPBearer()


def get_user_repo(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_token_repo(session: SessionDep) -> TokenRepository:
    return TokenRepository(session)


def get_auth_service(
        user_repo: UserRepository = Depends(get_user_repo),
        token_repo: TokenRepository = Depends(get_token_repo)
) -> AuthService:
    return AuthService(user_repo, token_repo)


def get_profile_service(
        user_repo: UserRepository = Depends(get_user_repo),
        token_repo: TokenRepository = Depends(get_token_repo)
) -> ProfileService:
    return ProfileService(user_repo, token_repo)


def get_user_service(
        user_repo: UserRepository = Depends(get_user_repo),
        token_repo: TokenRepository = Depends(get_token_repo)
) -> UserService:
    return UserService(user_repo, token_repo)


async def get_current_user(
        auth: HTTPAuthorizationCredentials = Depends(security),
        user_repo: UserRepository = Depends(get_user_repo)
) -> UserModel:
    payload = decode_jwr(auth.credentials)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Токен валиден, но не содержит ID пользователя")

    user = await user_repo.get_by_id_with_supervisor(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Такого пользователя нет")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Этот аккаунт удален")

    return user
