# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import cv2
import logging
import numpy
import os
from PIL import Image
import requests
from skimage.measure import structural_similarity as ssim
from StringIO import StringIO

from themyutils.requests import chrome

__all__ = [b"download_cover"]

logger = logging.getLogger(__name__)


def download_cover(music_dir, directory, min_size):
    pieces = directory.split("/")
    if pieces[0] in ["Drum&Bass", "Rap", "Rock", "Rave", "Trance"]:
        pieces = pieces[2:]
    else:
        pieces = pieces[1:]

    q = " ".join(pieces) + " cover"

    cover_io = None
    covers = _query_cover(q)
    if covers:
        cover_io = _cover_io(covers[0])
        if not _cover_size_ok(covers[0], min_size):
            cover_io = (_find_bigger_cover_io(cover_io, covers[1:], min_size) or
                        _find_bigger_cover_io(cover_io, _query_cover(q, imgsz="xxlarge"), min_size) or
                        cover_io)

    if cover_io:
        image = Image.open(cover_io)
        with open(os.path.join(music_dir, directory, "cover.jpg"), "w") as f:
            image.save(f, "JPEG")
        logger.info("Downloaded cover for %s", directory)
        return True
    else:
        return False


def _query_cover(q, **kwargs):
    try:
        results = requests.get("https://ajax.googleapis.com/ajax/services/search/images",
                               params=dict(v="1.0", q=q, **kwargs),
                               headers={"Referer": "http://player.thelogin.ru"}).json()["responseData"]["results"]
        logger.info("For query=%r, kwargs=%r got covers=%r", q, kwargs, results)
        return results
    except:
        logger.debug("Unable to query google for %s", q, exc_info=True)
        return []


def _cover_size_ok(cover, min_size):
    return map(int, (cover["width"], cover["height"])) > min_size


def _cover_io(cover):
    return StringIO(requests.get(cover["url"], headers={"User-Agent": chrome}).content)


def _find_bigger_cover_io(cover_io, covers, min_size):
    cover_cv2 = _cover_io_cv2(cover_io)

    for bigger_cover in covers:
        if _cover_size_ok(bigger_cover, min_size):
            bigger_cover_io = _cover_io(bigger_cover)
            bigger_cover_cv2 = _cover_io_cv2(bigger_cover_io)
            if ssim(cover_cv2, bigger_cover_cv2) >= 0.6:
                return bigger_cover_io


def _cover_io_cv2(cover_io):
    cover_cv2 = cv2.imdecode(numpy.asarray(bytearray(cover_io.read()), dtype=numpy.uint8), cv2.CV_LOAD_IMAGE_GRAYSCALE)
    cover_io.seek(0)

    return cover_cv2
