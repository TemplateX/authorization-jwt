from datetime import datetime
import enum
from typing import Optional

from sqlalchemy import ForeignKey, Enum, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(enum.Enum):
    admin = "admin"
    moderator = "moderator"
    editor = "editor"
    user = "user"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    supervisor = relationship("UserModel", remote_side="UserModel.id")
    supervisor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)
    user_email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    is_active: Mapped[bool]
    user_name: Mapped[str]
    user_surname: Mapped[str]
    user_patronymic: Mapped[str]


class TokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_hash_token: Mapped[str]
