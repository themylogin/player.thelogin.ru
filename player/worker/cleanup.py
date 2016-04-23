# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import os
import subprocess

from player.app import app
from player.celery import cron

logger = logging.getLogger(__name__)


@cron.job(hour=0, minute=0)
def clear_cache():
    subprocess.check_call(["find", app.config["TMP_DIR"],
                           "!", "-name", ".gitkeep", "-and",
                           "-mtime", "+1",
                           "-exec", "rm", "{}", ";"])


@cron.job(hour=0, minute=0)
def clear_old_library_revisions():
    subprocess.check_call(["find", os.path.join(app.config["DATA_DIR"], b"library_revisions"),
                           "-mtime", "+30",
                           "-exec", "rm", "{}", ";"])
