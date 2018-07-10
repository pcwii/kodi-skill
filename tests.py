from kodipydent import Kodi

my_kodi_instance = Kodi('192.168.0.32')


def find_films_matching(kodi_id,search):
    my_movies = kodi_id.VideoLibrary.GetMovies()['result']['movies']
    results = []
    for m in my_movies:
        if search in m['label'].lower():
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
# play_film_by_search(my_kodi_instance, "iron man")

my_kodi_instance.Player.PlayPause(playerid=1)

# print(movie_id)
# print(my_kodi_instance)
# play_film_by_search("wonder woman")