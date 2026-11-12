from datetime import datetime, timezone
from bot.config import settings
from bot.storage.json_store import Stores
async def role_of(user_id: int, stores: Stores) -> str | None:
    if user_id == settings.owner_id: return 'owner'
    data=await stores.admins.read()
    return 'admin' if any(int(x['user_id'])==user_id and x.get('active',True) for x in data['admins']) else None
async def log_activity(stores: Stores, user_id: int, action: str, detail: str='') -> None:
    def mutate(data):
        data['events'].append({'user_id':user_id,'action':action,'detail':detail,'at':datetime.now(timezone.utc).isoformat()}); data['events']=data['events'][-1000:]
    await stores.activity.update(mutate)
