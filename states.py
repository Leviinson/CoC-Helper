from aiogram.dispatcher.filters.state import State, StatesGroup

class Authentification(StatesGroup):
    create_clan_tag = State()
    clan_tag_registered = State()