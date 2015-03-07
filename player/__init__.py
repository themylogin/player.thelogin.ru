# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker

from player.db import initialize_sql


def db(request):
    maker = request.registry.dbmaker
    session = maker()

    def cleanup(request):
        if request.exception is not None:
            session.rollback()
        else:
            session.commit()
        session.close()
    request.add_finished_callback(cleanup)

    return session


def main(global_config, **settings):
    config = Configurator(settings=settings)

    config.add_route("file", "/file")
    config.add_route("file_size", "/file_size")
    config.add_route("cover", "/cover")
    config.add_route("cover_for_file", "/cover_for_file")
    config.add_route("lyrics", "/lyrics")
    config.add_route("library", "/library")
    config.add_route("update", "/update")
    config.add_route("player_command", "/player/{command}")
    config.scan()

    engine = engine_from_config(settings, "sqlalchemy.")
    initialize_sql(engine)
    config.registry.dbmaker = sessionmaker(bind=engine)
    config.add_request_method(db, reify=True)

    return config.make_wsgi_app()
