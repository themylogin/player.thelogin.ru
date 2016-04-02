# -*- coding=utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import unittest

from player.views.recommendations import find_variants, choose_best_track_path


class FindVariantsTestCase(unittest.TestCase):
    def test_apostrophe(self):
        self.assertSetEqual(
            find_variants("Don't You Remember", [
                "I Miss You",
                "Need You Now (ft. Darius Rucker) (Live At CMT Artists Of The Year Awards)",
                "Dont You Remember",
                "Painting Pictures",
                "Rumor Has It",
                "Fool That I Am (Live)",
                "He Wont Go",
                "Sweetest Devotion",
                "Don't You Remember",
                "That's It, I Quit, I'm Moving On",
            ]),
            {
                "Dont You Remember",
                "Don't You Remember",
            }
        )

    def test_case(self):
        self.assertSetEqual(find_variants("HADOUKEN!", ["Hadouken!", "HADOUKEN!"]), {"Hadouken!", "HADOUKEN!"})

    def test_false_positive(self):
        self.assertEqual(
            find_variants("Professional (feat. Robin Guthrie)", [
                "Professional (feat. Robin Guthrie)",
                "Evensong (feat. Robin Guthrie)",
            ]),
            {
                "Professional (feat. Robin Guthrie)",
            }
        )


class ChooseBestTrackPathTestCase(unittest.TestCase):
    def test_choose_from_album(self):
        self.assertEqual(
            choose_best_track_path([
                b'Pop/Adele/Bonus/2008 - 19/Bonus CD - Acoustic Set Live From The Hotel Cafe, Los Angeles/07. Make You Feel My Love.mp3',
                b'Pop/Adele/Others/2008 - Make You Feel My Love (CD, Single)/01. Make You Feel My Love.mp3',
                b'Pop/Adele/Albums/2008 - 19/09. Make You Feel My Love.mp3',
                b'Pop/Adele/Others/2011 - Live At The Royal Albert Hall/15. Make You Feel My Love.mp3',
            ]),
            b'Pop/Adele/Albums/2008 - 19/09. Make You Feel My Love.mp3'
        )

    def test_choose_not_from_compilation(self):
        self.assertEqual(
            choose_best_track_path([
                b'Rave/Industrial/Nine Inch Nails/Official/SEED/(2008) Lights In The Sky - Over North America 2008 Tour Sampler/02 Does it Offend You, Yeah_ - We Are Rockstars.mp3'
                b'Rave/Retarded Music/Does It Offend You, Yeah/2008 - We Are Rockstars (Promo CDM)/02-does_it_offend_you_yeah-we_are_rockstars.mp3',
                b'Rave/Retarded Music/Does It Offend You, Yeah/2008 - You Have No Idea What You\'re Getting Yourself Into/03 We Are Rockstars.flac',
            ]),
            b'Rave/Retarded Music/Does It Offend You, Yeah/2008 - You Have No Idea What You\'re Getting Yourself Into/03 We Are Rockstars.flac'
        )

    def test_choose_from_earlier_album(self):
        self.assertEqual(
            choose_best_track_path([
                b'Rock/Classic/Dire Stratis/Sultans Of Swing (The Very Best Of Dire Straits)/CD1/02 - Lady Writer.flac',
                b'Rock/Classic/Dire Stratis/1979 - Communique/05 - Lady Writer.flac',
            ]),
            b'Rock/Classic/Dire Stratis/1979 - Communique/05 - Lady Writer.flac',
        )

    def test_better_choose_from_ep_than_undated_directory(self):
        self.assertEqual(
            choose_best_track_path([
                b'Rave/Retarded Music/Hadouken!/Etc/Others Tracks/2009 - Something Very Bad.mp3',
                b'Rave/Retarded Music/Hadouken!/EPs/2009 - M.A.D. EP/02. Something Very Bad.mp3',

            ]),
            b'Rave/Retarded Music/Hadouken!/EPs/2009 - M.A.D. EP/02. Something Very Bad.mp3'
        )
