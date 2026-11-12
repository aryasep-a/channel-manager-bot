from pyrogram import filters
from pyrogram.types import Message

from bot.client import app
from bot.storage.json_store import Stores
from bot.services.permissions import role_of
from bot.keyboards.menus import main_menu


def register_common(stores: Stores) -> None:
    @app.on_message(filters.private & filters.command("start"))
    async def start(_, message: Message):
        if not await role_of(message.from_user.id, stores):
            await message.reply_text("⛔ Akses ditolak. Hubungi owner bot untuk meminta akses.")
            return
        await message.reply_text(
            "👋 <b>CHANNEL MANAGER</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Kelola channel dan distribusikan konten dari satu tempat.\n\n"
            "Pilih fitur dari menu di bawah. Ketik /help untuk melihat daftar perintah.",
            reply_markup=main_menu(),
        )

    @app.on_message(filters.private & filters.command("help"))
    async def help_cmd(_, message: Message):
        if not await role_of(message.from_user.id, stores):
            return
        await message.reply_text(
            "📚 <b>PANDUAN CHANNEL MANAGER</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "/channels · daftar channel\n"
            "/addchannel @username · tambah channel\n"
            "/delchannel ID · hapus channel\n"
            "/post · posting langsung\n"
            "/schedule YYYY-MM-DD HH:MM · jadwalkan\n"
            "/schedules · daftar jadwal\n"
            "/drafts · daftar draft\n"
            "/history · riwayat posting\n"
            "/stats · statistik\n"
            "/settings · pengaturan\n"
            "/cancel · batalkan proses aktif",
        )

    @app.on_message(filters.private & filters.command("cancel"))
    async def cancel(_, message: Message):
        app.pending.pop(message.from_user.id, None)
        await message.reply_text("✖️ Proses dibatalkan.", reply_markup=main_menu())
