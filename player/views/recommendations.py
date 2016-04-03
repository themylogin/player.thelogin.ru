# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from collections import defaultdict
from difflib import SequenceMatcher
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

DISC_DIRECTORY_REGEXP = r"(CD|Disc|Side)\s*(\d|[a-dA-D])"


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

    directories = filter(lambda x: not re.search(DISC_DIRECTORY_REGEXP, x), directories)

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

    include_dirs = request.args.getlist("include-dir")
    exclude_dirs = request.args.getlist("exclude-dir")

    yielded = set()
    for line in requests.get(
        app.config["LAST_FM_THELOGIN_RU_URL"] + "/api/recommendations/",
        params=params,
        stream=True
    ).iter_lines():
        recommendation = json.loads(line)
        track_paths = set().union(*[
            set().union(*[
                artists_tracks[artist][track]
                for track in find_variants(recommendation["track"], artists_tracks[artist].keys())
            ])
            for artist in find_variants(recommendation["artist"], artists_tracks.keys())
        ])
        if track_paths:
            track_path = choose_best_track_path(track_paths)

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
    directory = (filter(lambda item: item["path"] == encode_path(os.path.dirname(path)),
                        item_siblings_index(path).values()) + [None])[0]
    if directory:
        if re.search(DISC_DIRECTORY_REGEXP, directory["path"]):
            return directory_for_track(directory["path"])
        else:
            return directory


def item_siblings_index(path):
    with open(os.path.join(os.path.dirname(os.path.join(app.config["DATA_DIR"], b"library", encode_path(path))),
                           os.path.pardir,
                           b"index.json")) as f:
        return json.load(f)


def find_variants(name, variants):
    name_variants = set()
    for variant in variants:
        if SequenceMatcher(None, name.lower(), variant.lower()).ratio() >= 0.85:
            name_variants.add(variant)
    return name_variants


def choose_best_track_path(paths):
    rates = defaultdict(list)
    for path in paths:
        m = re.search(b"[^0-9]((1|2)[0-9]{3})[^0-9]", b"/".join(path.split(b"/")[:-1]))
        if m:
            rate = int(m.group(1))
        else:
            rate = 13000

        for substring, weight in [
            (b"EP",         10000),
            (b"VA",         12500),
            (b"Single",     15000),
            (b"Singles",    15000),
            (b"Promo",      17500),
            (b"Live",       20000),
        ]:
            if re.search(b"\W%s\W" % substring, path, re.IGNORECASE):
                rate += weight
                break
        else:
            siblings_count = 0
            siblings_artists = set()
            index = item_siblings_index(path).values()
            for item in filter(lambda item: item["type"] == "file", index):
                siblings_count += 1
                siblings_artists.add(item["artist"])

            if len(siblings_artists) > siblings_count / 4:
                rate += 5000 + len(siblings_artists)
            else:
                rate += 0

            if re.search(b"\W(anniversary|deluxe|remaster)\W", path, re.IGNORECASE):
                rate += 1000

        rates[rate].append(path)

    return rates[sorted(rates.keys())[0]][0]
