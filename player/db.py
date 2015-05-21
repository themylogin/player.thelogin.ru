# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
from sqlalchemy import Column, DateTime, Integer, Unicode, UnicodeText
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

__all__ = [b"Lyrics"]

Base = declarative_base()


def initialize_sql(engine):
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)


class Lyrics(Base):
    __tablename__ = "lyrics"
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime())
    url = Column(Unicode(255))
    html = Column(Unicode(255))
    provider = Column(Unicode(255))
    artist = Column(Unicode(255))
    title = Column(Unicode(255))
    lyrics = Column(UnicodeText())
