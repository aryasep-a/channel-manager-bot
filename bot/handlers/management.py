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
from bot.keyboards.menus import settings_menu, main_menu, channel_menu, admins_menu, back_menu
from bot import runtime


_awaiting_settings: dict[int, str] = {}


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
        f"• <b>{escape(str(item['title']))}</b>\n  <code>{item['chat_id']}</code>"
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
                ("\n".join(f"• {escape(str(item['name']))}" for item in rows) if rows else "Belum ada template.")
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

    @app.on_callback_query(filters.regex(r"^menu:(schedules|stats|drafts|settings|history)$"))
    async def dashboard_sections(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        section = query.data.split(":", 1)[1]
        if section == "settings":
            text = await _settings_text(stores)
            markup = settings_menu()
        elif section == "stats":
            history = await stores.history.read()
            channels = await stores.channels.read()
            today = datetime.now().astimezone().date().isoformat()
            today_count = sum(item["sent_at"].startswith(today) for item in history["posts"])
            text = (
                "📊 <b>STATISTIK</b>\n" + _line()
                + f"\n📝 Total posting: <b>{len(history['posts'])}</b>"
                + f"\n📅 Hari ini: <b>{today_count}</b>"
                + f"\n📢 Channel terhubung: <b>{len(channels['channels'])}</b>"
            )
            markup = back_menu()
        elif section == "history":
            rows = (await stores.history.read())["posts"][-20:]
            listing = "\n".join(
                f"• <code>{item['channel_id']}</code> · pesan <code>{item['message_id']}</code> · {escape(str(item.get('sent_at', '-'))[:16])}"
                for item in reversed(rows)
            )
            text = "🧾 <b>RIWAYAT POSTING</b>\n" + _line() + "\n" + (listing or "Belum ada posting berhasil.")
            markup = back_menu()
        elif section == "drafts":
            rows = (await stores.drafts.read())["drafts"][-15:]
            listing = "\n".join(
                f"• <code>{item['id']}</code> · {escape(str(item.get('created_at', '-')))}"
                for item in reversed(rows)
            )
            text = "📝 <b>DRAFT TERSIMPAN</b>\n" + _line() + "\n" + (listing or "Belum ada draft.")
            markup = back_menu()
        else:
            rows = (await stores.schedules.read())["schedules"][-20:]
            listing = "\n".join(
                f"• <code>{item['id']}</code> · {escape(str(item['run_at']))} · <b>{escape(str(item['status']))}</b>"
                for item in reversed(rows)
            )
            text = "🗓 <b>JADWAL POSTING</b>\n" + _line() + "\n" + (listing or "Belum ada jadwal.")
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            buttons = [[InlineKeyboardButton("➕ Buat jadwal", callback_data="menu:schedule")]]
            buttons.extend(
                [InlineKeyboardButton(f"✖️ Batalkan {item['id']}", callback_data=f"schedule:cancel:{item['id']}")]
                for item in reversed(rows) if item.get("status") == "pending"
            )
            buttons.append([InlineKeyboardButton("⬅️ Menu utama", callback_data="menu:home")])
            markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(text, reply_markup=markup)
        await query.answer()

    @app.on_callback_query(filters.regex(r"^schedule:cancel:"))
    async def cancel_schedule_button(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        schedule_id = query.data.split(":", 2)[2]
        ok = await runtime.schedule_service.cancel(schedule_id)
        await query.answer("Jadwal dibatalkan." if ok else "Jadwal pending tidak ditemukan.", show_alert=True)
        rows = (await stores.schedules.read())["schedules"][-20:]
        listing = "\n".join(
            f"• <code>{item['id']}</code> · {escape(str(item['run_at']))} · <b>{escape(str(item['status']))}</b>"
            for item in reversed(rows)
        )
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = [[InlineKeyboardButton("➕ Buat jadwal", callback_data="menu:schedule")]]
        buttons.extend(
            [InlineKeyboardButton(f"✖️ Batalkan {item['id']}", callback_data=f"schedule:cancel:{item['id']}")]
            for item in reversed(rows) if item.get("status") == "pending"
        )
        buttons.append([InlineKeyboardButton("⬅️ Menu utama", callback_data="menu:home")])
        await query.message.edit_text(
            "🗓 <b>JADWAL POSTING</b>\n" + _line() + "\n" + (listing or "Belum ada jadwal."),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    @app.on_callback_query(filters.regex(r"^settings:"))
    async def settings_actions(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        action = query.data.split(":", 1)[1]
        if action == "admins":
            admins = (await stores.admins.read())["admins"]
            await query.message.edit_text(
                "👥 <b>KELOLA ADMIN</b>\n" + _line() + "\nPilih tindakan:",
                reply_markup=admins_menu(admins),
            )
            await query.answer()
            return
        if action == "add_admin":
            if not await is_owner(query.from_user.id, stores):
                await query.answer("Khusus owner.", show_alert=True)
                return
            _awaiting_settings[query.from_user.id] = "add_admin"
            text = "Kirim Telegram user ID yang ingin dijadikan admin."
        elif action.startswith("remove_admin:"):
            if not await is_owner(query.from_user.id, stores):
                await query.answer("Khusus owner.", show_alert=True)
                return
            target = action.split(":", 1)[1]
            if not target.isdigit():
                await query.answer("ID tidak valid.", show_alert=True)
                return
            data = await stores.admins.read()
            data["admins"] = [item for item in data["admins"] if int(item["user_id"]) != int(target)]
            await stores.admins.write(data)
            await query.message.edit_text("🗑 Admin dihapus.", reply_markup=admins_menu(data["admins"]))
            await query.answer()
            return
        elif action == "timezone_help":
            if not await is_owner(query.from_user.id, stores):
                await query.answer("Khusus owner.", show_alert=True)
                return
            _awaiting_settings[query.from_user.id] = "timezone"
            text = "🕒 Kirim zona waktu, contoh <code>Asia/Jakarta</code> atau <code>UTC</code>."
        elif action == "owner_help":
            if not await is_owner(query.from_user.id, stores):
                await query.answer("Khusus owner.", show_alert=True)
                return
            _awaiting_settings[query.from_user.id] = "owner"
            text = "👑 Kirim Telegram user ID owner baru. Perubahan langsung berlaku."
        elif action in ("update", "restart"):
            if not await is_owner(query.from_user.id, stores):
                await query.answer("Khusus owner.", show_alert=True)
                return
            text = (
                "🔄 Update GitHub dimulai. Bot akan restart setelah proses selesai."
                if action == "update" else "♻️ Restart bot dimulai."
            )
        else:
            text = "Pengaturan tidak dikenal."
        await query.message.reply_text(text, reply_markup=back_menu())
        await query.answer()
        if action in ("update", "restart"):
            try:
                _launch_operation(action)
            except Exception as exc:
                await query.message.reply_text(f"❌ Operasi gagal: <code>{escape(str(exc))}</code>")

    settings_input_filter = filters.create(
        lambda _, __, message: bool(message.from_user and message.from_user.id in _awaiting_settings)
    )

    @app.on_message(filters.private & filters.text & settings_input_filter)
    async def receive_settings_input(_, message: Message):
        uid = message.from_user.id
        action = _awaiting_settings.pop(uid, None)
        if not action:
            return
        value = (message.text or "").strip()
        if not await is_owner(uid, stores):
            await message.reply_text("⛔ Hanya owner yang dapat mengubah pengaturan.")
            return
        if action == "timezone":
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError:
                _awaiting_settings[uid] = action
                await message.reply_text("Zona waktu tidak dikenal. Coba lagi, contoh Asia/Jakarta.")
                return
            await stores.settings.update(lambda data: data.update({"timezone": value}))
            await message.reply_text(f"✅ Zona waktu diperbarui: <code>{escape(value)}</code>", reply_markup=settings_menu())
        elif action == "owner":
            if not value.isdigit() or int(value) <= 0:
                _awaiting_settings[uid] = action
                await message.reply_text("Kirim user ID numerik yang valid.")
                return
            await stores.settings.update(lambda data: data.update({"owner_id": int(value)}))
            await log_activity(stores, uid, "set_owner", value)
            await message.reply_text(
                f"👑 Owner baru: <code>{value}</code>. Akun ini tidak lagi menjadi owner.",
                reply_markup=main_menu(),
            )
        elif action == "add_admin":
            if not value.isdigit() or int(value) <= 0:
                _awaiting_settings[uid] = action
                await message.reply_text("Kirim user ID numerik yang valid.")
                return
            data = await stores.admins.read()
            if any(int(item["user_id"]) == int(value) for item in data["admins"]):
                await message.reply_text("User tersebut sudah menjadi admin.", reply_markup=admins_menu(data["admins"]))
                return
            data["admins"].append({"user_id": int(value), "active": True})
            await stores.admins.write(data)
            await message.reply_text("✅ Admin ditambahkan.", reply_markup=admins_menu(data["admins"]))


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
