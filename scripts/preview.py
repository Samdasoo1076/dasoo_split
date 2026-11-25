"""Render a quick PNG preview of a generated board.

F.Cu is drawn red, B.Cu blue, vias white, front silkscreen light grey, and the
legend of every key (``Home``, ``End``, ``Up`` ...) is printed in the middle of
the key so the layout can be checked at a glance.

Run:  python3 scripts/preview.py left
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from pcbgen.geom import place

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FONT_PATHS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def render(board, path, scale=4.0, labels=True, region=None):
    x0, y0, x1, y1 = region or board.cfg["outline"]
    W = int((x1 - x0) * scale) + 20
    H = int((y1 - y0) * scale) + 20
    img = Image.new("RGB", (W, H), (16, 16, 18))
    d = ImageDraw.Draw(img)

    def P(x, y):
        return ((x - x0) * scale + 10, (y - y0) * scale + 10)

    # front silkscreen first, so copper sits on top of it.  Footprint graphics
    # are local, so every point goes through the placement (parts such as the
    # USB-C link port are placed turned 180 degrees).
    for fp in board.fps:
        for g in fp.graphics:
            if g[3] != "F.SilkS":
                continue
            if g[0] == "line":
                d.line([P(*place(fp.px, fp.py, g[1][0], g[1][1], fp.ang, fp.side)),
                        P(*place(fp.px, fp.py, g[2][0], g[2][1], fp.ang, fp.side))],
                       fill=(96, 96, 100), width=max(1, int(g[4] * scale)))
            elif g[0] == "circle":
                (cx, cy), r = g[1], g[2][1]
                a, b = (P(*place(fp.px, fp.py, cx - r, cy - r, fp.ang, fp.side)),
                        P(*place(fp.px, fp.py, cx + r, cy + r, fp.ang, fp.side)))
                d.ellipse([a[0], a[1], b[0], b[1]], outline=(96, 96, 100),
                          width=max(1, int(g[4] * scale)))

    # board cutouts (stabilizer housings) on Edge.Cuts -- footprint graphics are
    # stored in local coordinates, so they are placed with the footprint's own
    # position, rotation and side
    for fp in board.fps:
        for g in fp.graphics:
            if g[3] != "Edge.Cuts" or g[0] != "line":
                continue
            a = place(fp.px, fp.py, g[1][0], g[1][1], fp.ang, fp.side)
            b = place(fp.px, fp.py, g[2][0], g[2][1], fp.ang, fp.side)
            d.line([P(*a), P(*b)], fill=(150, 255, 190),
                   width=max(1, int(0.2 * scale)))

    # pads
    for fp in board.fps:
        for p in fp.pads:
            if p.is_hole:
                a = P(p.gx - p.w / 2, p.gy - p.h / 2)
                b = P(p.gx + p.w / 2, p.gy + p.h / 2)
                d.ellipse([a[0], a[1], b[0], b[1]],
                          fill=(30, 30, 34), outline=(120, 120, 90))
            else:
                for lay in p.pad_layers():
                    col = (200, 120, 60) if lay == "F.Cu" else (80, 120, 220)
                    if p.shape == "circle":
                        c = P(p.gx, p.gy)
                        r = p.w / 2 * scale
                        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=col)
                    else:
                        a, b = P(p.gx - p.w / 2, p.gy - p.h / 2), P(p.gx + p.w / 2, p.gy + p.h / 2)
                        d.rectangle([a[0], a[1], b[0], b[1]], fill=col)

    for tr in board.tracks:
        col = (255, 90, 60) if tr.layer == "F.Cu" else (90, 150, 255)
        d.line([P(*tr.a), P(*tr.b)], fill=col, width=max(1, int(tr.width * scale)))

    for v in board.vias:
        c = P(v.x, v.y)
        r = max(1.5, v.dia / 2 * scale)
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(235, 235, 235))

    # key legends
    if labels:
        f = _font(max(9, int(2.4 * scale)))
        fs = _font(max(8, int(2.0 * scale)))
        for k in board.keys:
            cx, cy = P(k["cx"], k["cy"])
            txt = k["label"]
            font = f
            if txt in ("BSpc", "Enter", "RShift", "LShift", "Caps", "LCtrl"):
                font = fs
            w = d.textlength(txt, font=font)
            fill = (250, 230, 150) if k["kind"] == "encoder" else (225, 225, 225)
            d.text((cx - w / 2, cy - font.size * 0.7), txt, font=font, fill=fill)

    a, b = P(x0, y0), P(x1, y1)
    d.rectangle([a[0], a[1], b[0], b[1]], outline=(120, 220, 120), width=2)
    title = "choc-split-60 %s  -  %d keys" % (board.hand, len(board.keys))
    d.text((14, 12), title, font=_font(max(12, int(3.2 * scale))), fill=(160, 240, 160))
    img.save(path)
    return path


def render_stab_details(board, hand, root):
    """One 12 px/mm crop around every stabilizer key, for the docs."""
    from pcbgen.layout import stab_keys
    out = []
    for k in stab_keys(hand):
        cx, cy = k["cx"], k["cy"]
        hw = k["wu"] * 19.05 / 2 + 12.0
        region = (cx - hw, cy - 16.0, cx + hw, cy + 24.0)
        path = os.path.join(root, "docs", "detail-%s-%s.png" % (hand, k["label"].lower()))
        render(board, path, scale=10.0, labels=True, region=region)
        out.append(path)
    return out


if __name__ == "__main__":
    import generate_pcb as g
    args = sys.argv[1:]
    if args[:1] == ["detail"]:
        args = args[1:] or ["left", "right"]
        for hand in args:
            b, r = g.build(hand, verbose=True)
            for path in render_stab_details(b, hand, g.ROOT):
                print("wrote", path)
        sys.exit(0)
    hands = args or ["left", "right"]
    for hand in hands:
        b, r = g.build(hand, verbose=True)
        out = os.path.join(g.ROOT, "docs", "preview-%s.png" % hand)
        render(b, out)
        print("wrote", out, "failed", r.failed)
