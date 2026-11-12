from pyrogram import filters
from pyrogram.types import Message
from bot.client import app
from bot.config import settings
from bot.storage.json_store import Stores
from bot.services.permissions import log_activity

def register_admin(stores:Stores)->None:
    @app.on_message(filters.private & filters.command(["addadmin","deladmin","admins"]))
    async def admin_cmd(_,message:Message):
        uid=message.from_user.id
        if uid!=settings.owner_id:
            await message.reply_text("Only the Owner can manage admins."); return
        data=await stores.admins.read(); cmd=message.command[0]
        if cmd=="admins":
            await message.reply_text("Admins:\n"+("\n".join(str(x["user_id"]) for x in data["admins"]) or "None")); return
        if len(message.command)<2 or not message.command[1].isdigit():
            await message.reply_text(f"Usage: /{cmd} USER_ID"); return
        target=int(message.command[1])
        if target==settings.owner_id: await message.reply_text("Owner is already privileged."); return
        if cmd=="addadmin":
            if any(int(x["user_id"])==target for x in data["admins"]):
                await message.reply_text("Already an admin."); return
            data["admins"].append({"user_id":target,"active":True})
        else: data["admins"]=[x for x in data["admins"] if int(x["user_id"])!=target]
        await stores.admins.write(data); await log_activity(stores,uid,cmd,str(target))
        await message.reply_text("✅ Admin list updated.")
