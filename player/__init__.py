# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from pyramid.config import Configurator

from player.inotify import UpdatersManager
from player.players import create_player, PlayerUpdater


def main(global_config, **settings):
    config = Configurator(settings=settings)

    config.add_route("file", "/file")
    config.add_route("file_size", "/file_size")
    config.add_route("cover", "/cover")
    config.add_route("lyrics", "/lyrics")
    config.add_route("library", "/library")
    config.add_route("update", "/update")
    config.add_route("player_command", "/player/{command}")
    config.scan()

    updates_manager = UpdatersManager(settings["music_dir"])
    if settings.get("player"):
        player = create_player(settings["player"])
        updates_manager.add_updater(PlayerUpdater(player))

    return config.make_wsgi_app()
