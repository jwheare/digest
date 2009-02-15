# -*- coding: utf-8 -*-
#
# pylast - A Python interface to the Last.fm API.
# Copyright (C) 2008-2009  Amr Hassan
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#
# http://code.google.com/p/pylast/

__name__ = 'pyLast'
__version__ = '0.3.0'
__doc__ = 'A Python interface to the Last.fm API.'
__author__ = 'Amr Hassan'
__email__ = 'amr.hassan@gmail.com'

HOST_NAME = 'ws.audioscrobbler.com'
HOST_SUBDIR = '/2.0/'

# In order to use proxy set this value to a 
# sequence of host name or ip and port number like: ("x.x.x.x", "x")
# To disable using a proxy, set it to None.
PROXY = None

import hashlib
import httplib
import urllib
import threading
import time
import datetime
from xml.dom import minidom

STATUS_INVALID_SERVICE = 2
STATUS_INVALID_METHOD = 3
STATUS_AUTH_FAILED = 4
STATUS_INVALID_FORMAT = 5
STATUS_INVALID_PARAMS = 6
STATUS_INVALID_RESOURCE = 7
STATUS_TOKEN_ERROR = 8
STATUS_INVALID_SK = 9
STATUS_INVALID_API_KEY = 10
STATUS_OFFLINE = 11
STATUS_SUBSCRIBERS_ONLY = 12
STATUS_INVALID_SIGNATURE = 13
STATUS_TOKEN_UNAUTHORIZED = 14
STATUS_TOKEN_EXPIRED = 15

EVENT_ATTENDING = '0'
EVENT_MAYBE_ATTENDING = '1'
EVENT_NOT_ATTENDING = '2'

PERIOD_OVERALL = 'overall'
PERIOD_3MONTHS = '3month'
PERIOD_6MONTHS = '6month'
PERIOD_12MONTHS = '12month'

IMAGE_SMALL = 0
IMAGE_MEDIUM = 1
IMAGE_LARGE = 2
IMAGE_EXTRA_LARGE = 3

DOMAIN_ENGLISH = 'www.last.fm'
DOMAIN_GERMAN = 'www.lastfm.de'
DOMAIN_SPANISH = 'www.lastfm.es'
DOMAIN_FRENCH = 'www.lastfm.fr'
DOMAIN_ITALIAN = 'www.lastfm.it'
DOMAIN_POLISH = 'www.lastfm.pl'
DOMAIN_PORTUGUESE = 'www.lastfm.com.br'
DOMAIN_SWEDISH = 'www.lastfm.se'
DOMAIN_TURKISH = 'www.lastfm.com.tr'
DOMAIN_RUSSIAN = 'www.lastfm.ru'
DOMAIN_JAPANESE = 'www.lastfm.jp'
DOMAIN_CHINESE = 'cn.last.fm'

USER_MALE = 'Male'
USER_FEMALE = 'Female'

def md5(text):
	hash = hashlib.md5()
	hash.update(text.encode('utf-8'))
	
	return hash.hexdigest()

def GetAuthenticatedUser(api_key, api_secret, session_key):
	"""Returns the authenticated user."""
	
	return AuthenticatedUser(api_key, api_secret, session_key)

class ServiceException(Exception):
	"""Exception related to the Last.fm web service"""
	
	def __init__(self, lastfm_status, details):
		self._lastfm_status = lastfm_status
		self._details = details
	
	def __str__(self):
		return self._details
	
	def getID(self):
		"""Returns the exception ID, from one of the following:
			STATUS_INVALID_SERVICE = 2
			STATUS_INVALID_METHOD = 3
			STATUS_AUTH_FAILED = 4
			STATUS_INVALID_FORMAT = 5
			STATUS_INVALID_PARAMS = 6
			STATUS_INVALID_RESOURCE = 7
			STATUS_TOKEN_ERROR = 8
			STATUS_INVALID_SK = 9
			STATUS_INVALID_API_KEY = 10
			STATUS_OFFLINE = 11
			STATUS_SUBSCRIBERS_ONLY = 12
			STATUS_TOKEN_UNAUTHORIZED = 14
			STATUS_TOKEN_EXPIRED = 15
		"""
		
		return self._lastfm_status

class _ThreadedFunct(threading.Thread):
	"""A class used by _Asynchronizer."""
	
	def __init__(self, sender, funct, funct_args, callback, callback_args):
		threading.Thread.__init__(self)
		
		self.funct = funct
		self.funct_args = funct_args
		self.callback = callback
		self.callback_args = callback_args
		
		self.sender = sender
	
	def run(self):
		if self.funct:
			if self.funct_args:
				output = self.funct(*self.funct_args)
			else:
				output = self.funct()
				
		if self.callback:
			if self.callback_args:
				self.callback(self.sender, output, *self.callback_args)
			else:
				self.callback(self.sender, output)

class _Asynchronizer(object):
	"""This class helps performing asynchronous operations less painfully."""
	
	def async_call(self, call, callback = None, call_args = None, callback_args = None):
		"""This is the function for setting up an asynchronous operation.
		* call: The function to call asynchronously.
		* callback: The function to call after the operation is complete.
		* call_args: A sequence of args to be passed to call.
		* callback_args: A sequence of args to be passed to callback.
		"""
		
		thread = _ThreadedFunct(self, call, call_args, callback, callback_args)
		thread.start()
	
class _Request(object):
	"""Representing an abstract web service operation."""
	
	def __init__(self, method_name, params, api_key, secret = None, session_key = None):

		self.params = params		
		self.secret = secret
		
		self.params['api_key'] = api_key
		self.params['method'] = method_name
		
		if session_key:
			self.signIt()
	
	def signIt(self):
		"""Sign this request."""
		
		if not "api_sig" in self.params.keys():
			self.params['api_sig'] = self._getSignature()
	
	def _getSignature(self):
		"""Returns a 32-character hexadecimal md5 hash of the signature string."""
		
		keys = self.params.keys()[:]
		
		keys.sort()
		
		string = unicode()
		
		for name in keys:
			string += name
			string += self.params[name]
		
		string += self.secret
		
		return md5(string.encode('utf-8'))
	
	def execute(self):
		"""Returns the XML DOM response of the POST Request from the server"""
		
		data = []
		for name in self.params.keys():
			data.append('='.join((name, urllib.quote_plus(self.params[name].encode('utf-8')))))
		data = '&'.join(data)
		
		headers = {
			"Content-type": "application/x-www-form-urlencoded",
			'Accept-Charset': 'utf-8',
			'User-Agent': __name__ + '/' + __version__
			}		
		
		if PROXY:
			conn = httplib.HTTPConnection(host=PROXY[0], port=PROXY[1])
			conn.request(method='POST', url="http://" + HOST_NAME + HOST_SUBDIR, 
				body=data, headers=headers)
		else:
			conn = httplib.HTTPConnection(host=HOST_NAME)
			conn.request(method='POST', url=HOST_SUBDIR, body=data, headers=headers)
		
		response = conn.getresponse()
			
		doc = minidom.parse(response)
			
		self._checkResponseStatus(doc)
		
		return doc
	
	def _checkResponseStatus(self, xml_dom):
		"""Checks the response for errors and raises one if any exists."""
		
		doc = xml_dom
		e = doc.getElementsByTagName('lfm')[0]
		
		if e.getAttribute('status') != "ok":
			e = doc.getElementsByTagName('error')[0]
			status = e.getAttribute('code')
			details = e.firstChild.data.strip()
			raise ServiceException(status, details)

class SessionGenerator(_Asynchronizer):
	"""Methods of generating a session key:
	1) Web Authentication:
		a. sg = SessionGenerator(API_KEY, API_SECRET)
		b. url = sg.getWebAuthURL()
		c. Ask the user to open the url and authorize you, and wait for it.
		d. session_key = sg.getWebAuthSessionKey(url)
	2) Username and Password Authentication:
		a. username = raw_input("Please enter your username: ")
		b. md5_password = pylast.md5(raw_input("Please enter your password: ")
		c. session_key = SessionGenerator(API_KEY, API_SECRET).getSessionKey(username, md5_password)
	
	A session key's lifetime is infinie, unless the user provokes the rights of the given API Key.
	"""
	
	def __init__(self, api_key, secret):
		_Asynchronizer.__init__(self)
		
		self.api_key = api_key
		self.secret = secret
		self.web_auth_tokens = {}
	
	def _getWebAuthToken(self):
		"""Retrieves a token from Last.fm for web authentication.
		The token then has to be authorized from getAuthURL before creating session.
		"""
		
		request = _Request('auth.getToken', dict(), self.api_key, self.secret)
		request.signIt()
		
		doc = request.execute()
		
		e = doc.getElementsByTagName('token')[0]
		return e.firstChild.data
	
	def getWebAuthURL(self):
		"""The user must open this page, and you first, then call getWebAuthSessionKey(url) after that."""
		
		token = self._getWebAuthToken()
		
		url = 'http://www.last.fm/api/auth/?api_key=%(api)s&token=%(token)s' % \
			{'api': self.api_key, 'token': token}
		
		self.web_auth_tokens[url] = token
		
		return url

	def getWebAuthSessionKey(self, url):
		"""Retrieves the session key of a web authorization process by its url."""
		
		if url in self.web_auth_tokens.keys():
			token = self.web_auth_tokens[url]
		else:
			token = ""	#that's gonna raise a ServiceException of an unauthorized token when the request is executed.
		
		request = _Request('auth.getSession', {'token': token}, self.api_key, self.secret)
		request.signIt()
		
		doc = request.execute()
		
		return doc.getElementsByTagName('key')[0].firstChild.data
	
	def getSessionKey(self, username, md5_password):
		"""Retrieve a session key with a username and a md5 hash of the user's password."""
		
		params = {"username": username, "authToken": md5(username + md5_password)}
		request = _Request("auth.getMobileSession", params, self.api_key, self.secret)
		request.signIt()
		
		doc = request.execute()
		
		return doc.getElementsByTagName('key')[0].firstChild.data

class _BaseObject(_Asynchronizer):
	"""An abstract webservices object."""
		
	def __init__(self, api_key, secret, session_key):
		_Asynchronizer.__init__(self)
		
		self.api_key = api_key
		self.secret = secret
		self.session_key = session_key
		
		self.auth_data = (self.api_key, self.secret, self.session_key)
	
	def _extract(self, node, name, index = 0):
		"""Extracts a value from the xml string"""
		
		nodes = node.getElementsByTagName(name)
		
		if len(nodes):
			if nodes[index].firstChild:
				return nodes[index].firstChild.data.strip()
		else:
			return None
	
	def _extract_all(self, node, name, limit_count = None):
		"""Extracts all the values from the xml string. returning a list."""
		
		list = []
		
		for i in range(0, len(node.getElementsByTagName(name))):
			if len(list) == limit_count:
				break
			
			list.append(self._extract(node, name, i))
		
		return list
	
	def _get_url_safe(self, text):
		
		if type(text) == type(unicode()):
			text = text.encode('utf-8')
		
		return urllib.quote_plus(urllib.quote_plus(text))

	def _getFromInfo(self, *key_names):
		"""Returns the cached collection of info regarding this object
		If not available in cache, it will be downloaded first.
		"""
		
		value_or_container = self._getInfo()
		for key in key_names:
			
			if not len(value_or_container):
				return None
			
			value_or_container = value_or_container[key]
		
		return value_or_container

	def toStr():
		return ""
	
	def _hash(self):
		return self.toStr().lower()
	
	def __str__(self):
		return self.toStr()

class _Taggable(object):
	"""Common functions for classes with tags."""
	
	def __init__(self, ws_prefix):
		self.ws_prefix = ws_prefix
	
	def addTags(self, *tags):
		"""Adds one or several tags.
		* *tags: Any number of tag names or Tag objects. 
		"""
		
		for tag in tags:
			self._addTag(tag)	
	
	def _addTag(self, tag):
		"""Adds one or several tags.
		* tag: one tag name or a Tag object.
		"""
		
		if isinstance(tag, Tag):
			tag = tag.getName()
		
		params = self._getParams()
		params['tags'] = unicode(tag)
		
		_Request(self.ws_prefix + '.addTags', params, *self.auth_data).execute()
	
	def _removeTag(self, single_tag):
		"""Remove a user's tag from this object."""
		
		if isinstance(single_tag, Tag):
			single_tag = single_tag.getName()
		
		params = self._getParams()
		params['tag'] = unicode(single_tag)
		
		_Request(self.ws_prefix + '.removeTag', params, *self.auth_data).execute()

	def getTags(self):
		"""Returns a list of the user-set tags to this object."""
		
		params = self._getParams()
		doc = _Request(self.ws_prefix + '.getTags', params, *self.auth_data).execute()
		
		tag_names = self._extract_all(doc, 'name')
		tags = []
		for tag in tag_names:
			tags.append(Tag(tag, *self.auth_data))
		
		return tags
	
	def removeTags(self, *tags):
		"""Removes one or several tags from this object.
		* *tags: Any number of tag names or Tag objects. 
		"""
		
		for tag in tags:
			self._removeTag(tag)
	
	def clearTags(self):
		"""Clears all the user-set tags. """
		
		self.removeTags(*(self.getTags()))
	
	def setTags(self, *tags):
		"""Sets this object's tags to only those tags.
		* *tags: any number of tag names.
		"""
		
		c_old_tags = []
		old_tags = []
		c_new_tags = []
		new_tags = []
		
		to_remove = []
		to_add = []
		
		tags_on_server = self.getTags()
		if tags_on_server == None:
			return
		
		for tag in tags_on_server:
			c_old_tags.append(tag.getName().lower())
			old_tags.append(tag.getName())
		
		for tag in tags:
			c_new_tags.append(tag.lower())
			new_tags.append(tag)
		
		for i in range(0, len(old_tags)):
			if not c_old_tags[i] in c_new_tags:
				to_remove.append(old_tags[i])
		
		for i in range(0, len(new_tags)):
			if not c_new_tags[i] in c_old_tags:
				to_add.append(new_tags[i])
		
		self.removeTags(*to_remove)
		self.addTags(*to_add)

class Album(_BaseObject, _Taggable):
	"""A Last.fm album."""
	
	def __init__(self, artist_name, album_title, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		_Taggable.__init__(self, 'album')
		
		self.artist_name = artist_name
		self.title = album_title
	
	def _getParams(self):
		return {'artist': self.artist_name, 'album': self.title, 'sk': self.session_key}

	def _getInfo(self):
		"""Returns a dictionary with various metadata values."""	
		
		params = self._getParams()
		
		doc = _Request('album.getInfo', params, *self.auth_data).execute()
		
		data = {}
		
		data['name'] = self._extract(doc, 'name')
		data['artist'] = self._extract(doc, 'artist')
		data['id'] = self._extract(doc, 'id')
		data['release_date'] = self._extract(doc, 'releasedate')
		data['images'] = self._extract_all(doc, 'image')
		data['listeners'] = self._extract(doc, 'listeners')
		data['play_count'] = self._extract(doc, 'playcount')
		
		tags_element = doc.getElementsByTagName('toptags')[0]
		data['top_tags'] = self._extract_all(tags_element, 'name')
		
		return data
	
	def getArtist(self):
		"""Returns the associated Artist object. """
		
		return Artist(self.getArtistName(), *self.auth_data)
	
	def getArtistName(self, from_server = False):
		"""Returns the artist name.
		  * from_server: If set to True, the value will be retrieved from the server.
		"""
		
		if from_server:
			return self._getFromInfo('artist')
		else:
			return self.artist_name
	
	def getTitle(self, from_server = False):
		"""Returns the album title.
		  * from_server: If set to True, the value will be retrieved from the server.
		"""
		
		if from_server:
			return self._getFromInfo('name')
		else:
			return self.title
	
	def getName(self, from_server = False):
		"""Returns the album title (alias to Album.getTitle).
		  * from_server: If set to True, the value will be retrieved from the server.
		"""
		
		return self.getTitle(from_server)
	
	def getReleaseDate(self):
		"""Retruns the release date of the album."""
		
		return self._getFromInfo('release_date')
	
	def getImage(self, size = IMAGE_EXTRA_LARGE):
		"""Returns the associated image URL.
		* size: The image size. Possible values:
		  o IMAGE_EXTRA_LARGE
		  o IMAGE_LARGE
		  o IMAGE_MEDIUM
		  o IMAGE_SMALL
		"""
		
		return self._getFromInfo('images', size)
	
	def getID(self):
		"""Returns the Last.fm ID. """
		
		return self._getFromInfo('id')
	
	def getPlayCount(self):
		"""Returns the number of plays on Last.fm."""
		
		return int(self._getFromInfo('play_count'))
	
	def getListenerCount(self):
		"""Returns the number of liteners on Last.fm."""
		
		return int(self._getFromInfo('listeners'))
	
	def getTopTags(self, limit = None):
		"""Returns a list of the most-applied tags to this album. """
		
		#Web services currently broken.
		#TODO: add getTopTagsWithCounts
		
		l = []
		for tag in self._getFromInfo('top_tags'):
			if limit and len(l) >= limit:
				break
			
			l.append(Tag(tag, *self.auth_data))
		
		return l

	def getTracks(self):
		"""Returns the list of Tracks on this album. """
		
		uri = 'lastfm://playlist/album/%s' %self.getID()
		
		return XSPF(uri, *self.auth_data).getTracks()
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the album page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		
		url = 'http://%(domain)s/music/%(artist)s/%(album)s'
		
		artist = self._get_url_safe(self.getArtist().getName())
		album = self._get_url_safe(self.getTitle())
		
		return url %{'domain': domain_name, 'artist': artist, 'album': album}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getArtist().getName().encode('utf-8') + ' - ' + self.getTitle().encode('utf-8')

class Track(_BaseObject, _Taggable):
	"""A Last.fm track."""
	
	def __init__(self, artist_name, title, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		_Taggable.__init__(self, 'track')
		
		self.artist_name = artist_name
		self.title = title
	
	def _getParams(self):
		return {'sk': self.session_key, 'artist': self.artist_name, 'track': self.title}
	
	def _getInfo(self):
		"""Returns a dictionary with vairous metadata values about this track."""
		
		params = self._getParams()
		doc = _Request('track.getInfo', params, *self.auth_data).execute()
		
		data = {}
		
		data['id'] = self._extract(doc, 'id')
		data['title'] = self._extract(doc, 'name')
		data['duration'] = self._extract(doc, 'duration')
		data['listener_count'] = self._extract(doc, 'listeners')
		data['play_count'] = self._extract(doc, 'playcount')
		data['artist_name'] = self._extract(doc, 'name', 1)
		data['album_name'] = self._extract(doc, 'title')
		data["album_artist_name"] = self._extract(doc, "artist", 1)
		data['images'] = self._extract_all(doc, 'image')
		
		tags_element = doc.getElementsByTagName('toptags')[0]
		top_tags = self._extract_all(tags_element, 'name')
		
		data['top_tags'] = []
		
		for tag in top_tags:
			data['top_tags'].append(Tag(tag, *self.auth_data))
		
		if len(doc.getElementsByTagName('wiki')) > 0:
			wiki_element = doc.getElementsByTagName('wiki')[0]
			data['wiki'] = {}
			data['wiki']['published_date'] = self._extract(wiki_element, 'published')
			data['wiki']['summary'] = self._extract(wiki_element, 'summary')
			data['wiki']['content'] = self._extract(wiki_element, 'content')
		
		return data
		
	def getArtist(self, from_server = False):
		"""Returns the associated Artist object.
		  * from_server: If set to True, the artist name will be retrieved from the server.
		"""
		
		return Artist(self.getArtistName(from_server), *self.auth_data)
	
	def getArtistName(self, from_server = False):
		"""Returns the name of the artist.
		  * from_server: If set to True, the value will be retrieved from the server.
		"""
		
		if from_server:
			return self._getFromInfo('artist_name')
		else:
			return self.artist_name
	
	def getTitle(self, from_server = False):
		"""Returns the track title.
		  * from_server: If set to True, the value will be retrieved from the server.
		"""
		
		if from_server:
			return self._getFromInfo('title')
		else:
			return self.title
	
	def getName(self, from_server = False):
		"""Returns the track title (alias to Track.getTitle).
		  * from_server: If set to True, the value will be retrieved from the server.
		"""
		
		return self.getTitle(from_server)
	
	def getID(self):
		"""Returns the track id on Last.fm."""
		
		return self._getFromInfo('id')
	
	def getDuration(self):
		"""Returns the track duration."""
		
		return int(self._getFromInfo('duration'))
	
	def getListenerCount(self):
		"""Returns the listener count."""
		
		return int(self._getFromInfo('listener_count'))
	
	def getPlayCount(self):
		"""Returns the play count."""
		
		return int(self._getFromInfo('play_count'))
	
	def getAlbumName(self):
		"""Returns the name of the album."""
		
		return self._getFromInfo('album_name')
	
	def getAlbumArtistName(self):
		"""Returns the name of the album artist."""
		
		return self._getFromInfo("album_artist_name")
	
	def getAlbumArtist(self):
		"""Returns the album artist."""
		
		return Artist(self.getAlbumArtistName, *self.auth_data)
	
	def getAlbum(self):
		"""Returns the album object of this track."""
		
		if self.getAlbumName():
			return Album(self.getAlbumArtistName, self.getAlbumName(), *self.auth_data)
	
	def love(self):
		"""Adds the track to the user's loved tracks. """
		
		params = self._getParams()
		_Request('track.love', params, *self.auth_data).execute()
	
	def ban(self):
		"""Ban this track from ever playing on the radio. """
		
		params = self._getParams()
		_Request('track.ban', params, *self.auth_data).execute()
	
	def getSimilar(self):
		"""Returns similar tracks for this track on Last.fm, based on listening data. """
		
		params = self._getParams()
		doc = _Request('track.getSimilar', params, *self.auth_data).execute()
		
		tracks = doc.getElementsByTagName('track')
		
		data = []
		for track in tracks:
			extra_info = {}
			
			title = self._extract(track, 'name', 0)
			artist = self._extract(track, 'name', 1)
			
			data.append(Track(artist, title, *self.auth_data))
		
		return data
	
	def getTopFans(self, limit = None):
		"""Returns the top fans for this track on Last.fm. """
		
		pairs = self.getTopFansWithWeights(limit)
		
		list = []
		for p in pairs:
			list.append(pairs[0])
		
		return list

	def getTopFansWithWeights(self, limit = None):
		"""Returns the top fans for this track as a sequence of (User, weight). """
		
		params = self._getParams()
		doc = _Request('track.getTopFans', params, *self.auth_data).execute()
		
		list = []
		
		elements = doc.getElementsByTagName('user')
		
		for element in elements:
			if limit and len(list) >= limit:
				break
				
			name = self._extract(element, 'name')
			weight = self._extract(element, 'weight')
			
			list.append((User(name, *self.auth_data), weight))
		
		return list

	def getTopTags(self, limit = None):
		"""Returns the top tags for this track on Last.fm, ordered by tag count."""
		
		pairs = self.getTopTagsWithCounts(limit)
		
		list = []
		for pair in pairs:
			list.append(pair[0])
		
		return list

	def getTopTagsWithCounts(self, limit = None):
		"""Returns the top tags for this track on Last.fm, ordered by tag count as a sequence of (Tag, tag_count) tuples. """
		
		params = self._getParams()
		doc = _Request('track.getTopTags', params, *self.auth_data).execute()
		
		list = []
		elements = doc.getElementsByTagName('tag')
		
		for element in elements:
			if limit and len(list) >= limit:
				break
			
			tag_name = self._extract(element, 'name')
			tag_count = self._extract(element, 'count')
			
			list.append((Tag(tag_name, *self.auth_data), tag_count))
		
		return list
	
	def share(self, users, message = None):
		"""Shares this track (sends out recommendations). 
  		* users: A list that can contain usernames, emails, User objects, or all of them.
  		* message: A message to include in the recommendation message. 
		"""
		
		#last.fm currently accepts a max of 10 recipient at a time
		while(len(users) > 10):
			section = users[0:9]
			users = users[9:]
			self.share(section, message)
		
		nusers = []
		for user in users:
			if isinstance(user, User):
				nusers.append(user.getName())
			else:
				nusers.append(user)
		
		params = self._getParams()
		recipients = ','.join(nusers)
		params['recipient'] = recipients
		if message: params['message'] = unicode(message)
		
		_Request('track.share', params, *self.auth_data).execute()
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the track page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		url = 'http://%(domain)s/music/%(artist)s/_/%(title)s'
		
		artist = self._get_url_safe(self.getArtist().getName())
		title = self._get_url_safe(self.getTitle())
		
		return url %{'domain': domain_name, 'artist': artist, 'title': title}
	
	def getWikiPublishedDate(self):
		"""Returns the date of publishing the wiki content."""
		
		return self._getFromInfo('wiki', 'published_date')
	
	def getWikiContent(self):
		"""Returns the full wiki content."""
		
		return self._getFromInfo('wiki', 'content')
	
	def getWikiSummary(self):
		"""Returns the wiki summary."""
		
		return self._getFromInfo('wiki', 'summary')
	
	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getArtist().getName().encode('utf-8') + ' - ' + self.getTitle().encode('utf-8')
		
class Artist(_BaseObject, _Taggable):
	"""A Last.fm artist."""
	
	def __init__(self, artist_name, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		_Taggable.__init__(self, 'artist')
		
		self.name = artist_name
	
	def _getParams(self):
		return {'sk': self.session_key, 'artist': self.name}

	def _getInfo(self):
		"""Get the metadata for an artist on Last.fm, Includes biography"""
		
		params = self._getParams()
		doc = _Request('artist.getInfo', params, *self.auth_data).execute()
		
		data = {}
		
		data['name'] = self._extract(doc, 'name')
		data['images'] = self._extract_all(doc, 'image', 3)
		data['streamable'] = self._extract(doc, 'streamable')
		data['listeners'] = self._extract(doc, 'listeners')
		data['play_count'] = self._extract(doc, 'playcount')
		bio = {}
		bio['published'] = self._extract(doc, 'published')
		bio['summary'] = self._extract(doc, 'summary')
		bio['content'] = self._extract(doc, 'content')
		data['bio'] = bio
		
		return data
	
	def getName(self, from_server = False):
		"""Returns the name of the artist.
		  * from_server: If set to True, the value will be retrieved from the server.
		"""
		
		if from_server:
			return self._getFromInfo('name')
		else:
			return self.name
	
	def getImage(self, size = IMAGE_LARGE):
		"""Returns the associated image URL. 
		* size: The image size. Possible values:
		  o IMAGE_LARGE
		  o IMAGE_MEDIUM
		  o IMAGE_SMALL
		"""
		
		return self._getFromInfo('images', size)
	
	def getPlayCount(self):
		"""Returns the number of plays on Last.fm. """
		
		return int(self._getFromInfo('play_count'))
	
	def getListenerCount(self):
		"""Returns the number of liteners on Last.fm. """
		
		return int(self._getFromInfo('listeners'))
	
	def getBioPublishedDate(self):
		"""Returns the date on which the artist's biography was published. """
		
		return self._getFromInfo('bio', 'published')
	
	def getBioSummary(self):
		"""Returns the summary of the artist's biography. """
		
		return self._getFromInfo('bio', 'summary')
	
	def getBioContent(self):
		"""Returns the content of the artist's biography. """
		
		return self._getFromInfo('bio', 'content')
	
	def getEvents(self):
		"""Returns a list of the upcoming Events for this artist. """
		
		params = self._getParams()
		doc = _Request('artist.getEvents', params, *self.auth_data).execute()
		
		ids = self._extract_all(doc, 'id')
		
		events = []
		for id in ids:
			events.append(Event(id, *self.auth_data))
		
		return events
	
	def getSimilar(self, limit = None):
		"""Returns the similar artists on Last.fm. 
		* limit: The limit of similar artists to retrieve. 
		"""
		
		params = self._getParams()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = _Request('artist.getSimilar', params, *self.auth_data).execute()
		
		names = self._extract_all(doc, 'name')
		
		artists = []
		for name in names:
			artists.append(Artist(name, *self.auth_data))
		
		return artists
	
	def getTopAlbums(self):
		"""Returns a list of the top Albums by this artist on Last.fm. """
		
		params = self._getParams()
		doc = _Request('artist.getTopAlbums', params, *self.auth_data).execute()
		
		names = self._extract_all(doc, 'name')
		
		albums = []
		for name in names:
			albums.append(Album(self.getName(), name, *self.auth_data))
		
		return albums
	
	def getTopFans(self, limit = None):
		"""Returns a list of the Users who listened to this artist the most. """
		
		pairs = self.getTopFansWithWeights(limit)
		
		list = []
		for p in pairs:
			list.append(pairs[0])
		
		return list
	
	def getTopFansWithWeights(self, limit = None):
		"""Returns a list of the Users who listened to this artist the most as a sequence of (User, weight)."""
		
		params = self._getParams()
		doc = _Request('artist.getTopFans', params, *self.auth_data).execute()
		
		list = []
		
		elements = doc.getElementsByTagName('user')
		
		for element in elements:
			if limit and len(list) >= limit:
				break
				
			name = self._extract(element, 'name')
			weight = self._extract(element, 'weight')
			
			list.append((User(name, *self.auth_data), weight))
		
		return list
	
	def getTopTags(self, limit = None):
		"""Returns a list of the most frequently used Tags on this artist. """
		
		pairs = self.getTopTagsWithCounts(limit)
		
		list = []
		for pair in pairs:
			list.append(pair[0])
		
		return list
	
	def getTopTagsWithCounts(self, limit = None):
		"""Returns a list of tuples (Tag, tag_count) of the most frequently used Tags on this artist. """
		
		params = self._getParams()
		doc = _Request('artist.getTopTags', params, *self.auth_data).execute()
		
		elements = doc.getElementsByTagName('tag')
		list = []
		
		for element in elements:
			if limit and len(list) >= limit:
				break
			tag_name = self._extract(element, 'name')
			tag_count = self._extract(element, 'count')
			
			list.append((Tag(tag_name, *self.auth_data), tag_count))
		
		return list
	
	def getTopTracks(self):
		"""Returns a list of the most listened to Tracks by this artist. """
		
		params = self._getParams()
		doc = _Request('artist.getTopTracks', params, *self.auth_data).execute()
		
		list = []
		
		for track in doc.getElementsByTagName('track'):
			t = {}
			title = self._extract(track, 'name')
			artist = self.getName()
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list

	def share(self, users, message = None):
		"""Shares this artist (sends out recommendations). 
		* users: A list that can contain usernames, emails, User objects, or all of them.
		* message: A message to include in the recommendation message. 
		"""
		
		#last.fm currently accepts a max of 10 recipient at a time
		while(len(users) > 10):
			section = users[0:9]
			users = users[9:]
			self.share(section, message)
		
		nusers = []
		for user in users:
			if isinstance(user, User):
				nusers.append(user.getName())
			else:
				nusers.append(user)
		
		params = self._getParams()
		recipients = ','.join(nusers)
		params['recipient'] = recipients
		if message: params['message'] = unicode(message)
		
		_Request('artist.share', params, *self.auth_data).execute()
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the artist page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		
		url = 'http://%(domain)s/music/%(artist)s'
		
		artist = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'artist': artist}
	
	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName().encode('utf-8')

class Event(_BaseObject):
	"""A Last.fm event."""
	
	def __init__(self, event_id, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		
		self.id = unicode(event_id)
		self.data = {}
	
	def _getParams(self):
		return {'sk': self.session_key, 'event': self.getID()}
	
	def attend(self, attending_status):
		"""Sets the attending status.
		* attending_status: The attending status. Possible values:
		  o EVENT_ATTENDING
		  o EVENT_MAYBE_ATTENDING
		  o EVENT_NOT_ATTENDING 
		"""
		
		params = self._getParams()
		params['status'] = unicode(attending_status)
		
		doc = _Request('event.attend', params, *self.auth_data).execute()
	
	def _getInfo(self, refetch = False):
		"""Get the metadata for an event on Last.fm
		Includes attendance and lineup information"""
		
		if not self.data or refetch:
			params = self._getParams()
			
			doc = _Request('event.getInfo', params, *self.auth_data).execute()
			
			self.data = {}
			self.data['title'] = self._extract(doc, 'title')
			artists = []
			for i in range(0, len(doc.getElementsByTagName('artist'))):
				artists.append(self._extract(doc, 'artist', i))
			self.data['artists'] = artists
			self.data['headliner'] = self._extract(doc, 'headliner')
			self.data['startDate'] = self._extract(doc, 'startDate')
			
			venue = {}
			venue['name'] = self._extract(doc, 'name')
			venue['city'] = self._extract(doc, 'city')
			venue['country'] = self._extract(doc, 'country')
			venue['street'] = self._extract(doc, 'street')
			venue['postal_code'] = self._extract(doc, 'postalcode')
			
			geo = {}
			geo['lat'] = self._extract(doc, 'geo:lat')
			geo['long'] = self._extract(doc, 'geo:long')
			
			venue['geo'] = geo
			venue['time_zone'] = self._extract(doc, 'timezone')
			
			self.data['venue'] = venue
			self.data['description'] = self._extract(doc, 'description')
			self.data['images'] = self._extract_all(doc, 'image')
			self.data['attendance'] = self._extract(doc, 'attendance')
			self.data['reviews'] = self._extract(doc, 'reviews')
		
		return self.data
	
	def getStartDate(self):
		"""Returns the start date of the event as a datetime object. """
		
		startDate = self._getFromInfo('startDate')
		if startDate:
			return datetime.datetime(*time.strptime(startDate, "%a, %d %b %Y %H:%M:%S")[:6])
		else:
			return None
	
	def getID(self):
		"""Returns the id of the event on Last.fm. """
		return self.id
	
	def getTitle(self):
		"""Returns the title of the event. """
		
		return self._getFromInfo('title')
	
	def getHeadliner(self):
		"""Returns the headliner of the event. """
		
		return self._getFromInfo('headliner')
	
	def getArtists(self):
		"""Returns a list of the participating Artists. """
		
		names = self._getFromInfo('artists')
		
		artists = []
		for name in names:
			artists.append(Artist(name, *self.auth_data))
		
		return artists
	
	def getVenueName(self):
		"""Returns the name of the venue where the event is held. """
		
		return self._getFromInfo('venue', 'name')
	
	def getCityName(self):
		"""Returns the name of the city where the event is held. """
		
		return self._getFromInfo('venue', 'city')
	
	def getCountryName(self):
		"""Returns the name of the country where the event is held. """
		
		return self._getFromInfo('venue', 'country')

	def getPostalCode(self):
		"""Returns the postal code of where the event is held. """
		
		return self._getFromInfo('venue', 'postal_code')

	def getStreetName(self):
		"""Returns the name of the street where the event is held. """
		
		return self._getFromInfo('venue', 'street')
	
	def getGeoPoint(self):
		"""Returns a tuple of latitude and longitude values of where the event is held. """
		
		i = (self._getFromInfo('venue', 'geo', 'lat'), self._getFromInfo('venue', 'geo', 'long'))
		return i
	
	def getTimeZone(self):
		"""Returns the timezone of where the event is held. """
		
		return self._getFromInfo('venue', 'time_zone')
	
	def getDescription(self):
		"""Returns the description of the event. """
		
		return self._getFromInfo('description')
	
	def getImage(self, size = IMAGE_LARGE):
		"""Returns the associated image URL. 
		* size: The image size. Possible values:
		  o IMAGE_LARGE
		  o IMAGE_MEDIUM
		  o IMAGE_SMALL 
		"""
		
		return self._getFromInfo('images', size)
	
	def getAttendanceCount(self):
		"""Returns the number of attending people. """
		
		return self._getFromInfo('attendance')
	
	def getReviewCount(self):
		"""Returns the number of available reviews for this event. """
		
		return self._getFromInfo('reviews')
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the event page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		
		url = 'http://%(domain)s/event/%(id)s'
		
		return url %{'domain': domain_name, 'id': self.getID()}

	def share(self, users, message = None):
		"""Shares this event (sends out recommendations). 
  		* users: A list that can contain usernames, emails, User objects, or all of them.
  		* message: A message to include in the recommendation message. 
		"""
		
		#last.fm currently accepts a max of 10 recipient at a time
		while(len(users) > 10):
			section = users[0:9]
			users = users[9:]
			self.share(section, message)
		
		nusers = []
		for user in users:
			if isinstance(user, User):
				nusers.append(user.getName())
			else:
				nusers.append(user)
		
		params = self._getParams()
		recipients = ','.join(nusers)
		params['recipient'] = recipients
		if message: params['message'] = unicode(message)
		
		_Request('event.share', params, *self.auth_data).execute()
	
	def toStr(self):
		"""Returns a string representation of the object."""
		
		sa = ""
		artists = self.getArtists()
		for i in range(0, len(artists)):
			if i == 0:
				sa = artists[i].getName().encode('utf-8')
				continue
			elif i< len(artists)-1:
				sa += ', '
				sa += artists[i].getName().encode('utf-8')
				continue
			elif i == len(artists) - 1:
				sa += ' and '
				sa += artists[i].getName().encode('utf-8')
		
		return "%(title)s: %(artists)s at %(place)s" %{'title': self.getTitle().encode('utf-8'), 'artists': sa, 'place': self.getVenueName().encode('utf-8')}

class Country(_BaseObject):
	"""A country at Last.fm."""
	
	# TODO geo.getEvents
	
	def __init__(self, country_name, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		
		self.name = country_name
	
	def _getParams(self):
		return {'country': self.name}
	
	def __str__(self):
		return self.toStr()
	
	def getName(self):
		"""Returns the country name. """
		
		return self.name
	
	def getTopArtists(self):
		"""Returns a tuple of the most popular Artists in the country, ordered by popularity. """
		
		params = self._getParams()
		doc = _Request('geo.getTopArtists', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		names = self._extract_all(doc, 'name')
		
		artists = []
		for name in names:
			artists.append(Artist(name, *self.auth_data))
		
		return artists
	
	def getTopTracks(self, location = None):
		"""Returns a tuple of the most popular Tracks in the country, ordered by popularity. 
		* location: A metro name, to fetch the charts for (must be within the country specified).
		"""
		
		params = self._getParams()
		if location:
			params['location'] = unicode(location)
			
		doc = _Request('geo.getTopTracks', params, *self.auth_data).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('track'):
			
			title = self._extract(n, 'name')
			artist = self._extract(n, 'name', 1)
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the event page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		
		url = 'http://%(domain)s/place/%(country_name)s'
		
		country_name = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'country_name': country_name}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName().encode('utf-8')
	
class Group(_BaseObject):
	"""A Last.fm group."""
	
	def __init__(self, group_name, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		
		self.name = group_name
	
	def _getParams(self):
		return {'group': self.name}
	
	def getName(self):
		"""Returns the group name. """
		return self.name
	
	def getTopWeeklyAlbums(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Albums in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList. 
  		* from_value: The value marking the beginning of a week.
  		* to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = unicode(from_value)
			params['to'] = unicode(to_value)
		
		doc = _Request('group.getWeeklyAlbumChart', params, *self.auth_data).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('album'):
			artist = self._extract(n, 'artist')
			name = self._extract(n, 'name')
			
			list.append(Album(artist, name, *self.auth_data))
		
		return list
	
	def getTopWeeklyArtists(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Artists in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList. 
  		* from_value: The value marking the beginning of a week.
  		* to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = unicode(from_value)
			params['to'] = unicode(to_value)
		
		doc = _Request('group.getWeeklyArtistChart', params, *self.auth_data).execute()
		
		list = []
		
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list

	def getTopWeeklyTracks(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Tracks in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList. 
		* from_value: The value marking the beginning of a week.
		* to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = from_value
			params['to'] = to_value
		
		doc = _Request('group.getWeeklyTrackChart', params, *self.auth_data).execute()
		
		list = []
		for track in doc.getElementsByTagName('track'):
			artist = self._extract(track, 'artist')
			title = self._extract(track, 'name')
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list

	def getWeeklyChartList(self):
		"""Returns a list of range pairs to use with the chart methods. """
		
		params = self._getParams()
		doc = _Request('group.getWeeklyChartList', params, *self.auth_data).execute()
		
		list = []
		for chart in doc.getElementsByTagName('chart'):
			c = {}
			c['from'] = chart.getAttribute('from')
			c['to'] = chart.getAttribute('to')
			
			list.append(c)
		
		return list

	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the group page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		
		url = 'http://%(domain)s/group/%(name)s'
		
		name = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'name': name}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName().encode('utf-8')

class Library(_BaseObject):
	"""A user's Last.fm library."""
	
	def __init__(self, username, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		
		self._username = username
		
		self._albums_playcounts = {}
		self._albums_tagcounts = {}
		self._artists_playcounts = {}
		self._artists_tagcounts = {}
		self._tracks_playcounts = {}
		self._tracks_tagcounts = {}
		
		self._album_pages = None
		self._album_perpage = None
		self._artist_pages = None
		self._artist_perpage = None
		self._track_pages = None
		self._track_perpage = None

	def _getParams(self):
		return {'sk': self.session_key, 'user': self._username}
	
	def getUser(self):
		"""Returns the user who owns this library."""
		
		return User(self._username, *self.auth_data)
	
	def _get_albums_info(self):
		
		params = self._getParams()
		doc = _Request('library.getAlbums', params, *self.auth_data).execute()
		
		self._album_pages = int(doc.getElementsByTagName('albums')[0].getAttribute('totalPages'))
		self._album_perpage = int(doc.getElementsByTagName('albums')[0].getAttribute('perPage'))

	def _get_artists_info(self):
		
		params = self._getParams()
		doc = _Request('library.getArtists', params, *self.auth_data).execute()
		
		self._artist_pages = int(doc.getElementsByTagName('artists')[0].getAttribute('totalPages'))
		self._artist_perpage = int(doc.getElementsByTagName('artists')[0].getAttribute('perPage'))

	def _get_tracks_info(self):
		
		params = self._getParams()
		doc = _Request('library.getTracks', params, *self.auth_data).execute()
		
		self._track_pages = int(doc.getElementsByTagName('tracks')[0].getAttribute('totalPages'))
		self._track_perpage = int(doc.getElementsByTagName('tracks')[0].getAttribute('perPage'))

	def getAlbumsPageCount(self):
		"""Returns the number of pages you'd get when calling getAlbums. """
		
		if self._album_pages:
			return self._album_pages
		
		self._get_albums_info()
		
		return self._album_pages
	
	def getAlbumsPerPage(self):
		"""Returns the number of albums per page you'd get wen calling getAlbums. """
		
		if self._album_perpage:
			return self._album_perpage
		
		self._get_albums_info()
		
		return self._album_perpage

	def getArtistsPageCount(self):
		"""Returns the number of pages you'd get when calling getArtists(). """
		
		if self._artist_pages:
			return self._artist_pages
		
		self._get_artists_info()
		
		return self._artist_pages
	
	def getArtistsPerPage(self):
		"""Returns the number of artists per page you'd get wen calling getArtists(). """
		
		if self._artist_perpage:
			return self._artist_perpage
		
		self._get_artists_info()
		
		return self._artist_perpage

	def getTracksPageCount(self):
		"""Returns the number of pages you'd get when calling getTracks(). """
		
		if self._track_pages:
			return self._track_pages
		
		self._get_tracks_info()
		
		return self._track_pages
	
	def getTracksPerPage(self):
		"""Returns the number of tracks per page you'd get wen calling getTracks. """
		
		if self._track_perpage:
			return self._track_perpage
		
		self._get_tracks_info()
		
		return self._track_perpage
	
	def getAlbums(self, limit = None, page = None):
		"""Returns a paginated list of all the albums in a user's library. 
		* limit: The number of albums to retrieve.
		* page: The page to retrieve (default is the first one). 
		"""
		
		params = self._getParams()
		if limit: params['limit'] = unicode(limit)
		if page: params['page'] = unicode(page)
		
		doc = _Request('library.getAlbums', params, *self.auth_data).execute()
		
		albums = doc.getElementsByTagName('album')
		list = []
		
		for album in albums:
			artist = self._extract(album, 'name', 1)
			name = self._extract(album, 'name')
			
			playcount = self._extract(album, 'playcount')
			tagcount = self._extract(album, 'tagcount')
			
			a = Album(artist, name, *self.auth_data)
			list.append(a)
			
			self._albums_playcounts[a._hash()] = playcount
			self._albums_tagcounts[a._hash()] = tagcount
		
		return list

	def getArtists(self, limit = None, page = None):
		"""Returns a paginated list of all the artists in a user's library. 
		* limit: The number of artists to retrieve.
		* page: The page to retrieve (default is the first one). 
		"""
		
		params = self._getParams()
		if limit: params['limit'] = unicode(limit)
		if page: params['page'] = unicode(page)
		
		doc = _Request('library.getArtists', params, *self.auth_data).execute()
		
		artists = doc.getElementsByTagName('artist')
		list = []
		
		for artist in artists:
			name = self._extract(artist, 'name')
			
			playcount = self._extract(artist, 'playcount')
			tagcount = self._extract(artist, 'tagcount')
			
			a = Artist(name, *self.auth_data)
			list.append(a)
			
			self._artists_playcounts[a._hash()] = playcount
			self._artists_tagcounts[a._hash()] = tagcount
		
		return list

	def getTracks(self, limit = None, page = None):
		"""Returns a paginated list of all the tracks in a user's library. """
		
		params = self._getParams()
		if limit: params['limit'] = unicode(limit)
		if page: params['page'] = unicode(page)
		
		doc = _Request('library.getTracks', params, *self.auth_data).execute()
		
		tracks = doc.getElementsByTagName('track')
		list = []
		
		for track in tracks:
			
			title = self._extract(track, 'name')
			artist = self._extract(track, 'name', 1)
			
			playcount = self._extract(track, 'playcount')
			tagcount = self._extract(track, 'tagcount')
			
			t = Track(artist, title, *self.auth_data)
			list.append(t)
			
			self._tracks_playcounts[t._hash()] = playcount
			self._tracks_tagcounts[t._hash()] = tagcount
		
		return list
	
	def getAlbumPlaycount(self, album_object):
		"""Goes through the library until it finds the playcount of this album and returns it (could take a relatively long time). 
		* album_object : The Album to find. 
		"""
		
		key = album_object._hash()
		if key in self._albums_playcounts.keys():
			return self._albums_playcounts[key]
		
		for i in range(1, self.getAlbumsPageCount() +1):
			stack = self.getAlbums(page = i)
			
			for album in stack:
				if album._hash() == album_object._hash():
					return self._albums_playcounts[album._hash()]

	def getAlbumTagcount(self, album_object):
		"""Goes through the library until it finds the tagcount of this album and returns it (could take a relatively long time). 
		* album_object : The Album to find. 
		"""
		
		key = album_object._hash()
		if key in self._albums_tagcounts.keys():
			return self._albums_tagcounts[key]
		
		for i in range(1, self.getAlbumsPageCount() +1):
			stack = self.getAlbums(page = i)
			
			for album in stack:
				if album._hash() == album_object._hash():
					return self._albums_tagcounts[album._hash()]

	def getArtistPlaycount(self, artist_object):
		"""Goes through the library until it finds the playcount of this artist and returns it (could take a relatively long time). 
		* artist_object : The Artist to find. 
		"""
		
		key = artist_object._hash()
		if key in self._artists_playcounts.keys():
			return self._artists_playcounts[key]
		
		for i in range(1, self.getArtistsPageCount() +1):
			stack = self.getArtists(page = i)
			
			for artist in stack:
				if artist._hash() == artist_object._hash():
					return self._artists_playcounts[artist._hash()]

	def getArtistTagcount(self, artist_object):
		"""Goes through the library until it finds the tagcount of this artist and returns it (could take a relatively long time). 
		* artist_object : The Artist to find. 
		"""
		
		key = artist_object._hash()
		if key in self._artists_tagcounts.keys():
			return self._artists_tagcounts[key]
		
		for i in range(1, self.getArtistsPageCount() +1):
			stack = self.getArtist(page = i)
			
			for artist in stack:
				if artist._hash() == artist_object._hash():
					return self._artists_tagcounts[artist._hash()]

	def getTrackPlaycount(self, track_object):
		"""Goes through the library until it finds the playcount of this track and returns it (could take a relatively long time). 
		* track_object : The Track to find. 
		"""
		
		key = track_object._hash()
		if key in self._tracks_playcounts.keys():
			return self._tracks_playcounts[key]
		
		for i in range(1, self.getTracksPageCount() +1):
			stack = self.getTracks(page = i)
			
			for track in stack:
				if track._hash() == track_object._hash():
					return self._tracks_playcounts[track._hash()]

	def getTrackTagcount(self, track_object):
		"""Goes through the library until it finds the tagcount of this track and returns it (could take a relatively long time). 
		* track_object : The Track to find. 
		"""
		
		key = track_object._hash()
		if key in self._tracks_tagcounts.keys():
			return self._tracks_tagcounts[key]
		
		for i in range(1, self.getTracksPageCount() +1):
			stack = self.getTracks(page = i)
			
			for track in stack:
				if track._hash() == track_object._hash():
					return self._tracks_tagcounts[track._hash()]
	
	def addAlbum(self, album):
		"""Add an album to a user's Last.fm library. """
		
		params = self._getParams()
		params['artist'] = album.getArtist().getName()
		params['album'] = album.getName()
		
		_Request('library.addAlbum', params, *self.auth_data).execute()
	
	def addArtist(self, artist):
		"""Add an artist to a user's Last.fm library."""
		
		if isinstance(artist, Artist):
			artist = artist.getName()
		
		params = self._getParams()
		params['artist'] = artist
		
		_Request('library.addArtist', params, *self.auth_data).execute()
	
	def addTrack(self, track):
		"""Add a track to a user's Last.fm library."""
		
		params = self._getParams()
		params['artist'] = track.getArtistName()
		params['track'] = track.getTitle()
		
		_Request('library.addTrack', params, *self.auth_data).execute()

class XSPF(_BaseObject):
	"A Last.fm XSPF playlist."""
	
	def __init__(self, playlist_uri, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		
		self._playlist_uri = playlist_uri
	
	def _getParams(self):
		return {'playlistURL': self._playlist_uri}
	
	def getPlaylistURI(self):
		"""Returns the Last.fm playlist URI. """
		
		return self._playlist_uri
	
	def getTracks(self):
		"""Returns the tracks on this playlist."""
		
		params = self._getParams()
		
		doc = _Request('playlist.fetch', params, *self.auth_data).execute()
		
		data = {}
		
		data['title'] = self._extract(doc, 'title')
		list = []
		
		for n in doc.getElementsByTagName('track'):
			title = self._extract(n, 'title')
			artist = self._extract(n, 'creator')
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getPlaylistURI()

class Tag(_BaseObject):
	"""A Last.fm object tag."""
	
	# TODO: getWeeklyArtistChart (too lazy, i'll wait for when someone requests it)
	
	def __init__(self, tag_name, api_key, secret, session_key):
		_BaseObject.__init__(self, api_key, secret, session_key)
		
		self.name = tag_name
	
	def _getParams(self):
		return {'tag': self.name}
	
	def getName(self):
		"""Returns the name of the tag. """
		
		return self.name

	def getSimilar(self):
		"""Returns the tags similar to this one, ordered by similarity. """
		
		params = self._getParams()
		doc = _Request('tag.getSimilar', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		list = []
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(Tag(name, *self.auth_data))
		
		return list
	
	def getTopAlbums(self):
		"""Returns a list of the top Albums tagged by this tag, ordered by tag count. """
		
		params = self._getParams()
		doc = _Request('tag.getTopAlbums', params, *self.auth_data).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('album'):
			name = self._extract(n, 'name')
			artist = self._extract(n, 'name', 1)
			
			list.append(Album(artist, name, *self.auth_data))
		
		return list
	
	def getTopArtists(self):
		"""Returns a list of the top Artists tagged by this tag, ordered by tag count. """
		
		params = self._getParams()
		doc = _Request('tag.getTopArtists', params, *self.auth_data).execute()
		
		list = []
		
		names = self._extract_all(doc, 'name')
		
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list
	
	def getTopTracks(self):
		"""Returns a list of the top Tracks tagged by this tag, ordered by tag count. """
		
		params = self._getParams()
		doc = _Request('tag.getTopTracks', params, *self.auth_data).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('track'):
			title = self._extract(n, 'name')
			artist = self._extract(n, 'name', 1)
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def fetchPlaylist(self, free_tracks_only = False):
		"""Returns lit of the tracks tagged by this tag. 
		* free_tracks_only: Set to True to include only free tracks. 
		"""
		
		uri = 'lastfm://playlist/tag/%s' %self.getName()
		if free_tracks_only:
			uri += '/freetracks'
		
		return XSPF(uri, *self.auth_data).getTracks()

	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the tag page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		
		url = 'http://%(domain)s/tag/%(name)s'
		
		name = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'name': name}

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName().encode('utf-8')

class User(_BaseObject):
	"""A Last.fm user."""
	
	def __init__(self, user_name, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self.name = user_name
	
	def _getParams(self):
		return {'sk': self.session_key, "user": self.getName()}
		
	def getName(self):
		"""Returns the nuser name."""
		
		return self.name
	
	def getEvents(self):
		"""Returns all the upcoming events for this user. """
		
		params = self._getParams()
		doc = _Request('user.getEvents', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		ids = self._extract_all(doc, 'id')
		events = []
		
		for id in ids:
			events.append(Event(id, *self.auth_data))
		
		return events
	
	def getFriends(self, limit = None):
		"""Returns a list of the user's friends. """
		
		params = self._getParams()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = _Request('user.getFriends', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		list = []
		users = doc.getElementsByTagName('user')
		
		names = self._extract_all(doc, 'name')
		
		for name in names:
			list.append(User(name, *self.auth_data))
		
		return list
	
	def getLovedTracks(self):
		"""Returns the last 50 tracks loved by this user. """
		
		params = self._getParams()
		doc = _Request('user.getLovedTracks', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		list = []
		
		for track in doc.getElementsByTagName('track'):
			title = self._extract(track, 'name', 0)
			artist = self._extract(track, 'name', 1)
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def getNeighbours(self, limit = None):
		"""Returns a list of the user's friends. 
		* limit: A limit for how many neighbours to show. 
		"""
		
		params = self._getParams()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = _Request('user.getNeighbours', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		list = []
		names = self._extract_all(doc, 'name')
		
		for name in names:
			list.append(User(name, *self.auth_data))
		
		return list
	
	def getPastEvents(self, limit = None, page = None):
		"""Retruns a paginated list of all events a user has attended in the past.
		* limit: The limit number of events to return.
		* page: The page of results to return.
		"""
		
		params = self._getParams()
		if limit:
			params['limit'] = unicode(limit)
		if page:
			params['page'] = unicode(page)
		
		doc = _Request('user.getPastEvents', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		ids = self._extract_all(doc, 'id')
		list = []
		
		for id in ids:
			list.append(Event(id, *self.auth_data))
		
		return list
	
	def getPlaylists(self):
		"""Returns a list of Playlists that this user owns."""
		
		data = self.getPlaylistsData()
		
		ids = []
		for p in data:
			ids.append(p['id'])
		
		playlists = []
		
		for id in ids:
			playlists.append(UserPlaylist(self.getName(), id, *self.auth_data))
		
		return playlists
	
	def getPlaylistsData(self):
		"""Returns a list of dictionaries for each playlist. """
		
		params = self._getParams()
		doc = _Request('user.getPlaylists', params, *self.auth_data).execute()
		
		list = []		
		for playlist in doc.getElementsByTagName('playlist'):
			p = {}
			p['id'] = self._extract(playlist, 'id')
			p['title'] = self._extract(playlist, 'title')
			p['date'] = self._extract(playlist, 'date')
			p['size'] = int(self._extract(playlist, 'size'))
			p['description'] = self._extract(playlist, 'description')
			p['duration'] = self._extract(playlist, 'duration')
			p['streamable'] = self._extract(playlist, 'streamable')
			p['images'] = self._extract_all(playlist, 'image')
			p['url_appendix'] = self._extract(playlist, 'url')[19:]
			
			list.append(p)
		
		return list
	
	def getNowPlaying(self):
		"""Returns the currently playing track, or None if nothing is playing. """
		
		params = self._getParams()
		params['limit'] = '1'
		
		list = []
		
		doc = _Request('user.getRecentTracks', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		e = doc.getElementsByTagName('track')[0]
		
		if not e.hasAttribute('nowplaying'):
			return None
		
		artist = self._extract(e, 'artist')
		title = self._extract(e, 'name')
		
		return Track(artist, title, *self.auth_data)


	def getRecentTracks(self, limit = None):
		"""Returns this user's recent listened-to tracks. """
		
		params = self._getParams()
		if limit:
			params['limit'] = unicode(limit)
		
		list = []
		
		doc = _Request('user.getRecentTracks', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		for track in doc.getElementsByTagName('track'):
			title = self._extract(track, 'name')
			artist = self._extract(track, 'artist')
			
			if track.hasAttribute('nowplaying'):
				continue	#to prevent the now playing track from sneaking in here
				
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def getTopAlbums(self, period = PERIOD_OVERALL):
		"""Returns the top albums listened to by a user. 
		* period: The period of time. Possible values:
		  o PERIOD_OVERALL
		  o PERIOD_3MONTHS
		  o PERIOD_6MONTHS
		  o PERIOD_12MONTHS 
		"""
		
		params = self._getParams()
		params['period'] = period
		
		doc = _Request('user.getTopAlbums', params, *self.auth_data).execute()
		
		if not doc:
			return None
		
		list = []
		for album in doc.getElementsByTagName('album'):
			name = self._extract(album, 'name')
			artist = self._extract(album, 'name', 1)
			
			list.append(Album(artist, name, *self.auth_data))
		
		return list
	
	def getTopArtists(self, period = PERIOD_OVERALL):
		"""Returns the top artists listened to by a user. 
		* period: The period of time. Possible values:
		  o PERIOD_OVERALL
		  o PERIOD_3MONTHS
		  o PERIOD_6MONTHS
		  o PERIOD_12MONTHS 
		"""
		
		params = self._getParams()
		params['period'] = period
		
		doc = _Request('user.getTopArtists', params, *self.auth_data).execute()
		
		list = []
		
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list
	
	def getTopTags(self, limit = None):
		"""Returns a sequence of the top tags used by this user with their counts as (Tag, tag_count). 
		* limit: The limit of how many tags to return. 
		"""
		
		pairs = self.getTopTagsWithCounts(limit)
		
		list = []
		for pair in pairs:
			list.append(pair[0])
		
		return list
	
	def getTopTagsWithCounts(self, limit = None):
		"""Returns the top tags used by this user. 
		* limit: The limit of how many tags to return. 
		"""
		
		params = self._getParams()
		if limit:
			params['limit'] = unicode(limit)
		
		doc = _Request('user.getTopTags', params, *self.auth_data).execute()
		
		list = []
		elements = doc.getElementsByTagName('tag')
		
		for element in elements:
			tag_name = self._extract(element, 'name')
			tag_count = self._extract(element, 'count')
			
			list.append((Tag(tag_name, *self.auth_data), tag_count))
		
		return list
	
	def getTopTracks(self, period = PERIOD_OVERALL):
		"""Returns the top tracks listened to by a user. 
		* period: The period of time. Possible values:
		  o PERIOD_OVERALL
		  o PERIOD_3MONTHS
		  o PERIOD_6MONTHS
		  o PERIOD_12MONTHS 
		"""
		
		params = self._getParams()
		params['period'] = period
		
		doc = _Request('user.getTopTracks', params, *self.auth_data).execute()
		
		list = []
		for track in doc.getElementsByTagName('track'):
			title = self._extract(track, 'name')
			artist = self._extract(track, 'name', 1)
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def getTopWeeklyAlbums(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Albums in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList(). 
		* from_value: The value marking the beginning of a week.
		* to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = from_value
			params['to'] = to_value
		
		doc = _Request('user.getWeeklyAlbumChart', params, *self.auth_data).execute()
		
		list = []
		
		for n in doc.getElementsByTagName('album'):
			artist = self._extract(n, 'artist')
			name = self._extract(n, 'name')
			
			list.append(Album(artist, name, *self.auth_data))
		
		return list
	
	def getTopWeeklyArtists(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Artists in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList(). 
		* from_value: The value marking the beginning of a week.
		* to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = from_value
			params['to'] = to_value
		
		doc = _Request('user.getWeeklyArtistChart', params, *self.auth_data).execute()
		
		list = []
		
		names = self._extract_all(doc, 'name')
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list
	
	def getTopWeeklyTracks(self, from_value = None, to_value = None):
		"""Returns a tuple of the most frequently listened to Tracks in a week range. If no date range is supplied, it will return the most recent week's data. You can obtain the available ranges from getWeeklyChartList(). 
		* from_value: The value marking the beginning of a week.
		* to_value: The value marking the end of a week. 
		"""
		
		params = self._getParams()
		if from_value and to_value:
			params['from'] = from_value
			params['to'] = to_value
		
		doc = _Request('user.getWeeklyTrackChart', params, *self.auth_data).execute()
		
		list = []
		for track in doc.getElementsByTagName('track'):
			artist = self._extract(track, 'artist')
			title = self._extract(track, 'name')
			
			
			list.append(Track(artist, title, *self.auth_data))
		
		return list
	
	def getWeeklyChartList(self):
		"""Returns a list of range pairs to use with the chart methods."""
		
		params = self._getParams()
		doc = _Request('user.getWeeklyChartList', params, *self.auth_data).execute()
		
		list = []
		for chart in doc.getElementsByTagName('chart'):
			c = {}
			c['from'] = chart.getAttribute('from')
			c['to'] = chart.getAttribute('to')
			
			list.append(c)
		
		return list
	
	def compareWithUser(self, user, shared_artists_limit = None):
		"""Compare this user with another Last.fm user. Returns a sequence (tasteometer_score, (shared_artist1, shared_artist2, ...))
		user: A User object or a username string/unicode object.
		"""
		
		if isinstance(user, User):
			user = user.getName()
		
		params = self._getParams()
		if shared_artists_limit:
			params['limit'] = unicode(shared_artists_limit)
		params['type1'] = 'user'
		params['type2'] = 'user'
		params['value1'] = self.getName()
		params['value2'] = user
		
		doc = _Request('tasteometer.compare', params, *self.auth_data).execute()
		
		score = self._extract(doc, 'score')
		
		artists = doc.getElementsByTagName('artists')[0]
		shared_artists_names = self._extract_all(artists, 'name')
		
		shared_artists_list = []
		
		for name in shared_artists_names:
			shared_artists_list.append(Artist(name, *self.auth_data))
		
		return (score, shared_artists_list)
	
	def getRecommendedEvents(self, page = None, limit = None):
		"""Returns a paginated list of all events recommended to a user by Last.fm, based on their listening profile.
		* page: The page number of results to return.
		* limit: The limit of events to return.
		"""
		
		params = self._getParams()
		if page:
			params['page'] = unicode(page)
		if limit:
			params['limit'] = unicode(limit)
		
		doc = _Request('user.getRecommendedEvents', params, *self.auth_data).execute()
		
		ids = self._extract_all(doc, 'id')
		list = []
		for id in ids:
			list.append(Event(id, *self.auth_data))
		
		return list
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the user page on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		url = 'http://%(domain)s/user/%(name)s'
		
		name = self._get_url_safe(self.getName())
		
		return url %{'domain': domain_name, 'name': name}

	def getLibrary(self):
		"""Returns the associated Library object. """
		
		return Library(self.getName(), *self.auth_data)

	def toStr(self):
		"""Returns a string representation of the object."""
		
		return self.getName().encode('utf-8')

class AuthenticatedUser(User):
	def __init__(self, api_key, api_secret, session_key):
		User.__init__("", api_key, api_secret, session_key);
		
		self.name = self.getName()
	
	def _getParams(self):
		return {'sk': self.session_key}
	
	def _getInfo(self):
		"""Returns a dictionary with various metadata values."""
		
		params = self._getParams()
		doc = _Request('user.getInfo', params, *self.auth_data).execute()
		
		data = {}
		
		data['name'] = self._extract(doc, 'name')
		data['image'] = self._extract(doc, 'image')
		data['language'] = self._extract(doc, 'lang')
		data['country'] = self._extract(doc, 'country')
		data['age'] = self._extract(doc, 'age')
		data['gender'] = self._extract(doc, 'gender')
		data['subscriber'] = self._extract(doc, 'subscriber')
		data['play_count'] = self._extract(doc, 'playcount')
		
		return data
	
	def getName(self):
		"""Returns the user name."""
			
		return self._getFromInfo('name')
	
	def getImage(self):
		"""Returns the user's avatar."""
		
		return self._getFromInfo('image')
	
	def getLanguage(self):
		"""Returns the language code of the language used by the user."""
		
		return self._getFromInfo('language')
	
	def getCountryName(self):
		"""Returns the name of the country of the user."""
		
		return self._getFromInfo('country')
	
	def getAge(self):
		"""Returns the user's age."""
		
		return self._getFromInfo('age')
	
	def getGender(self):
		"""Returns the user's gender. Either USER_MALE or USER_FEMALE."""
		
		value = self._getFromInfo('gender')
		if value == 'm':
			return USER_MALE
		elif value == 'f':
			return USER_FEMALE
		
		return None
	
	def isSubscriber(self):
		"""Returns whether the user is a subscriber or not. True or False."""
		
		value = self._getFromInfo('subscriber')
		
		if value == '1':
			return True
		elif value == '0':
			return False
		
		return None
	
	def getPlayCount(self):
		"""Returns the user's playcount so far."""
		
		return int(self._getFromInfo('play_count'))

class _Search(_BaseObject):
	"""An abstract class. Use one of its derivatives."""
	
	def __init__(self, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self._limit = None
		self._page = None
		self._total_result_count = None

	def getLimit(self):
		"""Returns the limit of the Search."""
		
		return self._limit
	
	def getPage(self):
		"""Returns the last page retrieved."""
		
		return self._page
	
	def getTotalResultCount(self):
		"""Returns the total count of all the results."""
		
		return self._total_result_count
	
	def getResults(self, limit = 30, page = 1):
		pass
	
	def getFirstMatch(self):
		"""Returns the first match."""
		
		matches = self.getResults(1)
		if matches:
			return matches[0]

class ArtistSearch(_Search):
	"""Search for an artist by artist name."""
	
	def __init__(self, artist_name, api_key, api_secret, session_key):
		_Search.__init__(self, api_key, api_secret, session_key)
		
		self._artist_name = artist_name

	def _getParams(self):
		return {'sk': self.session_key, 'artist': self.getArtistName()}
		
	def getArtistName(self):
		"""Returns the artist name."""
		
		return self._artist_name

	def getResults(self, limit = 30, page = 1):
		"""Returns the matches sorted by relevance.
		* limit: Limit the number of artists returned at one time. Default (maximum) is 30.
		* page: Scan into the results by specifying a page number. Defaults to first page.
		"""
		
		params = self._getParams()
		params['limit'] = unicode(limit)
		params['page'] = unicode(page)
		
		doc = _Request('artist.Search', params, *self.auth_data).execute()
		
		self._total_result_count = self._extract(doc, 'opensearch:totalResults')
		self._page = page
		self._limit = limit
		
		e = doc.getElementsByTagName('artistmatches')[0]
		
		names = self._extract_all(e, 'name')
		
		list = []
		for name in names:
			list.append(Artist(name, *self.auth_data))
		
		return list

class AlbumSearch(_Search):
	"""Search for an album by name."""
	
	def __init__(self, album_name, api_key, api_secret, session_key):
		_Search.__init__(self, api_key, api_secret, session_key)
		
		self._album_name = album_name

	def _getParams(self):
		return {'sk': self.session_key, 'album': self.getAlbumName()}
		
	def getAlbumName(self):
		"""Returns the album name."""
		
		return self._album_name

	def getResults(self, limit = 30, page = 1):
		"""Returns the matches sorted by relevance.
		* limit: Limit the number of albums returned at one time. Default (maximum) is 30.
		* page: Scan into the results by specifying a page number. Defaults to first page.
		"""
		
		params = self._getParams()
		params['limit'] = unicode(limit)
		params['page'] = unicode(page)
		
		doc = _Request('album.search', params, *self.auth_data).execute()
		
		self._total_result_count = self._extract(doc, 'opensearch:totalResults')
		self._page = page
		self._limit = limit
		
		e = doc.getElementsByTagName('albummatches')[0]
		
		names = self._extract_all(e, 'name')
		artists = self._extract_all(e, 'artist')
		
		list = []
		for i in range(0, len(names)):
			list.append(Album(artists[i], names[i], *self.auth_data))
		
		return list

class Playlist(_BaseObject):
	"""A Last.fm user playlist."""
	
	def __init__(self, username, playlist_id, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
		
		self._username = username
		self._playlist_id = unicode(playlist_id)

	def _getInfo(self):
		
		playlists = self.getUser().getPlaylistsData()
		data = None
		
		for p in playlists:
			if p['id'] == self.getPlaylistID():
				data = p
		
		return data
	
	def _getParams(self):
		return {'sk': self.session_key, 'user': self._username, 'playlistID': self._playlist_id}
	
	def getPlaylistID(self):
		"""Returns the playlist id."""
		
		return self._playlist_id
	
	def getUser(self):
		"""Returns the owner user of this playlist."""
		
		return User(self._username, *self.auth_data)
	
	def getTracks(self):
		"""Returns a list of the tracks on this user playlist."""
		
		uri = u'lastfm://playlist/%s' %unicode(self.getPlaylistID())
		
		return XSPF(uri, *self.auth_data).getTracks()
	
	def addTrack(self, track):
		"""Adds a Track to this Playlist.
		* track: Any Track object.
		"""
		
		params = self._getParams()
		params['artist'] = track.getArtist().getName()
		params['track'] = track.getTitle()
		
		_Request('playlist.addTrack', params, *self.auth_data).execute()
		
		print self.last_error()
	
	def getTitle(self):
		"""Returns the title of this playlist."""
		
		return self._getFromInfo('title')
	
	def getCreationDate(self):
		"""Returns the creation date of this playlist."""
		
		return self._getFromInfo('date')
	
	def getSize(self):
		"""Returns the size of this playlist."""
		
		return int(self._getFromInfo('size'))
	
	def getDescription(self):
		"""Returns the description of this playlist."""
		
		return self._getFromInfo('description')
	
	def getDuration(self):
		"""Returns the duration of this playlist."""
		
		return int(self._getFromInfo('duration'))
	
	def isStreamable(self):
		"""Returns True if the playlist is streamable.
		For a playlist to be streamable, it needs at least 45 tracks by 15 different artists."""
		
		if self._getFromInfo('streamable') == '1':
			return True
		else:
			return False
	
	def hasTrack(self, track):
		"""Checks to see if track is already in the playlist.
		* track: Any Track object.
		"""
		
		tracks = self.getTracks()
		
		if not tracks:
			return False
		
		has_it = False
		for t in tracks:
			if track._hash() == t._hash():
				has_it = True
				break
		
		return has_it

	def getImage(self, size = IMAGE_LARGE):
		"""Returns the associated image URL.
		* size: The image size. Possible values:
		  o IMAGE_LARGE
		  o IMAGE_MEDIUM
		  o IMAGE_SMALL
		"""
		
		return self._getFromInfo('images', size)
	
	def getURL(self, domain_name = DOMAIN_ENGLISH):
		"""Returns the url of the playlist on Last.fm. 
		* domain_name: Last.fm's language domain. Possible values:
		  o DOMAIN_ENGLISH
		  o DOMAIN_GERMAN
		  o DOMAIN_SPANISH
		  o DOMAIN_FRENCH
		  o DOMAIN_ITALIAN
		  o DOMAIN_POLISH
		  o DOMAIN_PORTUGUESE
		  o DOMAIN_SWEDISH
		  o DOMAIN_TURKISH
		  o DOMAIN_RUSSIAN
		  o DOMAIN_JAPANESE
		  o DOMAIN_CHINESE 
		"""
		url = 'http://%(domain)s/%(appendix)s'
		
		return url %{'domain': domain_name, 'appendix': self._getFromInfo('url_appendix')}


class PlaylistCreator(_BaseObject):
	"""Used to create playlists for the authenticated user."""
	
	def __init__(self, api_key, api_secret, session_key):
		_BaseObject.__init__(self, api_key, api_secret, session_key)
	
	def _getParams(self):
		return {'sk': self.session_key}
	
	def create(self, title, description):
		"""Creates a playlist for the authenticated user and returns it.
		* title: The title of the new playlist.
		* description: The description of the new playlist.
		"""
		
		params = self._getParams()
		
		params['title'] = unicode(title)
		params['description'] = unicode(description)
		
		doc = _Request('playlist.create', params, *self.auth_data).execute()
		
		id = self._extract(doc, 'id')
		user = doc.getElementsByTagName('playlists')[0].getAttribute('user')
		
		return Playlist(user, id, *self.auth_data)
	
	
class TagSearch(_Search):
	"""Search for a tag by tag name."""
	
	def __init__(self, tag_name, api_key, api_secret, session_key):
		_Search.__init__(self, api_key, api_secret, session_key)
		
		self._tag_name = tag_name

	def _getParams(self):
		return {'sk': self.session_key, 'tag': self.getTagName()}
		
	def getTagName(self):
		"""Returns the tag name."""
		
		return self._tag_name

	def getResults(self, limit = 30, page = 1):
		"""Returns the matches sorted by relevance.
		* limit: Limit the number of artists returned at one time. Default (maximum) is 30.
		* page: Scan into the results by specifying a page number. Defaults to first page.
		"""
		
		params = self._getParams()
		params['limit'] = unicode(limit)
		params['page'] = unicode(page)
		
		doc = _Request('tag.Search', params, *self.auth_data).execute()
		
		self._total_result_count = self._extract(doc, 'opensearch:totalResults')
		self._page = page
		self._limit = limit
		
		e = doc.getElementsByTagName('tagmatches')[0]
		
		names = self._extract_all(e, 'name')
		
		list = []
		for name in names:
			list.append(Tag(name, *self.auth_data))
		
		return list

class TrackSearch(_Search):
	"""Search for a track by track title. If you don't wanna narrow the results down
	by specifying the artist name, set it to None"""
	
	def __init__(self, track_title, artist_name, api_key, api_secret, session_key):
		_Search.__init__(self, api_key, api_secret, session_key)
		
		self._track_title = track_title
		self._artist_name = artist_name

	def _getParams(self):
		params = {'sk': self.session_key, 'track': self.getTrackTitle()}
		if self.getTrackArtistName():
			params['artist'] = self.getTrackArtistName()
		
		return params
		
	def getTrackTitle(self):
		"""Returns the track title."""
		
		return self._track_title
	
	def getTrackArtistName(self):
		"""Returns the artist name."""
		
		return self._artist_name

	def getResults(self, limit = 30, page = 1):
		"""Returns the matches sorted by relevance.
		* limit: Limit the number of artists returned at one time. Default (maximum) is 30.
		* page: Scan into the results by specifying a page number. Defaults to first page.
		"""
		
		params = self._getParams()
		params['limit'] = unicode(limit)
		params['page'] = unicode(page)
		
		doc = _Request('track.Search', params, *self.auth_data).execute()
		
		self._total_result_count = self._extract(doc, 'opensearch:totalResults')
		self._page = page
		self._limit = limit
		
		e = doc.getElementsByTagName('trackmatches')[0]
		
		titles = self._extract_all(e, 'name')
		artists = self._extract_all(e, 'artist')
		
		list = []
		for i in range(0, len(titles)):
			list.append(Track(artists[i], titles[i], *self.auth_data))
		
		return list
