# This skill is under development and remains a WIP
# ***Not usable at this time***
#**************************************************
# Wish List
# 1. play / stop / pause / resume functions for movies. - WIP
# 2. Search for movies - WIP
# 3. Cursor control (up, down, left, right, select, back - WIP
# 4. Notifications - WIP
# Kodi Skill for Mycroft AI

This is an attempt to create a skill for the new [MycroftAI](https://mycroft.ai) which can search for, play and control Kodi instances via Kodi's JSON-RPC API.

This uses [kodipydent](https://github.com/haikuginger/kodipydent) to interface with the Kodi JSON-RPC interface.


## Installation

You will need to install kodipydent:

    pip install kodipydent

inside the correct virtualenv for mycroft, and then clone this repo into `~/.mycroft/third_party_skills`.


## Features

Currently this skill can do the following things (with some variation):

    Mycroft, play film The Matrix
    Mycroft, search for films containing Matrix

If it tries to play a film and there is multiple matches it will read out the search results you asked for and then let you refine your query.
