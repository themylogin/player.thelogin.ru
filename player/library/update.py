# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict
import json
import hashlib
import mutagen
import mutagen.easyid3
import os
import pickle
import re
import shutil
import urllib

from player.app import app
from player.cover.find import find_cover
from player.utils import get_duration

__all__ = [b"update_library"]


def update_library(rebuild=False):
    music_dir = app.config["MUSIC_DIR"]
    library_dir = os.path.join(app.config["DATA_DIR"], "library")

    dirs_with_content = set()
    dirs_with_content_encoded = set()
    dirs_with_files = set()
    artists_tracks = defaultdict(dict, **(unserialize(os.path.join(library_dir, b"artists_tracks.pickle")) or {}))
    dirs_with_content_mtimes = {}
    for root, dirs, files in os.walk(music_dir, topdown=False, followlinks=True):
        rel_root = os.path.relpath(root, music_dir)
        if rel_root == b".":
            rel_root = b""
        yield rel_root

        index_file = os.path.join(library_dir, encode_path(rel_root), b"index.json")
        checksum_file = os.path.join(library_dir, encode_path(rel_root), b"index.json.checksum")

        try:
            with open(index_file) as f:
                index_json = f.read()
                index = json.loads(index_json)
        except (IOError, ValueError):
            index_json = None
            index = {}

        new_index = {}

        for dirname in dirs:
            rel_dirname = os.path.join(rel_root, dirname)
            if rel_dirname in dirs_with_content:
                dirname_decoded = dirname.decode("utf8", "ignore")
                if (not rebuild and
                        dirname_decoded in index and
                        (index[dirname_decoded]["cover"] is None or
                            os.path.exists(os.path.join(music_dir, index[dirname_decoded]["cover"])))):
                    cover = index[dirname_decoded]["cover"]
                else:
                    if os.path.join(root, dirname) in dirs_with_files:
                        cover = find_cover(os.path.join(root, dirname))
                        if cover:
                            cover = urllib.quote(os.path.relpath(cover, music_dir))
                    else:
                        cover = None

                new_index[dirname_decoded] = {
                    "type"  : "directory",
                    "name"  : dirname_decoded,
                    "path"  : encode_path(rel_dirname),
                    "cover" : cover,
                }

        for filename in files:
            extension = os.path.splitext(filename)[1].lower()[1:]
            if extension in app.config["MUSIC_EXTENSIONS"]:
                filename_decoded = filename.decode("utf8", "ignore")
                abs_filename = os.path.realpath(os.path.join(root, filename))
                mtime = int(os.path.getmtime(abs_filename))
                size = os.path.getsize(abs_filename)

                if (not rebuild and
                    filename_decoded in index and
                    index[filename_decoded]["type"] == "file" and
                    index[filename_decoded]["mtime"] == mtime and
                    index[filename_decoded]["size"] == size):
                    new_index[filename_decoded] = index[filename_decoded]
                else:
                    rel_filename = os.path.relpath(abs_filename, music_dir)

                    try:
                        if extension == "mp3":
                            metadata = mutagen.easyid3.EasyID3(abs_filename)
                        else:
                            metadata = mutagen.File(abs_filename)
                    except:
                        metadata = {}

                    artist = metadata.get("artist", [""])[0]
                    title = metadata.get("title", [os.path.splitext(filename_decoded)[0]])[0]
                    track = metadata.get("tracknumber", ["0"])[0].split("/")[0].rjust(2, "0")
                    disc = metadata.get("discnumber", ["0"])[0].split("/")[0]

                    album = metadata.get("album", [""])[0]
                    date = metadata.get("date", [""])[0]
                    if not album or not date:
                        for date_album in reversed(rel_root.decode("utf8", "ignore").split(os.sep)):
                            match = re.match("(\d{4}|\d{4}\.\d{2})(.+)", date_album)
                            if match:
                                if not date:
                                    date = match.group(1)
                                if not album:
                                    album = match.group(2).strip().strip("-").strip()
                                break

                    dirs_with_files.add(root)
                    new_index[filename_decoded] = {
                        "type"      : "file",
                        "path"      : encode_path(rel_filename),
                        "url"       : urllib.quote(rel_filename),
                        "mtime"     : mtime,
                        "size"      : size,
                        "artist"    : artist,
                        "album"     : album,
                        "date"      : date,
                        "title"     : title,
                        "track"     : track,
                        "disc"      : disc,
                        "duration"  : get_duration(abs_filename) or 0,
                    }
                    artists_tracks[artist][title] = rel_filename

        artists = set()
        for key in new_index:
            if new_index[key]["type"] == "file":
                artists.add(new_index[key]["artist"])
                if len(artists) > 1:
                    break
        if len(artists) > 1:
            title_format = "%(track)s - %(artist)s - %(title)s"
        else:
            title_format = "%(track)s - %(title)s"
        for key in new_index:
            if new_index[key]["type"] == "file":
                new_index[key]["name"] = title_format % new_index[key]

        if new_index:
            new_index_json = json.dumps(new_index, sort_keys=True)
            if new_index_json != index_json:
                if not os.path.exists(os.path.dirname(index_file)):
                    os.makedirs(os.path.dirname(index_file))
                with open(index_file, "w") as f:
                    f.write(new_index_json)
                with open(checksum_file, "w") as f:
                    f.write(hashlib.md5(new_index_json).hexdigest())

            dirs_with_content.add(rel_root)
            dirs_with_content_encoded.add(encode_path(rel_root))

            dirs_with_content_mtimes[rel_root] = os.stat(root).st_mtime

    for root, dirs, files in os.walk(library_dir):
        rel_root = os.path.relpath(root, library_dir)
        if rel_root == ".":
            rel_root = ""

        for directory in dirs:
            if os.path.join(rel_root, directory) not in dirs_with_content_encoded:
                shutil.rmtree(os.path.join(root, directory))

    revision_data = {}
    for root, dirs, files in os.walk(library_dir, topdown=False):
        rel_root = os.path.relpath(root, library_dir)
        if rel_root == ".":
            rel_root = ""

        revision_data[rel_root] = open(os.path.join(root, b"index.json.checksum")).read()
    revision_data = json.dumps(revision_data)
    revision = hashlib.md5(revision_data).hexdigest()
    with open(os.path.join(library_dir, b"revision.txt"), "w") as f:
        f.write(revision)
    with open(os.path.join(app.config["DATA_DIR"], b"library_revisions", b"%s.json" % revision), "w") as f:
        f.write(revision_data)

    serialize(os.path.join(library_dir, b"artists_tracks.pickle"), artists_tracks)

    history = sorted(filter(lambda d: not re.search("(CD|Disc)\s*\d", d.split(b"/")[-1]),
                            dirs_with_content),
                     key=lambda d: dirs_with_content_mtimes[d])
    serialize(os.path.join(library_dir, b"history.pickle"), history)

    search_index = []
    build_search_index(search_index, library_dir)
    serialize(os.path.join(library_dir, b"search.json"), search_index)

    serialize(os.path.join(library_dir, b"genres.json"), app.config["LIST_GENRES"]())


def get_pickler_for(path):
    if path.endswith(b".json"):
        return json
    elif path.endswith(b".pickle"):
        return pickle
    else:
        raise ValueError(path)


def unserialize(path):
    try:
        with open(path) as f:
            return get_pickler_for(path).load(f)
    except (IOError, ValueError):
        pass


def serialize(path, data):
    with open(path, "w") as f:
        get_pickler_for(path).dump(data, f)


def encode_path(path):
    def encode_path_component(path_component):
        try:
            return path_component.encode("ascii").replace("\\", " ")
        except UnicodeEncodeError:
            root, ext = os.path.splitext(path_component)
            try:
                return hashlib.md5(root.encode("utf8")).hexdigest() + ext.encode("ascii")
            except UnicodeEncodeError:
                return hashlib.md5(path_component.encode("utf8")).hexdigest()

    return os.sep.join(map(encode_path_component, path.decode("utf8", "ignore").split(os.sep)))


def build_search_index(search_index, library_root, root=None):
    if root is None:
        root = library_root

    root_index_path = os.path.join(root, b"index.json")
    if not os.path.exists(root_index_path):
        return

    for item in unserialize(root_index_path).values():
        if item["type"] == "directory":
            search_index.append({"key":  search_index_key(item["name"]),
                                 "item": item})
            build_search_index(search_index, library_root, os.path.join(library_root, item["path"]))


def search_index_key(name):
    key = name

    key = re.sub(r"[0-9\-\.\(\)\[\]]+ ", "", key)
    key = re.sub(r"[\W]+", "", key, flags=re.UNICODE)

    key = key.lower().strip()

    return key
