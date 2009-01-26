#!/usr/bin/env python
# encoding: utf-8
"""
digest.py
Generate a daily digest PDF pocketmod booklet to print out and enjoy
"""

import urllib
import copy

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle

import pylast
import digestfetch

from settings import *

PAGE_SIZE = landscape(A4)
WIDTH, HEIGHT = PAGE_SIZE

X_FRAMES = 4
Y_FRAMES = 2

FRAME_PADDING = 10

MARGINS = {
    'top': 0,
    'right': 0,
    'bottom': 0,
    'left': 0,
}

FILENAME = "digest.pdf"

def calculate_frame_dimensions():
    """Get the width and height of our frames"""
    
    frame_width = (WIDTH - MARGINS['left'] - MARGINS['right']) / X_FRAMES
    frame_height = (HEIGHT - MARGINS['top'] - MARGINS['bottom']) / Y_FRAMES
    
    return frame_width, frame_height

def setup_frames(frame_width, frame_height):
    """Build the frameset"""
    
    from reportlab.platypus import Frame
    
    frames = [
        Frame(
            (x * frame_width) + MARGINS['left'],
            (y * frame_height) + MARGINS['top'],
            frame_width, frame_height,
            id="%d-%d" % (x, y),
            showBoundary=1,
            topPadding=FRAME_PADDING,
            rightPadding=FRAME_PADDING,
            bottomPadding=FRAME_PADDING,
            leftPadding=FRAME_PADDING,
        )
        for y in range(0, Y_FRAMES)
        for x in range(0, X_FRAMES)
    ]
    return frames

def get_stylesheet():
    """Get a stylesheet for this here PDF"""
    
    from reportlab.lib.styles import ParagraphStyle, StyleSheet1
    
    stylesheet = StyleSheet1()
    stylesheet.add(ParagraphStyle(
        name="Body",
        fontName="Times-Roman",
        fontSize=8,
        leading=10,
    ))
    image_size = inch / 4
    stylesheet.add(ParagraphStyle(
        name="Event",
        fontName="Times-Roman",
        fontSize=8,
        leading=10,
        spaceAfter=10,
        leftIndent=image_size + inch/28,
        firstLineIndent=-(image_size + inch/28),
    ))
    stylesheet.add(ParagraphStyle(
        name="List",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    ))
    return stylesheet

def format_event_recommendations(style):
    """Format event recommendations fetched from Last.fm into reportlab Flowables"""
    
    events = digestfetch.lastfm_event_recommendations()
    
    paragraphs = []
    latlongs = []
    i = 0
    for e in events:
        try:
            info = e._getInfo()
            print u"•", info['title'], e.getID()
            text = u"""
<img src="%(image)s" width="%(dimension)s" height="%(dimension)s" valign="top"/>
<seq id="eventrec">. <b>%(title)s</b> %(time)s
<br/>
%(artists)s at %(venue)s %(postcode)s
""" % {
                'image': info['images'][pylast.IMAGE_SMALL],
                'dimension': inch / 4,
                'title': info['title'],
                'artists': ", ".join(info['artists']),
                'venue': info['venue']['name'],
                'postcode': info['venue']['postal_code'] or u"",
                'time': "%s %s" % (
                    info['startDate'].strftime("%a"),
                    info['startDate'].strftime("%I:%M%p").lower().lstrip('0')
                )
            }
            i = i + 1
            latlongs.append((i, "%(lat)s,%(long)s" % info['venue']['geo']))
            paragraphs.append(Paragraph(text, style["Event"]))
        except pylast.ServiceException:
            pass
    return paragraphs, latlongs

def generate_map_url(latlongs, width, height):
    """Generate a Google Static Map image URL"""
    
    marker_color = "red"
    event_map_markers = ["%s,%s%i" % (latlong, marker_color, i) for (i, latlong) in latlongs]
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
    for (line, v) in line_status.items():
        print ".",
        name, status = v
        color, bg = colors[line]
        
        table_data.append([name, status])
        row_style = [
            ('BACKGROUND', (0, row), (1, row), HexColor("#%s" % bg)),
            ('TEXTCOLOR', (0, row), (1, row), HexColor("#%s" % color)),
        ]
        table_styles.extend(row_style)
        row = row + 1
    tl = (0, 0)
    tr = (1, 0)
    br = (1, row-1)
    bl = (0, row-1)
    table_styles.extend([
        ('FONT',            tl, br, 'Helvetica'),
        ('FONTSIZE',        tl, br, 6),
        ('LEADING',         tl, br, 6),
        ('VALIGN',          tl, br, 'MIDDLE'),
        ('TOPPADDING',      tl, br, 1),
        ('RIGHTPADDING',    tl, br, 2),
        ('BOTTOMPADDING',   tl, br, 3),
        ('LEFTPADDING',     tl, br, 2),
        ('ALIGN',           tr, br, 'RIGHT'),
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
    
    return flowables

def fetch_frame_content(style, available_width, available_height):
    """Fetch content to stuff in our frames"""
    
    print "Fetching event recs"
    event_flowables, latlongs = format_event_recommendations(style)
    
    map_width = int(available_width)
    map_height = int(available_height / 3)
    
    event_map_url = generate_map_url(latlongs, map_width*2, map_height*2)
    print "Event Map URL:", event_map_url
    
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
    print "done"
    print "==================="
    
    content = {
        '1-0': {
            'page': '6 right',
            'row': 'bottom',
            'content': tube_flowables,
        },
        '2-0': {
            'page': 'Back',
            'row': 'bottom',
            'content': [Paragraph(u'Back', style["Body"])],
        },
        '3-0': {
            'page': 'Front',
            'row': 'bottom',
            'content': [Paragraph(u'Front', style["Body"])],
        },
        '0-1': {
            'page': '1 left',
            'row': 'top',
            'content': [Paragraph(u"1 left", style["Body"])],
        },
        '1-1': {
            'page': '2 right',
            'row': 'top',
            'content': event_flowables,
        },
        '2-1': {
            'page': '3 left',
            'row': 'top',
            'content': [Paragraph(u"3 left", style["Body"])],
        },
        '3-1': {
            'page': '4 right',
            'row': 'top',
            'content': [Paragraph(u"4 right", style["Body"])],
        },
        '0-0': {
            'page': '5 left',
            'row': 'bottom',
            'content': [Paragraph(u"5 left", style["Body"])],
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
    
    available_width = frame_width - FRAME_PADDING*2
    available_height = frame_height - FRAME_PADDING*2
    
    content = fetch_frame_content(stylesheet, available_width, available_height)
    
    draw_frames(digest_canvas, frames, content, row_translations)
    
    # Save and close
    digest_canvas.showPage()
    digest_canvas.save()
    
    # Open in Finder
    from subprocess import call
    call(["open", FILENAME])

if __name__ == '__main__':
    main()
