from itsdangerous import URLSafeTimedSerializer
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User
import uuid
import bcrypt

RESET_SECRET = "shopkart-reset-secret-2024"
serializer   = URLSafeTimedSerializer(RESET_SECRET)


def hash_password(password: str) -> str:
    """bcrypt 4.x/5.x compatible password hashing."""
    password_bytes = password.encode("utf-8")
    # bcrypt has a 72-byte hard limit — truncate silently to avoid errors
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt 4.x/5.x compatible password verification."""
    plain_bytes = plain.encode("utf-8")
    if len(plain_bytes) > 72:
        plain_bytes = plain_bytes[:72]
    try:
        return bcrypt.checkpw(plain_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


def login_user(request: Request, user_id: str):
    request.session["user_id"] = user_id


def logout_user(request: Request):
    request.session.clear()


def get_current_user_id(request: Request):
    return request.session.get("user_id")


async def get_current_user(request: Request, db: AsyncSession):
    user_id = get_current_user_id(request)
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def get_session_id(request: Request) -> str:
    sid = request.cookies.get("session_id")
    if not sid:
        sid = "sess_" + str(uuid.uuid4())[:12]
    return sid


def generate_reset_token(email: str) -> str:
    return serializer.dumps(email, salt="password-reset")


def verify_reset_token(token: str, max_age: int = 3600):
    try:
        return serializer.loads(token, salt="password-reset", max_age=max_age)
    except Exception:
        return None
