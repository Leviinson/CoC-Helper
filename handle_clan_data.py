from typing import Generator
from typing import Dict
from typing import NamedTuple

from threading import Event
from threading import Thread

import requests
from requests.exceptions import ConnectionError

from datetime import datetime

from bot_config import API_TOKEN, bot
from aiogram.utils.markdown import text, bold
from aiogram.types import ParseMode


from errors import BadRequestError, ClanNotFoundError
from errors import ClanWarEndedError



from database import DataBaseManipulation
from database import Tables

import mysql.connector.errors
import threading


import logging
logging.basicConfig(level = logging.INFO)



class Response(NamedTuple):


    status_code: int
    json_clan_info: Dict[str, str]

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


    members_names: list[str]
    members_tags: list[str]
    members_roles: list[str]



def request_to_api(api_req: str) -> Response:


        api_endpoint = 'https://api.clashofclans.com/v1/'
        headers = {
            'Accept': "application/json",
            'Authorization': "Bearer " + API_TOKEN
        }
        api_link = api_endpoint + api_req

        request = requests.get(
                               api_link,
                               headers = headers
                              )
        status_code = request.status_code
        json_clan_info  = request.json()
        logging.info(f"Request status code: {status_code} | {datetime.now()}")
        return Response(status_code, json_clan_info)


class ResponseHandler(DataBaseManipulation):


    def _update_memberlist_in_DB(self, members_names: list[str], members_tags: list[str], members_roles: list[str], clan_tag: str):


        self.delete(Tables.ClanMembers.value, f"WHERE clan_tag = '{clan_tag}' AND member_tag NOT IN {tuple(members_tags)}")

        for member_name, member_tag, member_role in zip(members_names, members_tags, members_roles):
            self.insert(Tables.ClanMembers.value, {'member_name': member_name,
                        'member_tag' : member_tag,
                        'member_role' : member_role,
                        'clan_tag' : clan_tag}, ignore = True) 


    def _update_cwl_memberlist_in_DB(self, members_info: ClanWarLeagueMembersInfo, clan_tag: str):
        

        for member_name, member_tag, townHallLevel in zip(members_info.members_names, members_info.members_tags, members_info.members_townHallLevel):
            self.insert(Tables.CWL_members.value, {'member_name' : member_name,
                                                   'member_tag' : member_tag,
                                                   'townHallLevel' : townHallLevel,
                                                   'clan_tag' : clan_tag}, ignore=True)


    def _parse_clan_members_db_response(self, response: Response) -> ClanMembersInfo:

        match response.status_code:

            case 200:

                    members_names = [member['name'] for member in response.json_clan_info['items']]
                    members_tags = [member['tag'] for member in response.json_clan_info['items']]
                    members_roles = [members['role'] for members in response.json_clan_info['items']]

                    return ClanMembersInfo(members_names, members_tags, members_roles)
                
            case 404:
                
                raise BadRequestError()


    def _get_cw_membersinfo(self, response: Response) -> str:


        match response.status_code:

            case 200:

                if response.json_clan_info['state'] in ['inWar', 'preparation', 'warEnded']:

                    members_tags = (member['tag'] for member in response.json_clan_info['clan']['members'])
                    members_names = (member['name'] for member in response.json_clan_info['clan']['members'])
                    members_map_positions = (member['mapPosition'] for member in response.json_clan_info['clan']['members'])

                    return ClanWarMembersInfo(members_names, members_tags, members_map_positions)

                else:
                    raise ClanWarEndedError()

            case 404:
                raise BadRequestError()

    
    def _parse_cw_members_db_response(self, members_info: ClanWarMembersInfo):

        
        caption = ''
        for member_name, member_tag, member_map_position in zip(members_info.members_names, members_info.members_tags, members_info.members_map_positions):
            caption += text(bold(f'👤: {member_name}'),
                            bold(f'#️⃣: {member_tag}'),
                            bold(f'🗺: #{member_map_position}\n\n'), sep = '\n')
        return caption


    async def _parse_cwl_clan_members(self, members_info: list[tuple]) -> str:


        caption = ''
        for index, member_info in enumerate(members_info):
            caption += text(bold(f'{index+1}.'),
                            bold(f'👤: {member_info[0]}'),
                            bold(f'#️⃣: {member_info[1]}'),
                            bold(f'🗺: #{member_info[2]}\n\n'), sep = '\n')
        return caption

    
    def _parse_current_cwl_roundstatus(self, current_round: int) -> str:


        match current_round:

            case 0:

                caption = text(bold('Підготовка до першого раунду ⚔️'))

            case _:
                caption = text(bold(f'Підготовка до {current_round} раунду, війна на {current_round-1} раунді 🔫'))

        return caption


class ClanDataExtractions(ResponseHandler):


    async def _get_clan_tag(self, chat_id: int) -> str:


        clan_tag = self.fetch_one('clan_tag', Tables.Chats.value, f'WHERE chat_id = {chat_id}')
        return clan_tag[0]

    @staticmethod
    def _is_cwl_ended(cwl_state: dict[str,str]) -> bool:


        match cwl_state:

            case 'ended':
                
                return True

            case _:

                return False

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def get_cw_status(self, clan_tag: str) -> str:


        cw_info = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar').json_clan_info
        utcnow_time = str(datetime.utcnow().time()).split('.')[0] #.split() BECAUSE WE NEED TO GET RID OF MICROSECONDS

        match cw_info['state']:

            case 'inWar':

                caption = self._get_event_endtime('endTime', cw_info, utcnow_time)

            case 'preparation':

                caption = self._get_event_endtime('startTime', cw_info, utcnow_time)

            case _:

                caption = text(bold('Війна закінчена або не розпочата 😔'))
        
        return caption

    def __parse_datetime(self, unparsed_datetime: str) -> dict:


        year = unparsed_datetime[:4]
        month = unparsed_datetime[4:6]
        day = unparsed_datetime[6:8]
        hour = unparsed_datetime[9:11]
        minute = unparsed_datetime[11:13]
        second = unparsed_datetime[13:15]

        return {
                'hour' : hour, 'minute' : minute, 'second' : second, 
                'year' : year, 'month' : month, 'day' : day
               }
         
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    async def get_caption_memberlist(self, clan_tag: str) -> str:


        try:

            members_info = self.fetch_all('member_name, member_tag, member_role', Tables.ClanMembers.value, f"WHERE clan_tag = '{clan_tag}'")
            match members_info:
                
                case []:

                    await Polling().poll_clan_memberlist()
                    return await self.get_caption_memberlist(clan_tag)

                case _:

                    caption = ''
                    for index, member_info in enumerate(members_info):
                        caption += text(bold(f"{index+1}."),
                                        bold(f"👤 {member_info[0]}"),
                                        bold(f"#️⃣: {member_info[1]}"),
                                        bold(f"🗣: {member_info[2]}\n\n"), sep = '\n')
            return caption

        except mysql.connector.errors.ProgrammingError:
            caption = text(bold('З моєю Базою Даних сталася помилка 😔'))
            return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


    async def get_caption_cwl_memberlist(self, clan_tag: str) -> str:


        try:

            is_polling_cwl_memberlist_executed_flag = self._is_executed_cwl_memberlist_polling()
            clantag_in_cwl_table = self.fetch_one('clan_tag', Tables.CWL_members.value, f"WHERE clan_tag = '{clan_tag}'")
                          
            if not is_polling_cwl_memberlist_executed_flag:
                current_cwl_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar/leaguegroup') #HERE IS SLICE BECAUSE API ALREADY HAS PARSED SYMBOL '#' INTO THE LINK
                await self._insert_cwl_memberlist_in_DB(
                                                        Response(
                                                                 current_cwl_response.status_code, 
                                                                 current_cwl_response.json_clan_info
                                                                 ),
                                                        clan_tag
                                                       ) 
                state = current_cwl_response.json_clan_info['state']
                await self.__start_cwl_memberlist_polling(state, clan_tag)

            if not clantag_in_cwl_table:
                current_cwl_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar/leaguegroup') #HERE IS SLICE BECAUSE API ALREADY HAS PARSED SYMBOL '#' INTO THE LINK
                await self._insert_cwl_memberlist_in_DB(
                                                        Response(
                                                                 current_cwl_response.status_code, 
                                                                 current_cwl_response.json_clan_info
                                                                 ),
                                                        clan_tag
                                                       ) 


            caption = await self._parse_cwl_membersinfo_to_caption(clan_tag)
            return caption


        except BadRequestError:
            caption = text(bold('З мого боку сталася помилка 😔'))
            return caption

        except ClanWarEndedError:
            caption = text(bold('Війна закінчена, неможливо дізнатися учасників 😔'))
            return caption

        except ClanNotFoundError:
            caption = text(bold('Мені не вдалося знайти клан у списках кланів ЛВК 😔'))
            return caption


    def _is_executed_cwl_memberlist_polling(self) -> bool:


        thread_names = self._find_executed_threads_names()

        if 'PollCWL_memberlist' in thread_names:
            return True

        return False


    @staticmethod
    def _find_executed_threads_names():


        threads = threading.enumerate()
        threads_names = []
        for thread in threads:
            threads_names.append(thread.name)
        return threads_names

    
    @staticmethod
    async def __start_cwl_memberlist_polling(state: str, clan_tag: str):


        event = Event()
        Thread_PollClanWarLeagueMemberlist(event, 600, clan_tag, state).start()

    
    async def _parse_cwl_membersinfo_to_caption(self, clan_tag: str) -> str:

    
        members_info = self.fetch_all('*', Tables.CWL_members.value, f"WHERE clan_tag = '{clan_tag}'")
        caption = await self._parse_cwl_clan_members(members_info)
        return caption

    
    async def _insert_cwl_memberlist_in_DB(self, response: Response, clan_tag: str) -> str:


        match response.status_code:

            case 200:

                if response.json_clan_info['state'] in ['inWar', 'preparation']:

                    json_necessary_clan_info = self._find_necessary_clan(response.json_clan_info, clan_tag)
                    memberlist = json_necessary_clan_info['members']
                    members_info = self._return_cwl_members_info(memberlist)
                    self._update_cwl_memberlist_in_DB(members_info, clan_tag)


                else:
                    raise ClanWarEndedError()

            case 404:
                raise BadRequestError()

    
    @staticmethod
    def _find_necessary_clan(json_clan_info: Dict[str, str], clan_tag: str) -> Dict[str, str] | ClanNotFoundError:


            for clan in json_clan_info['clans']:

                if clan['tag'] == clan_tag.replace('O', '0'): #API JSON RESPONSE FOR SOME REASON REPLACES symbol o in upper register to 0 (zero with dot inside)
                    return clan
                else:
                    continue
            else:
                raise ClanNotFoundError()
        

    @staticmethod
    def _return_cwl_members_info(memberlist: Dict[str, str]) -> ClanWarLeagueMembersInfo:

        
        members_names = (member['name'] for member in memberlist)
        members_tags = (member['tag'] for member in memberlist)
        members_townhalls = (member['townHallLevel'] for member in memberlist)

        return ClanWarLeagueMembersInfo(members_names, members_tags, members_townhalls)

    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def get_cwl_results(self, clan_tag: str, chat_id: int):


        try:

            cwl_info_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar/leaguegroup') #here is slice because '#' in api link already parsed as '%23'
            match cwl_info_response.status_code:

                case 200:

                    cwl_info_json = cwl_info_response.json_clan_info
                    is_cwl_ended = self._is_cwl_ended(cwl_info_json['state'])
                    if is_cwl_ended:
                        
                        members_authentificated_flag = self._is_clanmembers_authentificated_in_table(clan_tag)
                        await self._notify_about_start_of_the_process(chat_id)

                        if members_authentificated_flag:

                            rounds = map(self._collect_cwl_round_tags, cwl_info_json['rounds'])
                            for war_tags in rounds:
                                    self._handle_necessary_round_war_tag(war_tags, clan_tag)

                        caption = self._parse_cwl_results_to_caption(clan_tag)
                        return caption

                    else:

                        caption = text(bold('На жаль, війна ще не закінчена або не розпочата 😔'))
                        return caption

                case 404:

                    raise BadRequestError()

        except BadRequestError:

            caption = text(bold('З мого боку сталася помилка 😔'))
            return caption

    
    def _collect_cwl_round_tags(self, cwl_rounds_info_json: dict[str, str]):


        return cwl_rounds_info_json['warTags']


    def _handle_necessary_round_war_tag(self, cwl_round_war_tags: list[str, str], clan_tag: str):


        for tag in cwl_round_war_tags:
            war_info = request_to_api(f'clanwarleagues/wars/%23{tag[1:]}').json_clan_info
            clan_tag_fixed = clan_tag.replace('O', '0')

            if war_info['clan']['tag'] == clan_tag_fixed: 
                self._initialize_cwl_memberlist_table('clan', war_info, clan_tag)
                
            
            if war_info['opponent']['tag'] == clan_tag_fixed:
                self._initialize_cwl_memberlist_table('opponent', war_info, clan_tag)

    
    def _initialize_cwl_memberlist_table(self, clan_war_side: str, war_info: dict[str], clan_tag: str):


        members_cwl_results = self._extract_members_info(war_info[clan_war_side]['members'])
        for member_cwl_result in members_cwl_results:
            self._insert_cwl_member_result_in_table(member_cwl_result, clan_tag)


    def _extract_members_info(self, memberlist: dict) -> Generator:


        members_names = (member['name'] for member in memberlist)
        members_tags = (member['tag'] for member in memberlist)
        members_stars = self._get_member_attacks_per_cwl_round(memberlist)

        for member_name, member_tag, member_stars in zip(members_names, members_tags, members_stars):
            
            yield ClanWarLeagueMembersAttacksResult(member_name, member_tag, member_stars)


    def _insert_cwl_member_result_in_table(self, member_cwl_result: ClanWarLeagueMembersAttacksResult, clan_tag: str):
        

        self.insert('ClanWarLeague_results', {"member_name": member_cwl_result.members_names, "member_tag" : member_cwl_result.members_tags, "stars" : member_cwl_result.members_stars,
                    "attacks" : 1, "avg_score" : member_cwl_result.members_stars, "clan_tag": clan_tag}, ignore = False,
                    expression = f"ON DUPLICATE KEY UPDATE stars = IF(clan_tag = '{clan_tag}', stars + VALUES(stars), stars), attacks = IF(clan_tag = '{clan_tag}', attacks+1, attacks), avg_score = stars / attacks")

    
    @staticmethod
    def _get_member_attacks_per_cwl_round(memberlist: list) -> Generator:


        for member in memberlist:
            try:
                yield int(member['attacks'][0]['stars'])

            except KeyError:
                yield 0


    def _is_clanmembers_authentificated_in_table(self, clan_tag: str) -> bool: #equals to False | True


        cursor = self.get_cursor()
        clan_tag_fixed = clan_tag.replace('0', 'O')
        cursor.execute(f'SELECT CASE WHEN EXISTS(SELECT clan_tag FROM ClanWarLeague_results WHERE clan_tag = "{clan_tag_fixed}") THEN 0 ELSE 1 END AS IsEmpty')
        result = cursor.fetchone()
        cursor.close()
        return result[0]


    def _parse_cwl_results_to_caption(self, clan_tag: str):


        members_info = self.fetch_all('*', 'ClanWarLeague_results', f"WHERE clan_tag = '{clan_tag}' ORDER BY avg_score DESC")
        caption = ''
        for index, member_info in enumerate(members_info):
            caption += text(bold(f'{index+1}.'),
                            bold(f'👤: {member_info[0]}'),
                            bold(f"#️⃣: {member_info[1]}"),
                            bold(f"⭐️: {member_info[2]}"),
                            bold(f"⚔️: {member_info[3]}"),
                            bold(f'AVG: {member_info[4]}\n\n'), sep = '\n')

        return caption

    async def _notify_about_start_of_the_process(self, chat_id: int, __ParseMode = ParseMode.MARKDOWN_V2):


        caption_pre_result = text(bold('У процесі 😌'))
        await bot.send_message(chat_id, caption_pre_result, __ParseMode)
        await bot.send_chat_action(chat_id, 'typing')

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    async def get_cwl_status(self, clan_tag):


        try:

            cwl_info_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar/leaguegroup') #here is slice because '#' in api link already parsed as '%23'
            match cwl_info_response.status_code:

                case 200:

                    cwl_info_json = cwl_info_response.json_clan_info
                    is_cwl_ended = self._is_cwl_ended(cwl_info_json['state'])
                    if is_cwl_ended:

                        caption = text(bold('Війна закінчена або не розпочата 😔'))
                        return caption

                    else:

                        rounds = map(self._collect_cwl_round_tags, cwl_info_json['rounds'])
                        last_available_round = self._define_last_available_round(rounds)
                        round_war_tag = list(rounds)[last_available_round][0]
                        caption = self._get_roundtime_by_current_round(current_round_tag = round_war_tag, number_current_round = last_available_round)
                        return caption

                case 404:

                    raise BadRequestError()

        except BadRequestError:
            caption = text(bold('З мого боку сталася помилка 😔'))
            return caption


    def _define_last_available_round(self, rounds: list[str]):


        for index, round in enumerate(rounds):
            for war_tag in round:
                if war_tag.startswith('#0'):
                    
                    return index-1
        else:
            return index

    def _get_roundtime_by_current_round(self, current_round_tag: list[str], number_current_round: int) -> str:


        utcnow_time = str(datetime.utcnow()).split('.')[0] #.split() BECAUSE WE NEED TO GET RID OF MICROSECONDS
        round_info = request_to_api(f'clanwarleagues/wars/%23{current_round_tag[1:]}').json_clan_info
        match number_current_round:

            case 0:

                result = self._get_event_endtime('startTime', round_info, utcnow_time)
                caption = text(bold(f'Час до початку першого раунду: {result} 🕔'))
                return caption

            case 6:
                
                state = round_info['state']

                if state == 'preparation':

                    result = result = self._get_event_endtime('startTime', round_info, utcnow_time)
                    caption = text(bold(f'Час до початку останнього раунду: {result} 🕔'))
                    return caption

                if state == 'inWar':

                    result = result = self._get_event_endtime('endTime', round_info, utcnow_time)
                    caption = text(bold(f'Час до кінця останнього раунду: {result} 🕔'))
                    return caption

            case _:

                result = self._get_event_endtime('endTime', round_info, utcnow_time)
                caption = text(bold(f'Час до кінця {number_current_round} раунду: {result} 🕔'))
                return caption

        return caption


    def _get_event_endtime(self, event_time: str, round_info: dict[str], utcnow_time: str):


        parsed_starttime = self.__parse_datetime(round_info[event_time])
        handled_event_time = datetime.strptime(f'{parsed_starttime["year"]}-{parsed_starttime["month"]}-{parsed_starttime["day"]} {parsed_starttime["hour"]}:{parsed_starttime["minute"]}:{parsed_starttime["second"]}', '%Y-%m-%d %H:%M:%S')
        handled_utcnow_time = datetime.strptime(utcnow_time, '%Y-%m-%d %H:%M:%S')

        result = handled_event_time - handled_utcnow_time
        return result

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def get_caption_cw_memberlist(self, clan_tag: str) -> str:


        try:
            cw_clan_members_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar') #here is slice because '#' in api link already parsed as '%23'
            members_info = await self._get_cw_membersinfo(
                                                                    Response(
                                                                             cw_clan_members_response.status_code,
                                                                             cw_clan_members_response.json_clan_info
                                                                            )
                                                                   )

            self._parse_cw_members_db_response(members_info)

        except BadRequestError:
            caption = text(bold('З мого боку сталася помилка 😔'))
            return caption


        except ClanWarEndedError:
            caption = text(bold('Війна закінчена, неможливо дізнатися учасників 😔'))
            return caption


    async def get_caption_rade_statistic(self, clan_tag: str, chat_id: int):


        try:

            members_info = self.fetch_all('member_name, collected_coins, donated_coins, saved_coins', Tables.RadeMembers.value, f"WHERE clan_tag = '{clan_tag}'")
            match members_info:
                
                case []:
                    
                    await self._notify_about_start_of_the_process(chat_id)
                    await Polling().poll_rade_statistic()
                    return await self.get_caption_rade_statistic(clan_tag, chat_id)

                case _:

                    caption = ''
                    for index, member_info in enumerate(members_info):
                        caption += text(bold(f"{index+1}."),
                                        bold(f"👤 {member_info[0]}"),
                                        bold(f"Накопичені 🪙: {member_info[1]}"),
                                        bold(f"Пожертвувані 🪙: {member_info[2]}"),
                                        bold(f"Збережені 🪙: {member_info[3]}\n\n"), sep = '\n')
            return caption

        except mysql.connector.errors.DatabaseError:
            caption = text(bold('З моэю Базою Даних сталася помилка 😔'))
            return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class Polling(ClanDataExtractions):


    def _get_clan_tags_from_db(self) -> list[str]:


        clan_tags = [clan_tag[0] for clan_tag in self.fetch_all('clan_tag', Tables.Chats.value)]
        return clan_tags


    @staticmethod
    def _get_clan_members_taglist(clan_tag: str) -> Generator:

        logging.info(f'PollRadeStatistic:getClanMemberList | {datetime.now()}')
        clan_info = request_to_api(f'clans/%23{clan_tag[1:]}/members').json_clan_info
        members_tags = (member['tag'] for member in clan_info['items'])
        return members_tags


    def _insert_member_rade_results_in_table(self, member_info: list[str], clan_tag: str):


        collected_coins = member_info['achievements'][-2]['value']
        donated_coins = member_info['achievements'][-1]['value']
        self.insert("RadeMembers", {"member_name": member_info['name'], "member_tag": member_info['tag'], "collected_coins" : collected_coins, "donated_coins" : donated_coins,
                    "saved_coins" : collected_coins - donated_coins, "clan_tag": clan_tag}, ignore = False,
        expression = f"ON DUPLICATE KEY UPDATE collected_coins = {collected_coins}, donated_coins = {donated_coins}, saved_coins = {collected_coins - donated_coins}")
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def poll_clan_memberlist(self): 


        try:
            clan_tags = self._get_clan_tags_from_db()

            for clan_tag in clan_tags:

                clan_members_response = request_to_api(f'clans/%23{clan_tag[1:]}/members') #HERE IS SLICE BECAUSE API ALREADY HAVE PARSED SYMBOL '#' INTO THE LINK
                members_info = self._parse_clan_members_db_response(
                                                              Response(
                                                                       clan_members_response.status_code, 
                                                                       clan_members_response.json_clan_info
                                                                       )
                                                             )

                self._update_memberlist_in_DB(
                                              members_info.members_names,
                                              members_info.members_tags,
                                              members_info.members_roles,
                                              clan_tag
                                             )

            
        except ConnectionError:
            logging.exception('Connection error from back-end concern...')

        except BadRequestError:
            logging.exception('RequestStatusCode - 404, maybe clan was deleted/became private')

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def poll_rade_statistic(self):

        try:
            clan_tags = self._get_clan_tags_from_db()
            for clan_tag in clan_tags:
                members_tags = self._get_clan_members_taglist(clan_tag)

                for member_tag in members_tags:
                    logging.info(f'PollRadeStatistic:getMemberAchievements | {datetime.now()}')
                    member_info = request_to_api(f'players/%23{member_tag[1:]}')
                    self._insert_member_rade_results_in_table(member_info.json_clan_info, clan_tag)

        except ConnectionError:
            logging.exception('Connection error from back-end concern...')


class Thread_PollClanWarLeagueMemberlist(Thread):

    
    def __init__(self, event: Event, delay_sec: int, clan_tag: str, state: str, __name = 'PollCWL_memberlist'):


        Thread.__init__(self, name = __name)
        self.flag = event
        self.delay_sec = delay_sec
        self.clan_tag = clan_tag
        self.state = state

    def run(self):


        while not self.flag.wait(self.delay_sec):
            match self.state:

                case 'inWar' | 'preparation':
                    continue

                case 'ended':
                    
                    DataBaseManipulation().delete(Tables.CWL_members.value, f"WHERE clan_tag = '{self.clan_tag}'")