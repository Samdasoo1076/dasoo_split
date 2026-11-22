"""Render a quick PNG preview of a generated board (F.Cu red, B.Cu blue)."""
import sys, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def render(board, path, scale=4.0, flip=False):
    x0, y0, x1, y1 = board.cfg["outline"]
    W = int((x1 - x0) * scale) + 20
    H = int((y1 - y0) * scale) + 20
    img = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(img)
    def P(x, y):
        return ((x - x0) * scale + 10, (y - y0) * scale + 10)
    # pads
    for fp in board.fps:
        for p in fp.pads:
            if p.is_hole:
                c = P(p.gx, p.gy)
                r = p.w / 2 * scale
                d.ellipse([c[0]-r, c[1]-r, c[0]+r, c[1]+r], fill=(30, 30, 34), outline=(90, 90, 90))
            else:
                for lay in p.pad_layers():
                    col = (200, 120, 60) if lay == "F.Cu" else (80, 120, 220)
                    if p.shape == "circle":
                        c = P(p.gx, p.gy)
                        r = p.w / 2 * scale
                        d.ellipse([c[0]-r, c[1]-r, c[0]+r, c[1]+r], fill=col)
                    else:
                        a, b = P(p.gx - p.w/2, p.gy - p.h/2), P(p.gx + p.w/2, p.gy + p.h/2)
                        d.rectangle([a[0], a[1], b[0], b[1]], fill=col)
    for tr in board.tracks:
        col = (255, 90, 60) if tr.layer == "F.Cu" else (90, 150, 255)
        d.line([P(*tr.a), P(*tr.b)], fill=col, width=max(1, int(tr.width*scale)))
    for v in board.vias:
        c = P(v.x, v.y)
        r = v.dia/2*scale
        d.ellipse([c[0]-r, c[1]-r, c[0]+r, c[1]+r], fill=(230, 230, 230))
    a, b = P(x0, y0), P(x1, y1)
    d.rectangle([a[0], a[1], b[0], b[1]], outline=(120, 220, 120), width=2)
    img.save(path)
    return path


if __name__ == "__main__":
    import generate_pcb as g
    hand = sys.argv[1] if len(sys.argv) > 1 else "left"
    b, r = g.build(hand, verbose=True)
    out = os.path.join(g.ROOT, "docs", "preview-%s.png" % hand)
    render(b, out)
    print("wrote", out, "failed", r.failed)
