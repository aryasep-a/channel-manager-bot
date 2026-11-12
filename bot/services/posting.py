from datetime import datetime, timezone

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.storage.json_store import Stores
from bot.services.permissions import log_activity


def _keyboard(buttons: list[list[dict]] | None):
    if not buttons:
        return None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text=item["text"], url=item["url"]) for item in row]
        for row in buttons
    ])


async def publish(
    client: Client,
    stores: Stores,
    source_chat_id: int,
    source_message_id: int,
    channel_ids: list[int],
    actor_id: int,
    buttons: list[list[dict]] | None = None,
) -> list[dict]:
    results = []
    markup = _keyboard(buttons)
    for channel_id in channel_ids:
        try:
            sent = await client.copy_message(
                chat_id=channel_id,
                from_chat_id=source_chat_id,
                message_id=source_message_id,
                reply_markup=markup,
            )
            results.append({"channel_id": channel_id, "message_id": sent.id, "ok": True})
            await stores.history.update(lambda data: data["posts"].append({
                "channel_id": channel_id,
                "message_id": sent.id,
                "source_chat_id": source_chat_id,
                "source_message_id": source_message_id,
                "actor_id": actor_id,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "has_buttons": bool(buttons),
            }))
        except Exception as exc:
            results.append({"channel_id": channel_id, "ok": False, "error": str(exc)[:300]})
    await log_activity(stores, actor_id, "publish", f"{sum(item['ok'] for item in results)}/{len(channel_ids)} channels")
    return results
