import uuid
from datetime import datetime
from html import escape
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from pyrogram import filters
from pyrogram.types import CallbackQuery, Message

from bot.client import app
from bot.config import settings
from bot.keyboards.menus import (
    channel_picker, confirm_keyboard, content_options, button_builder, cancel_keyboard, back_menu,
)
from bot.services.permissions import role_of
from bot.services.posting import publish
from bot.services.scheduler import ScheduleService
from bot.storage.json_store import Stores


EXCLUDED_COMMANDS = [
    "start", "help", "cancel", "post", "schedule", "channels",
    "addchannel", "delchannel", "setdefault", "addadmin", "deladmin",
    "admins", "stats", "history", "schedules", "cancel_schedule",
    "drafts", "settings", "setowner", "settimezone", "templates",
    "template_save", "update", "restart",
]


def _destination_prompt(channels: list[dict]) -> tuple[str, object]:
    return (
        "📍 <b>PILIH CHANNEL TUJUAN</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih satu channel atau kirim ke semua channel:",
        channel_picker(channels),
    )


async def _show_destinations(message, stores: Stores, pending: dict) -> None:
    channels = (await stores.channels.read())["channels"]
    if not channels:
        await message.reply_text("Belum ada channel terdaftar. Buka Channels → Tambah channel.")
        return
    pending["stage"] = "choose_target"
    text, keyboard = _destination_prompt(channels)
    await message.reply_text(text, reply_markup=keyboard)


def register_composer(stores: Stores, scheduler: ScheduleService) -> None:
    @app.on_callback_query(filters.regex(r"^menu:post$"))
    async def quick_post(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        app.pending[query.from_user.id] = {
            "mode": "post", "run_at": None, "buttons": [], "stage": "content"
        }
        await query.message.reply_text(
            "✍️ <b>POSTING BARU</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "Kirim teks, foto, video, GIF, atau dokumen yang ingin diposting.\n"
            "Setelah itu lu bisa menambahkan tombol URL atau langsung lanjut tanpa tombol.",
            reply_markup=cancel_keyboard(),
        )
        await query.answer()

    @app.on_callback_query(filters.regex(r"^menu:schedule$"))
    async def schedule_from_menu(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        app.pending[query.from_user.id] = {"mode": "schedule", "run_at": None, "buttons": [], "stage": "schedule_time"}
        await query.message.reply_text(
            "🗓 <b>JADWALKAN POSTING</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "Kirim tanggal dan waktu dengan format <code>YYYY-MM-DD HH:MM</code>.\n"
            "Zona waktu mengikuti Settings.",
            reply_markup=cancel_keyboard(),
        )
        await query.answer()

    @app.on_message(filters.private & filters.command(["post", "schedule"]))
    async def begin(_, message: Message):
        user_id = message.from_user.id
        if not await role_of(user_id, stores):
            return
        mode = message.command[0]
        run_at = None
        if mode == "schedule":
            if len(message.command) < 3:
                await message.reply_text("Format: <code>/schedule YYYY-MM-DD HH:MM</code>")
                return
            try:
                cfg = await stores.settings.read()
                tz = ZoneInfo(cfg.get("timezone", settings.timezone))
                when = datetime.strptime(" ".join(message.command[1:3]), "%Y-%m-%d %H:%M").replace(tzinfo=tz)
                if when <= datetime.now(tz):
                    raise ValueError
                run_at = when.isoformat()
            except (ValueError, KeyError):
                await message.reply_text("Tanggal tidak valid atau sudah lewat. Contoh: <code>/schedule 2026-12-31 19:30</code>")
                return
        app.pending[user_id] = {"mode": mode, "run_at": run_at, "buttons": [], "stage": "content"}
        await message.reply_text(
            "✍️ <b>KIRIM KONTEN</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "Kirim teks, foto, video, GIF, atau dokumen yang ingin dipublikasikan.",
            reply_markup=cancel_keyboard(),
        )

    composer_input_filter = filters.create(
        lambda _, __, message: bool(message.from_user and message.from_user.id in app.pending)
    )

    @app.on_message(filters.private & composer_input_filter & ~filters.command(EXCLUDED_COMMANDS))
    async def capture(_, message: Message):
        user_id = message.from_user.id
        pending = app.pending.get(user_id)
        if not pending or not await role_of(user_id, stores):
            return

        stage = pending.get("stage", "content")

        if stage == "schedule_time":
            try:
                cfg = await stores.settings.read()
                tz = ZoneInfo(cfg.get("timezone", settings.timezone))
                when = datetime.strptime((message.text or "").strip(), "%Y-%m-%d %H:%M").replace(tzinfo=tz)
                if when <= datetime.now(tz):
                    raise ValueError
                pending["run_at"] = when.isoformat()
                pending["stage"] = "content"
                await message.reply_text("✅ Waktu tersimpan. Sekarang kirim teks, foto, video, GIF, atau dokumen yang akan dijadwalkan.", reply_markup=cancel_keyboard())
            except (ValueError, KeyError):
                await message.reply_text("Format salah atau waktu sudah lewat. Contoh: <code>2026-12-31 19:30</code>")
            return

        if stage == "button_label":
            label = (message.text or "").strip()
            if not label or len(label) > 64:
                await message.reply_text("Label tombol wajib 1–64 karakter. Kirim ulang labelnya.")
                return
            pending["button_label"] = label
            pending["stage"] = "button_url"
            await message.reply_text("Sekarang kirim URL tujuan, harus diawali http:// atau https://.", reply_markup=cancel_keyboard())
            return

        if stage == "button_url":
            url = (message.text or "").strip()
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                await message.reply_text("URL tidak valid. Kirim URL lengkap, contoh: https://example.com")
                return
            pending.setdefault("buttons", []).append([{
                "text": pending.pop("button_label"),
                "url": url,
            }])
            pending["stage"] = "button_menu"
            app.pending[user_id] = pending
            names = "\n".join(f"• {escape(row[0]['text'])}" for row in pending["buttons"])
            await message.reply_text(
                "🔘 <b>TOMBOL DITAMBAHKAN</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"{names}\n\nTambah tombol lain atau lanjut ke pilihan channel:",
                reply_markup=button_builder(),
            )
            return

        if stage != "content":
            await message.reply_text("Gunakan tombol yang tersedia untuk melanjutkan proses.")
            return

        if not (message.text or message.caption or message.photo or message.video or message.document or message.animation):
            await message.reply_text("Format konten belum didukung. Kirim teks, foto, video, GIF, atau dokumen.")
            return

        channels = (await stores.channels.read())["channels"]
        if not channels:
            app.pending.pop(user_id, None)
            await message.reply_text("Belum ada channel. Buka Channels → Tambah channel terlebih dahulu.")
            return

        pending["source_chat_id"] = message.chat.id
        pending["source_message_id"] = message.id
        pending["stage"] = "content_options"
        app.pending[user_id] = pending
        await message.reply_text(
            "✅ <b>KONTEN DITERIMA</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "Mau menambahkan tombol URL di bawah postingan?",
            reply_markup=content_options(),
        )

    @app.on_callback_query(filters.regex(r"^compose:"))
    async def action(_, query: CallbackQuery):
        uid = query.from_user.id
        if not await role_of(uid, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        pending = app.pending.get(uid)
        if not pending:
            await query.answer("Sesi berakhir. Mulai lagi dari menu Buat posting.", show_alert=True)
            return
        action_name = query.data.split(":", 1)[1]

        if action_name == "cancel":
            app.pending.pop(uid, None)
            await query.message.edit_text("✖️ Proses dibatalkan.", reply_markup=back_menu())
            await query.answer()
            return

        if action_name == "add_buttons":
            if "source_message_id" not in pending:
                await query.answer("Kirim konten terlebih dahulu.", show_alert=True)
                return
            pending["stage"] = "button_label"
            await query.message.reply_text("Kirim teks label tombol (maksimal 64 karakter).", reply_markup=cancel_keyboard())
            await query.answer()
            return

        if action_name == "clear_buttons":
            pending["buttons"] = []
            pending["stage"] = "button_menu"
            await query.message.edit_text(
                "🗑 Semua tombol dihapus. Tambah tombol atau lanjut.",
                reply_markup=button_builder(),
            )
            await query.answer()
            return

        if action_name in ("no_buttons", "buttons_done"):
            if "source_message_id" not in pending:
                await query.answer("Konten belum diterima.", show_alert=True)
                return
            pending["stage"] = "choose_target"
            app.pending[uid] = pending
            await _show_destinations(query.message, stores, pending)
            await query.answer()
            return

        if action_name == "draft":
            item = {
                "id": uuid.uuid4().hex[:10],
                "actor_id": uid,
                **pending,
                "created_at": datetime.now().astimezone().isoformat(),
            }
            await stores.drafts.update(lambda data: data["drafts"].append(item))
            await query.message.edit_text("💾 <b>DRAFT TERSIMPAN</b>\nID: <code>" + item["id"] + "</code>", reply_markup=back_menu())
            app.pending.pop(uid, None)
            await query.answer()
            return

        if action_name == "publish":
            required = ("source_chat_id", "source_message_id", "channel_ids")
            if not all(key in pending for key in required):
                await query.answer("Data posting belum lengkap.", show_alert=True)
                return

            if pending["mode"] == "schedule":
                item = {
                    "id": uuid.uuid4().hex[:10],
                    "actor_id": uid,
                    "source_chat_id": pending["source_chat_id"],
                    "source_message_id": pending["source_message_id"],
                    "channel_ids": pending["channel_ids"],
                    "buttons": pending.get("buttons", []),
                    "run_at": pending["run_at"],
                    "status": "pending",
                }
                try:
                    await scheduler.create(item)
                    await query.message.edit_text(
                        "🗓 <b>JADWAL TERSIMPAN</b>\n"
                        f"ID: <code>{item['id']}</code>\nWaktu: <code>{item['run_at']}</code>",
                        reply_markup=back_menu(),
                    )
                except Exception as exc:
                    await query.message.edit_text(f"❌ Jadwal gagal: <code>{escape(str(exc)[:200])}</code>")
            else:
                await query.message.edit_text("⏳ Sedang mempublikasikan konten...")
                results = await publish(
                    app, stores, pending["source_chat_id"], pending["source_message_id"],
                    pending["channel_ids"], uid, pending.get("buttons"),
                )
                ok = sum(1 for item in results if item["ok"])
                failed = [item for item in results if not item["ok"]]
                text = f"🚀 <b>POSTING SELESAI</b>\n━━━━━━━━━━━━━━━━━━━━\nBerhasil: <b>{ok}/{len(results)}</b> channel."
                if failed:
                    text += "\n\n<b>Gagal:</b>\n" + "\n".join(
                        f"• <code>{item['channel_id']}</code>: {escape(item.get('error', 'Gagal')[:120])}"
                        for item in failed
                    )
                await query.message.reply_text(text, reply_markup=back_menu())
            app.pending.pop(uid, None)
            await query.answer()
            return

        await query.answer("Aksi tidak dikenal.", show_alert=True)

    @app.on_callback_query(filters.regex(r"^target:"))
    async def target(_, query: CallbackQuery):
        uid = query.from_user.id
        if not await role_of(uid, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        pending = app.pending.get(uid)
        if not pending or "source_message_id" not in pending:
            await query.answer("Sesi posting berakhir.", show_alert=True)
            return
        channels = (await stores.channels.read())["channels"]
        value = query.data.split(":", 1)[1]
        selected = channels if value == "all" else [x for x in channels if str(x["chat_id"]) == value]
        if not selected:
            await query.answer("Channel tidak ditemukan.", show_alert=True)
            return
        pending["channel_ids"] = [int(x["chat_id"]) for x in selected]
        pending["stage"] = "confirm"
        app.pending[uid] = pending
        names = "\n".join(f"• {escape(str(x['title']))}" for x in selected)
        heading = "🗓 <b>KONFIRMASI JADWAL</b>" if pending["mode"] == "schedule" else "📋 <b>KONFIRMASI POSTING</b>"
        button_lines = "\n".join(f"• {escape(row[0]['text'])}" for row in pending.get("buttons", [])) or "Tanpa tombol"
        await query.message.edit_text(
            f"{heading}\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Tujuan:</b>\n{names}\n\n"
            f"<b>Tombol URL:</b>\n{button_lines}\n\nPeriksa sebelum melanjutkan.",
            reply_markup=confirm_keyboard(pending["mode"] == "schedule"),
        )
        await query.answer()
