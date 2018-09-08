from kodipydent import Kodi
import re

my_kodi_instance = Kodi('192.168.0.32')


def find_films_matching(kodi_id, search):
    """
     Find all Movies Matching the search
     """
    my_movies = kodi_id.VideoLibrary.GetMovies()['result']['movies']
    results = []
    print(search)
    for m in my_movies:
        index_movie = re.sub('\W', ' ', m['label'].lower())
        index_movie = re.sub(' +', ' ', index_movie)
        if search in index_movie:
            results.append(m)
    return results


def play_film(kodi_id, movieid):
    """
    Play a movie by id.
    """
    kodi_id.Playlist.Clear(playlistid=1)
    kodi_id.Playlist.Add(playlistid=1, item={'movieid': movieid})
    kodi_id.Player.Open(item={'playlistid': 1})

def get_addons(kodi_id):
    all_addons = kodi_id.Addons.GetAddons
    print(all_addons)
    for kodi_addon in all_addons:
        print(kodi_addon)


def play_film_by_search(kodi_id, film_search):
    results = find_films_matching(kodi_id, film_search)
    if len(results) == 1:
        print('Found 1 Movie')
        play_film(kodi_id, results[0]['movieid'])
    elif len(results):
        print("I found multiple results: " + str(len(results)))  # film_search, results)
    else:
        print("I found no results for the search: {}.".format(film_search))

get_addons(my_kodi_instance)



#my_kodi_instance.Input.Up()
# my_kodi_instance.Player.Open(1)
# my_kodi_instance.GUI.ShowNotification(title="Mycroft.AI Message", message="Hello This is a Test!", displaytime=2000)


# movie_id = find_films_matching(my_kodi_instance, "iron man")
# print(movie_id)
#play_film_by_search(my_kodi_instance, "ant man")

#regex = r"(movie|film) (?P<Film>.*)"
#utt_str = "play the movie guardians of the galaxy"
#matches = re.finditer(regex, utt_str, re.MULTILINE | re.DOTALL)
#for matchNum, match in enumerate(matches):
#    matchNum = matchNum + 1
#    groupNum = 2
#    my_movie = "{group}".format(groupNum=groupNum, start=match.start(groupNum),
#                                                                    end=match.end(groupNum),
#                                                                    group=match.group(groupNum))
#    print(my_movie)
    #for groupNum in range(0, len(match.groups())):
    #    groupNum = groupNum + 1

     #   print("Group {groupNum} found at {start}-{end}: {group}".format(groupNum=groupNum, start=match.start(groupNum),
#                                                                        end=match.end(groupNum),
#                                                                        group=match.group(groupNum)))


# print(my_kodi_instance)

# print(movie_id)
# print(my_kodi_instance)
# play_film_by_search("wonder woman")

# mystring = "play the movie captain america the first avenger"
# mystring = re.sub('\W', ' ', mystring)
# movie_name = re.sub('(movie|film) (?P<Film>.*)', mystring[])
# print(movie_name)
# play_film_by_search(my_kodi_instance, movie_name)

#    def speak_multi_film_match(self, search, results):  # Tell the user about the list of results
#        output = "I found the following movies matching {}: ".format(search)
#        for film in results:
#            output += "{}, ".format(film['label'])
#        self.speak(output)

#    def handle_search_film_intent(self, message):
#        movie_name = message.data.get("Film")
#        movie_name = re.sub('\W', ' ', movie_name)
#        movie_name = re.sub(' +', ' ', movie_name)
#        # self.speak_dialog("find.film", data={"result": movie_name})
#        results = self.find_films_matching(self.kodi_instance, movie_name)
#        self.speak_multi_film_match(self, message.data.get('Film'), results)
#        # self.speak_multi_film_match(message.data.get['Film'], results)

#        search_film_intent = IntentBuilder("SearchFilmIntent"). \
#            require("SearchKeyword").require("Film").build()
#        self.register_intent(search_film_intent, self.handle_search_film_intent)