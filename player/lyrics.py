# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from bs4 import BeautifulSoup
import html2text
import logging
from pygoogle import pygoogle
import re
import requests
import urlparse

__all__ = [b"get_lyrics"]

fetchers = []
logger = logging.getLogger(__name__)


def get_lyrics(artist, title):
    google = pygoogle(("%s %s lyrics" % (artist, title)).encode("utf-8"))
    google.pages = 2
    for url in google.get_urls():
        logging.debug("Found %s", url)
        host = urlparse.urlparse(url).netloc
        for fetcher in fetchers:
            if fetcher["host"] in host:
                try:
                    lyrics = fetcher["fetcher"].fetch(url)
                    if lyrics:
                        return lyrics
                except Exception:
                    logger.exception("Error fetching lyrics from %s", url)


def fetcher(host):
    def wrap(cls):
        fetchers.append({"host": host,
                         "fetcher": cls()})
        return cls
    return wrap


class LyricsFetcher(object):
    def __init__(self):
        self.h = html2text.HTML2Text()
        self.h.ignore_links = True

    def fetch(self, url):
        html = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.104 Safari/537.36",
        }).text
        return self.h.handle(self.fetch_from_html(html)).strip()

    def fetch_from_html(self, html):
        raise NotImplementedError


class SoupLyricsFetcher(LyricsFetcher):
    def fetch_from_html(self, html):
        return self.fetch_from_soup(BeautifulSoup(html))

    def fetch_from_soup(self, soup):
        raise NotImplementedError


class SoupSimpleLyricsFetcher(SoupLyricsFetcher):
    tag = "div"
    attrs = {}

    def fetch_from_soup(self, soup):
        d = soup.find(self.tag, **self.attrs)
        if d:
            return unicode(d)


@fetcher("azlyrics.com")
class AzLyrics(LyricsFetcher):
    def fetch_from_html(self, html):
        m = re.search("%s(.+)%s" % (re.escape("<!-- start of lyrics -->"),
                                    re.escape("<!-- end of lyrics -->")), html, flags=re.DOTALL)
        if m:
            return m.group(1)


@fetcher("songmeanings.com")
class SongMeanings(SoupSimpleLyricsFetcher):
    attrs = {"class": "lyric-box"}


@fetcher("genius.com")
class Genius(SoupSimpleLyricsFetcher):
    attrs = {"class": "lyrics"}


@fetcher("lyricsfreak.com")
class LyricsFreak(SoupSimpleLyricsFetcher):
    attrs = {"id": "content_h"}


@fetcher("lyricsmania.com")
class LyricsMania(SoupSimpleLyricsFetcher):
    attrs = {"class": "lyrics-body"}
