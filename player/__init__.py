# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from pyramid.config import Configurator
from pyramid.request import Request
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
import urlparse
from webob.multidict import GetDict

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


def request_factory(environ):
    request = Request(environ)
    request.environ["webob._parsed_query_vars"] = (GetDict(urlparse.parse_qsl(request.query_string,
                                                                              keep_blank_values=True,
                                                                              strict_parsing=False),
                                                           request.environ),
                                                   request.query_string)
    return request


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

    config.set_request_factory(request_factory)

    return config.make_wsgi_app()
