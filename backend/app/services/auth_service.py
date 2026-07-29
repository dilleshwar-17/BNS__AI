from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.database.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, email: str, username: str, password: str):
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")
        existing = await self.user_repo.get_by_username(username)
        if existing:
            raise ValueError("Username already taken")
        import uuid

        from app.database.models.user import User

        user = User(id=str(uuid.uuid4()), email=email, username=username, hashed_password=hash_password(password))
        return await self.user_repo.create(user)

    async def login(self, username: str, password: str):
        user = await self.user_repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        return {
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
            "user": user,
        }
