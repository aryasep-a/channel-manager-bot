from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    api_id: int
    api_hash: str
    owner_id: int
    timezone: str
    log_level: str
    data_dir: Path
def load_settings() -> Settings:
    required = ('BOT_TOKEN','API_ID','API_HASH','OWNER_ID')
    missing = [key for key in required if not os.getenv(key)]
    if missing: raise RuntimeError('Missing environment variables: '+', '.join(missing))
    return Settings(os.environ['BOT_TOKEN'].strip(), int(os.environ['API_ID']), os.environ['API_HASH'].strip(), int(os.environ['OWNER_ID']), os.getenv('TIMEZONE','Asia/Jakarta'), os.getenv('LOG_LEVEL','INFO').upper(), Path(os.getenv('DATA_DIR','data')))
settings = load_settings()
