from typing import List

from fastapi import Depends, APIRouter

from app.models import UserModel
from app.schemas import UserProfileSchema, AdminUserUpdateSchema
from app.database import SessionDep
from app.dependencies import get_current_user, get_user_service
from app.services.user_service import UserService

router = APIRouter(tags=["Users"])


@router.patch("/users/{target_id}/assign-to-me")
async def assign_users(
        target_id: int,
        session: SessionDep,
        user: UserModel = Depends(get_current_user),
        user_service: UserService = Depends(get_user_service)
) -> UserProfileSchema:
    return await user_service.assign_users(target_id, user, session)


@router.get("/users/free-users")
async def search_free_users(
        user: UserModel = Depends(get_current_user),
        user_service: UserService = Depends(get_user_service)
) -> List[UserProfileSchema]:
    return await user_service.search_free_users(user)


@router.get("/users/my-users")
async def get_my_users(
        user: UserModel = Depends(get_current_user),
        user_service: UserService = Depends(get_user_service)
) -> List[UserProfileSchema]:
    return await user_service.get_my_users(user)


@router.get("/admin/users/{target_id}")
async def admin_get_user(
        target_id: int,
        user: UserModel = Depends(get_current_user),
        user_service: UserService = Depends(get_user_service)
) -> UserProfileSchema:
    return await user_service.admin_get_user(target_id, user)


@router.patch("/admin/users/{target_id}")
async def admin_edit_all(
        target_id: int,
        data: AdminUserUpdateSchema,
        session: SessionDep,
        user: UserModel = Depends(get_current_user),
        user_service: UserService = Depends(get_user_service)
) -> UserProfileSchema:
    return await user_service.admin_edit_all(data, target_id, user, session)
