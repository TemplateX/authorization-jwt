from datetime import datetime, timezone
import asyncio

from fastapi import HTTPException, APIRouter, Depends
from sqlalchemy import select

from app.dependencies import get_current_user, delete_user_refresh_tokens
from app.models import UserRole, UserModel, TokenModel
from app.pwdhash import password_to_hash, verify_password, token_to_hash
from app.schemas import UserRegisterSchema, UserResponseSchema, UserLoginSchema, RefreshTokenSchema
from app.tokens_functions import data_to_tokens
from app.database import SessionDep

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/refresh")
async def refresh_access_token(
        data: RefreshTokenSchema,
        session: SessionDep
):
    refresh_hash_token = token_to_hash(data.refresh_token)
    query = select(TokenModel).where(TokenModel.refresh_hash_token == refresh_hash_token)
    result = await session.execute(query)
    db_token = result.scalar_one_or_none()
    if not db_token:
        raise HTTPException(status_code=401, detail="refresh_token не найден")

    if db_token.expires < datetime.now(timezone.utc).replace(tzinfo=None):
        await session.delete(db_token)
        await session.commit()
        raise HTTPException(status_code=401, detail="refresh_token просрочен")

    user_query = select(UserModel).where(UserModel.id == db_token.user_id)
    user_result = await session.execute(user_query)
    user = user_result.scalar_one_or_none()

    new_access_token, new_refresh_token, new_refresh_expire, refresh_hash_token = data_to_tokens(db_token.user_id, user.role.value)

    db_token.refresh_hash_token = refresh_hash_token
    db_token.expires = new_refresh_expire

    await session.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer"
    }


@router.post("/registration", status_code=201)
async def add_personal_data_and_password(
        data: UserRegisterSchema,
        session: SessionDep
):
    query = select(UserModel).where(UserModel.user_email == data.user_email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    hashed_password = password_to_hash(data.password)

    if user:
        await asyncio.sleep(0.06)
        print("Кто-то (возможно, вы) пытался зарегистрировать "
              "новый аккаунт с этим email. Если это были вы — логин просиходит на /auth/login")
        # возвращаю "status": True чтобы не раскрывать существование аккаунта злоумышленникам
        return {"status": True}

    new_user = UserModel(
        user_email=data.user_email,
        password=hashed_password,
        is_active=True,
        user_name=data.user_name,
        user_surname=data.user_surname,
        user_patronymic=data.user_patronymic,
        role=UserRole(data.role)
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    print("ОТПРАВЛЯЮ НА ПОЧТУ КОД ПОДТВЕРЖЕНИЯ")

    return {"status": True}


@router.post("/login")
async def get_email_and_password(
        data: UserLoginSchema,
        session: SessionDep
) -> UserResponseSchema:

    query = select(UserModel).where(UserModel.user_email == data.user_email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user:
        if verify_password(data.password, user.password):
            if not user.is_active:
                raise HTTPException(status_code=401, detail="Вы удалили аккаунт.")

            new_access_token, new_refresh_token, new_refresh_expire, refresh_hash_token = data_to_tokens(user.id,
                                                                                                   user.role.value)
            new_token_entry = TokenModel(
                user_id=user.id,
                refresh_hash_token=refresh_hash_token,
                expires=new_refresh_expire
            )

            session.add(new_token_entry)
            await session.commit()
            await session.refresh(new_token_entry)

            user.access_token = new_access_token
            user.refresh_token = new_refresh_token

            return UserResponseSchema.model_validate(user)
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    else:
        fake_stupid_hash_password_empty = "$2b$12$.WiReYlihvc/hUdyj7nfnOEvxHSGBL443xMWBGcv8Gpg02fESq4ZG"
        verify_password(data.password, fake_stupid_hash_password_empty)
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")


@router.post("/logout")
async def logout(
        session: SessionDep,
        user: UserModel = Depends(get_current_user)
):
    try:
        await delete_user_refresh_tokens(user.id, session)
        await session.commit()

        return {"Status": True, "detail": "Успешный выход. refresh токены удалены. Фронтенд, удали JWT токен."
        }
    except Exception as e:
        await session.rollback()
        raise e