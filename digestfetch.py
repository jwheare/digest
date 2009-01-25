#!/usr/bin/env python
# encoding: utf-8
"""
digestfetch.py
Fetch bitesize content from the world of the web for use in a daily digest pocketmod
"""

import pylast

from settings import *

def lastfm_auth():
    """Authenticate with the Last.fm API"""
    
    sg = pylast.SessionGenerator(LASTFM_KEY, LASTFM_SECRET)
    token = sg.getToken()
    auth_url = sg.getAuthURL(token)
    
    print "Please open the following URL in your web browser and complete the authentication process, then press Enter to continue..."
    print auth_url
    
    raw_input()
    
    data = sg.getSessionKey(token)
    print data

def lastfm_event_recommendations():
    """Fetch a list of event recommendations for today from Last.fm"""
    user = pylast.User('jwheare', LASTFM_KEY, LASTFM_SECRET, LASTFM_SESSION)
    events = user.getRecommendedEvents(limit=5)
    return events

if __name__ == '__main__':
    lastfm_event_recommendations()