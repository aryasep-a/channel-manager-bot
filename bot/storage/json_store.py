from __future__ import annotations
import asyncio, json, os, tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
class JSONStore:
    def __init__(self, path: Path, default: Any): self.path, self.default, self._lock = path, default, asyncio.Lock()
    async def read(self) -> Any:
        async with self._lock: return await asyncio.to_thread(self._read_sync)
    def _read_sync(self) -> Any:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists(): self._write_sync(self.default)
        try:
            with self.path.open(encoding='utf-8') as f: return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            backup = self.path.with_suffix(self.path.suffix+'.corrupt')
            try: os.replace(self.path, backup)
            except OSError: pass
            self._write_sync(self.default)
            raise RuntimeError(f'Corrupt JSON store: {backup}') from exc
    async def write(self, value: Any) -> None:
        async with self._lock: await asyncio.to_thread(self._write_sync, value)
    def _write_sync(self, value: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.'+self.path.name, suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(value,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name): os.unlink(name)
    async def update(self, mutator: Callable[[Any], Any]) -> Any:
        async with self._lock:
            value = await asyncio.to_thread(self._read_sync); result = mutator(value)
            await asyncio.to_thread(self._write_sync,value); return result
@dataclass(slots=True)
class Stores:
    admins: JSONStore; channels: JSONStore; drafts: JSONStore; schedules: JSONStore
    templates: JSONStore; history: JSONStore; settings: JSONStore; activity: JSONStore
def init_stores(directory: Path) -> Stores:
    directory.mkdir(parents=True,exist_ok=True)
    return Stores(*[JSONStore(directory/name, default) for name,default in [
        ('admins.json',{'admins':[]}),('channels.json',{'channels':[]}),('drafts.json',{'drafts':[]}),('schedules.json',{'schedules':[]}),('templates.json',{'templates':[]}),('history.json',{'posts':[]}),('settings.json',{'default_channel':None,'owner_id':None,'timezone':'Asia/Jakarta','parse_mode':'html'}),('activity.json',{'events':[]})]])
