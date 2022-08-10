import logging
import re

from typing import NamedTuple, Dict
from enum import Enum

from mysql.connector import connection, errors
from mysql.connector.cursor import MySQLCursorBuffered


from mysql_config import mysql_config_host
from mysql_config import mysql_config_user
from mysql_config import mysql_config_port
from mysql_config import mysql_config_password
from mysql_config import mysql_config_charset
from mysql_config import mysql_config_db_name


conn = connection.MySQLConnection(
                                  host = mysql_config_host,
                                  port = mysql_config_port,
                                  user = mysql_config_user,
                                  password = mysql_config_password,
                                  charset = mysql_config_charset
                                )


cursor = MySQLCursorBuffered(conn)

class Tables(Enum):


    Chats = 'Chats'
    ClanMembers = 'ClanMembers'
    RadeMembers = 'RadeMembers'
    ChatMembers = 'ChatMembers'
    CWL_members = 'ClanWarLeague_memberlist'


class SelectWhere(NamedTuple):


    columns_name1: str
    table_name: Tables
    columns_name2: str
    expression_sql: str #VALUES MUST BE REPLACED BY PLACEHOLDERS (!)
    args: tuple[str,]


class FetchAll(NamedTuple):


    columns: tuple[str] | str
    tables: tuple[str] | str


class DataBaseManipulation():


    def get_cursor(self):


        return MySQLCursorBuffered(conn)


    def get_connection(self):


        return conn


    def select(self, columns: str, table_name: str, expression = None):


        
            cursor = self.get_cursor()
            cursor.execute('USE CoC_Helper')
            SQL_raw = f'SELECT {columns} FROM {table_name}'
            match expression:

                case str():
                    cursor.execute(f'{SQL_raw} {expression}')

                case None:
                    cursor.execute(SQL_raw) 

            return cursor

    
    def select_distinct(self, columns: str, table_name: str, expression = None):


        
            cursor = self.get_cursor()
            cursor.execute('USE CoC_Helper')
            SQL_raw = f"SELECT DISTINCT {columns} FROM {table_name}"
            match expression:

                case str():
                    cursor.execute(f"{SQL_raw} {expression}")
                    
                case None:
                    cursor.execute(SQL_raw)

            return cursor
    
    def fetch_one(self, columns: tuple[str] | str, tables: tuple[str] | str, expression = None) -> None | tuple[str, str]:


            match expression:

                case None:

                    return self.select(columns, tables).fetchone()

                case _:

                    return self.select(columns, tables, expression).fetchone()        

    def fetch_all(self, columns: tuple[str] | str, tables: tuple[str] | str, expression = None):


            match expression:

                case None:

                    return self.select(columns, tables).fetchall()

                case _:
                    
                    return self.select(columns, tables, expression).fetchall()

    def insert(self, table: str, columns_value: Dict[str, str], ignore = False, expression = None):

        
            cursor = self.get_cursor()
            columns = ', '.join(columns_value.keys())
            values = tuple(columns_value.values())
            placeholder = re.findall(r'%s', '%s'*len(values))

            match ignore, expression:

                case True, None:

                    SQL = f"INSERT IGNORE INTO {table}({columns}) VALUES({', '.join(placeholder)})"

                case True, str():

                    SQL = f"INSERT IGNORE INTO {table}({columns}) VALUES({', '.join(placeholder)}) {expression}"

                case False, None:

                    SQL = f"INSERT INTO {table}({columns}) VALUES({', '.join(placeholder)})"

                case False, str():

                    SQL = f"INSERT INTO {table}({columns}) VALUES({', '.join(placeholder)}) {expression}"

            cursor.execute('USE CoC_Helper')
            cursor.execute(SQL, params = values)
            cursor.close()
            return conn.commit()


    def delete(self, table_name: str, expressions: str, ignore = bool):

        

            cursor = self.get_cursor()
            match ignore:

                case True:
                    cursor.execute(f'DELETE IGNORE FROM {table_name} {expressions}')

                case _:

                    cursor.execute(f'DELETE FROM {table_name} {expressions}')
            conn.commit()
            cursor.close()


def _init_DB():


    with open('mysql_create_tables.sql', 'r') as script:
        sql_script = script.read()

        
        cursor = MySQLCursorBuffered(conn)  
        results = cursor.execute(sql_script, multi = True)

        for cur in results:
            logging.info(f'{cur}')

        conn.commit()
        cursor.close()


def check_initDB():


  try:
    cursor.execute(f'SHOW TABLES FROM {mysql_config_db_name};')
  except errors.ProgrammingError:
    _init_DB()