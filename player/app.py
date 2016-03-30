# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask import Flask
import logging

import player.config

logger = logging.getLogger(__name__)

__all__ = [b"app"]

app = Flask("player")
app.config.from_object(player.config)
