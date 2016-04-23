# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict
from flask import *
import logging
import os
import requests

from player.app import app
from player.db import db
from player.library.update import encode_path

logger = logging.getLogger(__name__)

__all__ = []


@app.route("/library/possessions")
def library_possessions():
    possessions = {}

    connection = db.session.get_bind(mapper=None).connect()
    try:
        result = connection.execution_options(stream_results=True).execute("""
            SELECT file.checksum, file.path
            FROM file
        """)
        for row in result:
            possessions[row["checksum"]] = encode_path(bytes(row["path"]))
    finally:
        connection.close()

    return jsonify(possessions)


@app.route("/library/rsync.excludes")
def library_rsync_excludes():
    players = request.args.getlist("player")

    directories2checksums = defaultdict(set)
    checksums2directories = defaultdict(set)
    connection = db.session.get_bind(mapper=None).connect()
    try:
        result = connection.execution_options(stream_results=True).execute("""
            SELECT file.checksum, file.path
            FROM file
        """)
        for row in result:
            directory = bytes(row["path"])
            while True:
                directory = os.path.dirname(directory)
                if not directory:
                    break

                directories2checksums[directory].add(row["checksum"])
                checksums2directories[row["checksum"]].add(directory)
    finally:
        connection.close()

    for player in players:
        for checksum in requests.get("%s/library/possessions" % player).json().iterkeys():
            for directory in checksums2directories[checksum]:
                directories2checksums[directory].discard(checksum)

    excludes = set()
    for directory in sorted(directories2checksums.keys(), key=len):
        if not directories2checksums[directory]:
            parent = directory
            while True:
                parent = os.path.dirname(parent)
                if not parent:
                    excludes.add(directory)
                    break
                if parent in excludes:
                    break

    return Response(b"\n".join(sorted(excludes)), headers={b"Content-type": b"text/plain"})
