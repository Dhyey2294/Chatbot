import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse, ChangePasswordRequest

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in .env — refusing to start.")

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = "http://localhost:8000"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()


# ── JWT helpers ──────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Shared dependency — resolves current user from JWT ───────────────────────

async def get_current_user(
    authorization: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Reads the Authorization header manually (no OAuth2PasswordBearer) so the
    token can also be tested easily from /docs without the lock icon.
    """
    from fastapi import Request

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization header missing.",
    )


# We attach the dependency properly via a helper used by bot_router:
async def get_current_user_from_header(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Placeholder — see auth_dependency below."""
    pass


from fastapi import Header


async def auth_dependency(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    user_id: str = payload.get("sub", "")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered.")

    hashed = pwd_context.hash(body.password)
    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        name=body.name,
        hashed_password=hashed,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.get("/google")
async def google_login():
    if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID == "your-google-client-id-here":
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )
    redirect_uri = f"{BACKEND_URL}/auth/google/callback"
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
    )
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    redirect_uri = f"{BACKEND_URL}/auth/google/callback"

    # 1. Exchange code for tokens
    try:
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_res.json()
            access_token_google = token_data.get("access_token")
            if not access_token_google:
                raise HTTPException(status_code=400, detail="Google OAuth failed: no access token.")

            # 2. Fetch user info from Google
            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token_google}"},
            )
            info = userinfo_res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google OAuth error: {str(e)}")

    google_id = info.get("sub")
    email = info.get("email")
    name = info.get("name", email)
    avatar_url = info.get("picture")

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Could not retrieve email from Google.")

    # 3. Upsert user by google_id or email
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user:
        # Update google fields if logging in via Google for first time on existing account
        user.google_id = google_id
        user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
    else:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    jwt_token = create_access_token(user.id, user.email)

    # 4. Redirect frontend to /auth/callback with token in query param
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(auth_dependency)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )


@router.patch("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_dependency),
):
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=400,
            detail="Cannot change password for accounts created via Google OAuth.",
        )

    if not pwd_context.verify(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect.",
        )

    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=422,
            detail="New password must be at least 6 characters.",
        )

    current_user.hashed_password = pwd_context.hash(body.new_password)
    await db.commit()
    return {"message": "Password updated successfully."}
