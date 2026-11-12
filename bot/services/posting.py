from datetime import datetime, timezone
from pyrogram import Client
from bot.storage.json_store import Stores
from bot.services.permissions import log_activity
async def publish(client: Client, stores: Stores, source_chat_id: int, source_message_id: int, channel_ids: list[int], actor_id: int) -> list[dict]:
    results=[]
    for channel_id in channel_ids:
        try:
            sent=await client.copy_message(channel_id,source_chat_id,source_message_id)
            results.append({'channel_id':channel_id,'message_id':sent.id,'ok':True})
            await stores.history.update(lambda d:d['posts'].append({'channel_id':channel_id,'message_id':sent.id,'source_chat_id':source_chat_id,'source_message_id':source_message_id,'actor_id':actor_id,'sent_at':datetime.now(timezone.utc).isoformat()}))
        except Exception as exc: results.append({'channel_id':channel_id,'ok':False,'error':str(exc)[:300]})
    await log_activity(stores,actor_id,'publish',f'{sum(x["ok"] for x in results)}/{len(channel_ids)} channels')
    return results
