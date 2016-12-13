# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask import *
import logging
import os
from PIL import Image
from StringIO import StringIO

from player.app import app
from player.cover.download import download_cover
from player.cover.find import find_cover
from player.views.utils import file_path_for_serving

logger = logging.getLogger(__name__)


@app.route("/cover/<path:path>")
def cover(path):
    path = file_path_for_serving("/cover/")

    io = StringIO()
    image = Image.open(path)
    image.thumbnail((640, 640), Image.ANTIALIAS)
    image.save(io, "JPEG")

    return Response(io.getvalue(), headers={b"Content-Type": b"image/jpeg"})


@app.route("/cover-for-file/<path:path>")
def cover_for_file(path):
    path = file_path_for_serving("/cover-for-file/")
    directory = os.path.dirname(path)

    cover = find_cover(directory)
    if not cover:
        music_dir = app.config["MUSIC_DIR"]
        if download_cover(music_dir, os.path.relpath(directory, music_dir), (640, 640)):
            cover = find_cover(directory)

    headers = {b"Content-Type": b"image/jpeg"}
    if cover:
        io = StringIO()
        image = Image.open(cover)
        headers[b"X-Cover-Path"] = os.path.relpath(cover, app.config["MUSIC_DIR"])
    else:
        io = StringIO()
        image = Image.open(os.path.join(app.config["DATA_DIR"], "default-cover.png"))
    image.save(io, "JPEG")
    return Response(io.getvalue(), headers=headers)
