# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import mpd

logger = logging.getLogger(__name__)

__all__ = [b"MPD"]


class MPD(object):
    def __init__(self, hostname, port):
        self.client = mpd.MPDClient()
        self.client.connect(hostname, port)

    def become_superseeded(self):
        playlistinfo = self.client.playlistinfo()
        status = self.client.status()
        self.client.clear()
        return {
            "playlist"  : [item["file"] for item in playlistinfo],
            "position"  : int(status.get("song", -1)),
            "elapsed"   : int(float(status.get("elapsed", -1))),
            "scrobbled" : (int(float(status.get("elapsed", -1))) >
                               min(int(playlistinfo[int(status.get("song"))]["time"]) / 2, 240)
                           if int(status.get("song", -1)) >= 0
                           else False)
        }

    def update(self, path):
        self.client.update(path)
