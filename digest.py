#!/usr/bin/env python
# encoding: utf-8
"""
digest.py
Generate a daily digest PDF pocketmod booklet to print out and enjoy
"""

import urllib
import copy
import datetime, time
import re
import sys

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle

import pylast
import digestfetch

from django.dateformat import DateFormat

from settings import *

PAGE_SIZE = landscape(A4)
WIDTH, HEIGHT = PAGE_SIZE

X_FRAMES = 4
Y_FRAMES = 2
SPREAD = '0-0'

FRAME_PADDING = 10

MARGINS = {
    'top': 0,
    'right': 0,
    'bottom': 0,
    'left': 0,
}


TL = (0, 0)
TR = (1, 0)
BR = (1, -1)
BL = (0, -1)

FILENAME = "output/digest.pdf"

def calculate_frame_dimensions():
    """Get the width and height of our frames"""
    
    frame_width = (WIDTH - MARGINS['left'] - MARGINS['right']) / X_FRAMES
    frame_height = (HEIGHT - MARGINS['top'] - MARGINS['bottom']) / Y_FRAMES
    
    return frame_width, frame_height

def setup_frames(frame_width, frame_height):
    """Build the frameset"""
    
    from reportlab.platypus import Frame
    
    frames = []
    for y in range(0, Y_FRAMES):
        for x in range(0, X_FRAMES):
            frame_id = "%d-%d" % (x, y)
            width = frame_width
            height = frame_height
            padding = FRAME_PADDING
            if SPREAD == frame_id:
                width *= 2
                padding = 0
            pos_x = (x * frame_width) + MARGINS['left']
            pos_y = (y * frame_height) + MARGINS['top']
            frames.append(
                Frame(
                    pos_x, pos_y,
                    width, height,
                    id=frame_id,
                    showBoundary=0,
                    topPadding=padding,
                    rightPadding=padding,
                    bottomPadding=padding,
                    leftPadding=padding,
                )
            )
    return frames

def get_stylesheet():
    """Get a stylesheet for this here PDF"""
    
    from reportlab.lib.styles import ParagraphStyle, StyleSheet1
    
    stylesheet = StyleSheet1()
    stylesheet.add(ParagraphStyle(
        name="Body",
        fontName="Times-Roman",
        fontSize=7,
        leading=8,
    ))
    image_size = inch / 4
    stylesheet.add(ParagraphStyle(
        name="Event",
        fontName="Times-Roman",
        fontSize=7,
        leading=8,
        spaceAfter=10,
        leftIndent=image_size + inch/28,
        firstLineIndent=-(image_size + inch/28),
    ))
    image_size = inch / 5
    stylesheet.add(ParagraphStyle(
        name="Twitter",
        fontName="Times-Roman",
        fontSize=7,
        leading=8,
        spaceAfter=8,
        leftIndent=image_size + inch/32,
        firstLineIndent=-(image_size + inch/32),
    ))
    stylesheet.add(ParagraphStyle(
        name="TwitterReply",
        fontName="Times-Roman",
        fontSize=7,
        leading=8,
        spaceAfter=8,
        leftIndent=image_size + inch/32,
        firstLineIndent=-(image_size + inch/32),
        textColor='red',
    ))
    stylesheet.add(ParagraphStyle(
        name="List",
        fontName="Times-Roman",
        fontSize=8,
        leading=9,
        bulletIndent=1,
    ))
    stylesheet.add(ParagraphStyle(
        name="Cal",
        fontName="Helvetica",
        fontSize=6,
        leading=8,
        textColor='white',
    ))
    stylesheet.add(ParagraphStyle(
        name="CalComment",
        fontName="Helvetica",
        fontSize=6,
        leading=6,
        textColor='black',
    ))
    stylesheet.add(ParagraphStyle(
        name="Photo",
        fontSize=1,
        leading=0,
    ))
    stylesheet.add(ParagraphStyle(
        name="PhotoCaption",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        leftIndent=5,
        borderPadding=5,
        textColor='black',
        backColor='white',
    ))

    return stylesheet

def format_event_recommendations(style):
    """Format event recommendations fetched from Last.fm into reportlab Flowables"""
    
    events = digestfetch.lastfm_event_recommendations()
    
    paragraphs = []
    latlongs = []
    i = 1
    for e in events:
        try:
            print u'• %s (%s)' % (e.getTitle(), e.getID())
            startDate = e.getStartDate()
            df = DateFormat(startDate)
            text = u"""
<img src="%(image)s" width="%(dimension)s" height="%(dimension)s" valign="top"/>
<seq id="eventrec">. <b>%(title)s</b> %(time)s - %(venue)s %(postcode)s
<br/>
%(artists)s
""" % {
                'image': e.getImage(pylast.IMAGE_SMALL),
                'dimension': inch / 4,
                'title': e.getTitle(),
                'artists': u", ".join(e._getFromInfo('artists')),
                'venue': e.getVenueName(),
                'postcode': e.getPostalCode() or u"",
                'time': df.format('D P'),
            }
            latlongs.append((i, "%s,%s" % e.getGeoPoint()))
            i += 1
            paragraphs.append(Paragraph(text, style["Event"]))
        except pylast.ServiceException:
            pass
    return paragraphs, latlongs

def generate_map_url(latlongs, width, height):
    """Generate a Google Static Map image URL"""
    
    marker_color = "red"
    event_map_markers = ["%s,%s%i" % (latlong, marker_color, i) for i, latlong in latlongs]
    event_map_url = "http://maps.google.com/staticmap?" + urllib.urlencode({
        "size": "%ix%i" % (width, height),
        "maptype": "mobile",
        "markers": "|".join(event_map_markers),
        "key": GMAPS_KEY,
        "sensor": "false"
    })
    return event_map_url

def format_tube_status(style, available_width):
    """Format Tube status fetched from TFL into reportlab Flowables"""
    
    line_status, station_status = digestfetch.tube_status()
    
    print "Processing",
    colors = digestfetch.get_tube_colors()
    
    flowables = []
    table_data = []
    table_styles = []
    row = 0
    for line, v in line_status.items():
        print ".",
        name, status = v
        color, bg = colors[line]
        
        table_data.append([name, status])
        row_style = [
            ('BACKGROUND', (0, row), (1, row), HexColor("#%s" % bg)),
            ('TEXTCOLOR', (0, row), (1, row), HexColor("#%s" % color)),
        ]
        table_styles.extend(row_style)
        row += 1
    table_styles.extend([
        ('FONT',            TL, BR, 'Helvetica'),
        ('FONTSIZE',        TL, BR, 6),
        ('LEADING',         TL, BR, 6),
        ('VALIGN',          TL, BR, 'MIDDLE'),
        ('TOPPADDING',      TL, BR, 1),
        ('RIGHTPADDING',    TL, BR, 2),
        ('BOTTOMPADDING',   TL, BR, 3),
        ('LEFTPADDING',     TL, BR, 2),
        ('ALIGN',           TR, BR, 'RIGHT'),
    ])
    fifth_width = available_width / 5
    table = Table(table_data, colWidths=(3*fifth_width, 2*fifth_width))
    table.setStyle(TableStyle(table_styles))
    flowables.append(table)
    flowables.append(Spacer(available_width, 8))
    
    for category, stations in station_status.iteritems():
        flowables.append(Paragraph(category, style["Body"]))
        for station in stations:
            print ".",
            flowables.append(Paragraph(u"<bullet>•</bullet> %s" % station.strip(), style["List"]))
    print "done"
    return flowables

def format_twitter_statuses(style):
    """Format Twitter statuses into reportlab Flowables"""
    paragraphs = []
    statuses = digestfetch.twitter_friends()
    if statuses:
        for status in statuses:
            updateDate = datetime.datetime.strptime(status['created_at'], '%a %b %d %H:%M:%S +0000 %Y')
            df = DateFormat(updateDate)
            image_text = u"""
<img src="%(image)s" width="%(dimension)s" height="%(dimension)s" valign="top"/>""" % {
                'image': status['user']['profile_image_url'],
                'dimension': inch / 5,
            }
            message_text = u"""
<b>%(user)s</b>: %(message)s (<i>%(time)s</i>)""" % {
                'user': status['user']['name'],
                'message': status['text'],
                'time': df.format('D P')
            }
            if status['in_reply_to_user_id'] == TWITTER_USERID:
                status_style = style["TwitterReply"]
            else:
                status_style = style["Twitter"]
            try:
                paragraphs.append(Paragraph(u"%s %s" % (image_text, message_text), status_style))
                print u"• %s" % status['user']['name']
            except IOError, e:
                paragraphs.append(Paragraph(message_text, status_style))
                print u"ERROR: %s" % e
                print u"! %s" % status['user']['name']
            
    return paragraphs

def format_newsgator_headlines(style):
    """Format RSS feeds from Newsgator into reportlab Flowables"""
    data = digestfetch.newsgator_headlines()
    
    print "Processing",
    flowables = []
    for entry in data.entries:
        updated = datetime.datetime.strptime(entry.updated, "%a, %d %b %Y %H:%M:%S %Z")
        df = DateFormat(updated)
        print ".",
        flowables.append(Paragraph(u"""<bullet>•</bullet> %s
<b>%s</b> (<i>%s</i>)""" % (
            entry.feedtitle,
            entry.title,
            df.format('D P'),
        ), style["List"]))
    print "done"
    return flowables

def format_gcal_events(style, available_width):
    """Form events from Google Calendar into reportlab Flowables"""
    events = digestfetch.gcal_events()
    
    print "Processing",
    flowables = []
    table_data = []
    table_styles = []
    line_styles = []
    row = 0
    weekday = ''
    for e in events:
        df = DateFormat(e['start'])
        old_weekday = weekday
        weekday = df.format('D')
        new_day = False
        if old_weekday and old_weekday != weekday:
            line_styles.append(
                ('LINEABOVE', (0, row), (1, row), 1, 'black')
            )
        
        if e['allday']:
            startstring = weekday
            formatstring = u"<b>%s</b>"
        else:
            startstring = u"%s %s" % (
                weekday,
                df.format('P'),
            )
            formatstring = u"%s"
        
        title_data = [Paragraph(formatstring % e['title'], style["Cal"])]
        
        if e['location']:
            title_data.append(Paragraph(e['location'], style["Cal"]))
        
        table_data.append([
            Paragraph(formatstring % startstring, style["Cal"]),
            title_data,
        ])
        row_style = [
            ('BACKGROUND', (0, row), (1, row), HexColor("#%s" % e['color'])),
        ]
        table_styles.extend(row_style)
        for c_row, c in enumerate(e['comments']):
            row += 1
            table_data.append([
                Paragraph(c['author'], style["CalComment"]),
                Paragraph(c['content'], style["CalComment"]),
            ])
            row_style = [
                ('BACKGROUND', (0, row+c_row), (1, row+c_row), "white"),
            ]
            table_styles.extend(row_style)
        row += 1
        print ".",
    table_styles.extend([  
        ('VALIGN',          TL, BR, 'TOP'),
        ('TOPPADDING',      TL, BR, 3),
        ('RIGHTPADDING',    TL, BR, 2),
        ('BOTTOMPADDING',   TL, BR, 1),
        ('LEFTPADDING',     TL, BR, 2),
    ])
    fifth_width = available_width / 5
    table = Table(table_data, colWidths=(1.2*fifth_width, 3.8*fifth_width), style=line_styles)
    table.setStyle(TableStyle(table_styles))
    flowables.append(table)
    print "done"
    return flowables

def format_weather(style, available_width):
    forecast_data, warning_data = digestfetch.weather()
    
    # http://www.bbc.co.uk/weather/images/symbols/57x57/3.gif
    # http://www.bbc.co.uk/weather/images/symbols/fiveday_sym/3.gif (80/65)
    image_source = forecast_data['feed']['image']['href'].replace('57x57', 'fiveday_sym')
    aspect_ratio = 65.0/80.0
    image_width = inch/2.5
    image_height = image_width * aspect_ratio
    image_cell = Paragraph(u'<img src="%(source)s" valign="middle" width="%(width)s" height="%(height)s"/>' % {
        'source': image_source,
        'width': image_width,
        'height': image_height,
    }, style['Body'])
    
    # Saturday: sunny intervals, Max Temp: 2°C (36°F), Min Temp: -2°C (28°F)
    weather_regex = re.compile(ur'([^:]+): ([^,]+), Max Temp: ([^°]+)°C [^,]+, Min Temp: ([^°]+)°C(.+)')
    table_data = []
    for i, day in enumerate(forecast_data['entries']):
        details = day['title'].strip()
        matches = weather_regex.match(details)
        if matches:
            params = {
                'day':      matches.group(1),
                'summary':  matches.group(2),
                'max_temp': matches.group(3),
                'min_temp': matches.group(4),
            }
            print u"• %s" % params['day']
            if i > 0:
                image_cell = u''
            table_data.append((
                image_cell,
                u"%(day)s: %(summary)s %(min_temp)s/%(max_temp)s°C" % params,
            ))
    
    left_width = image_width + inch/8
    table = Table(table_data, colWidths=(left_width, available_width - left_width), style=[
        ('SPAN', TL, (0, i)),
    ])
    table.setStyle(TableStyle([
        ('VALIGN',          TL, BR, 'MIDDLE'),
        ('TOPPADDING',      TL, BR, 0),
        ('RIGHTPADDING',    TL, BR, 0),
        ('BOTTOMPADDING',   TL, BR, 0),
        ('LEFTPADDING',     TL, BR, 0),
    ]))
    weather_flowables = [
        table,
        Spacer(available_width, 8),
    ]
    
    warning_regex = re.compile(ur'^(.+: )')
    warning_summmaries = []
    if warning_data['entries']:
        print "Warnings",
        for entry in warning_data['entries']:
            # ADVISORY of Heavy Snow for London & South East England
            warning_summmary = entry['summary'].strip().replace(' for %s' % MET_WEATHER_REGION_FULL, '')
            if warning_summmary not in warning_summmaries:
                print '.',
                # Block dupes
                warning_summmaries.append(warning_summmary)
                warning_date = datetime.datetime(*entry['updated_parsed'][:6])
                df = DateFormat(warning_date)
                weather_flowables.append(Paragraph(u"%s - %s" % (
                    df.format('D P'),
                    warning_summmary
                ), style['List']))
    print "done"
    return weather_flowables

def format_flickr_photo(style, width, height):
    photo, size = digestfetch.contact_photo()
    datetaken = datetime.datetime.strptime(photo.attrib['datetaken'], "%Y-%m-%d %H:%M:%S")
    df = DateFormat(datetaken)
    datestring = df.format('l F jS P')
    aspect_ratio = float(size.attrib['height']) / float(size.attrib['width'])
    height = width * aspect_ratio
    print u"• %s: %s (%s)" % (
        photo.attrib['ownername'],
        photo.attrib['title'],
        datestring
    )
    print u"- %s" % size.attrib['source']
    return [
        Paragraph(
            u"""<img src="%s" valign="top" width="%s" height="%s"/>""" % (
                size.attrib['source'],
                width,
                height,
            ),
            style["Photo"]
        ),
        Paragraph(
            u"""<b>%s</b>: %s <br/> <i>%s</i>""" % (
                photo.attrib['ownername'],
                photo.attrib['title'],
                datestring,
            ),
            style["PhotoCaption"]
        )
    ]

def fetch_frame_content(style, frame_width, frame_height):
    """Fetch content to stuff in our frames"""
    
    available_width = frame_width - FRAME_PADDING*2
    available_height = frame_height - FRAME_PADDING*2
    
    print "Fetching Flickr photo"
    flickr_flowable = format_flickr_photo(style, frame_width*2, frame_height)
    print "==================="
    
    print "Fetching weather forecast"
    weather_flowables = format_weather(style, available_width)
    print "==================="
    
    print "Fetching Google Calendar events"
    gcal_flowables = format_gcal_events(style, available_width)
    print "==================="
    
    print "Fetching event recs"
    event_flowables, latlongs = format_event_recommendations(style)
    
    map_width = int(available_width)
    map_height = int(available_height / 3)
    
    event_map_url = generate_map_url(latlongs, map_width*2, map_height*2)
    
    if event_map_url:
        event_flowables.insert(0, Spacer(map_width, map_height))
        event_flowables.insert(0, Paragraph(
            u'<img src="%s" valign="top" width="%s" height="%s"/>' % (
                event_map_url,
                map_width,
                map_height,
            ), style["Body"])
        )
    print "==================="
    
    print "Fetching tube status"
    tube_flowables = format_tube_status(style, available_width)
    print "==================="
    
    print "Fetching Twitter updates"
    twitter_flowables = format_twitter_statuses(style)
    print "==================="
    
    print "Fetching Newsgator headlines"
    newsgator_flowables = format_newsgator_headlines(style)
    print "==================="
    
    content = {
        '1-0': {
            'page': '6 right',
            'row': 'bottom',
            'content': '',
        },
        '2-0': {
            'page': 'Back',
            'row': 'bottom',
            'content': twitter_flowables,
        },
        '3-0': {
            'page': 'Front',
            'row': 'bottom',
            'content': event_flowables,
        },
        '0-1': {
            'page': '1 left',
            'row': 'top',
            'content': newsgator_flowables,
        },
        '1-1': {
            'page': '2 right',
            'row': 'top',
            'content': [Paragraph(u"2 right", style["Body"])],
        },
        '2-1': {
            'page': '3 left',
            'row': 'top',
            'content': weather_flowables + [Spacer(available_width, 8)] + gcal_flowables
        },
        '3-1': {
            'page': '4 right',
            'row': 'top',
            'content': tube_flowables,
        },
        '0-0': {
            'page': '5 left',
            'row': 'bottom',
            'content': flickr_flowable,
        },
    }
    return content

def draw_frames(canvas, frames, content, row_translation):
    """Fill our frames with content"""
    for f in frames:
        # f.drawBoundary(canvas)
        
        frame_info = content.get(f.id)
        if frame_info:
            # Rotate top row frames
            canvas.saveState()
            row = frame_info['row']
            if row is 'top':
                canvas.translate(
                    row_translation['translate_x'],
                    row_translation['translate_y']
                )
                canvas.rotate(row_translation['rotation'])
            # Render the content
            print u"Rendering frame %s (page: %s)" % (f.id, frame_info['page'])
            f.addFromList(frame_info['content'], canvas)
            canvas.restoreState()

def main():
    from reportlab.pdfgen import canvas
    
    # print u"Grid: %d × %d" % (X_FRAMES, Y_FRAMES)
    
    # print "Margins", MARGINS
    
    frame_width, frame_height = calculate_frame_dimensions()
    
    # print u"Frame size: %s × %s" % (frame_width, frame_height)
    
    # Rotation translations for second row
    row_translations = {
        'rotation': 180,
        'translate_x': WIDTH + MARGINS['left'] - MARGINS['right'],
        'translate_y': HEIGHT + MARGINS['top'] - MARGINS['bottom'] + frame_height,
    }
    
    digest_canvas = canvas.Canvas(FILENAME, pagesize=PAGE_SIZE, bottomup=1, verbosity=1)
    
    # x_list = [(x * frame_width) + MARGINS['left'] for x in range(0, X_FRAMES + 1)]
    # y_list = [(y * frame_height) + MARGINS['top'] for y in range(0, Y_FRAMES + 1)]
    # 
    # print x_list
    # print y_list
    # digest_canvas.grid(x_list, y_list)
    
    frames = setup_frames(frame_width, frame_height)
    
    stylesheet = get_stylesheet()
    
    content = fetch_frame_content(stylesheet, frame_width, frame_height)
    
    draw_frames(digest_canvas, frames, content, row_translations)
    
    # Save and close
    digest_canvas.showPage()
    digest_canvas.save()
    
    # Open in Finder
    from subprocess import call
    call(["open", FILENAME])

if __name__ == '__main__':
    main()
