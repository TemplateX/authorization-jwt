from typing import List

from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models import UserRole, UserModel
from app.schemas import UserProfileSchema, AdminUserUpdateSchema
from app.database import SessionDep
from app.dependencies import get_current_user, delete_user_refresh_tokens


router = APIRouter(tags=["Users"])


@router.patch("/users/{target_id}/assign-to-me")
async def assign_users(
        target_id: int,
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
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

    target_user = await session.get(UserModel, target_id)

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
        try:
            target_user.supervisor_id = user.id

            await session.commit()

            query = (
                select(UserModel).where(UserModel.id == target_id).options(joinedload(UserModel.supervisor))
            )

            result = await session.execute(query)
            updated_user = result.unique().scalar_one()

            return UserProfileSchema.model_validate(updated_user)
        except Exception as e:
            await session.rollback()  # Отменяем изменения в бд
            raise e


@router.get("/users/free-users")
async def search_free_users(
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
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

    query = select(UserModel).where(
        UserModel.role == target_role,
        UserModel.supervisor_id == None,
        UserModel.is_active == True
    )
    result = await session.execute(query)
    users = result.scalars().all()

    return [UserProfileSchema.model_validate(u) for u in users]


@router.get("/users/my-users")
async def get_my_users(
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
) -> List[UserProfileSchema]:

    query = select(UserModel).where(
        UserModel.role == UserRole.user,
        UserModel.supervisor_id == user.id
    )

    result = await session.execute(query)
    users = result.scalars().all()

    return [UserProfileSchema.model_validate(user) for user in users]


@router.get("/admin/users/{target_id}")
async def admin_get_user(
        target_id: int,
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
) -> UserProfileSchema:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав"
        )

    target_user = await session.get(UserModel, target_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Такого пользователя нет")

    return UserProfileSchema.model_validate(target_user)


@router.patch("/admin/users/{target_id}")
async def admin_edit_all(
        data: AdminUserUpdateSchema,
        target_id: int,
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
) -> UserProfileSchema:

    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав"
        )

    query = (
        select(UserModel)
        .where(UserModel.id == target_id)
        .options(joinedload(UserModel.supervisor))
    )
    result = await session.execute(query)
    target_user = result.unique().scalar_one_or_none()

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
        if update_supervisor_id == target_id:
            raise HTTPException(
                status_code=400,
                detail="Вы не можете назначить самого себя"
            )
        if update_supervisor_id is not None:
            supervisor_data = await session.get(UserModel, update_supervisor_id)
            if not supervisor_data:
                raise HTTPException(status_code=404, detail="Такого пользователя нет")

            if supervisor_data.role == UserRole.admin and update_supervisor_id != user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Вы не можете назначать подчиненных другим администраторам"
                )
    if "user_email" in update_data:
        new_email = update_data["user_email"]

        result = select(UserModel).where(
            UserModel.user_email == new_email,
            UserModel.id != target_id
        )

        email_check_data = await session.execute(result)
        existing_email_user = email_check_data.scalar_one_or_none()

        if existing_email_user:
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким email уже существует"
            )

    try:
        for key, value in update_data.items():
            setattr(target_user, key, value)

        if update_data.get("is_active") is False or "role" in update_data:
            await delete_user_refresh_tokens(target_user.id, session)

        await session.commit()
        await session.refresh(target_user)

        return UserProfileSchema.model_validate(target_user)

    except Exception as e:
        await session.rollback()
        raise e

