from pyrogram import filters
from pyrogram.types import Message
from bot.client import app
from bot.storage.json_store import Stores
from bot.services.permissions import role_of,log_activity

def register_channels(stores:Stores)->None:
    @app.on_message(filters.private & filters.command(["addchannel","delchannel","channels","setdefault"]))
    async def channel_cmd(_,message:Message):
        uid=message.from_user.id
        if not await role_of(uid,stores): return
        cmd=message.command[0]; data=await stores.channels.read()
        if cmd=="channels":
            await message.reply_text("Channels:\n"+("\n".join(f'{c["title"]} · {c["chat_id"]}' for c in data["channels"]) or "No channels registered.")); return
        if len(message.command)<2:
            await message.reply_text(f"Usage: /{cmd} CHANNEL_ID or @username"); return
        value=message.command[1]
        if cmd=="addchannel":
            try:
                chat=await app.get_chat(value); me=await app.get_me(); member=await app.get_chat_member(chat.id,me.id)
                status=str(member.status).lower()
                if "administrator" not in status and "owner" not in status and "creator" not in status:
                    await message.reply_text("Bot must be an administrator in that channel."); return
                if any(int(c["chat_id"])==int(chat.id) for c in data["channels"]):
                    await message.reply_text("Channel already registered."); return
                data["channels"].append({"chat_id":int(chat.id),"title":chat.title or str(chat.id),"username":chat.username})
                await stores.channels.write(data); await log_activity(stores,uid,"add_channel",str(chat.id))
                await message.reply_text(f"✅ Added {chat.title}.")
            except Exception as exc: await message.reply_text(f"Could not add channel: {exc}")
        elif not value.lstrip("-").isdigit():
            await message.reply_text("Use numeric channel ID."); return
        elif cmd=="delchannel":
            target=int(value); data["channels"]=[c for c in data["channels"] if int(c["chat_id"])!=target]
            await stores.channels.write(data); await message.reply_text("Channel removed.")
        else:
            target=int(value)
            if not any(int(c["chat_id"])==target for c in data["channels"]):
                await message.reply_text("Channel not found."); return
            cfg=await stores.settings.read(); cfg["default_channel"]=target; await stores.settings.write(cfg)
            await message.reply_text("Default channel updated.")
