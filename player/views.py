# -*- coding=utf-8 -*-

import copy
import json
import logging
from pyramid.httpexceptions import HTTPForbidden, HTTPNotFound
from pyramid.response import FileResponse, Response
from pyramid.view import view_config
import os
from PIL import Image
import re
from StringIO import StringIO
import subprocess
from tempfile import NamedTemporaryFile
import threading
import time
from zipfile import ZipFile, ZIP_DEFLATED

from player.constants import *
from player.cover import find_cover, download_cover
from player.db import *
from player.library import update_library
from player.lyrics import get_lyrics
from player.players import create_player

logger = logging.getLogger()


@view_config(route_name="file")
def file(request):
    """
    HTTP standard does not allow us to respond with 206/Partial Content with unknown range length,
    so we'll just implement download resuming our own way.

    When necessary, getting content_offset from Range request header can be done like this:

    content_offset = None
    if request.range is not None:
        if request.range.start > 0 and request.range.end is None:
            content_offset = request.range.start

    And responding can be done like this:

    content_length = NotImplemented
    if content_offset is not None:
        response.content_length = content_length - content_offset + 1
        response.content_range = ContentRange(content_offset, content_length, content_length)
        response.status_code = 206
    """

    path = file_path_for_serving(request)

    if file_can_be_transfered_directly(path):
        f = open(path)
        expected_length = os.path.getsize(path)
    else:
        f = IncompleteFile(convert_file_path(request))

        d = os.path.dirname(f.path)
        if not os.path.exists(d):
            os.makedirs(d)

        stdout, stderr = subprocess.Popen(["/usr/bin/avconv", "-i", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        m_duration = re.search("Duration: ([0-9:.]+),", stderr)
        if m_duration:
            [h, m, s] = m_duration.group(1).split(":")
            [s, ms] = s.split(".")
            expected_length = ((int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms) * 10) * (BITRATE * 1024) / 8 / 1000
        else:
            expected_length = None

        if not os.path.exists(f.path):
            def avconv_thread():
                while True:
                    with open(f.path, "w") as fh, open(os.devnull, "w") as null:
                        code = subprocess.call([
                            "/usr/bin/avconv", "-i", path,
                            "-acodec", "libmp3lame", "-ab", "%dk" % BITRATE, "-ar", "44100", "-f", "mp3",
                            "-map", "0:0",
                            "-",
                        ], stdout=fh, stderr=null)
                    if code == 0:
                        break
                f.set_completed()
            threading.Thread(target=avconv_thread).start()

    content_offset = int(request.GET.get("content_offset", 0))
    if content_offset > 0:
        f.read(content_offset)

    def app_iter():
        for data in iter(lambda: f.read(8192), ""):
            yield data
        f.close()

    response = Response()
    response.app_iter = app_iter()
    if expected_length:
        response.headers["X-Expected-Content-Length"] = str(expected_length)
    return response


@view_config(route_name="file_size")
def file_size(request):
    path = file_path_for_serving(request)

    if file_can_be_transfered_directly(path):
        size = os.path.getsize(path)
    else:
        convert_file = IncompleteFile(convert_file_path(request))
        if convert_file.is_completed():
            size = os.path.getsize(convert_file.path)
        else:
            size = -1

    return Response(str(size))


def file_path_for_serving(request):
    music_dir = request.registry.settings["music_dir"]
    path = os.path.normpath(os.path.join(music_dir, request.GET["path"]))
    if os.path.commonprefix([music_dir, path]) != music_dir:
        raise HTTPForbidden()
    if not os.path.exists(path.encode("utf8")):
        raise HTTPNotFound()
    return path.encode("utf-8")


def file_can_be_transfered_directly(path):
    return os.path.splitext(path)[1].lower()[1:] in IOS_MUSIC_EXTENSIONS


def convert_file_path(request):
    return os.path.join(request.registry.settings["tmp_dir"], request.GET["path"] + ".mp3").encode("utf-8")


class IncompleteFile(object):
    def __init__(self, path):
        self.path = path
        self.complete_path = path + ".complete"

        self.fh = None

    def is_completed(self):
        return os.path.exists(self.complete_path)

    def set_completed(self):
        open(self.complete_path, "w").close()

    def read(self, n):
        if self.fh is None:
            while True:
                try:
                    self.fh = open(self.path, "r")
                    break
                except IOError:
                    time.sleep(0.1)

        data = self.fh.read(n)
        while len(data) < n and not self.is_completed():
            time.sleep(0.1)
            data += self.fh.read(n - len(data))
        return data

    def close(self):
        if self.fh is not None:
            self.fh.close()


@view_config(route_name="file_size")
def file_size(request):
    path = file_path_for_serving(request)

    if file_can_be_transfered_directly(path):
        size = os.path.getsize(path)
    else:
        convert_file = IncompleteFile(convert_file_path(request))
        if convert_file.is_completed():
            size = os.path.getsize(convert_file.path)
        else:
            size = -1

    return Response(str(size))


@view_config(route_name="cover")
def cover(request):
    path = file_path_for_serving(request)

    io = StringIO()
    image = Image.open(path)
    image.thumbnail((640, 640), Image.ANTIALIAS)
    image.save(io, "JPEG")

    return Response(io.getvalue(), headerlist=[("Content-Type", "image/jpeg")])


@view_config(route_name="cover_for_file")
def cover_for_file(request):
    path = file_path_for_serving(request)
    directory = os.path.dirname(path)

    cover = find_cover(directory)
    if not cover:
        music_dir = request.registry.settings["music_dir"]
        if download_cover(music_dir, os.path.relpath(directory, music_dir), (640, 640)):
            cover = find_cover(directory)

    if cover:
        io = StringIO()
        image = Image.open(cover)
    else:
        io = StringIO()
        image = Image.open(os.path.join(DATA_DIR, "default-cover.png"))
    image.save(io, "JPEG")
    return Response(io.getvalue(), headerlist=[("Content-Type", "image/jpeg")])


@view_config(route_name="lyrics")
def lyrics(request):
    l = request.db.query(Lyrics).filter(Lyrics.artist == request.GET["artist"],
                                        Lyrics.title == request.GET["title"]).first()
    if l is None:
        ll = get_lyrics(request.GET["artist"], request.GET["title"])
        l = Lyrics()
        l.artist = request.GET["artist"]
        l.title = request.GET['title']
        if ll:
            l.provider = ll.provider
            l.lyrics = ll.text
        request.db.add(l)
        request.db.commit()

    return Response(l.lyrics if l.lyrics else "", headerlist=[("Content-type", "text/plain")])


@view_config(route_name="library")
def library(request):
    library_dir = os.path.join(DATA_DIR, "library")

    # {"dir1/dir2" : "0123456789abcdef0123456789abcdef (content of dir1/dir2/index.json.checksum)"}
    client_library_revision = os.path.join(DATA_DIR, "library_revisions", "%s.json" % request.GET["revision"])
    if os.path.exists(client_library_revision):
        client_directories = json.load(open(client_library_revision))
    else:
        client_directories = {}

    new_files = []
    delete_directories = copy.deepcopy(client_directories)
    for root, dirs, files in os.walk(library_dir, topdown=False):
        rel_root = os.path.relpath(root, library_dir)
        if rel_root == ".":
            rel_root = ""

        index_file = os.path.join(rel_root, "index.json")
        checksum_file = os.path.join(rel_root, "index.json.checksum")

        if rel_root not in client_directories or client_directories[rel_root] != open(os.path.join(library_dir, checksum_file)).read():
            new_files.append(index_file)
            new_files.append(checksum_file)

        if rel_root in delete_directories:
            del delete_directories[rel_root]

    with NamedTemporaryFile() as f:
        with ZipFile(f, "w", ZIP_DEFLATED) as zip_file:
            for new_file in new_files:
                zip_file.write(os.path.join(library_dir, new_file), new_file)
            zip_file.writestr("delete_directories.txt", "\n".join(delete_directories.keys()))
            zip_file.writestr("revision.txt", open(os.path.join(library_dir, "revision.txt")).read())

        response = FileResponse(os.path.abspath(f.name))
        response.headers["Content-Disposition"] = ("attachment; filename=library.zip")
        return response


@view_config(route_name="update")
def update(request):
    music_dir = request.registry.settings["music_dir"]

    def app_iter():
        t = 0
        for rel_root in update_library(music_dir, request.GET.get("rebuild", "0") == "1"):
            if time.time() - t > 1:
                yield "%s\n" % rel_root
                t = time.time()

    response = Response()
    response.app_iter = app_iter()
    return response


@view_config(route_name="player_command", renderer="json")
def player_command(request):
    player = create_player(request.registry.settings["player"])
    return getattr(player, request.matchdict["command"])(**request.POST)
