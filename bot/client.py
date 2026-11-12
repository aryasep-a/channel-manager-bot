from pyrogram import Client
from bot.config import settings
app = Client('channel_manager_bot', api_id=settings.api_id, api_hash=settings.api_hash, bot_token=settings.bot_token, workdir='data')
