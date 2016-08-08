# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging

from setuptools import find_packages, setup

logger = logging.getLogger(__name__)


setup(
    name="player",
    version="0.0.0",
    author="themylogin",
    packages=find_packages(exclude=[]),
    test_suite="nose.collector",
    dependency_links=[
        "https://github.com/themylogin/themyutils/archive/master.zip#egg=themyutils"
    ],
    install_requires=[
        "ago",
        "alembic",
        "beautifulsoup4",
        "celery==3.1.23",
        "Flask",
        "Flask-Bootstrap",
        "Flask-Script",
        "Flask-SQLAlchemy",
        "html2text",
        "mutagen",
        "numpy",
        "pillow",
        "psycopg2",
        "pyinotify",
        "python-magic",
        "python-mpd2",
        "raven[flask]",
        "redis",
        "requests",
        "scikit-image",
        "themyutils",
    ],
)
