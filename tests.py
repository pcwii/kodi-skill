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


def play_film_by_search(kodi_id, film_search):
    results = find_films_matching(kodi_id, film_search)
    if len(results) == 1:
        print('Found 1 Movie')
        play_film(kodi_id, results[0]['movieid'])
    elif len(results):
        print("I found multiple results: " + str(len(results)))  # film_search, results)
    else:
        print("I found no results for the search: {}.".format(film_search))

