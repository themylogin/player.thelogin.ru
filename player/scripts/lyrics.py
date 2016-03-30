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
    for l in db.query(Lyrics).filter(Lyrics.provider == fetcher["fetcher"].__class__.__name__):
        if l.html:
            lyrics = fetcher["fetcher"].fetch(l.html)
            if lyrics != l.lyrics:
                print "Lyrics for %s — %s were changed (%d -> %d)" % (l.artist, l.title,
                                                                      len(l.lyrics) if l.lyrics else -1,
                                                                      len(lyrics) if lyrics else -1)
                l.lyrics = lyrics

    if commit:
        db.commit()
