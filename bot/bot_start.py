'''Represents process of server preparing to the start actions.

Initializes DB tables if it aren't created, registers clan in DB if it isn't registered.
Provides instruction message for usage to user in chat.'''

import asyncio
import logging
import re
from threading import Event, Thread


from aiogram import types
from aiogram import executor
from aiogram.utils.markdown import text, bold
from aiogram.types import ParseMode
from aiogram.utils.exceptions import ChatNotFound

from mysql.connector.errors import IntegrityError

from database import DataBaseManipulations
from database import check_initDB


from handle_clan_data import Polling
from handle_clan_data import request_to_api
from handle_tg_user_data import check_user_status

from bot_config import dp, bot
from bot_config import DelayPollClanWarMemberlistAndRadeStatistic

from type_hintings import Response
from type_hintings import SelectQuery, Tables
from states import Authentification

import bot_functions

logging.basicConfig(level=logging.INFO)

db = DataBaseManipulations()

            
@dp.message_handler(content_types = 'new_chat_members', state='*')
async def say_hello_to_new_member(msg: types.Message):


    caption = bold(f'Ласкаво просимо, {msg.new_chat_members[0].full_name} 😃')
    await msg.answer(caption, ParseMode.MARKDOWN_V2)


@dp.message_handler(content_types = 'left_chat_member', state='*')
async def say_bye_to_member(msg: types.Message):


    caption = bold(f'Бувай, {msg.left_chat_member.full_name} 😔')
    await msg.answer(caption, ParseMode.MARKDOWN_V2)

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

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
        caption_for_chat_type = await define_caption_by_user_status(msg.chat.id, msg.from_user.id)
        return await msg.answer(caption_for_chat_type, ParseMode.MARKDOWN_V2)


async def define_caption_by_user_status(chat_id: int, user_id: str) -> str:
    """Defines user status in chat, if there is chat_id of the current chat in the table 'Chats' and returns
    caption for it with params chat_id and user_id; returns relative caption to the user status.

    :param chat_id: telegram chat id
    :param user_id: user id that sent messsage in current chat
    """


    user_status = await check_user_status(chat_id, user_id)
    if user_status in ['creator', 'owner', 'administrator']:

        clan_info = _find_chat_id_in_DB(chat_id)
        caption_for_chat_type = await _handle_searching_result(clan_info)


    else:
        caption_for_chat_type = text(bold('По кнопці знизу [ / ] можеш роздивитися мої команди 😌'))
        
    return caption_for_chat_type


def _find_chat_id_in_DB(chat_id: int) -> tuple | None:
    '''Takes chat id as a parameter, finds it and returns result.
    :parameter chat_id: `chat id` of the telegram chat'''


    result = db.fetch_one(SelectQuery('chat_id, clan_tag', Tables.Chats.value, f"WHERE chat_id = %s", (chat_id, )))
    return result


async def _handle_searching_result(clan_info: tuple | None) -> str:
    '''Checks if clan registered in table and activates relevant state.

    :parameter clan_info: `chat_id` and `clan_tag` values from table `Chats`'''
    
    match clan_info:

        case tuple():
            await Authentification.clan_tag_registered.set()
            caption = text(bold('Клан в цьому чаті вже зареєстрований 😊\n'),
                           bold('По кнопці знизу [ / ] можеш роздивитися мої команди 😌'), sep = '\n')
            return caption

        case None:
            await Authentification.create_clan_tag.set()
            caption = text(bold('Клан в цьому чаті ще не зареєстрований 😔\n'),
                           bold('Введіть у чаті #️⃣ клану:'), sep = '\n')
            return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@dp.message_handler(state = Authentification.create_clan_tag, content_types='text')
async def check_and_save_clanTag_in_DB(msg: types.Message):
    """Extracts clan tag from user message and sends request to the API with this clan tag to check if clan exists.

    Then, if the clan exists, it saves it to the table; else returns error message to the user."""

    
    clanTag = re.search(r'^#[a-zA-Z0-9]*$', msg.text)
    

    if clanTag:

        if _is_clan_exists(clanTag.group()):
            return await _save_clan(msg.chat.id, clanTag.group(), msg)
                
        else:
            caption = text(bold('Такого клану не існує, або з мого боку сталася помилка 😔'))
            return await msg.answer(caption, ParseMode.MARKDOWN_V2)

    else:
        caption = text(bold('Ha жаль, тег введено не в тому форматі 😔'),
                       bold('Спробуйте ще раз.'), sep='\n')
        return await msg.answer(caption, ParseMode.MARKDOWN_V2)


async def _save_clan(chat_id: int, clan_tag: str, msg: types.Message):
    """Inserts chat and clan info in the table; fills table 'ChatAdmins' by admins information from the chat.
    
    :param chat_id: telegram chat id
    :param clan_tag: clan tag"""

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
    '''Takes `clan tag`, makes a test request to api about clan with this clan tag.
    Returns True if request status code equalst to 200.'''

    req = request_to_api(f'clans/%23{clan_tag[1:]}') #here is slice because symbol '#' in api link already parsed as '%23'

    if req.status_code == 200:
        return True
    else:
        return False


async def _fill_ChatAdmins_table():
    '''Collects all chat ids from table, makes requests to Telegram Bot Api with this id to get list of chat administrators.
    Inserts chat creator ID and First Name into table ChatAdmins with current chat id.'''

    chat_id_list = (x[0] for x in db.fetch_all(SelectQuery('chat_id', Tables.Chats.value)))
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
    """Catches all commands when state 'clan_tag_registered' is off and returns relevant error message in chat."""


    caption = text(bold('На жаль, клан ще не зареєстрований або бот був перезапущений 😔'),
                   bold('Введіть або натисніть на команду /start'), sep = '\n')
    await msg.answer(caption, ParseMode.MARKDOWN_V2)

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def db_preparing(polling_delay_seconds: int = 600):
    '''
    Takes polling delay in seconds.
    Checks if database is initialized; otherwise initializes.

    Calls func _fill_ChatAdmins_table().
    
    Creates new thread event and launches class `PollingThread` with
    this event as a parameter and polling delay in seconds.
    
    :parameter `polling_delay_seconds`: delay for polling requests to CoC API in seconds.'''

    check_initDB()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_fill_ChatAdmins_table())
    stopFlag = Event()
    thread = PollingThread(stopFlag, DelayPollClanWarMemberlistAndRadeStatistic)
    thread.start()

class PollingThread(Thread):
    """Executes separate thread to send poll requests to API for clan memberlist and rade statistic every x seconds.

    :parameter event: class threading.Event()
    :parameter delay_sec: number of the seconds for delay"""

    def __init__(self, event: Event, delay_sec: int):
        Thread.__init__(self)
        self.stopped = event
        self.delay_sec = delay_sec

    def run(self):
        while not self.stopped.wait(self.delay_sec):
            _start_pollings()

def _start_pollings():
    '''Starts pollings.'''

    poll = Polling()
    clan_tags = _get_clan_tags_from_db()
    for clan_tag in clan_tags:

        clan_members_response = request_to_api(f'clans/%23{clan_tag[1:]}/members')
        logging.info('PollClanMemberlist')
        asyncio.run(poll.poll_clan_memberlist(Response(
                                                       clan_members_response.status_code,
                                                       clan_members_response.json_api_response_info
                                                       ),
                                              clan_tag))
        logging.info('PollClanRadeStatistic')
        asyncio.run(poll.poll_rade_statistic(clan_members_response.json_api_response_info, clan_tag)) #REPLACE BECAUSE API HAS ALREADY PARSED SYMBOL '#' INTO THE LINK


def _get_clan_tags_from_db() -> list:
        '''Extracts all clan tags from table `Chats`.
        
        Returns list of the registered clan tags.'''

        clan_tags = [clan_tag[0] for clan_tag in DataBaseManipulations().fetch_all(SelectQuery('clan_tag', Tables.Chats.value))]
        return clan_tags


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates = True, on_startup = db_preparing(polling_delay_seconds = DelayPollClanWarMemberlistAndRadeStatistic))
