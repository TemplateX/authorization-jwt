from datetime import datetime, timezone
import asyncio

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserRole, UserModel, TokenModel
from app.utils.pwdhash import password_to_hash, verify_password, token_to_hash
from app.schemas import UserRegisterSchema, UserResponseSchema, UserLoginSchema, RefreshTokenSchema
from app.utils.tokens_functions import data_to_tokens
from app.repositories.token_repo import TokenRepository
from app.repositories.user_repo import UserRepository

fake_stupid_hash_password_empty = "$2b$12$.WiReYlihvc/hUdyj7nfnOEvxHSGBL443xMWBGcv8Gpg02fESq4ZG"


class AuthService:
    def __init__(self, user_repo: UserRepository, token_repo: TokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def login(
            self,
            data: UserLoginSchema,
            session: AsyncSession
    ) -> UserResponseSchema:

        user = await self.user_repo.get_by_email(data.user_email)

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

                await self.token_repo.add(new_token_entry)
                await session.commit()

                user.access_token = new_access_token
                user.refresh_token = new_refresh_token

                return UserResponseSchema.model_validate(user)
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        else:

            verify_password(data.password, fake_stupid_hash_password_empty)
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    async def add_personal_data_and_password(
            self,
            data: UserRegisterSchema,
            session: AsyncSession
    ):
        user = await self.user_repo.get_by_email(data.user_email)

        hashed_password = password_to_hash(data.password)

        if user:
            await asyncio.sleep(0.06)
            print("Кто-то (возможно, вы) пытался зарегистрировать "
                  "новый аккаунт с этим email. Если это были вы — логин происходит на /auth/login")
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

        try:
            await self.user_repo.add(new_user)
            await session.commit()
        except IntegrityError:
            await asyncio.sleep(0.06)  # имитируем задержку для тайминг-защиты
            print("IntegrityError: возможно, параллельный запрос создал такого пользователя")
            return {"status": True}

        print("ОТПРАВЛЯЮ НА ПОЧТУ КОД ПОДТВЕРЖЕНИЯ")

        return {"status": True}

    async def refresh_access_token(
            self,
            data: RefreshTokenSchema,
            session: AsyncSession
    ):
        refresh_hash_token = token_to_hash(data.refresh_token)

        db_token = await self.token_repo.get_by_refresh_hash(refresh_hash_token)

        if not db_token:
            raise HTTPException(status_code=401, detail="refresh_token не найден")

        if db_token.expires < datetime.now(timezone.utc).replace(tzinfo=None):
            await self.token_repo.delete_token(db_token)
            await session.commit()
            raise HTTPException(status_code=401, detail="refresh_token просрочен")

        user = await self.user_repo.get_by_id(db_token.user_id)

        new_access_token, new_refresh_token, new_refresh_expire, refresh_hash_token = data_to_tokens(db_token.user_id,
                                                                                                     user.role.value)
        db_token.refresh_hash_token = refresh_hash_token
        db_token.expires = new_refresh_expire

        await session.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer"
        }

    async def logout(
            self,
            user_id: int,
            session: AsyncSession
    ) -> dict:
        await self.token_repo.delete_all_refresh(user_id)
        await session.commit()
        return {
            "Status": True,
            "detail": "Успешный выход. refresh токены удалены. Фронтенд, удали JWT токен."
        }
