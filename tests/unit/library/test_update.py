# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import unittest

from player.library.update import search_index_keys


class SearchIndexKeysTestCast(unittest.TestCase):
    def test_album_with_year(self):
        self.assertEqual(search_index_keys("2007 - Emerging Organisms Vol. 1"),
                         {"emergingorganismsvol1"})

    def test_album_with_year_and_month(self):
        self.assertEqual(search_index_keys("2014.09 - Yggdrasil"),
                         {"yggdrasil"})

    def test_poor_album_with_year(self):
        self.assertEqual(search_index_keys("(2005) Skreamizm Vol 1"),
                         {"skreamizmvol1"})

    def test_poor_album_with_artist_and_year(self):
        self.assertEqual(search_index_keys("(2010) Skream - Outside The Box"),
                         {"skreamoutsidethebox", "skream", "outsidethebox"})

    def test_hungarian(self):
        self.assertEqual(search_index_keys("Félperc"),
                         {"félperc", "felperc"})

    def test_russian(self):
        self.assertEqual(search_index_keys("Белые флаги зажигайте медленно"),
                         {"белыефлагизажигайтемедленно"})

    def test_articles(self):
        self.assertEqual(search_index_keys("A Shoreline Dream"),
                         {"ashorelinedream", "shorelinedream"})
