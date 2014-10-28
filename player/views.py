import copy
import gzip
import hashlib
import json
import mpd
import mutagen
import mutagen.easyid3
from pyramid.httpexceptions import HTTPForbidden, HTTPNotFound
from pyramid.response import FileResponse, Response
from pyramid.view import view_config
import os
import re
import shutil
import subprocess
from tempfile import NamedTemporaryFile
import threading
import time
import urllib
import urlparse
from webob.byterange import ContentRange
from zipfile import ZipFile, ZIP_DEFLATED

MUSIC_EXTENSIONS = ("flac", "m4a", "mp3")
IOS_MUSIC_EXTENSIONS = ("m4a", "mp3")
BITRATE = 256

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

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

@view_config(route_name="library")
def library(request):
    music_dir = request.registry.settings["music_dir"]
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
    library_dir = os.path.join(DATA_DIR, "library")

    def app_iter():
        t = 0
        for rel_root in update_library(music_dir, library_dir, request.GET.get("rebuild", "0") == "1"):
            if time.time() - t > 1:
                yield "%s\n" % rel_root
                t = time.time()

    response = Response()
    response.app_iter = app_iter()
    return response

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

def update_library(music_dir, library_dir, rebuild=False):
    music_dir = os.path.abspath(music_dir)
    library_dir = os.path.abspath(library_dir)

    dirs_with_content = set()
    dirs_with_content_encoded = set()
    for root, dirs, files in os.walk(music_dir, topdown=False, followlinks=True):
        rel_root = os.path.relpath(root, music_dir)
        if rel_root == ".":
            rel_root = ""
        yield rel_root

        index_file = os.path.join(library_dir, encode_path(rel_root), "index.json")
        checksum_file = os.path.join(library_dir, encode_path(rel_root), "index.json.checksum")

        try:
            index_json = open(index_file).read()
            index = json.loads(index_json)
        except (IOError, ValueError):
            index_json = None
            index = {}

        new_index = {}

        for dirname in dirs:
            rel_dirname = os.path.join(rel_root, dirname)
            if rel_dirname in dirs_with_content:
                dirname_decoded = dirname.decode("utf8", "ignore")
                new_index[dirname_decoded] = {
                    "type"  : "directory",
                    "name"  : dirname_decoded,
                    "path"  : encode_path(rel_dirname),
                }

        for filename in files:
            extension = os.path.splitext(filename)[1].lower()[1:]
            if extension in MUSIC_EXTENSIONS:
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
                    }

        artists = set()
        for key in new_index:
            if new_index[key]["type"] == "file":
                artists.add(new_index[key]["artist"])
                if len(artists) > 1:
                    break
        if len(artists) > 1:
            title_format = u"%(track)s - %(artist)s - %(title)s"
        else:
            title_format = u"%(track)s - %(title)s"
        for key in new_index:
            if new_index[key]["type"] == "file":
                new_index[key]["name"] = title_format % new_index[key]

        if new_index:
            new_index_json = json.dumps(new_index, sort_keys=True)
            if new_index_json != index_json:
                if not os.path.exists(os.path.dirname(index_file)):
                    os.makedirs(os.path.dirname(index_file))
                open(index_file, "w+").write(new_index_json)
                open(checksum_file, "w+").write(hashlib.md5(new_index_json).hexdigest())

            dirs_with_content.add(rel_root)
            dirs_with_content_encoded.add(encode_path(rel_root))

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

        revision_data[rel_root] = open(os.path.join(root, "index.json.checksum")).read()
    revision_data = json.dumps(revision_data)
    revision = hashlib.md5(revision_data).hexdigest()
    open(os.path.join(library_dir, "revision.txt"), "w").write(revision)
    open(os.path.join(DATA_DIR, "library_revisions", "%s.json" % revision), "w").write(revision_data)

@view_config(route_name="player_command", renderer="json")
def player_command(request):
    player = create_player(request.registry.settings["player"])
    return getattr(player, request.matchdict["command"])(**request.POST)

def create_player(url):
    o = urlparse.urlparse(url)

    if o.scheme == "mpd":
        return MPD(o.hostname, o.port)

    return None

class MPD(object):
    def __init__(self, hostname, port):
        self.client = mpd.MPDClient()
        self.client.connect(hostname, port)

    def current_state(self, **kwargs):
        playlistinfo = self.client.playlistinfo()
        status = self.client.status()
        return {
            "playlist"  : [item["file"] for item in playlistinfo],
            "position"  : int(status.get("song", -1)),
            "elapsed"   : int(float(status.get("elapsed", -1))),
        }
