# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import argparse
import os
import pipes
import random
import re
import shutil
import string
import subprocess
import textwrap


def install(args):
    cwd = os.path.dirname(__file__)

    with open(os.path.join(cwd, ".env"), "w") as env:
        env.write(b"MUSIC_DIRECTORY=%s\n" % pipes.quote(args.music_directory))
        env.write(b"PORT=%d\n" % args.port)

    shutil.copy(os.path.join(cwd, "alembic.example.ini"), os.path.join(cwd, "alembic.ini"))

    with open(os.path.join(cwd, "player/config.example.py")) as src:
        config = src.read()
        config = re.sub(r"^SECRET_KEY = .*$",
                        "SECRET_KEY = %r" % "".join(random.choice(string.ascii_letters) for i in range(64)),
                        config,
                        flags=re.MULTILINE)

        if args.last_fm_thelogin_ru:
            config = re.sub(r"^LAST_FM_THELOGIN_RU_URL = .*$",
                            "LAST_FM_THELOGIN_RU_URL = %r" % repr(args.last_fm_thelogin_ru),
                            config,
                            flags=re.MULTILINE)

        if args.local_player:
            config = re.sub(r"^LOCAL_PLAYER = .*$",
                            "LOCAL_PLAYER = %r" % repr(args.local_player),
                            config,
                            flags=re.MULTILINE)

        if args.sentry:
            config = re.sub(r"^SENTRY_DSN = .*$",
                            "SENTRY_DSN = %r" % repr(args.sentry),
                            config,
                            flags=re.MULTILINE)

        with open(os.path.join(cwd, "player/config.py"), "w") as dst:
            dst.write(config)

    subprocess.check_call(["docker-compose", "build"])
    subprocess.check_call(["docker-compose", "run",
                           "-w", "/player",
                           "app",
                           "alembic", "upgrade", "head"])


def update(args):
    cwd = os.path.dirname(__file__)

    new_config = os.path.join(cwd, "player", "config.example.py")
    old_config = os.path.join(cwd, "player", "config.example.py.old")
    if not os.path.exists(old_config):
        shutil.copy(new_config, old_config)

    subprocess.check_call(["docker-compose", "stop"])
    subprocess.check_call(["git", "pull"])

    if subprocess.check_output(["md5sum", new_config]) != subprocess.check_output(["md5sum", old_config]):
        print("Configuration file %r was updated. Please, revise it and press any key to continue")
        subprocess.call(["diff", old_config, new_config])
        raw_input()

    subprocess.check_call(["docker-compose", "build"])
    subprocess.check_call(["docker-compose", "run",
                           "-w", "/player",
                           "app",
                           "alembic", "upgrade", "head"])
    os.unlink(old_config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    install_parser = subparsers.add_parser(
            "install",
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent("""\
                Create configration files and run docker-compose build
            """)
    )
    install_parser.set_defaults(func=install)
    install_parser.add_argument(
            "music_directory",
            help=textwrap.dedent("""\
                Absolute path to your music directory
            """)
    )
    install_parser.add_argument(
            "port",
            type=int, default=80,
            help=textwrap.dedent("""\
                HTTP port to run web server
            """)
    )
    install_parser.add_argument(
            "--last-fm-thelogin-ru",
            metavar="<url>",
            help=textwrap.dedent("""\
                https://github.com/themylogin/last.fm.thelogin.ru
                instance URL (to make recommendations)
            """)
    )
    install_parser.add_argument(
            "--local-player",
            metavar="<url>",
            help=textwrap.dedent("""\
                Your local player URL. Supported protocols:
                - MPD: mpd://192.168.0.4:6600
            """)
    )
    install_parser.add_argument(
            "--sentry",
            metavar="<url>",
            help=textwrap.dedent("""\
                https://getsentry.com/ DSN (to log error messages)
            """)
    )

    update_parser = subparsers.add_parser(
            "update",
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent("""\
                Pull changes and run docker-compose build
            """)
    )
    update_parser.set_defaults(func=update)

    args = parser.parse_args()
    args.func(args)
