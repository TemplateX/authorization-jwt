from typing import Literal, Self, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import UserRole


class UserSchema(BaseModel):
    user_email: str
    user_name: str
    user_surname: str
    user_patronymic: str

    model_config = ConfigDict(from_attributes=True)


class UserLoginSchema(BaseModel):
    user_email: str
    password: str

    model_config = ConfigDict(extra="forbid")


class UserRegisterSchema(UserSchema):
    password: str
    password_repeat: str
    role: Literal["user", "editor"] = "user"

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError("Пароли не совпадают")
        return self


class UserChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str
    password_repeat: str

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.new_password != self.password_repeat:
            raise ValueError("Новые пароли не совпадают")
        if self.old_password == self.new_password:
            raise ValueError("Новый пароль не должен совпадать со старым")
        return self

    model_config = ConfigDict(extra="forbid")


class UserResponseSchema(UserSchema):
    id: int
    is_active: bool
    role: UserRole
    access_token: str
    token_type: str = "Bearer"
    refresh_token: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileSchema(UserSchema):
    id: int
    is_active: bool
    role: UserRole
    supervisor_id: Optional[int] = None
    supervisor: Optional[UserSchema] = None
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user_email": "boba@example.com",
                "user_name": "Alexey",
                "user_surname": "Popov",
                "user_patronymic": "Ivanovich",
                "id": 1,
                "is_active": True,
                "role": "user",
                "supervisor_id": None,
                "supervisor": {
                    "user_email": "ivan@boss.ru",
                    "user_name": "Ivan",
                    "user_surname": "Petrov",
                    "user_patronymic": "Nikolaevich"
                }
            }
        }
    )


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class UserUpdateSchema(BaseModel):
    user_name: Optional[str] = None
    user_surname: Optional[str] = None
    user_patronymic: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_patronymic": "Новое отчество",
            }
        }
    )


class AdminUserUpdateSchema(UserUpdateSchema):
    user_email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    supervisor_id: Optional[int] = None

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user_patronymic": "Новое отчество",
                "is_active": False
            }
        }
    )
