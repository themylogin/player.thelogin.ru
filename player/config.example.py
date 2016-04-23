# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask import request
import os

SECRET_KEY = '...'

SENTRY_DSN = None

REDIS = dict(host="redis", port=6379, db=0)

CELERY_BROKER_URL = "amqp://rabbitmq"
CELERYD_HIJACK_ROOT_LOGGER = False

SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://player:player@postgres/player"

MUSIC_BITRATE = 256
MUSIC_EXTENSIONS = (b"flac", b"m4a", b"mp3")
DIRECT_MUSIC_EXTENSIONS = (b"m4a", b"mp3")

DATA_DIR = os.path.join(os.path.dirname(__file__), b"../data")

MUSIC_DIR = b"/music"
TMP_DIR = b"/player/data/tmp"

FFMPEG = b"/usr/bin/ffmpeg"

LOCAL_PLAYER = None
LOCAL_PLAYER_ALLOWED = lambda: request.remote_addr.startswith(b"192.168.0.")

LAST_FM_THELOGIN_RU_URL = None

LIST_GENRES = lambda: sorted(
    [{"name": name,
      "path": name}
     for name in os.listdir(MUSIC_DIR)
     if os.path.isdir(os.path.join(MUSIC_DIR, name))] +
    sum([[{"name": "%s/%s" % (base, name),
           "path": "%s/%s" % (base, name)}
          for name in os.listdir(os.path.join(MUSIC_DIR, base))
          if os.path.isdir(os.path.join(MUSIC_DIR, base, name))]
         for base in ["Rave", "Rock", "Trance"]
         if os.path.isdir(os.path.join(MUSIC_DIR, base))],
        []),
    key=lambda genre: genre["name"].lower()
)
