from os.path import dirname
import datetime

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import getLogger
from mycroft.util.log import LOG
# from mycroft.skills.context import adds_context, removes_context
'''
also use self.remove_context(s, x)
also use self.set_context(s,x)
Note: the @adds_context / @removes_context can't be used with the Remove / set context options
'''
from mycroft.util.parse import extract_number
from mycroft.audio import wait_while_speaking

import pafy
import pychromecast
from pychromecast.controllers.youtube import YouTubeController

import urllib.error
import urllib.parse
import urllib.request

import requests
import re
import time
import json
import random

_author__ = 'PCWii'
this_release = "20190519"

LOGGER = getLogger(__name__)


class KodiSkill(MycroftSkill):
    """
    A Skill to control playback on a Kodi instance via the json-rpc interface.
    """
    def __init__(self):
        super(KodiSkill, self).__init__(name="KodiSkill")
        self.kodi_path = ""
        self.youtube_id = []
        self.youtube_search = ""
        self.kodi_payload = ""
        self.cv_payload = ""
        self.list_payload = ""
        self.json_header = {'content-type': 'application/json'}
        self.json_response = ""
        self.cv_response = ""
        self.list_response = ""
        self._is_setup = False
        self.playing_status = False
        self.notifier_bool = False
        self.movie_list = []
        self.movie_index = 0
        self.cv_request = False
        self.use_cv = False
        self.start_time = ""
        self.end_time = ""
        self.music_dict = []

    def initialize(self):
        self.load_data_files(dirname(__file__))
        LOG.info("Running Kodi-Skill Version: " + str(this_release))
        #  Check and then monitor for credential changes
        #self.settings.set_changed_callback(self.on_websettings_changed)
        self.settings_change_callback = self.on_websettings_changed
        self.on_websettings_changed()
        self.add_event('recognizer_loop:wakeword', self.handle_listen)
        self.add_event('recognizer_loop:utterance', self.handle_utterance)
        self.add_event('speak', self.handle_speak)

        # eg. stop the movie
        stop_intent = IntentBuilder("StopIntent"). \
            require("StopKeyword").one_of("FilmKeyword", "KodiKeyword", "YoutubeKeyword", "MusicKeyword").build()
        self.register_intent(stop_intent, self.handle_stop_intent)

        # eg. pause the movie
        pause_intent = IntentBuilder("PauseIntent"). \
            require("PauseKeyword").one_of("FilmKeyword", "KodiKeyword", "YoutubeKeyword", "MusicKeyword").build()
        self.register_intent(pause_intent, self.handle_pause_intent)

        # eg. resume the movie
        resume_intent = IntentBuilder("ResumeIntent"). \
            require("ResumeKeyword").one_of("FilmKeyword", "KodiKeyword", "YoutubeKeyword", "MusicKeyword").build()
        self.register_intent(resume_intent, self.handle_resume_intent)

        # eg. turn kodi notifications on
        notification_on_intent = IntentBuilder("NotifyOnIntent"). \
            require("NotificationKeyword").require("OnKeyword"). \
            require("KodiKeyword").build()
        self.register_intent(notification_on_intent, self.handle_notification_on_intent)

        # eg. turn kodi notifications off
        notification_off_intent = IntentBuilder("NotifyOffIntent"). \
            require("NotificationKeyword").require("OffKeyword"). \
            require("KodiKeyword").build()
        self.register_intent(notification_off_intent, self.handle_notification_off_intent)

    def on_websettings_changed(self):  # called when updating mycroft home page
        # if not self._is_setup:
        LOG.info('Websettings have changed! Updating path data')
        kodi_ip = self.settings.get("kodi_ip", "192.168.0.32")
        kodi_port = self.settings.get("kodi_port", "8080")
        kodi_user = self.settings.get("kodi_user", "")
        kodi_pass = self.settings.get("kodi_pass", "")
        try:
            if kodi_ip and kodi_port:
                kodi_ip = self.settings["kodi_ip"  ]
                kodi_port = self.settings["kodi_port"]
                kodi_user = self.settings["kodi_user"]
                kodi_pass = self.settings["kodi_pass"]
                self.kodi_path = "http://" + kodi_user + ":" + kodi_pass + "@" + kodi_ip + ":" + str(kodi_port) + \
                                 "/jsonrpc"
                LOG.info(self.kodi_path)
                self._is_setup = True
        except Exception as e:
            LOG.error(e)

    def numeric_replace(self, in_words=""):
        word_list = in_words.split()
        return_list = []
        for each_word in word_list:
            try:
                new_word = w2n.word_to_num(each_word)
            except Exception as e:
                # LOG.info(e)
                new_word = each_word
            return_list.append(new_word)
            return_string = ' '.join(str(e) for e in return_list)
        return return_string

    # find the movies in the library that match the optional search criteria
    def find_movies_with_filter(self, title=""):
        title = self.numeric_replace(title)
        found_list = []  # this is a dict
        movie_list = self.list_all_movies()
        title_list = title.replace("-", "").lower().split()
        for each_movie in movie_list:
            movie_name = each_movie["label"].replace("-", "")
            movie_name = self.numeric_replace(movie_name)
            LOG.info(movie_name)
            if all(words in movie_name.lower() for words in title_list):
                LOG.info("Found " + movie_name + " : " + "MovieID: " + str(each_movie["movieid"]))
                info = {
                    "label": each_movie['label'],
                    "movieid": each_movie['movieid']
                }
                found_list.append(info)
        temp_list = []  # this is a dict
        for each_movie in found_list:
            movie_title = str(each_movie['label'])
            info = {
                "label": each_movie['label'],
                "movieid": each_movie['movieid']
            }
            if movie_title not in str(temp_list):
                temp_list.append(info)
            else:
                if len(each_movie['label']) == len(movie_title):
                    LOG.info('found duplicate')
                else:
                    temp_list.append(info)
        found_list = temp_list
        return found_list  # returns a dictionary of matched movies

    # check if kodi is currently playing, required for some functions
    def is_kodi_playing(self):
        method = "Player.GetActivePlayers"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            parse_response = json.loads(kodi_response.text)["result"]
            if not parse_response:
                self.playing_status = False
            else:
                self.playing_status = True
        except Exception as e:
            LOG.error(e)
        LOG.info("Is Kodi Playing?...", str(self.playing_status))
        return self.playing_status

    def list_all_movies(self):
        method = "VideoLibrary.GetMovies"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1,
            "params": {
                "properties": [
                ],
            }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            movie_list = json.loads(kodi_response.text)["result"]["movies"]
            return movie_list
        except Exception as e:
            LOG.info(e)
            return "NONE"

# Added Music Functions here 20200514 #
    # add the songid to the active playlist songid is an integer
    def add_song_playlist(self, songid):
        method = "Playlist.Add"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {
                "playlistid": 1,
                "item": {
                    "songid": songid
                }
            }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            #LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    def list_all_music(self):
        LOG.info('Refreshing Music List!...')
        method = "AudioLibrary.GetSongs"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1,
            "params": {
                "properties": [
                    "artist",
                    "duration",
                    "album",
                    "track"
                ],
            }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            ret_music_list = json.loads(kodi_response.text)["result"]["songs"]
            return ret_music_list
        except Exception as e:
            LOG.info(e)
            return "NONE"

    def search_music_item(self, search_item, exact_match=False, category="label"):
        # category options: label, artist, album
        search_item = self.numeric_replace(search_item)
        found_list = []  # this is a dict of all the items found that match the search
        if len(self.music_dict) < 1:
            self.music_dict = self.list_all_music()
        #LOG.info("Music List: " + str(self.music_dict))
        search_words = search_item.replace("-", "").lower().split()
        search_length = len(search_words)
        # check each movie in the list for strings that match all the words in the search
        self.start_time = datetime.datetime.now()
        for each_song in self.music_dict:  # check each song in the list for the one we are looking for
            if category == "artist":  # artist is an array element so need to specify the index
                item_name = each_song[category][0].replace("-", "")
            else:
                #LOG.info('Not Filtered by Artist: ' + str(each_song))
                item_name = each_song[category].replace("-", "")
            if len(item_name) > 0:
                # print(item_name.lower())
                item_name = self.numeric_replace(item_name)
                if all(words in item_name.lower() for words in search_words):
                    found_length = len(each_song['label'].split())
                    if exact_match:
                        if found_length == search_length:
                            # print("Found Item: " + item_name + " : " + "SongID: " + str(each_song["songid"]))
                            info = {
                                "label": each_song['label'],
                                "songid": each_song['songid'],
                                "artist": each_song['artist']
                            }
                            found_list.append(info)
                    else:
                        # print("Found Item: " + item_name + " : " + "SongID: " + str(each_song["songid"]))
                        info = {
                            "label": each_song['label'],
                            "songid": each_song['songid'],
                            "artist": each_song['artist']
                        }
                        found_list.append(info)
        # remove duplicates
        temp_list = []  # this is a dict
        for each_song in found_list:
            song_title = str(each_song['label'])
            info = {
                "label": each_song['label'],
                "songid": each_song['songid'],
                "artist": each_song['artist']
            }
            if song_title not in str(temp_list):
                temp_list.append(info)
            else:
                if len(each_song['label']) == len(song_title):
                    LOG.info('found duplicate')
                else:
                    temp_list.append(info)
                found_list = temp_list
        self.end_time = datetime.datetime.now()
        delta_time_s = self.end_time - self.start_time
        LOG.info("Searching and preparing the requested music list took: " + str(delta_time_s) + ", seconds")
        return found_list  # returns a dictionary of matched movies

    def search_music_library(self, search_string, category="any"):
        found_list = []  # this is a dict that will contain all the items found in the library
        LOG.info("searching the music library for: " + search_string + ", " + category)
        if category == "any":
            found_list = self.search_music_item(search_string, category="label")
            if len(found_list) > 0:
                return found_list
            LOG.info("Label: " + search_string + ", Not Found!")
            found_list = self.search_music_item(search_string, category="artist")
            if len(found_list) > 0:
                return found_list
            LOG.info("Artist: " + search_string + ", Not Found!")
            found_list = self.search_music_item(search_string, category="album")
            if len(found_list) == 0:
                LOG.info("Album: " + search_string + ", Not Found!")
                return
        else:
            found_list = self.search_music_item(search_string, category=str(category))
        if len(found_list) > 0:
            return found_list

    def queue_and_play_music(self, music_playlist):
        self.clear_playlist()
        self.music_dict = []
        for each_song in music_playlist:
            LOG.info("Adding to Kodi Playlist: " + str(each_song["label"]) +", ID: "+ str(each_song["songid"]))
            self.add_song_playlist(each_song["songid"])
        self.play_normal()

    def parse_music_utterance(self, message):
        # returns what was spoken in the utterance
        return_type = "any"
        str_request = str(message.data.get('utterance'))
        LOG.info("Parse Music Received: " + str_request)
        primary_regex = r"((?<=album) (?P<album>.*$))|((?<=artist) (?P<artist>.*$))|((?<=song) (?P<label>.*$))"
        if str_request.find('some') != -1:
            secondary_regex = r"((?<=some) (?P<any>.*$))"
        else:
            secondary_regex = r"((?<=play) (?P<any>.*$))"
        key_found = re.search(primary_regex, str_request)
        if key_found:
            LOG.info("Primary Regex Key Found")
            if key_found.group("label"):
                LOG.info("found label")
                return_item = key_found.group("label")
                return_type = "label"
            elif key_found.group("artist"):
                LOG.info("found artist")
                return_item = key_found.group("artist")
                return_type = "artist"
            elif key_found.group("album"):
                LOG.info("found album")
                return_item = key_found.group("album")
                return_type = "album"
        else:
            LOG.info("Primary Regex Key Not Found")
            key_found = re.search(secondary_regex, str_request)
            if key_found.group("any"):
                LOG.info("Secondary Regex Key Found")
                return_item = key_found.group("any")
                return_type = "any"
            else:
                LOG.info("Secondary Regex Key Not Found")
                return_item = "none"
                return_type = "none"
        # Returns the item that was requested and the type of the requested item ie. artist, album, label
        return return_item, return_type

# End of Added Music Functions here 20200514 #

    # activate the kodi root menu system
    def show_root(self):
        method = "GUI.ActivateWindow"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "window": "videos",
                "parameters": [
                    "library://video/"
                ]
            },
            "id": "1"
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    # clear any active playlists
    def clear_playlist(self):
        method = "Playlist.Clear"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1,
            "params": {
                "playlistid": 1
            }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    # play the movie playlist with cinemavision addon, assumes the playlist is already populated
    def play_cinemavision(self):
        method = "Addons.ExecuteAddon"
        self.cv_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "addonid": "script.cinemavision",
                "params": [
                    "experience", "nodialog"
                ]
            },
            "id": 1
        }
        try:
            self.cv_response = requests.post(self.kodi_path, data=json.dumps(self.cv_payload),
                                             headers=self.json_header)
            LOG.info(self.cv_response.text)
        except Exception as e:
            LOG.error(e)

    # play the movie playlist normally without any addons, assumes there are movies in the playlist
    def play_normal(self):
        method = "player.open"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "item": {
                    "playlistid": 1
                }
            },
            "id": 1
        }
        try:
            self.json_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload),
                                               headers=self.json_header)
            LOG.info(self.json_response.text)
        except Exception as e:
            LOG.error(e)

    # add the movieid to the active playlist movieid is an integer
    def add_movie_playlist(self, movieid):
        method = "Playlist.Add"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {
                "playlistid": 1,
                "item": {
                    "movieid": movieid
                }
            }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)


    # pause any playing movie not youtube
    def pause_all(self):
        method = "Player.PlayPause"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "playerid": 1,
                "play": False},
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    # resume any paused movies not youtube
    def resume_all(self):
        method = "Player.PlayPause"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "playerid": 1,
                "play": True},
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    # check if the youtube addon exists
    def check_youtube_present(self):
        method = "Addons.GetAddons"
        addon_video = "xbmc.addon.video"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": "1",
            "params": {
                "type": addon_video
            }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
        except Exception as e:
            LOG.info(e)
            return False
        if "plugin.video.youtube" in kodi_response.text:
            return True
        else:
            return False

    # check if the cinemavision addon exists
    def check_cinemavision_present(self):
        self.list_payload = {
            "jsonrpc": "2.0",
            "method": "Addons.GetAddons",
            "params": {
                "type": "xbmc.addon.executable"
            },
            "id": "1"
        }
        try:
            self.list_response = requests.post(self.kodi_path, data=json.dumps(self.list_payload), headers=self.json_header)
            LOG.info(self.list_response.text)
        except Exception as e:
            LOG.info(e)
            return False
        if "script.cinemavision" in self.list_response.text:
            return True
        else:
            return False

    # use regex to find any movie names found in the utterance
    def movie_regex(self, message):
        film_regex = r"((movie|film) (?P<Film1>.*))| ((movie|film) (?P<Film2>.*)(with|using) (cinemavision))"
        utt_str = message
        film_matches = re.finditer(film_regex, utt_str, re.MULTILINE | re.DOTALL)
        for film_match_num, film_match in enumerate(film_matches):
            group_id = "Film1"
            my_movie = "{group}".format(group=film_match.group(group_id))
            self.cv_request = False
            if my_movie == "None":
                group_id = "Film2"
                my_movie = "{group}".format(group=film_match.group(group_id))
                self.cv_request = True
        LOG.info(my_movie)
        my_movie = re.sub('\W', ' ', my_movie)
        my_movie = re.sub(' +', ' ', my_movie)
        return my_movie.strip()

    # check the cursor control utterance for repeat commands
    def repeat_regex(self, message):
        value = extract_number(message)
        if value:
            repeat_value = value
        elif "once" in message:
            repeat_value = 1
        elif "twice" in message:
            repeat_value = 2
        else:
            repeat_value = 1
        return repeat_value

    # send a URI to Chromecast and play
    def cast_link(self, source_link, device_ip):
        cast = pychromecast.Chromecast(device_ip)
        cast.wait()
        mc = cast.media_controller
        LOG.info(source_link)
        mc.play_media(source_link, 'video/mp4')
        time.sleep(7) #wait for CC to be ready to play
        mc.block_until_active()
        mc.play()
        #mc.stop()

    # send a youtube videoID and play
    def cast_youtube(self, video_id, device_ip):
        cast = pychromecast.Chromecast(device_ip)
        cast.wait()
        yt = YouTubeController()
        cast.register_handler(yt)
        yt.play_video(video_id)

    # return the id of a movie from the kodi library based on its name
    def get_kodi_movie_id(self, movie_name):
        found_list = self.find_movies_with_filter(movie_name)
        my_id = found_list[0]["movieid"]
        return my_id

    # returns the full URI of a movie from the kodi library
    def get_kodi_movie_path(self, movie_name):
        movie_id = self.get_kodi_movie_id(movie_name)
        method = "VideoLibrary.GetMovieDetails"
        kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1,
            "params": {"movieid": movie_id,
                       "properties": [
                           # "art",
                           # "cast",
                           # "dateadded",
                           # "director",
                           # "fanart",
                           "file",
                           # "genre",
                           # "imdbnumber",
                           # "lastplayed",
                           # "mpaa",
                           # "originaltitle",
                           # "playcount",
                           # "plot",
                           # "plotoutline",
                           # "premiered",
                           # "rating",
                           # "runtime",
                           # "resume",
                           # "setid",
                           # "sorttitle",
                           # "streamdetails",
                           # "studio",
                           # "tagline",
                           # "thumbnail",
                           # "title",
                           # "trailer",
                           # "userrating",
                           # "votes",
                           # "writer"
                       ],
                       }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            movie_path = json.loads(kodi_response.text)["result"]["moviedetails"]["file"]
            base_path = 'http://' + self.kodi_ip + ':' + self.kodi_port + '/vfs/'
            url_path = base_path + urllib.parse.quote(movie_path, safe='')
            LOG.info('Found Kodi Movie Path ' + url_path)
            return url_path
        except Exception as e:
            LOG.info(e)
            return "NONE"

    # play the supplied video_id with the youtube addon
    def play_youtube_video(self, video_id):
        LOG.info('play youtube ID: ' + str(video_id))
        method = "Player.Open"
        # Playlist links are longer than individual links
        # individual links are 11 characters long
        if len(video_id) > 11:
            yt_link = "plugin://plugin.video.youtube/play/?playlist_id=" + video_id + "&play=1&order=shuffle"
        else:
            yt_link = "plugin://plugin.video.youtube/play/?video_id=" + video_id
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "params": {
                "item": {
                    "file": yt_link
                }
            },
            "method": method,
            "id": "libPlayer"
        }
        LOG.info(yt_link)
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    def get_yt_audio_url(self, youtube_url):
        base_url = 'https://www.youtube.com'
        abs_url = base_url + youtube_url
        LOG.debug('pafy processing: ' + abs_url)
        streams = pafy.new(abs_url)
        LOG.debug('audiostreams found: ' + str(streams.audiostreams));
        bestaudio = streams.getbestaudio()
        LOG.debug('audiostream selected: ' + str(bestaudio));
        return bestaudio.url

    # stop any playing movie not youtube
    def stop_all(self):
        method = "Player.Stop"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "playerid": 1
            },
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)



    # extract the requested youtube item from the utterance
    def youtube_query_regex(self, req_string):
        return_list = []
        pri_regex = re.search(r'play (?P<item1>.*) from youtube', req_string)
        sec_regex = re.search(r'play some (?P<item1>.*) from youtube|play the (?P<item2>.*)from youtube', req_string)
        if pri_regex:
            if sec_regex:  # more items requested
                temp_results = sec_regex
            else:  # single item requested
                temp_results = pri_regex
        if temp_results:
            item_result = temp_results.group(temp_results.lastgroup)
            return_list = item_result
            LOG.info(return_list)
            return return_list

    # extract the youtube links from the provided search_list
    def get_youtube_links(self, search_list):
        # search_text = str(search_list[0])
        search_text = str(search_list)
        query = urllib.parse.quote(search_text)
        url = "https://www.youtube.com/results?search_query=" + query
        response = urllib.request.urlopen(url)
        html = response.read()
        # Get all video links from page
        temp_links = []
        all_video_links = re.findall(r'href=\"\/watch\?v=(.{11})', html.decode())
        for each_video in all_video_links:
            if each_video not in temp_links:
                temp_links.append(each_video)
        video_links = temp_links
        # Get all playlist links from page
        temp_links = []
        all_playlist_results = re.findall(r'href=\"\/playlist\?list\=(.{34})', html.decode())
        sep = '"'
        for each_playlist in all_playlist_results:
            if each_playlist not in temp_links:
                cleaned_pl = each_playlist.split(sep, 1)[0]  # clean up dirty playlists
                temp_links.append(cleaned_pl)
        playlist_links = temp_links
        yt_links = []
        if video_links:
            yt_links.append(video_links[0])
            LOG.info("Found Single Links: " + str(video_links))
        if playlist_links:
            yt_links.append(playlist_links[0])
            LOG.info("Found Playlist Links: " + str(playlist_links))
        return yt_links

    # push a message to the kodi notification popup
    def post_kodi_notification(self, message):
        method = "GUI.ShowNotification"
        display_timeout = 5000
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "title": "Kelsey.AI",
                "message": str(message),
                "displaytime": display_timeout,
            },
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    # listening event used for kodi notifications
    def handle_listen(self, message):
        voice_payload = "Listening"
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    # utterance event used for kodi notifications
    def handle_utterance(self, message):
        utterance = message.data.get('utterances')
        voice_payload = utterance
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    # mycroft speaking event used for kodi notificatons
    def handle_speak(self, message):
        voice_payload = message.data.get('utterance')
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    # Primary Play Movie request - now handles music and films with optionally
    @intent_handler(IntentBuilder('PlayLocalIntent').require("AskKeyword").require("KodiKeyword").
                    require("PlayKeyword").optionally("FilmKeyword").
                    optionally("CinemaVisionKeyword").optionally('RandomKeyword').build())
    def handle_play_local_intent(self, message):
        LOG.info("Called Play Film Intent")
        if message.data.get("FilmKeyword"):
            LOG.info("Continue with Play Film intent")
            self.continue_play_film_intent(message)
        else:
            # Play Music Added here
            LOG.info("Continue with Play Music intent")
            self.continue_play_music_intent(message)

    def continue_play_music_intent(self, message):
        play_request = self.parse_music_utterance(message)  # get the requested Music Item
        LOG.info("Parse Routine Returned: "+str(play_request))
        music_playlist = self.search_music_library(play_request[0], category=play_request[1])  # search for the item in the library
        self.speak_dialog('play.music', data={"title": str(play_request[0]), "category": str(play_request[1])},
                          expect_response=False)
        self.queue_and_play_music(music_playlist)

    def continue_play_film_intent(self, message):
        if message.data.get("CinemaVisionKeyword"):
            self.cv_request = True
        else:
            self.cv_request = False
        if message.data.get("RandomKeyword"):
            self.handle_random_movie_select_intent()
        else:
            # Proceed normally
            movie_name = self.movie_regex(message.data.get('utterance'))
            try:
                LOG.info("movie: " + movie_name)
                self.speak_dialog("please.wait")
                results = self.find_movies_with_filter(movie_name)
                self.movie_list = results
                self.movie_index = 0
                LOG.info("possible movies are: " + str(results))
                ######
                if len(results) == 1:
                    self.play_film(results[0]['movieid'])
                elif len(results):
                    self.set_context('NavigateContextKeyword', 'NavigateContext')
                    self.speak_dialog('multiple.results', data={"result": str(len(results))}, expect_response=True)
                else:
                    self.speak_dialog('no.results', data={"result": movie_name}, expect_response=False)
                #####
            except Exception as e:
                LOG.info('an error was detected')
                LOG.error(e)
                self.on_websettings_changed()

    # stop film was requested in the utterance
    def handle_stop_intent(self, message):
        try:
            self.stop_all()
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    # pause film was requested in the utterance
    def handle_pause_intent(self, message):
        try:
            self.pause_all()
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    # resume the film was requested in the utterance
    def handle_resume_intent(self, message):
        try:
            self.resume_all()
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    # turn notifications on requested in the utterance
    def handle_notification_on_intent(self, message):
        self.notifier_bool = True
        self.speak_dialog("notification", data={"result": "On"})

    # turn notifications off requested in the utterance
    def handle_notification_off_intent(self, message):
        self.notifier_bool = False
        self.speak_dialog("notification", data={"result": "Off"})

    # move cursor utterance processing
    @intent_handler(IntentBuilder('MoveCursorIntent').require('MoveKeyword').require('CursorKeyword').
                    one_of('UpKeyword', 'DownKeyword', 'LeftKeyword', 'RightKeyword', 'EnterKeyword',
                           'SelectKeyword', 'BackKeyword').build())
    def handle_move_cursor_intent(self, message):  # a request was made to move the kodi cursor
        self.set_context('MoveKeyword', 'move')  # in future the user does not have to say the move keyword
        self.set_context('CursorKeyword', 'cursor')  # in future the user does not have to say the cursor keyword
        if "UpKeyword" in message.data:
            direction_kw = "Up"  # these english words are required by the kodi api
        if "DownKeyword" in message.data:
            direction_kw = "Down"  # these english words are required by the kodi api
        if "LeftKeyword" in message.data:
            direction_kw = "Left"  # these english words are required by the kodi api
        if "RightKeyword" in message.data:
            direction_kw = "Right"  # these english words are required by the kodi api
        if "EnterKeyword" in message.data:
            direction_kw = "Enter"  # these english words are required by the kodi api
        if "SelectKeyword" in message.data:
            direction_kw = "Select"  # these english words are required by the kodi api
        if "BackKeyword" in message.data:
            direction_kw = "Back"  # these english words are required by the kodi api
        repeat_count = self.repeat_regex(message.data.get('utterance'))
        LOG.info('utterance: ' + str(message.data.get('utterance')))
        LOG.info('repeat_count: ' + str(repeat_count))
        if direction_kw:
            method = "Input." + direction_kw
            for each_count in range(0, int(repeat_count)):
                self.kodi_payload = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "id": 1
                }
                try:
                    kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload),
                                                  headers=self.json_header)
                    LOG.info(kodi_response.text)
                except Exception as e:
                    LOG.error(e)
                    self.on_websettings_changed()
                self.speak_dialog("direction", data={"result": direction_kw},
                                  expect_response=True)
                time.sleep(1)

    # play the movie based on movie ID
    def play_film(self, movieid):
        self.clear_playlist()
        self.add_movie_playlist(movieid)
        if self.check_cinemavision_present():  # Cinemavision is installed
            self.set_context('CinemaVisionContextKeyword', 'CinemaVisionContext')
            self.speak_dialog('cinema.vision', expect_response=True)
        else:  # Cinemavision is NOT installed
            self.play_normal()

    # execute cinemavision addon decision
    @intent_handler(IntentBuilder('CinemavisionRequestIntent').require('CinemaVisionContextKeyword')
                    .one_of('YesKeyword', 'NoKeyword').build())
    def handle_cinemavision_request_intent(self, message):
        self.set_context('CinemaVisionContextKeyword', '')
        if "YesKeyword" in message.data:  # Yes was spoken to navigate the list
            LOG.info('User responded with: ' + message.data.get("YesKeyword"))
            self.play_cinemavision()
        else:  # No was spoken to navigate the list
            LOG.info('User responded with: ' + message.data.get("NoKeyword"))
            self.play_normal()

    # movie list navigation decision utterance
    @intent_handler(IntentBuilder('NavigateDecisionIntent').require('NavigateContextKeyword').
                    one_of('YesKeyword', 'NoKeyword').build())
    def handle_navigate_Decision_intent(self, message):
        self.set_context('NavigateContextKeyword', '')
        if "YesKeyword" in message.data:  # Yes was spoken to navigate the list, reading the first item
            LOG.info('User responded with...' + message.data.get('YesKeyword'))
            self.set_context('ListContextKeyword', 'ListContext')
            msg_payload = str(self.movie_list[self.movie_index]['label'])
            self.speak_dialog('navigate', data={"result": msg_payload}, expect_response=True)
        else:  # No was spoken to navigate the list, reading the first item
            LOG.info('User responded with...' + message.data.get('NoKeyword'))
            self.speak_dialog('cancel', expect_response=False)

    # the currently listed move was selected to play
    @intent_handler(IntentBuilder('NavigatePlayIntent').require('ListContextKeyword').require("PlayKeyword").
                    build())
    def handle_navigate_play_intent(self, message):
        self.set_context('ListContextKeyword', '')
        msg_payload = str(self.movie_list[self.movie_index]['label'])
        self.speak_dialog('play.film', data={"result": msg_payload}, expect_response=False)
        try:
            self.play_film(self.movie_list[self.movie_index]['movieid'])
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    # the user has requested to skip the currently listed movie
    @intent_handler(IntentBuilder('ParseNextIntent').require('ListContextKeyword').require('NextKeyword').
                    build())
    def handle_parse_next_intent(self, message):
        self.set_context('ListContextKeyword', 'ListContext')
        self.movie_index += 1
        if self.movie_index < len(self.movie_list):
            msg_payload = str(self.movie_list[self.movie_index]['label'])
            self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)
        else:
            self.set_context('ListContextKeyword', '')
            self.speak_dialog('list.end', expect_response=False)

    # the user has requested to stop navigating the list
    @intent_handler(IntentBuilder('NavigateStopIntent').require('NavigateContextKeyword').require('StopKeyword').
                    build())
    def handle_navigate_stop_intent(self, message):
        self.set_context('NavigateContextKeyword', '')
        self.speak_dialog('cancel', expect_response=False)

    # the user has requested to stop parsing the list
    @intent_handler(IntentBuilder('ParseCancelIntent').require('ListContextKeyword').require('StopKeyword').
                    build())
    def handle_parse_cancel_intent(self, message):
        self.set_context('ListContextKeyword', '')
        self.speak_dialog('cancel', expect_response=False)

    # Cancel was spoken, Cancel the list navigation
    @intent_handler(IntentBuilder('CursorCancelIntent').require('MoveKeyword').require('CursorKeyword').
                    require('StopKeyword').build())
    def handle_cursor_cancel_intent(self, message):
        self.set_context('MoveKeyword', '')
        self.set_context('CursorKeyword', '')
        LOG.info('handle_cursor_cancel_intent')
        self.speak_dialog('cancel', expect_response=False)

    # An internal conversational context stoppage was issued
    def stop_navigation(self, message):
        self.speak_dialog('context', data={"result": message}, expect_response=False)

    # the movie information dialog was requested in the utterance
    @intent_handler(IntentBuilder('SetVolumeIntent').require('SetsKeyword').require('KodiKeyword').
                    require('VolumeKeyword').build())
    def handle_set_volume_intent(self, message):
        str_remainder = str(message.utterance_remainder())
        volume_level = re.findall('\d+', str_remainder)
        if volume_level:
            if int(volume_level[0]) < 101:
                new_volume = self.set_volume(int(volume_level[0]))
                LOG.info("Kodi Volume Now: " + str(new_volume))
                self.speak_dialog('volume.set', data={'result': str(new_volume)}, expect_response=False)
            else:
                self.speak_dialog('volume.error', data={'result': int(volume_level[0])}, expect_response=False)

    def set_volume(self, level):
        method = "Application.SetVolume"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "volume": level
            },
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            return json.loads(kodi_response.text)["result"]
            # return level
        except Exception as e:
            return e

    # the movie information dialog was requested in the utterance
    @intent_handler(IntentBuilder('ShowMovieInfoIntent').require('VisibilityKeyword').require('InfoKeyword').
                    optionally('KodiKeyword').optionally('FilmKeyword').
                    build())
    def handle_show_movie_info_intent(self, message):
        method = "Input.Info"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    # the user requested to skip the movie timeline forward or backward
    @intent_handler(IntentBuilder('SkipMovieIntent').require("NextKeyword").require('FilmKeyword').
                    one_of('ForwardKeyword', 'BackwardKeyword').
                    build())
    def handle_skip_movie_intent(self, message):
        method = "Player.Seek"
        backward_kw = message.data.get("BackwardKeyword")
        if backward_kw:
            dir_skip = "smallbackward"
        else:
            dir_skip = "smallforward"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "playerid": 1,
                "value": dir_skip
            },
            "id": 1
        }
        if self.is_kodi_playing():
            try:
                kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload),
                                              headers=self.json_header)
                LOG.info(kodi_response.text)
            except Exception as e:
                LOG.error(e)
        else:
            LOG.info("There is no movie playing to skip")

    # user has requested to turn on the movie subtitles
    @intent_handler(IntentBuilder('SubtitlesOnIntent').require("KodiKeyword").require('SubtitlesKeyword').
                    require('OnKeyword').
                    build())
    def handle_subtitles_on_intent(self, message):
        method = "Player.SetSubtitle"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {
                "playerid": 1,
                "subtitle": "on"
            }
        }
        if self.is_kodi_playing():
            try:
                kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload),
                                              headers=self.json_header)
                LOG.info(kodi_response)
            except Exception as e:
                LOG.error(e)
        else:
            LOG.info("Turning Subtitles On Failed, kodi not playing")

    # user has requested to turn off the movie subtitles
    @intent_handler(IntentBuilder('SubtitlesOffIntent').require("KodiKeyword").require('SubtitlesKeyword').
                    require('OffKeyword').
                    build())
    def handle_subtitles_off_intent(self, message):
        method = "Player.SetSubtitle"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {
                "playerid": 1,
                "subtitle": "off"
            }
        }
        if self.is_kodi_playing():
            try:
                kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload),
                                              headers=self.json_header)
                LOG.info(kodi_response)
            except Exception as e:
                LOG.error(e)
        else:
            LOG.info("Turning Subtitles Off Failed, kodi not playing")

    # user has requested to show the recently added movies list
    @intent_handler(IntentBuilder('ShowMoviesAddedIntent').require("ListKeyword").require('RecentKeyword').
                    require('FilmKeyword').
                    build())
    def handle_show_movies_added_intent(self, message):
        method = "GUI.ActivateWindow"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "window": "videos",
                "parameters": [
                    "videodb://recentlyaddedmovies/"
                ]
            },
            "id": "1"
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            sort_kw = message.data.get("RecentKeyword")
            self.speak_dialog('sorted.by', data={"result": sort_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to show the movies listed by genres
    @intent_handler(IntentBuilder('ShowMoviesGenresIntent').require("ListKeyword").require('FilmKeyword').
                    require('GenreKeyword').
                    build())
    def handle_show_movies_genres_intent(self, message):
        method = "GUI.ActivateWindow"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "window": "videos",
                "parameters": [
                    "videodb://movies/genres/"
                ]
            },
            "id": "1"
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            sort_kw = message.data.get("GenreKeyword")
            self.speak_dialog('sorted.by', data={"result": sort_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to show the movies listed by actor
    @intent_handler(IntentBuilder('ShowMoviesActorsIntent').require("ListKeyword").require('FilmKeyword').
                    require('ActorKeyword').
                    build())
    def handle_show_movies_actors_intent(self, message):
        method = "GUI.ActivateWindow"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "window": "videos",
                "parameters": [
                    "videodb://movies/actors/"
                ]
            },
            "id": "1"
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            sort_kw = message.data.get("ActorKeyword")
            self.speak_dialog('sorted.by', data={"result": sort_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to show the movies listed by studio
    @intent_handler(IntentBuilder('ShowMoviesStudioIntent').require("ListKeyword").require('FilmKeyword').
                    require('StudioKeyword').
                    build())
    def handle_show_movies_studio_intent(self, message):
        method = "GUI.ActivateWindow"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "window": "videos",
                "parameters": [
                    "videodb://movies/studios/"
                ]
            },
            "id": "1"
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            sort_kw = message.data.get("StudioKeyword")
            self.speak_dialog('sorted.by', data={"result": sort_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to show the movies listed by title
    @intent_handler(IntentBuilder('ShowMoviesTitleIntent').require("ListKeyword").require('FilmKeyword').
                    require('TitleKeyword').
                    build())
    def handle_show_movies_title_intent(self, message):
        method = "GUI.ActivateWindow"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "window": "videos",
                "parameters": [
                    "videodb://movies/titles/"
                ]
            },
            "id": "1"
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            sort_kw = message.data.get("TitleKeyword")
            self.speak_dialog('sorted.by', data={"result": sort_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to show the movies listed by movie sets
    @intent_handler(IntentBuilder('ShowMoviesSetsIntent').require("ListKeyword").require('FilmKeyword').
                    require('SetsKeyword').
                    build())
    def handle_show_movies_sets_intent(self, message):
        method = "GUI.ActivateWindow"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "window": "videos",
                "parameters": [
                    "videodb://movies/sets/"
                ]
            },
            "id": "1"
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            sort_kw = message.data.get("SetsKeyword")
            self.speak_dialog('sorted.by', data={"result": sort_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to show the movies listed all movies
    @intent_handler(IntentBuilder('ShowAllMoviesIntent').require("ListKeyword").require('AllKeyword').
                    require('FilmKeyword').
                    build())
    def handle_show_all_movies_intent(self, message):
        self.show_root()
        method = "GUI.ActivateWindow"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "window": "videos",
                "parameters": [
                    "videodb://movies/"
                ]
            },
            "id": "1"
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            sort_kw = message.data.get("AllKeyword")
            self.speak_dialog('sorted.by', data={"result": sort_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to refresh the movie library database
    @intent_handler(IntentBuilder('CleanLibraryIntent').require("CleanKeyword").require('KodiKeyword').
                    require('LibraryKeyword').
                    build())
    def handle_clean_library_intent(self, message):
        method = "VideoLibrary.Clean"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {
                "showdialogs": True
            }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            update_kw = message.data.get("CleanKeyword")
            self.speak_dialog('update.library', data={"result": update_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to update the movie database
    @intent_handler(IntentBuilder('ScanLibraryIntent').require("ScanKeyword").require('KodiKeyword').
                    require('LibraryKeyword').
                    build())
    def handle_scan_library_intent(self, message):
        method = "VideoLibrary.Scan"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": {
                "showdialogs": True
            }
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
            update_kw = message.data.get("ScanKeyword")
            self.speak_dialog('update.library', data={"result": update_kw}, expect_response=False)
        except Exception as e:
            LOG.error(e)

    # user has requested to play a video from youtube
    # changed this intent to avoid common-play-framework
    @intent_handler(IntentBuilder('PlayYoutubeIntent').require("AskKeyword").require("KodiKeyword").
                    require("PlayKeyword").require('FromYoutubeKeyword').build())
    def handle_play_youtube_intent(self, message):
        self.youtube_search = self.youtube_query_regex(message.data.get('utterance'))
        self.youtube_id = self.get_youtube_links(self.youtube_search)
        if self.check_youtube_present():
            wait_while_speaking()
            if len(self.youtube_id) > 1:
                self.set_context('PlaylistContextKeyword', 'PlaylistContext')
                self.speak_dialog('youtube.playlist.present', expect_response=True)
            else:
                self.speak_dialog('play.youtube', data={"result": self.youtube_search}, expect_response=False)
                self.play_youtube_video(self.youtube_id[0])
        else:
            self.speak_dialog('youtube.addon.error', expect_response=False)

    # user is requested to make a decision to play a single youtube link or a playlist link
    @intent_handler(IntentBuilder('YoutubePlayTypeDecisionIntent').require('PlaylistContextKeyword').
                    one_of('YesKeyword', 'NoKeyword').build())
    def handle_youtube_play_type_decision_intent(self, message):
        self.set_context('PlaylistContextKeyword', '')
        self.speak_dialog('play.youtube', data={"result": self.youtube_search}, expect_response=False)
        if "YesKeyword" in message.data:
            LOG.info('Playing youtube id: ' + str(self.youtube_id[1]))
            self.play_youtube_video(self.youtube_id[1])
        else:
            LOG.info('Playing youtube id: ' + str(self.youtube_id[0]))
            self.play_youtube_video(self.youtube_id[0])

    def handle_random_movie_select_intent(self):
        full_list = self.list_all_movies()
        random_id = random.randint(1, len(full_list))
        selected_entry = full_list[random_id]
        selected_name = selected_entry['label']
        selected_id = selected_entry['movieid']
        LOG.info(selected_name, selected_id)
        self.speak_dialog('play.film', data={"result": selected_name}, expect_response=False)
        try:
            self.play_film(selected_id)
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def stop(self):
        pass


def create_skill():
    return KodiSkill()
