import uuid
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from pyrogram import filters
from pyrogram.types import CallbackQuery, Message

from bot.client import app
from bot.config import settings
from bot.keyboards.menus import channel_picker, confirm_keyboard
from bot.services.permissions import role_of
from bot.services.posting import publish
from bot.services.scheduler import ScheduleService
from bot.storage.json_store import Stores


EXCLUDED_COMMANDS = [
    "start", "help", "cancel", "post", "schedule", "channels",
    "addchannel", "delchannel", "setdefault", "addadmin", "deladmin",
    "admins", "stats", "history", "schedules", "cancel_schedule",
    "drafts", "settings", "setowner", "settimezone", "templates",
    "template_save",
]


def register_composer(stores: Stores, scheduler: ScheduleService) -> None:
    @app.on_message(filters.private & filters.command(["post", "schedule"]))
    async def begin(_, message: Message):
        user_id = message.from_user.id
        if not await role_of(user_id, stores):
            return

        mode = message.command[0]
        run_at = None

        if mode == "schedule":
            if len(message.command) < 3:
                await message.reply_text(
                    "Format jadwal:\n<code>/schedule YYYY-MM-DD HH:MM</code>"
                )
                return

            try:
                cfg = await stores.settings.read()
                timezone_name = cfg.get("timezone", settings.timezone)
                timezone = ZoneInfo(timezone_name)
                scheduled_at = datetime.strptime(
                    " ".join(message.command[1:3]), "%Y-%m-%d %H:%M"
                ).replace(tzinfo=timezone)

                if scheduled_at <= datetime.now(timezone):
                    raise ValueError("Waktu harus di masa depan.")

                run_at = scheduled_at.isoformat()
            except (ValueError, KeyError):
                await message.reply_text(
                    "Tanggal tidak valid atau sudah lewat.\n"
                    "Contoh: <code>/schedule 2026-12-31 19:30</code>"
                )
                return

        app.pending[user_id] = {"mode": mode, "run_at": run_at}
        heading = "🗓 <b>JADWALKAN POSTING</b>" if mode == "schedule" else "✍️ <b>POSTING BARU</b>"
        await message.reply_text(
            f"{heading}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Kirim atau teruskan satu pesan yang ingin dipublikasikan.\n"
            "Bisa berupa teks, foto, video, atau dokumen.\n\n"
            "Ketik /cancel untuk membatalkan."
        )

    @app.on_message(
        filters.private
        & ~filters.command(EXCLUDED_COMMANDS)
        & ~filters.regex(
            r"^(📢 Channels|✍️ Quick Post|🗓 Schedules|📊 Statistics|📝 Drafts|⚙️ Settings)$"
        )
    )
    async def capture(_, message: Message):
        user_id = message.from_user.id
        pending = app.pending.get(user_id)

        if not pending or not await role_of(user_id, stores):
            return

        channels = (await stores.channels.read())["channels"]
        if not channels:
            app.pending.pop(user_id, None)
            await message.reply_text(
                "Belum ada channel terdaftar.\n"
                "Tambahkan dulu dengan <code>/addchannel @username</code>."
            )
            return

        pending["source_chat_id"] = message.chat.id
        pending["source_message_id"] = message.id
        app.pending[user_id] = pending

        await message.reply_text(
            "📍 <b>PILIH CHANNEL TUJUAN</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Pilih satu channel atau kirim ke semua channel:",
            reply_markup=channel_picker(channels),
        )

    @app.on_callback_query(filters.regex(r"^target:"))
    async def target(_, query: CallbackQuery):
        user_id = query.from_user.id
        if not await role_of(user_id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return

        pending = app.pending.get(user_id)
        if not pending:
            await query.answer("Sesi berakhir. Mulai lagi dengan /post.", show_alert=True)
            return

        channels = (await stores.channels.read())["channels"]
        value = query.data.split(":", 1)[1]
        selected = (
            channels
            if value == "all"
            else [item for item in channels if str(item["chat_id"]) == value]
        )

        if not selected:
            await query.answer("Channel tidak ditemukan.", show_alert=True)
            return

        pending["channel_ids"] = [int(item["chat_id"]) for item in selected]
        pending["channel_names"] = [item["title"] for item in selected]
        app.pending[user_id] = pending

        names = "\n".join(
            f"• {escape(str(item['title']))}" for item in selected
        )
        heading = (
            "🗓 <b>KONFIRMASI JADWAL</b>"
            if pending["mode"] == "schedule"
            else "📋 <b>KONFIRMASI POSTING</b>"
        )
        await query.message.edit_text(
            f"{heading}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Tujuan:</b>\n{names}\n\n"
            "Periksa tujuan sebelum melanjutkan.",
            reply_markup=confirm_keyboard(pending["mode"] == "schedule"),
        )
        await query.answer()

    @app.on_callback_query(filters.regex(r"^compose:"))
    async def action(_, query: CallbackQuery):
        user_id = query.from_user.id
        if not await role_of(user_id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return

        pending = app.pending.get(user_id)
        if not pending:
            await query.answer("Sesi berakhir. Mulai lagi dengan /post.", show_alert=True)
            return

        action_name = query.data.split(":", 1)[1]

        if action_name == "cancel":
            app.pending.pop(user_id, None)
            await query.message.edit_text("✖️ Proses dibatalkan.")
            await query.answer()
            return

        if not all(
            key in pending
            for key in ("source_chat_id", "source_message_id", "channel_ids")
        ):
            await query.answer("Data posting belum lengkap.", show_alert=True)
            return

        if action_name == "draft":
            item = {
                "id": uuid.uuid4().hex[:10],
                "actor_id": user_id,
                **pending,
                "created_at": datetime.now().astimezone().isoformat(),
            }
            await stores.drafts.update(lambda data: data["drafts"].append(item))
            await query.message.edit_text(
                "💾 <b>DRAFT TERSIMPAN</b>\n"
                f"ID: <code>{item['id']}</code>"
            )

        elif action_name == "publish" and pending["mode"] == "schedule":
            item = {
                "id": uuid.uuid4().hex[:10],
                "actor_id": user_id,
                "source_chat_id": pending["source_chat_id"],
                "source_message_id": pending["source_message_id"],
                "channel_ids": pending["channel_ids"],
                "run_at": pending["run_at"],
                "status": "pending",
            }
            try:
                await scheduler.create(item)
                await query.message.edit_text(
                    "🗓 <b>JADWAL BERHASIL DISIMPAN</b>\n"
                    f"ID: <code>{item['id']}</code>\n"
                    f"Waktu: <code>{item['run_at']}</code>"
                )
            except Exception as exc:
                await query.message.edit_text(
                    f"❌ Jadwal gagal disimpan:\n<code>{escape(str(exc)[:250])}</code>"
                )

        elif action_name == "publish":
            results = await publish(
                app,
                stores,
                pending["source_chat_id"],
                pending["source_message_id"],
                pending["channel_ids"],
                user_id,
            )
            succeeded = sum(1 for item in results if item["ok"])
            failed = [item for item in results if not item["ok"]]

            summary = (
                "🚀 <b>POSTING SELESAI</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Berhasil: <b>{succeeded}/{len(results)}</b> channel."
            )
            if failed:
                details = "\n".join(
                    f"• <code>{item['channel_id']}</code>: "
                    f"{escape(item.get('error', 'Gagal')[:120])}"
                    for item in failed
                )
                summary += f"\n\n<b>Gagal:</b>\n{details}"

            await query.message.edit_text(summary)

        else:
            await query.answer("Aksi tidak dikenal.", show_alert=True)
            return

        app.pending.pop(user_id, None)
        await query.answer()
