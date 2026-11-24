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
  7. every switch of 2 u and wider carries the four holes of the Cherry MX PCB
     mount stabilizer (2.00 u pattern) and no copper comes near them

Usage:  python3 scripts/verify_pcb.py [pcb/*.kicad_pcb ...]
"""
import math
import os
import re
import sys
from collections import defaultdict

CLEAR = 0.20          # copper to copper clearance (mm)
EDGE_CLEAR = 0.30     # copper to board edge
HOLE_CLEAR = 0.20     # copper to NPTH hole edge
MIN_W = 0.25          # thinnest track we accept
TOL = 1e-6

# Cherry MX PCB mount stabilizer, 2.00 u hole pattern (the same holes serve the
# 2.25 u keys): 11.938 mm beside the key centre, a 3.048 mm positioning hole
# behind the switch and a 3.9878 mm mounting hole towards the front.
STAB_MIN_U = 2.0
STAB_X = 11.938
STAB_PATTERN = ((3.048, -6.985), (3.9878, 8.225))

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
                lx = -lx
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
                    b.pads.append(Item("pad", None, ["F.Cu", "B.Cu"],
                                       (gx - hole[0] / 2, gy - hole[1] / 2,
                                        gx + hole[0] / 2, gy + hole[1] / 2),
                                       poly=poly_of(gx, gy, hole[0], hole[1], gang, "circle"),
                                       num="", ref=ref, fp=fname, x=gx, y=gy,
                                       w=hole[0], h=hole[1], hole=None, shape="hole"))
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


def check_stab(b):
    """Stabilizer holes of the wide keys and the copper clearance around them.

    A 2 u (or wider) key is useless without a stabilizer, so every switch that
    wide must carry the four NPTH holes of the standard Cherry MX PCB mount
    pattern, and neither track, via nor pad may come inside the clearance.
    Returns ``(errors, report)`` where report is one tuple per stabilizer.
    """
    errs = []
    holes = [p for p in b.pads if p.shape == "hole"]
    groups = defaultdict(list)
    for p in b.pads:
        if p.fp and "SW_Hotswap_Kailh_Choc_V1_" in p.fp:
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
        found = 0
        worst = None
        for sx in (-1, 1):
            for drill, dy in STAB_PATTERN:
                ex, ey = cx + sx * STAB_X, cy + dy
                near = [h for h in holes
                        if math.hypot(h.x - ex, h.y - ey) < 0.01
                        and abs(h.w - drill) < 0.01]
                if not near:
                    errs.append("%s (%.2fu): no %.4f mm hole at (%.2f, %.2f)"
                                % (ref, width, drill, ex, ey))
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
                if dmin < CLEAR - 0.001:
                    errs.append("%s: copper %.3f mm from the %.4f mm stab hole at "
                                "(%.2f, %.2f) [%s]"
                                % (ref, dmin, drill, h.x, h.y, _tag(who)))
                if worst is None or dmin < worst[0]:
                    worst = (dmin, drill, h, who)
        report.append((ref, width, found, worst))
    return errs, report


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
        errs += check_connectivity(b)
        errs += check_matrix(b)
        errs += check_zones(b)
        errs += check_angles(b)
        stab_errs, stab = check_stab(b)
        errs += stab_errs
        n_pads = len([p for p in b.pads if p.shape != "hole"])
        print("  pads=%d tracks=%d vias=%d nets=%d" %
              (n_pads, len(b.tracks), len(b.vias), len(b.nets)))
        n_stab = sum(1 for r in stab)
        print("  stabilizers=%d holes=%d" % (n_stab, 4 * n_stab))
        for ref, width, found, worst in stab:
            line = "    %-5s %.2fu: %d/4 holes" % (ref, width, found)
            if worst:
                line += ", nearest copper %.3f mm (%.4f mm hole at %.2f, %.2f)" % (
                    worst[0], worst[1], worst[2].x, worst[2].y)
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
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
