import asyncio
import logging
import re
from textwrap import fill
from threading import Event, Thread


from aiogram import types
from aiogram import executor
from aiogram.utils.markdown import text, bold
from aiogram.types import ParseMode
from aiogram.utils.exceptions import ChatNotFound



from database import DataBaseManipulation
from database import Tables
from database import check_initDB




from handle_clan_data import Polling
from handle_clan_data import request_to_api
from handle_tg_user_data import check_user_status

from bot_config import dp, bot

from mysql.connector.errors import IntegrityError
from states import Authentification

import bot_functions

logging.basicConfig(level=logging.INFO)

db = DataBaseManipulation()


async def define_caption_for_public_chat_type(chat_id: int, user_id: str):


    user_status = await check_user_status(chat_id, user_id)
    if user_status in ['creator', 'owner', 'administrator']:

        clan_info = _find_chat_id_in_DB(chat_id)
        caption_for_chat_type = await _handle_searching_result(clan_info)


    else:
        caption_for_chat_type = text(bold('По кнопці знизу [ / ] можеш роздивитися мої команди 😌'))
        
    return caption_for_chat_type


def _find_chat_id_in_DB(chat_id: int) -> tuple[str] | None:


    result = db.fetch_one('chat_id, clan_tag', Tables.Chats.value, f"WHERE chat_id = '{chat_id}'")
    return result




async def _handle_searching_result(clan_info: tuple[str, str] | None) -> str:
    

    if isinstance(clan_info, tuple):
        
        await Authentification.clan_tag_registered.set()
        caption = text(bold('Клан в цьому чаті вже зареєстрований 😊\n'),
                       bold('По кнопці знизу [ / ] можеш роздивитися мої команди 😌'), sep = '\n')
        return caption

    else:

        await Authentification.create_clan_tag.set()
        caption = text(bold('Клан в цьому чаті ще не зареєстрований 😔\n'),
                       bold('Введіть у чаті #️⃣ клану:'), sep = '\n')
        return caption

            
@dp.message_handler(content_types = 'new_chat_members', state='*')
async def say_hello_to_new_member(msg: types.Message):


    caption = bold(f'Ласкаво просимо, {msg.new_chat_members[0].full_name} 😃')
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(content_types = 'left_chat_member', state='*')
async def say_bye_to_member(msg: types.Message):


    caption = bold(f'Бувай, {msg.left_chat_member.full_name} 😔')
    await msg.answer(caption, ParseMode.MARKDOWN_V2)
    await bot.set_chat_permissions()


@dp.message_handler(commands = 'start', state = '*')
async def user_manual(msg: types.Message):


    caption_general = text(bold('Вітаю ☺️'),
                           bold('Моє призначення - облегшення життя керівників кланів Clash of Clans для проведення ігрової статистики членів клану.\n\n'),
                           bold('Можливо, по дорозі ви зустрінете пару багів, але не хвилуйтеся 😌'),
                           bold('Ось контакт мого розробника: @levinsxn'),
                           bold('Пишіть йому, він все вирішить.\n\n\n'), sep='\n')

    if msg.chat.type == 'private':
        caption_for_chat_type = text(bold('Ти можеш додати мене до групи, виконуючи наступні кроки:'),
                                     bold('1. Натисни зверху на моє їм\'я.'),
                                     bold('2. Натисни "Додати до групи"'),
                                     bold('3. Після вдачного вибрання групи - ОБОВ`ЯЗКОВО зроби мене адміністратором, та перевірте, є у групи статус "супергрупи".'),
                                     bold('4. На кінець - введи в чаті групи команду "/start", і я розпочну свою роботу.'), sep = '\n')
        return await msg.answer((caption_general + caption_for_chat_type), ParseMode.MARKDOWN_V2)

    else:
        caption_for_chat_type = await define_caption_for_public_chat_type(msg.chat.id, msg.from_user.id)
        return await msg.answer(caption_for_chat_type, ParseMode.MARKDOWN_V2)


@dp.message_handler(state = Authentification.create_clan_tag, content_types='text')
async def check_and_save_clanTag_in_DB(msg: types.Message):

    
    clanTag = re.search(r'^#[a-zA-Z0-9]*$', msg.text)
    

    if clanTag:

        if _is_clan_exists(clanTag.group()):
            return await _save_clan(msg.chat.id, clanTag.group(), msg)
                
        else:
            caption = text(bold('Такого клану не існує, або з мого боку сталася помилка 😔'))
            return await msg.answer(caption, ParseMode.MARKDOWN_V2)

    else:
        caption = text(bold('На жаль, тег введено не в тому форматі 😔'),
                       bold('Спробуйте ще раз.'), sep='\n')
        return await msg.answer(caption, ParseMode.MARKDOWN_V2)


async def _save_clan(chat_id: int, clan_tag: str, msg: types.Message):


    try:
        db.insert(f'Chats', {'chat_id' : chat_id, 'clan_tag' : clan_tag})
        await _fill_ChatAdmins_table()
        await Authentification.clan_tag_registered.set()

        caption = text(bold('Клан вдало зареєстрований 😌'),
                       bold('По кнопці знизу [ / ] можеш роздивитися мої команди 😌'), sep = '\n')
        return await msg.answer(caption, ParseMode.MARKDOWN_V2)
    except IntegrityError:
        caption = text(bold('На жаль, данний клан зареєстрований у іншому чаті 😔'),
                       bold('Спробуйте ще раз, але з іншим тегом'), sep='\n')
        return await msg.answer(caption, ParseMode.MARKDOWN_V2)


def _is_clan_exists(clan_tag: str) -> bool:


    req = request_to_api(f'clans/%23{clan_tag[1:]}') #here is slice because '#' in api link already parsed as '%23'

    if req.status_code == 200:
        return True
    else:
        return False


async def _fill_ChatAdmins_table():


    chat_id_list = (x[0] for x in db.fetch_all('chat_id', 'Chats'))
    try:

        for chat_id in chat_id_list:
            chat_admins = await bot.get_chat_administrators(chat_id)

            for admin in chat_admins:
                admin_info = list(admin)

                if admin_info[1][1] == 'creator':
                    db.insert('ChatAdmins', {'user_id' : admin_info[0][1]['id'], 'user_name' : admin_info[0][1]['first_name'], 'chat_id' : chat_id}, ignore = True)
    except ChatNotFound:
        logging.error('Table "Chats" is clear, so chat_id_list is empty.')


@dp.message_handler(commands=['members', 'cw_members', 'cw_time', 'cw_status', 'lvk_members', 'lvk_status', 'lvk_results', 'rade_statistic'])
async def answer_when_clan_is_not_registered(msg: types.Message):


    caption = text(bold('На жаль, клан ще не зареєстрований або бот був перезапущений 😔'),
                   bold('Введіть або натисніть на команду /start'), sep = '\n')
    await msg.answer(caption, ParseMode.MARKDOWN_V2)

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def db_preparing():

    check_initDB()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_fill_ChatAdmins_table())
    stopFlag = Event()
    thread = PollingThread(stopFlag, 300)
    thread.start()

class PollingThread(Thread):

    def __init__(self, event: Event, delay_sec: int):
        Thread.__init__(self)
        self.stopped = event
        self.delay_sec = delay_sec

    def run(self):
        while not self.stopped.wait(self.delay_sec):
            logging.info('PollClanMemberlist')
            _execute_pollings()

def _execute_pollings():

    poll = Polling()
    asyncio.run(poll.poll_clan_memberlist())
    asyncio.run(poll.poll_rade_statistic()) #REPLACE BECAUSE API HAS ALREADY PARSED SYMBOL '#' INTO THE LINK


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates = True, on_startup = db_preparing())