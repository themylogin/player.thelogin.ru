# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from flask import *
import logging

from player.app import app
from player.player.factory import create_player

logger = logging.getLogger(__name__)


@app.route("/player/<command>", methods=["POST"])
def player_command(command):
    return jsonify(getattr(create_player(app.config["PLAYER"]), command)(**request.form))
