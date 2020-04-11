# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/tv.svg' card_color='#40DBB0' width='50' height='50' style='vertical-align:bottom'/> Kodi Control
Control KODI open source media center with Mycroft.ai

## About 
Utilize the kodi API and Python library for controlling the KODI open source media center with Mycroft.ai. The control is mostly geared towards videos/movies but is capable of handling cursor navigation as well.
The Kodi Skill uses conversational dialog to help you to control your KODI instance more naturally. 

## Examples 
* "ask kodi to play the movie guardians of the galaxy"
* "ask kodi to play the film planet of the apes"
* "ask kodi to play a random movie"
* "turn kodi subtitles on"
* "turn kodi subtitles off"
* "skip kodi forward"
* "skip kodi backward"
* "pause kodi"
* "pause the film"
* "re-start kodi"
* "stop the movie"
* "stop kodi"
* "set kodi volume to 100"
* "set kodi volume to 25"
* "show kodi movie information"
* "hide kodi movie information"
* "turn kodi notifications on"
* "turn kodi notifications off"
* "move the kodi cursor up / down / left / right / back / select / cancel"
* "move the kodi cursor right 3 times"
* "move the kodi cursor down twice"
* "update the kodi library"
* "clean the kodi library"
* "ask kodi to list recently added movies"
* "ask kodi to list the movies by genre"
* "ask kodi to list the movies by studio"
* "list kodi movie sets"
* "list kodi movies by title"
* "list kodi movies by actor"
* "list all kodi movies"
## Conversational Context
** If mycroft.ai locates more than one movie that matches your request it will permit you to itterate through your requests
using conversational context.
* eg. "hey mycroft:"
* Request: "ask kodi to play the move Iron Man"
* Response: "I have located 3 movies with the name Iron Man, would you like me to list them?"
* Request: "yes" / "no"
* Response: "Iron Man, to Skip, say Next, say play, to play, or Cancel, to stop"
* Request: "next" / "skip"
* Response: "Iron Man 2"
* Request: "play" / "select"
* Response: "o-k, attempting to play, Iron Man 2"
## Cinemavision Addon
If mycroft.ai locates the addon CinemaVision it will prompt the user if this addon should be used during the 
playback of the movie that was selected.
* Response: "Would you like to play the movie using cinemavision?"
* Request: "yes / no"
## Youtube Addon
* Request: "ask kodi to play some Elton John from youtube
* Request: "ask kodi to Play the official captain marvel trailer from youtube"
* Request: "Stop kodi"
## Credits 
* PCWii
* Original work forked from https://github.com/Cadair/mycroft-kodi
## Category
**Media**
## Tags
'#kodi, #Krypton #Leia, #mycroft.ai, #python, #skills #youtube'
## Require 
Tested on platform_picroft (others untested) 
## Other Requirements
- [Mycroft](https://docs.mycroft.ai/installing.and.running/installation)
## Further Reading
- [KODI API](https://kodi.wiki/index.php?title=JSON-RPC_API/v8)
- [CinemaVision](https://kodi.wiki/view/Add-on:CinemaVision)
## Installation Notes
- SSH and run: msm install https://github.com/pcwii/kodi-skill.git
- Configure Kodi to “allow remote control via HTTP”, under the Kodi settings:services
- Configure Kodi to “allow remote control from applications on other systems”, under the Kodi settings:services
- Under Kodi settings:services note the port number (8080)
- Configure home.mycroft.ai to set your kodi instance ip address and port number
## Todo
- ~~Convert all kodipydent functions to json requests~~ (Completed 20191021)
- ~~Enable username and password support in webgui~~ (Complete)
- ~~Enable subtitle control~~ (Complete)
- ~~Enable library scanning / cleaning~~ (Complete)
- ~~Enable Support for cinemavision~~ (Complete)
- ~~Correct cinemavision dialog control~~ (Complete)
- ~~Enable kodi Volume Control~~ (Completed 20191023)
- ~~Enable movie skip fwd/rev~~ (Complete)
- ~~Enable random movie selection~~ (Completed 20191021)
- ~~Add play "from youtube" option for videos / music~~ (Complete)
- ~~Clean up decision tree, requires significant pruning~~ ;-)
- Show a filtered list of movies when a play request returns multiple results (WIP)
- Add support for the CommonPlay Skill Infrastructure (Changed verbal requests 20191021)
- Investigate other play functions for music / episodes / pvr
- Investigate method to handle multiple KODI instances on network 
- ~~Add a single stop command for all playing items~~ (Completed 20191021)
- ~~Change skill call trigger words to reduce CommonPlay conflicts~~ (Completed 20191021)
- Add the ability to cast any Kodi Library item to a chromecast enabled device (WIP 20191219)
