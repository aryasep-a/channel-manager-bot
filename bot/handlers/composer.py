import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from pyrogram import filters
from pyrogram.types import Message,CallbackQuery
from bot.client import app
from bot.config import settings
from bot.storage.json_store import Stores
from bot.keyboards.menus import channel_picker,confirm_keyboard
from bot.services.permissions import role_of
from bot.services.posting import publish
from bot.services.scheduler import ScheduleService

def register_composer(stores:Stores,scheduler:ScheduleService)->None:
    @app.on_message(filters.private & filters.command(["post","schedule"]))
    async def begin(_,message:Message):
        uid=message.from_user.id
        if not await role_of(uid,stores): return
        mode=message.command[0]; run_at=None
        if mode=="schedule":
            if len(message.command)<3:
                await message.reply_text("Usage: /schedule YYYY-MM-DD HH:MM"); return
            try:
                cfg=await stores.settings.read()
                timezone_name=cfg.get("timezone",settings.timezone)
                dt=datetime.strptime(" ".join(message.command[1:3]),"%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(timezone_name))
                if dt<=datetime.now(ZoneInfo(timezone_name)): raise ValueError
                run_at=dt.isoformat()
            except ValueError:
                await message.reply_text("Invalid or past date. Example: /schedule 2026-12-31 19:30"); return
        app.pending[uid]={"mode":mode,"run_at":run_at}
        await message.reply_text("✍️ <b>POSTING BARU</b>\n━━━━━━━━━━━━━━━━━━━━\nKirim atau teruskan satu pesan yang ingin dipublikasikan.\nKetik /cancel untuk membatalkan.")
    @app.on_message(filters.private & ~filters.command(["start","help","cancel","post","schedule","channels","addchannel","delchannel","setdefault","addadmin","deladmin","admins","stats","history","schedules","cancel_schedule","drafts","settings","setowner","settimezone","setparsemode","templates","template_save"]) & ~filters.regex(r"^(📢 Channels|✍️ Quick Post|🗓 Schedules|📊 Statistics|📝 Drafts|⚙️ Settings)$"))
    async def capture(_,message:Message):
        uid=message.from_user.id; pending=app.pending.get(uid)
        if not pending or not await role_of(uid,stores): return
        channels=await stores.channels.read()
        if not channels["channels"]:
            app.pending.pop(uid,None); await message.reply_text("Belum ada channel terdaftar. Tambahkan dulu dengan <code>/addchannel @username</code>."); return
        pending.update({"source_chat_id":message.chat.id,"source_message_id":message.id})
        app.pending[uid]=pending
        await message.reply_text("📍 <b>PILIH CHANNEL TUJUAN</b>\\nPilih satu atau kirim ke semua channel:",reply_markup=channel_picker(channels["channels"]))
    @app.on_callback_query(filters.regex(r"^target:"))
    async def target(_,query:CallbackQuery):
        if not await role_of(query.from_user.id,stores):
            await query.answer("Akses ditolak.",show_alert=True); return
        pending=app.pending.get(query.from_user.id)
        if not pending: await query.answer("Sesi berakhir. Mulai lagi dengan /post.",show_alert=True); return
        data=await stores.channels.read(); value=query.data.split(":",1)[1]
        selected=data["channels"] if value=="all" else [x for x in data["channels"] if str(x["chat_id"])==value]
        if not selected: await query.answer("Channel not found.",show_alert=True); return
        pending["channel_ids"]=[int(x["chat_id"]) for x in selected]; pending["channel_names"]=[x["title"] for x in selected]
        app.pending[query.from_user.id]=pending
        await query.message.edit_text("Preview destination:\n"+ "\n".join("• "+x["title"] for x in selected),reply_markup=confirm_keyboard(pending["mode"] == "schedule"))
        await query.answer()
    @app.on_callback_query(filters.regex(r"^compose:"))
    async def action(_,query:CallbackQuery):
        uid=query.from_user.id
        if not await role_of(uid,stores):
            await query.answer("Akses ditolak.",show_alert=True); return
        pending=app.pending.get(uid)
        if not pending: await query.answer("Sesi berakhir. Mulai lagi dengan /post.",show_alert=True); return
        action=query.data.split(":")[1]
        if action=="cancel":
            app.pending.pop(uid,None); await query.message.edit_text("✖️ Proses dibatalkan."); await query.answer(); return
        if action=="draft":
            item={"id":uuid.uuid4().hex[:10],"actor_id":uid,**pending,"created_at":datetime.now().astimezone().isoformat()}
            await stores.drafts.update(lambda d:d["drafts"].append(item))
            await query.message.edit_text("💾 <b>DRAFT TERSIMPAN</b>\nID: <code>"+item["id"]+"</code>")
        elif pending["mode"]=="schedule":
            item={"id":uuid.uuid4().hex[:10],"actor_id":uid,"source_chat_id":pending["source_chat_id"],"source_message_id":pending["source_message_id"],"channel_ids":pending["channel_ids"],"run_at":pending["run_at"],"status":"pending"}
            try:
                await scheduler.create(item); await query.message.edit_text("🗓 Schedule created: "+item["id"])
            except Exception as exc: await query.message.edit_text("Schedule failed: "+str(exc))
        else:
            result=await publish(app,stores,pending["source_chat_id"],pending["source_message_id"],pending["channel_ids"],uid)
            ok=sum(1 for x in result if x["ok"])
            failed=[x for x in result if not x["ok"]]
            summary=f"🚀 <b>POSTING SELESAI</b>\nBerhasil: <b>{ok}/{len(result)}</b> channel."
            if failed:
                details="\n".join(f"• <code>{x['channel_id']}</code>: {x.get('error','gagal')[:120]}" for x in failed)
                summary += "\n\n<b>Gagal:</b>\n"+details
            await query.message.edit_text(summary)
        app.pending.pop(uid,None); await query.answer()
