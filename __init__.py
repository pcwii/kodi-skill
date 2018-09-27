from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import getLogger
from mycroft.util.log import LOG
from mycroft.skills.context import adds_context, removes_context
from mycroft.util.parse import extract_number

import urllib.error
import urllib.parse
import urllib.request

from kodipydent import Kodi
import requests
import re
import time
import json

_author__ = 'PCWii'
# Release - 20180713

LOGGER = getLogger(__name__)


class KodiSkill(MycroftSkill):
    """
    A Skill to control playback on a Kodi instance via the json-rpc interface.
    """
    def __init__(self):
        super(KodiSkill, self).__init__(name="KodiSkill")
        self.settings["kodi_ip"  ] = "127.0.0.1"
        self.settings["kodi_port"] = "8080"
        self.settings["kodi_user"] = ""
        self.settings["kodi_pass"] = ""
        self.kodi_path = ""
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

    def initialize(self):
        self.load_data_files(dirname(__file__))

        #  Check and then monitor for credential changes
        self.settings.set_changed_callback(self.on_websettings_changed)
        self.on_websettings_changed()

        self.add_event('recognizer_loop:wakeword', self.handle_listen)
        self.add_event('recognizer_loop:utterance', self.handle_utterance)
        self.add_event('speak', self.handle_speak)

        play_film_intent = IntentBuilder("PlayFilmIntent"). \
            require("PlayKeyword").require("FilmKeyword").optionally("CinemaVisionKeyword").build()
        self.register_intent(play_film_intent, self.handle_play_film_intent)

        stop_film_intent = IntentBuilder("StopFilmIntent"). \
            require("StopKeyword").require("FilmKeyword").build()
        self.register_intent(stop_film_intent, self.handle_stop_film_intent)

        pause_film_intent = IntentBuilder("PauseFilmIntent"). \
            require("PauseKeyword").require("FilmKeyword").build()
        self.register_intent(pause_film_intent, self.handle_pause_film_intent)

        resume_film_intent = IntentBuilder("ResumeFilmIntent"). \
            require("ResumeKeyword").require("FilmKeyword").build()
        self.register_intent(resume_film_intent, self.handle_resume_film_intent)

        notification_on_intent = IntentBuilder("NotifyOnIntent"). \
            require("NotificationKeyword").require("OnKeyword"). \
            require("KodiKeyword").build()
        self.register_intent(notification_on_intent, self.handle_notification_on_intent)

        notification_off_intent = IntentBuilder("NotifyOffIntent"). \
            require("NotificationKeyword").require("OffKeyword"). \
            require("KodiKeyword").build()
        self.register_intent(notification_off_intent, self.handle_notification_off_intent)

        move_kodi_intent = IntentBuilder("MoveKodiIntent"). \
            require("MoveKeyword").require("CursorKeyword").\
            require("DirectionKeyword").\
            build()
        self.register_intent(move_kodi_intent, self.handle_move_kodi_intent)

    def on_websettings_changed(self):
        if not self._is_setup:
            kodi_ip   = self.settings.get("kodi_ip", "127.0.0.1")
            kodi_port = self.settings.get("kodi_port", "8080")
            kodi_user = self.settings.get("kodi_user", "")
            kodi_pass = self.settings.get("kodi_pass", "")
            try:
                if kodi_ip and kodi_port:
                    kodi_ip   = self.settings["kodi_ip"  ]
                    kodi_port = self.settings["kodi_port"]
                    kodi_user = self.settings["kodi_user"]
                    kodi_pass = self.settings["kodi_pass"]
                    # TODO - remove kodipydent usage
                    self.kodi_instance = Kodi(hostname=kodi_ip,
                                              port=kodi_port,
                                              username=kodi_user,
                                              password=kodi_pass)
                    self.kodi_path = "http://" + kodi_user + ":" + kodi_pass + "@" + kodi_ip + ":" + str(kodi_port) + \
                                     "/jsonrpc"
                    self._is_setup = True
            except Exception as e:
                LOG.error(e)

    def is_kodi_playing(self):
        LOG.info("Checking if kodi is playing a movie")
        method = "Player.GetActivePlayers"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            parse_response = json.loads(kodi_response.text)["result"]
            LOG.info(kodi_response.text)
            if not parse_response:
                self.playing_status = False
            else:
                self.playing_status = True
        except Exception as e:
            LOG.error(e)
        LOG.info("Is Kodi Playing?...", str(self.playing_status))
        return self.playing_status

    def show_root(self):
        method = "GUI.ActivateWindow"
        kodi_payload = {
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
            kodi_response = requests.post(kodi_path, data=json.dumps(kodi_payload), headers=json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

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

    def add_playlist(self, movieid):
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

    def stop_movie(self):
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

    def pause_movie(self):
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

    def resume_movie(self):
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

    def find_films_matching(self, kodi_id, search):  # called from, play_film_by_search
        """
        Find all Movies Matching the search
        """
        my_movies = kodi_id.VideoLibrary.GetMovies()['result']['movies']
        results = []
        for m in my_movies:
            index_movie = re.sub('\W', ' ', m['label'].lower())
            index_movie = re.sub(' +', ' ', index_movie)
            if search in index_movie:
                results.append(m)
        return results

    def check_youtube_present(self):
        method = "Addons.GetAddons"
        addon_video = "xbmc.addon.video"
        kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": "1",
            "params": {
                "type": addon_video
            }
        }
        try:
            kodi_response = requests.post(kodi_path, data=json.dumps(kodi_payload), headers=json_header)
        except Exception as e:
            print(e)
            return False
        if "plugin.video.youtube" in kodi_response.text:
            return True
        else:
            return False

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
            print(e)
            return False
        if "script.cinemavision" in self.list_response.text:
            return True
        else:
            return False

    def movie_regex(self, message):
        # film_regex = r"(movie|film) (?P<Film>.*)"
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
        my_movie = re.sub('\W', ' ', my_movie)
        my_movie = re.sub(' +', ' ', my_movie)
        return my_movie.strip()

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

    def play_youtube_video(self, video_id):
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
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.inof(kodi_response.text)
        except Exception as e:
            LOG.error(e)

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

    def get_youtube_links(self, search_list):
        search_text = str(search_list[0])
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
            LOG.info("Found Single Links: " + video_links)
        if playlist_links:
            yt_links.append(playlist_links[0])
            LOG.info("Found Playlist Links: " + playlist_links)
        return yt_links

    def post_kodi_notification(self, message):
        method = "GUI.ShowNotification"
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "title": "Kelsey.AI",
                "message": str(message),
                "displaytime": 5000,
            },
            "id": 1
        }
        try:
            kodi_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload), headers=self.json_header)
            LOG.info(kodi_response.text)
        except Exception as e:
            LOG.error(e)

    def handle_listen(self, message):
        voice_payload = "Listening"
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def handle_utterance(self, message):
        utterance = message.data.get('utterances')
        voice_payload = utterance
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def handle_speak(self, message):
        voice_payload = message.data.get('utterance')
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def handle_play_film_intent(self, message):  # executed with original voice command
        if message.data.get("CinemaVisionKeyword"):
            self.cv_request = True
        else:
            self.cv_request = False
        movie_name = self.movie_regex(message.data.get('utterance'))
        try:
            LOG.info("movie: " + movie_name)
            # TODO - remove kodipydent usage
            self.play_film_by_search(self.kodi_instance, movie_name)
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def handle_stop_film_intent(self, message):
        try:
            self.stop_movie()
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def handle_pause_film_intent(self, message):
        try:
            self.pause_movie()
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def handle_resume_film_intent(self, message):
        try:
            self.resume_movie()
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def handle_notification_on_intent(self, message):
        self.notifier_bool = True
        self.speak_dialog("notification", data={"result": "On"})

    def handle_notification_off_intent(self, message):
        self.notifier_bool = False
        self.speak_dialog("notification", data={"result": "Off"})

    @adds_context('Navigate')
    def handle_move_kodi_intent(self, message):
        direction_kw = message.data.get("DirectionKeyword")
        repeat_count = self.repeat_regex(message.data.get('utterance'))
        LOG.info('utterance: ' + str(message.data.get('utterance')))
        LOG.info('repeat_count: ' + str(repeat_count))
        if direction_kw:
            method = "Input." + direction_kw.capitalize()
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
                self.speak_dialog("direction", data={"result": direction}, 
                                  expect_response=(each_count == repeat_count-1))
                time.sleep(1)
        self.set_context('MoveKeyword', 'move')
        self.set_context('CursorKeyword', 'cursor')

    @removes_context('ParseList')
    @removes_context('Navigate')
    def play_film(self, kodi_id, movieid):  # play the movie based on movie ID
        self.clear_playlist()
        self.add_playlist(movieid)
        self.kodi_payload = {
            "jsonrpc": "2.0",
            "method": "player.open",
            "params": {
                "item": {
                    "playlistid": 1
                }
            },
            "id": 1
        }
        self.cv_payload = {
            "jsonrpc": "2.0",
            "method": "Addons.ExecuteAddon",
            "params": {
                "addonid": "script.cinemavision",
                "params": [
                    "experience", "nodialog"
                ]
            },
            "id": 1
        }
        # all_addons = self.list_addons()
        # if "script.cinemavision" in all_addons:
        self.use_cv = False
        if self.check_cinemavision_present():  # Cinemavision is installed
            if not self.cv_request:  # Cinemavision was not commanded in the utterance
                if self.ask_yesno('cinema.vision') == 'yes':
                    self.use_cv = True
                else:  # User does NOT want to use Cinemavision
                    self.use_cv = False
            else:  # Cinemavision WAS commanded by the utterance
                self.use_cv = True
        else:  # Cinemavision is NOT installed
            self.use_cv = False
        if self.use_cv:
            try:  # run with Cinemavision
                self.cv_response = requests.post(self.kodi_path, data=json.dumps(self.cv_payload),
                                                 headers=self.json_header)
                LOG.info(self.cv_response.text)
            except Exception as e:
                LOG.error(e)
        else:
            try:
                self.json_response = requests.post(self.kodi_path, data=json.dumps(self.kodi_payload),
                                                   headers=self.json_header)
                LOG.info(self.json_response.text)
            except Exception as e:
                LOG.error(e)

    @adds_context('Navigate')
    def play_film_by_search(self, kodi_id, film_search):  # called from, handle_play_film_intent
        results = self.find_films_matching(kodi_id, film_search)
        self.movie_list = results
        self.movie_index = 0
        if len(results) == 1:
            self.play_film(kodi_id, results[0]['movieid'])
        elif len(results):
            msg_payload = "I found, " + str(len(results)) + ", results, would you like me to list them?"
            if self.notifier_bool:
                try:
                    self.post_kodi_notification(msg_payload)
                except Exception as e:
                    LOG.error(e)
                    self.on_websettings_changed()
            self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)
        else:
            msg_payload = "I found no results for the search: {}.".format(film_search)
            if self.notifier_bool:
                try:
                    self.post_kodi_notification(msg_payload)
                except Exception as e:
                    LOG.error(e)
                    self.on_websettings_changed()
            self.stop_navigation(msg_payload)

    @intent_handler(IntentBuilder('NavigateYesIntent').require("YesKeyword").require('Navigate').build())
    @adds_context('ParseList')
    def handle_navigate_yes_intent(self, message):  # Yes was spoken to navigate the list, reading the first item
        msg_payload = str(self.movie_list[self.movie_index]['label']) + ", To Skip, say Next, Say play, to" \
                                                               " play, or Cancel, to stop"
        self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)

    @intent_handler(IntentBuilder('NavigatePlayIntent').require("PlayKeyword").require('ParseList').
                    optionally('Navigate').build())  # optionally('OrdinalKeyword').build())
    @removes_context('ParseList')
    @removes_context('Navigate')
    def handle_navigate_play_intent(self, message):  # Play was spoken, calls play_film
        msg_payload = "Attempting to play, " + str(self.movie_list[self.movie_index]['label'])
        self.speak_dialog('context', data={"result": msg_payload}, expect_response=False)
        try:
            # TODO - remove kodipydent usage
            self.play_film(self.kodi_instance, self.movie_list[self.movie_index]['movieid'])
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    @intent_handler(IntentBuilder('SkipIntent').require("NextKeyword").require('ParseList').optionally('Navigate').
                    build())
    def handle_navigate_skip_intent(self, message):  # Skip was spoken, navigates to next item in the list
        self.movie_index += 1
        if self.movie_index < len(self.movie_list):
            msg_payload = str(self.movie_list[self.movie_index]['label'])
            self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)
        else:
            msg_payload = "there are no more movies in the list"
            self.stop_navigation(msg_payload)

    @intent_handler(IntentBuilder('NavigateCancelIntent').require("CancelKeyword").require('Navigate').
                    optionally('ParseList').build())
    @removes_context('Navigate')
    @removes_context('ParseList')
    def handle_navigate_cancel_intent(self, message):  # Cancel was spoken, Cancel the list navigation
        msg_payload = 'Canceled'
        self.speak_dialog('context', data={"result": msg_payload}, expect_response=False)

    @removes_context('Navigate')
    @removes_context('ParseList')
    def stop_navigation(self, message):  # An internal conversational context stoppage was issued
        self.speak_dialog('context', data={"result": message}, expect_response=False)

    @intent_handler(IntentBuilder('ShowMovieInfoIntent').require("VisibilityKeyword").require('InfoKeyword').
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

    @intent_handler(IntentBuilder('SkipMovieIntent').require("SkipKeyword").require('FilmKeyword').
                    require('SkipDirectionKeyword').
                    build())
    def handle_skip_movie_intent(self, message):
        method = "Player.Seek"
        dir_kw = message.data.get("SkipDirectionKeyword")
        if dir_kw == "backward":
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
            LOG.info("Subtitles On Failed, kodi not playing")

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
            LOG.info("Subtitles Off Failed, kodi not playing")

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

    @intent_handler(IntentBuilder('PlayYoutubeIntent').require("PlayKeyword").require('FromYoutubeKeyword').
                    build())
    def handle_play_youtube_intent(self, message):
        youtube_search = self.youtube_query_regex(message.data.get('utterance'))
        youtube_id = self.get_youtube_links(youtube_search)
        if self.check_youtube_present():
            self.speak_dialog('play.youtube', data={"result": youtube_search}, expect_response=False)
            if len(youtube_id) > 1:
                if self.ask_yesno('youtube.playlist.present') == 'yes':
                    self.play_youtube_video(youtube_id[1])
                else:
                    self.play_youtube_video(youtube_id[0])
            else:
                self.play_youtube_video(youtube_id[0])
        else:
            self.speak_dialog('youtube.addon.error', expect_response=False)

    def stop(self):
        pass


def create_skill():
    return KodiSkill()
