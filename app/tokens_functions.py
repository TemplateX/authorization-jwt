import os
import uuid
import datetime

from dotenv import load_dotenv
import jwt
from fastapi import HTTPException

from app.pwdhash import token_to_hash


load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

def data_to_tokens(user_id: int, user_role: str):
    payload = {
        "user_id": user_id,
        "user_role": user_role,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    }

    access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token = str(uuid.uuid4())
    refresh_expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    refresh_hash = token_to_hash(refresh_token)


    return access_token, refresh_token, refresh_expire, refresh_hash


def decode_jwr(jwt_token: str) -> dict:
    try:
        return jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Срок действия токена истек")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Неверный токен")

