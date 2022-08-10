from datetime import datetime, timedelta
import logging
import re

from aiogram import types
from aiogram.types import ParseMode
from aiogram.utils.markdown import text, bold
from aiogram.utils.exceptions import UserIsAnAdministratorOfTheChat
from aiogram.dispatcher.filters import AdminFilter, IsReplyFilter

from bot_config import dp, bot
from states import Authentification

from handle_clan_data import ClanDataExtractions
from handle_tg_user_data import ChatDBManipulations


chat = ChatDBManipulations()
clan = ClanDataExtractions()


logging.basicConfig(level = logging.INFO)

async def anti_flood(msg: types.Message, *args, **kwargs):

    
    caption = text(bold('Ви відправляєте запити занадто часто.\nБудь-ласка, будьте повільніше 😌'),
                   bold('Встановлена частота запитів - один на 10 секунд.'), sep = '\n')
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'members', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = 10)
async def get_clan_members(msg: types.Message):


    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_caption_memberlist(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'cw_members', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = 10)
async def get_cw_memberlist(msg: types.Message):
    
    
    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_caption_cw_memberlist(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'lvk_members', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = 10)
async def get_cwl_memberlist(msg: types.Message):

    
    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_caption_cwl_memberlist(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'cw_status', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = 10)
async def get_remaining_time_cw(msg: types.Message):
    
    
    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_cw_status(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands='lvk_status', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = 10)
async def get_current_cwl_status(msg: types.Message):


    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_cwl_status(clan_tag)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'lvk_results', state = Authentification.clan_tag_registered)
@dp.throttled(anti_flood, rate = 10)
async def get_cwl_results(msg: types.Message):


    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_cwl_results(clan_tag.replace('0', 'O'), msg.chat.id)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(commands = 'rade_statistic', state = Authentification.clan_tag_registered)
async def get_rade_statistic(msg: types.Message):

    clan_tag = clan.get_clan_tag(msg.chat.id)
    caption = await clan.get_caption_rade_statistic(clan_tag, msg.chat.id)
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(AdminFilter(), IsReplyFilter(is_reply = True), commands= 'set_admin', state = Authentification.clan_tag_registered)
async def set_new_admin(msg: types.Message):

    if chat._is_member_admin(msg.from_user.id, msg.chat.id):

        chat.set_new_admin(msg.reply_to_message.from_user.id, msg.reply_to_message.from_user.first_name, msg.chat.id)
        caption = text(bold(f"Користувач {msg.reply_to_message.from_user.first_name} стає адміністратором❗️"))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)
    
    else:
        
        caption = text(bold('В вас немає прав адміністратора ❗️'))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(AdminFilter(), IsReplyFilter(is_reply = True), commands = 'remove_admin', state = Authentification.clan_tag_registered)
async def remove_admin_role(msg: types.Message):

    if chat._is_member_admin(msg.from_user.id, msg.chat.id):

        chat.remove_admin(msg.reply_to_message.from_user.id, msg.chat.id)
        caption = text(bold(f"Користувач {msg.reply_to_message.from_user.id} лишився прав адміністратора❗️"))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)

    else:
        
        caption = text(bold('В вас немає прав адміністратора ❗️'))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)

@dp.message_handler(IsReplyFilter(is_reply = True), commands = 'mute', state = Authentification.clan_tag_registered)
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


@dp.message_handler(IsReplyFilter(is_reply = False), commands= ['set_admin', 'remove_admin', 'mute', 'unmute'], state = Authentification.clan_tag_registered)
async def set_new_admin(msg: types.Message):


    if chat._is_member_admin(msg.from_user.id, msg.chat.id):
        caption = text(bold('Для цієї команди є одна з умов: вона повинна бути відповіддю на повідомленя користувача.'))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)

    else:
        caption = text(bold('Для цієї команди є одна з умов: ви повинні бути адміністратором '))
        await msg.answer(caption, ParseMode.MARKDOWN_V2)
