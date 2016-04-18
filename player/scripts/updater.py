# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import time

from player.app import app
from player.library.update import update_library
from player.manager import manager
from player.player.factory import create_player
from player.updater import UpdatersManager

logger = logging.getLogger(__name__)


class LibraryUpdater(object):
    def update(self, updates):
        list(update_library())


class PlayerUpdater(object):
    def __init__(self, player):
        self.player = player

    def update(self, updates):
        for update in updates:
            self.player.update(update)


@manager.command
def updater():
    updates_manager = UpdatersManager(app.config["MUSIC_DIR"])

    updates_manager.add_updater(LibraryUpdater())

    updates_manager.add_updater(PlayerUpdater(create_player(app.config["LOCAL_PLAYER"])))

    while True:
        time.sleep(1)
