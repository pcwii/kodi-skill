from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import getLogger
from mycroft.util.log import LOG
from mycroft.skills.context import adds_context, removes_context
from mycroft.util.parse import extract_number

from kodipydent import Kodi
import requests
import re
import time

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
        self.json_header = {'content-type': 'application/json'}
        self.json_response = ""
        self._is_setup = False

        self.notifier_bool = False
        self.movie_list = []
        self.movie_index = 0

        # self.engine = IntentDeterminationEngine()

    def initialize(self):
        self.load_data_files(dirname(__file__))

        #  Check and then monitor for credential changes
        self.settings.set_changed_callback(self.on_websettings_changed)
        self.on_websettings_changed()

        self.add_event('recognizer_loop:wakeword', self.handle_listen)
        self.add_event('recognizer_loop:utterance', self.handle_utterance)
        self.add_event('speak', self.handle_speak)

        play_film_intent = IntentBuilder("PlayFilmIntent"). \
            require("PlayKeyword").require("FilmKeyword").build()
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
                    self.kodi_instance = Kodi(hostname=kodi_ip,
                                              port=kodi_port,
                                              username=kodi_user,
                                              password=kodi_pass)
                    self.kodi_path = "http://"+kodi_ip+":"+kodi_port+"/jsonrpc"
                    # self.kodi_payload = '{"jsonrpc":"2.0","method":"player.open", "params": {"item":{"playlistid":1}}}'
                    self._is_setup = True
            except Exception as e:
                LOG.error(e)

    def movie_regex(self, message):
        regex = r"(movie|film) (?P<Film>.*)"
        utt_str = message
        matches = re.finditer(regex, utt_str, re.MULTILINE | re.DOTALL)
        for match_num, match in enumerate(matches):
            group_num = 2
            my_movie = "{group}".format(group=match.group(group_num))
        my_movie = re.sub('\W', ' ', my_movie)
        my_movie = re.sub(' +', ' ', my_movie)
        return my_movie

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

    def handle_listen(self, message):
        voice_payload = "Listening"
        if self.notifier_bool:
            try:
                self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI", message=voice_payload, displaytime=4000)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def handle_utterance(self, message):
        utterance = message.data.get('utterances')
        voice_payload = utterance
        if self.notifier_bool:
            try:
                self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI", message=voice_payload, displaytime=4000)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def handle_speak(self, message):
        voice_payload = message.data.get('utterance')
        if self.notifier_bool:
            try:
                self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI", message=voice_payload, displaytime=4000)
            except Exception as e:
                LOG.error(e)
                self.on_websettings_changed()

    def handle_play_film_intent(self, message):  # executed with original voice command
        # movie_name = message.data.get("Film")
        movie_name = self.movie_regex(message.data.get('utterance'))
        try:
            self.play_film_by_search(self.kodi_instance, movie_name)
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def handle_stop_film_intent(self, message):
        try:
            self.kodi_instance.Player.Stop(playerid=1)
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def handle_pause_film_intent(self, message):
        try:
            self.kodi_instance.Player.PlayPause(playerid=1)
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def handle_resume_film_intent(self, message):
        try:
            self.kodi_instance.Player.PlayPause(playerid=1)
        except Exception as e:
            LOG.error(e)
            self.on_websettings_changed()

    def handle_notification_on_intent(self, message):
        self.notifier_bool = True
        self.speak_dialog("notification", data={"result": "On"})

    def handle_notification_off_intent(self, message):
        self.notifier_bool = False
        self.speak_dialog("notification", data={"result": "Off"})

    def handle_move_kodi_intent(self, message):
        direction = message.data.get("DirectionKeyword")
        repeat_count = self.repeat_regex(message.data.get('utterance'))
        LOG.info('utterance: ' + str(message.data.get('utterance')))
        LOG.info('repeat_count: ' + str(repeat_count))
        if direction:
            for each_count in range(0, int(repeat_count)):
                try:
                    if direction == "up":
                        self.kodi_instance.Input.Up()
                    elif direction == "down":
                        self.kodi_instance.Input.Down()
                    elif direction == "left":
                        self.kodi_instance.Input.Left()
                    elif direction == "right":
                        self.kodi_instance.Input.Right()
                    elif direction == "select":
                        self.kodi_instance.Input.Select()
                    elif direction == "enter":
                        self.kodi_instance.Input.Select()
                    elif direction == "back":
                        self.kodi_instance.Input.Back()
                except Exception as e:
                    LOG.error(e)
                    self.on_websettings_changed()
                self.speak_dialog("direction", data={"result": direction}, 
                                  expect_response=(each_count==repeat_count-1))
                time.sleep(1)
        self.set_context('MoveKeyword', 'move')
        self.set_context('CursorKeyword', 'cursor')

    # Kodi specific functions for searching and playing movies
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

    @removes_context('ParseList')
    @removes_context('Navigate')
    def play_film(self, kodi_id, movieid):  # play the movie based on movie ID
        kodi_id.Playlist.Clear(playlistid=1)
        # time.sleep(1)  # add delay to avoid socket timeout
        kodi_id.Playlist.Add(playlistid=1, item={'movieid': movieid})
        # time.sleep(1)  # add delay to avoid socket timeout
        self.kodi_payload = '{"jsonrpc":"2.0","method":"player.open", "params": {"item":{"playlistid":1}}}'
        try:
            self.json_response = requests.post(self.kodi_path, data=self.kodi_payload, headers=self.json_header)  # start directly with json request
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
                    self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI", message=msg_payload, displaytime=2500)
                except Exception as e:
                    LOG.error(e)
                    self.on_websettings_changed()
            self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)
        else:
            msg_payload = "I found no results for the search: {}.".format(film_search)
            if self.notifier_bool:
                try:
                    self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI", message=msg_payload, displaytime=2500)
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
        self.kodi_payload = '{"jsonrpc":"2.0","method":"Input.Info", "params": {}}}'
        try:
            self.json_response = requests.post(self.kodi_path, data=self.kodi_payload,
                                      headers=self.json_header)  # start directly with json request
        except Exception as e:
            LOG.error(e)


    def stop(self):
        pass


def create_skill():
    return KodiSkill()
