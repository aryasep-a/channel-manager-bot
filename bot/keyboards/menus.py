from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📢 Channels"), KeyboardButton("✍️ Quick Post")],
            [KeyboardButton("🗓 Schedules"), KeyboardButton("📊 Statistics")],
            [KeyboardButton("📝 Drafts"), KeyboardButton("⚙️ Settings")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Pilih menu Channel Manager",
    )


def channel_menu(channels: list[dict]):
    rows = [
        [InlineKeyboardButton("➕ Cara menambahkan channel", callback_data="channel:add_help")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="channel:refresh")],
    ]
    for item in channels:
        rows.append([
            InlineKeyboardButton(
                f"🗑 {item['title'][:24]}",
                callback_data=f"channel:confirm_remove:{item['chat_id']}",
            )
        ])
    return InlineKeyboardMarkup(rows)


def confirm_channel_remove(chat_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Ya, hapus channel", callback_data=f"channel:remove:{chat_id}")],
        [InlineKeyboardButton("Batal", callback_data="channel:refresh")],
    ])


def settings_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Kelola admin", callback_data="settings:admins")],
        [InlineKeyboardButton("🕒 Zona waktu", callback_data="settings:timezone_help")],
        [InlineKeyboardButton("🔐 Ganti owner", callback_data="settings:owner_help")],
        [InlineKeyboardButton("📋 Semua perintah", callback_data="settings:commands")],
        [InlineKeyboardButton("🔄 Update dari GitHub", callback_data="settings:update")],
        [InlineKeyboardButton("♻️ Restart bot", callback_data="settings:restart")],
    ])


def channel_picker(channels: list[dict]):
    rows = [
        [InlineKeyboardButton(c["title"][:30], callback_data=f"target:{c['chat_id']}")]
        for c in channels
    ]
    rows.append([InlineKeyboardButton("📣 Semua channel", callback_data="target:all")])
    rows.append([InlineKeyboardButton("✖️ Batal", callback_data="compose:cancel")])
    return InlineKeyboardMarkup(rows)


def confirm_keyboard(is_schedule: bool = False):
    publish_label = "🗓 Konfirmasi jadwal" if is_schedule else "🚀 Terbitkan sekarang"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(publish_label, callback_data="compose:publish")],
        [InlineKeyboardButton("💾 Simpan draft", callback_data="compose:draft")],
        [InlineKeyboardButton("✖️ Batalkan", callback_data="compose:cancel")],
    ])
