# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask import *
import logging
import os
import urllib
from werkzeug.exceptions import Forbidden, NotFound

from player.app import app

logger = logging.getLogger(__name__)

__all__ = [b"file_path_for_serving"]


def file_path_for_serving(prefix):
    path = urllib.unquote_plus(request.environ["PATH_INFO"][len(prefix):])
    path = os.path.normpath(os.path.join(app.config["MUSIC_DIR"], path))
    if os.path.commonprefix([app.config["MUSIC_DIR"], path]) != app.config["MUSIC_DIR"]:
        raise Forbidden()
    if not os.path.exists(path):
        raise NotFound()
    return path
