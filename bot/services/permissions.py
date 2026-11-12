from datetime import datetime, timezone

from bot.config import settings
from bot.storage.json_store import Stores


async def owner_id(stores: Stores) -> int:
    data = await stores.settings.read()
    configured = data.get("owner_id")
    return int(configured) if configured else settings.owner_id


async def is_owner(user_id: int, stores: Stores) -> bool:
    return user_id == await owner_id(stores)


async def role_of(user_id: int, stores: Stores) -> str | None:
    if await is_owner(user_id, stores):
        return "owner"
    data = await stores.admins.read()
    if any(int(item["user_id"]) == user_id and item.get("active", True) for item in data["admins"]):
        return "admin"
    return None


async def log_activity(stores: Stores, user_id: int, action: str, detail: str = "") -> None:
    def mutate(data):
        data["events"].append({
            "user_id": user_id,
            "action": action,
            "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        data["events"] = data["events"][-1000:]
    await stores.activity.update(mutate)
