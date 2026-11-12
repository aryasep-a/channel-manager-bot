from html import escape

from pyrogram import filters
from pyrogram.types import Message, CallbackQuery

from bot.client import app
from bot.storage.json_store import Stores
from bot.services.permissions import role_of, log_activity
from bot.keyboards.menus import channel_menu, confirm_channel_remove, main_menu


_waiting_add: set[int] = set()


async def _add_channel_from_input(message: Message, stores: Stores) -> None:
    uid = message.from_user.id
    value = (message.text or "").strip()
    data = await stores.channels.read()
    try:
        chat = await app.get_chat(value)
        me = await app.get_me()
        member = await app.get_chat_member(chat.id, me.id)
        status = str(member.status).lower()
        if not any(token in status for token in ("administrator", "owner", "creator")):
            await message.reply_text("⛔ Bot belum menjadi admin channel. Jadikan bot admin dan aktifkan izin Post Messages.")
            return
        if any(int(item["chat_id"]) == int(chat.id) for item in data["channels"]):
            await message.reply_text("Channel ini sudah terdaftar.", reply_markup=channel_menu(data["channels"]))
            return
        data["channels"].append({"chat_id": int(chat.id), "title": chat.title or str(chat.id), "username": chat.username})
        await stores.channels.write(data)
        await log_activity(stores, uid, "add_channel", str(chat.id))
        await message.reply_text(
            "✅ <b>CHANNEL DITAMBAHKAN</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"Nama: <b>{escape(str(chat.title or chat.id))}</b>\nID: <code>{chat.id}</code>",
            reply_markup=channel_menu(data["channels"]),
        )
    except Exception as exc:
        await message.reply_text(f"❌ Gagal menambahkan channel.\n<code>{escape(str(exc)[:250])}</code>")


def register_channels(stores: Stores) -> None:
    @app.on_callback_query(filters.regex(r"^menu:channels$"))
    async def open_channels(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        rows = (await stores.channels.read())["channels"]
        text = "📢 <b>CHANNELS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        text += "\n".join(f"• {escape(str(item['title']))} · <code>{item['chat_id']}</code>" for item in rows) if rows else "Belum ada channel yang terhubung."
        await query.message.edit_text(text, reply_markup=channel_menu(rows))
        await query.answer()

    @app.on_callback_query(filters.regex(r"^channel:add$"))
    async def begin_add(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        _waiting_add.add(query.from_user.id)
        await query.message.reply_text(
            "➕ <b>TAMBAH CHANNEL</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "Kirim @username channel atau ID channel privat.\n"
            "Pastikan bot sudah menjadi admin dengan izin Post Messages.\n\n"
            "Ketik /cancel untuk membatalkan."
        )
        await query.answer()

    channel_input_filter = filters.create(
        lambda _, __, message: bool(message.from_user and message.from_user.id in _waiting_add)
    )

    @app.on_message(filters.private & filters.text & channel_input_filter)
    async def receive_channel(_, message: Message):
        uid = message.from_user.id
        if uid not in _waiting_add:
            return
        if not await role_of(uid, stores):
            _waiting_add.discard(uid)
            return
        _waiting_add.discard(uid)
        await _add_channel_from_input(message, stores)

    @app.on_message(filters.private & filters.command(["addchannel", "delchannel", "channels", "setdefault"]))
    async def channel_cmd(_, message: Message):
        uid = message.from_user.id
        if not await role_of(uid, stores):
            return
        cmd = message.command[0]
        data = await stores.channels.read()
        if cmd == "channels":
            rows = data["channels"]
            text = "📢 <b>CHANNELS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            text += "\n".join(f"• {escape(str(item['title']))} · <code>{item['chat_id']}</code>" for item in rows) if rows else "Belum ada channel."
            await message.reply_text(text, reply_markup=channel_menu(rows))
            return
        if len(message.command) < 2:
            await message.reply_text(f"Format: <code>/{cmd} {'@username' if cmd == 'addchannel' else 'CHANNEL_ID'}</code>")
            return
        value = message.command[1]
        if cmd == "addchannel":
            try:
                chat = await app.get_chat(value)
                me = await app.get_me()
                member = await app.get_chat_member(chat.id, me.id)
                status = str(member.status).lower()
                if not any(token in status for token in ("administrator", "owner", "creator")):
                    await message.reply_text("⛔ Bot belum menjadi admin di channel tersebut.")
                    return
                if any(int(item["chat_id"]) == int(chat.id) for item in data["channels"]):
                    await message.reply_text("Channel tersebut sudah terdaftar.")
                    return
                data["channels"].append({
                    "chat_id": int(chat.id),
                    "title": chat.title or str(chat.id),
                    "username": chat.username,
                })
                await stores.channels.write(data)
                await log_activity(stores, uid, "add_channel", str(chat.id))
                await message.reply_text(
                    "✅ <b>CHANNEL BERHASIL DITAMBAHKAN</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"Nama: <b>{escape(str(chat.title))}</b>\n"
                    f"ID: <code>{chat.id}</code>",
                )
            except Exception as exc:
                await message.reply_text(f"❌ Gagal menambahkan channel.\n<code>{escape(str(exc)[:250])}</code>")
        elif not value.lstrip("-").isdigit():
            await message.reply_text("Gunakan ID channel numerik.")
            return
        elif cmd == "delchannel":
            target = int(value)
            before = len(data["channels"])
            data["channels"] = [item for item in data["channels"] if int(item["chat_id"]) != target]
            if len(data["channels"]) == before:
                await message.reply_text("Channel tidak ditemukan.")
                return
            await stores.channels.write(data)
            await log_activity(stores, uid, "delete_channel", str(target))
            await message.reply_text("🗑 Channel berhasil dihapus dari daftar.")
        else:
            target = int(value)
            if not any(int(item["chat_id"]) == target for item in data["channels"]):
                await message.reply_text("Channel tidak ditemukan.")
                return
            cfg = await stores.settings.read()
            cfg["default_channel"] = target
            await stores.settings.write(cfg)
            await message.reply_text("✅ Default channel diperbarui.")

    @app.on_callback_query(filters.regex(r"^channel:"))
    async def channel_actions(_, query: CallbackQuery):
        if not await role_of(query.from_user.id, stores):
            await query.answer("Akses ditolak.", show_alert=True)
            return
        parts = query.data.split(":")
        action = parts[1]
        if action == "add_help":
            await query.message.reply_text(
                "➕ <b>TAMBAH CHANNEL</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "1. Tambahkan bot ke channel sebagai admin.\n"
                "2. Aktifkan izin <b>Post Messages</b>.\n"
                "3. Kirim <code>/addchannel @username</code> ke bot.\n\n"
                "Untuk channel privat, gunakan ID channel."
            )
            await query.answer()
        elif action == "refresh":
            rows = (await stores.channels.read())["channels"]
            text = "📢 <b>CHANNELS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            text += "\n".join(f"• {escape(str(item['title']))} · <code>{item['chat_id']}</code>" for item in rows) if rows else "Belum ada channel yang terhubung."
            await query.message.edit_text(text, reply_markup=channel_menu(rows))
            await query.answer("Diperbarui.")
        elif action == "confirm_remove" and len(parts) == 3 and parts[2].lstrip("-").isdigit():
            target = int(parts[2])
            data = await stores.channels.read()
            item = next((row for row in data["channels"] if int(row["chat_id"]) == target), None)
            if not item:
                await query.answer("Channel tidak ditemukan.", show_alert=True)
                return
            await query.message.reply_text(
                f"Yakin ingin menghapus <b>{escape(str(item['title']))}</b> dari daftar channel?",
                reply_markup=confirm_channel_remove(target),
            )
            await query.answer()
        elif action == "remove" and len(parts) == 3 and parts[2].lstrip("-").isdigit():
            target = int(parts[2])
            data = await stores.channels.read()
            before = len(data["channels"])
            data["channels"] = [item for item in data["channels"] if int(item["chat_id"]) != target]
            if len(data["channels"]) == before:
                await query.answer("Channel tidak ditemukan.", show_alert=True)
                return
            await stores.channels.write(data)
            await log_activity(stores, query.from_user.id, "delete_channel", str(target))
            text = "📢 <b>CHANNELS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            text += "\n".join(f"• {escape(str(item['title']))} · <code>{item['chat_id']}</code>" for item in data["channels"]) if data["channels"] else "Belum ada channel yang terhubung."
            await query.message.edit_text(text, reply_markup=channel_menu(data["channels"]))
            await query.answer("Channel dihapus.")
