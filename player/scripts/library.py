# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging

from player.library.update import update_library as _update_library
from player.manager import manager

logger = logging.getLogger(__name__)


@manager.command
def update_library(rebuild=False):
    for d in _update_library(rebuild):
        print(d)
