# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import redis

from player.app import app

logger = logging.getLogger(__name__)

__all__ = []


redis = redis.StrictRedis(**app.config["REDIS"])
