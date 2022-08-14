from bot_config import bot
from handle_clan_data import DataBaseManipulations

async def check_user_status(chat_id: str, user_id: int):

    user_data = await bot.get_chat_member(chat_id, user_id)
    user_status = user_data['status']

    return user_status

class ChatDBManipulations(DataBaseManipulations):


    def _is_member_admin(self, user_id: int, chat_id: int) -> bool:


        cursor = self.get_cursor()
        cursor.execute(f'SELECT CASE WHEN EXISTS(SELECT user_name FROM ChatAdmins WHERE user_id = {user_id} AND chat_id = {chat_id}) THEN 1 ELSE 0 END AS IsEmpty')
        member_in_table_flag = cursor.fetchone()
        if member_in_table_flag:
            return True
            
        return False


    def set_new_admin(self, user_id: int, user_name: str, chat_id: int):
        self.insert('ChatAdmins', {'user_id' : user_id, 'user_name' : user_name, 'chat_id' : chat_id}, ignore = True)


    def remove_admin(self, user_id: int, chat_id: int):
        self.delete('ChatAdmins', f'WHERE user_id = {user_id} AND chat_id = {chat_id}', ignore = True)
