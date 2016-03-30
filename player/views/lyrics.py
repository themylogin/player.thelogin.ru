# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
from flask import *
import logging

from player.app import app
from player.db import db
from player.lyrics import get_lyrics
from player.models import Lyrics

logger = logging.getLogger(__name__)


@app.route("/lyrics/<artist>/<title>")
def lyrics(artist, title):
    lyrics = db.session.query(Lyrics).\
                filter(Lyrics.artist == artist,
                       Lyrics.title == title).\
                first()
    if lyrics is not None and lyrics.text is None and lyrics.datetime < datetime.now() - timedelta(days=7):
        db.session.delete(lyrics)
        db.session.commit()
        lyrics = None

    if lyrics is None:
        internet_lyrics = get_lyrics(artist, title)
        lyrics = Lyrics()
        lyrics.datetime = datetime.now()
        lyrics.artist   = artist
        lyrics.title    = title
        if internet_lyrics:
            lyrics.url      = internet_lyrics.url
            lyrics.html     = internet_lyrics.html
            lyrics.provider = internet_lyrics.provider
            lyrics.text     = internet_lyrics.text
        db.session.add(lyrics)
        db.session.commit()

    return Response(lyrics.text or "", headers={"Content-type": "text/plain; charset=utf-8"})
