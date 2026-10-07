from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        self.client = AsyncIOMotorClient(
            settings.mongodb_url, serverSelectionTimeoutMS=3000
        )
        self.db = self.client[settings.mongodb_db_name]

    async def disconnect(self) -> None:
        if self.client is not None:
            self.client.close()

    async def ping(self) -> bool:
        if self.client is None:
            return False
        await self.client.admin.command("ping")
        return True


mongodb = MongoDB()


def get_database() -> AsyncIOMotorDatabase:
    if mongodb.db is None:
        raise RuntimeError("Database is not connected yet")
    return mongodb.db
