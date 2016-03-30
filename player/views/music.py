# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask import *
import logging
import os
import subprocess
import tempfile
import threading
import time

from player.app import app
from player.mime import mime
from player.utils import get_duration
from player.views.utils import file_path_for_serving

logger = logging.getLogger(__name__)


class IncompleteFile(object):
    def __init__(self, path):
        self.path = path

        self.completed_path = path + b".complete"
        self.error = None

        self.fh = None

    @property
    def completed(self):
        return os.path.exists(self.completed_path)

    def set_completed(self):
        with open(self.completed_path, "w"):
            pass

    def set_error(self, code, stderr):
        self.error = (code, stderr)

    def read(self, n):
        if self.fh is None:
            while True:
                try:
                    self.fh = open(self.path, "r")
                    break
                except IOError:
                    time.sleep(0.1)

        data = self.fh.read(n)
        while len(data) < n and self.error is None and not self.completed:
            time.sleep(0.1)
            data += self.fh.read(n - len(data))
        return data

    def close(self):
        if self.fh is not None:
            self.fh.close()


def convert(src, incomplete_file):
    code = -1
    with tempfile.TemporaryFile() as errors:
        for i in range(5):
            with open(incomplete_file.path, "w") as output:
                code = subprocess.call([
                    app.config["FFMPEG"],
                    b"-i", src,
                    b"-acodec", b"libmp3lame",
                    b"-ab", b"%dk" % app.config["MUSIC_BITRATE"],
                    b"-ar", b"44100",
                    b"-f", b"mp3",
                    b"-map", b"0:0",
                    b"-",
                ], stdout=output, stderr=errors)
                if code == 0:
                    incomplete_file.set_completed()
                    return

        errors.seek(0)
        error = errors.read()
        incomplete_file.set_error(code, error)
        logger.error("Error converting file %r: ffmpeg returned code %r:\n%r", src, code, error)


def file_streamer(f):
    try:
        for data in iter(lambda: f.read(8192), b""):
            yield data
    finally:
        f.close()


@app.route("/music/<path:path>", methods=["HEAD", "GET"])
def music(path):
    path = file_path_for_serving("/music/")

    serve_directly = os.path.splitext(path)[1].lower()[1:] in app.config["DIRECT_MUSIC_EXTENSIONS"]
    converted_tmp_path = os.path.join(app.config["TMP_DIR"], b"%s.mp3" % os.path.relpath(path, app.config["MUSIC_DIR"]))

    if request.method == "HEAD":
        if serve_directly:
            size = os.path.getsize(path)
        else:
            convert_file = IncompleteFile(converted_tmp_path)
            if convert_file.completed:
                size = os.path.getsize(convert_file.path)
            else:
                size = -1

        return Response("", headers={"X-Content-Length": str(size)})

    if request.method == "GET":
        if serve_directly:
            f = open(path)
            content_type = mime.from_file(path)
            expected_length = os.path.getsize(path)
        else:
            f = IncompleteFile(converted_tmp_path)

            d = os.path.dirname(f.path)
            if not os.path.exists(d):
                os.makedirs(d)

            content_type = b"audio/mpeg"

            duration = get_duration(path)
            if duration:
                expected_length = int(duration * (app.config["MUSIC_BITRATE"] * 1024) / 8)
            else:
                expected_length = None

            if not os.path.exists(f.path):
                convert_thread = threading.Thread(target=convert, args=(path, f))
                convert_thread.daemon = True
                convert_thread.start()

        """
        HTTP standard does not allow us to respond with 206/Partial Content with unknown range length,
        so we'll just implement download resuming our own way.
        """
        content_offset = request.headers.get("X-Content-Offset", 0, type=int)
        if content_offset > 0:
            f.read(content_offset)

        headers = {"Content-Type": content_type,
                   "X-Accel-Buffering": "no"}
        if expected_length is not None:
            headers["X-Expected-Content-Length"] = str(expected_length)

        return Response(file_streamer(f), headers=headers)
