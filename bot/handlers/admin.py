from pyrogram import filters
from pyrogram.types import Message

from bot.client import app
from bot.storage.json_store import Stores
from bot.services.permissions import is_owner, log_activity


def register_admin(stores: Stores) -> None:
    @app.on_message(filters.private & filters.command(["addadmin", "deladmin", "admins"]))
    async def admin_cmd(_, message: Message):
        uid = message.from_user.id
        if not await is_owner(uid, stores):
            await message.reply_text("⛔ Hanya owner yang dapat mengelola admin.")
            return
        data = await stores.admins.read()
        cmd = message.command[0]
        if cmd == "admins":
            lines = "\n".join(f"• <code>{item['user_id']}</code>" for item in data["admins"])
            await message.reply_text("👥 <b>DAFTAR ADMIN</b>\n━━━━━━━━━━━━━━━━━━━━\n" + (lines or "Belum ada admin tambahan."))
            return
        if len(message.command) < 2 or not message.command[1].isdigit():
            await message.reply_text(f"Format: <code>/{cmd} USER_ID</code>")
            return
        target = int(message.command[1])
        if target == uid:
            await message.reply_text("Owner tidak perlu ditambahkan sebagai admin.")
            return
        if cmd == "addadmin":
            if any(int(item["user_id"]) == target for item in data["admins"]):
                await message.reply_text("User tersebut sudah menjadi admin.")
                return
            data["admins"].append({"user_id": target, "active": True})
        else:
            data["admins"] = [item for item in data["admins"] if int(item["user_id"]) != target]
        await stores.admins.write(data)
        await log_activity(stores, uid, cmd, str(target))
        await message.reply_text("✅ Daftar admin berhasil diperbarui.")
