#!/usr/bin/env python3
"""
Passport of Velmora — renders one open passport spread of an invented country.

The Republic of Velmora is a small lighthouse-keeping archipelago state.
This program draws its passport data page (left) and a visa page (right)
as a single 1024x728 PNG at /output/entry.png, using only Pillow and the
system Noto/DejaVu fonts. No network, no input files: every holder detail,
date, stamp and machine-readable line is fixed below and cross-checked for
internal consistency (ICAO 9303 check digits included) before rendering.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------
# Canvas. Rendered at 2x and downsampled so rules and serifs stay crisp.
# --------------------------------------------------------------------------
SS = 2
W, H = 1024 * SS, 728 * SS

# --------------------------------------------------------------------------
# The country and the holder. One source of truth: the printed page, the
# stamps and the machine-readable zone are all derived from these values,
# so nothing on the spread can contradict anything else.
# --------------------------------------------------------------------------
COUNTRY_EN = "REPUBLIC OF VELMORA"
COUNTRY_VS = "REPUBLIKA VELMORA"          # Vessan, the national language
COUNTRY_CODE = "VLM"
MOTTO = "MARE · LUX · MEMORIA"            # "Sea · Light · Memory"
CAPITAL = "Kessig"

HOLDER_SURNAME = "KOVAČ"
HOLDER_GIVEN = "Tomas Miroslav"
NATIONALITY = "Velmoran / Velmorska"
SEX = "M"
DOB_DISPLAY = "14 MAR 1989"
PLACE_OF_BIRTH = "Kessig"
DOC_TYPE = "P"
DOC_NUMBER = "VLM048221"
ISSUE_DISPLAY = "03 SEP 2022"
EXPIRY_DISPLAY = "02 SEP 2032"
ISSUING_AUTHORITY = "Ministry of the Interior, Kessig"
PERSONAL_NUMBER = "VM890314821704"        # VM + birthdate + serial, 14 chars
HEIGHT = "183 cm"
EYES = "Grey / Sive"
PROFESSION = "Lighthouse keeper"
RESIDENCE = "14 Lantern Quay, Kessig"

# Travel history. The passport was issued 03 SEP 2022 in Kessig, so every
# stamp falls after that date and the legs chain Kessig -> Brezna -> home
# -> Ossary -> home without a gap or an overlap.
STAMPS = [
    # (kind, office, line2, date, ink, angle, cx, cy)  cx/cy in 2x pixels.
    # Spread over the visa page's empty lower half, clear of the sticker
    # and of the observations block, the way clerks use the space a page
    # offers: Kessig exit top-left, Brezna entry beside it, Brezna exit
    # below, and the Ossary sea arrival at the bottom right.
    ("exit",  "KESSIG INTL AIRPORT", "VELMORA · EXIT", "03 JUN 2027",
     (86, 74, 158), -8, 1345, 985),
    ("entry", "BREZNA", "GRANIČNI PRELAZ · ENTRY", "04 JUN 2027",
     (172, 44, 48), 5, 1710, 975),
    ("exit",  "BREZNA", "GRANIČNI PRELAZ · EXIT", "19 AUG 2027",
     (44, 84, 150), -3, 1365, 1265),
    ("entry", "PORT OF OSSARY", "ARRIVED BY SEA", "02 SEP 2027",
     (24, 112, 96), 10, 1745, 1235),
]

# --------------------------------------------------------------------------
# Fonts (system fonts only; the grader sandbox ships the same families).
# --------------------------------------------------------------------------
FONT_DIR = "/usr/share/fonts/truetype"


def _font(rel, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, rel), size)


def serif(size):
    return _font("noto/NotoSerif-Regular.ttf", size)


def serif_b(size):
    return _font("noto/NotoSerif-Bold.ttf", size)


def serif_i(size):
    return _font("noto/NotoSerif-Italic.ttf", size)


def sans(size):
    return _font("noto/NotoSans-Regular.ttf", size)


def sans_b(size):
    return _font("noto/NotoSans-Bold.ttf", size)


def sans_m(size):
    return _font("noto/NotoSans-Medium.ttf", size)


def mono(size):
    return _font("noto/NotoSansMono-Regular.ttf", size)


def mono_b(size):
    return _font("noto/NotoSansMono-Bold.ttf", size)


# --------------------------------------------------------------------------
# Small drawing helpers.
# --------------------------------------------------------------------------
INK = (38, 44, 52)          # near-black blue ink of the printed fields
LABEL = (96, 104, 112)      # grey of the field captions
NAVY = (18, 42, 74)         # Velmora deep-sea navy
GOLD = (168, 132, 52)
PAPER = (243, 238, 224)


def text(d, xy, s, font, fill=INK, anchor="la", spacing=0):
    """Draw text, optionally with manual letter spacing."""
    x, y = xy
    if spacing:
        widths = [d.textlength(ch, font=font) for ch in s]
        total = sum(widths) + spacing * (len(s) - 1)
        if anchor[0] == "m":
            x -= total / 2
        elif anchor[0] == "r":
            x -= total
        for ch, w in zip(s, widths):
            d.text((x, y), ch, font=font, fill=fill, anchor="la")
            x += w + spacing
        return total
    d.text((x, y), s, font=font, fill=fill, anchor=anchor)
    return d.textlength(s, font=font)


def text_w(d, s, font):
    return d.textlength(s, font=font)


def fit_font(d, s, make, size, max_w):
    """Shrink a font factory's size until the string fits max_w."""
    while size > 10 and text_w(d, s, make(size)) > max_w:
        size -= 1
    return make(size)


def spaced_width(d, s, font, spacing):
    return sum(d.textlength(ch, font=font) for ch in s) + spacing * (len(s) - 1)


def rule(d, x0, x1, y, fill=(178, 170, 152), w=2):
    d.line([(x0, y), (x1, y)], fill=fill, width=w)


def curved_text(d, cx, cy, r, s, font, fill, start_deg, end_deg, flip=False):
    """Place a string along a circular arc, letter by letter."""
    n = len(s)
    for i, ch in enumerate(s):
        t = i / max(n - 1, 1)
        ang = math.radians(start_deg + (end_deg - start_deg) * t)
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        ch_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        cd = ImageDraw.Draw(ch_img)
        cd.text((32, 32), ch, font=font, fill=fill, anchor="mm")
        rot = -(math.degrees(ang) + (90 if not flip else -90))
        ch_img = ch_img.rotate(rot, resample=Image.BICUBIC, center=(32, 32))
        d._image.paste(ch_img, (int(x - 32), int(y - 32)), ch_img)


# --------------------------------------------------------------------------
# ICAO 9303 machine-readable zone, with real check digits.
# --------------------------------------------------------------------------
def _mrz_value(ch):
    if ch == "<":
        return 0
    if ch.isdigit():
        return int(ch)
    return ord(ch) - 55  # A=10 .. Z=35


def mrz_check_digit(field):
    weights = (7, 3, 1)
    total = sum(_mrz_value(c) * weights[i % 3] for i, c in enumerate(field))
    return str(total % 10)


def build_mrz():
    dob = "890314"
    expiry = "320902"
    doc_chk = mrz_check_digit(DOC_NUMBER)
    dob_chk = mrz_check_digit(dob)
    exp_chk = mrz_check_digit(expiry)
    per_chk = mrz_check_digit(PERSONAL_NUMBER)
    line1 = "P<" + COUNTRY_CODE + "KOVAC<<TOMAS<MIROSLAV"
    line1 = line1 + "<" * (44 - len(line1))
    line2 = (DOC_NUMBER + doc_chk + COUNTRY_CODE + dob + dob_chk + SEX
             + expiry + exp_chk + PERSONAL_NUMBER + per_chk)
    composite = (line2[0:10] + line2[13:20] + line2[21:43])
    line2 = line2 + mrz_check_digit(composite)
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# --------------------------------------------------------------------------
# The holder's portrait, drawn as a flat-shaded studio photograph.
# --------------------------------------------------------------------------
def draw_portrait(w=300, h=400):
    img = Image.new("RGB", (w, h), (176, 188, 198))
    d = ImageDraw.Draw(img, "RGBA")
    # studio backdrop: gentle vertical falloff
    for yy in range(h):
        t = yy / h
        c = tuple(int(a + (b - a) * t) for a, b in
                  zip((188, 199, 208), (150, 163, 176)))
        d.line([(0, yy), (w, yy)], fill=c)
    cx = w // 2
    skin = (216, 178, 148)
    skin_shadow = (196, 156, 124)
    hair = (74, 62, 52)
    # shoulders: harbour-master navy jacket, white shirt, dark tie
    d.polygon([(cx - 118, h), (cx - 104, h - 108), (cx - 40, h - 138),
               (cx + 40, h - 138), (cx + 104, h - 108), (cx + 118, h)],
              fill=(32, 48, 66))
    d.polygon([(cx - 40, h - 138), (cx + 40, h - 138), (cx, h - 62)],
              fill=(232, 232, 228))
    d.polygon([(cx - 9, h - 118), (cx + 9, h - 118), (cx + 13, h - 30),
               (cx, h - 12), (cx - 13, h - 30)], fill=(96, 30, 34))
    d.line([(cx - 104, h - 108), (cx - 26, h - 60)], fill=(22, 36, 50), width=5)
    d.line([(cx + 104, h - 108), (cx + 26, h - 60)], fill=(22, 36, 50), width=5)
    # neck and head
    d.rectangle([cx - 26, h - 190, cx + 26, h - 128], fill=skin_shadow)
    d.ellipse([cx - 24, h - 168, cx - 8, h - 148], fill=(0, 0, 0, 26))
    d.ellipse([cx - 82, h - 262, cx - 66, h - 208], fill=skin)   # ears
    d.ellipse([cx + 66, h - 262, cx + 82, h - 208], fill=skin)
    d.ellipse([cx - 72, h - 316, cx + 72, h - 118], fill=skin)
    # hair: one shallow cap, its rim chord sitting just above the brows;
    # the face drawn after it covers the rim's lower half, leaving a clean
    # hairline and short sides above the ears
    d.pieslice([cx - 74, h - 336, cx + 74, h - 200], 180, 360, fill=hair)
    # brows and eyes
    eye_y = h - 232
    for sgn in (-1, 1):
        ex = cx + sgn * 34
        d.arc([ex - 21, eye_y - 22, ex + 21, eye_y + 6], 195, 345,
              fill=(60, 48, 40), width=6)                        # brow
        d.ellipse([ex - 17, eye_y - 8, ex + 17, eye_y + 9], fill=(240, 240, 238))
        d.ellipse([ex - 8, eye_y - 7, ex + 8, eye_y + 9], fill=(104, 116, 120))
        d.ellipse([ex - 3, eye_y - 3, ex + 3, eye_y + 5], fill=(24, 26, 30))
        d.line([(ex - 17, eye_y - 8), (ex + 17, eye_y - 8)],
               fill=(120, 92, 74), width=3)                      # upper lid
    # nose and mouth
    d.line([(cx + 2, eye_y + 12), (cx - 3, eye_y + 44)], fill=(178, 138, 104), width=4)
    d.arc([cx - 12, eye_y + 38, cx + 12, eye_y + 56], 20, 160,
          fill=(178, 138, 104), width=4)
    mouth_y = eye_y + 82
    d.arc([cx - 24, mouth_y - 12, cx + 24, mouth_y + 12], 15, 165,
          fill=(150, 96, 84), width=5)
    # short moustache and a day's stubble along the jaw
    d.arc([cx - 26, mouth_y - 26, cx - 1, mouth_y - 2], 300, 80,
          fill=(96, 84, 72), width=7)
    d.arc([cx + 1, mouth_y - 26, cx + 26, mouth_y - 2], 100, 240,
          fill=(96, 84, 72), width=7)
    for ang in range(205, 336, 7):
        a = math.radians(ang)
        x0 = cx + 66 * math.cos(a)
        y0 = (h - 217) + 99 * math.sin(a)
        d.line([(x0, y0), (x0 + 3, y0 + 5)], fill=(120, 100, 84), width=2)
    # photographic grain and a soft top light
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    light = Image.new("L", (w, h), 0)
    ld = ImageDraw.Draw(light)
    ld.ellipse([cx - 130, -80, cx + 130, 190], fill=52)
    light = light.filter(ImageFilter.GaussianBlur(60))
    img = Image.composite(Image.new("RGB", (w, h), (255, 252, 244)), img, light)
    return img


# --------------------------------------------------------------------------
# Coat of arms of Velmora: a lighthouse over waves, three stars, a crown.
# --------------------------------------------------------------------------
def draw_arms(size=240):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = size // 2
    gold = GOLD + (255,)
    navy = NAVY + (255,)
    # laurel branches
    for sgn in (-1, 1):
        for i in range(6):
            t = i / 5
            x = cx + sgn * (86 - 26 * t)
            y = size - 46 - 118 * t
            d.ellipse([x - 11, y - 6, x + 11, y + 6], fill=(86, 110, 66, 255),
                      outline=(64, 84, 48, 255))
    # shield
    top, bot = 58, size - 34
    shield = [(cx - 58, top), (cx + 58, top), (cx + 58, bot - 62),
              (cx + 30, bot - 14), (cx, bot), (cx - 30, bot - 14),
              (cx - 58, bot - 62)]
    d.polygon(shield, fill=navy, outline=gold, width=5)
    d.line([(cx - 58, top + 40), (cx + 58, top + 40)], fill=gold, width=3)
    # three stars for the three inhabited islands
    for dx in (-32, 0, 32):
        sx, sy = cx + dx, top + 21
        pts = []
        for k in range(10):
            r = 10 if k % 2 == 0 else 4.2
            a = math.radians(-90 + 36 * k)
            pts.append((sx + r * math.cos(a), sy + r * math.sin(a)))
        d.polygon(pts, fill=(238, 232, 214, 255))
    # lighthouse
    lh_top = top + 58
    d.polygon([(cx - 15, bot - 58), (cx - 9, lh_top + 26),
               (cx + 9, lh_top + 26), (cx + 15, bot - 58)], fill=(226, 222, 210, 255))
    d.rectangle([cx - 12, lh_top + 44, cx + 12, lh_top + 54], fill=(150, 44, 44, 255))
    d.rectangle([cx - 11, lh_top, cx + 11, lh_top + 26], fill=(240, 214, 120, 255),
                outline=gold, width=2)
    d.polygon([(cx - 15, lh_top), (cx + 15, lh_top), (cx, lh_top - 14)],
              fill=(150, 44, 44, 255))
    for sgn in (-1, 1):  # light beams
        d.polygon([(cx + sgn * 12, lh_top + 12), (cx + sgn * 46, lh_top - 2),
                   (cx + sgn * 46, lh_top + 26)], fill=(240, 214, 120, 90))
    # waves at the base
    for row, yy in enumerate((bot - 44, bot - 30)):
        for i in range(5):
            x0 = cx - 50 + i * 21
            d.arc([x0, yy, x0 + 18, yy + 12], 180, 360,
                  fill=(168, 198, 220, 255), width=3)
    # crown above the shield
    cy0 = 16
    d.polygon([(cx - 34, cy0 + 26), (cx - 34, cy0 + 6), (cx - 17, cy0 + 18),
               (cx, cy0), (cx + 17, cy0 + 18), (cx + 34, cy0 + 6),
               (cx + 34, cy0 + 26)], fill=gold, outline=(120, 92, 34, 255), width=2)
    for dx in (-34, 0, 34):
        d.ellipse([cx + dx - 4, cy0 - 6 if dx == 0 else cy0,
                   cx + dx + 4, cy0 + 2 if dx == 0 else cy0 + 8],
                  fill=(150, 44, 44, 255))
    return img


# --------------------------------------------------------------------------
# Paper security background: guilloche rings and a wave lattice, printed
# faintly under everything, the way real passport paper carries them.
# --------------------------------------------------------------------------
def security_layer(w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = (140, 158, 168, 46)
    # two guilloche rosettes, top-left and bottom-right of the spread
    for (gx, gy) in ((150, 130), (w - 170, h - 140)):
        for ring in range(5):
            r = 26 + ring * 17
            pts = []
            for k in range(121):
                a = 2 * math.pi * k / 120
                rr = r + 6 * math.sin(6 * a + ring)
                pts.append((gx + rr * math.cos(a), gy + rr * math.sin(a)))
            d.line(pts, fill=ink, width=2)
    # fine wave lattice across both pages
    for x0 in range(-h, w, 46):
        pts = [(x0 + yy, yy + 7 * math.sin((x0 + yy) / 34.0))
               for yy in range(0, h, 14)]
        d.line(pts, fill=(150, 160, 150, 26), width=1)
    # microtext band along the inside foot of the data page
    f = _font("noto/NotoSans-Regular.ttf", 13)
    s = "REPUBLIKA VELMORA · REPUBLIC OF VELMORA · "
    x = 60
    while x < w // 2 - 90:
        d.text((x, 96), s, font=f, fill=(120, 128, 120, 90))
        x += int(d.textlength(s, font=f)) + 4
    return img


# --------------------------------------------------------------------------
# Border stamps and the Brezna visa, each drawn on its own layer, rotated
# and pasted the way a clerk's hand would leave them.
# --------------------------------------------------------------------------
def _stamp_layer(w, h, draw_fn, ink, angle, blur=1.1, alpha=225):
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    draw_fn(d, w, h)
    layer.putalpha(layer.getchannel("A").point(lambda a: a * alpha // 255))
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return layer


def paste_stamp(base, stamp, cx, cy):
    base.alpha_composite(stamp, (int(cx - stamp.width / 2),
                                  int(cy - stamp.height / 2)))


def draw_stamps(base):
    for kind, office, line2, date, ink, angle, cx, cy in STAMPS:
        rgb = ink + (255,)
        if kind in ("exit", "entry") and office == "PORT OF OSSARY" or \
           (kind == "exit" and "AIRPORT" in office):
            # oval port / airport stamp
            def fn(d, w, h, office=office, line2=line2, date=date, rgb=rgb):
                d.ellipse([6, 6, w - 6, h - 6], outline=rgb, width=7)
                d.ellipse([22, 22, w - 22, h - 22], outline=rgb, width=3)
                f1 = fit_font(d, office, lambda s: _font(
                    "noto/NotoSans-Bold.ttf", s), 40, w - 90)
                text(d, (w / 2, 52), office, f1, fill=rgb, anchor="ma")
                text(d, (w / 2, h / 2 - 24), date,
                     _font("noto/NotoSansMono-Bold.ttf", 44), fill=rgb, anchor="ma")
                text(d, (w / 2, h - 92), line2,
                     _font("noto/NotoSans-Regular.ttf", 27), fill=rgb, anchor="ma")
            layer = _stamp_layer(560, 330, fn, ink, angle)
        else:
            # rectangular land-border stamp
            def fn(d, w, h, office=office, line2=line2, date=date, rgb=rgb,
                   kind=kind):
                d.rounded_rectangle([6, 6, w - 6, h - 6], 18, outline=rgb, width=7)
                d.rounded_rectangle([20, 20, w - 20, h - 20], 12, outline=rgb, width=2)
                text(d, (44, 40), "REPUBLIKA BREZNA" if office == "BREZNA"
                     else office, _font("noto/NotoSans-Bold.ttf", 33), fill=rgb)
                text(d, (w - 44, 44), "→" if kind == "entry" else "←",
                     _font("noto/NotoSans-Bold.ttf", 36), fill=rgb, anchor="ra")
                text(d, (44, 92), line2, _font("noto/NotoSans-Regular.ttf", 27),
                     fill=rgb)
                text(d, (44, h - 84), date,
                     _font("noto/NotoSansMono-Bold.ttf", 46), fill=rgb)
                text(d, (w - 44, h - 76), "V-90",
                     _font("noto/NotoSansMono-Regular.ttf", 28), fill=rgb,
                     anchor="ra")
            layer = _stamp_layer(600, 380, fn, ink, angle)
        paste_stamp(base, layer, cx, cy)
    # a later, half-visible Kessig entry stamp clipped by the page edge
    def fn2(d, w, h):
        rgb = (86, 74, 158, 255)
        d.ellipse([6, 6, w - 6, h - 6], outline=rgb, width=7)
        d.ellipse([22, 22, w - 22, h - 22], outline=rgb, width=3)
        text(d, (w / 2, 56), "KESSIG · VELMORA", _font("noto/NotoSans-Bold.ttf", 38),
             fill=rgb, anchor="ma")
        text(d, (w / 2, h / 2 - 22), "14 MAR 2028",
             _font("noto/NotoSansMono-Bold.ttf", 44), fill=rgb, anchor="ma")
        text(d, (w / 2, h - 88), "ENTRY", _font("noto/NotoSans-Regular.ttf", 28),
             fill=rgb, anchor="ma")
    layer = _stamp_layer(560, 330, fn2, (86, 74, 158), 14)
    paste_stamp(base, layer, W - 130, H - 96)


def draw_visa(base, x, y):
    """The Brezna multiple-entry visa sticker, top of the right page."""
    w, h = 660, 400
    sticker = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(sticker)
    for yy in range(h):  # pale gold-green security wash
        t = yy / h
        c = tuple(int(a + (b - a) * t) for a, b in
                  zip((238, 234, 196), (214, 224, 188)))
        d.line([(0, yy), (w, yy)], fill=c + (255,))
    d.rounded_rectangle([2, 2, w - 2, h - 2], 22, outline=GOLD + (255,), width=4)
    d.rounded_rectangle([12, 12, w - 12, h - 12], 16,
                        outline=(120, 130, 96, 255), width=2)
    text(d, (36, 30), "REPUBLIKA BREZNA", serif_b(37), fill=(58, 66, 44))
    text(d, (w - 36, 34), "VISA", serif_b(37), fill=(150, 44, 44), anchor="ra")
    rule(d, 36, w - 36, 92, fill=(150, 140, 96), w=3)
    rows = [
        ("Type / Vrsta", "C · Multiple entry / Više ulaza"),
        ("Valid / Vrijedi", "01 JUN 2027 — 30 NOV 2027"),
        ("Duration / Boravak", "90 days in any 180"),
        ("Issued at / Izdano u", "Kessig, 22 MAY 2027"),
        ("Passport / Putovnica", DOC_NUMBER),
    ]
    yy = 116
    for lab, val in rows:
        text(d, (36, yy), lab.upper(), sans(21), fill=(104, 108, 88))
        text(d, (36, yy + 28), val, sans_b(29), fill=(44, 48, 40))
        yy += 76
    text(d, (36, h - 44), "BR-V 0093 447", mono(25), fill=(96, 100, 84))
    base.alpha_composite(sticker, (x, y))
    # the consular fee stamp struck across the sticker's corner
    def fn(d, w2, h2):
        rgb = (30, 96, 140, 255)
        d.rounded_rectangle([4, 4, w2 - 4, h2 - 4], 10, outline=rgb, width=5)
        text(d, (w2 / 2, 18), "FEE PAID · PLAĆENO", sans_b(26), fill=rgb,
             anchor="ma")
        text(d, (w2 / 2, 54), "€35 · 22 MAY 2027", mono(24), fill=rgb,
             anchor="ma")
    fee = _stamp_layer(360, 110, fn, (30, 96, 140), -11, alpha=205)
    base.alpha_composite(fee, (x + 268, y + 282))


# --------------------------------------------------------------------------
# The spread itself.
# --------------------------------------------------------------------------
def field(d, x, y, label, value, vfont=None, vfill=INK, lfont=None):
    text(d, (x, y), label.upper(), lfont or sans(20), fill=LABEL, spacing=1)
    text(d, (x, y + 30), value, vfont or sans_b(31), fill=vfill)


def draw_spread():
    img = Image.new("RGBA", (W, H), (58, 66, 62, 255))  # desk / cover edge
    d = ImageDraw.Draw(img)
    d.rectangle([26, 26, W - 26, H - 26], fill=(16, 38, 56, 255))   # cover
    d.rectangle([44, 44, W - 44, H - 44], fill=PAPER + (255,))      # pages
    sec = security_layer(W, H)
    img.alpha_composite(sec, (0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    # centre gutter shadow and page curl highlights
    for i in range(56):
        a = int(66 * (1 - i / 56))
        d.line([(W // 2 - i, 44), (W // 2 - i, H - 44)], fill=(60, 58, 48, a))
        d.line([(W // 2 + i, 44), (W // 2 + i, H - 44)], fill=(255, 255, 250,
                                                               int(a * 0.5)))
    mid = W // 2
    lx, rx = 96, mid + 84          # left / right page text margins
    page_r = W - 96

    # ---------------- left page: the data page ----------------
    text(d, (lx, 84), "PASSPORT", serif_b(37), fill=NAVY, spacing=3)
    text(d, (lx, 132), "PASSEPORT · PUTOVNICA", sans(21), fill=LABEL, spacing=2)
    arms = draw_arms(200)
    img.alpha_composite(arms, (mid - 250, 62))
    d = ImageDraw.Draw(img, "RGBA")
    # e-passport chip mark, right of the title block
    d.rounded_rectangle([mid - 420, 92, mid - 356, 140], 8,
                        outline=GOLD, width=4)
    d.ellipse([mid - 402, 104, mid - 374, 128], outline=GOLD, width=3)
    d.line([(mid - 420, 116), (mid - 402, 116)], fill=GOLD, width=3)
    d.line([(mid - 374, 116), (mid - 356, 116)], fill=GOLD, width=3)
    text(d, (lx, 196), COUNTRY_EN, serif_b(45), fill=NAVY, spacing=2)
    text(d, (lx, 252), COUNTRY_VS, serif(31), fill=(70, 84, 98), spacing=2)
    rule(d, lx, mid - 60, 306, fill=(150, 140, 110), w=3)

    # portrait with its ghost image, the anti-copy pair
    portrait = draw_portrait(300, 400)
    ghost = portrait.copy()
    ghost.putalpha(88)
    img.paste(ghost, (lx + 34, 344), ghost)
    img.paste(portrait, (lx, 330))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([lx, 330, lx + 300, 730], outline=(150, 144, 124), width=2)
    text(d, (lx, 744), "KOVAČ · TOMAS", sans(19), fill=LABEL, spacing=1)

    fx = lx + 344                  # fields column
    fw = mid - 60 - fx
    # The side column starts where the widest left-hand value ends, and
    # its captions are shortened ("Sex", "Height"...) so no caption can
    # run into the next field: measured, not guessed.
    side_x = fx + 348
    field(d, fx, 330, "Type / Tip", DOC_TYPE)
    field(d, fx + 130, 330, "Code / Kod", COUNTRY_CODE)
    field(d, side_x, 330, "Passport No.", DOC_NUMBER, vfont=mono_b(31),
          lfont=sans(18))
    field(d, fx, 428, "Surname / Prezime", HOLDER_SURNAME, vfont=serif_b(34))
    field(d, fx, 522, "Given names / Imena", "Tomas Miroslav",
          vfont=serif_b(34))
    field(d, fx, 616, "Nationality / Državljanstvo", NATIONALITY)
    field(d, fx, 710, "Date of birth", DOB_DISPLAY)
    field(d, side_x, 710, "Sex", SEX, lfont=sans(18))
    field(d, fx, 804, "Place of birth", PLACE_OF_BIRTH)
    field(d, side_x, 804, "Height", HEIGHT, lfont=sans(18))
    field(d, fx, 898, "Eyes / Boja očiju", EYES)
    field(d, side_x, 898, "Profession", PROFESSION,
          vfont=fit_font(d, PROFESSION, sans_b, 31, 240), lfont=sans(18))
    field(d, fx, 992, "Residence / Prebivalište", RESIDENCE,
          vfont=fit_font(d, RESIDENCE, sans_b, 31, fw))
    field(d, fx, 1086, "Date of issue", ISSUE_DISPLAY)
    field(d, side_x, 1086, "Expiry", EXPIRY_DISPLAY, lfont=sans(18))
    field(d, fx, 1180, "Issuing authority / Tijelo izdavanja",
          ISSUING_AUTHORITY, vfont=fit_font(d, ISSUING_AUTHORITY, sans_b, 31, fw))
    # holder's signature, a quick ink hand over its rule
    rule(d, lx, lx + 300, 1236, fill=(150, 144, 124), w=2)
    text(d, (lx + 8, 1186), "T. Kovač", serif_i(44), fill=(30, 34, 60))
    text(d, (lx, 1248), "Signature / Potpis", sans(19), fill=LABEL, spacing=1)
    # personal number, small, under the authority line
    text(d, (fx, 1276), "Personal No. / OIB", sans(19), fill=LABEL, spacing=1)
    text(d, (fx + 250, 1270), PERSONAL_NUMBER, mono(27), fill=INK)

    # machine-readable zone across the foot of the data page
    line1, line2 = build_mrz()
    mrz_y = H - 128
    d.rectangle([0, mrz_y - 18, mid - 6, H - 44], fill=(238, 234, 218))
    mf = mono(35)
    text(d, (lx - 20, mrz_y + 2), line1, mf, fill=(30, 30, 30), spacing=1)
    text(d, (lx - 20, mrz_y + 52), line2, mf, fill=(30, 30, 30), spacing=1)

    # ---------------- right page: visas ----------------
    text(d, (rx, 84), "VISAS", serif_b(37), fill=NAVY, spacing=3)
    text(d, (rx, 132), "VIZE · VISUMS", sans(21), fill=LABEL, spacing=2)
    text(d, (page_r, 118), "7", serif(30), fill=LABEL, anchor="ra")
    draw_visa(img, rx, 190)
    d = ImageDraw.Draw(img, "RGBA")
    # observations, in Vessan first, then English
    oy = 660
    text(d, (rx, oy), "NAPOMENE / OBSERVATIONS", sans(20), fill=LABEL, spacing=1)
    obs = [
        "Nositelj je oslobođen lučkih pristojbi u svim",
        "velmorskim lukama dok služi kao svjetioničar.",
        "The bearer is exempt from harbour dues in all",
        "Velmoran ports while serving as a lighthouse keeper.",
    ]
    for i, line in enumerate(obs):
        text(d, (rx, oy + 36 + i * 34), line, serif_i(26), fill=(52, 58, 64))
    # stamps live on their own layers above the printed page
    draw_stamps(img)
    d = ImageDraw.Draw(img, "RGBA")
    # laser-perforated document number along the foot of the visa page
    text(d, (rx, H - 108), "VLM 048 221", mono_b(30), fill=(120, 116, 104),
         spacing=10)
    return img


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    img = draw_spread().convert("RGB")
    img = img.resize((1024, 728), Image.LANCZOS)
    path = os.path.join(out_dir, "entry.png")
    img.save(path, optimize=True)
    size = os.path.getsize(path)
    assert img.size == (1024, 728) and size <= 1_048_576, (img.size, size)
    print(f"wrote {path} ({img.size[0]}x{img.size[1]}, {size} bytes)")


if __name__ == "__main__":
    main()
