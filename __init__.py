from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

from kodipydent import Kodi

_author__ = 'PCWii'

LOGGER = getLogger(__name__)


class KodiSkill(MycroftSkill):
    """
    A Skill to control playback on a Kodi instance via the json-rpc interface.
    """
    def __init__(self):
        super(KodiSkill, self).__init__(name="KodiSkill")
        # self.settings["ipstring"] = ""
        self.kodi_instance = Kodi('192.168.0.32')
        self.notifier_bool = False

    def initialize(self):
        self.load_data_files(dirname(__file__))

        # Check and then monitor for credential changes
        # self.settings.set_changed_callback(self.on_websettings_changed)
        # self.on_websettings_changed()

        self.register_regex("film (?P<Film>.*)")
        self.register_regex("movie (?P<Film>.*)")
        self.register_regex("with (?P<Film>.*)")
        self.register_regex("containing (?P<Film>.*)")
        self.register_regex("matching (?P<Film>.*)")
        self.register_regex("including (?P<Film>.*)")

        self.add_event('recognizer_loop:wakeword', self.handle_listen)
        self.add_event('recognizer_loop:utterance', self.handle_utterance)
        self.add_event('speak', self.handle_speak)

        play_film_intent = IntentBuilder("PlayFilmIntent"). \
            require("PlayKeyword").require("FilmKeyword").build()
        self.register_intent(play_film_intent, self.handle_play_film_intent)

        search_film_intent = IntentBuilder("SearchFilmIntent"). \
            require("SearchKeyword").require("FilmKeyword").build()
        self.register_intent(search_film_intent, self.handle_search_film_intent)

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
            require("DirectionKeyword").build()
        self.register_intent(move_kodi_intent, self.handle_move_kodi_intent)


    def handle_listen(self, message):
        voice_payload = "Listening"
        if self.notifier_bool:
            self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI Message", message=voice_payload, displaytime=2000)

    def handle_utterance(self, message):
        utterance = message.data.get('utterances')
        voice_payload = utterance
        if self.notifier_bool:
            self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI Message", message=voice_payload, displaytime=2000)

    def handle_speak(self, message):
        speak = message.data.get('utterance')
        voice_payload = speak
        if self.notifier_bool:
            self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI Message", message=voice_payload, displaytime=2000)

    def handle_play_film_intent(self, message):
        utt_string = str(message.data.get('utterances'))
        film_kw = message.data.get("FilmKeyword")
        start_index = utt_string.find(film_kw) + len(film_kw) + 1
        movie_name = utt_string[start_index:]
        self.speak_dialog("play.film", data={"result": movie_name})
        self.play_film_by_search(self.kodi_instance, movie_name)

    def handle_search_film_intent(self, message):
        utt_string = str(message.data.get('utterances'))
        film_kw = message.data.get("FilmKeyword")
        start_index = utt_string.find(film_kw) + len(film_kw) + 1
        movie_name = utt_string[start_index:]
        self.speak_dialog("find.film", data={"result": movie_name})
        results = self.find_films_matching(self.kodi_instance, movie_name)
        self.speak_multi_film_match(message.data.get['Film'], results)

    def handle_stop_film_intent(self, message):
        self.kodi_instance.Player.Stop(playerid=1)

    def handle_pause_film_intent(self, message):
        self.kodi_instance.Player.PlayPause(playerid=1)

    def handle_resume_film_intent(self, message):
        self.kodi_instance.Player.PlayPause(playerid=1)

    def handle_notification_on_intent(self, message):
        self.notifier_bool = True
        self.speak_dialog("notification", data={"result": "On"})

    def handle_notification_off_intent(self, message):
        self.notifier_bool = False
        self.speak_dialog("notification", data={"result": "Off"})

    def handle_move_kodi_intent(self, message):
        direction = message.data.get("DirectionKeyword")
        if direction == "up":
            self.kodi_instance.Input.Up()
        if direction == "down":
            self.kodi_instance.Input.Down()
        if direction == "left":
            self.kodi_instance.Input.Left()
        if direction == "right":
            self.kodi_instance.Input.Right()
        if direction == "select" or direction == "enter":
            self.kodi_instance.Input.Select()
        if direction == "back":
            self.kodi_instance.Input.Back()
        move_kw = message.data.get('MoveKeyword')
        kodi_kw = message.data.get('KodiKeyword')
        self.speak("o-k, next", expect_response=True)
        self.set_context('MoveKeyword', move_kw)
        self.set_context('KodiKeyword', kodi_kw)

    # Kodi specific functions for searching and playing movies
    def find_films_matching(self, kodi_id, search):
        """
        Find all Movies Matching the search
        """
        my_movies = kodi_id.VideoLibrary.GetMovies()['result']['movies']
        results = []
        for m in my_movies:
            if search in m['label'].lower():
                results.append(m)
        return results

    def play_film(self, kodi_id, movieid):
        """
        Play a movie by id.
        """
        kodi_id.Playlist.Clear(playlistid=1)
        kodi_id.Playlist.Add(playlistid=1, item={'movieid': movieid})
        kodi_id.Player.Open(item={'playlistid': 1})


    def speak_multi_film_match(self, search, results):
        """
        Tell the user about a list of results.
        """
        output = "I found the following movies matching {}: ".format(search)
        for film in results:
            output += "{}, ".format(film['label'])

        self.speak(output)

    def play_film_by_search(self, kodi_id, film_search):
        results = self.find_films_matching(kodi_id, film_search)
        if len(results) == 1:
            self.play_film(kodi_id, results[0]['movieid'])
        elif len(results):
            print("I found multiple results: " + str(len(results)))  # film_search, results)
            play_index = 3
            self.play_film(kodi_id, results[play_index - 1]['movieid'])
        else:
            print("I found no results for the search: {}.".format(film_search))

    def stop():
        pass


def create_skill():
    return KodiSkill()
