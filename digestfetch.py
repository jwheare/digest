#!/usr/bin/env python
# encoding: utf-8
"""
digestfetch.py
Fetch bitesize content from the world of the web for use in a daily digest pocketmod
"""

import sitecustomize

# Builtin modules
from copy import copy
from operator import itemgetter
import re
import time, datetime
import urllib, urllib2, httplib

# 3rd party modules
import pylast

import gdata.calendar.service

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup, SoupStrainer

import simplejson

import feedparser

import flickrapi

# Settings, keys, passwords
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
    events = user.getRecommendedEvents(limit=6)
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
    soup = BeautifulSoup(urllib.urlopen(url), markupMassage=BeautifulSoup.MARKUP_MASSAGE,
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
    passman.add_password("Twitter API", "twitter.com", TWITTER_USERNAME, TWITTER_PASSWORD)
    
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    
    opener = urllib2.build_opener(authhandler)
    
    try:
        json = opener.open(url).read()
        statuses = simplejson.loads(json)
        return statuses
    except urllib2.HTTPError, e:
        print e

def newsgator_headlines():
    """Fetch unread feeds from Newsgator"""
    url = "http://services.newsgator.com/ngws/svc/Subscription.aspx/%s/headlines" % NEWSGATOR_LOCATIONID
    
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password("NewsGator Online Services", "services.newsgator.com", NEWSGATOR_USERNAME, NEWSGATOR_PASSWORD)
    
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    
    opener = urllib2.build_opener(authhandler)
    opener.addheaders = [
        ('X-NGAPIToken', NEWSGATOR_KEY)
    ]
    try:
        data = feedparser.parse(opener.open(url))
        return data
    except urllib2.HTTPError, e:
        print e

def gcal_events():
    """Fetch events from a list of Google Calendars"""
    calendar_service = gdata.calendar.service.CalendarService()
    calendar_service.email = GCAL_USERNAME
    calendar_service.password = GCAL_PASSWORD
    calendar_service.ProgrammaticLogin()
    
    # feed = calendar_service.GetAllCalendarsFeed()
    # for i, calendar in enumerate(feed.entry):
    #     print '\t%s. %s (%s %s)' % (i, calendar.title.text, calendar.color.value, calendar.id.text.split('/')[-1])
    
    events = []
    
    start_min = time.strftime('%Y-%m-%d', time.gmtime(time.time()))
    start_max = time.strftime('%Y-%m-%d', time.gmtime(time.time() + 60*60*24*3))
    for (calendar, info) in GCAL_CALENDARS.iteritems():
        cal_name, color = info
        print u'•', cal_name
        query = gdata.calendar.service.CalendarEventQuery(calendar, 'private', 'composite')
        query.start_min = start_min
        query.start_max = start_max
        query.orderby = 'starttime'
        query.sortorder = 'ascending'
        
        try:
            feed = calendar_service.CalendarQuery(query)
            # print feed
            for event in feed.entry:
                if event.when:
                    comments = []
                    if event.comments and event.comments.feed_link and event.comments.feed_link.feed:
                        for c in event.comments.feed_link.feed.entry:
                            if c.content.text:
                                comments.append({
                                    'author': c.author[0].name.text,
                                    'content': c.content.text,
                                })
                    event_info = {
                        'color': color,
                        'title': event.title.text,
                        'comments': comments,
                        'allday': False,
                        'location': event.where[0].value_string
                    }
                    try:
                        start = datetime.datetime.strptime(event.when[0].start_time, "%Y-%m-%dT%H:%M:%S.000Z")
                    except ValueError:
                        start = datetime.datetime.strptime(event.when[0].start_time, "%Y-%m-%d")
                        event_info['allday'] = True
                    event_info['start'] = start
                    events.append(event_info)
        except httplib.BadStatusLine, e:
            print "! %s" % e
    events.sort(key=itemgetter('start'))
    return events

def weather():
    forecast_url = "http://feeds.bbc.co.uk/weather/feeds/rss/5day/world/%s.xml" % BBC_WEATHER_LOCATION
    forecast_data = feedparser.parse(urllib.urlopen(forecast_url))
    
    warning_url = "http://www.metoffice.gov.uk/xml/warnings_rss_%s.xml" % MET_WEATHER_REGION
    warning_data = feedparser.parse(urllib.urlopen(warning_url))
    
    return forecast_data, warning_data

def flickr_auth():
    """Authenticate with the Flickr API"""
    flickr = flickrapi.FlickrAPI(FLICKR_KEY, FLICKR_SECRET)
    
    token, frob = flickr.get_token_part_one(perms='read')
    if not token:
        raw_input("Press ENTER after you authorized this program")
        flickr.get_token_part_two((token, frob))
    return flickr
    
def contact_photo():
    flickr = flickr_auth()
    yesterday = datetime.datetime.now() - datetime.timedelta(hours=24)
    photos = flickr.photos_search(
        user_id='me',
        contacts='all',
        media='photos',
        sort='interestingness-desc',
        min_upload_date=int(time.mktime(yesterday.timetuple())),
        extras='owner_name,tags,date_taken'
    )
    print "Searching",
    for p in photos.findall('photos/photo'):
        print '#',
        sizes = flickr.photos_getSizes(photo_id=p.attrib['id'])
        for size in sizes.findall("sizes/size"):
            print '.',
            if size.attrib['label'] == u'Original':
                if int(size.attrib['width']) > int(size.attrib['height']):
                    print 'done'
                    return p, size

if __name__ == '__main__':
    gcal_events()