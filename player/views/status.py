# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from ago import human
from datetime import datetime
import errno
import fcntl
from flask import *
import logging
import os

from player.app import app
from player.redis import redis

logger = logging.getLogger(__name__)


@app.route("/status")
def status():
    data = {}

    with open(os.path.join(app.config["DATA_DIR"], b"library", b"lock"), "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
            data["updating"] = False
        except IOError as e:
            if e.errno in (errno.EACCES, errno.EAGAIN):
                data["updating"] = True
            else:
                raise
    if data["updating"]:
        data["update_started"] = human(datetime.now().replace(microsecond=0) -
                                       datetime.fromtimestamp(float(redis.get("library_update:start"))).replace(microsecond=0))
        data["updater"] = {"cmdline": redis.get("library_update:updater:cmdline"),
                           "pid": int(redis.get("library_update:updater:pid"))}
        data["updating"] = (redis.get("library_update:current") or b"").decode("utf-8", "ignore")
    else:
        finish = redis.get("library_update:finish")
        if finish:
            data["last_update"] = human(datetime.now().replace(microsecond=0) -
                                        datetime.fromtimestamp(float(finish)).replace(microsecond=0))

    return render_template("status.html", **data)
