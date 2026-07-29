import asyncio

from app.database.init_db import init_database


async def main():
    print("Seeding database...")
    await init_database()
    print("Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(main())
