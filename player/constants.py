# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import os

__all__ = [b"MUSIC_EXTENSIONS", b"IOS_MUSIC_EXTENSIONS", b"BITRATE",
           b"DATA_DIR"]

MUSIC_EXTENSIONS = ("flac", "m4a", "mp3")
IOS_MUSIC_EXTENSIONS = ("m4a", "mp3")
BITRATE = 256

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
