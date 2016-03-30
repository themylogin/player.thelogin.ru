# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import logging
import magic

logger = logging.getLogger(__name__)

__all__ = [b"mime"]

mime = magic.Magic(mime=True)
