# Clash of Clans TG Helper
## This telegram bot helps clan owners in the game Clash of Clans helps keep small statistics about their teammates right in the telegram group.


[![](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/) [![](https://img.shields.io/badge/aiogram-2.21-red)](https://github.com/aiogram/aiogram) [![](https://img.shields.io/badge/MySQL-8.0.30-blueviolet)](https://www.mysql.com/downloads/) [![](https://img.shields.io/badge/Clash_of_Clans-API-blueviolet)](https://developer.clashofclans.com/#/)

## Key Features:
- asynchronous code
- saving basic clan data in MySQL DataBase
- updating information in the database based on polling requests

# Getting Started
## Installing

```
git clone https://github.com/Leviinson/CoC-Helper_aiogram.git
```

## Bot setup
- in the configuration module `bot_config.py` insert necessary bot and Clash of Clans API tokens
and choose a delay for polling requests to CoC API.
- in the configuration module `mysql_config.py` insert necessary settings for mysql server.

Optionally, you can replace the direct insertion of private data into the configuration file with environment variables

## Abbreviations that may appear in the code:
- CWL - Clan War League
- CW - Clan War
- LVK - Ukrainian abbreviation that equals to CWL (occurs only in command names, which can be easily replaced with a custom value.)


