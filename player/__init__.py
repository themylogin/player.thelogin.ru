# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask_bootstrap import Bootstrap
import mimetypes
from raven import Client
from raven.contrib.celery import register_logger_signal, register_signal
from raven.contrib.flask import Sentry
from werkzeug.exceptions import HTTPException

from player.app import app
from player.celery import celery
from player.db import db
from player.manager import manager
from player.models import *

import player.scripts
import player.views
import player.worker

mimetypes.init()

Bootstrap(app)

if app.config.get("SENTRY_DSN"):
    app.config["RAVEN_IGNORE_EXCEPTIONS"] = [HTTPException]
    sentry = Sentry(app)

    sentry_client = Client(app.config["SENTRY_DSN"])
    register_logger_signal(sentry_client)
    register_signal(sentry_client)
