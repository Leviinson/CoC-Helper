'''Represents clan data handlers and their look at output to the user in chat.

Classes:

    Parsers
    ClanDataExtractions(DataBaseManipulations, Parsers)
    Polling(ClanDataExtractions)
    Thread_PollClanWarLeagueMemberlist(Thread)

Functions:

    request_to_api(api_req: str) -> Response [class from module `type_hintings.py`]
'''


import requests
import logging
from requests.exceptions import ConnectionError
from typing import Generator
from threading import enumerate as thread_enumerate
from datetime import datetime

from aiogram.utils.markdown import text, bold
from aiogram.types import ParseMode
import mysql.connector.errors

from bot_config import API_TOKEN, bot
from database import DataBaseManipulations
from errors import BadRequestError, ClanNotFoundError, ClanWarEndedError

from type_hintings import Response, DateTime
from type_hintings import ClanWarLeagueMembersInfo, ClanWarLeagueMembersAttacksResult
from type_hintings import ClanWarMembersInfo, ClanMembersInfo
from type_hintings import SelectQuery, Tables


logging.basicConfig(level = logging.INFO)
def request_to_api(api_req: str) -> Response:
    '''Takes an api endpoint, returns response status code and a json result.'''

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
    json_api_response_json  = request.json()
    logging.info(f"Request status code: {status_code} | {datetime.now()}")
    return Response(status_code, json_api_response_json)


class Parsers: 
    '''Parses clan info from data set to message caption for user in chat.'''

    def _parse_clan_memberlist_to_caption(self, members_info_db_response: list) -> str:
        '''Takes DB response about memberlist info, return message caption.'''

        caption = ''
        for index, member_info in enumerate(members_info_db_response):
            caption += text(bold(f"{index+1}."),
                            bold(f"👤 {member_info[0]}"),
                            bold(f"#️⃣: {member_info[1]}"),
                            bold(f"🗣: {member_info[2]}\n\n"), sep = '\n')
        return caption


    def _parse_cw_membersinfo_to_caption(self, members_info: ClanWarMembersInfo):
        '''Takes members info formatted in ClanWarMembersInfo typehinting class, returns message caption.'''
        
        caption = ''
        for member_name, member_tag, member_map_position in zip(members_info.members_names, members_info.members_tags, members_info.members_map_positions):
            caption += text(bold(f'👤: {member_name}'),
                            bold(f'#️⃣: {member_tag}'),
                            bold(f'🗺: #{member_map_position}\n\n'), sep = '\n')
        return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def _parse_cwl_memberlist_to_caption(self, members_info: list) -> str:
        '''Takes DB response about cwl memberlist, returns message caption.'''

        caption = ''
        for index, member_info in enumerate(members_info):
            caption += text(bold(f'{index+1}.'),
                            bold(f'👤: {member_info[0]}'),
                            bold(f'#️⃣: {member_info[1]}'),
                            bold(f'🗺: #{member_info[2]}\n\n'), sep = '\n')
        return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 
    def _parse_cwl_results_to_caption(self, members_info: list):
        '''Takes DB response about cwl clan results, returns message caption.'''

        caption = ''
        for index, member_info in enumerate(members_info):
            caption += text(bold(f'{index+1}.'),
                            bold(f'👤: {member_info[0]}'), #indexes - it`s column number of the table ClanWarLeague_results
                            bold(f"#️⃣: {member_info[1]}"),
                            bold(f"⭐️: {member_info[2]}"),
                            bold(f"⚔️: {member_info[3]}"),
                            bold(f'AVG: {member_info[4]}\n\n'), sep = '\n')

        return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def _parse_rade_statistic_to_caption(self, members_info: list[str]) -> str:
        '''Takes DB response about clan rade statistic, returns message caption.'''

        caption = ''
        for index, member_info in enumerate(members_info):
            caption += text(bold(f"{index+1}."),
                            bold(f"👤 {member_info[0]}"),
                            bold(f"Накопичені 🪙: {member_info[1]}"),
                            bold(f"Пожертвувані 🪙: {member_info[2]}"),
                            bold(f"Збережені 🪙: {member_info[3]}\n\n"), sep = '\n')
        return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def _parse_datetime(self, unparsed_datetime: str) -> DateTime:
        '''Takes incorrect ISO datetime format, separates by year, month, day, hour, minute, data; returns formatted look in typehinting Datetime class.'''

        year = unparsed_datetime[:4]
        month = unparsed_datetime[4:6]
        day = unparsed_datetime[6:8]
        hour = unparsed_datetime[9:11]
        minute = unparsed_datetime[11:13]
        seconds = unparsed_datetime[13:15]

        return DateTime(year, month, day,
                        hour, minute, seconds)


class ClanDataExtractions(DataBaseManipulations, Parsers):
    '''Processes api response about clan info and parses it to message caption for user in chat.
    
    It will be good, if at the start you get acquainted with look of the API response.'''

    @staticmethod
    def _is_cwl_ended(cwl_state: dict) -> bool:
        '''Takes cwl state, returns True if it is ended.'''

        match cwl_state:

            case 'ended':
                return True

            case _:
                return False


    def get_clan_tag(self, chat_id: int) -> str:
        '''Takes chat id of current chat and returns relative clan tag to this chat.'''

        clan_tag = self.fetch_one(SelectQuery('clan_tag', Tables.Chats.value, f'WHERE chat_id = %s', (chat_id,)))
        return clan_tag[0] #object of NoneType isn`t subscriptable, but keep in mind, that we can`t start use the program, while user is not registered
    
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def get_cw_status(self, clan_tag: str) -> str:
        '''Takes clan tag, returns current formatted status of CW to message caption.'''

        cw_info = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar').json_api_response_info
        current_utc_time = str(datetime.utcnow()).split('.')[0] #.split() BECAUSE WE NEED TO GET RID OF MICROSECONDS
        match cw_info['state']:

            case 'inWar':
                end_time = self._get_state_endtime('endTime', cw_info, current_utc_time)
                caption = text(bold('⏰ Час до кінця бою: ', end_time))

            case 'preparation':
                end_time = self._get_state_endtime('startTime', cw_info, current_utc_time)
                caption = text(bold('⏰ Час до закінчення підготовки: ', end_time))
            case _:
                caption = text(bold('Війна закінчена або не розпочата 😔'))
        
        return caption
         
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    async def get_caption_memberlist(self, clan_tag: str) -> str:
        '''Takes clan tag, collects members info from DB, returns formatted clan memberlist to message 
        caption if the corresponding polling is started, else starts it and calls func `self.get_caption_memberlist(clan_tag: str)` recursively.
        
        If there is no members info (in DB), thant raises `mysql.connector.errors.ProgrammingError` error and 
        returns corresponding message error.'''

        try:

            members_info_db_response = self.fetch_all(SelectQuery('member_name, member_tag, member_role', Tables.ClanMembers.value, f"WHERE clan_tag = %s", (clan_tag, )))
            match members_info_db_response:
                
                case []:
                    clan_members_response = request_to_api(f'clans/%23{clan_tag[1:]}/members')
                    await Polling().poll_clan_memberlist(Response(
                                                                  clan_members_response.status_code,
                                                                  clan_members_response.json_api_response_info
                                                                  ),
                                                         clan_tag)
                    return await self.get_caption_memberlist(clan_tag)

                case _:
                    caption = self._parse_clan_memberlist_to_caption(members_info_db_response)

            return caption

        except mysql.connector.errors.ProgrammingError:
            caption = text(bold('З моєю Базою Даних сталася помилка 😔'))
            return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


    async def get_caption_cwl_memberlist(self, clan_tag: str) -> str:
        '''Takes `clan tag`, checks if polling CWL memberlistreturns is launched and if clan members info is already into the table.

        Returns message caption with members info if all is ok; else launches polling/inserts member info
            into the table while polling is launched and returns message caption with members info.'''

        try:

            is_polling_cwl_memberlist_launched_flag = self._is_launched_cwl_memberlist_polling()
            clantag_into_the_cwl_memberlist_table_flag = self.fetch_one(SelectQuery('clan_tag', Tables.CWL_members.value, f"WHERE clan_tag = %s", (clan_tag,)))
                          
            if not is_polling_cwl_memberlist_launched_flag:
                current_cwl_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar/leaguegroup') #HERE IS SLICE BECAUSE API ALREADY HAS PARSED SYMBOL '#' INTO THE LINK
                await self._insert_cwl_memberlist_in_DB(
                                                        Response(
                                                                 current_cwl_response.status_code, 
                                                                 current_cwl_response.json_api_response_info
                                                                 ),
                                                        clan_tag
                                                       ) 

            if not clantag_into_the_cwl_memberlist_table_flag:
                current_cwl_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar/leaguegroup') #HERE IS SLICE BECAUSE API ALREADY HAS PARSED SYMBOL '#' INTO THE LINK
                await self._insert_cwl_memberlist_in_DB(
                                                        Response(
                                                                 current_cwl_response.status_code, 
                                                                 current_cwl_response.json_api_response_info
                                                                 ),
                                                        clan_tag
                                                       ) 

            members_info = self.fetch_all(SelectQuery('*', Tables.CWL_members.value, f"WHERE clan_tag = %s", (clan_tag,)))
            caption = self._parse_cwl_memberlist_to_caption(members_info)
            return caption


        except BadRequestError:
            caption = text(bold('З мого боку сталася помилка або дані про минуле ЛВК наразі недоступні 😔'))
            return caption

        except ClanWarEndedError:
            self.delete(Tables.CWL_members.value, f"WHERE clan_tag = '{clan_tag}'")
            caption = text(bold('Війна закінчена, неможливо дізнатися учасників 😔'))
            return caption

        except ClanNotFoundError:
            caption = text(bold('Мені не вдалося знайти клан у списках кланів ЛВК 😔'))
            return caption


    def _is_launched_cwl_memberlist_polling(self) -> bool:
        '''Searches current polling thread into the list of launched threads.
        
        Returns True if thread name is found, else returns False.'''

        thread_names = self._find_launched_threads_names()

        if 'PollCWL_memberlist' in thread_names:
            return True

        return False


    @staticmethod
    def _find_launched_threads_names():
        '''Returns list of launched threads'''


        threads = thread_enumerate()
        threads_names = []
        for thread in threads:
            threads_names.append(thread.name)
        return threads_names

    
    async def _insert_cwl_memberlist_in_DB(self, response: Response, clan_tag: str):
        '''Takes typehinting class "Response" and clan_tag as a parameters.

        Continues operation if cwl state is `'inWar'` or `'preparation'`, else raises `ClanWarEndedError`. 
        '''
    
        match response.status_code:

            case 200:

                if response.json_api_response_info['state'] in ['inWar', 'preparation']:

                    json_necessary_clan_info = self._find_necessary_clan(response.json_api_response_info, clan_tag)
                    memberlist = json_necessary_clan_info['members']
                    members_info = self._get_cwl_members_info(memberlist)
                    self._update_cwl_memberlist_in_DB(members_info, clan_tag)


                else:
                    raise ClanWarEndedError()

            case 404:
                raise BadRequestError()

    
    @staticmethod
    def _find_necessary_clan(json_clan_info: dict, clan_tag: str) -> dict | ClanNotFoundError:
        '''Takes an api response in JSON format and clan tag as a parameters;

        Checks if clan tag from list of clans corresponds to the desired clan tag, specified in the func parameters.
        Returns clan information in JSON format of the desired clan.'''

        for clan in json_clan_info['clans']:

            if clan['tag'].replace('0', 'O') == clan_tag: #API JSON RESPONSE FOR SOME REASON REPLACES symbol o in upper register to 0 (zero with dot inside)
                return clan

            else:
                continue
        else:
            raise ClanNotFoundError()
        

    @staticmethod
    def _get_cwl_members_info(memberlist: dict) -> ClanWarLeagueMembersInfo:
        '''Takes memberlist in JSON format, collects member name, tag and townhall level into 3 separate generators.
        
        Returns `ClanWarLeagueMembersInfo` with this generators as a parameters.'''
        
        members_names = (member['name'] for member in memberlist)
        members_tags = (member['tag'] for member in memberlist)
        members_townhalls = (member['townHallLevel'] for member in memberlist)

        return ClanWarLeagueMembersInfo(members_names, members_tags, members_townhalls)

    
    def _update_cwl_memberlist_in_DB(self, members_info: ClanWarLeagueMembersInfo, clan_tag: str):
        '''Takes typehinting class ClanWarLeagueMembersInfo, clan tag as a parameters.
        
        Inserts members info into the table `ClanWarLeague_members`.'''

        for member_name, member_tag, townHallLevel in zip(members_info.members_names, members_info.members_tags, members_info.members_townHallLevel):
            self.insert(Tables.CWL_members.value, {'member_name' : member_name,
                                                   'member_tag' : member_tag,
                                                   'townHallLevel' : townHallLevel,
                                                   'clan_tag' : clan_tag}, ignore=True)

    #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def get_cwl_results(self, clan_tag: str, chat_id: int):
        '''Takes clan tag, chat id as a parameters.
        Sends request to API about current CWL war. Continues operation if status code of response equals to 200.
        Else raises `BadRequestError`.
        
        Then checks if CWL state is "ended" and continues operation, if it's true.
        
        Else returns corresponding message caption error.'''

        try:
            cwl_info_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar/leaguegroup') #here is slice because '#' in api link already parsed as '%23'
            match cwl_info_response.status_code:

                case 200:

                    cwl_info_json = cwl_info_response.json_api_response_info
                    is_cwl_ended = self._is_cwl_ended(cwl_info_json['state'])
                    if is_cwl_ended:
                        
                        members_authentificated_flag = self._is_clanmembers_authentificated_in_table(clan_tag)
                        await self._notify_about_start_of_the_process(chat_id)

                        if members_authentificated_flag:
                            self._load_cwl_results_in_table(clan_tag, cwl_info_json['rounds'])
                        
                        members_info = self.fetch_all(SelectQuery('*', Tables.CWL_results.value, f"WHERE clan_tag = %s ORDER BY avg_score DESC", (clan_tag,)))
                        caption = self._parse_cwl_results_to_caption(members_info)
                        return caption

                    else:

                        caption = text(bold('На жаль, війна ще не закінчена або не розпочата 😔'))
                        return caption

                case 404:

                    raise BadRequestError()

        except BadRequestError:

            caption = text(bold('З мого боку сталася помилка або дані до минулого ЛВК наразі недоступні 😔'))
            return caption

    def _load_cwl_results_in_table(self, clan_tag: str, cwl_rounds_info_json: dict):
        '''Takes clan tag and list of CWL rounds in json format, collects list of rounds with tags of each skirmishe
        in it and calls func `_handle_necessary_round_war_tag` with necessary list of skirmishe and clan tag as a parameters.
        '''

        rounds = map(self._collect_cwl_round_tags, cwl_rounds_info_json)
        for war_tags in rounds:
            self._handle_necessary_round_war_tag(war_tags, clan_tag)

    
    def _collect_cwl_round_tags(self, cwl_rounds_info_json: dict):
        '''Extracts skirmishes tags from each round.
        
        Returns taglist of the skirmishes.'''

        return cwl_rounds_info_json['warTags']


    def _handle_necessary_round_war_tag(self, cwl_round_war_tags: list, clan_tag: str):
        '''Takes list of skirmishes tags and clan tag as a parameters, makes for each api request about results
        of it and checks the side played by the clan.
        
        Then start initialization of membersinfo into the table ClanWarLeague_results.'''

        for tag in cwl_round_war_tags:
            war_info = request_to_api(f'clanwarleagues/wars/%23{tag[1:]}').json_api_response_info
            clan_tag_fixed = clan_tag.replace('O', '0')

            if war_info['clan']['tag'] == clan_tag_fixed: 
                self._initialize_cwl_memberlist_table('clan', war_info, clan_tag)
                
            
            if war_info['opponent']['tag'] == clan_tag_fixed:
                self._initialize_cwl_memberlist_table('opponent', war_info, clan_tag)

    
    def _initialize_cwl_memberlist_table(self, clan_war_side: str, war_info: dict, clan_tag: str):
        '''Takes the side played by the clan, information about the results of the skirmish and clan tag as a parameters.
        
        Extracts members info from skirmishe results and inserts information of each clan memebrs into the table ClanWarLeague_results.'''

        members_cwl_results = self._extract_members_info(war_info[clan_war_side]['members'])
        for member_cwl_result in members_cwl_results:
            self._insert_cwl_member_result_in_table(member_cwl_result, clan_tag)


    def _extract_members_info(self, member_cwl_result: dict) -> Generator:
        '''Takes cwl members results as a parameter and divides members names, tags and earned stars into the 3 separate generators.
        
        combines information about each member into a single generator from typehinting classes `ClanWarLeagueMembersAttacksResult`.'''


        members_names = (member['name'] for member in member_cwl_result)
        members_tags = (member['tag'] for member in member_cwl_result)
        members_stars = self._get_member_attacks_per_cwl_round(member_cwl_result)

        for member_name, member_tag, member_stars in zip(members_names, members_tags, members_stars):
            
            yield ClanWarLeagueMembersAttacksResult(member_name, member_tag, member_stars)


    def _insert_cwl_member_result_in_table(self, member_cwl_result: ClanWarLeagueMembersAttacksResult, clan_tag: str):
        '''Takes member cwl result in the form of typehinting class `ClanWarLeagueMembersAttacksResult` and clan tag as a parameters;

        then finally inserts member info into the table `ClanWarLeague_results`.'''

        self.insert(Tables.CWL_results.value, {"member_name": member_cwl_result.members_names, "member_tag" : member_cwl_result.members_tags, "stars" : member_cwl_result.members_stars,
                    "attacks" : 1, "avg_score" : member_cwl_result.members_stars, "clan_tag": clan_tag}, ignore = False,
                    expression = f"ON DUPLICATE KEY UPDATE stars = IF(clan_tag = '{clan_tag}', stars + VALUES(stars), stars), attacks = IF(clan_tag = '{clan_tag}', attacks+1, attacks), avg_score = stars / attacks")

    
    @staticmethod
    def _get_member_attacks_per_cwl_round(memberlist: dict) -> Generator:
        '''Separate generator function takes information of each member in memberlist and returns number of earned stars as int.'''

        for member in memberlist:
            try:
                yield int(member['attacks'][0]['stars'])

            except KeyError:
                yield 0


    def _is_clanmembers_authentificated_in_table(self, clan_tag: str) -> bool:
        '''Takes clan tag as a parameter and check if clan already exists in the table.
        
        Serves to determine, is it worth to do request about each member to the api, or just load
            information about each member from the table and don't spend extra resources for requests.
            
        Returns 0 or 1, that equals to False or True when it will come to theck results.'''

        cursor = self.get_cursor()
        clan_tag_fixed = clan_tag.replace('0', 'O')
        cursor.execute(f'SELECT CASE WHEN EXISTS(SELECT clan_tag FROM {Tables.CWL_results.value} WHERE clan_tag = "{clan_tag_fixed}") THEN 0 ELSE 1 END AS IsEmpty')
        result = cursor.fetchone()
        cursor.close()
        return result

    async def _notify_about_start_of_the_process(self, chat_id: int, __ParseMode = ParseMode.MARKDOWN_V2):
        '''Takes chat id and ParseMode as a parameters, serves to notify the user, that obtaining information about each member of the CWL began.
        Returns directly into the chat message, that process began.'''

        caption_pre_result = text(bold('У процесі 😌'))
        await bot.send_message(chat_id, caption_pre_result, __ParseMode)
        await bot.send_chat_action(chat_id, 'typing')

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    async def get_cwl_status(self, clan_tag):
        '''Takes clan tag as a parameter, sends request to the API about current CWL war of the clan.
        
        Continues operation if resposne status code equals to 200, else raises BadRequestError.'''

        try:

            cwl_info_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar/leaguegroup') #here is slice because '#' in api link already parsed as '%23'
            match cwl_info_response.status_code:

                case 200:

                    cwl_info_json = cwl_info_response.json_api_response_info
                    is_cwl_ended = self._is_cwl_ended(cwl_info_json['state'])
                    if is_cwl_ended:

                        caption = text(bold('Війна закінчена або не розпочата 😔'))
                        return caption

                    else:

                        rounds = map(self._collect_cwl_round_tags, cwl_info_json['rounds'])
                        last_available_round = self._define_last_available_round(rounds)
                        round_war_tag = list(rounds)[last_available_round][0]
                        caption = self._get_end_time_of_the_current_round_state(current_round_tag = round_war_tag, current_round_number = last_available_round)
                        return caption

                case 404:

                    raise BadRequestError()

        except BadRequestError:
            caption = text(bold('З мого боку сталася помилка 😔'))
            return caption


    def _define_last_available_round(self, rounds: list):
        '''Takes list of the skirmishes tags as a parameter, returns index of the last

        unavailable round `(NOT SKIRMISH INDEX, CONCRECTLY LAST ROUND INDEX.)`'''

        for index, round in enumerate(rounds):
            for war_tag in round:
                if war_tag.startswith('#0'):
                    
                    return index-1
        else:
            return index

    def _get_end_time_of_the_current_round_state(self, current_round_tag: list[str], current_round_number: int) -> str:
        '''Takes current round tag and current roudn number as a parameters, defines caption for index 0 and 6
        
        because computing of the state end time is different in according with others cases.
        
        Returns prepared message caption.'''

        current_utc_time = str(datetime.utcnow()).split('.')[0] #.split() BECAUSE WE NEED TO GET RID OF MICROSECONDS
        round_info = request_to_api(f'clanwarleagues/wars/%23{current_round_tag[1:]}').json_api_response_info
        match current_round_number:

            case 0:

                result = self._get_state_endtime('startTime', round_info, current_utc_time)
                caption = text(bold(f'Час до початку першого раунду: {result} 🕔'))

            case 6:
                
                state = round_info['state']

                if state == 'preparation':

                    result = result = self._get_state_endtime('startTime', round_info, current_utc_time)
                    caption = text(bold(f'Час до початку останнього раунду: {result} 🕔'))

                if state == 'inWar':

                    result = result = self._get_state_endtime('endTime', round_info, current_utc_time)
                    caption = text(bold(f'Час до кінця останнього раунду: {result} 🕔'))

            case _:

                result = self._get_state_endtime('endTime', round_info, current_utc_time)
                caption = text(bold(f'Час до кінця {current_round_number} раунду: {result} 🕔'))

        return caption


    def _get_state_endtime(self, event_time: str, round_info: dict, current_utc_time: str):
        '''Computing state end time by subtracting from current utc time, returns -> datetime.datetime.timedelta'''

        parsed_starttime = self._parse_datetime(round_info[event_time])
        formatted_event_time = datetime.strptime(f'{parsed_starttime.year}-{parsed_starttime.month}-{parsed_starttime.day} {parsed_starttime.hour}:{parsed_starttime.minute}:{parsed_starttime.seconds}', '%Y-%m-%d %H:%M:%S')
        formatted_current_utc_time = datetime.strptime(current_utc_time, '%Y-%m-%d %H:%M:%S')

        result = formatted_event_time - formatted_current_utc_time
        return result

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def get_caption_cw_memberlist(self, clan_tag: str) -> str:
        '''Takes clan tag as a parameter, makes request to the api about current clan war.
            Extracts from api response membersinfo and parsed it to the message caption.
                Returns message caption.
        
        Returns message caption for the user, corresponding to the each error, that met in the process.'''

        try:
            cw_api_response = request_to_api(f'clans/%23{clan_tag[1:]}/currentwar') #here is slice because '#' in api link already parsed as '%23'
            match cw_api_response.status_code:

                case 200:
                    members_info = self._get_cw_membersinfo(
                                                             Response(
                                                                      cw_api_response.status_code,
                                                                      cw_api_response.json_api_response_info
                                                                     )
                                                            )

                    caption = self._parse_cw_membersinfo_to_caption(members_info)

                case 404:
                    caption = text(bold('З мого боку сталася помилка 😔'))

        except ClanWarEndedError:
            caption = text(bold('Війна закінчена, неможливо дізнатися учасників 😔'))

        return caption

    
    def _get_cw_membersinfo(self, response: Response) -> ClanWarMembersInfo:
        '''Takes typehinting class `Response` as a parameter, 
            collects members info from api response into the three separate generators.
        
        Returns typehinting filled class `ClanWarMembersInfo`'''

        if response.json_api_response_info['state'] in ['inWar', 'preparation', 'warEnded']:

            members_tags = (member['tag'] for member in response.json_api_response_info['clan']['members'])
            members_names = (member['name'] for member in response.json_api_response_info['clan']['members'])
            members_map_positions = (member['mapPosition'] for member in response.json_api_response_info['clan']['members'])

            return ClanWarMembersInfo(members_names, members_tags, members_map_positions)

        else:
            raise ClanWarEndedError()


    async def get_caption_rade_statistic(self, clan_tag: str, chat_id: int):
        '''Takes clan tag, chat id as a parameters, fetching members rade results from table if it was initialized whenever
        
        and parsed it to the message caption.
            Else launched polling requests to the API and then recalls this func recursively.
        Returns message caption with results of the clan members on the raid.
        '''

        try:

            members_info = self.fetch_all(SelectQuery('member_name, collected_coins, donated_coins, saved_coins', Tables.RadeMembers.value, f"WHERE clan_tag = %s", (clan_tag,)))
            match members_info:
                
                case []:
                    
                    await self._notify_about_start_of_the_process(chat_id)
                    clan_members_response = request_to_api(f'clans/%23{clan_tag[1:]}/members').json_api_response_info
                    await Polling().poll_rade_statistic(clan_members_response, clan_tag)
                    return await self.get_caption_rade_statistic(clan_tag, chat_id)

                case _:
                    caption = self._parse_rade_statistic_to_caption(members_info)
                    
            return caption

        except mysql.connector.errors.DatabaseError:
            caption = text(bold('З моэю Базою Даних сталася помилка 😔'))
            return caption

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class Polling(ClanDataExtractions):


    async def poll_clan_memberlist(self, clan_members_response: Response, clan_tag: str): 
        '''Takes polling response and clan tag as a parameter.
        Inserts data into the `ClanMembers` table.'''

        try:
            members_info = self._get_clan_memberlist(
                                                    Response(
                                                            clan_members_response.status_code, 
                                                            clan_members_response.json_api_response_info
                                                            )
                                                    )

            self._update_memberlist_in_DB(members_info, clan_tag)

            
        except ConnectionError:
            logging.exception('Connection error from back-end concern...')

        except BadRequestError:
            logging.exception('RequestStatusCode - 404, maybe clan was deleted/became private')


    def _get_clan_memberlist(self, response: Response) -> ClanMembersInfo:
        '''Takes typehinting class `Response` as a parameter, divide members info to three separate lists.
        Returns filled typehinting class `ClanMembersInfo`.'''

        match response.status_code:

            case 200:
                    
                    members_names = [member['name'] for member in response.json_api_response_info['items']]
                    members_tags = [member['tag'] for member in response.json_api_response_info['items']]
                    members_roles = [members['role'] for members in response.json_api_response_info['items']]
                    return ClanMembersInfo(members_names, members_tags, members_roles)
                
            case 404:
                
                raise BadRequestError()

    
    def _update_memberlist_in_DB(self, members_info: ClanMembersInfo, clan_tag: str):
        '''Takes typehinting class `ClanMembersInfo and clan tag as a parameters.
        
        Deletes extra members from the table, that was kicked/banned in the clan and don't existing anymore.
        
        Inserts new clan members into the table.`'''
        self.delete(Tables.ClanMembers.value, f"WHERE clan_tag = '{clan_tag}' AND member_tag NOT IN {tuple(members_info.members_tags)}")

        for member_name, member_tag, member_role in zip(members_info.members_names, members_info.members_tags, members_info.members_roles):
            self.insert(Tables.ClanMembers.value, {'member_name': member_name,
                        'member_tag' : member_tag,
                        'member_role' : member_role,
                        'clan_tag' : clan_tag}, ignore = True)

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    async def poll_rade_statistic(self, json_clan_members_response: dict, clan_tag: str):
        '''Starts send polling requests to the API about achievements of each clan member,
            that storages members results in rade wars.
        Inserts members results into the table.'''
        try:
            
            members_tags = self._get_clan_members_taglist(json_clan_members_response)
            for member_tag in members_tags:
                logging.info(f'PollRadeStatistic:getMemberAchievements | {datetime.now()}')
                member_info = request_to_api(f'players/%23{member_tag[1:]}')
                self._insert_member_rade_results_in_table(member_info.json_api_response_info, clan_tag)

        except ConnectionError:
            logging.exception('Connection error from back-end concern...')


    @staticmethod
    def _get_clan_members_taglist(clan_info: dict) -> Generator:
        '''Takes clan info in a json format as a parameter.

        Returns generator of memebrs tags.'''

        members_tags = (member['tag'] for member in clan_info['items'])
        return members_tags


    def _insert_member_rade_results_in_table(self, member_info: dict, clan_tag: str):
        '''Takes member results on a rade and clan tag of his clan as a separate parameter.
        
        Inserts member info into the table.'''

        collected_coins = member_info['achievements'][-2]['value'] #INDEX -2 IT`S NUMBER OF THE NECESSARY ACHIEVEMNT IN ACHIEVEMENTS LIST
        donated_coins = member_info['achievements'][-1]['value']
        self.insert(Tables.RadeMembers.value,
                    {"member_name": member_info['name'], "member_tag": member_info['tag'], "collected_coins" : collected_coins,
                    "donated_coins" : donated_coins, "saved_coins" : collected_coins - donated_coins, "clan_tag": clan_tag}, ignore = False,
                    expression = f"ON DUPLICATE KEY UPDATE collected_coins = VALUES(collected_coins), donated_coins = VALUES(donated_coins), saved_coins = VALUES(saved_coins)")                    
