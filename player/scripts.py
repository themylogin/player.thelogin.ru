# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
from pyramid.paster import get_appsettings, setup_logging
import sys
import time


def updates_manager():
    config_uri = sys.argv[1]

    setup_logging(config_uri)

    settings = get_appsettings(config_uri)

    from player.inotify import UpdatersManager
    from player.library import LibraryUpdater
    from player.players import create_player, PlayerUpdater

    updates_manager = UpdatersManager(settings["music_dir"])
    updates_manager.add_updater(LibraryUpdater(settings["ffmpeg"], settings["music_dir"]))
    if settings.get("player"):
        player = create_player(settings["player"])
        updates_manager.add_updater(PlayerUpdater(player))

    while True:
        time.sleep(1)


def rebuild_lyrics():
    config_uri = sys.argv[1]

    setup_logging(config_uri)

    settings = get_appsettings(config_uri)

    from sqlalchemy import engine_from_config
    from sqlalchemy.orm import sessionmaker

    from player.db import initialize_sql, Lyrics
    from player.lyrics import fetchers

    engine = engine_from_config(settings, "sqlalchemy.")
    initialize_sql(engine)
    db = sessionmaker(bind=engine)()

    fetcher = [fetcher for fetcher in fetchers if fetcher["fetcher"].__class__.__name__ == sys.argv[2]][0]
    for l in db.query(Lyrics).filter(Lyrics.provider == fetcher["fetcher"].__class__.__name__):
        if l.html:
            lyrics = fetcher["fetcher"].fetch(l.html)
            if lyrics != l.lyrics:
                print "Lyrics for %s — %s were changed (%d -> %d)" % (l.artist, l.title,
                                                                      len(l.lyrics) if l.lyrics else -1,
                                                                      len(lyrics) if lyrics else -1)
                l.lyrics = lyrics

    if sys.argv[3] == "commit":
        db.commit()
