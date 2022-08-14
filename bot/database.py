"""This module contains all database controls.

Classes:
    DataBaseManilupations
    Tables
    SelectWhere
    FetchAll
Funcs:
    _init_DB()
    _Check_init_DB()"""


import logging
import re

from type_hintings import SelectQuery

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


class DataBaseManipulations():


    def get_cursor(self):
        '''Returns `MySQLCursorBuffered` with current `mysql.connector.connection.MySQLConnection()` as a parameter.'''
        return MySQLCursorBuffered(conn)


    def get_connection(self):
        '''Returns current mysql.connector.connection.MySQLConnection()'''
        return conn


    def select(self, query: SelectQuery):
        '''Takes as a parameter `SelectQuery` class, executes select query and returns current cursor place.'''

        cursor = self.get_cursor()
        cursor.execute('USE CoC_Helper')
        SQL_raw = f'SELECT {query.columns_name} FROM {query.table_name}'
        match query.expression:

            case str():
                cursor.execute(f'{SQL_raw} {query.expression}', params = query.expression_values)

            case None:
                cursor.execute(SQL_raw) 

        return cursor

    
    def fetch_one(self, select_query: SelectQuery) -> tuple | None:
        '''Takes as a parameter `SelectQuery' class, returns next row of a query result set'''

        match select_query.expression:

            case None:
                return self.select(SelectQuery(select_query.columns_name,
                                               select_query.table_name
                                               )).fetchone()

            case _:
                return self.select(SelectQuery(select_query.columns_name,
                                               select_query.table_name,
                                               select_query.expression,
                                               select_query.expression_values
                                               )).fetchone()        

    def fetch_all(self, select_query: SelectQuery) -> list:
        '''Takes as a parameter `SelectQuery` class, returns all rows of a query result set.

        :parameter `select_query`: class `SelectQuery`'''

        match select_query.expression:

            case None:
                return self.select(SelectQuery(select_query.columns_name,
                                               select_query.table_name
                                               )).fetchall()

            case _: 
                return self.select(SelectQuery(
                                               select_query.columns_name,
                                               select_query.table_name,
                                               select_query.expression,
                                               select_query.expression_values
                                               )).fetchall()

    def insert(self, table: str, columns_value: dict, ignore: bool = False, expression: str = None):
        '''Takes table name, columns name and it values, bool value of mode `ignore`, expression as optional parameter;
        parses parameters into SQL query and executes it, confirms SQL connection commit, closes cursor.'''
        
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
        conn.commit()
        cursor.close()
        

    def delete(self, table_name: str, expressions: str, ignore: bool = False):
        '''Takes table name, expression, bool value of mode `ignore`;
        parses parameters into SQL query and execute it, confirms SQL connection commit, closes cursor.'''
        

        cursor = self.get_cursor()
        match ignore:

            case True:
                cursor.execute(f'DELETE IGNORE FROM {table_name} {expressions}')

            case _:

                cursor.execute(f'DELETE FROM {table_name} {expressions}')
        conn.commit()
        cursor.close()


def _init_DB():
    '''Executes mysql_create_tables.sql script, confirms SQL connection commit, closes cursor.'''

    with open('mysql_create_tables.sql', 'r') as script:
        sql_script = script.read()

        
        cursor = MySQLCursorBuffered(conn)  
        results = cursor.execute(sql_script, multi = True)

        for cur in results:
            logging.info(f'{cur}')

        conn.commit()
        cursor.close()


def check_initDB():
    '''Requests test SQL query to DB, initiate DB if raises exception ProgrammingError.'''

    try:
        cursor.execute(f'SHOW TABLES FROM {mysql_config_db_name};')
    except errors.ProgrammingError:
        _init_DB()
