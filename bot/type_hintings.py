'''Represents typehintings for handlers in handle_clan_data.py module.

Classes:

    Response(NamedTuple)
    ClanWarLeagueMembersInfo(NamedTuple)
    ClanWarLeagueMembersAttacksResul(NamedTuple)
    ClanWarMembersInfo(NamedTuple)
    ClanMembersInfo(NamedTuple)
    DateTime(NamedTuple)'''

from typing import NamedTuple, Generator
from enum import Enum

class Response(NamedTuple):


    status_code: int
    json_api_response_info: dict

class Tables(Enum):
    '''
    Storing the names of all tables in DB.

    :parameter `Chats`: table name `Chats`
    :parameter `ClanMembers`: table name `ClanMembers`
    :parameter `RadeMembers`: table name `RadeMembers`
    :parameter `ChatMembers`: table name `ChatMembers`
    :parameter `CWL_members`: table name `ClanWarLeague_memberlist`
    :parameter `CWL_results`: table name `ClanWarLeague_results`
    '''

    Chats = 'Chats'
    ClanMembers = 'ClanMembers'
    RadeMembers = 'RadeMembers'
    ChatMembers = 'ChatMembers'
    CWL_members = 'ClanWarLeague_memberlist'
    CWL_results = 'ClanWarLeague_results'
    UsersNames = 'ChatUsers_nicknames'

class SelectQuery(NamedTuple):
    '''
    Patterns to fill SQL query, accepted as a parameter in funcs.

    :parameter `columns_name`: columns names, which need to select (in according SQL query format)
    :parameter `table_name`: tables names, which need to select (in according SQL query format)
    :parameter `expression`: optional parameter inserting after main sql query, values must be replaced by placeholder - `%s` (!)
    :parameter `expression_values`: optional parameter, that inserts expression values into placeholders, that indicated in parameter "expression"
        for example: `(value,)` or `(value, value)`.
    '''

    columns_name: str
    table_name: Tables
    expression: str = None
    expression_values: tuple = None

class ClanWarLeagueMembersInfo(NamedTuple):


    members_names: Generator
    members_tags: Generator
    members_townHallLevel: Generator


class ClanWarLeagueMembersAttacksResult(NamedTuple):


    members_names: Generator
    members_tags: Generator
    members_stars: Generator


class ClanWarMembersInfo(NamedTuple):


    members_names: Generator
    members_tags: Generator
    members_map_positions: Generator


class ClanMembersInfo(NamedTuple):


    members_names: list
    members_tags: list
    members_roles: list


class DateTime(NamedTuple):


    year: str
    month: str
    day: str
    hour: str
    minute: str
    seconds: str