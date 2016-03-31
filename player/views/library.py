# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import copy
from flask import *
import json
import logging
import os
from tempfile import NamedTemporaryFile
import time
from zipfile import ZipFile, ZIP_DEFLATED

from player.app import app
from player.library.update import update_library

logger = logging.getLogger(__name__)

__all__ = []


@app.route("/library")
def library():
    library_dir = os.path.join(app.config["DATA_DIR"], "library")

    client_directories = {}
    client_revision = request.args.get("since-revision")
    if client_revision:
        client_revision_path = os.path.join(app.config["DATA_DIR"], "library_revisions", "%s.json" % client_revision)
        if os.path.exists(client_revision_path):
            with open(client_revision_path) as f:
                client_directories = json.load(f)

    new_files = []
    delete_directories = copy.deepcopy(client_directories)
    for root, dirs, files in os.walk(library_dir, topdown=False):
        rel_root = os.path.relpath(root, library_dir)
        if rel_root == ".":
            rel_root = ""

        index_file = os.path.join(rel_root, "index.json")
        checksum_file = os.path.join(rel_root, "index.json.checksum")

        checksum = None
        if os.path.exists(os.path.join(library_dir, checksum_file)):
            with open(os.path.join(library_dir, checksum_file)) as f:
                checksum = f.read()

        if rel_root not in client_directories or client_directories[rel_root] != checksum:
            new_files.append(index_file)
            new_files.append(checksum_file)

        if rel_root in delete_directories:
            del delete_directories[rel_root]

    with NamedTemporaryFile(delete=False) as f:
        try:
            with ZipFile(f, "w", ZIP_DEFLATED) as zip_file:
                for new_file in new_files:
                    zip_file.write(os.path.join(library_dir, new_file), new_file)
                zip_file.writestr("delete_directories.txt", "\n".join(delete_directories.keys()))
                zip_file.writestr("genres.json", open(os.path.join(library_dir, "genres.json")).read())
                zip_file.writestr("revision.txt", open(os.path.join(library_dir, "revision.txt")).read())
                zip_file.writestr("search.json", open(os.path.join(library_dir, "search.json")).read())

            return send_file(f.name, as_attachment=True, attachment_filename="library.zip")
        finally:
            os.unlink(f.name)


@app.route("/library/update")
def library_update():
    return Response(update_library_reporter(request.args.get("rebuild", False, type=bool)),
                    headers={"X-Accel-Buffering": "no"})


def update_library_reporter(*args, **kwargs):
    t = 0
    for rel_root in update_library(*args, **kwargs):
        if time.time() - t > 1:
            yield b"%s\n" % rel_root
            t = time.time()
