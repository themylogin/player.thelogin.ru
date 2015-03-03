# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
from pyramid.paster import get_appsettings, setup_logging
import sys
import time


__all__ = []


def updates_manager():
    config_uri = sys.argv[1]

    setup_logging(config_uri)

    settings = get_appsettings(config_uri)

    from player.inotify import UpdatersManager
    from player.library import LibraryUpdater
    from player.players import create_player, PlayerUpdater

    updates_manager = UpdatersManager(settings["music_dir"])
    updates_manager.add_updater(LibraryUpdater(settings["music_dir"]))
    if settings.get("player"):
        player = create_player(settings["player"])
        updates_manager.add_updater(PlayerUpdater(player))

    while True:
        time.sleep(1)
