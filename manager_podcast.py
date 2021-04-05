#! /Library/Frameworks/Python.framework/Versions/3.8/bin/python3.8
# -*- coding: utf-8 -*-

import os
import requests
from datetime import datetime
import xmltodict
from dateutil.parser import parse
import psycopg2
import hashlib
import config
import xml.parsers.expat

class StatusCode:
    OK = 1
    ERROR = 2


class Response:

    def __init__(self, code, data=None):
        self.code = code
        self.data = data


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
}

CHECK_TIME = 86400  # 24 hours


def connect_database():
    DATABASE_URL = os.environ['DATABASE_URL']
    return psycopg2.connect(DATABASE_URL, sslmode='require')


def create_database():
    dataBase = connect_database()
    cursor = dataBase.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS account (
                   id SERIAL PRIMARY KEY,
                   login TEXT NOT NULL,
                   password TEXT NOT NULL,
                   token TEXT NOT NULL)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS podcast (
                   id SERIAL PRIMARY KEY,
                   title TEXT,
                   publisher TEXT,
                   description TEXT,
                   image_url TEXT,
                   rss_url TEXT,
                   last_check INTEGER DEFAULT 0)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS episode (
                   id SERIAL PRIMARY KEY,
                   podcast_id INTEGER REFERENCES podcast(id) ON DELETE CASCADE,
                   rss_guid TEXT,
                   position INTEGER,
                   title TEXT,
                   description TEXT,
                   audio_url TEXT,
                   pub_date_ms TEXT, duration INTEGER)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS user_podcast (
                   user_id INTEGER REFERENCES account(id) ON DELETE CASCADE,
                   podcast_id INTEGER REFERENCES podcast(id) ON DELETE CASCADE,
                   PRIMARY KEY (user_id, podcast_id))""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS user_episode (
                   user_id INTEGER REFERENCES account(id) ON DELETE CASCADE,
                   episode_id INTEGER REFERENCES episode(id) ON DELETE CASCADE,
                   readed INTEGER DEFAULT 0,
                   sync_watch INTEGER DEFAULT 0,
                   PRIMARY KEY (user_id, episode_id))""")
    dataBase.commit()
    dataBase.close()


def create_account(login, password):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    cursor.execute("""SELECT count(id)
                    FROM account""")
    if(cursor.fetchone()[0] <= int(os.environ['NUMBER_MAX_USER'])):
        cursor.execute("""SELECT id 
                        FROM account 
                        WHERE login = %s """, (login,))
        if cursor.fetchone() == None:
            hash_password = hashlib.sha256(password.encode()).hexdigest()
            token = hashlib.sha1((login+password).encode()).hexdigest()
            cursor.execute("""INSERT INTO account 
                            (login,password,token) 
                            VALUES (%s,%s,%s)""",
                           (login, hash_password, token))
            dataBase.commit()
            dataBase.close()
            return Response(StatusCode.OK, token)
        else:
            dataBase.close()
            return Response(StatusCode.ERROR, "user already exists")
    else:
        dataBase.close()
        return Response(StatusCode.ERROR, "Maximum number of users reached")


def user_id(token):
    user_id = None
    if token != None:
        dataBase = connect_database()
        cursor = dataBase.cursor()
        cursor.execute("""SELECT id 
                        FROM account 
                        WHERE token = %s """,
                       (token,))
        user = cursor.fetchone()
        if(user != None):
            user_id = user[0]
        dataBase.close()
    return user_id


def token(login, password):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    hash_password = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute(
        """SELECT token FROM account WHERE login = %s AND password = %s""", (login, hash_password))
    token = cursor.fetchone()
    if(token != None):
        return Response(StatusCode.OK, token[0])
    else:
        return Response(StatusCode.ERROR, "Error in login or password")


def list_episode_sync_watch(user_id, remove_readed):
    if(remove_readed != 'false'):
        reset_sync_watch(user_id)
    dataBase = connect_database()
    cursor = dataBase.cursor()
    cursor.execute("""SELECT 
                    podcast.id,
                    podcast.title,
                    podcast.image_url,
                    episode.id,
                    episode.title,
                    episode.position,
                    episode.audio_url,
                    episode.duration 
                    FROM user_podcast 
                    LEFT JOIN podcast ON podcast.id = user_podcast.podcast_id 
                    LEFT JOIN episode ON episode.podcast_id = podcast.id
                    LEFT JOIN user_episode ON user_episode.episode_id = episode.id
                    WHERE sync_watch = 1 AND user_podcast.user_id = %s 
                    ORDER BY podcast.title, episode.position""", (user_id,))
    podcasts = {}
    for episode in cursor.fetchall():
        if(episode[0] not in podcasts):
            podcasts[episode[0]] = {
                'id': episode[0],
                'name': episode[1],
                'image_url': episode[2],
                'episodes': []
            }
        episodes = podcasts[episode[0]]['episodes']
        episodes.append({
            'id': episode[3],
            'name': episode[4],
            'position': episode[5],
            'audio_url': episode[6],
            'duration': episode[7]
        })
    dataBase.close()
    return list(podcasts.values())


def readed_episodes(user_id, ids):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    for id in ids.split(","):
        cursor.execute("""UPDATE user_episode 
                        SET readed = 1 
                        WHERE user_id = %s AND episode_id = %s""", (user_id, id))
    dataBase.commit()
    dataBase.close()
    return {}


def not_readed_episodes(user_id, ids):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    for id in ids.split(","):
        cursor.execute("""UPDATE user_episode 
                        SET readed = 0 
                        WHERE user_id = %s AND episode_id = %s""", (user_id, id))
    dataBase.commit()
    dataBase.close()
    return {}


def sync_watch_episodes(user_id, ids):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    for id in ids.split(","):
        cursor.execute("""UPDATE user_episode 
                        SET sync_watch = 1
                        WHERE user_id = %s AND episode_id = %s""", (user_id, id))
    dataBase.commit()
    dataBase.close()
    return {}


def not_sync_watch_episodes(user_id, ids):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    for id in ids.split(","):
        cursor.execute("""UPDATE user_episode
                        SET sync_watch = 0 
                        WHERE user_id = %s AND episode_id = %s""", (user_id, id))
    dataBase.commit()
    dataBase.close()
    return {}


def reset_sync_watch(user_id):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    cursor.execute("""UPDATE user_episode 
                    SET sync_watch = 0 
                    WHERE readed = 1 AND user_id = %s""", (user_id,))
    dataBase.commit()
    return {}


def add_podcast_rss(user_id, rss_url):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    cursor.execute("""SELECT id
                    FROM podcast 
                    WHERE rss_url = %s""", (rss_url,))
    if cursor.fetchone() == None:
        response = requests.get(rss_url, headers=HEADERS)
        if(response.status_code == requests.codes['ok']):
            dataBase = connect_database()
            cursor = dataBase.cursor()
            cursor.execute("""SELECT id 
                            FROM podcast 
                            WHERE rss_url = %s """, (rss_url,))
            if cursor.fetchone() == None:
                cursor.execute("""INSERT INTO Podcast (rss_url) 
                                VALUES (%s)""", (rss_url,))
                dataBase.commit()
            check_new_episodes()
            state_url_ok = True
        else:
            state_url_ok = True
    else:
        state_url_ok = True

    if state_url_ok:
        cursor.execute("""SELECT id 
                        FROM podcast 
                        WHERE rss_url = %s""", (rss_url,))
        podcast_id = cursor.fetchone()[0]
        cursor.execute("""INSERT INTO user_podcast (user_id, podcast_id) 
                        VALUES(%s,%s) ON CONFLICT DO NOTHING""", (user_id, podcast_id))
        dataBase.commit()
        cursor.execute("""SELECT id FROM episode 
                       WHERE podcast_id = %s""", (podcast_id,))
        for episode in cursor.fetchall():
            cursor.execute("""INSERT INTO user_episode (user_id, episode_id) 
                            VALUES(%s,%s) ON CONFLICT DO NOTHING""", (user_id, episode[0]))
        dataBase.commit()
        dataBase.close()
        return Response(StatusCode.OK)
    else:
        return Response(StatusCode.ERROR)


def remove_podcast(user_id, podcast_id):
    dataBase = connect_database()
    cursor = dataBase.cursor()
    cursor.execute("""DELETE 
                    FROM user_podcast
                    WHERE user_id = %s AND podcast_id = %s""", (user_id, podcast_id))
    dataBase.commit()
    cursor.execute("""SELECT COUNT(user_id) 
                    FROM user_podcast 
                    WHERE podcast_id = %s""", (podcast_id,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""DELETE 
                        FROM podcast
                        WHERE id = %s""", (podcast_id,))
        dataBase.commit()
    dataBase.close()
    return {}


def list_podcast(user_id, no_episodes=False):
    dataBase = connect_database()
    cursor = dataBase.cursor()

    cursor.execute("""SELECT 
                   podcast.id,
                   podcast.title,
                   podcast.description,
                   podcast.publisher,
                   podcast.image_url 
                   FROM podcast 
                   LEFT JOIN user_podcast ON user_podcast.podcast_id = podcast.id 
                   WHERE user_podcast.user_id = %s 
                   ORDER BY podcast.title""", (user_id,))
    podcasts = []
    for podcast in cursor.fetchall():
        episodes = []
        if not no_episodes:
            cursor.execute("""SELECT 
                           episode.id,
                           episode.title,
                           episode.description,
                           episode.position,
                           episode.pub_date_ms,
                           episode.duration,
                           episode.audio_url,
                           user_episode.readed,
                           user_episode.sync_watch 
                           FROM user_episode
                           LEFT JOIN episode ON episode.id = user_episode.episode_id   
                           WHERE episode.podcast_id = %s AND 
                           user_episode.user_id = %s 
                           ORDER BY episode.position""", (podcast[0], user_id))
            for episode in cursor.fetchall():
                episodes.append({
                    'id': episode[0],
                    'title': episode[1],
                    'description': episode[2],
                    'position': episode[3],
                    'pub_date_ms': episode[4],
                    'duration': episode[5],
                    'audio_url': episode[6],
                    'readed': episode[7],
                    'sync_watch': episode[8],
                })
        podcasts.append({
            'id': podcast[0],
            'title': podcast[1],
            'description': podcast[2],
            'publisher': podcast[3],
            'image_url': podcast[4],
            'episodes': episodes
        })
    dataBase.close()
    return podcasts


def podcast(user_id, podcast_id):
    episodes = []
    dataBase = connect_database()
    cursor = dataBase.cursor()
    cursor.execute("""SELECT 
                   episode.id,
                   episode.title,
                   episode.description,
                   episode.position,
                   episode.pub_date_ms,
                   episode.duration,
                   episode.audio_url,
                   user_episode.readed,
                   user_episode.sync_watch 
                   FROM episode 
                   LEFT JOIN user_episode ON user_episode.episode_id = episode.id 
                   WHERE user_episode.user_id=%s AND episode.podcast_id=%s ORDER BY Episode.position DESC""", (user_id, podcast_id,))
    for episode in cursor.fetchall():
        episodes.append({
            'id': episode[0],
            'title': episode[1],
            'description': episode[2],
            'position': episode[3],
            'pub_date_ms': episode[4],
            'duration': episode[5],
            'audio_url': episode[6],
            'readed': episode[7],
            'sync_watch': episode[8]
        })
    cursor.execute("""SELECT
                   podcast.id,
                   podcast.title,
                   podcast.description,
                   podcast.publisher,
                   podcast.image_url
                   FROM podcast WHERE podcast.id=%s""", (podcast_id,))
    podcast = cursor.fetchone()
    dataBase.close()
    return {
        'id': podcast[0],
        'title': podcast[1],
        'description': podcast[2],
        'publisher': podcast[3],
        'image': podcast[4],
        'episodes': episodes
    }


def check_new_episodes(delta=CHECK_TIME):
    if config.ACTIVE_LOG:
        print("Check new episodes :"+str(delta))
    dataBase = connect_database()
    cursor = dataBase.cursor()
    cursor.execute("""SELECT 
                    podcast.id,
                    podcast.rss_url,
                    podcast.last_check
                    FROM podcast""")
    for podcast in cursor.fetchall():
        now = datetime.now()
        timestamp = datetime.timestamp(now)
        someday = podcast[2]
        diff = int(timestamp) - int(someday)
        if(diff >= delta):
            if config.ACTIVE_LOG:
                print("Check new episodes podcast rss  "+podcast[1])
            parse_rss(dataBase, podcast[0], podcast[1])
    dataBase.close()


def parse_rss(dataBase, podcast_id, rss_url):
    response = requests.get(rss_url, headers=HEADERS)
    if(response.status_code == requests.codes['ok']):
        try:
            podcast = xmltodict.parse(response.content)['rss']['channel']
            cursor = dataBase.cursor()
            now = datetime.now()
            timestamp = datetime.timestamp(now)
            description = None
            if('itunes:summary' in podcast.keys()):
                description = podcast['itunes:summary']
            elif('description' in podcast.keys()):
                description = podcast['description']

            image = None
            if('itunes:image' in podcast.keys()):
                image = podcast["itunes:image"]['@href']
            elif('image' in podcast.keys()):
                image_xml = podcast['image']
                if("url" in image_xml.keys()):
                    image = image_xml["url"]
            author = None
            if('itunes:author' in podcast.keys()):
                author = podcast["itunes:author"]
            if(type(author) is list):
                author = author[0]
            cursor.execute("""UPDATE podcast SET 
                            title = %s,
                            description = %s,
                            publisher = %s,
                            image_url = %s,
                            last_check = %s 
                            WHERE id = %s""", (podcast['title'], description, author, image, int(timestamp), podcast_id))

            episodes = podcast['item']
            list_rss_guid = None
            if(isinstance(episodes, dict)):
                list_rss_guid = '\'' + \
                    add_episode(dataBase, podcast_id, episodes, 1)+'\''
            else:
                position = len(episodes)
                for episode in episodes:
                    rss_guid = add_episode(dataBase, podcast_id, episode, position)
                    if(rss_guid is not None):
                        if(position == len(episodes)):
                            list_rss_guid = '\''+rss_guid+'\''
                        else:
                            list_rss_guid = list_rss_guid+',\''+rss_guid+'\''
                    position -= 1
            if(list_rss_guid is not None):
                cursor.execute("""DELETE FROM episode 
                                WHERE ( rss_guid NOT IN ("""+list_rss_guid+""") 
                                OR rss_guid IS NULL ) 
                                AND podcast_id = """+str(podcast_id))
            dataBase.commit()
        except (xmltodict.ParsingInterrupted, xml.parsers.expat.ExpatError):
            print("parsing error "+rss_url)

def add_episode(dataBase, podcast_id, episode, position):
    cursor = dataBase.cursor()
    description = None
    if('itunes:summary' in episode.keys()):
        description = episode['itunes:summary']
    elif('description' in episode.keys()):
        description = episode['description']

    pub_date_ms = 0
    if('pubDate' in episode.keys()):
        pub_date_ms = datetime.timestamp(
            parse(episode["pubDate"], ignoretz=True))*1000
    duration = 0
    if('itunes:duration' in episode.keys()):
        arrayDuration = episode["itunes:duration"].split(":")
        if(len(arrayDuration) == 3):
            duration = int(
                arrayDuration[0])*3600+int(arrayDuration[1])*60+int(arrayDuration[2])
        elif(len(arrayDuration) == 2):
            duration = int(
                arrayDuration[0])*60+int(arrayDuration[1])
        else:
            duration = int(arrayDuration[0])
    rss_guid = None
    if('enclosure' in episode.keys()):
        if('guid' in episode.keys()):
            if(isinstance(episode['guid'], dict)):
                rss_guid = episode['guid']['#text']
            else:
                rss_guid = episode['guid']
        else:
            rss_guid = episode['enclosure']['@url']
        if exist_episode_rss_guid(dataBase, podcast_id, rss_guid):
            cursor.execute("""UPDATE episode SET 
                            title = %s,
                            position = %s,
                            description = %s,
                            audio_url = %s,
                            pub_date_ms = %s,
                            duration = %s 
                            WHERE podcast_id = %s AND rss_guid = %s""",
                           (episode['title'], position, description, episode['enclosure']['@url'], int(pub_date_ms), duration, podcast_id, rss_guid))
        else:
            if exist_episode_rss_title(dataBase, podcast_id, episode['title']):
                cursor.execute("""UPDATE episode SET
                                position = %s,
                                description = %s,
                                audio_url = %s,
                                pub_date_ms = %s,
                                duration = %s,
                                rss_guid = %s
                                WHERE podcast_id = %s AND title = %s""",
                               (position, description, episode['enclosure']['@url'], int(pub_date_ms), duration, rss_guid, podcast_id, episode['title']))
            else:
                cursor.execute("""INSERT INTO episode 
                                (podcast_id,position,title,description,audio_url,pub_date_ms,duration,rss_guid)
                                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                               (podcast_id, position, episode['title'], description, episode['enclosure']['@url'], int(pub_date_ms), duration, rss_guid))
        dataBase.commit()

        cursor.execute("""SELECT id 
                        FROM episode 
                        WHERE audio_url = %s""", (episode['enclosure']['@url'],))
        episode_id = cursor.fetchone()[0]
        cursor.execute("""SELECT user_id FROM user_podcast WHERE podcast_id=%s""", (podcast_id,))
        for user_id in cursor.fetchall():
            cursor.execute("""INSERT INTO user_episode (user_id, episode_id) 
                            VALUES(%s,%s) ON CONFLICT DO NOTHING""", (user_id, episode_id))        
        dataBase.commit()
    return rss_guid


def exist_episode_rss_guid(dataBase, id, rss_guid):
    cursor = dataBase.cursor()
    cursor.execute("""SELECT id 
                    FROM episode 
                    WHERE podcast_id = %s AND rss_guid = %s """, (id, rss_guid))
    return cursor.fetchone() != None


def exist_episode_rss_title(dataBase, id, title):
    cursor = dataBase.cursor()
    cursor.execute("""SELECT id 
                    FROM episode 
                    WHERE podcast_id = %s AND title = %s """, (id, title))
    return cursor.fetchone() != None
