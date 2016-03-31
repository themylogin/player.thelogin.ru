# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
from flask import *
import logging
import os
import pickle
import random
import re
import requests

from player.app import app
from player.library.update import encode_path

logger = logging.getLogger(__name__)


@app.route("/recommendations/unheard/<username>")
def recommendations_unheard(username):
    return Response(stream_with_context(recommendations_unheard_streamer(username)),
                    headers={b"X-Accel-Buffering": b"no"})


def recommendations_unheard_streamer(username):
    exclude = request.args.getlist("exclude")
    sort = request.args.get("sort", "recent")
    limit = request.args.get("limit", 1, type=int)

    library_path = os.path.join(app.config["DATA_DIR"], b"library")

    with open(os.path.join(library_path, b"history.pickle")) as f:
        directories = pickle.load(f)

    directories = filter(lambda x: not re.search("(CD|Disc)\s*\d", x), directories)

    if exclude:
        directories = filter(lambda d: not any(d.startswith(e) for e in exclude),
                             directories)

    if sort == "recent":
        directories = list(reversed(directories))
    else:
        random.shuffle(directories)

    for d in directories:
        files = []
        for root, _, _ in os.walk(os.path.join(library_path, d)):
            with open(os.path.join(root, b"index.json")) as f:
                files += filter(lambda v: v["type"] == "file", json.load(f).values())

        if not (4 <= len(files) <= 30):
            logger.info("%r len = %d" % (d, len(files)))
            continue

        for f in files:
            if f["artist"] and f["title"]:
                scrobble_count = requests.post(
                    app.config["LAST_FM_THELOGIN_RU_URL"] + "/api/sql",
                    headers={"Content-type": "application/json"},
                    data=json.dumps({"query": """SELECT COUNT(*) AS count
                                                 FROM scrobble
                                                 INNER JOIN user ON (user.id = scrobble.user_id)
                                                 WHERE user.username = :username
                                                   AND scrobble.artist = :artist
                                                   AND scrobble.track = :track""",
                                     "params": {"username": username,
                                                "artist": f["artist"],
                                                "track": f["title"]}})
                ).json()[0]["count"]

                if scrobble_count == 0:
                    directory = directory_for_track(f["path"])
                    if directory:
                        yield json.dumps(directory) + b"\n"

                    limit -= 1
                    if limit == 0:
                        return
                else:
                    logger.info("%r — %r from %r was scrobbled %d time(s)" % (f["artist"], f["title"], d, scrobble_count))

                break


@app.route("/recommendations/for/<for_username>/from/<from_username>")
def recommendations_for_from(for_username, from_username):
    return Response(stream_with_context(recommendations_for_from_streamer(for_username, from_username)),
                    headers={b"X-Accel-Buffering": b"no"})


def recommendations_for_from_streamer(for_username, from_username):
    library_path = os.path.join(app.config["DATA_DIR"], b"library")

    with open(os.path.join(library_path, b"artists_tracks.pickle")) as f:
        artists_tracks = pickle.load(f)

    params = {"include-user": from_username,
              "min-scrobbles-count": request.args["min-scrobbles-count"],
              "sort": request.args["sort"],
              "limit": 10000}
    if request.args.get("datetime-start"):
        params["datetime-start"] = request.args.get("datetime-start")
    if request.args.get("datetime-end"):
        params["datetime-end"] = request.args.get("datetime-end")
    if for_username != from_username:
        params["exclude-user"] = for_username
    limit = request.args.get("limit", 100, type=int)

    include_dirs = request.args.getlist("include-dirs")
    exclude_dirs = request.args.getlist("exclude-dirs")

    yielded = set()
    for line in requests.get(
        app.config["LAST_FM_THELOGIN_RU_URL"] + "/api/recommendations/",
        params=params,
        stream=True
    ).iter_lines():
        recommendation = json.loads(line)
        track_path = artists_tracks.get(recommendation["artist"], {}).get(recommendation["track"])
        if track_path:
            if include_dirs and not any(track_path.startswith(prefix.encode("utf-8"))
                                        for prefix in include_dirs):
                continue
            if exclude_dirs and any(track_path.startswith(prefix.encode("utf-8"))
                                    for prefix in exclude_dirs):
                continue

            if request.args.get("type") == "file":
                with open(os.path.join(os.path.dirname(os.path.join(library_path, encode_path(track_path))),
                                       b"index.json")) as f:
                    track = (filter(lambda item: item["path"] == encode_path(track_path),
                                    json.load(f).values()) + [None])[0]
                    if track:
                        yield json.dumps(track) + "\n"
                        limit -= 1
                        if limit == 0:
                            break
            elif request.args.get("type") == "directory":
                directory = directory_for_track(track_path)
                if directory:
                    if directory["path"] not in yielded:
                        yielded.add(directory["path"])
                        yield json.dumps(directory) + "\n"
                        limit -= 1
                        if limit == 0:
                            break


def directory_for_track(path):
    with open(os.path.join(os.path.dirname(os.path.join(app.config["DATA_DIR"], b"library", encode_path(path))),
                           os.path.pardir,
                           b"index.json")) as f:
        directory = (filter(lambda item: item["path"] == encode_path(os.path.dirname(path)),
                            json.load(f).values()) + [None])[0]
        if directory:
            if re.search("(CD|Disc)\s*\d", directory["path"]):
                return directory_for_track(directory["path"])
            else:
                return directory
