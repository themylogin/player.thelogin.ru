# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from themyutils.celery.beat import Cron
from themyutils.flask.celery import make_celery

from player.app import app
from player.db import db

__all__ = [b"celery"]

celery = make_celery(app, db)
cron = Cron(celery)
