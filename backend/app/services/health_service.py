from app.db.mongodb import mongodb
from app.models.health import HealthStatus


async def check_health() -> HealthStatus:
    try:
        is_connected = await mongodb.ping()
        database_status = "connected" if is_connected else "disconnected"
    except Exception:
        database_status = "disconnected"

    return HealthStatus(status="ok", database=database_status)
