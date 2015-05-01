# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import re
import subprocess

logger = logging.getLogger(__name__)

__all__ = []


def get_duration(path):
    stdout, stderr = subprocess.Popen([b"/usr/bin/avconv", b"-i", path],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    m_duration = re.search("Duration: ([0-9:.]+),", stderr)
    if m_duration:
        [h, m, s] = m_duration.group(1).split(":")
        [s, ms] = s.split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100
