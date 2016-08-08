# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask_script import Manager

from player.app import app

__all__ = [b"manager"]

manager = Manager(app)
