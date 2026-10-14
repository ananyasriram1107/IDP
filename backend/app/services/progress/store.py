from app.db.mongodb import get_database
from app.models.progress import ProgressEvent

COLLECTION_NAME = "progress_events"


async def insert_event(event: ProgressEvent) -> None:
    db = get_database()
    await db[COLLECTION_NAME].insert_one(
        {"_id": event.event_id, **event.model_dump(exclude={"event_id"})}
    )


async def list_events_for_user(user_name: str) -> list[ProgressEvent]:
    db = get_database()
    cursor = db[COLLECTION_NAME].find({"user_name": user_name}).sort("recorded_at", -1)
    records = await cursor.to_list(length=5000)
    return [
        ProgressEvent(event_id=record["_id"], **{k: v for k, v in record.items() if k != "_id"})
        for record in records
    ]
