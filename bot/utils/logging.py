import logging, sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
def setup_logging(level: str) -> None:
    Path('logs').mkdir(exist_ok=True); fmt=logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    root=logging.getLogger(); root.setLevel(getattr(logging,level,logging.INFO)); root.handlers.clear()
    for handler in (logging.StreamHandler(sys.stdout),RotatingFileHandler('logs/bot.log',maxBytes=5000000,backupCount=3,encoding='utf-8')):
        handler.setFormatter(fmt); root.addHandler(handler)
