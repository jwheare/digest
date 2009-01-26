#!/usr/bin/env python
# encoding: utf-8
"""
digestfetch.py
Fetch bitesize content from the world of the web for use in a daily digest pocketmod
"""

import re, sys, getopt, urllib, urllib2, httplib, socket
from cgi import parse_qs
from copy import copy

from BeautifulSoup import BeautifulSoup, SoupStrainer
AMPERSAND_MASSAGE = copy(BeautifulSoup.MARKUP_MASSAGE)

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

def tube_status():
    """Fetch Tube status from TFL"""
    url = "http://www.tfl.gov.uk/tfl/livetravelnews/realtime/tube/default.html"
    soup = BeautifulSoup(urllib.urlopen(url), markupMassage=AMPERSAND_MASSAGE,
        parseOnlyThese=SoupStrainer("div", { "id": "service-board" }))
    
    # Parse line status
    lines = soup.find("dl", { "id": "lines" }).findAll("dt")
    line_status = {}
    for line in lines:
        status = line.findNext("dd")
        if status.h3:
            line_status[line.string] = status.h3.string
        else: 
            line_status[line.string] = status.string
    # Parse station status
    station_categories = soup.find("dl", { "id": "stations" }).findAll("dt")
    station_status = {}
    for category in station_categories:
        stations = []
        next = category.findNextSibling(re.compile("dt|dd"))
        while next and next.name != u"dt":
            if next.h3:
                stations.append(next.h3.string)
            next = next.findNextSibling(re.compile("dt|dd"))
        station_status[category.string] = stations
    
    return line_status, station_status

if __name__ == '__main__':
    import pprint
    pprint.pprint(tube_status())