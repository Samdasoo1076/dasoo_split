#!/usr/bin/env python3
"""Independent verification of the choc-split-60 KiCad boards.

Parses the generated .kicad_pcb files (does not import the generator) and
checks, for each half:

  1. every signal net is fully connected (no unconnected pad)
  2. no two copper items of different nets touch or come closer than the
     design clearance on the same layer
  3. switch <-> diode pairing is 1:1 with correct polarity (COL2ROW)
  4. Edge.Cuts forms a single closed loop and all copper is inside
  5. all tracks are 0/45/90 degrees and respect the minimum width
  6. a GND zone exists on both copper layers
  7. every switch of 2 u and wider carries the Kailh Choc v2 PCB mount
     stabilizer (4 oval clip holes of the 2.00 u pattern plus the two Edge.Cuts
     cutouts) and no copper comes near the holes or the cutouts
  8. no via sits on a pad (via in pad): every via is 0.30 mm or more from the
     copper edge of every pad and from every drilled hole
  9. every diode clears the hot swap socket of the key below by 3 mm or more
 10. the USB-C link port (J1) is present with all 16 pins plus the four shell
     legs, VBUS on VCC, both shell legs and the four GND pins on GND, D+/D- on
     the crossed UART pair (one half TX, the other RX), CC/SBU unconnected, and
     the connector turned so that its mouth faces the top board edge (the pin
     row 6.0 .. 8.5 mm inside it, no copper within 1 mm of the edge)

Usage:  python3 scripts/verify_pcb.py [pcb/*.kicad_pcb ...]
"""
import math
import os
import re
import sys
from collections import defaultdict

CLEAR = 0.20          # copper to copper clearance (mm)
EDGE_CLEAR = 0.30     # copper to board edge
HOLE_CLEAR = 0.30     # copper to NPTH hole / board cutout edge
VIA_PAD_CLEAR = 0.30  # via to any pad copper: a via may not sit on a pad
DIODE_SOCKET_CLEAR = 3.00   # diode to the socket of the key in the row below
MIN_W = 0.25          # thinnest track we accept
TOL = 1e-6

# Kailh Choc v2 PCB mount stabilizer, 2.00 u pattern (Salicylic-acid3 /
# Keeb-On! part, the same footprint serves the 2.25 u keys):
#   3.2 x 3.4 mm oval NPTH at (+-11.9, -6.2), 3.0 x 4.0 mm oval NPTH at
#   (+-11.9, +8.24), and two board cutouts x = 8.9 .. 14.9 (mirrored),
#   y = -3.75 .. +3.75.
STAB_MIN_U = 2.0
STAB_HOLES = ((11.9, -6.2, 3.2, 3.4), (11.9, 8.24, 3.0, 4.0))
STAB_CUTOUT = (8.9, -3.75, 14.9, 3.75)
CHOC_V2_PREFIX = "SW_Hotswap_Kailh_Choc_V2_"
V2_POST = (-5.0, 5.15, 1.8, 2.2)      # x, y, size along x, size along y
V1_PEG = (5.5, 0.0, 1.9)              # x, y, drill -- must be gone

# --------------------------------------------------------------------- parser
TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def parse(text):
    stack = [[]]
    for m in TOKEN.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append([])
        elif t == ")":
            top = stack.pop()
            stack[-1].append(top)
        else:
            if t.startswith('"'):
                stack[-1].append(t[1:-1])
            else:
                stack[-1].append(t)
    return stack[0][0]


def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def kid(node, name, default=None):
    for c in node:
        if isinstance(c, list) and c and c[0] == name:
            return c
    return default


def all_kids(node, name, out=None):
    if out is None:
        out = []
    for c in node:
        if isinstance(c, list):
            if c and c[0] == name:
                out.append(c)
            else:
                all_kids(c, name, out)
    return out


def fnum(x):
    return float(x)


# ------------------------------------------------------------------ geometry
def rot(x, y, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (x * c + y * s, -x * s + y * c)


def seg_dist(a, b, c, d):
    def ps(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))

    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    d1, d2 = cr(c, d, a), cr(c, d, b)
    d3, d4 = cr(a, b, c), cr(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(ps(a, c, d), ps(b, c, d), ps(c, a, b), ps(d, a, b))


def poly_of(cx, cy, w, h, ang, shape, n=20):
    """Conservative polygon for a pad."""
    if shape == "circle":
        r = w / 2.0 / math.cos(math.pi / n)
        pts = [(cx + r * math.cos(2 * math.pi * i / n),
                cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        return pts
    if shape == "oval":
        r = min(w, h) / 2.0
        ln = (max(w, h) / 2.0) - r
        pts = []
        for i in range(n // 2 + 1):
            a = -math.pi / 2 + math.pi * i / (n // 2)
            pts.append((ln + r * math.cos(a), r * math.sin(a)))
        for i in range(n // 2 + 1):
            a = math.pi / 2 + math.pi * i / (n // 2)
            pts.append((-ln + r * math.cos(a), r * math.sin(a)))
        if w < h:
            pts = [(y, x) for (x, y) in pts]
        return [(cx + rot(x, y, ang)[0], cy + rot(x, y, ang)[1]) for (x, y) in pts]
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [(cx + rot(x, y, ang)[0], cy + rot(x, y, ang)[1]) for (x, y) in pts]


def in_poly(p, poly):
    x, y = p
    inside = False
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y):
            if x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
                inside = not inside
    return inside


def seg_poly_dist(a, b, poly):
    if in_poly(a, poly) or in_poly(b, poly):
        return 0.0
    best = 1e9
    for i in range(len(poly)):
        c = poly[i]
        d = poly[(i + 1) % len(poly)]
        best = min(best, seg_dist(a, b, c, d))
        if best == 0.0:
            return 0.0
    return best


def pt_poly_dist(p, poly):
    if in_poly(p, poly):
        return 0.0
    return min(seg_dist(p, p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def poly_dist(P, Q):
    if any(in_poly(p, Q) for p in P) or any(in_poly(q, P) for q in Q):
        return 0.0
    best = 1e9
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        best = min(best, seg_poly_dist(a, b, Q))
        if best == 0.0:
            return 0.0
    return best


def cutout_rects(lines):
    """Group Edge.Cuts segments into closed loops and return their boxes."""
    def key(p):
        return (round(p[0], 4), round(p[1], 4))

    remaining = list(range(len(lines)))
    loops = []
    while remaining:
        i = remaining.pop(0)
        loop = [lines[i]]
        start, cur = key(lines[i][0]), key(lines[i][1])
        while cur != start and remaining:
            found = None
            for j in remaining:
                if key(lines[j][0]) == cur:
                    found = (j, key(lines[j][1]))
                    break
                if key(lines[j][1]) == cur:
                    found = (j, key(lines[j][0]))
                    break
            if not found:
                break
            j, nxt = found
            remaining.remove(j)
            loop.append(lines[j])
            cur = nxt
        loops.append(loop)
    out = []
    for loop in loops:
        pts = [p for a, b in loop for p in (a, b)]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        closed = abs(loop[-1][1][0] - loop[0][0][0]) < 1e-6 and \
            abs(loop[-1][1][1] - loop[0][0][1]) < 1e-6
        per = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in loop)
        out.append(dict(x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys),
                        edges=len(loop), closed=closed, perimeter=per))
    return out


# --------------------------------------------------------------------- items
class Item:
    def __init__(self, kind, net, layers, bbox, **kw):
        self.kind = kind
        self.net = net
        self.layers = layers
        self.bbox = bbox
        self.__dict__.update(kw)

    def bbox_expanded(self, m):
        x0, y0, x1, y1 = self.bbox
        return (x0 - m, y0 - m, x1 + m, y1 + m)


def bbox_overlap(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def item_dist(A, B, layer):
    """Minimum copper distance between two items that share a layer."""
    if A.kind == "pad" and B.kind == "pad":
        return poly_dist(A.poly, B.poly)
    if A.kind == "pad" and B.kind == "track":
        return max(0.0, seg_poly_dist(B.a, B.b, A.poly) - B.w / 2.0)
    if A.kind == "track" and B.kind == "pad":
        return max(0.0, seg_poly_dist(A.a, A.b, B.poly) - A.w / 2.0)
    if A.kind == "track" and B.kind == "track":
        return max(0.0, seg_dist(A.a, A.b, B.a, B.b) - A.w / 2.0 - B.w / 2.0)
    if A.kind == "via" and B.kind == "track":
        return max(0.0, seg_dist(B.a, B.b, (A.x, A.y), (A.x, A.y)) - A.r - B.w / 2.0)
    if A.kind == "track" and B.kind == "via":
        return max(0.0, seg_dist(A.a, A.b, (B.x, B.y), (B.x, B.y)) - B.r - A.w / 2.0)
    if A.kind == "via" and B.kind == "pad":
        return max(0.0, pt_poly_dist((A.x, A.y), B.poly) - A.r)
    if A.kind == "pad" and B.kind == "via":
        return max(0.0, pt_poly_dist((B.x, B.y), A.poly) - B.r)
    if A.kind == "via" and B.kind == "via":
        return max(0.0, math.hypot(A.x - B.x, A.y - B.y) - A.r - B.r)
    raise RuntimeError("bad pair")


# ------------------------------------------------------------------- loading
class Board:
    pass


def load(path):
    txt = open(path).read()
    root = parse(txt)
    b = Board()
    b.path = path
    b.name = os.path.basename(path)
    # nets
    b.nets = {}
    for n in kids(root, "net"):
        if len(n) >= 3:
            b.nets[n[2]] = int(n[1])
    b.pads = []
    b.tracks = []
    b.vias = []
    b.graphics = []
    b.zones = []
    b.refs = defaultdict(int)
    for fp in kids(root, "footprint"):
        layer = kid(fp, "layer")[1]
        at = kid(fp, "at")
        px, py = fnum(at[1]), fnum(at[2])
        pang = fnum(at[3]) if len(at) > 3 else 0.0
        ref = None
        for p in kids(fp, "property"):
            if p[1] == "Reference":
                ref = p[2]
        b.refs[ref] += 1
        side = "F" if layer == "F.Cu" else "B"
        fname = fp[1]
        for pad in kids(fp, "pad"):
            if pad[1] == "":
                num = ""
            else:
                num = pad[1]
            atyp = pad[2]
            shape = pad[3]
            pat = kid(pad, "at")
            lx, ly = fnum(pat[1]), fnum(pat[2])
            pang2 = fnum(pat[3]) if len(pat) > 3 else 0.0
            size = kid(pad, "size")
            w, h = fnum(size[1]), fnum(size[2])
            if side == "B":
                # KiCad keeps a back side footprint's stored frame unmirrored:
                # the pad is written where it sits on the board.  Mirroring it
                # here (as this checker used to) hides exactly the diode
                # pad/track mismatch it is supposed to catch.
                pass
            gx, gy = rot(lx, ly, pang)
            gx += px
            gy += py
            gang = pang + pang2 if side == "F" else pang + pang2
            lay = kid(pad, "layers")
            layers = []
            for l in lay[1:]:
                if l == "*.Cu":
                    layers = ["F.Cu", "B.Cu"]
                    break
                if l in ("F.Cu", "B.Cu"):
                    layers.append(l)
            netnode = kid(pad, "net")
            net = netnode[2] if netnode else None
            drill = kid(pad, "drill")
            hole = None
            if drill is not None and atyp != "smd":
                vals = [x for x in drill[1:] if not isinstance(x, list)]
                if vals and vals[0] == "oval":
                    hole = (fnum(vals[1]), fnum(vals[2]))
                elif vals:
                    hole = (fnum(vals[0]), fnum(vals[0]))
            poly = poly_of(gx, gy, w, h, gang, shape)
            if atyp == "np_thru_hole":
                if hole:
                    hshape = "oval" if abs(hole[0] - hole[1]) > 1e-9 else "circle"
                    b.pads.append(Item("pad", None, ["F.Cu", "B.Cu"],
                                       (gx - hole[0] / 2, gy - hole[1] / 2,
                                        gx + hole[0] / 2, gy + hole[1] / 2),
                                       poly=poly_of(gx, gy, hole[0], hole[1], gang, hshape),
                                       num="", ref=ref, fp=fname, x=gx, y=gy,
                                       w=hole[0], h=hole[1], hole=None, shape="hole",
                                       holdw=hole[0], holdh=hole[1], gang=gang))
                continue
            it = Item("pad", net, layers,
                      (min(p[0] for p in poly), min(p[1] for p in poly),
                       max(p[0] for p in poly), max(p[1] for p in poly)),
                      poly=poly, num=num, ref=ref, fp=fname, x=gx, y=gy,
                      w=w, h=h, hole=hole, shape=shape)
            b.pads.append(it)
            if hole and atyp == "np_thru_hole":
                # separate hole item (blocks all layers, no net)
                b.pads.append(Item("pad", None, ["F.Cu", "B.Cu"],
                                   (gx - hole[0] / 2, gy - hole[1] / 2,
                                    gx + hole[0] / 2, gy + hole[1] / 2),
                                   poly=poly_of(gx, gy, hole[0], hole[1], gang, "circle"),
                                   num="", ref=ref, fp=fname, x=gx, y=gy,
                                   w=hole[0], h=hole[1], hole=None, shape="hole"))
    for s in kids(root, "segment"):
        st = kid(s, "start")
        en = kid(s, "end")
        a = (fnum(st[1]), fnum(st[2]))
        bb = (fnum(en[1]), fnum(en[2]))
        w = fnum(kid(s, "width")[1])
        lay = kid(s, "layer")[1]
        net = b.nets.get("", 0)
        nn = kid(s, "net")
        net = None
        if nn:
            for name, idx in b.nets.items():
                if idx == int(nn[1]):
                    net = name
        it = Item("track", net, [lay],
                  (min(a[0], bb[0]) - w / 2, min(a[1], bb[1]) - w / 2,
                   max(a[0], bb[0]) + w / 2, max(a[1], bb[1]) + w / 2),
                  a=a, b=bb, w=w)
        b.tracks.append(it)
    for v in kids(root, "via"):
        at = kid(v, "at")
        x, y = fnum(at[1]), fnum(at[2])
        size = fnum(kid(v, "size")[1])
        nn = kid(v, "net")
        net = None
        if nn:
            for name, idx in b.nets.items():
                if idx == int(nn[1]):
                    net = name
        b.vias.append(Item("via", net, ["F.Cu", "B.Cu"],
                           (x - size / 2, y - size / 2, x + size / 2, y + size / 2),
                           x=x, y=y, r=size / 2))
    for g in kids(root, "gr_line"):
        lay = kid(g, "layer")[1]
        st = kid(g, "start")
        en = kid(g, "end")
        b.graphics.append((lay, (fnum(st[1]), fnum(st[2])), (fnum(en[1]), fnum(en[2]))))
    # board cutouts live on Edge.Cuts inside the footprints (the stabilizer
    # housings); collect them separately from the board outline
    b.cutout_lines = []
    for fp in kids(root, "footprint"):
        at = kid(fp, "at")
        px, py = fnum(at[1]), fnum(at[2])
        pang = fnum(at[3]) if len(at) > 3 else 0.0
        side = "F" if kid(fp, "layer")[1] == "F.Cu" else "B"
        for ln in kids(fp, "fp_line"):
            if kid(ln, "layer")[1] != "Edge.Cuts":
                continue
            st, en = kid(ln, "start"), kid(ln, "end")
            a = (fnum(st[1]), fnum(st[2]))
            c = (fnum(en[1]), fnum(en[2]))
            if side == "B":
                pass          # no mirror on load, see the pad loop above
            a = (a[0] + px, a[1] + py)
            c = (c[0] + px, c[1] + py)
            b.cutout_lines.append((a, c))
    b.cutouts = cutout_rects(b.cutout_lines)
    for z in kids(root, "zone"):
        lay = kid(z, "layer")
        netn = kid(z, "net_name")
        poly = kid(z, "polygon")
        pts = []
        if poly:
            for p in all_kids(poly, "xy"):
                pts.append((fnum(p[1]), fnum(p[2])))
        b.zones.append((lay[1] if lay else None, netn[1] if netn else None, pts))
    return b


# ------------------------------------------------------------------- checks
def check_connectivity(b):
    errs = []
    by_net = defaultdict(list)
    for it in b.pads:
        if it.net and it.shape != "hole":
            by_net[it.net].append(it)
    for it in b.tracks + b.vias:
        if it.net:
            by_net[it.net].append(it)
    for net, items in sorted(by_net.items()):
        idx = {id(it): i for i, it in enumerate(items)}
        parent = list(range(len(items)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, c):
            ra, rc = find(a), find(c)
            if ra != rc:
                parent[ra] = rc

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                A, B = items[i], items[j]
                if not set(A.layers) & set(B.layers):
                    continue
                if not bbox_overlap(A.bbox, B.bbox):
                    continue
                if item_dist(A, B, None) <= 0.001:
                    union(i, j)
        comps = defaultdict(list)
        for i, it in enumerate(items):
            comps[find(i)].append(it)
        if len(comps) > 1:
            pads = [it for it in items if it.kind == "pad"]
            bad = []
            for root_, group in comps.items():
                n = len([i for i in group if i.kind == "pad"])
                bad.append(n)
            if len([p for p in pads]) > 0:
                errs.append("net %-6s split into %d groups (pad counts %s)"
                            % (net, len(comps), bad))
    return errs


def check_pad_track(b):
    """No track may touch a pad of another net (a shorted pad).

    check_clearance catches this as a clearance error, but a pad that a track
    runs onto is the failure the KiCad DRC reports as shorting_items and it
    deserves a message that says which pad and which net, not a distance.
    """
    errs = []
    for t in b.tracks + b.vias:
        if not t.net:
            continue
        for p in b.pads:
            if not p.net or p.net == t.net or p.shape == "hole":
                continue
            if not set(t.layers) & set(p.layers):
                continue
            if not bbox_overlap(t.bbox, p.bbox):
                continue
            if item_dist(t, p, None) <= 0.001:
                errs.append("track %s on %s touches %s.%s [%s] (short)"
                            % (t.net, t.layers[0] if t.layers else "?",
                               p.ref, p.num, p.net))
    return errs


def _tag(it):
    d = dict(kind=it.kind, net=it.net)
    if hasattr(it, "ref"):
        d["ref"] = it.ref
        d["pad"] = it.num
    if it.kind == "track":
        d["a"] = tuple(round(v, 2) for v in it.a)
        d["b"] = tuple(round(v, 2) for v in it.b)
    if it.kind == "via":
        d["at"] = (round(it.x, 2), round(it.y, 2))
    return str(d)


def check_clearance(b, outline):
    errs = []
    items = b.pads + b.tracks + b.vias
    for i in range(len(items)):
        A = items[i]
        for j in range(i + 1, len(items)):
            B = items[j]
            if A.net is not None and A.net == B.net:
                continue
            if getattr(A, "shape", "") == "hole" and getattr(B, "shape", "") == "hole":
                continue
            layers = set(A.layers) & set(B.layers)
            if not layers:
                continue
            if not bbox_overlap(A.bbox_expanded(CLEAR), B.bbox_expanded(CLEAR)):
                continue
            d = item_dist(A, B, None)
            need = CLEAR
            if d < need - 0.001:
                errs.append("clearance %.3f < %.2f : %s %s vs %s %s"
                            % (d, need, A.kind, _tag(A), B.kind, _tag(B)))
    return errs


def check_edge(b, outline):
    errs = []
    x0, y0, x1, y1 = outline
    for it in b.tracks + b.vias + [p for p in b.pads if p.shape != "hole"]:
        bx0, by0, bx1, by1 = it.bbox
        d = min(bx0 - x0, by0 - y0, x1 - bx1, y1 - by1)
        if d < EDGE_CLEAR - 0.001:
            errs.append("edge clearance %.3f : %s net=%s at (%.2f,%.2f)"
                        % (d, it.kind, it.net, getattr(it, 'x', 0), getattr(it, 'y', 0)))
    return errs


def check_angles(b):
    errs = []
    for t in b.tracks:
        dx = abs(t.b[0] - t.a[0])
        dy = abs(t.b[1] - t.a[1])
        if dx > 1e-6 and dy > 1e-6 and abs(dx - dy) > 1e-3:
            errs.append("track not 0/45/90: (%.3f,%.3f)-(%.3f,%.3f) net=%s"
                        % (t.a[0], t.a[1], t.b[0], t.b[1], t.net))
        if t.w < MIN_W - 1e-9:
            errs.append("track thinner than %.2f: %.3f net=%s" % (MIN_W, t.w, t.net))
    return errs


def check_edge_cuts(b):
    errs = []
    segs = [g for g in b.graphics if g[0] == "Edge.Cuts"]
    if not segs:
        return ["no Edge.Cuts lines"]
    pts = defaultdict(int)
    for _, a, c in segs:
        pts[(round(a[0], 4), round(a[1], 4))] += 1
        pts[(round(c[0], 4), round(c[1], 4))] += 1
    bad = [p for p, n in pts.items() if n != 2]
    if bad:
        errs.append("Edge.Cuts not a closed loop, %d bad vertices (e.g. %s)"
                    % (len(bad), bad[:3]))
    # single cycle: walk
    adj = defaultdict(list)
    for i, (_, a, c) in enumerate(segs):
        adj[(round(a[0], 4), round(a[1], 4))].append((round(c[0], 4), round(c[1], 4)))
        adj[(round(c[0], 4), round(c[1], 4))].append((round(a[0], 4), round(a[1], 4)))
    start = next(iter(adj))
    seen = {start}
    cur = start
    prev = None
    steps = 0
    while True:
        nxt = [p for p in adj[cur] if p != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        steps += 1
        if cur == start:
            break
        if cur in seen:
            errs.append("Edge.Cuts branches at %s" % (cur,))
            break
        seen.add(cur)
    if steps != len(segs):
        errs.append("Edge.Cuts has %d segments but the loop walks %d"
                    % (len(segs), steps))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return errs, (min(xs), min(ys), max(xs), max(ys))


def check_matrix(b):
    """switch <-> diode pairing, polarity and row/col assignment."""
    errs = []
    pads = b.pads
    sw = defaultdict(dict)
    di = defaultdict(dict)
    for p in pads:
        if p.shape == "hole" or not p.ref:
            continue
        if p.ref.startswith("SW") and p.ref[2:].isdigit():
            sw[p.ref][p.num] = p
        elif p.ref.startswith("D") and p.ref[1:].isdigit():
            di[p.ref][p.num] = p
    if not sw:
        return ["no switches found"]
    used_cols = set()
    used_rows = set()
    for ref, pp in sorted(sw.items()):
        if "1" not in pp or "2" not in pp:
            errs.append("%s missing pad 1/2" % ref)
            continue
        colnet = pp["1"].net
        knet = pp["2"].net
        if not colnet or not colnet.startswith("COL"):
            errs.append("%s pad1 on %s, expected a COL net" % (ref, colnet))
        else:
            used_cols.add(colnet)
        dref = "D" + ref[2:]
        if dref not in di:
            errs.append("%s has no diode %s" % (ref, dref))
            continue
        dd = di[dref]
        if dd.get("1") is None or dd.get("2") is None:
            errs.append("%s missing pads" % dref)
            continue
        if dd["2"].net != knet:
            errs.append("%s anode on %s but switch pad2 on %s (polarity)"
                        % (dref, dd["2"].net, knet))
        rnet = dd["1"].net
        if not rnet or not rnet.startswith("ROW"):
            errs.append("%s cathode on %s, expected a ROW net" % (dref, rnet))
        else:
            used_rows.add(rnet)
            # the K net must contain exactly these two pads
            kn = [p for p in pads if p.net == knet and p.shape != "hole"]
            if len(kn) != 2:
                errs.append("net %s has %d pads, expected 2 (%s, %s)"
                            % (knet, len(kn), ref, dref))
    return errs


def _loc(lx, ly, cx, cy, ang):
    """Footprint local coordinate -> board coordinate (KiCad, y down)."""
    a = math.radians(ang)
    c, s = math.cos(a), math.sin(a)
    return (cx + lx * c + ly * s, cy - lx * s + ly * c)


def _switch_angle(pads, cx, cy):
    """Recover the placement angle of a switch from its pad 1 (-3.5, -6.0)."""
    p1 = [p for p in pads if p.shape != "hole" and p.num == "1"]
    if not p1:
        return 0.0
    for ang in (0.0, 90.0, 180.0, -90.0):
        ex, ey = _loc(-3.5, -6.0, cx, cy, ang)
        if math.hypot(p1[0].x - ex, p1[0].y - ey) < 0.01:
            return ang
    return 0.0


def check_stab(b):
    """Choc v2 stabilizer of the wide keys, and the copper clearance around it.

    Every switch of 2 u and wider must carry the four oval clip holes of the
    Kailh Choc v2 PCB mount stabilizer, the two Edge.Cuts cutouts its housing
    hangs through, and the v2 guide post hole of the switch itself (and must not
    carry v1's side pegs, which is what makes the board v2 only).
    Returns ``(errors, report)`` with one tuple per stabilizer.
    """
    errs = []
    holes = [p for p in b.pads if p.shape == "hole"]
    groups = defaultdict(list)
    for p in b.pads:
        if p.fp and CHOC_V2_PREFIX in p.fp:
            groups[(p.ref, p.fp)].append(p)
    copper = [p for p in b.pads if p.shape != "hole" and p.net] + b.tracks + b.vias
    report = []
    for (ref, fname), pads in sorted(groups.items()):
        m = re.search(r"_([0-9.]+)u$", fname)
        if not m or float(m.group(1)) < STAB_MIN_U - 1e-9:
            continue
        width = float(m.group(1))
        centre = [p for p in pads if p.shape == "hole" and abs(p.w - 5.05) < 0.01]
        if len(centre) != 1:
            errs.append("%s: cannot locate the switch centre hole" % ref)
            continue
        cx, cy = centre[0].x, centre[0].y
        # the switch of a stabilizer key is turned 90 degrees, so map the local
        # feature coordinates with the rotation the footprint was placed at
        ang = _switch_angle(pads, cx, cy)
        px, py, pw, ph = V2_POST
        ex, ey = _loc(px, py, cx, cy, ang)
        post = [h for h in holes
                if math.hypot(h.x - ex, h.y - ey) < 0.01
                and abs(h.w - pw) < 0.01 and abs(h.h - ph) < 0.01]
        if not post:
            errs.append("%s: no %.1f x %.1f mm v2 guide post hole at (%.2f, %.2f)"
                        % (ref, pw, ph, ex, ey))
        for sx in (-1, 1):
            vx, vy, vd = V1_PEG
            gx, gy = _loc(sx * vx, vy, cx, cy, ang)
            for h in holes:
                if math.hypot(h.x - gx, h.y - gy) < 0.01 and abs(h.w - vd) < 0.02:
                    errs.append("%s: v1 side peg hole still at (%.2f, %.2f)"
                                % (ref, h.x, h.y))
        # the four clip holes and their clearance
        found = 0
        worst = None
        for sx in (-1, 1):
            for dx, dy, w, hgt in STAB_HOLES:
                ex, ey = cx + sx * dx, cy + dy
                near = [h for h in holes
                        if math.hypot(h.x - ex, h.y - ey) < 0.01
                        and abs(h.w - w) < 0.01 and abs(h.h - hgt) < 0.01]
                if not near:
                    errs.append("%s (%.2fu): no %.1f x %.1f mm hole at (%.2f, %.2f)"
                                % (ref, width, w, hgt, ex, ey))
                    continue
                found += 1
                h = near[0]
                dmin, who = 1e9, None
                for c in copper:
                    if not bbox_overlap(h.bbox_expanded(1.5), c.bbox_expanded(1.5)):
                        continue
                    d = item_dist(c, h, None)
                    if d < dmin:
                        dmin, who = d, c
                if dmin < HOLE_CLEAR - 0.001:
                    errs.append("%s: copper %.3f mm from the %.1f x %.1f mm stab hole "
                                "at (%.2f, %.2f) [%s]"
                                % (ref, dmin, w, hgt, h.x, h.y, _tag(who)))
                if worst is None or dmin < worst[0]:
                    worst = (dmin, w, hgt, h, who)
        report.append((ref, width, found, worst))
    return errs, report


def check_cutouts(b, outline):
    """Stabilizer cutouts: closed, inside the board, and clear of copper.

    Returns ``(errors, report)``; report is ``(n, min_copper_distance)``.
    """
    errs = []
    cos = getattr(b, "cutouts", [])
    x0b, y0b, x1b, y1b = outline
    copper = [p for p in b.pads if p.shape != "hole" and p.net] + b.tracks + b.vias
    dmin = 1e9
    for c in cos:
        if not c["closed"] or c["edges"] != 4:
            errs.append("cutout at (%.2f, %.2f) is not a closed 4 sided loop "
                        "(%d edges, closed=%s)"
                        % (c["x0"], c["y0"], c["edges"], c["closed"]))
            continue
        w, h = c["x1"] - c["x0"], c["y1"] - c["y0"]
        if abs(c["perimeter"] - 2 * (w + h)) > 1e-3:
            errs.append("cutout at (%.2f, %.2f) is not rectangular" % (c["x0"], c["y0"]))
        if (c["x0"] < x0b + EDGE_CLEAR or c["y0"] < y0b + EDGE_CLEAR
                or c["x1"] > x1b - EDGE_CLEAR or c["y1"] > y1b - EDGE_CLEAR):
            errs.append("cutout at (%.2f, %.2f)-(%.2f, %.2f) reaches the board edge"
                        % (c["x0"], c["y0"], c["x1"], c["y1"]))
        poly = [(c["x0"], c["y0"]), (c["x1"], c["y0"]),
                (c["x1"], c["y1"]), (c["x0"], c["y1"])]
        box = (c["x0"], c["y0"], c["x1"], c["y1"])
        for it in copper:
            if not bbox_overlap(box, it.bbox_expanded(HOLE_CLEAR)):
                continue
            if it.kind == "track":
                d = max(0.0, seg_poly_dist(it.a, it.b, poly) - it.w / 2.0)
            elif it.kind == "via":
                d = max(0.0, pt_poly_dist((it.x, it.y), poly) - it.r)
            else:
                d = poly_dist(it.poly, poly)
            dmin = min(dmin, d)
            if d < HOLE_CLEAR - 0.001:
                errs.append("copper %.3f mm from the cutout at (%.2f, %.2f) [%s]"
                            % (d, c["x0"], c["y0"], _tag(it)))
    return errs, (len(cos), dmin)


def check_via_pad(b):
    """No via in pad: every via is clear of every pad and drilled hole.

    A via inside a pad lets the solder wick down the barrel during reflow and
    the hole can tear the pad off when the board flexes or a hot swap socket is
    pulled, so each via of this board has to sit outside the pad copper.  The
    check looks at all pads of both layers, the via's own net included; the
    return value carries the closest pair for the report.
    """
    errs = []
    pads = [p for p in b.pads if p.shape != "hole"]
    holes = [p for p in b.pads if p.shape == "hole"]
    worst = (9.9, None, None)
    for v in b.vias:
        best = (9.9, None)
        for p in pads:
            if not set(v.layers) & set(p.layers):
                continue
            d = item_dist(v, p, None)
            if d < best[0]:
                best = (d, p)
        for h in holes:
            d = item_dist(v, h, None)
            if d < best[0]:
                best = (d, h)
        if best[0] < worst[0]:
            worst = (best[0], v, best[1])
        if best[1] is not None and best[0] < VIA_PAD_CLEAR - 0.001:
            errs.append("via at (%.2f, %.2f) only %.3f mm from %s %s (%s)"
                        % (v.x, v.y, best[0],
                           "hole" if best[1].shape == "hole" else "pad",
                           best[1].num or "-", best[1].ref))
    return errs, worst


def check_diode_socket(b):
    """Every diode is well clear of the hot swap socket of the key below.

    Both the diode (SOD-123, 2.6 x 1.6 mm body) and the socket sit on the back
    side, so the distance between the diode pads and the socket pads of any
    *other* key is the assembly margin: it used to be 2.05 mm, which leaves no
    room for the socket body and the diode body next to each other.
    """
    errs = []
    diodes = defaultdict(list)
    sockets = defaultdict(list)
    for p in b.pads:
        if p.shape == "hole" or not p.ref:
            continue
        if p.fp and "D_SOD-123" in p.fp:
            diodes[p.ref].append(p)
        elif p.fp and "Choc_V2" in p.fp and p.num in ("1", "2"):
            sockets[p.ref].append(p)
    worst = (9.9, None, None)
    for dref, dpads in sorted(diodes.items()):
        best = (9.9, None)
        for sref, spads in sockets.items():
            if dref[1:] == sref[2:]:        # its own key, connected on purpose
                continue
            for d in dpads:
                for s in spads:
                    val = poly_dist(d.poly, s.poly)
                    if val < best[0]:
                        best = (val, sref)
        if best[1] is None:
            continue
        if best[0] < worst[0]:
            worst = (best[0], dref, best[1])
        if best[0] < DIODE_SOCKET_CLEAR - 0.001:
            errs.append("diode %s only %.3f mm from socket pad of %s"
                        % (dref, best[0], best[1]))
    return errs, worst


def check_usbc(b, outline):
    """The USB-C link port: pins, nets, orientation and its place on the edge."""
    errs = []
    fname, pads = None, []
    for p in b.pads:
        if p.shape == "hole" or p.ref != "J1":
            continue
        fname = p.fp
        pads.append(p)
    if not pads:
        return ["no USB-C link port (J1) on the board"], None
    if "USB_C_Receptacle" not in (fname or ""):
        errs.append("J1 is %s, not a USB-C receptacle" % fname)
    by = defaultdict(list)
    for p in pads:
        by[p.num].append(p)
    want = ("A1", "A4", "A5", "A6", "A7", "A8", "A9", "A12",
            "B1", "B4", "B5", "B6", "B7", "B8", "B9", "B12")
    for num in want:
        if len(by.get(num, [])) < 1:
            errs.append("J1 has no pad %s" % num)
    shell = by.get("S1", [])
    if len(shell) != 4:
        errs.append("J1 has %d shell legs, expected 4" % len(shell))
    elif any(p.shape == "hole" for p in shell):
        errs.append("J1 shell legs are not plated through holes")
    sig = [p for p in pads if p.num != "S1"]
    nets = {num: sorted({p.net for p in ps if p.net})
            for num, ps in by.items() if num != "S1"}
    for num in ("A4", "B9", "A9", "B4"):
        if nets.get(num) != ["VCC"]:
            errs.append("J1 %s (VBUS) is on %s, expected VCC" % (num, nets.get(num)))
    for num in ("A1", "B12", "A12", "B1"):
        if nets.get(num) != ["GND"]:
            errs.append("J1 %s (GND) is on %s, expected GND" % (num, nets.get(num)))
    for num in ("A5", "B5", "A8", "B8"):
        if nets.get(num):
            errs.append("J1 %s (CC/SBU) should stay unconnected, is on %s"
                        % (num, nets.get(num)))
    dplus = set(tuple(nets.get(n, [])) for n in ("A6", "B6"))
    dminus = set(tuple(nets.get(n, [])) for n in ("A7", "B7"))
    if len(dplus) != 1 or len(dminus) != 1:
        errs.append("D+ pads A6/B6 or D- pads A7/B7 are not tied together")
    else:
        dp, dm = list(dplus)[0], list(dminus)[0]
        if not dp or not dm or dp == dm:
            errs.append("D+ on %s and D- on %s (must be two different UART nets)" % (dp, dm))
        elif set(dp + dm) != {"TX", "RX"}:
            errs.append("D+/D- on %s/%s, expected the TX/RX pair" % (dp, dm))
    for p in shell:
        if p.net != "GND":
            errs.append("J1 shell leg at (%.2f, %.2f) on %s, expected GND"
                        % (p.x, p.y, p.net))
    # The connector's mouth has to face the top board edge: the 16 pins sit at
    # the BACK of the part, so the pad row is about 7.2 mm inside the edge while
    # the 8.94 x 7.30 mm body overhangs it by 0.46 mm.
    row_y = sum(p.y for p in sig) / float(len(sig))
    y0 = outline[1] if outline else None
    if y0 is not None:
        inset = row_y - y0
        if not (6.0 - 1e-6 <= inset <= 8.5 + 1e-6):
            errs.append("J1 pad row is %.3f mm inside the top edge (expected 6.0 .. "
                        "8.5: the pins at the back, the mouth at the edge)" % inset)
        near = min(p.y - max(p.w, p.h) / 2.0 for p in pads)
        if near < y0 + 1.0 - 1e-6:
            errs.append("J1 copper reaches within %.2f mm of the top board edge"
                        % (near - y0))
    cx = sum(p.x for p in sig) / float(len(sig))
    rep = dict(ref="J1", fp=fname, x=cx, y=row_y,
               tip=row_y - (outline[1] if outline else 0), n=len(pads),
               dplus=list(dplus)[0] if len(dplus) == 1 else None,
               dminus=list(dminus)[0] if len(dminus) == 1 else None)
    return errs, rep


def check_zones(b):
    errs = []
    zl = [(l, n) for (l, n, pts) in b.zones if n == "GND"]
    layers = set(l for l, n in zl)
    for L in ("F.Cu", "B.Cu"):
        if L not in layers:
            errs.append("no GND zone on %s" % L)
    for (l, n, pts) in b.zones:
        if len(pts) < 4:
            errs.append("GND zone on %s has no polygon" % l)
    return errs


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = argv[1:] or [
        os.path.join(root, "pcb", "choc-split-60-left.kicad_pcb"),
        os.path.join(root, "pcb", "choc-split-60-right.kicad_pcb"),
    ]
    rc = 0
    for f in files:
        print("=" * 70)
        print("checking", os.path.basename(f))
        b = load(f)
        res = check_edge_cuts(b)
        if isinstance(res, tuple):
            edge_errs, outline = res
        else:
            edge_errs, outline = res, None
        errs = []
        errs += edge_errs
        if outline:
            errs += check_edge(b, outline)
        errs += check_clearance(b, outline)
        errs += check_pad_track(b)
        errs += check_connectivity(b)
        errs += check_matrix(b)
        errs += check_zones(b)
        errs += check_angles(b)
        stab_errs, stab = check_stab(b)
        errs += stab_errs
        cut_errs, (n_cut, cut_min) = check_cutouts(b, outline)
        errs += cut_errs
        via_errs, (via_d, via_it, via_near) = check_via_pad(b)
        errs += via_errs
        dio_errs, (dio_d, dio_ref, dio_sock) = check_diode_socket(b)
        errs += dio_errs
        usb_errs, usb = check_usbc(b, outline)
        errs += usb_errs
        n_pads = len([p for p in b.pads if p.shape != "hole"])
        print("  pads=%d tracks=%d vias=%d nets=%d" %
              (n_pads, len(b.tracks), len(b.vias), len(b.nets)))
        n_stab = sum(1 for r in stab)
        print("  stabilizers=%d holes=%d cutouts=%d (nearest copper %.3f mm)"
              % (n_stab, 4 * n_stab, n_cut, cut_min))
        for ref, width, found, worst in stab:
            line = "    %-5s %.2fu: %d/4 holes" % (ref, width, found)
            if worst:
                line += ", nearest copper %.3f mm (%.1f x %.1f hole at %.2f, %.2f)" % (
                    worst[0], worst[1], worst[2], worst[3].x, worst[3].y)
            print(line)
        if errs:
            rc = 1
            print("  %d problem(s):" % len(errs))
            for e in errs[:40]:
                print("   -", e)
            if len(errs) > 40:
                print("   ... %d more" % (len(errs) - 40))
        else:
            print("  OK: all checks passed")
        if via_near is not None:
            print("  via in pad: %d vias, nearest pad/hole %.3f mm (via at %.2f, %.2f, %s %s)"
                  % (len(b.vias), via_d, via_it.x, via_it.y,
                     "hole" if via_near.shape == "hole" else "pad",
                     via_near.ref))
        if dio_sock is not None:
            print("  diode to next row socket: nearest %.3f mm (%s to %s)"
                  % (dio_d, dio_ref, dio_sock))
        if usb:
            print("  USB-C link %s: %d pads centred (%.2f, %.2f), pad row %.2f mm "
                  "inside the top edge (mouth at the edge), D+ %s / D- %s"
                  % ((usb["fp"] or "").replace("choc60:", ""),
                     usb["n"], usb["x"], usb["y"],
                     usb["tip"], usb["dplus"], usb["dminus"]))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
