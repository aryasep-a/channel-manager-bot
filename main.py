import asyncio,logging
from bot.client import app
from bot.config import settings
from bot.storage.json_store import init_stores
from bot.utils.logging import setup_logging
from bot.services.scheduler import ScheduleService
from bot import runtime
from bot.handlers.common import register_common
from bot.handlers.admin import register_admin
from bot.handlers.channels import register_channels
from bot.handlers.composer import register_composer
from bot.handlers.management import register_management
async def main()->None:
    setup_logging(settings.log_level); log=logging.getLogger("main")
    stores=init_stores(settings.data_dir)
    for store in (stores.admins,stores.channels,stores.drafts,stores.schedules,stores.templates,stores.history,stores.settings,stores.activity):
        await store.read()
    app.pending={}
    runtime.schedule_service=ScheduleService(app,stores,settings.timezone)
    register_common(stores); register_admin(stores); register_channels(stores)
    register_composer(stores,runtime.schedule_service); register_management(stores)
    await app.start(); me=await app.get_me(); log.info("Started as @%s (%s)",me.username,me.id)
    await runtime.schedule_service.start()
    try: await asyncio.Event().wait()
    finally:
        await runtime.schedule_service.shutdown(); await app.stop()
if __name__=="__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
