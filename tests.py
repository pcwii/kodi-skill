from kodipydent import Kodi
import re

my_kodi_instance = Kodi('192.168.0.32')


def find_films_matching(kodi_id,search):
    my_movies = kodi_id.VideoLibrary.GetMovies()['result']['movies']
    print(my_movies)
    results = []
    for m in my_movies:
        index_movie = re.sub('\W', ' ', m['label'].lower())
        index_movie = re.sub(' +', ' ', index_movie)
        print(index_movie)
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


def play_film_by_search(kodi_id, film_search):
    results = find_films_matching(kodi_id, film_search)
    if len(results) == 1:
        play_film(kodi_id, results[0]['movieid'])
    elif len(results):
        print("I found multiple results: " + str(len(results)))  # film_search, results)
        play_index = 3
        play_film(kodi_id, results[play_index - 1]['movieid'])
    else:
        print("I found no results for the search: {}.".format(film_search))

#my_kodi_instance.Input.Up()
# my_kodi_instance.Player.Open(1)
# my_kodi_instance.GUI.ShowNotification(title="Mycroft.AI Message", message="Hello This is a Test!", displaytime=2000)


# movie_id = find_films_matching(my_kodi_instance, "iron man")
# print(movie_id)
# play_film_by_search(my_kodi_instance, "thor the dark world")

# my_kodi_instance.Player.PlayPause(playerid=1)
# print(my_kodi_instance)

# print(movie_id)
# print(my_kodi_instance)
# play_film_by_search("wonder woman")

mystring = "play the movie spider-man homecoming"
mystring = re.sub('\W', ' ', mystring)
keyword = "movie"
start_index = mystring.find(keyword) + len(keyword) + 1
print(start_index)
movie_name = mystring[start_index:]
print(movie_name)
play_film_by_search(my_kodi_instance, movie_name)