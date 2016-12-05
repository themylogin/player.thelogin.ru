# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from player.db import db
from player.lyrics import fetchers
from player.models import Lyrics

import logging

from player.lyrics import fetch_lyrics_from_url
from player.manager import manager

logger = logging.getLogger(__name__)


@manager.command
def fetch_lyrics(url):
    lyrics = fetch_lyrics_from_url(url)
    if lyrics:
        print(lyrics.text)


@manager.command
def rebuild_lyrics(fetcher_class, commit=False):
    fetcher = [fetcher for fetcher in fetchers
               if fetcher["fetcher"].__class__.__name__ == fetcher_class][0]
    for lyrics in db.session.query(Lyrics).filter(Lyrics.provider == fetcher["fetcher"].__class__.__name__):
        if lyrics.html:
            text = fetcher["fetcher"].fetch(lyrics.html)
            if text != lyrics.text:
                print "Lyrics for %s — %s were changed (%d -> %d)" % (lyrics.artist, lyrics.title,
                                                                      len(lyrics.text) if lyrics.text else -1,
                                                                      len(text) if text else -1)
                lyrics.text = text

    if commit:
        db.session.commit()
