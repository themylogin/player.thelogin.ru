# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import mpd


class MPD(object):
    def __init__(self, hostname, port):
        self.client = mpd.MPDClient()
        self.client.connect(hostname, port)

    def current_state(self):
        playlistinfo = self.client.playlistinfo()
        status = self.client.status()
        return {
            "playlist"  : [item["file"] for item in playlistinfo],
            "position"  : int(status.get("song", -1)),
            "elapsed"   : int(float(status.get("elapsed", -1))),
        }

    def update(self, path):
        self.client.update(path)
