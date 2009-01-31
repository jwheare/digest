#!/usr/bin/env python
# encoding: utf-8
"""
digestfetch.py
Fetch bitesize content from the world of the web for use in a daily digest pocketmod
"""

import re, urllib, urllib2
from copy import copy

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup, SoupStrainer
AMPERSAND_MASSAGE = copy(BeautifulSoup.MARKUP_MASSAGE)

import pylast

from django.utils import simplejson

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

def get_tube_colors():
    colors = {
        "bakerloo":            ("ffffff", "ae6118"),
        "central":             ("ffffff", "e41f1f"),
        "circle":              ("113b92", "f8d42d"),
        "district":            ("ffffff", "00a575"),
        "eastlondon":          ("113b92", "f2ad41"),
        "hammersmithandcity":  ("113b92", "e899a8"),
        "jubilee":             ("ffffff", "8f989e"),
        "metropolitan":        ("ffffff", "893267"),
        "northern":            ("ffffff", "000000"),
        "piccadilly":          ("ffffff", "0450a1"),
        "victoria":            ("ffffff", "009fe0"),
        "waterlooandcity":     ("113b92", "70c3ce"),
        "dlr":                 ("ffffff", "00bbb4"),
    }
    return colors

def tube_status():
    """Fetch Tube status from TFL"""
    url = "http://www.tfl.gov.uk/tfl/livetravelnews/realtime/tube/later.html"
    soup = BeautifulSoup(urllib.urlopen(url), markupMassage=AMPERSAND_MASSAGE,
        parseOnlyThese=SoupStrainer("div", { "id": "service-board" }),
        convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
    
    # Parse line status
    lines = soup.find("dl", { "id": "lines" }).findAll("dt")
    line_status = {}
    for line in lines:
        status = line.findNext("dd")
        if status.h3:
            line_status[line['class']] = (line.string, status.h3.string)
        else: 
            line_status[line['class']] = (line.string, "")
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

def twitter_friends():
    """Fetch Twitter updates from friends"""
    url = "http://twitter.com/statuses/friends_timeline.json"
    
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password("Twitter API", url, TWITTER_USERNAME, TWITTER_PASSWORD)
    
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    
    opener = urllib2.build_opener(authhandler)
    
    try:
        json = opener.open(url).read()
        statuses = simplejson.loads(json)
        return statuses
    except urllib2.HTTPError, e:
        print e

if __name__ == '__main__':
    statuses = twitter_friends()
    for status in statuses:
        print "%s: %s (%s)" % (status['user']['name'], status['text'], status['user']['profile_image_url'])
