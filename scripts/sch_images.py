"""Render the KiCad schematics to high resolution review PNGs.

`kicad-cli` is not installed in this container, so this script reads the
`.kicad_sch` S-expression files itself and draws them with Pillow: symbol
bodies (outline + background fill), pins with their numbers and names,
reference / value fields, every wire, junction, net label, no-connect marker
and note text, on a sheet with the KiCad style frame and title block.

Every string is placed through :func:`Renderer.text`, which remembers the ink
box of the text; :func:`Renderer.collisions` then lists text pairs whose boxes
overlap, so a layout that renders cleanly can be proven instead of eyeballed
(the script exits non zero when anything collides or leaves the sheet).

Run:  python3 scripts/sch_images.py
      python3 scripts/sch_images.py --half left --check   # collision report only
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FONT_CANDIDATES = {
    False: [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/local/lib/python3.12/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf",
    ],
    True: [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/local/lib/python3.12/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf",
    ],
}

# ---------------------------------------------------------------- colours
BG = (255, 255, 255)
FRAME = (132, 0, 0)
FRAME_TXT = (132, 0, 0)
BODY_LINE = (132, 0, 0)
BODY_FILL = (255, 255, 194)
PIN = (132, 0, 0)
PIN_NUM = (169, 0, 0)
PIN_NAME = (0, 100, 100)
FIELD = (0, 132, 132)
LABEL = (0, 0, 0)
WIRE = (0, 132, 0)
JUNCTION = (0, 132, 0)
NOCONNECT = (0, 0, 194)
NOTE = (0, 0, 132)

PAPER = {"A4": (297.0, 210.0), "A3": (420.0, 297.0),
         "A2": (594.0, 420.0), "A1": (841.0, 594.0), "A0": (1189.0, 841.0)}

CROSS_GAP = 0.254          # half size of the no-connect X, mm (KiCad default)


# ------------------------------------------------------------------ s-expr
class Sym(str):
    """A quoted string from the file (kept apart from bare atoms)."""


def parse_sexp(text):
    stack = [[]]
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "(":
            stack.append([])
            i += 1
        elif c == ")":
            node = stack.pop()
            stack[-1].append(node)
            i += 1
        elif c == '"':
            i += 1
            buf = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    buf.append(text[i + 1])
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            stack[-1].append(Sym("".join(buf)))
            i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            stack[-1].append(text[i:j])
            i = j
    return stack[0][0]


def kids(node, tag):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == tag]


def kid(node, tag):
    for c in node[1:]:
        if isinstance(c, list) and c and c[0] == tag:
            return c
    return None


def fnum(node, tag, idx=1, default=None):
    c = kid(node, tag)
    if c is None or len(c) <= idx:
        return default
    return float(c[idx])


def points(node):
    """`(pts (xy a b) (xy c d) ...)` -> [(a, b), (c, d)]"""
    p = kid(node, "pts")
    if p is None:
        return []
    return [(float(xy[1]), float(xy[2])) for xy in kids(p, "xy")]


def stroke_width(node, default=0.1524):
    s = kid(node, "stroke")
    if s is not None:
        w = kid(s, "width")
        if w is not None and float(w[1]) > 0:
            return float(w[1])
    return default


def fill_type(node):
    f = kid(node, "fill")
    if f is None:
        return "none"
    t = kid(f, "type")
    return t[1] if t is not None else "none"


def effects_of(node):
    """Return (size_mm, justify, hidden) of an element's `effects`."""
    e = kid(node, "effects")
    size, justify, hidden = 1.27, ("center", "center"), False
    if e is None:
        return size, justify, hidden
    if "hide" in [x for x in e[1:] if isinstance(x, str)]:
        hidden = True
    f = kid(e, "font")
    if f is not None:
        s = kid(f, "size")
        if s is not None:
            size = float(s[1])
        if "hide" in [x for x in f[1:] if isinstance(x, str)]:
            hidden = True
    j = kid(e, "justify")
    if j is not None:
        jt = [x for x in j[1:] if isinstance(x, str)]
        horiz = "center"
        vert = "center"
        if "left" in jt:
            horiz = "left"
        elif "right" in jt:
            horiz = "right"
        if "top" in jt:
            vert = "top"
        elif "bottom" in jt:
            vert = "bottom"
        justify = (horiz, vert)
    return size, justify, hidden


# ------------------------------------------------------------------ render
class Renderer:
    def __init__(self, page_w, page_h, scale):
        self.pw, self.ph = page_w, page_h
        self.s = float(scale)
        self.img = Image.new("RGB", (int(page_w * self.s) + 1,
                                     int(page_h * self.s) + 1), BG)
        self.d = ImageDraw.Draw(self.img)
        self._fonts = {}
        self.texts = []          # (label, box, size_mm)
        self.issues = []

    # -- geometry
    def P(self, x, y):
        return (x * self.s, y * self.s)

    def box(self, x0, y0, x1, y1):
        a = self.P(x0, y0)
        b = self.P(x1, y1)
        return [min(a[0], b[0]), min(a[1], b[1]),
                max(a[0], b[0]), max(a[1], b[1])]

    def line(self, pts, color, width_mm, cap=True):
        w = max(1, int(round(width_mm * self.s)))
        xy = [self.P(*p) for p in pts]
        if len(xy) > 2:
            self.d.line(xy, fill=color, width=w, joint="curve")
        else:
            self.d.line(xy, fill=color, width=w)
        if cap and len(xy) <= 2 and w > 2:
            r = w / 2.0
            for p in xy:
                self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)

    # -- text
    def font(self, size_mm, bold=False):
        key = (round(size_mm, 3), bold)
        if key not in self._fonts:
            px = max(7, int(round(size_mm * self.s * 1.38)))
            for path in FONT_CANDIDATES[bold]:
                if os.path.exists(path):
                    try:
                        self._fonts[key] = ImageFont.truetype(path, px)
                        break
                    except OSError:
                        pass
            else:
                self._fonts[key] = ImageFont.load_default()
        return self._fonts[key]

    def text(self, s, x, y, size, color, justify=("center", "center"),
             bold=False, angle=0, name=None):
        """Draw text with a KiCad style anchor; remember its ink box."""
        if not s:
            return None
        f = self.font(size, bold)
        px, py = self.P(x, y)
        anchor = {("left", "center"): "lm", ("center", "center"): "mm",
                  ("right", "center"): "rm", ("left", "bottom"): "ls",
                  ("center", "bottom"): "ms", ("right", "bottom"): "rs",
                  ("left", "top"): "la", ("center", "top"): "ma",
                  ("right", "top"): "ra"}[justify]
        if angle:
            # rotated text: render on a scratch canvas and rotate in place
            return self._text_rot(s, px, py, f, size, color, anchor, angle, name)
        self.d.text((px, py), s, font=f, fill=color, anchor=anchor)
        b = self.d.textbbox((px, py), s, font=f, anchor=anchor)
        self.texts.append((name or s, b, size))
        return b

    def _text_rot(self, s, px, py, f, size, color, anchor, angle, name):
        tmp = Image.new("RGBA", (int(f.size * len(s) * 1.2) + 4,
                                 int(f.size * 2) + 4), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((2, 2), s, font=f, fill=color, anchor="la")
        bb = td.textbbox((2, 2), s, font=f, anchor="la")
        tmp = tmp.crop(bb)
        tmp = tmp.rotate(-angle, expand=True, resample=Image.BICUBIC)
        w, h = tmp.size
        img = self.img.convert("RGBA")
        pos = (int(px - w / 2), int(py - h / 2))
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        layer.paste(tmp, pos, tmp)
        self.img = Image.alpha_composite(img, layer).convert("RGB")
        self.d = ImageDraw.Draw(self.img)
        box = [pos[0], pos[1], pos[0] + w, pos[1] + h]
        self.texts.append((name or s, box, size))
        return box

    # -- verification
    def collisions(self, pad_mm=0.06):
        bad = []
        t = self.texts
        pad = pad_mm * self.s
        for i in range(len(t)):
            ai, bi, _ = t[i]
            for j in range(i + 1, len(t)):
                aj, bj, _ = t[j]
                if (bi[0] - pad < bj[2] and bj[0] - pad < bi[2] and
                        bi[1] - pad < bj[3] and bj[1] - pad < bi[3]):
                    bad.append((ai, aj))
        return bad

    def outside(self):
        W, H = self.img.size
        return [(n, b) for n, b, _ in self.texts
                if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H]


# --------------------------------------------------------------- symbols
class Schematic:
    def __init__(self, path):
        with open(path) as f:
            doc = parse_sexp(f.read())
        self.path = path
        self.doc = doc
        paper = kid(doc, "paper")
        self.paper = paper[1] if paper and isinstance(paper[1], str) else "A3"
        self.libs = {}
        libs = kid(doc, "lib_symbols")
        if libs is not None:
            for s in kids(libs, "symbol"):
                self.libs[str(s[1])] = s
        self.items = [c for c in doc[1:] if isinstance(c, list) and c]

    def symbols(self):
        return [n for n in self.items if n[0] == "symbol" and kid(n, "lib_id")]


def transform(pt, sx, sy, ang, mirror):
    x, y = pt
    if mirror == "y":
        x = -x
    elif mirror == "x":
        y = -y
    if ang:
        import math
        a = math.radians(ang)
        x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    return (sx + x, sy - y)


def pin_dir(ang):
    """Unit vector (local, y up) a pin of the given angle runs along."""
    return {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[int(ang) % 360]


def draw_schematic(sch, R, title_lines):
    page = PAPER.get(sch.paper, PAPER["A3"])

    # ---- sheet frame first, so everything sits on top of it
    draw_frame(R, page, title_lines)

    # ---- wires
    for n in sch.items:
        if n[0] == "wire":
            pts = points(n)
            if len(pts) >= 2:
                R.line(pts, WIRE, stroke_width(n, 0.1524))

    # ---- junctions
    for n in sch.items:
        if n[0] == "junction":
            at = kid(n, "at")
            if at:
                x, y = float(at[1]), float(at[2])
                r = 0.508
                a, b = R.P(x - r, y - r), R.P(x + r, y + r)
                R.d.ellipse([a[0], a[1], b[0], b[1]], fill=JUNCTION)

    # ---- symbol instances
    for n in sch.symbols():
        lib_id = str(kid(n, "lib_id")[1])
        lib = sch.libs.get(lib_id)
        at = kid(n, "at")
        sx, sy, ang = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
        mir = kid(n, "mirror")
        mirror = mir[1] if mir and len(mir) > 1 else None
        if lib is not None:
            draw_lib_body(R, lib, sx, sy, ang, mirror)

        # properties (Reference / Value; the rest are hidden)
        for p in kids(n, "property"):
            name, value = str(p[1]), str(p[2])
            if name not in ("Reference", "Value") or not value:
                continue
            size, justify, hidden = effects_of(p)
            if hidden:
                continue
            pat = kid(p, "at")
            px, py = float(pat[1]), float(pat[2])
            pang = float(pat[3]) if len(pat) > 3 else 0.0
            col = FIELD
            bold = name == "Reference"
            R.text(value, px, py, size, col, justify, bold=bold,
                   angle=pang, name="%s %s" % (name, value))

    # ---- net labels
    for n in sch.items:
        if n[0] in ("label", "global_label", "hierarchical_label"):
            txt = str(n[1])
            at = kid(n, "at")
            x, y = float(at[1]), float(at[2])
            ang = float(at[3]) if len(at) > 3 else 0.0
            size, justify, _ = effects_of(n)
            horiz, vert = justify
            if vert == "center":
                vert = "bottom"
            # lift the text off the wire it is attached to
            oy = -0.42 if vert == "bottom" else 0.42
            R.text(txt, x, y + oy, size, LABEL, (horiz, vert),
                   angle=ang, name="net %s" % txt)

    # ---- no-connect crosses
    for n in sch.items:
        if n[0] == "no_connect":
            at = kid(n, "at")
            x, y = float(at[1]), float(at[2])
            g = CROSS_GAP
            R.line([(x - g, y - g), (x + g, y + g)], NOCONNECT, 0.15, cap=False)
            R.line([(x - g, y + g), (x + g, y - g)], NOCONNECT, 0.15, cap=False)

    # ---- note text
    for n in sch.items:
        if n[0] == "text":
            txt = str(n[1])
            at = kid(n, "at")
            x, y = float(at[1]), float(at[2])
            ang = float(at[3]) if len(at) > 3 else 0.0
            size, justify, _ = effects_of(n)
            R.text(txt, x, y, size, NOTE, justify, bold=True, angle=ang,
                   name="note")


def draw_lib_body(R, lib, sx, sy, ang, mirror):
    def T(pt):
        return transform(pt, sx, sy, ang, mirror)

    # graphics unit(s): the "NAME_0_1" style children hold the drawing
    for unit in kids(lib, "symbol"):
        for g in unit[1:]:
            if not isinstance(g, list) or not g:
                continue
            kind = g[0]
            fill = fill_type(g)
            w = stroke_width(g, 0.1524)
            if kind == "rectangle":
                s = kid(g, "start")
                e = kid(g, "end")
                a = T((float(s[1]), float(s[2])))
                b = T((float(e[1]), float(e[2])))
                xy = [min(a[0], b[0]), min(a[1], b[1]),
                      max(a[0], b[0]), max(a[1], b[1])]
                xy = [xy[0] * R.s, xy[1] * R.s, xy[2] * R.s, xy[3] * R.s]
                if fill in ("background", "outline"):
                    R.d.rectangle(xy, fill=BODY_FILL if fill == "background" else BODY_LINE)
                R.d.rectangle(xy, outline=BODY_LINE,
                              width=max(1, int(round(w * R.s))))
            elif kind in ("polyline", "line"):
                pts = [T(p) for p in points(g)]
                if not pts:
                    continue
                if fill in ("background", "outline") and len(pts) > 2:
                    R.d.polygon([R.P(*p) for p in pts],
                                fill=BODY_FILL if fill == "background" else BODY_LINE)
                R.line(pts, BODY_LINE, w)
            elif kind == "circle":
                c = kid(g, "center")
                rad = kid(g, "radius")
                cx, cy = T((float(c[1]), float(c[2])))
                rr = float(rad[1])
                a = R.P(cx - rr, cy - rr)
                b = R.P(cx + rr, cy + rr)
                if fill in ("background", "outline"):
                    R.d.ellipse([a[0], a[1], b[0], b[1]], fill=BODY_FILL)
                R.d.ellipse([a[0], a[1], b[0], b[1]], outline=BODY_LINE,
                            width=max(1, int(round(w * R.s))))
            elif kind == "text":
                txt = str(g[1])
                at = kid(g, "at")
                size, justify, hidden = effects_of(g)
                cx, cy = T((float(at[1]), float(at[2])))
                if not hidden:
                    R.text(txt, cx, cy, size, BODY_LINE, justify,
                           name="body text %s" % txt)
            # pins live in the second unit
            elif kind == "pin":
                draw_pin(R, g, lib, T, R)


def draw_pin(R, pin, lib, T, rend):
    at = kid(pin, "at")
    lx, ly, pang = float(at[1]), float(at[2]), float(at[3])
    length = float(kid(pin, "length")[1])
    dx, dy = pin_dir(pang)
    conn_local = (lx, ly)
    end_local = (lx + dx * length, ly + dy * length)
    conn = T(conn_local)
    end = T(end_local)
    R.line([conn, end], PIN, 0.1524, cap=False)

    pin_names_hidden = lib is not None and kid(lib, "pin_names") is not None and \
        "hide" in [x for x in kid(lib, "pin_names")[1:] if isinstance(x, str)]
    pin_numbers_hidden = lib is not None and kid(lib, "pin_numbers") is not None and \
        "hide" in [x for x in kid(lib, "pin_numbers")[1:] if isinstance(x, str)]
    offset = 1.016
    if lib is not None:
        pn = kid(lib, "pin_names")
        if pn is not None:
            o = kid(pn, "offset")
            if o is not None:
                offset = float(o[1])

    # pin number: above the line, centred on it
    if not pin_numbers_hidden:
        num = kid(pin, "number")
        if num is not None:
            size, _, _ = effects_of(num)
            mx, my = T(((lx + end_local[0]) / 2.0, (ly + end_local[1]) / 2.0))
            if abs(dx) > 0:
                R.text(str(num[1]), mx, my - 0.55, size, PIN_NUM, ("center", "bottom"),
                       name="pin number %s" % num[1])
            else:
                R.text(str(num[1]), mx + 0.55, my, size, PIN_NUM, ("left", "center"),
                       name="pin number %s" % num[1])

    # pin name: inside the body, past the pin end
    if not pin_names_hidden:
        nm = kid(pin, "name")
        if nm is not None and str(nm[1]):
            size, _, _ = effects_of(nm)
            if abs(dx) > 0:
                if dx > 0:
                    ax, ay = T((end_local[0] + offset, end_local[1]))
                    R.text(str(nm[1]), ax, ay, size, PIN_NAME, ("left", "center"),
                           name="pin name %s" % nm[1])
                else:
                    ax, ay = T((end_local[0] - offset, end_local[1]))
                    R.text(str(nm[1]), ax, ay, size, PIN_NAME, ("right", "center"),
                           name="pin name %s" % nm[1])
            else:
                if dy > 0:
                    ax, ay = T((end_local[0], end_local[1] + offset))
                    R.text(str(nm[1]), ax, ay, size, PIN_NAME, ("center", "bottom"),
                           name="pin name %s" % nm[1])
                else:
                    ax, ay = T((end_local[0], end_local[1] - offset))
                    R.text(str(nm[1]), ax, ay, size, PIN_NAME, ("center", "top"),
                           name="pin name %s" % nm[1])


def draw_frame(R, page, title_lines):
    pw, ph = page
    m = 10.0
    R.d.rectangle(R.box(m, m, pw - m, ph - m), outline=FRAME,
                  width=max(1, int(round(0.25 * R.s))))
    # zone marks
    step = 50.0
    n = int(round((pw - 2 * m) / step))
    for i in range(n + 1):
        x = m + i * step
        if x > pw - m:
            break
        R.line([(x, m), (x, m + 2.0)], FRAME, 0.15, cap=False)
        R.line([(x, ph - m - 2.0), (x, ph - m)], FRAME, 0.15, cap=False)
        if i < n:
            cx = min(x + step / 2.0, pw - m - step / 2.0)
            R.text(str(i + 1), cx, m - 1.2, 1.8, FRAME_TXT, ("center", "bottom"),
                   name="zone %d" % (i + 1))
            R.text(str(i + 1), cx, ph - m + 1.2, 1.8, FRAME_TXT, ("center", "top"),
                   name="zone top %d" % (i + 1))
    rows = int(round((ph - 2 * m) / step))
    letters = "ABCDEFGH"
    for i in range(rows + 1):
        y = m + i * step
        if y > ph - m:
            break
        R.line([(m, y), (m + 2.0, y)], FRAME, 0.15, cap=False)
        R.line([(pw - m - 2.0, y), (pw - m, y)], FRAME, 0.15, cap=False)
        if i < rows:
            cy = min(y + step / 2.0, ph - m - step / 2.0)
            R.text(letters[i], m - 1.2, cy, 1.8, FRAME_TXT, ("right", "center"),
                   name="row %s" % letters[i])
            R.text(letters[i], pw - m + 1.2, cy, 1.8, FRAME_TXT, ("left", "center"),
                   name="row right %s" % letters[i])

    # title block (bottom right)
    bw, bh = 118.0, 32.0
    x0, y1 = pw - m, ph - m
    x1 = x0 - bw
    y0 = y1 - bh
    R.d.rectangle(R.box(x1, y0, x0, y1), outline=FRAME,
                  width=max(1, int(round(0.2 * R.s))))
    for i, txt in enumerate(title_lines):
        yy = y0 + 4.6 + i * 5.6
        R.text(txt, x1 + 2.0, yy, 1.6, FRAME_TXT, ("left", "bottom"),
               bold=(i == 0), name="title %d" % i)
    R.line([(x1, y0 + 2.0), (x0, y0 + 2.0)], FRAME, 0.15, cap=False)


def render(half, out_path, title_lines, scale=None):
    sch_path = os.path.join(ROOT, "pcb", "choc-split-60-%s.kicad_sch" % half)
    sch = Schematic(sch_path)
    page = PAPER.get(sch.paper, PAPER["A3"])
    if scale is None:
        scale = 11.0 if page[0] >= 400 else 13.0
    R = Renderer(page[0], page[1], scale)
    draw_schematic(sch, R, title_lines)
    R.img.save(out_path, optimize=True)
    return R, page


def main(argv):
    halves = [a for a in argv if a in ("left", "right")] or ["left", "right"]
    check = "--check" in argv
    outdir = os.path.join(ROOT, "docs", "review")
    os.makedirs(outdir, exist_ok=True)
    bad = 0
    for half in halves:
        lines = [
            "choc-split-60 %s half - switches, diodes, controller, USB-C link, reset%s"
            % (half, ", rotary encoder" if half == "left" else ""),
            "Size A3   Date 2026-11-25   Rev 1.1   Sheet 1/1",
            "File pcb/choc-split-60-%s.kicad_sch   Project dasoo_split" % half,
            "Rendered by scripts/sch_images.py - COL2ROW matrix, one diode per key",
            "github.com/Samdasoo1076/dasoo_split",
        ]
        out = os.path.join(outdir, "sch-%s.png" % half)
        R, page = render(half, out, lines)
        print("%s: %s  %dx%d px  (%.1f px/mm)"
              % (half, out, R.img.size[0], R.img.size[1], R.s))
        coll = R.collisions()
        out_of_page = R.outside()
        if coll:
            bad += len(coll)
            print("  %d text collisions:" % len(coll))
            for a, b in coll[:40]:
                print("    %r <-> %r" % (a, b))
        if out_of_page:
            bad += len(out_of_page)
            print("  %d strings off the sheet:" % len(out_of_page))
            for a, _ in out_of_page[:20]:
                print("    %r" % (a,))
        if not coll and not out_of_page:
            print("  no text collisions, every string inside the sheet")
        if check:
            os.remove(out)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
