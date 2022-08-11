'''Represents typehintings for handlers in handle_clan_data.py module.

Classes:

    Response(NamedTuple)
    ClanWarLeagueMembersInfo(NamedTuple)
    ClanWarLeagueMembersAttacksResul(NamedTuple)
    ClanWarMembersInfo(NamedTuple)
    ClanMembersInfo(NamedTuple)
    DateTime(NamedTuple)'''

from typing import NamedTuple, Generator

class Response(NamedTuple):


    status_code: int
    json_api_response_info: dict

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


    members_names: Generator
    members_tags: Generator
    members_roles: Generator


class DateTime(NamedTuple):


    year: str
    month: str
    day: str
    hour: str
    minute: str
    seconds: str