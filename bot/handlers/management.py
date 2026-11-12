from datetime import datetime
from html import escape
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pyrogram import filters
from pyrogram.types import Message, CallbackQuery

from bot.client import app
from bot.config import settings
from bot.storage.json_store import Stores
from bot.services.permissions import role_of, is_owner, owner_id, log_activity
from bot.keyboards.menus import settings_menu, main_menu, channel_menu
from bot import runtime


def _line():
    return "━━━━━━━━━━━━━━━━━━━━"


def _now():
    return datetime.now().astimezone().strftime("%d %b %Y · %H:%M")


async def _channels_text(stores: Stores) -> str:
    rows = (await stores.channels.read())["channels"]
    if not rows:
        return (
            "📢 <b>CHANNELS</b>\n"
            f"{_line()}\n"
            "Belum ada channel yang terhubung.\n\n"
            "<b>Tambah channel</b>\n"
            "1. Jadikan bot sebagai admin channel.\n"
            "2. Beri izin <b>Post Messages</b>.\n"
            "3. Kirim perintah berikut:\n"
            "<code>/addchannel @username</code>\n\n"
            "Channel privat: gunakan ID <code>-100...</code> jika bot sudah ada di dalamnya."
        )
    listing = "\n".join(
        f"• <b>{item['title']}</b>\n  <code>{item['chat_id']}</code>"
        for item in rows
    )
    return (
        f"📢 <b>CHANNELS</b> · {len(rows)} terhubung\n"
        f"{_line()}\n{listing}\n\n"
        "Gunakan tombol di bawah untuk mengelola channel."
    )


async def _settings_text(stores: Stores) -> str:
    cfg = await stores.settings.read()
    current_owner = await owner_id(stores)
    channels = len((await stores.channels.read())["channels"])
    admins = len((await stores.admins.read())["admins"])
    return (
        "⚙️ <b>PENGATURAN</b>\n"
        f"{_line()}\n"
        f"👑 Owner ID: <code>{current_owner}</code>\n"
        f"👥 Admin tambahan: <b>{admins}</b>\n"
        f"📢 Channel terhubung: <b>{channels}</b>\n"
        f"🕒 Zona waktu: <code>{cfg.get('timezone', settings.timezone)}</code>\n"
        f"🖥 Runtime: <code>Python 3.10+</code>\n\n"
        "<b>Perintah konfigurasi</b>\n"
        "<code>/setowner USER_ID</code> · pindah owner\n"
        "<code>/settimezone Asia/Jakarta</code> · zona waktu\n"
        "Format pesan: HTML Telegram."
    )


def register_management(stores: Stores) -> None:
    @app.on_message(filters.private & filters.command([
        "stats", "history", "schedules", "cancel_schedule", "drafts",
        "templates", "template_save", "settings", "setowner",
        "settimezone", "update", "restart",
    ]))
    async def manage(_, message: Message):
        uid = message.from_user.id
        role = await role_of(uid, stores)
        if not role:
            return
        cmd = message.command[0]

        if cmd == "stats":
            history = await stores.history.read()
            channels = await stores.channels.read()
            today = datetime.now().astimezone().date().isoformat()
            count_today = sum(item["sent_at"].startswith(today) for item in history["posts"])
            await message.reply_text(
                "📊 <b>STATISTIK</b>\n" + _line() +
                f"\n📝 Total posting: <b>{len(history['posts'])}</b>"
                f"\n📅 Hari ini: <b>{count_today}</b>"
                f"\n📢 Channel aktif: <b>{len(channels['channels'])}</b>",
                reply_markup=main_menu(),
            )
        elif cmd == "history":
            rows = (await stores.history.read())["posts"][-15:]
            lines = [
                f"• <code>{item['channel_id']}</code> · pesan <code>{item['message_id']}</code>"
                for item in reversed(rows)
            ]
            await message.reply_text(
                "🧾 <b>RIWAYAT POSTING</b>\n" + _line() + "\n" +
                ("\n".join(lines) if lines else "Belum ada posting berhasil.")
            )
        elif cmd == "schedules":
            rows = (await stores.schedules.read())["schedules"][-20:]
            lines = [
                f"• <code>{item['id']}</code>\n  {item['run_at']} · <b>{item['status']}</b>"
                for item in reversed(rows)
            ]
            await message.reply_text(
                "🗓 <b>JADWAL POSTING</b>\n" + _line() + "\n" +
                ("\n".join(lines) if lines else "Belum ada jadwal.")
            )
        elif cmd == "cancel_schedule":
            if len(message.command) < 2:
                await message.reply_text("Format: <code>/cancel_schedule ID</code>")
                return
            ok = await runtime.schedule_service.cancel(message.command[1])
            await message.reply_text("✅ Jadwal dibatalkan." if ok else "Jadwal pending tidak ditemukan.")
        elif cmd == "drafts":
            rows = (await stores.drafts.read())["drafts"][-20:]
            lines = [f"• <code>{item['id']}</code> · {item.get('created_at', '-')}" for item in reversed(rows)]
            await message.reply_text(
                "📝 <b>DRAFT TERSIMPAN</b>\n" + _line() + "\n" +
                ("\n".join(lines) if lines else "Belum ada draft.")
            )
        elif cmd == "template_save":
            if not message.reply_to_message or len(message.command) < 2:
                await message.reply_text("Balas pesan dengan <code>/template_save NAMA</code>.")
                return
            item = {
                "name": message.command[1],
                "source_chat_id": message.reply_to_message.chat.id,
                "source_message_id": message.reply_to_message.id,
                "created_by": uid,
            }
            await stores.templates.update(lambda data: data["templates"].append(item))
            await message.reply_text("✅ Referensi template tersimpan.")
        elif cmd == "templates":
            rows = (await stores.templates.read())["templates"]
            await message.reply_text(
                "📚 <b>TEMPLATE</b>\n" + _line() + "\n" +
                ("\n".join(f"• {item['name']}" for item in rows) if rows else "Belum ada template.")
            )
        elif cmd == "settings":
            await message.reply_text(await _settings_text(stores), reply_markup=settings_menu())
        elif cmd == "setowner":
            if not await is_owner(uid, stores):
                await message.reply_text("⛔ Hanya owner aktif yang dapat memindahkan kepemilikan.")
                return
            if len(message.command) < 2 or not message.command[1].isdigit():
                await message.reply_text("Format: <code>/setowner USER_ID</code>")
                return
            target = int(message.command[1])
            if target <= 0:
                await message.reply_text("User ID tidak valid.")
                return
            await stores.settings.update(lambda data: data.update({"owner_id": target}))
            await log_activity(stores, uid, "set_owner", str(target))
            await message.reply_text(
                f"👑 Owner dipindahkan ke <code>{target}</code>.\n"
                "Akun owner lama tidak lagi memiliki akses owner."
            )
        elif cmd in ("update", "restart"):
            if not await is_owner(uid, stores):
                await message.reply_text("⛔ Hanya owner yang dapat menjalankan operasi server.")
                return
            script = "update" if cmd == "update" else "restart"
            response = (
                "🔄 Update GitHub dimulai. Bot akan berhenti sementara lalu hidup kembali."
                if script == "update"
                else "♻️ Restart dimulai. Bot akan aktif kembali sebentar lagi."
            )
            await message.reply_text(response)
            try:
                _launch_operation(script)
            except Exception as exc:
                await message.reply_text(f"❌ Gagal menjalankan operasi: <code>{escape(str(exc))}</code>")
        elif cmd == "settimezone":
            if not await is_owner(uid, stores):
                await message.reply_text("⛔ Hanya owner yang dapat mengubah konfigurasi global.")
                return
            if len(message.command) < 2:
                await message.reply_text("Format: <code>/settimezone Asia/Jakarta</code>")
                return
            try:
                ZoneInfo(message.command[1])
            except ZoneInfoNotFoundError:
                await message.reply_text("Zona waktu tidak dikenal. Contoh: <code>Asia/Jakarta</code>.")
                return
            await stores.settings.update(lambda data: data.update({"timezone": message.command[1]}))
            await message.reply_text("✅ Zona waktu disimpan dan langsung digunakan untuk jadwal baru.")
    @app.on_message(filters.private & filters.regex(r"^(📢 Channels|✍️ Quick Post|🗓 Schedules|📊 Statistics|📝 Drafts|⚙️ Settings)$"))
    async def menu(_, message: Message):
        if not await role_of(message.from_user.id, stores):
            return
        label = message.text
        if label == "📢 Channels":
            await message.reply_text(await _channels_text(stores), reply_markup=channel_menu((await stores.channels.read())["channels"]))
        elif label == "⚙️ Settings":
            await message.reply_text(await _settings_text(stores), reply_markup=settings_menu())
        elif label == "✍️ Quick Post":
            app.pending[message.from_user.id] = {"mode": "post", "run_at": None}
            await message.reply_text(
                "✍️ <b>POSTING BARU</b>\n" + _line() +
                "\nKirim atau teruskan satu pesan yang ingin dipublikasikan.\n"
                "Bisa berupa teks, foto, video, atau dokumen.\n\n"
                "Ketik /cancel untuk membatalkan."
            )
        elif label == "🗓 Schedules":
            rows = (await stores.schedules.read())["schedules"][-20:]
            lines = [f"• <code>{item['id']}</code> · {item['run_at']} · {item['status']}" for item in reversed(rows)]
            await message.reply_text("🗓 <b>JADWAL</b>\n" + _line() + "\n" + ("\n".join(lines) if lines else "Belum ada jadwal."))
        elif label == "📊 Statistics":
            history = await stores.history.read()
            channels = await stores.channels.read()
            today = datetime.now().astimezone().date().isoformat()
            count_today = sum(item["sent_at"].startswith(today) for item in history["posts"])
            await message.reply_text(
                "📊 <b>STATISTIK</b>\n" + _line() +
                f"\n📝 Total posting: <b>{len(history['posts'])}</b>"
                f"\n📅 Hari ini: <b>{count_today}</b>"
                f"\n📢 Channel aktif: <b>{len(channels['channels'])}</b>"
            )
        elif label == "📝 Drafts":
            rows = (await stores.drafts.read())["drafts"][-20:]
            lines = [f"• <code>{item['id']}</code>" for item in reversed(rows)]
            await message.reply_text("📝 <b>DRAFT</b>\n" + _line() + "\n" + ("\n".join(lines) if lines else "Belum ada draft."))

    @app.on_callback_query(filters.regex(r"^settings:"))
    async def settings_actions(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        action = query.data.split(":", 1)[1]
        if action == "admins":
            admins = (await stores.admins.read())["admins"]
            lines = [f"• <code>{item['user_id']}</code>" for item in admins]
            text = "👥 <b>ADMIN</b>\n" + _line() + "\n" + ("\n".join(lines) if lines else "Belum ada admin tambahan.")
            text += "\n\nTambah: <code>/addadmin USER_ID</code>\nHapus: <code>/deladmin USER_ID</code>"
        elif action == "timezone_help":
            text = "🕒 Zona waktu\nGunakan <code>/settimezone Asia/Jakarta</code>.\nContoh lain: Asia/Singapore, UTC."
        elif action == "owner_help":
            text = "👑 Ganti owner\nGunakan <code>/setowner USER_ID</code>.\nHanya owner saat ini yang dapat menjalankannya. Perubahan langsung berlaku."
        elif action in ("update", "restart"):
            if not await is_owner(query.from_user.id, stores):
                await query.answer("Khusus owner.", show_alert=True)
                return
            script = "update" if action == "update" else "restart"
            text = (
                "🔄 Update GitHub dimulai. Bot akan restart setelah proses selesai."
                if script == "update"
                else "♻️ Restart bot dimulai."
            )
        else:
            text = "📚 <b>PERINTAH</b>\n" + _line() + (
                "\n/channels · /addchannel @username"
                "\n/delchannel CHANNEL_ID · /setdefault CHANNEL_ID"
                "\n/post · /schedule YYYY-MM-DD HH:MM"
                "\n/schedules · /cancel_schedule ID"
                "\n/drafts · /history · /stats"
                "\n/addadmin USER_ID · /deladmin USER_ID"
                "\n/setowner USER_ID · /settimezone ZONE"
                "\n/settings · /cancel"
            )
        await query.message.reply_text(text)
        await query.answer()
        if action in ("update", "restart"):
            try:
                _launch_operation(action)
            except Exception as exc:
                await query.message.reply_text(
                    f"❌ Operasi gagal: <code>{escape(str(exc))}</code>"
                )


def _launch_operation(script_name: str) -> None:
    if script_name not in ("update", "restart"):
        raise ValueError("Unsupported operation")
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / script_name
    if not script_path.is_file():
        raise FileNotFoundError(f"Script tidak ditemukan: {script_path}")
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_handle = (log_dir / "operations.log").open("a", encoding="utf-8")
    try:
        subprocess.Popen(
            ["bash", str(script_path)],
            cwd=str(project_root),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        log_handle.close()
