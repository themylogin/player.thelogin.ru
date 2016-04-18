# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from player.db import db

__all__ = [b"File", b"Lyrics", b"Track"]


class File(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    track_id        = db.Column(db.Integer, db.ForeignKey("track.id"), nullable=False)
    path            = db.Column(db.Binary, nullable=False)
    checksum        = db.Column(db.String(32))

    __table_args__  = (db.UniqueConstraint(path, name="ix_file_path"),
                       db.Index("ix_file_checksum", checksum),)


class Lyrics(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    datetime        = db.Column(db.DateTime())
    url             = db.Column(db.Unicode(255))
    html            = db.Column(db.UnicodeText())
    provider        = db.Column(db.Unicode(255))
    artist          = db.Column(db.Unicode(255))
    title           = db.Column(db.Unicode(255))
    text            = db.Column(db.UnicodeText())

    __table_args__  = (db.UniqueConstraint(artist, title, name="ix_lyrics_artist_title"),)


class Track(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    artist          = db.Column(db.Text, nullable=False)
    title           = db.Column(db.Text, nullable=False)

    __table_args__  = (db.UniqueConstraint(artist, title, name="ix_track_artist_title"),)

