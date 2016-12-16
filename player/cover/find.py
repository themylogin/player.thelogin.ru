# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import os
from PIL import Image

logger = logging.getLogger(__name__)

__all__ = [b"find_cover"]


def find_cover(directory, check_siblings=True):
    images = []
    directories_with_images = set()
    for root, dirs, files in os.walk(directory):
        stop = False
        for filename in files:
            extension = os.path.splitext(filename)[1].lower()[1:]
            if extension in (b"bmp", b"gif", b"jpg", b"jpeg", b"tif", b"tiff"):
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
    worse_aspect_ratio = max(max(size) / min(size) for size in images_size.values())
    for image, size in images_size.iteritems():
        rating = 0

        if b"front" in image.lower():
            rating += 1000000
        if b"folder" in image.lower():
            rating += 100000
        if not any(os.path.dirname(another_image) == os.path.dirname(image)
                   for another_image in images_size.keys()
                   if another_image != image):
            rating += 10000

        rating += 1000 * (worse_aspect_ratio - (max(size) / min(size)))

        rating += 100.0 * max(size) / max_size

        rating += sorted(images_size.keys(), key=lambda i: i.lower()).index(image)

        images_rating[image] = rating

    return sorted(images_rating.keys(), key=lambda i: images_rating[i])[-1]
