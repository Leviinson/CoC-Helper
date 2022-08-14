CREATE DATABASE CoC_Helper;
USE CoC_Helper;
CREATE TABLE Chats (chat_id varchar(20), clan_tag varchar(10), CONSTRAINT pk_chats UNIQUE (clan_tag));
CREATE TABLE ClanMembers (member_tag varchar(12),  member_name varchar(20), member_role varchar(10), clan_tag varchar(10), CONSTRAINT pk_clanMembers UNIQUE (member_tag));
CREATE TABLE RadeMembers (member_name varchar(20), member_tag varchar(12), collected_coins INT, donated_coins INT, saved_coins INT, clan_tag varchar(12), CONSTRAINT pk_radeMembers UNIQUE (member_tag));
CREATE TABLE ChatAdmins (user_id BIGINT, user_name varchar(15), chat_id varchar(20), CONSTRAINT pk_chatMembers UNIQUE (user_id));
CREATE TABLE ClanWarLeague_memberlist (member_name varchar(15), member_tag varchar(12), townHallLevel varchar(2), clan_tag varchar(10));
CREATE TABLE ClanWarLeague_results (member_name varchar(15), member_tag varchar(12), stars TINYINT UNSIGNED DEFAULT 0, attacks TINYINT UNSIGNED DEFAULT 0, avg_score DECIMAL(4,3) DEFAULT 0, clan_tag varchar(12), CONSTRAINT pk_CWL_results UNIQUE (member_tag));
CREATE TABLE ChatUsers_nicknames(user_id BIGINT, chat_id varchar(20), user_nickname varchar(30), CONSTRAINT pk_userid UNIQUE (user_id));