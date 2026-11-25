"""Render per-side review images for r/PrintedCircuitBoard posts.

That subreddit asks for one image per copper side ("2D PCB top" / "2D PCB
bottom") with no net names, no pad numbers and nothing that is not in the
gerbers, so this renderer draws:

  * one copper layer at a time (F.Cu for the top image, B.Cu for the bottom),
  * only the silkscreen of the side being shown,
  * pads, through holes and vias,
  * the board outline.

The bottom image is mirrored left-right, the way a bottom view is exported.

Run:  python3 scripts/review_images.py
"""

import os

from PIL import Image, ImageDraw

import generate_pcb as g
import preview
from pcbgen.geom import place

OUT = os.path.join(g.ROOT, "docs", "review")

BG = (18, 24, 20)          # board area (dark, like a soldermask)
COPPER = (222, 176, 92)    # copper: gold shade
SILK = (238, 238, 238)     # silkscreen: white
HOLE = (8, 8, 8)           # drilled holes: black
VIA = (200, 200, 200)
OUTLINE = (120, 220, 120)


def render_side(board, path, copper, silk, mirror, title, scale=5.0):
    x0, y0, x1, y1 = board.cfg["outline"]
    W = int((x1 - x0) * scale) + 20
    H = int((y1 - y0) * scale) + 20
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    def P(x, y):
        if mirror:
            x = x1 - (x - x0)
        return ((x - x0) * scale + 10, (y - y0) * scale + 10)

    # silkscreen of the shown side
    for fp in board.fps:
        for gr in fp.graphics:
            if gr[3] != silk:
                continue
            if gr[0] == "line":
                d.line([P(*gr[1]), P(*gr[2])], fill=SILK,
                       width=max(1, int(gr[4] * scale)))
            elif gr[0] == "circle":
                (cx, cy), r = gr[1], gr[2][1]
                a, b = P(cx - r, cy - r), P(cx + r, cy + r)
                d.ellipse([a[0], a[1], b[0], b[1]], outline=SILK,
                          width=max(1, int(gr[4] * scale)))

    # pads: copper on the shown layer, holes always
    for fp in board.fps:
        for p in fp.pads:
            if p.is_hole:
                a = P(p.gx - p.w / 2, p.gy - p.h / 2)
                b = P(p.gx + p.w / 2, p.gy + p.h / 2)
                d.ellipse([min(a[0], b[0]), min(a[1], b[1]),
                           max(a[0], b[0]), max(a[1], b[1])], fill=HOLE)
            elif copper in p.pad_layers():
                if p.shape == "circle":
                    c = P(p.gx, p.gy)
                    r = p.w / 2 * scale
                    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=COPPER)
                else:
                    a, b = P(p.gx - p.w / 2, p.gy - p.h / 2), P(p.gx + p.w / 2, p.gy + p.h / 2)
                    d.rectangle([min(a[0], b[0]), min(a[1], b[1]),
                                 max(a[0], b[0]), max(a[1], b[1])], fill=COPPER)

    # tracks of the shown layer
    for tr in board.tracks:
        if tr.layer != copper:
            continue
        d.line([P(*tr.a), P(*tr.b)], fill=COPPER, width=max(1, int(tr.width * scale)))

    for v in board.vias:
        c = P(v.x, v.y)
        r = max(1.5, v.dia / 2 * scale)
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=VIA)

    # board cutouts of the stabilizer housings (footprint graphics are local)
    for fp in board.fps:
        for gr in fp.graphics:
            if gr[3] != "Edge.Cuts" or gr[0] != "line":
                continue
            a = place(fp.px, fp.py, gr[1][0], gr[1][1], fp.ang, fp.side)
            b = place(fp.px, fp.py, gr[2][0], gr[2][1], fp.ang, fp.side)
            d.line([P(*a), P(*b)], fill=OUTLINE,
                   width=max(1, int(0.2 * scale)))

    a, b = P(x0, y0), P(x1, y1)
    d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])],
                outline=OUTLINE, width=2)
    d.rectangle([10, 10, W - 10, H - 10], outline=OUTLINE, width=1)
    d.text((14, 12), title, font=preview._font(max(12, int(3.2 * scale))), fill=OUTLINE)
    img.save(path)
    return path


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for hand in ("left", "right"):
        board, report = g.build(hand, verbose=False)
        for side, copper, silk, mirror in (
            ("top", "F.Cu", "F.SilkS", False),
            ("bottom", "B.Cu", "B.SilkS", True),
        ):
            path = os.path.join(OUT, "pcb-%s-%s.png" % (hand, side))
            render_side(board, path, copper, silk, mirror,
                        "choc-split-60 %s - %s, %s" % (hand, copper, side))
            print("wrote", path)
        print(hand, "checks:", report.failed or "all passed")
