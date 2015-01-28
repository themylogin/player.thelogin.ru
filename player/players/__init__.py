# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import functools
import logging
from pyramid.exceptions import ConfigurationError
import urlparse

from player.players.mpd import MPD

logger = logging.getLogger(__name__)


class PlayerNotAvailable(Exception):
    pass


class PersistentPlayer(object):
    def __init__(self, player_factory):
        self.player_factory = player_factory
        self.player = None

    def __getattr__(self, attr):
        return functools.partial(self._player_command, attr)

    def _player_command(self, command, *args, **kwargs):
        if self.player is None:
            self.player = self._create_player()

        func = getattr(self.player, command)

        try:
            return func(*args, **kwargs)
        except:
            logger.exception("Player is temporarily unavailable, re-creating player")

            self.player = self._create_player()
            func = getattr(self.player, command)

            try:
                return func(*args, **kwargs)
            except:
                logger.exception("Player is permanently unavailable")
                raise PlayerNotAvailable()


    def _create_player(self):
        try:
            return self.player_factory()
        except:
            logger.exception("Error creating player")
            raise PlayerNotAvailable()


def create_player(url):
    return PersistentPlayer(functools.partial(create_player_engine, url))


def create_player_engine(url):
    o = urlparse.urlparse(url)

    if o.scheme == "mpd":
        return MPD(o.hostname, o.port)

    raise ConfigurationError("%s player engine is not supported", o.scheme)


class PlayerUpdater(object):
    def __init__(self, player):
        self.player = player

    def update(self, updates):
        for update in updates:
            self.player.update(update)
