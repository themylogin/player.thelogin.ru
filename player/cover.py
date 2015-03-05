# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import os
from PIL import Image
import requests
from StringIO import StringIO

logger = logging.getLogger(__name__)


def find_cover(directory, check_siblings=True):
    images = []
    directories_with_images = set()
    for root, dirs, files in os.walk(directory):
        stop = False
        for filename in files:
            extension = os.path.splitext(filename)[1].lower()[1:]
            if extension in ("bmp", "gif", "jpg", "jpeg", "tif", "tiff"):
                images.append(os.path.join(root, filename))

                directories_with_images.add(root)
                if len(directories_with_images) > 10:
                    # Too many nested directories, do not search them
                    images = filter(lambda image: os.path.split(image) == directory, images)
                    stop = True
                    break
        if stop:
            break

    if not images:
        parent_directory = os.path.normpath(os.path.join(directory, os.path.pardir))
        if check_siblings and len(os.walk(parent_directory).next()[1]) < 5:
            # This is "CD1" directory or something like that, it's cover can be in sibling "Covers" directory
            return find_cover(parent_directory, False)
        else:
            return None

    images_size = {}
    for image in images:
        try:
            images_size[image] = Image.open(image).size
        except IOError:
            logger.exception("Error processing %s", image)

    if not images_size:
        return None

    images_rating = {}
    max_size = max(max(size) for size in images_size.values())
    for image, size in images_size.iteritems():
        rating = 0

        if "front" in image.lower():
            rating += 1000

        rating += 100.0 * max(size) / max_size

        rating += sorted(images_size.keys(), key=lambda i: i.lower()).index(image)

        images_rating[image] = rating

    return sorted(images_rating.keys(), key=lambda i: images_rating[i])[-1]


def download_cover(music_dir, directory):
    pieces = directory.split("/")
    if pieces[0] in ["Drum&Bass", "Rap", "Rock", "Rave", "Trance"]:
        pieces = pieces[2:]
    else:
        pieces = pieces[1:]

    try:
        r = requests.get("https://ajax.googleapis.com/ajax/services/search/images",
                         params={"v": "1.0",
                                 "q": " ".join(pieces) + " cover",
                                 "imgsz": "xxlarge"},
                         headers={"Referer": "http://player.thelogin.ru"}).json()
    except:
        logger.debug("Unable to query google for %s cover", directory, exc_info=True)
        return False

    for result in r["responseData"]["results"]:
        try:
            input = StringIO(requests.get(result["url"]).content)
            output = StringIO()
            image = Image.open(input)
            image.save(output, "JPEG")
            with open(os.path.join(music_dir, directory, "cover.jpg"), "w") as f:
                f.write(output.getvalue())
                logger.info("Downloaded cover for %s", directory)
            return True
        except:
            logger.debug("Unable to download %s cover", result["url"], exc_info=True)

    return False
