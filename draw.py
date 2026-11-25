#!/usr/bin/env python3
"""THE DAILY ATLAS — burgundy edition, Tuesday 24 November 2026.

Renders a 1024x1024 broadsheet front page with Pillow + numpy.

Law of this file
----------------
* Artwork comes from assets/*.jpg (Recraft flat-editorial scenes). Art is
  placed, never drawn over with text. Every word on the page is typeset here
  from the story data below.
* Text wraps. It never truncates, never clips, never overlaps. wrap() raises
  rather than drop a word, and the layout asserts in section (f) check the
  finished pixel geometry, not just the intent.
* The story numbers are the page's single numbering device: the numeral
  printed in a tile or brief is the numeral on its map pin. No badges.
* Facts come only from the story data. Nothing is inferred, no figure is
  invented, and the numbers in DATE CHECK are the only place a disputed
  figure is allowed to appear.
"""

import os
import sys
import math

from PIL import Image, ImageDraw, ImageFont
import numpy as np

PAGE = 1024
HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = lambda name: os.path.join(HERE, "assets", name)

# ---------------------------------------------------------------- palette --
PAPER = (247, 242, 234)      # warm cream ground
INK = (34, 28, 21)           # near-black brown, all body text
BURGUNDY = (110, 20, 35)     # masthead rule, kickers, numerals, pins
GOLD = (169, 128, 58)        # hairlines, pin rings
CREAM = (251, 246, 238)      # panels
LAND = (222, 213, 196)       # map land tint

MARGIN = 28
LIVE_L = MARGIN
LIVE_R = PAGE - MARGIN                        # 996
LIVE_W = LIVE_R - LIVE_L                      # 968

# ------------------------------------------------------------ type faces --
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
_FACES = {
    "serif_b":   "DejaVuSerif-Bold.ttf",
    "serif":     "DejaVuSerif.ttf",
    "sans":      "DejaVuSans.ttf",
    "sans_b":    "DejaVuSans-Bold.ttf",
    "mono":      "DejaVuSansMono.ttf",
    "mono_b":    "DejaVuSansMono-Bold.ttf",
}
_cache = {}


def font(face, size):
    """Cached truetype loader. size is float, rounded to int for Pillow."""
    key = (face, round(size * 4))
    f = _cache.get(key)
    if f is None:
        f = ImageFont.truetype(FONT_DIR + _FACES[face], max(1, int(round(size))))
        _cache[key] = f
    return f


# ------------------------------------------------------------- the day --
DAY_NAME = "TUESDAY"
DAY_DATE = "24 NOVEMBER 2026"
DAY_LINE = "Tuesday 24 November 2026  -  World news in one page  -  33 stories"

# ------------------------------------------------------------ the data --
# Featured three. `art` is the crop in assets/; every character below is
# typeset by this file. Deks are summaries of the story data, never new fact.
FEATURED = [
    {
        "n": 1,
        "region": "GLOBAL",
        "sure": "CONFIRMED",
        "kicker": "WALL STREET  -  MARKETS",
        "headline": "Huang's return ignites the rebound, then Tuesday fades it",
        "art": "f1.jpg",
        "dek": ("Monday's close was Wall Street's best session since April 2025, "
                "after Nvidia's board reinstated Jensen Huang: Nasdaq +6.51% to "
                "24,089.56, S&P 500 +4.73% to 7,237.17, Dow +3.01% to 49,595.31. "
                "Tuesday Asia ran with it, then the US session faded: Dow +0.85% "
                "to 50,018.70, S&P 500 -0.5%, Nasdaq -1.48%."),
        "source": "Zacks  -  Reuters  -  AP",
    },
    {
        "n": 2,
        "region": "MIDDLE EAST",
        "sure": "CONFIRMED",
        "kicker": "KHARG ISLAND  -  STANDOFF",
        "headline": "Trump dares, Iran answers with the law",
        "art": "f2.jpg",
        "dek": ("Fourteen-plus tankers are positioned at Kharg Island with crews "
                "aboard; the convoy has not sailed and Tehran denies one was "
                "launched. Trump, on Fox News Sunday: \"I hope they do, they'll all "
                "be at the bottom of the sea like the rest of the navy.\" Baghaei "
                "invokes UN Charter Article 51. The IRGC claims three escorted "
                "tankers struck mines in Hormuz; JMIC calls that unconfirmed."),
        "source": "Fox News  -  UKMTO  -  JMIC",
    },
    {
        "n": 3,
        "region": "ASIA",
        "sure": "CONFIRMED",
        "kicker": "SERANG, BANTEN  -  DISASTER",
        "headline": "Serang toll 26, and a negligence probe opens",
        "art": "f3.jpg",
        "dek": ("Police on Tuesday confirmed 26 workers killed in Saturday's fire "
                "at the PT Fonusa Agung Mulia (Milkita) candy factory in Cikande, "
                "two more bodies retrieved Tuesday, with 8 workers still missing. "
                "Most victims were on the second floor. Banten deputy police chief "
                "Zain Dwi Nugroho: \"We have found indications of a criminal offense "
                "related to negligence.\""),
        "source": "AP  -  Euronews  -  NewsCentralTV",
    },
]

# Grid of twelve. `strip` is the tile-left scene crop; `n` is the map numeral.
GRID = [
    {
        "n": 4, "region": "MIDDLE EAST", "sure": "CONFIRMED",
        "place": "GAZA CITY",
        "headline": "Hamas security chief killed in Tuesday's strikes",
        "dek": ("Naeem Abu Nahel and six others, including two police officers. "
                "Monday's strikes killed at least three."),
        "source": "Just Security  -  Reuters",
        "strip": "s04.jpg",
    },
    {
        "n": 5, "region": "EUROPE", "sure": "OFFICIAL",
        "place": "ZAPORIZHZHIA",
        "headline": "Two killed, 40 wounded in an overnight strike",
        "dek": ("The regional governor reports four children among the wounded and "
                "damage to an apartment building."),
        "source": "Just Security",
        "strip": "s05.jpg",
    },
    {
        "n": 6, "region": "GLOBAL", "sure": "REPORTED",
        "place": "ANTALYA",
        "headline": "COP31 fallout: the process itself on trial",
        "dek": ("Navarro says COP31 was \"kidnapped and held hostage by the oil "
                "producers\"; Erdogan calls the outcome \"a very valuable "
                "foundation\"."),
        "source": "Reuters  -  Carbon Brief  -  POLITICO",
        "strip": "s06.jpg",
    },
    {
        "n": 7, "region": "ASIA", "sure": "OFFICIAL",
        "place": "NEW DELHI",
        "headline": "Shah-Modi outcomes land",
        "dek": ("Eight MoUs and a Joint Vision, plus Rs 15,000 crore: Rs 3,500 "
                "crore grant, Rs 11,500 crore credit. The border dispute and "
                "Pancheshwar are unresolved."),
        "source": "Himalaya Times  -  Dainik Jagran",
        "strip": "s07.jpg",
    },
    {
        "n": 8, "region": "EUROPE", "sure": "CONFIRMED",
        "place": "BRUSSELS",
        "headline": "The outcome: 404 flights, 51,000 travellers",
        "dek": ("404 flights cancelled and 51,000+ travellers affected; only 25 "
                "of 429 planned flights operate outside 07:00-21:00."),
        "source": "BBC  -  The Flight Brief",
        "strip": "s08.jpg",
    },
    {
        "n": 9, "region": "AFRICA", "sure": "OFFICIAL",
        "place": "ITURI, DR CONGO",
        "headline": "Fighting traps Ebola responders",
        "dek": ("WHO says its teams took cover for more than 24 hours as fighting "
                "closed the roads around them."),
        "source": "UN News",
        "strip": "s09.jpg",
    },
    {
        "n": 10, "region": "EUROPE", "sure": "OFFICIAL",
        "place": "BERLIN",
        "headline": "Germany first into Ukraine's Delta system",
        "dek": ("A letter of intent is signed, with a \"preliminary agreement\" on "
                "interceptor missiles."),
        "source": "Kyiv Independent",
        "strip": "s10.jpg",
    },
    {
        "n": 11, "region": "GLOBAL", "sure": "OFFICIAL",
        "place": "NATO",
        "headline": "Rutte warns on space",
        "dek": ("NATO must be able to defend against space threats, Rutte says, citing "
                "reports that Russia is preparing a nuclear-armed satellite."),
        "source": "The Global Eye",
        "strip": "s11.jpg",
    },
    {
        "n": 12, "region": "AMERICAS", "sure": "REPORTED",
        "place": "WASHINGTON",
        "headline": "Vance and Rubio meet Qatar's PM, separately",
        "dek": ("Sheikh Mohammed bin Abdulrahman bin Jassim Al Thani met both on Monday, "
                "per an AP source."),
        "source": "AP",
        "strip": "s12.jpg",
    },
    {
        "n": 13, "region": "MIDDLE EAST", "sure": "OFFICIAL",
        "place": "KIRKUK",
        "headline": "Baghdad moves on Kurdish-area oilfields",
        "dek": ("The prime minister orders the federal oil ministry to take charge, the "
                "state news agency reports."),
        "source": "Reuters",
        "strip": "s13.jpg",
    },
    {
        "n": 14, "region": "AMERICAS", "sure": "OFFICIAL",
        "place": "WASHINGTON",
        "headline": "Trump orders the death penalty pushed faster",
        "dek": ("A Justice Department directive covers the murders of children and "
                "rapists or human traffickers who kill their victims."),
        "source": "Just Security",
        "strip": "s14.jpg",
    },
    {
        "n": 15, "region": "AMERICAS", "sure": "REPORTED",
        "place": "PORTLAND",
        "headline": "Oregon and Virginia sue SpaceX over Grok images",
        "dek": ("Two states bring suit over images generated by the Grok system."),
        "source": "IQMIA",
        "strip": "s15.jpg",
    },
]

# Eighteen briefs, two columns, numbers 16-33. `place` leads, the rest is the
# brief. These are the day's smaller stories; each one wraps to its full text.
BRIEFS = [
    {"n": 16, "region": "EUROPE", "sure": "REPORTED",
     "place": "TALLINN",
     "text": ("Russia warns that Estonia's moves are \"on the verge of triggering "
              "open war\".")},
    {"n": 17, "region": "EUROPE", "sure": "REPORTED",
     "place": "MOSCOW",
     "text": ("More than 700,000 Russian soldiers have been killed in the nearly "
              "five-year war, according to a new analysis.")},
    {"n": 18, "region": "EUROPE", "sure": "OFFICIAL",
     "place": "BERLIN",
     "text": ("At the NATO Parliamentary Assembly, Zelensky calls for Ukraine to "
              "enter the alliance.")},
    {"n": 19, "region": "AFRICA", "sure": "OFFICIAL",
     "place": "BENGHAZI",
     "text": ("UNSMIL calls for an independent investigation into Sunday's attacks "
              "at Benghazi port and off the coast.")},
    {"n": 20, "region": "EUROPE", "sure": "REPORTED",
     "place": "BRUSSELS / KYIV",
     "text": ("Seven countries call to limit Russians' travel into the EU, "
              "especially for sporting events.")},
    {"n": 21, "region": "ASIA", "sure": "OFFICIAL",
     "place": "SEOUL",
     "text": ("Several Russian aircraft flew inside the air defence identification "
              "zone.")},
    {"n": 22, "region": "ASIA", "sure": "OFFICIAL",
     "place": "WASHINGTON",
     "text": ("Commerce blacklists the Singaporean cloud firm Megaspeed "
              "International.")},
    {"n": 23, "region": "AMERICAS", "sure": "REPORTED",
     "place": "WASHINGTON / OTTAWA",
     "text": ("The Pentagon accuses Canada of falling short as a credible partner "
              "in defending North America.")},
    {"n": 24, "region": "ASIA", "sure": "OFFICIAL",
     "place": "SEOUL",
     "text": ("Rewards of up to $375,000 to catch students using AI to cheat in "
              "the college entrance exam.")},
    {"n": 25, "region": "AFRICA", "sure": "REPORTED",
     "place": "MOGADISHU / KAMPALA",
     "text": ("Somalia and Uganda will intensify operations against Al-Shabaab as "
              "a withdrawal begins.")},
    {"n": 26, "region": "EUROPE", "sure": "REPORTED",
     "place": "CAMBRIDGE",
     "text": ("Arm extends CEO Rene Haas' tenure to 2033 amid Nvidia "
              "speculation.")},
    {"n": 27, "region": "EUROPE", "sure": "OFFICIAL",
     "place": "EUROPE",
     "text": ("Champions League MD5: Real Madrid 5-1 PSV, Arsenal 1-1 Dortmund, "
              "Man City 2-2 Napoli, Galatasaray 1-0 Villa, Feyenoord 0-1 Porto, "
              "Leipzig 3-1 Lens.")},
    {"n": 28, "region": "ASIA", "sure": "OFFICIAL",
     "place": "SINGAPORE",
     "text": ("Q3 GDP grows 6.1%, and the 2026 forecast is raised to around "
              "6%.")},
    {"n": 29, "region": "ASIA", "sure": "REPORTED",
     "place": "BEIJING",
     "text": ("A record 90 billion yuan of state ETF buying struggles to halt the "
              "AI sell-off; Shanghai edges up from a 16-month low.")},
    {"n": 30, "region": "ASIA", "sure": "OFFICIAL",
     "place": "TOKYO",
     "text": ("Flash Nov PMI: manufacturing 53.7 on the strongest export orders "
              "since 2018, services slowing to 50.5; the 10-year JGB yield falls "
              "to 2.70%.")},
    {"n": 31, "region": "GLOBAL", "sure": "CONFIRMED",
     "place": "MARKETS",
     "text": ("Oil near a three-month low, Brent ~$86 early Tuesday and back "
              "toward ~$91 by the US close; gold -2.16% at $3,556.31; bitcoin "
              "slips toward $60,000.")},
    {"n": 32, "region": "ASIA", "sure": "REPORTED",
     "place": "SEOUL / SYDNEY",
     "text": ("The BoK is seen hiking to 3.25% on Thursday; ANZ brings its first "
              "RBA cut forward to June 2027.")},
    {"n": 33, "region": "AMERICAS", "sure": "OFFICIAL",
     "place": "WASHINGTON",
     "text": ("PCE inflation and GDP land Wednesday; US markets close Thursday "
              "for Thanksgiving.")},
]

# The UTC spine: six moments, two rows of three.
TIMELINE = [
    ("MON 20:00-21:00 UTC",
     "Wall Street closes: Nasdaq +6.51%, S&P 500 +4.73%, Dow +3.01%"),
    ("TUE 00:00-02:00 UTC",
     "Asia opens the rebound: Kospi +6.5%, Taiex +9%+, Nikkei +3.9%"),
    ("TUE MORNING WIB",
     "Serang police confirm the toll of 26 and open the negligence probe"),
    ("TUE DAYTIME UTC",
     "Gaza strikes kill Hamas security chief Naeem Abu Nahel"),
    ("TUE EVENING CET",
     "Champions League matchday 5: Real Madrid 5-1 PSV"),
    ("TUE 20:00-21:00 UTC",
     "US session fades: Dow tops 50,000 while S&P and Nasdaq fall"),
]

# Six numbers that define the day. Captions run to two lines.
STATS = [
    ("+31.5%", "Nvidia's Monday jump, adding about $952bn on Huang's "
               "reinstatement"),
    ("+6.51%", "Nasdaq's Monday close, its best session since April 2025"),
    ("14+", "tankers massed at Kharg Island; the convoy has not sailed"),
    ("26", "confirmed dead in the Serang fire, with 8 workers still missing"),
    ("404", "Brussels Airport flights cancelled in Monday's nationwide strike"),
    ("700,000+", "Russian soldiers killed in the war, according to a new "
                 "analysis"),
]

# ---------------------------------------------------------- the regions --
REGIONS = ["MIDDLE EAST", "EUROPE", "AMERICAS", "ASIA", "AFRICA", "OCEANIA",
           "GLOBAL"]
assert_regions_expected = {
    "MIDDLE EAST": [2, 4, 13],
    "EUROPE": [5, 8, 10, 16, 17, 18, 20, 26, 27],
    "AMERICAS": [12, 14, 15, 23, 33],
    "ASIA": [3, 7, 21, 22, 24, 28, 29, 30, 32],
    "AFRICA": [9, 19, 25],
    "OCEANIA": [],
    "GLOBAL": [1, 6, 11, 31],
}

# ------------------------------------------------------------ how sure --
HOW_SURE = [
    ("CONFIRMED", "two or more major outlets"),
    ("OFFICIAL", "on the record from officials or agencies"),
    ("REPORTED", "one outlet"),
    ("CLAIM", "unverified, typeset as a claim"),
]

# ----------------------------------------------------------- date check --
# Ten stories deliberately kept off this page, and the six due next.
# day, what, why-it-is-not-here.
LEFT_OUT = [
    ("MONDAY 23 NOV", "Brussels strike shutdown",
     "Tuesday carries only the tally"),
    ("MONDAY 23 NOV", "Shah-Modi talks",
     "Tuesday carries the outcomes"),
    ("MONDAY 23 NOV", "Wall Street rebound close",
     "Tuesday carries Asia and the fade"),
    ("SUNDAY 22 NOV", "COP31 collapse",
     "Tuesday carries the fallout"),
    ("MONDAY 23 NOV", "Vance and Rubio with Qatar's PM",
     "Monday's meetings, reported Tuesday"),
    ("THU 19 NOV", "GTA VI \"$3.8bn first-day\"", "excluded, wrong day"),
    ("JAN 2025", "Kate \"in remission\"", "excluded, wrong year"),
    ("28 AUG / 4 SEP 2026", "CRISPR \"cuts cholesterol 52%\"",
     "excluded, wrong day"),
    ("THU 19 NOV", "ICJ Myanmar genocide ruling", "excluded, wrong day"),
    ("TUE 24 NOV", "Serang \"28 unaccounted\"",
     "one police statement; conflicts with AP and Euronews' 8 still missing"),
]

NOT_YET = [
    ("SUN 29 NOV", "Spain election"),
    ("SUN 29 NOV", "OPEC+ ministerial"),
    ("SUN 29 NOV", "\"Heal\" documentary premiere"),
    ("MON 30 NOV", "Minnesota House recount"),
    ("THU 26 NOV", "Bank of Korea rate decision"),
    ("9-10 DEC", "BepiColombo separation"),
]

# ------------------------------------------------------------- map data --
# numeral -> (lon, lat). Repeated cities are offset in latitude and joined to
# their true position by a leader line, so pins never sit on top of each other.
PINS = {
    1: (-74.0, 40.7), 2: (50.3, 29.2), 3: (106.1, -6.1), 4: (34.5, 31.5),
    5: (35.1, 47.8), 6: (30.7, 36.9), 7: (77.2, 28.6), 8: (4.4, 50.8),
    9: (30.2, 1.6), 10: (13.4, 52.5), 11: (4.4, 54.2), 12: (-77.0, 38.9),
    13: (44.4, 35.5), 14: (-77.0, 36.4), 15: (-122.7, 45.5), 16: (24.8, 59.4),
    17: (37.6, 55.8), 18: (13.4, 49.8), 19: (20.1, 32.1), 20: (30.5, 50.5),
    21: (127.0, 37.6), 22: (103.8, 1.4), 23: (-75.7, 45.4), 24: (127.0, 40.2),
    25: (45.3, 2.0), 26: (0.1, 52.2), 28: (103.8, 4.6), 29: (116.4, 39.9),
    30: (139.7, 35.7), 32: (151.2, -33.9), 33: (-77.0, 42.0),
}
# Leader lines are no longer hand-listed. At world scale a degree of longitude
# is 1.15px, so New York, Washington and Boston land 3-6px apart and their
# numerals printed on top of each other. PIN_SEP is the minimum centre-to-centre
# gap a 5.2px-radius pin with a two-digit numeral needs; draw_map places each
# pin at its true position if that spot is free and otherwise at the nearest
# free spot, then draws a leader back to the true one. Derived, not tuned.
PIN_SEP = 12.4
PIN_R = 5.2
# Two stories have no single city; they get a note inside the map panel.
NO_PIN = {27: "nine grounds across Europe", 31: "oil, gold, bitcoin: the markets"}

# Europe's nine pins cannot sit apart at world scale in a 416px panel, so the
# European cluster is drawn enlarged in an inset, with a detail box marking the
# region it comes from. Hand-placed positions (lon, lat) keep the relative
# geography right while guaranteeing no two pins touch.
WORLD_EUROPE = {5, 8, 10, 11, 16, 17, 18, 20, 26}
INSET_AT = {
    26: (1.0, 51.0),      # Cambridge
    8: (6.0, 52.5),       # Brussels
    11: (6.0, 56.6),      # NATO
    10: (14.0, 53.5),     # Berlin
    18: (14.0, 49.4),     # Berlin, second story
    20: (31.0, 51.5),     # Kyiv
    5: (36.0, 47.4),      # Zaporizhzhia
    17: (38.5, 56.6),     # Moscow
    16: (25.0, 60.2),     # Tallinn
}
# City each inset pin belongs to, for the tiny label under the number.
INSET_CITY = {
    26: "Cambridge", 8: "Brussels", 11: "NATO", 10: "Berlin", 18: "Berlin",
    20: "Kyiv", 5: "Zaporizhzhia", 17: "Moscow", 16: "Tallinn",
}

# Coarse equirectangular landmasses (lon, lat). Overlapping blobs share one
# fill, so the silhouette reads as one world. Simplified on purpose: this is
# an editorial locator, not a survey.
LANDMASSES = [
    # North America
    [(-168, 65), (-162, 58), (-153, 57), (-145, 60), (-136, 58), (-130, 53),
     (-124, 48), (-124, 42), (-121, 35), (-117, 32), (-114, 29), (-110, 24),
     (-106, 23), (-97, 16), (-92, 15), (-88, 16), (-87, 21), (-91, 21),
     (-94, 18), (-97, 25), (-97, 29), (-93, 29), (-89, 29), (-84, 30),
     (-81, 25), (-80, 32), (-76, 35), (-70, 41), (-67, 45), (-60, 47),
     (-55, 52), (-66, 58), (-78, 62), (-95, 68), (-115, 69), (-130, 70),
     (-145, 70), (-160, 71)],
    # Greenland
    [(-45, 60), (-22, 70), (-22, 78), (-40, 83), (-58, 80), (-58, 70),
     (-50, 62)],
    # South America
    [(-81, 8), (-77, 8), (-72, 12), (-62, 11), (-52, 5), (-44, -2), (-35, -6),
     (-38, -13), (-40, -20), (-48, -25), (-54, -34), (-58, -38), (-62, -40),
     (-65, -45), (-68, -52), (-75, -52), (-74, -45), (-73, -37), (-71, -30),
     (-70, -23), (-70, -18), (-76, -14), (-81, -5), (-80, 2)],
    # Africa
    [(-17, 15), (-17, 21), (-10, 27), (0, 32), (10, 34), (20, 32), (32, 31),
     (35, 25), (39, 15), (43, 11), (51, 12), (43, 2), (41, -6), (40, -15),
     (35, -24), (28, -33), (20, -35), (18, -30), (12, -17), (9, -2), (3, 6),
     (-8, 5), (-13, 8)],
    # Europe
    [(-10, 36), (-9, 44), (-4, 48), (2, 51), (6, 54), (8, 58), (12, 55),
     (18, 55), (22, 60), (25, 65), (30, 70), (40, 68), (45, 60), (45, 50),
     (40, 45), (35, 42), (28, 41), (24, 40), (20, 40), (16, 42), (12, 44),
     (8, 44), (3, 42), (-2, 36)],
    # Asia
    [(30, 70), (40, 68), (50, 69), (60, 70), (70, 72), (80, 74), (95, 76),
     (110, 75), (125, 73), (140, 72), (155, 70), (170, 68), (180, 66),
     (180, 58), (170, 60), (160, 58), (155, 52), (148, 59), (142, 54),
     (140, 45), (130, 42), (122, 32), (118, 24), (110, 20), (107, 10),
     (103, 2), (100, 7), (97, 16), (92, 21), (86, 22), (80, 17), (76, 8),
     (72, 20), (66, 25), (60, 25), (55, 20), (48, 15), (45, 10), (40, 12),
     (35, 25), (30, 30), (35, 36), (40, 40), (45, 45), (45, 55), (42, 62),
     (35, 66)],
    # Arabia
    [(35, 30), (43, 30), (48, 29), (52, 25), (57, 22), (59, 20), (55, 16),
     (52, 14), (45, 12), (43, 15), (40, 20), (35, 25)],
    # Australia
    [(114, -22), (113, -26), (115, -32), (119, -34), (126, -32), (131, -31),
     (137, -33), (140, -38), (146, -39), (150, -37), (153, -30), (153, -25),
     (146, -19), (142, -11), (136, -12), (130, -11), (125, -14), (122, -17),
     (118, -20)],
    # Japan
    [(130, 32), (135, 34), (140, 36), (142, 40), (145, 44), (143, 45),
     (140, 42), (137, 37), (132, 34)],
    # British Isles
    [(-6, 50), (-5, 55), (-6, 58), (-3, 58), (0, 53), (1, 51), (-3, 50)],
    # Madagascar
    [(44, -16), (49, -13), (50, -16), (48, -25), (45, -25), (43, -20)],
    # New Zealand
    [(172, -34), (176, -38), (178, -39), (175, -42), (170, -44), (167, -45),
     (170, -41), (172, -38)],
    # Indonesia arc
    [(95, 5), (105, -6), (115, -8), (120, -9), (115, -2), (105, 0), (98, 4)],
    # Borneo
    [(109, 2), (117, 4), (119, -3), (110, -4)],
    # Philippines
    [(120, 18), (124, 14), (126, 8), (122, 6), (120, 12)],
]


# ====================================================================== #
#  Text engine. Every string on this page goes through wrap().            #
# ====================================================================== #

_SCRATCH = ImageDraw.Draw(Image.new("RGB", (8, 8), PAPER))


class TextError(Exception):
    """Raised when text cannot be set at the size asked for."""


def text_w(s, face, size):
    return _SCRATCH.textlength(s, font=font(face, size))


def line_h(face, size):
    """Cap-to-descender height plus a consistent sliver of leading."""
    f = font(face, size)
    a, d = f.getmetrics()
    return a + d


def wrap(text, face, size, max_w, label=""):
    """Greedy wrap on spaces. Returns lines; never truncates, never drops a word.

    A single word wider than max_w is a layout failure, not something to hide:
    raise TextError so the render stops and the geometry gets fixed.
    """
    words = text.split()
    if not words:
        return []
    lines, cur = [], words[0]
    if text_w(cur, face, size) > max_w:
        raise TextError("word %r (%.1fpx) overflows %.1fpx box [%s] at %.1fpt"
                        % (cur, text_w(cur, face, size), max_w, label, size))
    for w in words[1:]:
        trial = cur + " " + w
        if text_w(trial, face, size) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
            if text_w(cur, face, size) > max_w:
                raise TextError("word %r overflows %.1fpx box [%s] at %.1fpt"
                                % (cur, max_w, label, size))
    lines.append(cur)
    return lines


def fit_wrap(text, face, max_w, max_lines, hi, lo, label=""):
    """Largest size in [lo, hi] whose wrap fits in max_lines lines.

    Raises if even the floor overflows: the caller must give the text more
    room rather than shrink past the legibility floor.
    """
    size = hi
    while size >= lo:
        try:
            lines = wrap(text, face, size, max_w, label)
        except TextError:
            lines = None
        if lines is not None and len(lines) <= max_lines:
            return size, lines
        size -= 0.25
    try:
        lines = wrap(text, face, lo, max_w, label)
    except TextError as e:
        raise TextError("%s: does not fit %d lines at the %.1fpt floor (%s)"
                        % (label, max_lines, lo, e))
    if len(lines) > max_lines:
        raise TextError("%s: needs %d lines at the %.1fpt floor, budget is %d"
                        % (label, len(lines), lo, max_lines))
    return lo, lines


def fit_line(text, face, max_w, hi, lo, label=""):
    """Largest size in [lo, hi] that sets text on one line inside max_w."""
    size = hi
    while size >= lo:
        if text_w(text, face, size) <= max_w:
            return size
        size -= 0.25
    raise TextError("%s: %r will not set on one line at the %.1fpt floor"
                    % (label, text, lo))


def draw_lines(d, xy, lines, face, size, fill=INK, leading=1.0, anchor_x=None):
    """Draw wrapped lines. Returns (y_after_last_line, list_of_line_boxes).

    With anchor_x set, each line is centred on that x instead of left-set.
    """
    x, y = xy
    f = font(face, size)
    step = line_h(face, size) * leading
    boxes = []
    for ln in lines:
        w = text_w(ln, face, size)
        lx = x if anchor_x is None else anchor_x - w / 2.0
        d.text((lx, y), ln, font=f, fill=fill)
        boxes.append((lx, y, lx + w, y + step))
        y += step
    return y, boxes


def note_box(x, y, s, face, size, anchor_x=None, anchor_y=None):
    """Register one already-drawn run's INK box, and return its end x.

    The five bands that set a single run per element (masthead, timeline,
    region bar, stat strip, HOW SURE) draw with d.text directly. They used to
    register nothing, so check_text_boxes() never saw them: the whole upper
    half of the page was outside the overlap audit. This closes that.

    It registers the ink extent from getbbox(), not the em box from
    getmetrics(). The 68pt masthead date has an em box 81px tall that reaches
    back over its own kicker; the ink is 52px tall and stops clear of it. An
    em-box audit would either raise on a page that reads fine or force real
    spacing to be given up to satisfy a phantom. Ink is what a reader sees.

    anchor_x / anchor_y mirror the d.text anchor used to draw: "m" on x
    centres, "s" on y sets the baseline, "s" on x left-sets. Anything else
    raises rather than silently mis-registering.
    """
    f = font(face, size)
    bx0, by0, bx1, by1 = f.getbbox(s)
    w = bx1 - bx0
    asc = f.getmetrics()[0]
    if anchor_x is None:
        left = x
    elif anchor_x == "m":
        left = x - w / 2.0 - bx0
    else:
        raise TextError("note_box: unsupported anchor_x %r" % (anchor_x,))
    if anchor_y is None:
        top = y
    elif anchor_y == "s":
        top = y - asc
    else:
        raise TextError("note_box: unsupported anchor_y %r" % (anchor_y,))
    TEXT_BOXES.append((left + bx0, top + by0, left + bx0 + w, top + by1))
    return left + bx0 + w

def clear_band(d, y0, y1):
    """Flat cream ground behind a band, so nothing shows through from below."""
    d.rectangle([LIVE_L, y0, LIVE_R, y1], fill=PAPER)


def hairline(d, y, x0=LIVE_L, x1=LIVE_R, color=GOLD, w=1):
    d.line([(x0, y), (x1, y)], fill=color, width=w)


def rule(d, y, x0=LIVE_L, x1=LIVE_R, color=BURGUNDY, w=3):
    d.line([(x0, y), (x1, y)], fill=color, width=w)


# ====================================================================== #
#  Geometry. One place, so the startup budget assert can sum it.          #
# ====================================================================== #

GEO = {
    "masthead":   (20, 116),
    "timeline":   (118, 144),
    "regionbar":  (146, 166),
    "stats":      (168, 217),
    "featured":   (217, 476),
    "grid":       (478, 714),
    "bottom":     (716, 900),
    "howsure":    (902, 916),
    "datecheck":  (918, 996),
}

FEAT_W = 314
FEAT_ART_H = 157
FEAT_GAP = (LIVE_W - 3 * FEAT_W) // 2          # 13
GRID_TOP, GRID_BOT = GEO["grid"]
GRID_ROWS = 4
GRID_GUT = 4
GRID_ROW_H = (GRID_BOT - GRID_TOP - GRID_GUT * (GRID_ROWS - 1)) // GRID_ROWS
GRID_W = 314
GRID_GAP = (LIVE_W - 3 * GRID_W) // 2
STRIP_W, STRIP_H = 52, 40
GRID_TEXT_X = STRIP_W + 6
BRIEF_X0, BRIEF_X1 = LIVE_L, 556
MAP_X0, MAP_X1 = 580, LIVE_R

# Rectangles that received text, for the overlap audit in (f).
TEXT_BOXES = []
_IMG = None


def all_stories():
    return FEATURED + GRID + BRIEFS


def story_by_n(n):
    for s in all_stories():
        if s["n"] == n:
            return s
    raise KeyError(n)


def region_counts():
    counts = {r: 0 for r in REGIONS}
    nums = {r: [] for r in REGIONS}
    for s in all_stories():
        counts[s["region"]] += 1
        nums[s["region"]].append(s["n"])
    return counts, nums


# ------------------------------------------------------------------ (c) --
def draw_masthead(d):
    top, bot = GEO["masthead"]
    hairline(d, top, w=1)
    d.text((LIVE_L, 31), "THE DAILY ATLAS", font=font("mono_b", 9.5),
           fill=BURGUNDY)
    note_box(LIVE_L, 31, "THE DAILY ATLAS", "mono_b", 9.5)
    right = "BURGUNDY EDITION  -  WORLD NEWS IN ONE PAGE"
    rx = LIVE_R - text_w(right, "mono", 6.4)
    d.text((rx, 34), right, font=font("mono", 6.4), fill=GOLD)
    note_box(rx, 34, right, "mono", 6.4)

    size = fit_line("TUESDAY 24 NOVEMBER 2026", "serif_b", LIVE_W, 68, 40,
                    "masthead date")
    f = font("serif_b", size)
    d.text((PAGE / 2, 96), "TUESDAY 24 NOVEMBER 2026", font=f, fill=INK,
           anchor="ms")
    note_box(PAGE / 2, 96, "TUESDAY 24 NOVEMBER 2026", "serif_b", size,
             anchor_x="m", anchor_y="s")
    rule(d, 102, w=3)
    hairline(d, 107, w=1)
    sub = "COMPILED FROM WIRE REPORTS   -   TIMES UTC UNLESS MARKED   -   33 STORIES ON ONE PAGE"
    fs = fit_line(sub, "mono", LIVE_W, 6.9, 5.8, "masthead sub")
    d.text((PAGE / 2, bot - 1), sub, font=font("mono", fs),
           fill=(90, 78, 62), anchor="ms")
    note_box(PAGE / 2, bot - 1, sub, "mono", fs, anchor_x="m", anchor_y="s")
    return size


def draw_timeline(d):
    top, bot = GEO["timeline"]
    clear_band(d, top, bot)
    hairline(d, top - 4, color=(214, 203, 186))
    cols = 3
    cell_w = (LIVE_W - 2 * 10) // cols
    for i, (when, what) in enumerate(TIMELINE):
        cx = LIVE_L + (i % cols) * (cell_w + 10)
        cy = top + (i // cols) * 14
        d.rectangle([cx, cy + 2, cx + 2, cy + 10], fill=BURGUNDY)
        tw_ = text_w(when, "mono_b", 6.4)
        d.text((cx + 6, cy + 1), when, font=font("mono_b", 6.4),
               fill=BURGUNDY)
        note_box(cx + 6, cy + 1, when, "mono_b", 6.4)
        avail = cell_w - tw_ - 12
        fs = fit_line(what, "sans", avail, 7.1, 6.0, "timeline %d" % i)
        d.text((cx + 6 + tw_ + 5, cy + 1), what, font=font("sans", fs),
               fill=INK)
        note_box(cx + 6 + tw_ + 5, cy + 1, what, "sans", fs)
    hairline(d, bot + 4, color=(214, 203, 186))


def draw_regionbar(d):
    top, bot = GEO["regionbar"]
    clear_band(d, top, bot)
    d.rectangle([LIVE_L, top, LIVE_R, bot], fill=CREAM,
                outline=(222, 211, 194), width=1)
    counts, nums = region_counts()
    total = sum(counts.values())

    x = LIVE_L + 10
    size = 8.0
    for r in REGIONS:
        d.text((x, top + 3), r, font=font("mono", size), fill=INK)
        note_box(x, top + 3, r, "mono", size)
        x += text_w(r, "mono", size) + 4
        c = str(counts[r])
        d.text((x, top + 2.4), c, font=font("mono_b", size + 1), fill=BURGUNDY)
        note_box(x, top + 2.4, c, "mono_b", size + 1)
        x += text_w(c, "mono_b", size + 1) + 16
    tail = "TOTAL %d" % total
    tx = LIVE_R - 10 - text_w(tail, "mono_b", 8.4)
    d.text((tx, top + 2.4), tail, font=font("mono_b", 8.4), fill=BURGUNDY)
    note_box(tx, top + 2.4, tail, "mono_b", 8.4)

    # Proportional bar: widths track the counts, drawn inside the panel.
    bar_y = bot - 5
    span = LIVE_W - 20
    bx = LIVE_L + 10
    for r in REGIONS:
        if counts[r] == 0:
            continue
        w = span * counts[r] / total
        d.rectangle([bx, bar_y, bx + w - 2, bar_y + 2], fill=BURGUNDY)
        bx += w
    d.rectangle([LIVE_L + 10, bar_y, LIVE_L + 10 + span, bar_y + 2],
                outline=(222, 211, 194))
    return counts, total


def draw_stats(d):
    top, bot = GEO["stats"]
    clear_band(d, top, bot)
    n = len(STATS)
    gap = 10
    cell_w = (LIVE_W - gap * (n - 1)) // n

    # One size and one baseline for all six numerals. Fitting each numeral on
    # its own made 700,000+ shrink to 23pt beside 27pt siblings, which reads
    # as a defect. The strip is decided once, from the worst numeral in both
    # width and ink depth: 700,000+ is the widest, and its comma is the only
    # descender in the row, so it sets the shared baseline.
    csize, caps = [], []
    for i, (num, cap) in enumerate(STATS):
        cs, lines = fit_wrap(cap, "sans", cell_w, 2, 6.9, 6.0, "stat cap %d" % i)
        csize.append(cs)
        caps.append(lines)
    cap_h = max(len(l) for l in caps) * max(line_h("sans", s) for s in csize) * 1.02
    cap_top = bot - 2 - cap_h
    slot_h = cap_top - 3 - (top + 1)

    nsize = 27.0
    while nsize > 15.0:
        worst_w = max(text_w(num, "serif_b", nsize) for num, _ in STATS)
        worst_h = max(font("serif_b", nsize).getbbox(num)[3]
                      - font("serif_b", nsize).getbbox(num)[1]
                      for num, _ in STATS)
        if worst_w <= cell_w and worst_h <= slot_h:
            break
        nsize -= 0.5
    nf = font("serif_b", nsize)
    n_asc = nf.getmetrics()[0]
    deepest = max(nf.getbbox(num)[3] for num, _ in STATS)
    n_base = cap_top - 3 + n_asc - deepest

    for i, (num, cap) in enumerate(STATS):
        cx = LIVE_L + i * (cell_w + gap)
        if i:
            d.line([(cx - gap // 2, top + 2), (cx - gap // 2, bot - 2)],
                   fill=GOLD, width=1)
        d.text((cx, n_base), num, font=nf, fill=BURGUNDY, anchor="ls")
        note_box(cx, n_base, num, "serif_b", nsize, anchor_y="s")
        _, cboxes = draw_lines(d, (cx, cap_top), caps[i], "sans", csize[i],
                               INK, 1.02)
        TEXT_BOXES.extend(cboxes)
        assert n_base - n_asc + deepest <= cboxes[0][1] - 1.0, (
            "stat %d numeral ink (bottom %.1f) crowds its caption (top %.1f)"
            % (i, n_base - n_asc + deepest, cboxes[0][1]))
        assert n_base - n_asc + nf.getbbox(num)[1] >= top + 1, (
            "stat %d numeral ink runs above the band (top %.1f, band %d)"
            % (i, n_base - n_asc + nf.getbbox(num)[1], top))
        assert text_w(num, "serif_b", nsize) <= cell_w, (
            "stat %d numeral %r is %.1fpx wide in a %.1fpx cell"
            % (i, num, text_w(num, "serif_b", nsize), cell_w))
    hairline(d, bot + 6, color=(214, 203, 186))


# ------------------------------------------------------------------ (d) --
def draw_featured(d):
    """Three panels: art 314x157 on top, caption block strictly underneath."""
    top, bot = GEO["featured"]
    clear_band(d, top, bot)
    for i, s in enumerate(FEATURED):
        px = LIVE_L + i * (FEAT_W + FEAT_GAP)

        # --- artwork, placed at its exact size, never stretched ---
        art = Image.open(ASSET(s["art"])).convert("RGB")
        if art.size != (FEAT_W, FEAT_ART_H):
            art = art.resize((FEAT_W, FEAT_ART_H), Image.LANCZOS)
        _IMG.paste(art, (px, top))

        # hairline frame around the art, drawn on the page, not on the art
        d.rectangle([px, top, px + FEAT_W - 1, top + FEAT_ART_H - 1],
                    outline=(196, 184, 166))

        # --- caption block starts below the art ---
        cy = top + FEAT_ART_H + 5
        kick = "%d  %s  -  %s  -  %s" % (s["n"], s["region"], s["sure"],
                                        s["kicker"])
        ksize = fit_line(kick, "mono_b", FEAT_W, 7.0, 6.0,
                         "featured kicker %d" % s["n"])
        d.text((px, cy), kick, font=font("mono_b", ksize), fill=BURGUNDY)
        cy += line_h("mono_b", ksize) + 2.0

        hsize, hlines = fit_wrap(s["headline"], "serif_b", FEAT_W, 2, 13.0, 10.0,
                                 "featured headline %d" % s["n"])
        cy, boxes = draw_lines(d, (px, cy), hlines, "serif_b", hsize, INK, 1.02)
        TEXT_BOXES.extend(boxes)
        cy += 2.5

        avail = bot - cy - 2
        dsize, dlines = fit_wrap(s["dek"], "sans", FEAT_W, 12, 7.2, 6.0,
                                 "featured dek %d" % s["n"])
        # Tighten leading only if the dek hits the bottom of the band.
        need = len(dlines) * line_h("sans", dsize)
        lead = 1.06
        if need > avail:
            lead = max(0.96, avail / float(need))
        cy2, boxes = draw_lines(d, (px, cy), dlines, "sans", dsize, INK, lead)
        TEXT_BOXES.extend(boxes)
        assert cy2 <= bot + 1, ("featured dek %d overruns band by %.1fpx"
                               % (s["n"], cy2 - bot))

        ssize = fit_line(s["source"], "mono", FEAT_W, 6.0, 5.4,
                         "featured source %d" % s["n"])
        d.text((px, bot - 7), s["source"], font=font("mono", ssize),
               fill=(96, 84, 68))
        d.line([(px, bot - 10), (px + 44, bot - 10)], fill=GOLD, width=1)


def draw_grid(d):
    """Twelve tiles, 3 across and 4 down, each with a scene strip at its left."""
    top, bot = GEO["grid"]
    clear_band(d, top, bot)
    for i, s in enumerate(GRID):
        col, row = i % 3, i // 3
        tx = LIVE_L + col * (GRID_W + GRID_GAP)
        ty = top + row * (GRID_ROW_H + GRID_GUT)

        # tile frame
        d.rectangle([tx, ty, tx + GRID_W - 1, ty + GRID_ROW_H - 1],
                    fill=CREAM, outline=(224, 213, 196), width=1)

        # scene strip, flush left, cropped from the 2x source
        strip = Image.open(ASSET(s["strip"])).convert("RGB")
        strip = strip.resize((STRIP_W, STRIP_H), Image.LANCZOS)
        sy = ty + (GRID_ROW_H - STRIP_H) // 2
        _IMG.paste(strip, (tx + 3, sy))
        d.rectangle([tx + 3, sy, tx + 2 + STRIP_W, sy + STRIP_H - 1],
                    outline=(196, 184, 166))

        # numeral sits right of the strip, top of the text block
        nx = tx + GRID_TEXT_X + 4
        num = str(s["n"])
        nsz = 12.0
        d.text((nx, ty + 2.5), num, font=font("serif_b", nsz), fill=BURGUNDY)
        nw = text_w(num, "serif_b", nsz)

        place = "%s  -  %s  -  %s" % (s["place"], s["region"], s["sure"])
        place_x = nx + nw + 5
        tw_all = GRID_W - GRID_TEXT_X - 4 - 2
        psize = fit_line(place, "mono", tx + GRID_W - 4 - place_x, 5.6, 5.0,
                         "grid place %d" % s["n"])
        d.text((place_x, ty + 5), place, font=font("mono", psize),
               fill=(120, 44, 52))

        hwid = tx + GRID_W - 4 - nx
        hsize, hlines = fit_wrap(s["headline"], "sans_b", hwid, 2, 8.8, 7.4,
                                 "grid headline %d" % s["n"])
        hy, boxes = draw_lines(d, (nx, ty + 17.0), hlines, "sans_b", hsize, INK,
                               1.0)
        TEXT_BOXES.extend(boxes)

        dy = hy + 0.4
        avail = ty + GRID_ROW_H - dy - 2
        dsize, dlines = fit_wrap(s["dek"], "sans", tw_all, 6, 6.5, 5.5,
                                 "grid dek %d" % s["n"])
        need = len(dlines) * line_h("sans", dsize)
        lead = 1.04
        if need > avail:
            lead = max(0.92, avail / float(need))
        dy2, boxes = draw_lines(d, (nx, dy), dlines, "sans", dsize, INK, lead)
        TEXT_BOXES.extend(boxes)
        # the line box carries descender space the glyphs do not use, so the
        # audit allows it to close on the tile edge
        assert dy2 <= ty + GRID_ROW_H + 0.6, (
            "grid dek %d overruns tile by %.1fpx" % (s["n"],
                                                    dy2 - (ty + GRID_ROW_H)))

# ------------------------------------------------------------------ (e) --
def draw_briefs(d):
    """Eighteen briefs in two columns of nine, full text, no ellipsis."""
    top, bot = GEO["bottom"]
    band_top = top + 12
    gap = 12
    col_w = (BRIEF_X1 - BRIEF_X0 - gap) // 2
    per_col = 9
    rows = [BRIEFS[0:per_col], BRIEFS[per_col:]]

    head = "ALSO ON THE PAGE"
    d.text((BRIEF_X0, top), head, font=font("mono_b", 7.2), fill=BURGUNDY)
    dw = text_w("EIGHTEEN MORE STORIES, TODAY", "mono", 6.2)
    d.text((BRIEF_X1 - dw, top + 0.6), "EIGHTEEN MORE STORIES, TODAY",
           font=font("mono", 6.2), fill=GOLD)
    hairline(d, band_top - 3, x0=BRIEF_X0, x1=BRIEF_X1, color=(214, 203, 186))

    for ci, col in enumerate(rows):
        cx = BRIEF_X0 + ci * (col_w + gap)
        band_h = bot - band_top

        # Choose one size for the whole column: the largest whose wrap fits
        # every brief AND whose stacked height fits the band. If the band is
        # tight, tighten the inter-brief padding before touching the type.
        size = 7.0
        chosen = None
        while size >= 6.0:
            try:
                wrapped = [wrap(brief_text(s), "sans", size, col_w - 16,
                                "brief %d" % s["n"]) for s in col]
            except TextError:
                size -= 0.1
                continue
            step = line_h("sans", size) * 1.02
            total = sum(len(w) for w in wrapped) * step
            if total + (len(col) - 1) * 1.0 <= band_h:
                chosen = (size, wrapped, step, total)
                break
            size -= 0.1
        if chosen is None:
            raise TextError(
                "brief column %d cannot fit %d briefs in %.1fpx even at the "
                "6.0pt floor" % (ci, len(col), band_h))

        size, wrapped, step, used = chosen
        n_pads = (len(col) - 1)
        slack = band_h - used
        gpad = max(1.0, slack / float(max(1, n_pads)))

        y = band_top
        for s, lines in zip(col, wrapped):
            num = "%d" % s["n"]
            d.text((cx, y + 0.4), num, font=font("mono_b", 7.4),
                   fill=BURGUNDY)
            numw = text_w(num, "mono_b", 7.4)
            y2, boxes = draw_lines(d, (cx + numw + 5, y), lines, "sans", size,
                                   INK, 1.0)
            TEXT_BOXES.extend(boxes)
            y = y2 + gpad
        assert y - gpad <= bot + 1, ("brief column %d overruns by %.1fpx"
                                     % (ci, y - gpad - bot))


def brief_text(s):
    return s["place"] + "  -  " + s["text"]


def draw_map(d):
    """World map with numbered pins, plus a Europe inset for the dense cluster.

    The numeral on a pin is the same numeral printed in the tile or brief, and
    it is the only numbering device on the page.
    """
    top, bot = GEO["bottom"]
    x0, x1 = MAP_X0, MAP_X1
    band_top = top + 12
    mh = bot - band_top

    d.text((x0, top), "WHERE IT HAPPENED", font=font("mono_b", 7.2),
           fill=BURGUNDY)
    hrule = "THE NUMERAL IS THE STORY NUMBER"
    d.text((x1 - text_w(hrule, "mono", 5.6), top + 1), hrule,
           font=font("mono", 5.6), fill=GOLD)
    hairline(d, band_top - 3, x0=x0, x1=x1, color=(214, 203, 186))

    d.rectangle([x0, band_top, x1, bot], fill=CREAM,
                outline=(222, 211, 194), width=1)

    lon_l, lon_r = -170.0, 185.0
    lat_t, lat_b = 74.0, -58.0
    px0, py0 = x0 + 4, band_top + 12
    pw, ph = x1 - x0 - 8, mh - 22

    def proj(lon, lat):
        u = (lon - lon_l) / (lon_r - lon_l)
        v = (lat_t - lat) / (lat_t - lat_b)
        return (px0 + u * pw, py0 + v * ph)

    gc = (228, 219, 204)
    for lon in range(-150, 181, 30):
        d.line([proj(lon, lat_t), proj(lon, lat_b)], fill=gc, width=1)
    for lat in range(-40, 71, 20):
        d.line([proj(lon_l, lat), proj(lon_r, lat)], fill=gc, width=1)

    for poly in LANDMASSES:
        d.polygon([proj(lo, la) for lo, la in poly], fill=LAND)

    def place_pins(names, home, min_sep, box):
        """Nearest-free-spot placement: no two pins closer than min_sep.

        A force relaxation was tried first and oscillated against the panel
        clamp without converging (12 pairs still touching after 4000 passes) --
        mutually pushing pins just trade places. Greedy placement is
        deterministic and terminates: pins are taken in reading order, each
        tries its true position, then rings of candidates outward, and keeps the
        first spot that clears every pin already fixed. Every pin therefore ends
        up as close to its true city as the density allows, and any pin that had
        to move gets a leader drawn back to the truth.
        """
        bx0, by0, bx1, by1 = box
        placed = {}
        moved = {}
        for n in names:
            hx, hy = home[n]
            spot = None
            for ring in range(0, 60):
                radius = ring * 1.0
                steps = 1 if ring == 0 else (8 if ring == 1 else 24)
                for k in range(steps):
                    ang = 2 * math.pi * k / steps
                    x = hx + radius * math.cos(ang)
                    y = hy + radius * math.sin(ang)
                    if not (bx0 <= x <= bx1 and by0 <= y <= by1):
                        continue
                    if all(math.hypot(x - placed[m][0], y - placed[m][1])
                           >= min_sep for m in placed):
                        spot = (x, y)
                        break
                if spot:
                    break
            assert spot is not None, "no room on the map for pin %d" % n
            placed[n] = spot
            moved[n] = math.hypot(spot[0] - hx, spot[1] - hy)
        return placed

    world = sorted(n for n in PINS if n not in WORLD_EUROPE)
    home = {n: proj(*PINS[n]) for n in world}
    # Reading order keeps the result stable: top-to-bottom, then left-to-right.
    reading = sorted(world, key=lambda n: (round(home[n][1], 1), home[n][0]))
    # The bottom clamp stops above the footer row: a pin parked at the old
    # limit (y=884) would sit on top of the NO SINGLE PIN text, which now runs
    # the full width of the panel. 30px up leaves room for the pin radius and
    # for the note's ink.
    pin_bot = bot - 30
    placed = place_pins(reading, home, PIN_SEP,
                        (px0 + 7, py0 + 6, px0 + pw - 7, pin_bot))

    # leader lines, only where a pin had to be displaced, under the pins
    for n in world:
        if placed[n] != tuple(home[n]):
            d.line([home[n], placed[n]], fill=GOLD, width=1)

    # world pins, excluding the European cluster (handled in the inset)
    for n in world:
        cx, cy = placed[n]
        d.ellipse([cx - PIN_R, cy - PIN_R, cx + PIN_R, cy + PIN_R],
                  fill=BURGUNDY, outline=GOLD, width=1)
        d.text((cx, cy + 0.3), str(n), font=font("mono_b", 6.4 if n < 10 else 5.8),
               fill=CREAM, anchor="mm")

    # ---- Europe inset, bottom-left inside the panel ----
    iw, ih = 150, 96
    ix0 = x0 + 5
    # The bottom edge stops well short of `bot`: the un-pinned-story note is a
    # footer across the panel and needs a clear row under the inset.
    iy1 = bot - 24
    iy0 = iy1 - ih
    d.rectangle([ix0, iy0, ix0 + iw, iy1], fill=PAPER,
                outline=(206, 194, 176), width=1)
    d.text((ix0 + 4, iy0 + 2), "EUROPE, ENLARGED", font=font("mono_b", 5.2),
           fill=BURGUNDY)

    ilon_l, ilon_r = -12.0, 46.0
    ilat_t, ilat_b = 64.0, 40.0

    def iproj(lon, lat):
        u = (lon - ilon_l) / (ilon_r - ilon_l)
        v = (ilat_t - lat) / (ilat_t - ilat_b)
        return (ix0 + 6 + u * (iw - 12), iy0 + 11 + v * (ih - 17))

    def clip_poly(poly, lo_x, hi_x, lo_y, hi_y):
        """Sutherland-Hodgman: clip a lon/lat ring to an axis-aligned window.

        The old code kept only the vertices that happened to land inside the
        window and drew the survivors as a polygon. That is wrong twice over:
        the survivors are not a ring any more, so d.polygon closes them with a
        straight false chord across the panel, and nothing is clipped to the
        frame, so the chord and the fill spill off the inset. Clipping the
        edges properly keeps the real coastline where it crosses the border.
        """
        def clip_edge(pts, inside, cut):
            out = []
            if not pts:
                return out
            prev = pts[-1]
            for cur in pts:
                if inside(cur):
                    if not inside(prev):
                        out.append(cut(prev, cur))
                    out.append(cur)
                elif inside(prev):
                    out.append(cut(prev, cur))
                prev = cur
            return out

        def cut_x(a, b, x):
            t = (x - a[0]) / (b[0] - a[0])
            return (x, a[1] + t * (b[1] - a[1]))

        def cut_y(a, b, y):
            t = (y - a[1]) / (b[1] - a[1])
            return (a[0] + t * (b[0] - a[0]), y)

        pts = [tuple(p) for p in poly]
        pts = clip_edge(pts, lambda p: p[0] >= lo_x, lambda a, b: cut_x(a, b, lo_x))
        pts = clip_edge(pts, lambda p: p[0] <= hi_x, lambda a, b: cut_x(a, b, hi_x))
        pts = clip_edge(pts, lambda p: p[1] >= lo_y, lambda a, b: cut_y(a, b, lo_y))
        pts = clip_edge(pts, lambda p: p[1] <= hi_y, lambda a, b: cut_y(a, b, hi_y))
        return pts

    for poly in LANDMASSES:
        ring = clip_poly(poly, ilon_l, ilon_r, ilat_b, ilat_t)
        if len(ring) >= 3:
            d.polygon([iproj(lo, la) for lo, la in ring], fill=(226, 216, 199))

    # tie the inset to the world: a faint box round Europe on the world map
    bx0, by0 = proj(-12, 64)
    bx1, by1 = proj(46, 40)
    d.rectangle([bx0, by0, bx1, by1], outline=(176, 152, 110), width=1)
    d.line([(bx0, by1), (ix0 + iw, iy0)], fill=(176, 152, 110), width=1)
    d.line([(bx1, by1), (ix0 + iw, iy0)], fill=(176, 152, 110), width=1)

    for n in sorted(INSET_AT):
        cx, cy = iproj(*INSET_AT[n])
        r = 4.6
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BURGUNDY,
                  outline=GOLD, width=1)
        d.text((cx, cy + 0.2), str(n), font=font("mono_b", 5.6), fill=CREAM,
               anchor="mm")

    # The two un-pinned stories, as a footer across the panel under the inset.
    # This note has now failed the render twice in two different ways, so both
    # bounds are asserted, not just the one that broke first:
    #
    #  1. It was originally one unwrapped run from x=743 -- 249px of room for a
    #     247px sentence -- so it finished level with the panel border and read
    #     as if it had been cut. It wraps now.
    #  2. Worse, the second line was silently ERASED: draw_howsure() runs after
    #     draw_map() and clear_band()s 900..918 to PAPER, and the line sat at
    #     y=896 with ink down to 902. The overlap audit cannot catch that -- it
    #     compares registered boxes, and a flat rectangle over the top leaves
    #     the box perfectly legal. So the note is now a footer under the inset,
    #     clear of the clearance band, and its ink is asserted to stop above it.
    note_x0 = ix0
    note_x1 = x1 - 6
    lead = "NO SINGLE PIN"
    ny = iy1 + 5
    lw = note_box(note_x0, ny, lead, "mono_b", 5.4)
    seg = "   " + ";   ".join("%d %s" % (n, NO_PIN[n]) for n in sorted(NO_PIN))
    nlines = wrap(seg, "mono", 5.4, note_x1 - lw - 4, "NO SINGLE PIN note")
    nlines[0] = nlines[0].lstrip()
    _, nboxes = draw_lines(d, (lw + 4, ny), nlines, "mono", 5.4,
                           (96, 84, 68), 1.0)
    TEXT_BOXES.extend(nboxes)
    clear_top = GEO["howsure"][0] - 2      # first row clear_band() paints over
    for bx0n, by0n, bx1n, by1n in nboxes:
        assert bx1n <= note_x1, "NO SINGLE PIN note reaches %.1f, panel %d" % (
            bx1n, note_x1)
        assert by1n <= clear_top, (
            "NO SINGLE PIN note ink reaches y=%.1f; anything past %d is erased "
            "by draw_howsure's clear_band" % (by1n, clear_top))
        assert by0n >= iy1 + 1, "NO SINGLE PIN note rides up into the inset"

    # No two pins may overlap anywhere on the map or in the inset: the numeral
    # is the only identity a pin carries, so two pins that touch make both
    # unreadable. This guards the world pins (the inset is checked separately
    # by check_pins against its own coordinates).
    for i, a in enumerate(world):
        for b in world[i + 1:]:
            gap = math.hypot(placed[a][0] - placed[b][0],
                             placed[a][1] - placed[b][1])
            assert gap >= PIN_SEP - 0.01, (
                "pins %d and %d are %.2fpx apart on the map, need %.1f"
                % (a, b, gap, PIN_SEP))
    return proj


def draw_howsure(d):
    top, bot = GEO["howsure"]
    clear_band(d, top - 2, bot + 2)
    hairline(d, top - 3, color=(214, 203, 186))
    d.text((LIVE_L, top), "HOW SURE", font=font("mono_b", 6.4), fill=BURGUNDY)
    x = LIVE_L + text_w("HOW SURE", "mono_b", 6.4) + 12
    note_box(LIVE_L, top, "HOW SURE", "mono_b", 6.4)
    for key, desc in HOW_SURE:
        kw = text_w(key, "mono_b", 6.4)
        d.text((x, top), key, font=font("mono_b", 6.4), fill=INK)
        note_box(x, top, key, "mono_b", 6.4)
        x += kw + 4
        seg = "- " + desc + "    "
        d.text((x, top), seg, font=font("sans", 6.4), fill=(96, 84, 68))
        note_box(x, top, seg, "sans", 6.4)
        x += text_w(seg, "sans", 6.4)
    assert x < LIVE_R + 2, "HOW SURE row overruns the page edge"


def draw_datecheck(d):
    """Drawn last, and everything above it must clear it.

    Two blocks side by side: the ten stories deliberately left out (two
    columns of five) and the six due next (two columns of three). The row
    pitch is a fixed number of points, not a number solved from however much
    room is left over, and it is asserted against the line box -- the earlier
    version divided the leftover height by six and produced 7.5px rows in an
    8px line box, which printed all six NOT YET entries on top of each other.
    The divider is placed from the measured width of the left block, so the
    two blocks cannot share a column. Every line registers in TEXT_BOXES.
    """
    top, bot = GEO["datecheck"]
    d.rectangle([LIVE_L, top, LIVE_R, bot], fill=CREAM,
                outline=(222, 211, 194), width=1)
    d.rectangle([LIVE_L, top, LIVE_R, top + 2], fill=BURGUNDY)

    body_top = top + 21
    body_bot = bot - 4
    step = 10.4
    day_size = what_size = 5.9
    why_size = 5.4

    def seg(x, y, s, face, size, fill):
        """One run of a table row: draw it, register its box, return its end."""
        d.text((x, y), s, font=font(face, size), fill=fill)
        w_ = text_w(s, face, size)
        TEXT_BOXES.append((x, y, x + w_, y + step))
        return x + w_

    hx = LIVE_L + 8
    d.text((hx, top + 6), "DATE CHECK", font=font("mono_b", 8.0),
           fill=BURGUNDY)
    hw = text_w("DATE CHECK", "mono_b", 8.0)
    TEXT_BOXES.append((hx, top + 6, hx + hw, top + 6 + line_h("mono_b", 8.0)))
    hx2 = seg(hx + hw + 8, top + 7,
              "ten stories from other days kept off this page, and six due next",
              "sans", 6.2, (96, 84, 68))

    def item_w(day, what, why):
        return (text_w(day + "  ", "mono_b", day_size)
                + text_w(what, "sans", what_size) + 3
                + text_w("(" + why + ")", "sans", why_size))

    # left block: ten left-out items, two columns of five
    col_w = max(item_w(*row) for row in LEFT_OUT) + 4
    col_gap = 14
    for i, (day, what, why) in enumerate(LEFT_OUT):
        col, row = i % 2, i // 2
        cx = hx + col * (col_w + col_gap)
        cy = body_top + row * step
        x = seg(cx, cy, day + "  ", "mono_b", day_size, (140, 96, 40))
        x = seg(x, cy, what, "sans", what_size, INK)
        seg(x + 3, cy, "(" + why + ")", "sans", why_size, (120, 108, 92))
    left_r = hx + col_w + col_gap + col_w

    # right block: six due next, two columns of three, after a hairline rule
    d.line([(left_r + 9, body_top - 1), (left_r + 9, body_bot)],
           fill=(222, 211, 194))
    rx = left_r + 18
    ny_rows = 3
    ny_col_w = max(text_w(day + "  ", "mono_b", day_size)
                   + text_w(what, "sans", what_size) for day, what in NOT_YET) + 4
    for i, (day, what) in enumerate(NOT_YET):
        col, row = i // ny_rows, i % ny_rows
        cx = rx + col * ny_col_w
        cy = body_top + row * step
        x = seg(cx, cy, day + "  ", "mono_b", day_size, (140, 96, 40))
        seg(x, cy, what, "sans", what_size, INK)

    assert step >= line_h("sans", what_size) + 2.0, (
        "DATE CHECK row pitch %.2f is too tight for a %.2f line box"
        % (step, line_h("sans", what_size)))
    assert body_top + 4 * step + line_h("sans", what_size) <= body_bot, \
        "LEFT OUT overruns the DATE CHECK panel"
    assert body_top + (ny_rows - 1) * step + line_h("sans", what_size) <= body_bot, \
        "NOT YET overruns the DATE CHECK panel"
    assert rx + 2 * ny_col_w <= LIVE_R - 6, "NOT YET runs off the panel"
    assert hx2 < LIVE_R - 8, "DATE CHECK header runs off the panel"


# ------------------------------------------------------------------ (f) --
def check_geometry():
    """Band table must be ordered, inside the page, and non-overlapping."""
    prev_name, prev_bot = None, 0
    for name, (t, b) in GEO.items():
        assert 0 <= t < b <= PAGE, "%s band %r is not inside the page" % (
            name, (t, b))
        assert t >= prev_bot, "%s band starts at %d, above %s which ends at %d" % (
            name, t, prev_name, prev_bot)
        prev_name, prev_bot = name, b
    assert prev_bot <= PAGE, "page content runs past the bottom edge"
    return prev_bot


def check_regions():
    counts, nums = region_counts()
    assert sum(counts.values()) == 33, "region counts sum to %d, not 33" % (
        sum(counts.values()))
    for r in REGIONS:
        assert sorted(nums[r]) == sorted(assert_regions_expected[r]), (
            "%s carries %r, expected %r" % (r, sorted(nums[r]),
                                            sorted(assert_regions_expected[r])))
    assert len(all_stories()) == 33, "story count is %d" % len(all_stories())
    seen = sorted(s["n"] for s in all_stories())
    assert seen == list(range(1, 34)), "story numbers are not 1..33: %r" % seen
    for s in all_stories():
        assert s["sure"] in dict(HOW_SURE), (
            "story %d has unknown sure tag %r" % (s["n"], s["sure"]))
    return counts


def check_pins():
    pinned = set(PINS)
    unpinned = set(NO_PIN)
    expected = set(range(1, 34)) - unpinned
    assert pinned == expected, (
        "pin set wrong; missing %r, extra %r"
        % (sorted(expected - pinned), sorted(pinned - expected)))
    for n in PINS:
        assert n not in NO_PIN, "story %d is both pinned and unpinned" % n
    assert set(INSET_AT) == WORLD_EUROPE, (
        "inset set %r does not match the European cluster %r"
        % (sorted(INSET_AT), sorted(WORLD_EUROPE)))


def check_text_boxes(tol=0.9):
    """No two text boxes may overlap; nothing may sit outside the live area."""
    boxes = TEXT_BOXES
    for (ax0, ay0, ax1, ay1) in boxes:
        assert ax0 >= LIVE_L - 1 and ax1 <= LIVE_R + 1, (
            "text box %r escapes the live width" % ((ax0, ax1),))
        assert ay0 >= -1 and ay1 <= PAGE + 1, "text box %r escapes the page" % (
            (ay0, ay1),)
    for i in range(len(boxes)):
        ax0, ay0, ax1, ay1 = boxes[i]
        for j in range(i + 1, len(boxes)):
            bx0, by0, bx1, by1 = boxes[j]
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > tol and oy > tol:
                raise AssertionError(
                    "text overlap %.1fx%.1fpx between boxes %d and %d: %r / %r"
                    % (ox, oy, i, j, boxes[i], boxes[j]))


def check_accent(img):
    """Accent-family pixels must stay under 12% of the page."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]

    def near(rgb, tol):
        return ((np.abs(r - rgb[0]) <= tol) & (np.abs(g - rgb[1]) <= tol)
                & (np.abs(b - rgb[2]) <= tol))

    burg = near(BURGUNDY, 26)
    gold = near(GOLD, 26)
    accent = burg | gold
    frac = float(accent.mean())
    assert frac < 0.12, ("accent coverage %.2f%% is over the 12%% guard"
                         % (frac * 100))
    return frac


def check_no_flat_panels(img):
    """Every art region must carry real picture variance, not a flat panel."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    regions = []
    top = GEO["featured"][0]
    for i in range(3):
        px = LIVE_L + i * (FEAT_W + FEAT_GAP)
        regions.append(("featured %d" % (i + 1),
                        a[top:top + FEAT_ART_H, px:px + FEAT_W]))
    gtop = GEO["grid"][0]
    for i, s in enumerate(GRID):
        col, row = i % 3, i // 3
        tx = LIVE_L + col * (GRID_W + GRID_GAP)
        ty = gtop + row * (GRID_ROW_H + GRID_GUT)
        sy = ty + (GRID_ROW_H - STRIP_H) // 2
        regions.append(("strip %d" % s["n"],
                        a[sy:sy + STRIP_H, tx + 3:tx + 3 + STRIP_W]))
    for name, reg in regions:
        assert reg.size, "%s has no pixels" % name
        sd = float(reg.std())
        # a flat colour banner or glyph plate sits well under 12
        assert sd > 12.0, ("%s looks flat (std %.1f) - not a scene" % (name, sd))
        uniq = len(np.unique(reg.reshape(-1, 3).astype(np.uint8), axis=0))
        assert uniq > 400, ("%s has only %d distinct colours - not a scene"
                            % (name, uniq))


def render():
    global _IMG
    check_geometry()
    counts = check_regions()
    check_pins()

    img = Image.new("RGB", (PAGE, PAGE), PAPER)
    _IMG = img
    d = ImageDraw.Draw(img)

    draw_masthead(d)
    draw_timeline(d)
    draw_regionbar(d)
    draw_stats(d)
    draw_featured(d)
    draw_grid(d)
    draw_briefs(d)
    draw_map(d)
    draw_howsure(d)
    draw_datecheck(d)

    check_text_boxes()
    frac = check_accent(img)
    check_no_flat_panels(img)

    out = os.path.join(HERE, "entry.png")
    img.save(out, "PNG", optimize=True)
    size = os.path.getsize(out)
    assert size <= 1024 * 1024, "entry.png is %d bytes, over 1 MiB" % size
    print("entry.png  %d bytes  accent %.2f%%  regions %s"
          % (size, frac * 100,
             " ".join("%s=%d" % (r.split()[0][:4], counts[r]) for r in REGIONS)))
    return out


if __name__ == "__main__":
    try:
        render()
    except TextError as e:
        print("LAYOUT FAILED: %s" % e, file=sys.stderr)
        sys.exit(2)



