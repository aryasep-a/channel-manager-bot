from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
def main_menu():
    return ReplyKeyboardMarkup([[KeyboardButton('📢 Channels'),KeyboardButton('✍️ Quick Post')],[KeyboardButton('🗓 Schedules'),KeyboardButton('📊 Statistics')],[KeyboardButton('📝 Drafts'),KeyboardButton('⚙️ Settings')]],resize_keyboard=True)
def channel_picker(channels:list[dict]):
    rows=[[InlineKeyboardButton(c['title'][:30],callback_data=f'target:{c["chat_id"]}')] for c in channels]
    rows.append([InlineKeyboardButton('All channels',callback_data='target:all')]); return InlineKeyboardMarkup(rows)
def confirm_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton('Publish',callback_data='compose:publish'),InlineKeyboardButton('Save draft',callback_data='compose:draft')],[InlineKeyboardButton('Cancel',callback_data='compose:cancel')]])
