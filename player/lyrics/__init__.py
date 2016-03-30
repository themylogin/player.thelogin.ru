# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

from bs4 import BeautifulSoup, Tag
from collections import namedtuple
import html2text
import logging
import re
import requests
import urlparse

from themyutils.requests import chrome

__all__ = [b"get_lyrics", b"fetch_lyrics_from_url"]

fetchers = []
logger = logging.getLogger(__name__)
Lyrics = namedtuple("Lyrics", ["url", "html", "provider", "text"])


def get_lyrics(artist, title):
    try:
        r = requests.get("https://www.google.com/search?oe=utf8&ie=utf8&source=uds&start=0&hl=ru&gws_rd=ssl",
                         params={"q": ("%s %s lyrics" % (artist, title)).encode("utf-8")})
        for a in BeautifulSoup(r.text).select("h3 a"):
            url = dict(urlparse.parse_qsl(urlparse.urlparse(a["href"]).query))["q"]
            logging.debug("Found %s", url)
            lyrics = fetch_lyrics_from_url(url)
            if lyrics:
                return lyrics
    except Exception:
        logger.error("Error querying %s %s lyrics", artist, title, exc_info=True)


def fetch_lyrics_from_url(url):
    host = urlparse.urlparse(url).netloc
    for fetcher in fetchers:
        if fetcher["host"] in host:
            try:
                html = requests.get(url, headers={"User-Agent": chrome}).text
                lyrics = fetcher["fetcher"].fetch(html)
                if lyrics:
                    return Lyrics(url, html, fetcher["fetcher"].__class__.__name__, lyrics)
            except Exception:
                logger.error("Error fetching lyrics from %s", url, exc_info=True)


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

    def fetch(self, html):
        lyrics_html = self.fetch_from_html(html)
        if lyrics_html:
            text = self.h.handle(lyrics_html).strip()

            if re.sub("\W", "", text, flags=re.UNICODE).lower().replace("instrumental", "") != "":
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
class AzLyrics(SoupLyricsFetcher):
    def fetch_from_soup(self, soup):
        lyricsh = soup.find("div", class_="ringtone")
        while lyricsh:
            if isinstance(lyricsh, Tag) and lyricsh.name == "div" and self.h.handle(unicode(lyricsh)).strip():
                return unicode(lyricsh)

            lyricsh = lyricsh.next_element


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
                if trash.get("class") and set(trash.get("class")).intersection({"p402_premium"}):
                    continue

                trash.extract()


@fetcher("songlyrics.com")
class SongLyrics(SoupSimpleLyricsFetcher):
    tag = "p"
    attrs = {"id": "songLyricsDiv"}

    def process_html(self, result):
        if "We do not have the lyrics for " in result:
            return None

        return result
