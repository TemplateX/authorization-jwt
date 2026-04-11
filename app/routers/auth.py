from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, get_auth_service
from app.models import UserModel
from app.schemas import UserRegisterSchema, UserResponseSchema, UserLoginSchema, RefreshTokenSchema
from app.services.auth_service import AuthService
from app.database import SessionDep

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/registration", status_code=201)
async def add_personal_data_and_password(
        data: UserRegisterSchema,
        session: SessionDep,
        auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.add_personal_data_and_password(data, session)


@router.post("/login")
async def login(
        data: UserLoginSchema,
        session: SessionDep,
        auth_service: AuthService = Depends(get_auth_service)
) -> UserResponseSchema:
    return await auth_service.login(data, session)


@router.post("/logout")
async def logout(
        session: SessionDep,
        user: UserModel = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.logout(user.id, session)


@router.post("/refresh")
async def refresh_access_token(
        data: RefreshTokenSchema,
        session: SessionDep,
        auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.refresh_access_token(data, session)
