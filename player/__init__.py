# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask.ext.bootstrap import Bootstrap
from raven.contrib.flask import Sentry
import sys
from werkzeug.exceptions import HTTPException

from player.app import app
from player.celery import celery
from player.db import db
from player.models import *

import player.scripts
import player.views

Bootstrap(app)

runner = sys.argv[0].split("/")[-1]
if runner in ["celery", "gunicorn", "uwsgi"]:
    app.config["RAVEN_IGNORE_EXCEPTIONS"] = [HTTPException]
    sentry = Sentry(app, wrap_wsgi=runner != "gunicorn")
