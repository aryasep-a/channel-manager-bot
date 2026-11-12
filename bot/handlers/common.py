from pyrogram import filters
from pyrogram.types import Message, CallbackQuery

from bot.client import app
from bot.storage.json_store import Stores
from bot.services.permissions import role_of, owner_id
from bot.keyboards.menus import main_menu


def register_common(stores: Stores) -> None:
    @app.on_message(filters.private & filters.command("start"))
    async def start(_, message: Message):
        uid = message.from_user.id
        role = await role_of(uid, stores)
        if not role:
            current_owner = await owner_id(stores)
            await message.reply_text(
                "🔒 <b>AKSES BELUM DIBERIKAN</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Telegram ID lu: <code>{uid}</code>\n"
                f"Owner terdaftar: <code>{current_owner}</code>\n\n"
                "Kirim Telegram ID di atas ke owner agar akun lu ditambahkan sebagai admin. "
                "Jika ini akun owner, samakan OWNER_ID di .env dengan owner yang tersimpan di data/settings.json."
            )
            return
        await message.reply_text(
            "👋 <b>CHANNEL MANAGER</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Kelola channel, posting media, tombol URL, dan jadwal dari satu dashboard.\n\n"
            "Pilih menu:",
            reply_markup=main_menu(),
        )

    @app.on_message(filters.private & filters.command("help"))
    async def help_cmd(_, message: Message):
        await message.reply_text(
            "📚 <b>PANDUAN SINGKAT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Semua navigasi memakai tombol di dashboard.\n"
            "• Posting: kirim teks/foto/video/dokumen, pilih channel, atur tombol URL, lalu terbitkan.\n"
            "• Tambah channel: Channels → Tambah channel, lalu kirim @username atau ID.\n"
            "• Tombol posting: label tombol lalu URL tujuan. Opsional.\n"
            "• /start membuka dashboard.\n"
            "• /help menampilkan panduan.\n"
            "• /cancel membatalkan proses yang sedang berjalan."
        )

    @app.on_message(filters.private & filters.command("cancel"))
    async def cancel(_, message: Message):
        app.pending.pop(message.from_user.id, None)
        await message.reply_text("✖️ Proses dibatalkan.", reply_markup=main_menu())

    @app.on_callback_query(filters.regex(r"^menu:(home|start|help)$"))
    async def dashboard(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses belum diberikan.", show_alert=True)
            return
        action = query.data.split(":", 1)[1]
        if action in ("home", "start"):
            await query.message.edit_text(
                "👋 <b>CHANNEL MANAGER</b>\n━━━━━━━━━━━━━━━━━━━━\nPilih fitur:",
                reply_markup=main_menu(),
            )
            await query.answer()
        elif action == "help":
            await query.answer("Gunakan /help untuk panduan.", show_alert=True)
