from kodipydent import Kodi
import kodi

my_kodi_instance = Kodi('192.168.0.32')
my_movies = my_kodi_instance.VideoLibrary.GetMovies()
# my_kodi_instance.Input.Down()
# my_kodi_instance.Player.Open(1)
# my_kodi_instance.GUI.ShowNotification('Mycroft.ai Message, message['This is a test message', image, username, password, 2000])
print(my_movies)
# print(my_kodi_instance)
