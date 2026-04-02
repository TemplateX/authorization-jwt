from passlib.context import CryptContext
import hashlib

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def password_to_hash(unhashed_string: str):
    return password_context.hash(unhashed_string)


def verify_password(unhashed_password: str, hashed_password: str):
    return password_context.verify(unhashed_password, hashed_password)


def token_to_hash(token: str):
    return hashlib.sha256(token.encode()).hexdigest()

