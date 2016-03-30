# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from player.db import db

__all__ = [b"Lyrics"]


class Lyrics(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    datetime        = db.Column(db.DateTime())
    url             = db.Column(db.Unicode(255))
    html            = db.Column(db.UnicodeText())
    provider        = db.Column(db.Unicode(255))
    artist          = db.Column(db.Unicode(255))
    title           = db.Column(db.Unicode(255))
    text            = db.Column(db.UnicodeText())

    __table_args__  = (db.UniqueConstraint(artist, title, name="ix_artist_title"),)
