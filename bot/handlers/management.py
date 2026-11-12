from pyrogram import filters
from pyrogram.types import Message
from bot.client import app
from bot.storage.json_store import Stores
from bot.services.permissions import role_of
from bot import runtime

def register_management(stores:Stores)->None:
    @app.on_message(filters.private & filters.command(["stats","history","schedules","cancel_schedule","drafts","templates","template_save","settings"]))
    async def manage(_,message:Message):
        if not await role_of(message.from_user.id,stores): return
        cmd=message.command[0]
        if cmd=="stats":
            h=await stores.history.read(); c=await stores.channels.read(); today=__import__("datetime").datetime.now().astimezone().date().isoformat()
            await message.reply_text(f"Total posts: {len(h['posts'])}\\nToday: {sum(x['sent_at'].startswith(today) for x in h['posts'])}\\nActive channels: {len(c['channels'])}")
        elif cmd=="history":
            h=(await stores.history.read())["posts"][-15:]
            await message.reply_text("Recent posts:\\n"+("\\n".join(f"{x['channel_id']} / {x['message_id']} / {x['sent_at']}" for x in reversed(h)) or "Empty."))
        elif cmd=="schedules":
            rows=(await stores.schedules.read())["schedules"][-20:]
            await message.reply_text("Schedules:\\n"+("\\n".join(f"{x['id']} | {x['run_at']} | {x['status']}" for x in rows) or "Empty."))
        elif cmd=="cancel_schedule":
            if len(message.command)<2: await message.reply_text("Usage: /cancel_schedule ID"); return
            ok=await runtime.schedule_service.cancel(message.command[1])
            await message.reply_text("Schedule cancelled." if ok else "Pending schedule not found.")
        elif cmd=="drafts":
            rows=(await stores.drafts.read())["drafts"][-20:]
            await message.reply_text("Draft IDs:\\n"+("\\n".join(x["id"] for x in rows) or "Empty."))
        elif cmd=="template_save":
            if not message.reply_to_message or len(message.command)<2:
                await message.reply_text("Reply to a message with /template_save NAME."); return
            item={"name":message.command[1],"source_chat_id":message.reply_to_message.chat.id,"source_message_id":message.reply_to_message.id,"created_by":message.from_user.id}
            await stores.templates.update(lambda d:d["templates"].append(item)); await message.reply_text("Template reference saved.")
        elif cmd=="templates":
            rows=(await stores.templates.read())["templates"]
            await message.reply_text("Templates:\\n"+("\\n".join(x["name"] for x in rows) or "Empty."))
        else:
            cfg=await stores.settings.read()
            await message.reply_text(f"Default channel: {cfg.get('default_channel')}\\nParse mode: {cfg.get('parse_mode')}\\nTimezone: {settings_timezone()}")

    @app.on_message(filters.private & filters.regex(r"^(📢 Channels|✍️ Quick Post|🗓 Schedules|📊 Statistics|📝 Drafts|⚙️ Settings)$"))
    async def menu(_,message:Message):
        if not await role_of(message.from_user.id,stores): return
        label=message.text
        if label=="📢 Channels":
            rows=(await stores.channels.read())["channels"]
            listing="\\n".join(f"• {x['title']} · {x['chat_id']}" for x in rows) or "Belum ada channel terdaftar."
            await message.reply_text("📢 **Channel Manager**\\n\\n"+listing+"\\n\\nTambah channel dengan:\\n/addchannel @username\\n\\nPastikan bot sudah menjadi admin channel.")
        elif label=="⚙️ Settings":
            cfg=await stores.settings.read()
            await message.reply_text(f"⚙️ **Settings**\\nDefault channel: {cfg.get('default_channel')}\\nParse mode: {cfg.get('parse_mode')}\\nTimezone: {settings_timezone()}")
        elif label=="✍️ Quick Post":
            app.pending[message.from_user.id]={"mode":"post","run_at":None}
            await message.reply_text("Kirim atau forward SATU pesan yang ingin dipublikasikan. Gunakan /cancel untuk membatalkan.")
        elif label=="🗓 Schedules":
            rows=(await stores.schedules.read())["schedules"][-20:]
            await message.reply_text("Schedules:\\n"+("\\n".join(f"{x['id']} | {x['run_at']} | {x['status']}" for x in rows) or "Belum ada jadwal."))
        elif label=="📊 Statistics":
            h=await stores.history.read(); c=await stores.channels.read(); today=__import__("datetime").datetime.now().astimezone().date().isoformat()
            await message.reply_text(f"📊 **Statistics**\\nTotal posts: {len(h['posts'])}\\nToday: {sum(x['sent_at'].startswith(today) for x in h['posts'])}\\nActive channels: {len(c['channels'])}")
        elif label=="📝 Drafts":
            rows=(await stores.drafts.read())["drafts"][-20:]
            await message.reply_text("Draft IDs:\\n"+("\\n".join(x["id"] for x in rows) or "Belum ada draft."))

def settings_timezone()->str:
    from bot.config import settings
    return settings.timezone
