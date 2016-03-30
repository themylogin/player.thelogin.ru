# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import functools
import logging

logger = logging.getLogger(__name__)

__all__ = [b"PlayerNotAvailableException", b"PersistentPlayer"]


class PlayerNotAvailableException(Exception):
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
            logger.warning("Player is temporarily unavailable, re-creating player", exc_info=True)

            self.player = self._create_player()
            func = getattr(self.player, command)

            try:
                return func(*args, **kwargs)
            except:
                logger.error("Player is permanently unavailable", exc_info=True)
                raise PlayerNotAvailableException()


    def _create_player(self):
        try:
            return self.player_factory()
        except:
            logger.error("Error creating player", exc_info=True)
            raise PlayerNotAvailableException()
