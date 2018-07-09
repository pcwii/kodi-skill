from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

from kodipydent import Kodi
import kodi

_author__ = 'PCWii'

LOGGER = getLogger(__name__)


class KodiSkill(MycroftSkill):
    """
    A Skill to control playback on a Kodi instance via the json-rpc interface.
    """

    def __init__(self):
        super(KodiSkill, self).__init__(name="KodiSkill")
        self.settings["ipstring"] = ""
        self.kodi = Kodi('192.168.0.32')

    def initialize(self):
        self.load_data_files(dirname(__file__))

        # Check and then monitor for credential changes
        self.settings.set_changed_callback(self.on_websettings_changed)
        self.on_websettings_changed()

        self.register_regex("film (?P<Film>.*)")
        self.register_regex("movie (?P<Film>.*)")
        self.register_regex("with (?P<Film>.*)")
        self.register_regex("containing (?P<Film>.*)")
        self.register_regex("matching (?P<Film>.*)")
        self.register_regex("including (?P<Film>.*)")

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

        move_kodi_intent = IntentBuilder("MoveKodiIntent"). \
            require("MoveKeyword").require("KodiKeyword").\
            require("DirectionKeyword").build()
        self.register_intent(move_kodi_intent, self.handle_move_kodi_intent)

    def handle_play_film_intent(self, message):
        #self.play_film_by_search(self.kodi, message.metadata['Film'])
        str_remainder = str(message.utterance_remainder())
        self.play_film_by_search(str_remainder)

    def handle_search_film_intent(self, message):
        results = kodi.find_films_matching(self.kodi, message.metadata['Film'])
        self.speak_multi_film_match(message.metadata['Film'], results)

    def handle_stop_film_intent(self, message):
        kodi.stop_playback()

    def handle_pause_film_intent(self, message):
        kodi.playpause_playback()

    def handle_resume_film_intent(self, message):
        kodi.playpause_playback()

    def handle_move_kodi_intent(self, message):
        direction = message.data.get("DirectionKeyword")
        if direction == "up":
            kodi.Input.Up()
        if direction == "down":
            kodi.Input.Down()
        if direction == "left":
            kodi.Input.Left()
        if direction == "right":
            kodi.Input.Right()


    # Mycroft Actions, speaking etc. #
    def speak_multi_film_match(self, search, results):
        """
        Tell the user about a list of results.
        """
        output = "I found the following movies matching {}: ".format(search)
        for film in results:
            output += "{}, ".format(film['label'])

        self.speak(output)

    def play_film_by_search(self, film_search):
        """
        Search for films using the query, then play if only one result,
        otherwise tell the user about the results.

        Parameters
        ----------

        mycroft : `MycroftSkill` instance
            The current Mycroft instance.

        film_search : `string` A string to search the library for.
        """
        results = kodi.find_films_matching(film_search)
        if len(results) == 1:
            kodi.play_film(results[0]['movieid'])
        elif len(results):
            self.speak_multi_film_match(film_search, results)
        else:
            self.speak("I found no results for the search: {}.".format(film_search))

    def stop():
        pass


def create_skill():
    return KodiSkill()
