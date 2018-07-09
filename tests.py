from kodipydent import Kodi
# import kodi

my_kodi_instance = Kodi('192.168.0.32')
my_movies = my_kodi_instance.VideoLibrary.GetMovies()
#my_kodi_instance.Input.Up()
# my_kodi_instance.Player.Open(1)
my_kodi_instance.GUI.ShowNotification(title="Mycroft.AI Message", message="Hello This is a Test!", displaytime=2000)
# print(my_movies)
# print(my_kodi_instance)
