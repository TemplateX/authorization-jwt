from fastapi import Depends, APIRouter

from app.models import UserModel
from app.schemas import UserProfileSchema, UserUpdateSchema, UserChangePasswordSchema
from app.database import SessionDep
from app.dependencies import get_current_user, get_profile_service
from app.services.profile_service import ProfileService

router = APIRouter(tags=["Profile"])


@router.get("/profile")
async def get_profile(
        user: UserModel = Depends(get_current_user),
        profile_service: ProfileService = Depends(get_profile_service)
) -> UserProfileSchema:
    return await profile_service.get_profile(user)


@router.delete("/profile")
async def deactivate_profile(
        session: SessionDep,
        user: UserModel = Depends(get_current_user),
        profile_service: ProfileService = Depends(get_profile_service)
):
    return await profile_service.deactivate_profile(user, session)


@router.patch("/profile")
async def edit_profile(
        session: SessionDep,
        data: UserUpdateSchema,
        user: UserModel = Depends(get_current_user),
        profile_service: ProfileService = Depends(get_profile_service)
) -> UserProfileSchema:
    return await profile_service.edit_profile(data, user, session)


@router.post("/profile/change-password")
async def change_user_password(
        session: SessionDep,
        data: UserChangePasswordSchema,
        user: UserModel = Depends(get_current_user),
        profile_service: ProfileService = Depends(get_profile_service)
):
    return await profile_service.change_user_password(data, user, session)
