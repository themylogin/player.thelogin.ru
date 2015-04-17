# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from bs4 import BeautifulSoup
from collections import namedtuple
import html2text
import logging
import re
import requests
import urlparse

__all__ = [b"get_lyrics"]

fetchers = []
logger = logging.getLogger(__name__)
Lyrics = namedtuple("Lyrics", ["provider", "text"])


def get_lyrics(artist, title):
    try:
        r = requests.get("https://www.google.com/search?oe=utf8&ie=utf8&source=uds&start=0&hl=ru&gws_rd=ssl",
                         params={"q": ("%s %s lyrics" % (artist, title)).encode("utf-8")})
        for a in BeautifulSoup(r.text).select("h3 a"):
            url = dict(urlparse.parse_qsl(urlparse.urlparse(a["href"]).query))["q"]
            logging.debug("Found %s", url)
            host = urlparse.urlparse(url).netloc
            for fetcher in fetchers:
                if fetcher["host"] in host:
                    try:
                        lyrics = fetcher["fetcher"].fetch(url)
                        if lyrics:
                            return Lyrics(fetcher["fetcher"].__class__.__name__, lyrics)
                    except Exception:
                        logger.exception("Error fetching lyrics from %s", url)
    except Exception:
        logger.exception("Error querying %s %s lyrics" % (artist, title))


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
        text = self.h.handle(self.fetch_from_html(html)).strip()

        text = text.replace("\r\n", "\n")
        if text.count("\n\n") > len(text.split("\n")) * 0.25:
            text = text.replace("\n\n", "\n")

        return text

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
        result = soup.find(self.tag, **self.attrs)
        if result:
            self.process_soup(result)
            return self.process_html(unicode(result))

    def process_soup(self, result):
        return result

    def process_html(self, result):
        return result


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

    def process_html(self, result):
        return re.sub("<a(.*?)</a>", "", result)


@fetcher("genius.com")
class Genius(SoupSimpleLyricsFetcher):
    attrs = {"class": "lyrics"}


@fetcher("lyricsfreak.com")
class LyricsFreak(SoupSimpleLyricsFetcher):
    attrs = {"id": "content_h"}


@fetcher("lyricsmania.com")
class LyricsMania(SoupSimpleLyricsFetcher):
    attrs = {"class": "lyrics-body"}

    def process_soup(self, result):
        for tag in ["div", "strong"]:
            for trash in result.findAll(tag):
                trash.extract()


@fetcher("songlyrics.com")
class SongLyrics(SoupSimpleLyricsFetcher):
    tag = "p"
    attrs = {"id": "songLyricsDiv"}

    def process_html(self, result):
        if "We do not have the lyrics for " in result:
            return None

        return result
