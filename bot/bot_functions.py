'''Represents bot interface, returns message answer to user in telegram chat.'''

from datetime import datetime, timedelta
import logging
import re

from aiogram import types
from aiogram.types import ParseMode
from aiogram.utils.markdown import text, bold
from aiogram.utils.exceptions import UserIsAnAdministratorOfTheChat
from aiogram.dispatcher.filters import AdminFilter, IsReplyFilter

from bot_config import dp, bot
from bot_config import ThrottlingDelay
from states import Authentification

from handle_clan_data import ClanDataExtractions
from handle_tg_user_data import ChatDBManipulations
from database import DataBaseManipulations
from type_hintings import SelectQuery, Tables



chat = ChatDBManipulations()
clan = ClanDataExtractions()


logging.basicConfig(level = logging.INFO)

async def anti_flood(msg: types.Message, *args, **kwargs):

    
    caption = text(bold('Ви відправляєте запити занадто часто.\nБудь-ласка, будьте повільніше 😌'),
                   bold(f'Встановлена частота запитів - один на {ThrottlingDelay} секунд.'), sep = '\n')
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'members', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def get_clan_members(msg: types.Message):


    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_caption_memberlist(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'cw_members', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def get_cw_memberlist(msg: types.Message):
    
    
    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_caption_cw_memberlist(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'lvk_members', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def get_cwl_memberlist(msg: types.Message):

    
    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_caption_cwl_memberlist(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'cw_status', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def get_remaining_time_cw(msg: types.Message):
    
    
    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_cw_status(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands='lvk_status', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def get_current_cwl_status(msg: types.Message):


    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_cwl_status(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'lvk_results', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def get_cwl_results(msg: types.Message):


    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_cwl_results(clan_tag.replace('0', 'O'), msg.chat.id)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'rade_statistic', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def get_rade_statistic(msg: types.Message):

    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_caption_rade_statistic(clan_tag, msg.chat.id)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(AdminFilter(), IsReplyFilter(is_reply = True), commands= 'set_admin', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def set_new_admin(msg: types.Message):

    if chat._is_member_admin(msg.from_user.id, msg.chat.id):

        chat.set_new_admin(msg.reply_to_message.from_user.id, msg.reply_to_message.from_user.first_name, msg.chat.id)
        caption = text(bold(f"Користувач {msg.reply_to_message.from_user.first_name} стає адміністратором❗️"))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)
    
    else:
        
        caption = text(bold('В вас немає прав адміністратора ❗️'))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(AdminFilter(), IsReplyFilter(is_reply = True), commands = 'remove_admin', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def remove_admin_role(msg: types.Message):

    if chat._is_member_admin(msg.from_user.id, msg.chat.id):

        chat.remove_admin(msg.reply_to_message.from_user.id, msg.chat.id)
        caption = text(bold(f"Користувач {msg.reply_to_message.from_user.id} лишився прав адміністратора❗️"))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)

    else:
        
        caption = text(bold('В вас немає прав адміністратора ❗️'))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(IsReplyFilter(is_reply = True), commands = 'mute', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def mute_chat_member(msg: types.Message):


    user_msg = msg.text
    time_minute = re.search(r"\d*", user_msg[6:])
    if time_minute:
        member_is_admin_flag = chat._is_member_admin(msg.from_user.id, msg.chat.id)

        if member_is_admin_flag:
            try:
                await bot.restrict_chat_member(msg.chat.id,
                                               msg.reply_to_message.from_user.id,

                                               can_send_media_messages = False,
                                               can_send_other_messages = False,
                                               can_add_web_page_previews = False,

                                               until_date = datetime.now() + timedelta(minutes = int(time_minute.group(0)))
                                               )
                caption = text(bold(f"Користувач {msg.reply_to_message.from_user.first_name} зам'ючений"))
                await msg.answer(caption, ParseMode.MARKDOWN_V2)

            except UserIsAnAdministratorOfTheChat:
                caption = text(bold("Це був адміністратор чату, він непокорний м'юченню принципово 😌"))
                await msg.answer(caption, ParseMode.MARKDOWN_V2)
    else:
        caption = text(bold('Команда повинна мати формат типу: /mute [кіль-ть хвилин]'))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(IsReplyFilter(is_reply = True), commands = 'unmute', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def unmute_chat_member(msg: types.Message):


    try:
        if chat._is_member_admin(msg.reply_to_message.from_user.id, msg.chat.id):
            await bot.restrict_chat_member(msg.chat.id,
                                           msg.reply_to_message.from_user.id,

                                           can_add_web_page_previews = True,
                                           can_send_media_messages = True,
                                           can_send_other_messages = True
                                          )
            caption = text(bold(f"Користувачу {msg.reply_to_message.from_user.first_name} дозволений доступ до чата ❗️"))
            await msg.answer(caption, ParseMode.MARKDOWN_V2)
    except UserIsAnAdministratorOfTheChat:

        logging.error('User have tried to unmute chat administrator.')
        caption = text(bold("Це був адміністратор чату, він непокорний м'юченню принципово 😌"))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(IsReplyFilter(is_reply = True), commands = 'set_nick', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def add_user_nickname(msg: types.Message):
    '''Chat owner creates nickname for users by answer on his message,
    then this nickname inserts into the table "ChatUsers_nicknames"'''

    user_id = msg.reply_to_message.from_user.id
    chat_id = msg.chat.id
    if chat._is_member_admin(user_id, chat_id):
        try:
            user_nickname = msg.text.split(' ')[1] #it can raise IndexError, when msg after command is empty
            if len(user_nickname) > 30:
                caption = text(bold('Ім`я не повинно перевищувати кількість 30-ти символів ❗️'))
                return await msg.answer(caption, ParseMode.MARKDOWN_V2)

            DataBaseManipulations().insert(Tables.UsersNames.value,
                                           {"user_id" : user_id, "chat_id" : chat_id, "user_nickname" : user_nickname},
                                           expression = f"ON DUPLICATE KEY UPDATE user_nickname = VALUES(user_nickname)")
            await msg.answer(text(bold(f'Користувачу {msg.reply_to_message.from_user.id} встановлено локальний нікнейм {user_nickname} ❗️')), ParseMode.MARKDOWN_V2)
        
        except IndexError:
            caption = text(bold('Ім`я повинно бути більше ніж з одного символа ❗️'))
            return await msg.answer(caption, ParseMode.MARKDOWN_V2)
    else:
        return await msg.answer(text(bold('Це доступно тільки власнику чату ❗️')))


@dp.message_handler(IsReplyFilter(is_reply = True), commands = 'get_nick', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def get_user_nickname(msg: types.Message):
    '''Returns user nickname from table "ChatUsers_nicknames" by answer on his message'''

    user_nickname = DataBaseManipulations().fetch_one(SelectQuery('user_nickname', Tables.UsersNames.value, f'WHERE chat_id = {msg.chat.id} AND user_id = {msg.reply_to_message.from_user.id}'))
    match user_nickname:

        case tuple():
            
            return await msg.answer(text(bold(user_nickname[0])), ParseMode.MARKDOWN_V2)

        case None:

            return await msg.answer(text(bold('Данному користувачу не встановленого жодного нікнейму 😔')), ParseMode.MARKDOWN_V2)


@dp.message_handler(IsReplyFilter(is_reply = False), commands= ['set_admin', 'remove_admin', 'mute', 'unmute'], state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = ThrottlingDelay)
async def set_new_admin(msg: types.Message):


    if chat._is_member_admin(msg.from_user.id, msg.chat.id):
        caption = text(bold('Для цієї команди є одна з умов: вона повинна бути відповіддю на повідомленя користувача.'))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)

    else:
        caption = text(bold('Для цієї команди є одна з умов: ви повинні бути адміністратором '))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)