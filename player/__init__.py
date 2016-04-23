# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask.ext.bootstrap import Bootstrap
import mimetypes
from raven.contrib.flask import Sentry
import sys
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

if False:
    runner = sys.argv[0].split("/")[-1]

    try:
        from themylog.client import setup_logging_handler
        setup_logging_handler("player" + ("-%s" % runner
                                          if not (runner.startswith("python") or runner == "-c")
                                          else ""))
    except ImportError:
        pass

    if app.config.get("SENTRY_DSN"):
        app.config["RAVEN_IGNORE_EXCEPTIONS"] = [HTTPException]
        sentry = Sentry(app, wrap_wsgi=runner != "gunicorn")
