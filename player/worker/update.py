# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging

from player.app import app
from player.celery import cron
from player.library.update import update_library
from player.player.factory import create_player

logger = logging.getLogger(__name__)


@cron.job(hour="*", minute=0)
def periodic_update_just_in_case():
    list(update_library())

    if app.config["PLAYER"]:
        create_player(app.config["PLAYER"]).update("")
