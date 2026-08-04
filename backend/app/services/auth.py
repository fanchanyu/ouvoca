from typing import Optional
from datetime import datetime, timedelta, UTC
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC).replace(tzinfo=None) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解碼 JWT（驗證簽名與到期）。失敗拋 jose.JWTError。"""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ─── v3.62 登入鎖定（暴力破解防護）────────────────────────

async def get_login_lock_threshold(db) -> int:
    """從 system_settings 讀鎖定閾值（預設 5 次）。"""
    try:
        from app.services.system_settings import get_setting
        return int(await get_setting(db, "security.login_lockout_threshold", 5) or 5)
    except Exception:
        return 5


def is_login_locked(user) -> bool:
    """使用者目前是否被鎖定。"""
    if user.locked_until is None:
        return False
    locked_until = user.locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    return datetime.now(UTC) < locked_until


def lock_window_minutes() -> int:
    return 15


async def record_failed_login(db, user) -> None:
    """登入失敗：計數 +1；超過閾值鎖定 15 分鐘。"""
    threshold = await get_login_lock_threshold(db)
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= threshold:
        user.locked_until = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            minutes=lock_window_minutes()
        )
        user.failed_login_count = 0
    await db.commit()


async def reset_login_attempts(db, user) -> None:
    if user.failed_login_count or user.locked_until:
        user.failed_login_count = 0
        user.locked_until = None
        await db.commit()


# ─── v3.64 MFA（TOTP）───────────────────────────────────────

def generate_mfa_secret() -> str:
    """產生 TOTP secret（base32）。"""
    import pyotp
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    """驗證 TOTP code（允許 ±1 步漂移）。"""
    import pyotp
    if not secret or not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except Exception:
        return False


def mfa_challenge_token(user) -> str:
    """登入第一步通過密碼後，發出 5 分鐘 MFA 挑戰 token。"""
    return create_token({
        "sub": user.employee_id,
        "username": user.username,
        "mfa_pending": True,
        "permissions": [],
        "ver": user.token_version or 0,
    }, expires_delta=timedelta(minutes=5))
