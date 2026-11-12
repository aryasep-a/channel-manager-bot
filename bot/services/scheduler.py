from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from pyrogram import Client
from bot.storage.json_store import Stores
from bot.services.posting import publish
class ScheduleService:
    def __init__(self, client: Client, stores: Stores, timezone: str):
        self.client,self.stores,self.tz=client,stores,ZoneInfo(timezone); self.scheduler=AsyncIOScheduler(timezone=self.tz)
    async def start(self):
        self.scheduler.start(); data=await self.stores.schedules.read()
        for item in data['schedules']:
            if item.get('status')!='pending': continue
            when=datetime.fromisoformat(item['run_at'])
            if when.tzinfo is None: when=when.replace(tzinfo=self.tz)
            if when>datetime.now(self.tz): self._add(item['id'],when)
            else: await self._status(item['id'],'missed')
    def _add(self, sid: str, when: datetime): self.scheduler.add_job(self._execute,DateTrigger(run_date=when),args=[sid],id=sid,replace_existing=True,misfire_grace_time=300)
    async def create(self,item:dict):
        when=datetime.fromisoformat(item['run_at'])
        if when.tzinfo is None: when=when.replace(tzinfo=self.tz)
        if when<=datetime.now(self.tz): raise ValueError('Schedule time must be in the future')
        await self.stores.schedules.update(lambda d:d['schedules'].append(item)); self._add(item['id'],when)
    async def _status(self,sid:str,status:str):
        def change(d):
            for x in d['schedules']:
                if x['id']==sid: x['status']=status
        await self.stores.schedules.update(change)
    async def _execute(self,sid:str):
        data=await self.stores.schedules.read(); item=next((x for x in data['schedules'] if x['id']==sid),None)
        if not item or item['status']!='pending': return
        result=await publish(self.client,self.stores,item['source_chat_id'],item['source_message_id'],item['channel_ids'],item['actor_id'],item.get('buttons'))
        await self._status(sid,'sent' if all(x['ok'] for x in result) else 'partial')
    async def cancel(self,sid:str)->bool:
        data=await self.stores.schedules.read()
        if not any(x['id']==sid and x['status']=='pending' for x in data['schedules']): return False
        try: self.scheduler.remove_job(sid)
        except Exception: pass
        await self._status(sid,'cancelled'); return True
    async def shutdown(self):
        if self.scheduler.running: self.scheduler.shutdown(wait=False)
