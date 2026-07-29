import asyncio
import uuid

from app.core.permissions import Role
from app.core.security import hash_password
from app.database.models.user import User
from app.database.session import async_session_factory


async def main():
    email = input("Admin email: ")
    username = input("Admin username: ")
    password = input("Admin password: ")
    full_name = input("Full name (optional): ") or None

    async with async_session_factory() as session:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            username=username,
            hashed_password=hash_password(password),
            is_active=True,
            role=Role.ADMIN.value,
            full_name=full_name,
        )
        session.add(user)
        await session.flush()
        print(f"Admin user '{username}' created successfully!")


if __name__ == "__main__":
    asyncio.run(main())
