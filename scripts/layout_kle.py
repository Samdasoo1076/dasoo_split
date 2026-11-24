"""Draw the KLE style picture of the layout (docs/layout-kle.png).

The key table in :mod:`pcbgen.layout` is the single source of truth, so this
picture can never disagree with the PCB or the firmware: every keycap is drawn
at ``xu`` with its own width ``wu``, which is exactly what exposes a missing
row stagger.

Run:  python3 scripts/layout_kle.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pcbgen.layout import ROWS, keys   # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "docs", "layout-kle.png")

S = 58.0                    # pixels per key unit
GAP = 5                     # gap between keycaps, px
PAD = 26                    # inner padding of a half, px
HEAD = 46                   # room for the half's title, px
MARGIN = 30
BG = (20, 24, 30)
PANEL = (33, 39, 49)
PANEL_EDGE = (62, 72, 88)
ALPHA = (238, 238, 240)
ALPHA_TXT = (28, 30, 36)
MOD = (60, 68, 80)
MOD_TXT = (226, 231, 238)
MACRO = (50, 58, 70)
MACRO_TXT = (206, 216, 228)
ARROW = (112, 146, 196)
ARROW_TXT = (18, 22, 30)
ACCENT = (86, 196, 214)

MODS = {"Tab", "Caps", "LShift", "LCtrl", "LWin", "LAlt", "Space",
        "BSpc", "Enter", "RShift", "RAlt", "RCtrl", "Del"}
MACROS = {"Home", "End", "PgUp", "PgDn"}
ARROWS = {"Up", "Down", "Left", "Right"}

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def fit_font(text, w, h, size):
    """Largest font that keeps `text` inside a w x h box."""
    f = font(size)
    while size > 7:
        if f.getlength(text) <= w and size <= h:
            return f
        size -= 1
        f = font(size)
    return f


def half_box(hand):
    ks = keys(hand)
    x0 = min(k["xu"] for k in ks)
    x1 = max(k["xu"] + k["wu"] for k in ks)
    return x0, x1, len(ROWS[hand])


def draw_half(d, hand, ox, oy, title):
    x0, x1, nrow = half_box(hand)
    w = (x1 - x0) * S + 2 * PAD
    h = nrow * S + 2 * PAD + HEAD
    d.rounded_rectangle([ox, oy, ox + w, oy + h], radius=14,
                        fill=PANEL, outline=PANEL_EDGE, width=2)
    tf = fit_font(title, w - 2 * PAD, 22, 22)
    d.text((ox + PAD, oy + 14), title, font=tf, fill=(232, 236, 242))
    top = oy + HEAD + PAD * 0.4

    def P(u, v):
        return (ox + PAD + (u - x0) * S, top + v * S)

    for k in keys(hand):
        xu, wu, r = k["xu"], k["wu"], k["row"]
        a = P(xu, r)
        b = P(xu + wu, r + 1)
        box = [a[0] + GAP / 2, a[1] + GAP / 2, b[0] - GAP / 2, b[1] - GAP / 2]
        bw, bh = box[2] - box[0], box[3] - box[1]
        label = k["label"]
        if k["kind"] == "encoder":
            c = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            rad = min(bw, bh) / 2 - 2
            d.ellipse([c[0] - rad, c[1] - rad, c[0] + rad, c[1] + rad],
                      fill=MACRO, outline=ACCENT, width=3)
            f = fit_font("KNOB", rad * 1.6, 18, 18)
            d.text((c[0] - f.getlength("KNOB") / 2, c[1] - 9), "KNOB",
                   font=f, fill=ACCENT)
            continue
        if label in ARROWS:
            fill, txt = ARROW, ARROW_TXT
        elif label in MACROS:
            fill, txt = MACRO, MACRO_TXT
        elif label in MODS:
            fill, txt = MOD, MOD_TXT
        else:
            fill, txt = ALPHA, ALPHA_TXT
        d.rounded_rectangle(box, radius=6, fill=fill)
        f = fit_font(label, bw - 8, 20, 20)
        tw = f.getlength(label)
        d.text((box[0] + (bw - tw) / 2, box[1] + (bh - f.size) / 2 - 1),
               label, font=f, fill=txt)
    return w, h


def main():
    hands = ("left", "right")
    sizes = []
    for hand in hands:
        x0, x1, nrow = half_box(hand)
        sizes.append(((x1 - x0) * S + 2 * PAD, nrow * S + 2 * PAD + HEAD))
    W = int(sum(s[0] for s in sizes) + MARGIN * (len(hands) + 1))
    H = int(max(s[1] for s in sizes) + MARGIN * 2)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    titles = {
        "left": "Left Half: 33 keys + encoder, macro column 0.25u apart",
        "right": "Right Half: 38 keys, row starts -0.5 / 0 / 0.25 / -0.5 / 0.25u",
    }
    x = MARGIN
    for hand, (w, h) in zip(hands, sizes):
        draw_half(d, hand, x, MARGIN, titles[hand])
        x += w + MARGIN
    img.save(OUT)
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()
