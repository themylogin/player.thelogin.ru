# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import functools
import logging
import urlparse

from player.player.persistent import PersistentPlayer
from player.player.impls.mpd import MPD

logger = logging.getLogger(__name__)

__all__ = [b"create_player"]


def create_player(url):
    return PersistentPlayer(functools.partial(create_player_engine, url))


def create_player_engine(url):
    o = urlparse.urlparse(url)

    if o.scheme == "mpd":
        return MPD(o.hostname, o.port)

    raise ValueError("%s player engine is not supported" % o.scheme)
