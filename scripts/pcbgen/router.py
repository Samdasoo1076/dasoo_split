"""Grid maze router with 45 degree moves and through vias.

The router only has to close the fan-in from the matrix truss and the power /
serial nets to the controller, because the key matrix itself is placed by
hand (see build.build_truss).  Movement is 8-connected, so every produced
segment is horizontal, vertical or exactly 45 degrees.
"""
import heapq
import math

import numpy as np

SIG = 0.25
PWR = 0.5
CLEAR = 0.2
CUT_CLEAR = 0.50        # copper to a board cutout edge (Edge.Cuts)
VIA_D = 0.6
VIA_DRILL = 0.3


def _segdist(a, b, c, d):
    def ps(p, x, y):
        dx, dy = y[0] - x[0], y[1] - x[1]
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            return math.hypot(p[0] - x[0], p[1] - x[1])
        t = max(0.0, min(1.0, ((p[0] - x[0]) * dx + (p[1] - x[1]) * dy) / L2))
        return math.hypot(p[0] - (x[0] + t * dx), p[1] - (x[1] + t * dy))
    return min(ps(a, c, d), ps(b, c, d), ps(c, a, b), ps(d, a, b))


class Router:
    def __init__(self, board, step=0.25):
        self.b = board
        x0, y0, x1, y1 = board.cfg["outline"]
        self.step = step
        self.ox = x0
        self.oy = y0
        self.nx = int(math.ceil((x1 - x0) / step)) + 1
        self.ny = int(math.ceil((y1 - y0) / step)) + 1
        self.blocked = [np.zeros((self.ny, self.nx), dtype=bool) for _ in range(2)]
        self.owner = [np.zeros((self.ny, self.nx), dtype=np.int16) for _ in range(2)]
        self.obst = [np.zeros((self.ny, self.nx), dtype=bool) for _ in range(2)]
        self.obst_net = [np.zeros((self.ny, self.nx), dtype=np.int16) for _ in range(2)]
        self.failed = []

    # ---------------------------------------------------------------- helpers
    def cell(self, x, y):
        return (int(round((y - self.oy) / self.step)), int(round((x - self.ox) / self.step)))

    def xy(self, iy, ix):
        return (self.ox + ix * self.step, self.oy + iy * self.step)

    def _bbox(self, x, y, r):
        ix0 = max(0, int(math.floor((x - r - self.ox) / self.step)))
        ix1 = min(self.nx - 1, int(math.ceil((x + r - self.ox) / self.step)))
        iy0 = max(0, int(math.floor((y - r - self.oy) / self.step)))
        iy1 = min(self.ny - 1, int(math.ceil((y + r - self.oy) / self.step)))
        return iy0, iy1, ix0, ix1

    def _mask(self, x, y, w, h, ang, shape, margin):
        r = math.hypot(w, h) / 2 + margin
        iy0, iy1, ix0, ix1 = self._bbox(x, y, r)
        if iy1 < iy0 or ix1 < ix0:
            return None
        ys = self.oy + np.arange(iy0, iy1 + 1) * self.step
        xs = self.ox + np.arange(ix0, ix1 + 1) * self.step
        dx = xs[None, :] - x
        dy = ys[:, None] - y
        a = math.radians(ang)
        c, s = math.cos(a), math.sin(a)
        u = dx * c - dy * s
        v = dx * s + dy * c
        if shape == "circle":
            rr = w / 2.0 + margin
            m = (u * u + v * v) <= rr * rr
        elif shape in ("rect", "roundrect"):
            m = (np.abs(u) <= w / 2.0 + margin) & (np.abs(v) <= h / 2.0 + margin)
        elif shape == "oval":
            if w >= h:
                rr = h / 2.0 + margin
                ln = (w - h) / 2.0
                m = (np.maximum(np.abs(u) - ln, 0) ** 2 + v ** 2) <= rr * rr
            else:
                rr = w / 2.0 + margin
                ln = (h - w) / 2.0
                m = (u ** 2 + np.maximum(np.abs(v) - ln, 0) ** 2) <= rr * rr
        else:
            m = np.zeros((len(ys), len(xs)), dtype=bool)
        return iy0, iy1, ix0, ix1, m

    def _stamp(self, arr, layer, x, y, w, h, ang, shape, margin, value=True):
        got = self._mask(x, y, w, h, ang, shape, margin)
        if got is None:
            return
        iy0, iy1, ix0, ix1, m = got
        if value is True:
            arr[layer][iy0:iy1 + 1, ix0:ix1 + 1] |= m
        else:
            arr[layer][iy0:iy1 + 1, ix0:ix1 + 1] &= ~m

    def _obst(self, lay, x, y, w, h, ang, shape, margin, nid):
        got = self._mask(x, y, w, h, ang, shape, margin)
        if got is None:
            return
        iy0, iy1, ix0, ix1, m = got
        self.obst[lay][iy0:iy1 + 1, ix0:ix1 + 1] |= m
        self.obst_net[lay][iy0:iy1 + 1, ix0:ix1 + 1][m] = nid

    # ------------------------------------------------------------------ masks
    def build_masks(self, edge_margin=0.55):
        b = self.b
        x0, y0, x1, y1 = b.cfg["outline"]
        self.blocked = [np.zeros((self.ny, self.nx), dtype=bool) for _ in range(2)]
        self.owner = [np.zeros((self.ny, self.nx), dtype=np.int16) for _ in range(2)]
        self.obst = [np.zeros((self.ny, self.nx), dtype=bool) for _ in range(2)]
        self.obst_net = [np.zeros((self.ny, self.nx), dtype=np.int16) for _ in range(2)]
        # board edge keepout
        ys = self.oy + np.arange(self.ny) * self.step
        xs = self.ox + np.arange(self.nx) * self.step
        outside = ((xs[None, :] < x0 + edge_margin) | (xs[None, :] > x1 - edge_margin) |
                   (ys[:, None] < y0 + edge_margin) | (ys[:, None] > y1 - edge_margin))
        for l in range(2):
            self.blocked[l] |= outside
        # pads
        for fp in b.fps:
            for p in fp.pads:
                self.add_pad(p, track_w=SIG)
        # board cutouts of the stabilizer keys: keep the whole rectangle free
        for c in getattr(b, "cutouts", []):
            for l in range(2):
                self._stamp(self.blocked, l,
                            (c["x0"] + c["x1"]) / 2.0,
                            (c["y0"] + c["y1"]) / 2.0,
                            c["x1"] - c["x0"], c["y1"] - c["y0"],
                            0.0, "rect", CUT_CLEAR)
        # truss copper
        for tr in b.tracks:
            self.add_track(tr, track_w=tr.width)
        for v in b.vias:
            self.add_via_copper(v)

    def add_pad(self, p, track_w=SIG):
        if p.net is None:
            nid = 0
        else:
            nid = self.b.net_id[p.net]
        inflate = CLEAR + PWR / 2 + 0.12
        if p.is_hole:
            for l in range(2):
                self._stamp(self.blocked, l, p.gx, p.gy, p.w, p.h, p.gang, p.shape,
                            inflate + 0.10)
            return
        for l in p.pad_layers():
            lay = 0 if l == "F.Cu" else 1
            self._obst(lay, p.gx, p.gy, p.w, p.h, p.gang, p.shape, inflate, nid)
            if nid:
                got = self._mask(p.gx, p.gy, p.w, p.h, p.gang, p.shape, -0.05)
                if got:
                    iy0, iy1, ix0, ix1, m = got
                    self.owner[lay][iy0:iy1 + 1, ix0:ix1 + 1][m] = nid

    def add_track(self, tr, track_w=None):
        nid = self.b.net_id[tr.net]
        lay = 0 if tr.layer == "F.Cu" else 1
        w = track_w or tr.width
        self._raster_line(lay, tr.a, tr.b, w, nid, inflate=CLEAR + PWR / 2 + 0.12)

    def add_via_copper(self, v):
        nid = self.b.net_id[v.net]
        for lay in range(2):
            self._obst(lay, v.x, v.y, v.dia, v.dia, 0, "circle",
                       CLEAR + PWR / 2 + 0.12, nid)
            # Only cells whose centre is really on the via disc count as
            # "already this net's copper": a path may start from an owner cell,
            # and commit() begins the track at the cell centre, so a cell just
            # outside the disc would produce a track that touches nothing.
            iy, ix = self.cell(v.x, v.y)
            r = max(1, int(round(v.dia / 2 / self.step)))
            for jy in range(iy - r, iy + r + 1):
                for jx in range(ix - r, ix + r + 1):
                    if 0 <= jy < self.ny and 0 <= jx < self.nx:
                        cx, cy = self.xy(jy, jx)
                        if math.hypot(cx - v.x, cy - v.y) <= v.dia / 2 + 1e-9:
                            self.owner[lay][jy, jx] = nid

    def _raster_line(self, lay, a, b, w, nid, inflate, obst=False):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / (self.step * 0.25)) + 1)
        for i in range(n + 1):
            t = i / n
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            self._obst(lay, x, y, 2 * inflate, 2 * inflate, 0, "circle", 0.0, nid)
            got = self._mask(x, y, w, w, 0, "circle", -(w / 2 + 0.03))
            if got is None:
                # still mark the exact centre cell
                iy, ix = self.cell(x, y)
                self.owner[lay][iy, ix] = nid
                continue
            iy0, iy1, ix0, ix1, m = got
            self.owner[lay][iy0:iy1 + 1, ix0:ix1 + 1][m] = nid

    # --------------------------------------------------------------- searching
    def _blocked_for(self, nid):
        out = []
        for l in range(2):
            cls = self.blocked[l] | (self.obst[l] & (self.obst_net[l] != nid))
            out.append(cls)
        return out

    def path(self, nid, sources, goal_cells, width=SIG, prefer=("H", "V"),
             via_cost=45.0, max_expand=1500000, hcost=1.0):
        """Multi source A*: sources and goals are (layer, iy, ix) tuples."""
        blocked = self._blocked_for(nid)
        # allow the goals even if blocked by their own pad inflation
        goalset = set(goal_cells)
        dist = {}
        prev = {}
        pq = []
        gx = sum(g[2] for g in goalset) / float(len(goalset))
        gy = sum(g[1] for g in goalset) / float(len(goalset))
        for (l, iy, ix) in sources:
            dist[(l, iy, ix)] = 0.0
            prev[(l, iy, ix)] = None
            h = math.hypot(ix - gx, iy - gy) * hcost
            heapq.heappush(pq, (h, 0.0, l, iy, ix, -1))
        best = None
        expanded = 0
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        prefh = bool(prefer) and prefer[0] == "H"
        while pq:
            f, g, l, iy, ix, pdir = heapq.heappop(pq)
            key = (l, iy, ix)
            if g > dist.get(key, 1e18) + 1e-9:
                continue
            if key in goalset and g > 0:
                best = key
                break
            expanded += 1
            if expanded > max_expand:
                break
            for d, (dy, dx) in enumerate(dirs):
                ny, nx_ = iy + dy, ix + dx
                if ny < 0 or nx_ < 0 or ny >= self.ny or nx_ >= self.nx:
                    continue
                nkey = (l, ny, nx_)
                if nkey in goalset:
                    nong = 1.0
                else:
                    if blocked[l][ny, nx_]:
                        continue
                if dy and dx:
                    if blocked[l][iy, nx_] and (l, iy, nx_) not in goalset:
                        continue
                    if blocked[l][ny, ix] and (l, ny, ix) not in goalset:
                        continue
                step = math.hypot(dx, dy)
                # F.Cu carries the horizontal (row) wiring, B.Cu the vertical
                # (column) wiring, so a move along the layer's own direction is
                # cheap and a move across it is expensive.
                if prefer is None:
                    cost = step * (1.0 if (dy == 0 or dx == 0) else 1.28)
                elif dy == 0:            # horizontal
                    cost = step * (1.0 if prefh else 1.55)
                elif dx == 0:            # vertical
                    cost = step * (1.55 if prefh else 1.0)
                else:                    # 45 degree
                    cost = step * 1.28
                if pdir >= 0 and pdir != d:
                    cost += 0.35
                ng = g + cost
                if ng < dist.get(nkey, 1e18) - 1e-9:
                    if nkey not in goalset and blocked[l][ny, nx_]:
                        continue
                    dist[nkey] = ng
                    prev[nkey] = (key, d)
                    h = math.hypot(nx_ - gx, ny - gy) * hcost
                    heapq.heappush(pq, (ng + h, ng, l, ny, nx_, d))
            # layer change
            if True:
                ol = 1 - l
                okey = (ol, iy, ix)
                if (not blocked[ol][iy, ix]) and self._via_ok(blocked, iy, ix):
                    ng = g + via_cost
                    if ng < dist.get(okey, 1e18) - 1e-9:
                        dist[okey] = ng
                        prev[okey] = (key, -1)
                        h = math.hypot(ix - gx, iy - gy) * hcost
                        heapq.heappush(pq, (ng + h, ng, ol, iy, ix, -1))
        if best is None:
            return None
        # reconstruct
        out = []
        k = best
        while k is not None:
            out.append(k)
            p = prev[k]
            k = p[0] if p else None
        out.reverse()
        return out

    def _via_ok(self, blocked, iy, ix):
        r = 2
        if iy < r or ix < r or iy + r >= self.ny or ix + r >= self.nx:
            return False
        for l in range(2):
            if blocked[l][iy - r:iy + r + 1, ix - r:ix + r + 1].any():
                return False
        return True

    def audit_tracks(self, net):
        b = self.b
        new = b.tracks[-1]
        for t in b.tracks[:-1]:
            if t.net == new.net or t.layer != new.layer:
                continue
            d = _segdist(new.a, new.b, t.a, t.b)
            if d < 0.2:
                print("  !! %s crosses %s (d=%.3f) at %s-%s vs %s-%s"
                      % (new.net, t.net, d, new.a, new.b, t.a, t.b))

    def audit(self, nid, cells, net):
        bl = self._blocked_for(nid)
        bad = [c for c in cells if bl[c[0]][c[1], c[2]]]
        if bad:
            print("  !! %s path crosses %d blocked cell(s), e.g. %s" % (net, len(bad), bad[:3]))

    def commit(self, nid, cells, width, net):
        """Turn a cell path into tracks / vias on the board."""
        self.audit(nid, cells, net)
        pts = []
        for (l, iy, ix) in cells:
            x, y = self.xy(iy, ix)
            pts.append((l, x, y))
        i = 0
        while i < len(pts) - 1:
            l, x, y = pts[i]
            j = i + 1
            # extend while same layer and same direction
            dx0 = pts[j][1] - x
            dy0 = pts[j][2] - y
            while j + 1 < len(pts) and pts[j + 1][0] == l:
                dx1 = pts[j + 1][1] - pts[j][1]
                dy1 = pts[j + 1][2] - pts[j][2]
                if abs(dx1) < 1e-9 and abs(dy1) < 1e-9:
                    j += 1
                    continue
                if abs(dx1) < 1e-9 and abs(dx0) < 1e-9:
                    j += 1
                elif abs(dy1) < 1e-9 and abs(dy0) < 1e-9:
                    j += 1
                elif abs(abs(dx1) - abs(dy1)) < 1e-9 and abs(abs(dx0) - abs(dy0)) < 1e-9 \
                        and (dx1 * dx0 > 0) and (dy1 * dy0 > 0):
                    j += 1
                elif abs(dx1) < 1e-9 and abs(dx0) < 1e-9:
                    j += 1
                else:
                    break
            layer = "F.Cu" if l == 0 else "B.Cu"
            self.b.add_track((x, y), (pts[j][1], pts[j][2]), width, layer, net)
            # rasterize into the masks
            self.add_track(self.b.tracks[-1], track_w=width)
            self.audit_tracks(net)
            self.owner[l][self.cell(x, y)[0], self.cell(x, y)[1]] = nid
            i = j
        # vias
        for a, bb in zip(cells, cells[1:]):
            if a[0] != bb[0]:
                x, y = self.xy(a[1], a[2])
                self.b.add_via(x, y, net)
                self.add_via_copper(self.b.vias[-1])
