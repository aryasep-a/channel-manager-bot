from pyrogram import filters
from pyrogram.types import Message
from bot.client import app
from bot.storage.json_store import Stores
from bot.services.permissions import role_of
from bot.keyboards.menus import main_menu

def register_common(stores: Stores) -> None:
    @app.on_message(filters.private & filters.command("start"))
    async def start(_, message: Message):
        if not await role_of(message.from_user.id,stores):
            await message.reply_text("⛔ Access denied. Ask the Owner to add you as admin."); return
        await message.reply_text("👋 **Channel Manager**\nManage channels, publish posts and schedule messages.",reply_markup=main_menu())
    @app.on_message(filters.private & filters.command("help"))
    async def help_cmd(_,message:Message):
        if not await role_of(message.from_user.id,stores): return
        await message.reply_text("/channels · /addchannel @name · /delchannel ID\n/addadmin ID · /deladmin ID · /admins\n/post · /schedule YYYY-MM-DD HH:MM\n/schedules · /cancel_schedule ID\n/drafts · /history · /stats · /cancel")
    @app.on_message(filters.private & filters.command("cancel"))
    async def cancel(_,message:Message):
        app.pending.pop(message.from_user.id,None); await message.reply_text("Cancelled.",reply_markup=main_menu())
