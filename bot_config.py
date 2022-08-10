from aiogram import Dispatcher, Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware

BOT_TOKEN = 'BOT_TOKEN'
API_TOKEN = 'API_TOKEN'

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot, storage = MemoryStorage())
dp.middleware.setup(LoggingMiddleware())