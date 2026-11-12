from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Channels", callback_data="menu:channels"),
            InlineKeyboardButton("✍️ Buat posting", callback_data="menu:post"),
        ],
        [
            InlineKeyboardButton("🗓 Jadwal", callback_data="menu:schedules"),
            InlineKeyboardButton("📊 Statistik", callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton("📝 Draft", callback_data="menu:drafts"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"),
        ],
        [InlineKeyboardButton("📚 Bantuan", callback_data="menu:help")],
    ])


def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu utama", callback_data="menu:home")]])


def channel_menu(channels: list[dict]):
    rows = [[InlineKeyboardButton("➕ Tambah channel", callback_data="channel:add")]]
    rows.extend(
        [[InlineKeyboardButton(f"🗑 {str(item['title'])[:24]}", callback_data=f"channel:confirm_remove:{item['chat_id']}")]
         for item in channels]
    )
    rows.append([InlineKeyboardButton("🔄 Refresh", callback_data="channel:refresh")])
    rows.append([InlineKeyboardButton("⬅️ Menu utama", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def confirm_channel_remove(chat_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Ya, hapus channel", callback_data=f"channel:remove:{chat_id}")],
        [InlineKeyboardButton("Batal", callback_data="channel:refresh")],
    ])


def admins_menu(admins: list[dict]):
    rows = [[InlineKeyboardButton("➕ Tambah admin", callback_data="settings:add_admin")]]
    rows.extend([[InlineKeyboardButton(f"🗑 Hapus {item['user_id']}", callback_data=f"settings:remove_admin:{item['user_id']}")] for item in admins])
    rows.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu:settings")])
    return InlineKeyboardMarkup(rows)


def settings_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Kelola admin", callback_data="settings:admins")],
        [InlineKeyboardButton("🕒 Ubah zona waktu", callback_data="settings:timezone_help")],
        [InlineKeyboardButton("🔐 Pindah owner", callback_data="settings:owner_help")],
        [InlineKeyboardButton("🔄 Update dari GitHub", callback_data="settings:update")],
        [InlineKeyboardButton("♻️ Restart bot", callback_data="settings:restart")],
        [InlineKeyboardButton("⬅️ Menu utama", callback_data="menu:home")],
    ])


def channel_picker(channels: list[dict]):
    rows = [[InlineKeyboardButton(str(c["title"])[:30], callback_data=f"target:{c['chat_id']}")] for c in channels]
    rows.extend([
        [InlineKeyboardButton("📣 Semua channel", callback_data="target:all")],
        [InlineKeyboardButton("✖️ Batal", callback_data="compose:cancel")],
    ])
    return InlineKeyboardMarkup(rows)


def content_options():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔘 Tambah tombol URL", callback_data="compose:add_buttons")],
        [InlineKeyboardButton("➡️ Lanjut tanpa tombol", callback_data="compose:no_buttons")],
        [InlineKeyboardButton("✖️ Batalkan", callback_data="compose:cancel")],
    ])


def button_builder():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah tombol lagi", callback_data="compose:add_buttons")],
        [InlineKeyboardButton("✅ Selesai", callback_data="compose:buttons_done")],
        [InlineKeyboardButton("🗑 Hapus semua tombol", callback_data="compose:clear_buttons")],
        [InlineKeyboardButton("✖️ Batalkan", callback_data="compose:cancel")],
    ])


def confirm_keyboard(is_schedule: bool = False):
    label = "🗓 Simpan jadwal" if is_schedule else "🚀 Terbitkan sekarang"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Edit tombol URL", callback_data="compose:add_buttons")],
        [InlineKeyboardButton(label, callback_data="compose:publish")],
        [InlineKeyboardButton("💾 Simpan draft", callback_data="compose:draft")],
        [InlineKeyboardButton("✖️ Batalkan", callback_data="compose:cancel")],
    ])
